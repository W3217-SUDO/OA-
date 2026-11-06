"""“本人的客户”查询。多个条件写 OR 时规划器只能逐行解析全部客户 JSON（约 1 秒）；拆成 UNION 各走索引，结果相同。"""
import json

from sqlalchemy import func, literal_column, or_, select, union

from app.models import BusinessRecord


async def person_customer_rows(db, username, *, contact_accounts=False):
    """本人是负责人、客户管理人、协作人（contact_accounts=True 时含客户账号）的客户：id、serial_no。"""
    data = BusinessRecord.data
    token = json.dumps(username, ensure_ascii=False)
    contact_token = json.dumps(str(username).lower(), ensure_ascii=False)
    columns = (BusinessRecord.id, BusinessRecord.serial_no)
    base = BusinessRecord.module == "customer"
    if db.get_bind().dialect.name != "postgresql":
        arms = [BusinessRecord.owner == username,
                data["customer_managers"].as_string().contains(token, autoescape=True),
                data["coordinators"].as_string().contains(token, autoescape=True)]
        if contact_accounts:
            arms.append(func.lower(func.coalesce(data["contact_accounts"].as_string(), "")).contains(contact_token, autoescape=True))
        return (await db.execute(select(*columns).where(base, or_(*arms)))).all()
    arms = [BusinessRecord.owner == username,
            data["customer_managers"].as_string().contains(token, autoescape=True),
            data["coordinators"].as_string().contains(token, autoescape=True)]
    if contact_accounts:
        arms.append(func.lower(func.coalesce(data["contact_accounts"].as_string(), literal_column("''"))).contains(
            contact_token, autoescape=True))
    statement = union(*(select(*columns).where(base, BusinessRecord.deleted_at.is_(None), arm) for arm in arms))
    return (await db.execute(statement)).all()
