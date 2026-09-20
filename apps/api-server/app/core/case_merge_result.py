"""将两个案件归入一个新案号，原案只保留来源与追溯关系。"""
from copy import deepcopy
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.models import BusinessRecord, WorkflowEvent
from app.core.cases import _next_case_serial
from app.core.case_merge import merge_case_relations, move_case_finance_files


async def create_merged_case(primary, secondary, identity, comment, db):
    data = deepcopy(primary.data or {})
    # 来源快照由迁移函数完整保存，不能预先放入而跳过关联迁移。
    data.pop("merged_sources", None)
    case_type = str(data.get("case_type") or "").strip()
    result = BusinessRecord(
        module="case", serial_no=await _next_case_serial(case_type, db),
        title=primary.title, customer=primary.customer, status=primary.status,
        owner=primary.owner, department=primary.department, description=primary.description,
        data=data,
    )
    db.add(result)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise HTTPException(409, "新案件编号生成冲突，请重新提交合并") from exc

    # 已并入主案的来源已经包含在主案快照中，不重复复制其日志或费用。
    cases = [primary] if secondary.status == "已合并" else [primary, secondary]
    counts = [0, 0, 0]
    for case in cases:
        await merge_case_relations(case, result, db)
        moved = await move_case_finance_files(case, result, identity, db)
        counts = [left + right for left, right in zip(counts, moved)]
    for case in (primary, secondary):
        previous = case.status
        case.status = "已合并"
        case.data = {**(case.data or {}), "merged_into_case_id": result.id,
                     "merged_into_case_no": result.serial_no,
                     "merged_at": datetime.now().isoformat(timespec="seconds"),
                     "merged_by": identity["username"], "merge_comment": comment}
        db.add(WorkflowEvent(record_id=case.id, action="案件已合并", from_status=previous,
            to_status=case.status, operator=identity["username"],
            comment=f"合并生成新案号：{result.serial_no}。{comment}"))
    db.add(WorkflowEvent(record_id=result.id, action="合并生成案件", to_status=result.status,
        operator=identity["username"],
        comment=f"来源案件：{primary.serial_no}、{secondary.serial_no}。{comment}"))
    return result, counts
