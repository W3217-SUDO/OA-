"""从案件数据推出当事人库：我方/对方、诉讼地位、客户与当事人分类。"""
import re
import unicodedata

from sqlalchemy import delete, func, insert, select

from app.data_models.party_library import PartyLibraryEntry
from app.data_models.records import BusinessRecord

MIGRATION_REVISION = "party_library_v1"
_SPLIT = re.compile(r"[,，、;；\n]+")
_PLAINTIFF = "原告"
_DEFENDANT = "被告"
_THIRD = "第三人"


CASE_CATEGORIES = ("民事", "行政", "刑事", "仲裁", "法律顾问")


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
    manager_key = "|" + "|".join(managers) + "|" if managers else ""
    layout = case_party_layout(case)
    client = str(case.get("customer") or "").strip()
    category = case_category((case.get("data") or {}).get("case_type"))
    label = (lambda position: ARBITRATION_POSITIONS.get(position, position)) if category == "仲裁" else (lambda position: position)
    entries = []
    for name in [*layout["ours"], *layout["theirs"], *layout["others"]]:
        if name == client or name in client_titles:
            continue  # 客户不进当事人库，只作为“我方当事人”出现在行里
        record = (party_records or {}).get(_normalize(name))
        entries.append({
            "party_no": record[1] if record else "", "customer_record_id": record[0] if record else None,
            "case_id": case["id"], "case_no": case["serial_no"], "subject_name": name,
            "case_category": category,
            "subject_type": "当事人",
            "subject_position": label(layout["positions"].get(name, "")),
            "our_parties": layout["ours"], "our_position": label(layout["our_position"]),
            "opponent_parties": layout["theirs"], "opponent_position": label(layout["their_position"]),
            "managers": managers, "manager_key": manager_key, "case_status": str(case.get("status") or ""),
        })
    return entries


def rebuild_party_library(connection) -> int:
    """按案件重建整张表；案件和客户数据不改动。"""
    customers = connection.execute(select(
        BusinessRecord.id, BusinessRecord.title, BusinessRecord.owner, BusinessRecord.data, BusinessRecord.serial_no,
    ).where(BusinessRecord.module == "customer", BusinessRecord.status != "已回收").order_by(BusinessRecord.id)).all()
    client_titles = {title.strip() for _, title, _, data, _ in customers if (data or {}).get("customer_type", "客户") == "客户" and title}
    # 当事人沿用档案里的编号：从客户挪来的是原客户编号，新建的是 DSR 编号；同名取最早的一条。
    party_records: dict[str, tuple[int, str]] = {}
    for record_id, title, _, data, record_serial in customers:
        if (data or {}).get("customer_type", "客户") != "客户" and _normalize(title):
            party_records.setdefault(_normalize(title), (record_id, record_serial))
    managers_by_id = {}
    for record_id, _, owner, data, _ in customers:
        managers = (data or {}).get("customer_managers") or ([owner] if owner else [])
        managers_by_id[record_id] = [str(item) for item in (managers if isinstance(managers, list) else [managers]) if item]
    connection.execute(delete(PartyLibraryEntry))
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
        if len(rows) >= 2000:
            connection.execute(insert(PartyLibraryEntry), rows)
            rows = []
    if rows:
        connection.execute(insert(PartyLibraryEntry), rows)
    return int(connection.scalar(select(func.count()).select_from(PartyLibraryEntry)) or 0)


def upgrade_party_library(connection):
    PartyLibraryEntry.__table__.create(connection, checkfirst=True)
    rebuild_party_library(connection)


_ROLE_BY_POSITION = {"申请人": _PLAINTIFF, "被申请人": _DEFENDANT}


async def register_unnumbered_parties(db, identity: dict) -> dict:
    """给案件里出现过、但没有档案的当事人建档并发放 DSR 当事人编号，然后重建当事人库。

    只新增“当事人”类型的档案；已有档案（含沿用客户编号的）和案件数据都不改。
    """
    from uuid import uuid4
    from datetime import date

    from app.core.crm import _mark_customer_modified, _next_party_serial_no
    from app.core.legacy_sync import _sync_legacy_projection
    from app.data_models.records import WorkflowEvent

    pending = (await db.execute(
        select(PartyLibraryEntry.subject_name, PartyLibraryEntry.case_id, PartyLibraryEntry.case_no,
               PartyLibraryEntry.subject_position, PartyLibraryEntry.managers)
        .where(PartyLibraryEntry.party_no == "").order_by(PartyLibraryEntry.id)
    )).all()
    first_seen: dict[str, tuple] = {}
    for name, case_id, case_no, position, managers in pending:
        first_seen.setdefault(_normalize(name), (name, case_id, case_no, position, managers))
    existing = {_normalize(title) for (title,) in (await db.execute(
        select(BusinessRecord.title).where(BusinessRecord.module == "customer"))).all()}
    created = 0
    for normalized, (name, case_id, case_no, position, managers) in first_seen.items():
        if not normalized or normalized in existing:
            continue
        role = _ROLE_BY_POSITION.get(position, position) or _DEFENDANT
        owner = (managers or [identity["username"]])[0]
        party = BusinessRecord(
            module="customer", serial_no=await _next_party_serial_no(db), title=name, customer=name,
            status="潜在", owner=owner,
            description=f"由案件 {case_no} 当事人信息补发当事人编号",
            data={
                "customer_type": "当事人", "level": "潜在客户", "customer_managers": list(managers or [owner]),
                "shared_with": [], "is_shared": "否", "is_assisted": "否", "fee_reduction": "否",
                "customer_guid": str(uuid4()), "customer_source": "案件当事人",
                "file_date": date.today().isoformat(), "contact_accounts": [], "contact": "",
                "case_litigant_origin": {"case_id": case_id, "case_no": case_no, "roles": [role]},
            },
        )
        _mark_customer_modified(party, identity)
        db.add(party)
        await db.flush()
        db.add(WorkflowEvent(record_id=party.id, action="创建当事人", to_status=party.status, operator=identity["username"],
                             comment=f"补发当事人编号：案件 {case_no}（{role}）"))
        await _sync_legacy_projection(party, identity, db)
        existing.add(normalized)
        created += 1
    await db.flush()
    total = await db.run_sync(lambda session: rebuild_party_library(session.connection()))
    return {"created": created, "entries": total}
