"""合同草稿修改的共享业务命令；提交由入口负责。"""

from app.core.dependencies import (
    AsyncSession,
    BusinessRecord,
    HTTPException,
    User,
    WorkflowEvent,
    select,
    uuid4,
)
from app.models_shared import ContractDraftInput


async def update_contract_draft_record(
    contract_id: int, body: ContractDraftInput, identity: dict, db: AsyncSession
):
    from app.core.contracts import (
        _contract_customer_source_person,
        _resolve_contract_customer,
    )
    from app.core.formatters import (
        _normalize_external_contract_numbers,
    )
    from app.core.permissions import (
        _ensure_record_module,
        _record_dict_for_identity,
        _require_record_owner_or_manager,
    )

    item = await _ensure_record_module(contract_id, "contract", identity, db)
    await _require_record_owner_or_manager(item, identity, db)
    if item.status not in {"草稿", "已拒绝"}:
        raise HTTPException(
            status_code=409, detail="合同提交审批后不能直接编辑，请使用合同变更流程"
        )
    duplicate = await db.scalar(
        select(BusinessRecord.id).where(
            BusinessRecord.serial_no == body.serial_no.strip(),
            BusinessRecord.id != item.id,
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="合同编号已存在")
    duplicate_title = await db.scalar(
        select(BusinessRecord.id).where(
            BusinessRecord.module == "contract",
            BusinessRecord.title == body.title.strip(),
            BusinessRecord.id != item.id,
            BusinessRecord.status.not_in({"已删除", "已归档"}),
        )
    )
    if duplicate_title:
        raise HTTPException(status_code=409, detail="合同名称已存在，不能保存同名合同")
    data = _normalize_external_contract_numbers(dict(body.data or {}))
    customer = await _resolve_contract_customer(body.customer, data, identity, db)
    customer_data = customer.data or {}
    # 修改草稿时保留已落库的 GUID，忽略请求中的替换值。
    data = {
        **data,
        "contract_guid": str((item.data or {}).get("contract_guid") or uuid4()),
        "customer_id": customer.id,
        "customer_no": customer.serial_no,
        "customer_manager": "、".join(
            customer_data.get("customer_managers") or [customer.owner]
        ),
        "source_person": _contract_customer_source_person(customer),
    }
    if float(data.get("amount") or 0) < 0:
        raise HTTPException(status_code=422, detail="合同金额不能小于零")
    owner = body.owner.strip()
    department = body.department.strip()
    if identity.get("role") != "admin":
        current_user = await db.scalar(
            select(User).where(User.username == identity["username"])
        )
        if not current_user:
            raise HTTPException(status_code=401, detail="当前用户不存在")
        department = current_user.department
        if identity.get("role") == "user":
            owner = identity["username"]
    item.serial_no = body.serial_no.strip()
    item.title = body.title.strip()
    item.customer = customer.title
    item.owner = owner
    item.department = department
    item.description = body.description.strip()
    item.data = data
    db.add(
        WorkflowEvent(
            record_id=item.id,
            action="修改合同草稿",
            from_status=item.status,
            to_status=item.status,
            operator=identity["username"],
            comment="通过合同专用入口修改",
        )
    )
    await db.flush()
    await db.refresh(item)
    return await _record_dict_for_identity(item, identity, db)
