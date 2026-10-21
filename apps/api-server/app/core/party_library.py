"""从案件数据推出当事人库：我方/对方、诉讼地位、客户与当事人分类。"""
import re
import unicodedata

from datetime import datetime

from sqlalchemy import delete, func, insert, select

from app.data_models.ipr_cases import IprCaseCustomer
from app.data_models.parties import PartyRecord
from app.data_models.party_library import PartyLibraryEntry
from app.data_models.records import BusinessRecord

MIGRATION_REVISION = "party_library_v1"
PARTY_MASTER_REVISION = "party_master_v1"
_SPLIT = re.compile(r"[,，、;；\n]+")
_PLAINTIFF = "原告"
_DEFENDANT = "被告"
_THIRD = "第三人"


CASE_CATEGORIES = ("民事", "行政", "刑事", "仲裁", "法律顾问")
NON_LITIGATION = "非诉讼"  # 知识产权（商标/专利/著作权）等非诉讼案件，当事人是案件关联的申请人


def case_category(case_type) -> str:
    """案件类型归并到民事/行政/刑事/仲裁/法律顾问，其余（含未填）归为“其他”。"""
    text = str(case_type or "").strip()
    return next((name for name in CASE_CATEGORIES if text.startswith(name)), "其他")


# 仲裁案件不称原告/被告，其余称谓保持不变。
ARBITRATION_POSITIONS = {"原告": "申请人", "被告": "被申请人"}


def _normalize(value) -> str:
    return unicodedata.normalize("NFKC", str(value or "").strip()).casefold()


def _names(value) -> list[str]:
    """案件里的主体既可能是名单，也可能是逗号分隔的旧库字符串。"""
    if isinstance(value, (list, tuple)):
        raw = [str(item.get("name") if isinstance(item, dict) else item or "") for item in value]
    elif value:
        raw = _SPLIT.split(str(value))
    else:
        raw = []
    return list(dict.fromkeys(item.strip() for item in raw if item and item.strip()))


