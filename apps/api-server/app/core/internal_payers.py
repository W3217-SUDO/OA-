"""内部公司之间的转款（BUG 500784，思法汇成 11-01）：付款方是我们自己几家公司的到账单，
是客户已付款项在律所、平台账户之间的划转，不是客户又付了一笔钱。统计“客户收入”“实际到账”时不计入；
回款管理、到账查询按中心记账照常显示。"""
from sqlalchemy import and_, func

# 按名称关键字匹配，旧系统付款方名称常带尾随空格。
INTERNAL_PAYER_KEYWORDS = ("沪知律师事务所", "恒达知识产权代理", "国定律师事务所")


def is_internal_payer(name) -> bool:
    text = str(name or "")
    return any(keyword in text for keyword in INTERNAL_PAYER_KEYWORDS)


def not_internal_payer(column):
    value = func.coalesce(column, "")
    return and_(*(~value.contains(keyword) for keyword in INTERNAL_PAYER_KEYWORDS))
