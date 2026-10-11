"""控制台官费应收的保守补读筛选，不改合同匹配或金额计算。"""
import re

from sqlalchemy import func, or_

from app.core.constants import _OFFICIAL_RECEIVABLE_FEE_WORDS
from app.models import BusinessRecord


def dashboard_receivable_supplement_condition(data):
    """只排除确定不贡献官费、且不可能显式绑定对象的已删除费用。"""
    pattern = "|".join(re.escape(word) for word in _OFFICIAL_RECEIVABLE_FEE_WORDS)
    names = ("fee_type", "fee_type_name", "case_fee_type_name", "expense_subtype")
    # 对象绑定可绕过费用类型；未知类型不能依据字符串转换猜测为非官费。
    return or_(
        BusinessRecord.status.is_distinct_from("已删除"),
        data["contract_object_id"].as_string().is_not(None),
        BusinessRecord.title.regexp_match(pattern),
        *(or_(func.json_typeof(data[key]).not_in(("string", "null")),
              data[key].as_string().regexp_match(pattern)) for key in names),
    )
