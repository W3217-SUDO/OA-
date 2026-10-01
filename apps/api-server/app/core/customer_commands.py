"""客户资料修改的共享业务命令；提交由入口负责。"""

from app.core.constants import CUSTOMER_CREATE_DATA_FIELDS, FIELD_PERMISSION_DATA_KEYS
from app.core.customer_identity import (
    validate_customer_identity as _validate_customer_identity,
)
from app.core.dependencies import AsyncSession
from app.models_shared import CustomerPatchInput


async def patch_customer_record(
    customer_id: int, body: CustomerPatchInput, identity: dict, db: AsyncSession
):
    from app.core.crm import (
        _customer_event,
        _customer_or_404,
    )
    from app.core.permissions import (
        _record_dict_for_identity,
        _require_record_owner_or_manager,
    )
    from app.core.system import (
        _allowed_field_keys,
    )

    customer = await _customer_or_404(customer_id, identity, db)
    await _require_record_owner_or_manager(customer, identity, db)
    allowed_fields = await _allowed_field_keys(identity, db)
    current = dict(customer.data or {})
    accepted: dict[str, object] = {}
    for key, value in (body.data or {}).items():
        if key not in CUSTOMER_CREATE_DATA_FIELDS:
            continue
        permission = next(
            (
                permission
                for permission, keys in FIELD_PERMISSION_DATA_KEYS.items()
                if key in keys
            ),
            None,
        )
        if permission and permission not in allowed_fields:
            continue
        accepted[key] = value
    next_data = {**current, **accepted}
    if {"organization_type", "identity_no", "credit_code"} & set(accepted):
        await _validate_customer_identity(next_data, db, exclude_id=customer.id)
    customer.data = next_data
    if body.description is not None:
        customer.description = body.description.strip()
    db.add(
        _customer_event(
            customer,
            "更新客户资料",
            identity,
            f"更新字段：{'、'.join(accepted) or '无可写字段'}",
        )
    )
    await db.flush()
    await db.refresh(customer)
    return await _record_dict_for_identity(customer, identity, db)
