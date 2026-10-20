"""案件细阶段统计按旧阶段 ID、费用退费状态和客户管理人归集。"""
from datetime import datetime
import re

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import BusinessRecord, User
from app.security import current_identity
from app.core.permissions import _record_scope_conditions, _require_record_module_menu
from app.core.constants import CASE_EVENT_TIME_ZONE
from app.core.json_relation_query import scalar_in_values
from app.core.record_projection_query import read_record_projections
from app.areas.contract.export_workbooks import render_workbook

router = APIRouter()

# 列号对应模板；提交立案与等待立案以阶段字典为准，修正旧导出错序。
PHASE_COLUMNS = {
    101011: 2, 1010121: 3, 1010131: 4, 101012: 5, 101013: 6,
    1010140: 7, 1020120: 8, 101016: 9, 101017: 9, 102014: 9,
    102015: 9, 103013: 9, 101020: 15, 102017: 16, 104019: 17,
    104011: 18, 104012: 19, 104013: 20, 104014: 21, 104015: 22, 104016: 23,
    104021: 24, 104022: 25,
}
PHASE_LABEL_COLUMNS = {
    "文书准备": 2, "客户盖章": 3, "提交立案": 4, "等待立案": 5,
    "补充取证": 6, "一审阶段": 7, "一审": 7, "二审阶段": 8, "二审": 8, "一审准备开庭": 9,
    "一审再次开庭": 9, "二审通知开庭": 9, "二审再次开庭": 9, "再审通知开庭": 9,
    "一审待执行": 15, "二审待执行": 16, "执行准备材料": 17, "准备材料": 17, "执行立案": 18, "提交法院": 18,
    "执行受理": 19, "执行中止": 20, "执行结案": 21, "执行终本": 22,
    "执行终结": 23, "终结执行": 23, "执行亏损": 24, "执行异议": 25,
}
REFUND_COLUMNS = {10: 10, 20: 11, 30: 12, 35: 13, 40: 14}
# 统计实际读取的字段（与下面的循环保持一致；新增读取字段时必须同步这里）。
CASE_FIELDS = ("assistant_username", "assistant", "case_phase_id", "execution_status", "case_phase_name", "case_stage")
CASE_LEGACY_FIELDS = ("CaseAssistant", "CasePhaseId")
FEE_FIELDS = ("refund_status", "case_record_id", "case_id", "case_no")
FEE_LEGACY_FIELDS = ("RefundStatus",)
CUSTOMER_FIELDS = ("customer_managers",)
CLUE_FIELDS = ("clue_status", "customer_reviewed_at")
CLUE_LEGACY_FIELDS = ("Status",)
REFUND_LABELS = {"准备材料": 10, "客户盖章": 11, "已提交法院": 12, "待法院现场办理": 13, "退费到客户": 14}


def _tokens(value):
    values = value if isinstance(value, list) else re.split(r"[,，、;；\s]+", str(value or ""))
    return {str(item).strip() for item in values if str(item).strip()}


