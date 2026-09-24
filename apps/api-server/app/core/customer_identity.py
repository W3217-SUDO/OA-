import hashlib

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BusinessRecord


CUSTOMER_ORGANIZATION_TYPES = {"公司企业", "事业单位", "机关团体", "个人", "个体工商户", "其他"}


async def validate_customer_identity(data: dict, db: AsyncSession, *, exclude_id: int | None = None) -> None:
    organization_type = str(data.get("organization_type") or "").strip()
    if organization_type not in CUSTOMER_ORGANIZATION_TYPES:
        raise HTTPException(status_code=422, detail="请选择有效的组织类型")
    identity_field = "identity_no" if organization_type == "个人" else "credit_code"
    identity_label = "身份证号" if organization_type == "个人" else "统一社会信用代码"
    identity_value = str(data.get(identity_field) or "").strip().upper()
    if not identity_value:
        raise HTTPException(status_code=422, detail=f"{identity_label}不能为空")
    if any(character.isspace() for character in identity_value):
        raise HTTPException(status_code=422, detail=f"{identity_label}不允许包含空格")
    if organization_type == "个人":
        if len(identity_value) != 18 or not identity_value[:17].isdigit() or identity_value[-1] not in "0123456789X":
            raise HTTPException(status_code=422, detail="身份证号格式无效")
        data["credit_code"] = ""
    else:
        if len(identity_value) != 18 or not identity_value.isalnum():
            raise HTTPException(status_code=422, detail="统一社会信用代码格式无效")
        data["identity_no"] = ""
    data["organization_type"] = organization_type
    data[identity_field] = identity_value
    bind = db.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        lock_key = int.from_bytes(hashlib.sha256(f"customer:{identity_field}:{identity_value}".encode("utf-8")).digest()[:8], "big", signed=True)
        await db.execute(text("SELECT pg_advisory_xact_lock(:lock_key)"), {"lock_key": lock_key})
    existing = list((await db.scalars(
        select(BusinessRecord).where(BusinessRecord.module == "customer").with_for_update()
    )).all())
    for customer in existing:
        if exclude_id and customer.id == exclude_id:
            continue
        customer_data = customer.data or {}
        if str(customer_data.get(identity_field) or "").strip().upper() == identity_value:
            raise HTTPException(status_code=409, detail=f"{identity_label}已被其他客户使用")
