"""501634（tgn 11-05 07:22）：案件智能体确认窗口标题只写这次动了哪一块，例如“修改/编辑确认：修改诉讼标的”。

区块名按案件详情：诉讼标的、判决/调解金额、案件基本信息、法院信息、当事人、经办律师信息、开庭律师、案件阶段、执行状态等；
没动的区块不写。认不出的接口返回空列表，前端改用操作名称。
"""
from __future__ import annotations

BASIC_TOOLS = frozenset({"oa_update_normal_case_basic_put", "oa_update_counsel_case_basic_put", "oa_update_arbitration_case_basic_put"})
TOOL_SECTIONS = {
    "oa_update_case_litigants_put": "当事人", "oa_maintain_criminal_litigants_put": "当事人",
    "oa_update_case_court_info_put": "法院信息", "oa_maintain_criminal_courts_put": "法院信息",
    "oa_update_case_hearing_lawyer_put": "开庭律师", "oa_update_case_phase_post": "案件阶段",
    "oa_update_case_execution_status_post": "执行状态", "oa_update_case_notary_info_put": "公证信息",
    "oa_maintain_criminal_procuratorates_put": "检察院信息", "oa_maintain_criminal_public_security_put": "公安信息",
}
AMOUNT_SECTIONS = {"litigation_amount": "诉讼标的", "settlement_amount": "判决/调解金额", "judgment_amount": "判决/调解金额"}
LAWYER_FIELDS = frozenset({"handling_lawyers", "handling_lawyer", "lawyer", "lawyers", "responsible_lawyer", "assistant", "assistants"})


def _same(a, b) -> bool:
    empty = lambda value: value in (None, "", [], {})  # noqa: E731
    return (empty(a) and empty(b)) or a == b


def changed_fields(changes: list[dict]) -> list[str]:
    """真正要改的字段：读到原值且和新值一样的不算。"""
    return [change["field"] for change in changes or []
            if not (change.get("before_read") is True and _same(change.get("before"), change.get("after")))]


def confirm_sections(tool_name: str, changes: list[dict]) -> list[str]:
    fields = changed_fields(changes)
    if tool_name == "oa_update_case_settlement_amount_put":
        return list(dict.fromkeys(AMOUNT_SECTIONS[field] for field in fields if field in AMOUNT_SECTIONS))
    if tool_name in BASIC_TOOLS:
        lawyer = any(field in LAWYER_FIELDS for field in fields)
        other = any(field not in LAWYER_FIELDS for field in fields)
        return (["案件基本信息"] if other or not lawyer else []) + (["经办律师信息"] if lawyer else [])
    section = TOOL_SECTIONS.get(tool_name)
    return [section] if section else []
