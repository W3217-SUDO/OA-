"""费用草稿的只读准备，复用于原写入口和智能体确认预检。"""

from fastapi import HTTPException
from sqlalchemy import select

from app.core.constants import EXPENSE_SCOPE_FEE_TYPES, FINANCE_FEE_TYPES
from app.core.finance import (
    _case_fee_type_snapshot, _finance_fee_commission_payload, _finance_linked_case,
    _resolve_case_fee_contract, _resolve_case_fee_type_master, _round_fee_amount,
)
from app.core.permissions import (
    _case_detail_action_capabilities, _ensure_record_visible, _validate_finance_fee_scope_subtype,
)
from app.models import BusinessRecord, User


async def prepare_finance_fee_draft(body, identity, db):
    if body.amount == 0:
        raise HTTPException(422, "费用金额不能为 0")
    case_record = await _finance_linked_case(body.case_no, identity, db)
    if body.case_record_id:
        linked_case = await _ensure_record_visible(body.case_record_id, identity, db)
        if linked_case.module != "case":
            raise HTTPException(422, "关联记录不是案件")
        if case_record and case_record.id != linked_case.id:
            raise HTTPException(409, "案件编号与案件记录不一致")
        case_record = linked_case
    fee_snapshot = {
        "fee_type_id": None, "fee_type_code": "",
        "fee_type_name": body.expense_subtype or body.fee_type,
        "fee_type_path": body.expense_subtype or body.fee_type,
        "fee_type": body.fee_type, "expense_subtype": body.expense_subtype or "",
    }
    if case_record or body.fee_type_id:
        fee_parameter, fee_option = await _resolve_case_fee_type_master(
            body.fee_type_id, body.expense_scope, db,
            legacy_name=body.expense_subtype or "", legacy_base=body.fee_type,
        )
        fee_snapshot = _case_fee_type_snapshot(fee_parameter, fee_option)
        if body.fee_type != fee_snapshot["fee_type"]:
            raise HTTPException(422, "费用类型与系统费用分类不一致")
        if body.expense_subtype and body.expense_subtype != fee_parameter.name:
            raise HTTPException(422, "费用子类型与系统费用分类不一致")
    else:
        if body.fee_type not in FINANCE_FEE_TYPES:
            raise HTTPException(422, "费用类型无效")
        if body.expense_scope and body.fee_type not in EXPENSE_SCOPE_FEE_TYPES[body.expense_scope]:
            raise HTTPException(422, "费用归属与费用类型不一致")
        _validate_finance_fee_scope_subtype(body.expense_scope, body.expense_subtype, body.fee_type)
    if body.amount < 0 and fee_snapshot["fee_type"] != "内部费用":
        raise HTTPException(422, "只有内部费用可以使用负数冲销")
    if case_record and not (await _case_detail_action_capabilities(case_record, identity, db))["can_create_finance"]:
        raise HTTPException(403, "当前账号没有新增案件费用权限")
    contract_record = None
    if body.contract_record_id:
        contract_record = await db.get(BusinessRecord, body.contract_record_id) if case_record else await _ensure_record_visible(body.contract_record_id, identity, db)
        if not contract_record:
            raise HTTPException(404, "关联合同不存在")
        if contract_record.module != "contract":
            raise HTTPException(422, "关联记录不是合同")
        if case_record and contract_record.customer != case_record.customer:
            raise HTTPException(409, "关联合同必须属于当前案件客户")
    contract_record = await _resolve_case_fee_contract(case_record, contract_record, body.expense_scope, identity, db)
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    if not user:
        raise HTTPException(401, "当前用户不存在")
    handler = identity["username"] if identity.get("role") == "user" else body.handler
    amount = _round_fee_amount(body.amount)
    commission = await _finance_fee_commission_payload(body, amount, db, case_record=case_record)
    return case_record, fee_snapshot, contract_record, user, handler, amount, commission
