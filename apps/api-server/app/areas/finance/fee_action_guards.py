"""按独立业务职责组织的路由，注册顺序与端点行为保持稳定。"""
from app.core.dependencies import (
    AsyncSession,
    BusinessRecord,
    HTTPException,
)
from app.core.finance_batch_parity import (
    is_internal_fee,
)

def _is_internal_application(item: BusinessRecord) -> bool:
    data = item.data or {}
    return is_internal_fee(data) and bool(
        str(data.get("payment_application_no") or "").strip()
        or str(data.get("applicant") or "").strip()
    )


def _require_non_internal_application_action(item: BusinessRecord) -> None:
    if _is_internal_application(item):
        raise HTTPException(409, "内部请款单请使用整单审批或申请人操作入口")


async def _require_linked_case_fee_action(item: BusinessRecord, action_key: str, identity: dict, db: AsyncSession) -> None:
    """对案件费用的每个写动作应用角色动作权限。"""
    data = item.data or {}
    case_id = int(data.get("case_id") or data.get("case_record_id") or 0)
    if not case_id:
        return
    case_record = await db.get(BusinessRecord, case_id)
    if not case_record or case_record.module != "case":
        raise HTTPException(status_code=409, detail="案件费用关联的案件不存在")
    from app.core.cases import _case_action_granted
    if not await _case_action_granted(identity, db, action_key):
        raise HTTPException(status_code=403, detail="当前账号没有该案件费用操作权限")