async def stage_statistics_rows(identity, db, *, action="导出"):
    await _require_record_module_menu("case", identity, db, action=action)
    conditions = await _record_scope_conditions(identity, db)
    # 只读统计用到的字段：整条业务记录带着完整历史 JSON，案件/费用/线索合计十几万条，整条读入会让接口超时。
    cases = await read_record_projections(db, [
        BusinessRecord.module == "case", BusinessRecord.status.not_in({"已删除", "已合并"}), *conditions,
    ], CASE_FIELDS, legacy_fields=CASE_LEGACY_FIELDS)
    users = list((await db.scalars(select(User))).all())
    names = {user.username: user.display_name or user.username for user in users}
    usernames = {user.display_name: user.username for user in users if user.display_name}
    rows = {}
    def assistants(case):
        data = case.data or {}
        legacy = data.get("legacy_record") or {}
        values = _tokens(data.get("assistant_username") or data.get("assistant") or legacy.get("CaseAssistant"))
        return {usernames.get(value, value) for value in values}
    by_id = {item.id: item for item in cases}
    by_no = {item.serial_no: item for item in cases}
    for case in cases:
        data = case.data or {}
        legacy = data.get("legacy_record") or {}
        phase_id = data.get("case_phase_id") or legacy.get("CasePhaseId")
        # 新系统直接保存阶段文本时，以当前文本为准，不能使用过期迁移 ID。
        phase = str(data.get("execution_status") or data.get("case_phase_name") or data.get("case_stage") or case.status).strip()
        if data.get("execution_status") == "准备材料":
            phase = "执行准备材料"
        if data.get("execution_status") == "提交法院":
            phase = "执行立案"
        column = PHASE_LABEL_COLUMNS.get(phase)
        if column is None and phase_id:
            column = PHASE_COLUMNS.get(int(phase_id))
        for username in assistants(case):
            values = rows.setdefault(username, [names.get(username, username), str(datetime.now(CASE_EVENT_TIME_ZONE).date()), *([0] * 28)])
            if column is not None:
                values[column] += 1
    fees = await read_record_projections(db, [
        BusinessRecord.module == "finance", BusinessRecord.status != "已删除",
        or_(scalar_in_values(BusinessRecord.data["case_id"].as_integer(), by_id),
            scalar_in_values(BusinessRecord.data["case_record_id"].as_integer(), by_id),
            scalar_in_values(BusinessRecord.data["case_no"].as_string(), by_no)),
    ], FEE_FIELDS, legacy_fields=FEE_LEGACY_FIELDS) if cases else []
    for fee in fees:
        data = fee.data or {}
        legacy = data.get("legacy_record") or {}
        status_value = data.get("refund_status", legacy.get("RefundStatus"))
        column = REFUND_LABELS.get(str(status_value))
        code = str(status_value or "").removeprefix("R")
        if column is None and code.isdigit():
            column = REFUND_COLUMNS.get(int(code))
        case = by_id.get(int(data.get("case_record_id") or data.get("case_id") or 0)) or by_no.get(data.get("case_no"))
        if case and column is not None:
            for username in assistants(case):
                if username in rows:
                    rows[username][column] += 1
    customers = await read_record_projections(db, [BusinessRecord.module == "customer", *conditions], CUSTOMER_FIELDS)
    customer_by_id = {item.id: item for item in customers}
    clues = await read_record_projections(db, [
        BusinessRecord.module == "clue", BusinessRecord.status != "已删除", *conditions,
    ], CLUE_FIELDS, legacy_fields=CLUE_LEGACY_FIELDS)
    from app.core.clue_audit_scope import _customer_relations
    relations, clue_source, customer_source = _customer_relations()
    customer_links = dict((await db.execute(relations.where(
        scalar_in_values(clue_source.id, {clue.id for clue in clues}),
        scalar_in_values(customer_source.id, customer_by_id),
    ))).all()) if clues and customer_by_id else {}
    for clue in clues:
        data = clue.data or {}
        legacy = data.get("legacy_record") or {}
        customer = customer_by_id.get(customer_links.get(clue.id))
        if not customer:
            continue
        status_value = clue.status
        if status_value in {"历史数据", "历史线索"} or str(status_value).isdigit():
            status_value = str(data.get("clue_status") or legacy.get("Status") or status_value)
        columns = {"10": (26,), "20": (27,), "15": (28,), "60": (29,),
                   "待审核": (26,), "待审批": (26,), "已审核": (27,), "待客户审核": (28,), "客户已审核": (29,), "已通过": (27,),
                   "待取证": (29,) if data.get("customer_reviewed_at") else (27,),
                   "已取证": (29,) if data.get("customer_reviewed_at") else (27,)}.get(status_value, ())
        managers = _tokens((customer.data or {}).get("customer_managers") or customer.owner)
        for manager in managers:
            username = usernames.get(manager, manager)
            if username in rows:
                for column in columns:
                    rows[username][column] += 1
    return [{"id": key, "name": rows[key][0], "date": rows[key][1], "values": rows[key][2:]} for key in sorted(rows)]


@router.get(f"{settings.api_prefix}/cases/stage-statistics")
async def list_stage_statistics(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    items = await stage_statistics_rows(identity, db, action="查看")
    return {"items": items, "total": len(items)}


@router.get(f"{settings.api_prefix}/cases/stage-statistics/export")
async def export_stage_statistics(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    rows = await stage_statistics_rows(identity, db)
    return render_workbook("case-stage-statistics", [[row["name"], row["date"], *row["values"]] for row in rows])
