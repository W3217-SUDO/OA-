"""按人统计的进度表（报表中心“退费进度案件统计”，BUG 500789，思法汇成 11-01 定）。

每人一行、横向是退费进度，格子是案件数；“人”按案件的律师助理（多人各算一次），
只算未归档案件。退费进度取迁移自旧系统、记在每笔费用上的退费状态。
同一案件有几笔费用处在不同进度时，各进度分别算一次，合计里同一案件只算一次。
"""
import re

from sqlalchemy import select

from app.core.person_names import person_name, refresh_person_names
from app.models import BusinessRecord

REFUND_STAGES = (
    ("10", "准备材料"), ("20", "客户盖章"), ("30", "已提交法院"),
    ("35", "待法院现场办理"), ("40", "退费到客户"), ("50", "回款待分配"),
)
REFUND_STAGE_BY_CODE = dict(REFUND_STAGES)
ARCHIVED_CASE_STATUSES = frozenset({"已归档", "亏损归档"})
UNASSIGNED_PERSON = "未填律师助理"
_PEOPLE_SPLIT = re.compile(r"[、,，;；\s]+")


def _case_id(fee_data: dict) -> int:
    for key in ("case_record_id", "case_id"):
        try:
            value = int(fee_data.get(key) or 0)
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    return 0


def case_assistants(case_data: dict) -> list[str]:
    """律师助理姓名：先用案件上的姓名，没有姓名时用账号换姓名。"""
    names = [item for item in _PEOPLE_SPLIT.split(str(case_data.get("assistant") or "")) if item]
    if not names:
        accounts = case_data.get("assistant_usernames") or case_data.get("assistant_username") or []
        if isinstance(accounts, str):
            accounts = _PEOPLE_SPLIT.split(accounts)
        names = [person_name(item) for item in accounts if str(item or "").strip()]
    return list(dict.fromkeys(names)) or [UNASSIGNED_PERSON]


async def _refund_progress_entries(identity: dict, db) -> list[dict]:
    """可见、未归档案件上处于各退费进度的费用，一笔费用一条。"""
    from app.core.permissions import _record_scope_conditions
    status = BusinessRecord.data["refund_status"]
    # 旧系统迁来的退费状态是数字；PostgreSQL 按文本比较，SQLite（测试库）按数字比较。
    status_filter = (status.as_integer().in_([int(code) for code, _ in REFUND_STAGES]) if db.get_bind().dialect.name == "sqlite"
                     else status.as_string().in_([code for code, _ in REFUND_STAGES]))
    fees = (await db.execute(select(BusinessRecord.id, BusinessRecord.serial_no, BusinessRecord.title, BusinessRecord.data).where(
        BusinessRecord.module == "finance", status_filter,
    ))).all()
    fee_rows = [(fee_id, serial_no, title, data or {}) for fee_id, serial_no, title, data in fees]
    case_ids = {_case_id(data) for *_, data in fee_rows} - {0}
    if not case_ids:
        return []
    cases = {item.id: item for item in (await db.execute(select(
        BusinessRecord.id, BusinessRecord.serial_no, BusinessRecord.customer, BusinessRecord.status, BusinessRecord.data,
    ).where(
        BusinessRecord.module == "case", BusinessRecord.id.in_(case_ids),
        BusinessRecord.status.not_in(ARCHIVED_CASE_STATUSES),
        *(await _record_scope_conditions(identity, db)),
    ))).all()}
    entries = []
    for fee_id, serial_no, title, data in fee_rows:
        case = cases.get(_case_id(data))
        if case is None:
            continue
        code = str(data.get("refund_status") or "")
        entries.append({
            "case_id": case.id, "case_no": case.serial_no, "customer": case.customer, "case_status": case.status,
            "people": case_assistants(case.data or {}),
            "fee_id": fee_id, "fee_no": serial_no, "fee_name": data.get("fee_type_name") or data.get("expense_subtype") or title or "",
            "refund_amount": float(data.get("refund_amount") or data.get("refund_requested_amount") or 0),
            "stage": REFUND_STAGE_BY_CODE[code],
            "stage_started": str(data.get(f"refund_status{code}_start_time") or "")[:10],
        })
    return entries


async def refund_progress_report(identity: dict, db) -> dict:
    await refresh_person_names(db)
    entries = await _refund_progress_entries(identity, db)
    stages = [label for _, label in REFUND_STAGES]
    by_person: dict[str, dict[str, set[int]]] = {}
    by_stage: dict[str, set[int]] = {stage: set() for stage in stages}
    for entry in entries:
        by_stage[entry["stage"]].add(entry["case_id"])
        for person in entry["people"]:
            by_person.setdefault(person, {stage: set() for stage in stages})[entry["stage"]].add(entry["case_id"])
    rows = [{
        "person": person,
        "counts": {stage: len(ids) for stage, ids in counts.items()},
        "total": len(set().union(*counts.values())),
    } for person, counts in by_person.items()]
    # 按合计从多到少，“未填律师助理”放最后。
    rows.sort(key=lambda row: (row["person"] == UNASSIGNED_PERSON, -row["total"], row["person"]))
    return {
        "view": "refund-progress", "person_label": "律师助理", "stages": stages, "rows": rows,
        "totals": {stage: len(ids) for stage, ids in by_stage.items()},
        "total": len(set().union(*by_stage.values())) if by_stage else 0,
        "definition": "统计未归档案件；按案件律师助理统计，多位助理各算一次；同一案件几笔费用在不同进度时各进度分别计，合计里同一案件只算一次。",
        "source": "realtime",
    }


async def refund_progress_cases(identity: dict, db, *, person: str = "", stage: str = "") -> dict:
    """点表格数字时的案件清单：按人、按进度筛（空表示合计）。"""
    await refresh_person_names(db)
    entries = [entry for entry in await _refund_progress_entries(identity, db)
               if (not person or person in entry["people"]) and (not stage or entry["stage"] == stage)]
    entries.sort(key=lambda entry: (entry["case_no"] or "", entry["fee_id"]))
    return {"items": entries, "case_count": len({entry["case_id"] for entry in entries})}
