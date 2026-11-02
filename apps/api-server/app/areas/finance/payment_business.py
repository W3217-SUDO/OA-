"""付款管理 6 个页面的诉讼/非诉区分（501099）。

- 带业务类型（identity["_business_type"]）时只出、只办该类型的单据；不带时与原来完全一样。
- 只有非诉财务中心页面的账号写操作不会被页面访问临时提升；“给页面＝功能全有”，
  这里按真实菜单放行，用与页面访问相同的临时管理员身份走原有校验，再限定只办非诉单据。
"""
from fastapi import HTTPException

from app.core.finance_centers import (
    BUSINESS_TYPES, NONLITIGATION, business_types_for_ids, has_nonlitigation_page, nonlitigation_record_type,
    record_business_type,
)

PAYMENT_PAGES = {
    "mine": "ipr-finance-payment-mine",
    "audit": "ipr-finance-payment-audit",
    "print": "ipr-finance-payment-print",
    "package": "ipr-finance-payment-package-manage",
    "query": "ipr-finance-payment-query",
    "writeoff": "ipr-finance-payment-writeoff",
}


async def payment_actor(identity: dict, db, *pages: str) -> dict:
    """非诉页面的人办非诉单：返回与页面访问相同的临时管理员身份；其他情况原样返回。"""
    keys = [PAYMENT_PAGES.get(page, page) for page in pages]
    if not await has_nonlitigation_page(identity, db, *keys):
        return identity
    role_ids = [role for role in identity.get("role_ids") or [] if role != "admin"]
    return {**identity, "role": "admin", "role_ids": ["admin", *role_ids], "_page_menu_capability": True,
            "_nonlitigation_payment_actor": True}


def require_payment_business(record, identity: dict) -> None:
    """单据的业务类型要和当前一致；非诉页面放行的身份只能办非诉单。"""
    business = identity.get("_business_type")
    if identity.get("_nonlitigation_payment_actor"):
        business = NONLITIGATION
    if record is not None and business in BUSINESS_TYPES and record_business_type(record) != business:
        raise HTTPException(409, f"单据不属于当前业务类型（{business}）")


async def filter_payment_business(rows, identity: dict, db, *, id_of=lambda row: row.id):
    """只按业务类型过滤（不看中心）；不带业务类型时原样返回。"""
    rows = list(rows)
    business = identity.get("_business_type")
    if business not in BUSINESS_TYPES:
        return rows
    ids = [id_of(row) for row in rows if str(id_of(row) or "").isdigit()]
    types = await business_types_for_ids(db, ids)
    return [row for row in rows if (types.get(int(id_of(row)), "诉讼") if str(id_of(row) or "").isdigit() else "诉讼") == business]


def tag_nonlitigation(data: dict, *sources) -> dict:
    """来源全是非诉时新记录记 business_type=非诉；否则不写（=诉讼）。"""
    business = nonlitigation_record_type(*sources)
    return {**data, "business_type": business} if business else data
