"""新建客户的必填信息核对：智能体提交前先对照，缺什么当场告诉用户，不等保存失败才发现。

只读：不加锁、不写库；规则与新建客户接口和客户证件校验保持一致。
"""
from sqlalchemy import select

from app.core.constants import CUSTOMER_CREATE_STATUSES, CUSTOMER_LEVELS
from app.core.customer_identity import CUSTOMER_ORGANIZATION_TYPES
from app.core.formatters import _normalize_customer_name
from app.models import BusinessRecord, SystemParameter

_IDENTITY_KEYS = ("organization_type", "identity_no", "credit_code", "customer_type", "level")


async def missing_customer_create_fields(body: dict, db) -> list[str]:
    """列出新建客户还缺或不合规的信息；全部满足时返回空列表。"""
    data = dict(body.get("data") or {})
    for key in _IDENTITY_KEYS:
        if body.get(key) is not None:
            data[key] = body[key]
    problems: list[str] = []
    title = str(body.get("title") or "").strip()
    existing = (await db.execute(select(BusinessRecord.title, BusinessRecord.data).where(BusinessRecord.module == "customer"))).all()
    if not _normalize_customer_name(title):
        problems.append("客户名称")
    elif any(_normalize_customer_name(name) == _normalize_customer_name(title) for name, _ in existing):
        problems.append(f"客户名称「{title}」已存在，不能重复创建，请确认是否换一个名称或改用已有客户")
    status = str(body.get("status") or "").strip()
    if status and status not in CUSTOMER_CREATE_STATUSES:
        problems.append("客户状态（可选：" + "、".join(sorted(CUSTOMER_CREATE_STATUSES)) + "，也可不填）")
    customer_type = str(data.get("customer_type") or "客户").strip()
    active_types = set((await db.scalars(select(SystemParameter.name).where(
        SystemParameter.category == "customer_type", SystemParameter.is_active.is_(True)))).all())
    if customer_type not in active_types:
        problems.append("客户类型（可选：" + "、".join(sorted(active_types)) + "）")
    level = str(data.get("level") or "立案客户").strip()
    if level not in CUSTOMER_LEVELS:
        problems.append("客户等级（可选：" + "、".join(sorted(CUSTOMER_LEVELS)) + "，也可不填）")
    organization_type = str(data.get("organization_type") or "").strip()
    if organization_type not in CUSTOMER_ORGANIZATION_TYPES:
        problems.append("组织类型（可选：" + "、".join(sorted(CUSTOMER_ORGANIZATION_TYPES)) + "）")
        return problems  # 没有组织类型就无法判断该填身份证号还是统一社会信用代码
    person = organization_type == "个人"
    field, label = ("identity_no", "身份证号") if person else ("credit_code", "统一社会信用代码")
    value = str(data.get(field) or "").strip().upper()
    if not value:
        problems.append(f"{label}（{organization_type}必填）")
    elif any(ch.isspace() for ch in value):
        problems.append(f"{label}不允许包含空格")
    elif person and (len(value) != 18 or not value[:17].isdigit() or value[-1] not in "0123456789X"):
        problems.append("身份证号格式无效（应为 18 位）")
    elif not person and (len(value) != 18 or not value.isalnum()):
        problems.append("统一社会信用代码格式无效（应为 18 位字母数字）")
    elif any(str((row_data or {}).get(field) or "").strip().upper() == value for _, row_data in existing):
        problems.append(f"{label}已被其他客户使用，请确认是否已有该客户")
    return problems
