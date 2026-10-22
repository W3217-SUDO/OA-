"""需要网页确认的写入：执行后影响已发生在系统之外（审批结论及其下游流程、盖章与对外转交、付款核销、开具或作废发票），
恢复数据也撤不回，所以智能体和 MCP 调用这些接口时仍生成待确认请求，须用户在 OA 网页确认后才执行。其余写入直接执行，靠变更留痕兜底。"""

import re

from app.config import settings

_RULES = (
    ("审批", re.compile(r"/(review|approve|decision|batch-review|exception-review|customer-review)$")),
    ("盖章与对外转交", re.compile(r"^/seals/applications/(\{record_id\}/stamp|batch-stamp)$|^/official-outgoing/mark-stamped$"
                                r"|^/ipr/official-files/\{official_id\}/transmit$")),
    ("付款与核销", re.compile(r"/(pay|writeoff)$|^/finance/general-settlements/applications/payment$")),
    ("开票与作废", re.compile(r"^/finance/invoices/\{invoice_id\}/(issue|void)$")),
)


def irreversible_category(spec) -> str | None:
    """写入接口属于哪一类不可撤回操作；普通写入返回 None。"""
    if not spec.is_write:
        return None
    path = spec.path.removeprefix(settings.api_prefix)
    for category, pattern in _RULES:
        if pattern.search(path):
            return category
    return None