def _position_label(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith(("原告", "申请人")):
        return _PLAINTIFF
    if text.startswith(("被告", "被申请人")):
        return _DEFENDANT
    return _THIRD if text.startswith("第三人") else text


def case_party_layout(case: dict) -> dict:
    """返回我方/对方名单、双方诉讼地位；旧库的 opponent 与 defendant 同义。"""
    data = case.get("data") or {}
    client = str(case.get("customer") or "").strip()
    plaintiffs = _names(data.get("plaintiffs") or data.get("plaintiff"))
    defendants = _names(data.get("defendants") or data.get("defendant") or data.get("opponent"))
    thirds = _names(data.get("third_parties"))
    position = _position_label(data.get("client_position"))
    if not position:
        position = (_PLAINTIFF if client in plaintiffs else _DEFENDANT if client in defendants
                    else _THIRD if client in thirds else "")
    if not position and client and (plaintiffs or defendants):
        # 委托人不在名单里（多为关联主体）：被告方明确时视为原告方，反之亦然。
        position = _DEFENDANT if plaintiffs and not defendants else _PLAINTIFF
    sides = {_PLAINTIFF: plaintiffs, _DEFENDANT: defendants, _THIRD: thirds}
    ours = list(sides.get(position) or [])
    if client and client not in ours:
        ours.insert(0, client)
    if position == _PLAINTIFF:
        theirs, their_position = defendants, _DEFENDANT
    elif position == _DEFENDANT:
        theirs, their_position = plaintiffs, _PLAINTIFF
    else:
        theirs, their_position = [name for name in (*plaintiffs, *defendants) if name not in ours], ""
    theirs = [name for name in theirs if name not in ours]
    # 对方各人的诉讼地位以名单为准：我方是第三人时，对方原告/被告各自保留自己的地位。
    their_positions = {name: _PLAINTIFF if name in plaintiffs else _DEFENDANT if name in defendants else their_position
                       for name in theirs}
    if position == _THIRD:
        their_position = f"{_PLAINTIFF}/{_DEFENDANT}"  # 我方是第三人：对方是原告和被告
    # 不在我方、也不在对方名单里的第三人（如我方是原告时案件里的第三人）单独列出，诉讼地位为第三人。
    others = [name for name in thirds if name not in ours and name not in theirs]
    return {"ours": ours, "our_position": position, "theirs": theirs, "their_position": their_position,
            "others": others,
            "positions": {name: position for name in ours} | their_positions | {name: _THIRD for name in others}}


def build_entries(case: dict, client_titles: set[str], managers: list[str], party_records: dict | None = None) -> list[dict]:
    """party_records：规范化名称 -> (当事人表 id, 当事人编号, 来源客户记录 id)。"""
    manager_key = "|" + "|".join(managers) + "|" if managers else ""
    layout = case_party_layout(case)
    client = str(case.get("customer") or "").strip()
    category = case_category((case.get("data") or {}).get("case_type"))
    label = (lambda position: ARBITRATION_POSITIONS.get(position, position)) if category == "仲裁" else (lambda position: position)
    entries = []
    for name in [*layout["ours"], *layout["theirs"], *layout["others"]]:
        if _normalize(name) == _normalize(client) or _normalize(name) in client_titles:
            continue  # 客户不进当事人库，只作为“我方当事人”出现在行里
        record = (party_records or {}).get(_normalize(name))
        entries.append({
            "party_id": record[0] if record else None, "party_no": record[1] if record else "",
            "customer_record_id": record[2] if record else None,
            "case_id": case["id"], "case_no": case["serial_no"], "subject_name": name,
            "case_category": category,
            "subject_type": "当事人",
            "subject_position": label(layout["positions"].get(name, "")),
            "our_parties": layout["ours"], "our_position": label(layout["our_position"]),
            "opponent_parties": layout["theirs"], "opponent_position": label(layout["their_position"]),
            "managers": managers, "manager_key": manager_key, "case_status": str(case.get("status") or ""),
        })
    return entries


def next_party_no(existing_numbers, year: str | None = None) -> str:
    """新建当事人编号：DSR + 两位年份 + 5 位流水，只按当事人表里的编号计数。"""
    prefix = f"DSR{datetime.now():%y}" if year is None else f"DSR{year}"
    top = max((int(number[len(prefix):]) for number in existing_numbers
               if number.startswith(prefix) and number[len(prefix):].isdigit() and len(number) == len(prefix) + 5), default=0)
    return f"{prefix}{top + 1:05d}"


def sync_parties_from_customers(connection) -> int:
    """把客户表里非“客户”类型的记录登记进当事人表，编号沿用客户编号；只读客户表，不改它。"""
    have = {row[0] for row in connection.execute(select(PartyRecord.source_customer_id).where(PartyRecord.source_customer_id.is_not(None))).all()}
    taken = {row[0] for row in connection.execute(select(PartyRecord.party_no)).all()}
    rows = []
    for record_id, serial_no, title, owner, department, status, data, description in connection.execute(select(
            BusinessRecord.id, BusinessRecord.serial_no, BusinessRecord.title, BusinessRecord.owner, BusinessRecord.department,
            BusinessRecord.status, BusinessRecord.data, BusinessRecord.description,
    ).where(BusinessRecord.module == "customer").order_by(BusinessRecord.id)).all():
        data = data or {}
        kind = data.get("customer_type", "客户")
        if kind == "客户" or record_id in have or serial_no in taken or not str(title or "").strip():
            continue
        managers = data.get("customer_managers") or ([owner] if owner else [])
        rows.append({
            "party_no": serial_no, "name": str(title).strip(), "party_type": str(kind or "当事人"), "source_customer_id": record_id,
            "owner": owner or "", "department": department or "",
            "managers": [str(item) for item in (managers if isinstance(managers, list) else [managers]) if item],
            "status": status or "", "description": description or "", "data": data, "created_by": "migration",
        })
        taken.add(serial_no)
    for start in range(0, len(rows), 1000):
        connection.execute(insert(PartyRecord), rows[start:start + 1000])
    return len(rows)


def _register_missing_parties(connection, rows: list[dict]) -> int:
    """案件里出现过、当事人表里没有的人，登记进当事人表并发 DSR 号；只写当事人表。"""
    unresolved: dict[str, dict] = {}
    for row in rows:
        if not row["party_no"]:
            unresolved.setdefault(_normalize(row["subject_name"]), row)
    if not unresolved:
        return 0
    taken = {number for (number,) in connection.execute(select(PartyRecord.party_no)).all()}
    from app.data_models.identity import User
    departments = dict(connection.execute(select(User.username, User.department)).all())
    created: dict[str, tuple[str, str]] = {}
    new_rows = []
    for key, row in unresolved.items():
        number = next_party_no(taken)
        taken.add(number)
        owner = (row["managers"] or [""])[0]
        new_rows.append({
            "party_no": number, "name": row["subject_name"], "party_type": "当事人", "source_customer_id": None,
            "owner": owner, "department": departments.get(owner, "") or "", "managers": list(row["managers"] or []),
            "status": "潜在", "description": f"由案件 {row['case_no']} 当事人信息登记",
            "data": {"case_litigant_origin": {"case_id": row["case_id"], "case_no": row["case_no"], "roles": [row["subject_position"]]}},
            "created_by": "system",
        })
        created[key] = (number, row["subject_name"])
    for start in range(0, len(new_rows), 1000):
        connection.execute(insert(PartyRecord), new_rows[start:start + 1000])
    ids = {_normalize(name): pid for pid, name in connection.execute(
        select(PartyRecord.id, PartyRecord.name).where(PartyRecord.party_no.in_([number for number, _ in created.values()]))).all()}
    for row in rows:
        key = _normalize(row["subject_name"])
        if not row["party_no"] and key in created:
            row["party_no"] = created[key][0]
            row["party_id"] = ids.get(key)
    return len(new_rows)


def rebuild_party_library(connection) -> int:
    """先把客户表里的当事人类型记录登记进当事人表，再按案件重建当事人库，案件里没登记过的人自动登记并发 DSR 号。
    只写当事人表和当事人库，不改案件和客户表。"""
    sync_parties_from_customers(connection)
    customers = connection.execute(select(
        BusinessRecord.id, BusinessRecord.title, BusinessRecord.owner, BusinessRecord.data,
    ).where(BusinessRecord.module == "customer", BusinessRecord.status != "已回收").order_by(BusinessRecord.id)).all()
    client_titles = {_normalize(title) for _, title, _, data in customers if (data or {}).get("customer_type", "客户") == "客户" and _normalize(title)}
    # 当事人沿用档案里的编号；同名取最早的一条，已回收的不参与对应。
    party_records: dict[str, tuple[int, str, int | None]] = {}
    party_by_customer: dict[int, tuple[int, str]] = {}
    for pid, number, name, customer_id, status in connection.execute(select(
            PartyRecord.id, PartyRecord.party_no, PartyRecord.name, PartyRecord.source_customer_id, PartyRecord.status,
    ).order_by(PartyRecord.source_customer_id.is_(None), PartyRecord.id)).all():  # 同名时优先沿用从客户挪来的老编号
        if customer_id is not None:
            party_by_customer[customer_id] = (pid, number)
        if status != "已回收" and _normalize(name):
            party_records.setdefault(_normalize(name), (pid, number, customer_id))
    managers_by_id = {}
    for record_id, _, owner, data in customers:
        managers = (data or {}).get("customer_managers") or ([owner] if owner else [])
        managers_by_id[record_id] = [str(item) for item in (managers if isinstance(managers, list) else [managers]) if item]
    rows: list[dict] = []
    cases = connection.execute(select(
        BusinessRecord.id, BusinessRecord.serial_no, BusinessRecord.customer, BusinessRecord.owner, BusinessRecord.data,
        BusinessRecord.status,
    ).where(BusinessRecord.module == "case")).all()
    for case_id, serial_no, customer, owner, data, case_status in cases:
        data = data or {}
        try:
            customer_id = int(data.get("customer_id") or data.get("customer_record_id") or 0)
        except (TypeError, ValueError):
            customer_id = 0
        managers = managers_by_id.get(customer_id) or ([owner] if owner else [])
        rows.extend(build_entries(
            {"id": case_id, "serial_no": serial_no, "customer": customer, "data": data, "status": case_status}, client_titles, managers, party_records))
    rows.extend(_non_litigation_entries(connection, managers_by_id, party_by_customer))
    _register_missing_parties(connection, rows)
    connection.execute(delete(PartyLibraryEntry))
    for start in range(0, len(rows), 2000):
        connection.execute(insert(PartyLibraryEntry), rows[start:start + 2000])
    return int(connection.scalar(select(func.count()).select_from(PartyLibraryEntry)) or 0)


def _non_litigation_entries(connection, managers_by_id, party_by_customer) -> list[dict]:
    """非诉讼（知识产权）案件：案件关联的当事人表里的主体（多为申请人）是当事人；案件委托人列在“我方当事人”里。"""
    parties = {pid: (number, name) for pid, number, name in connection.execute(select(PartyRecord.id, PartyRecord.party_no, PartyRecord.name)).all()}
    links: dict[int, list[int]] = {}
    for case_record_id, customer_record_id in connection.execute(
            select(IprCaseCustomer.case_record_id, IprCaseCustomer.customer_record_id)
            .order_by(IprCaseCustomer.case_record_id, IprCaseCustomer.sorting_index, IprCaseCustomer.id)).all():
        links.setdefault(case_record_id, []).append(customer_record_id)
    entries: list[dict] = []
    cases = connection.execute(select(
        BusinessRecord.id, BusinessRecord.serial_no, BusinessRecord.customer, BusinessRecord.owner, BusinessRecord.data,
        BusinessRecord.status,
    ).where(BusinessRecord.module == "ipr_case")).all()
    for case_id, serial_no, customer, owner, data, status in cases:
        data = data or {}
        client = str(customer or "").strip()
        try:
            customer_id = int(data.get("customer_id") or 0)
        except (TypeError, ValueError):
            customer_id = 0
        managers = managers_by_id.get(customer_id) or ([owner] if owner else [])
        for linked_id in links.get(case_id, []):
            if linked_id not in party_by_customer:
                continue  # 关联的是客户，不进当事人库
            party_id, number = party_by_customer[linked_id]
            entries.append({
                "party_id": party_id, "party_no": number, "customer_record_id": linked_id, "case_id": case_id, "case_no": serial_no,
                "case_category": NON_LITIGATION, "subject_name": parties[party_id][1], "subject_type": "当事人",
                "subject_position": "申请人", "our_parties": [client] if client else [], "our_position": "",
                "opponent_parties": [], "opponent_position": "", "managers": managers,
                "manager_key": "|" + "|".join(managers) + "|" if managers else "", "case_status": str(status or ""),
            })
    return entries


def upgrade_party_master(connection):
    """当事人表建表并登记；当事人库表结构随之重建（它是由案件生成的派生数据）。"""
    PartyRecord.__table__.create(connection, checkfirst=True)
    PartyLibraryEntry.__table__.drop(connection, checkfirst=True)
    PartyLibraryEntry.__table__.create(connection)
    rebuild_party_library(connection)


def upgrade_party_library(connection):
    """第一版：当事人库建表。当事人表上线后，这一版的内容由 upgrade_party_master 接管重建。"""
    PartyLibraryEntry.__table__.create(connection, checkfirst=True)
