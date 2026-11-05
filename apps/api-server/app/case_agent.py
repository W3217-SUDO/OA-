from __future__ import annotations

import asyncio
import hashlib
import json
import re
from app.case_quick_checks import QUICK_COMMAND_RULES
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any, AsyncIterator, Callable, TypedDict
from uuid import uuid4

from .harness_agent.case_state import CaseStateStore
from .harness_agent.runtime import readiness

from .agent_skills import SKILLS_BY_ID, AgentSkill, split_skill_message
from .system_agent_skills import runtime_system_skill


ALLOWED_ACTION_TYPES = {
    "case.update",
    "case.data.update",
    "case.task.create",
    "case.reminder.create",
    "customer.update",
    "contract.update",
    "case.delete",
    "customer.delete",
    "contract.delete",
}
ACTION_CAPABILITY_BY_TYPE = {
    "case.update": "can_edit_basic",
    "case.data.update": "can_edit_basic",
    "case.task.create": "can_create_case_task",
    "case.reminder.create": "can_create_reminder",
    "customer.update": "can_update_customer",
    "contract.update": "can_update_contract",
    "case.delete": "can_delete_case",
    "customer.delete": "can_update_customer",
    "contract.delete": "can_update_contract",
}
ACTION_BLOCK_PATTERN = re.compile(r"<proposed_action>\s*(\{.*?\})\s*</proposed_action>", re.DOTALL)

RESPONSE_STYLE_RULES = (
    "先区分操作请求和分析请求。新增、修改、查询等操作请求要自然简短，直接推进用户要做的事，"
    "不必输出‘重点结论’、‘已确认事实’或风险简报；只询问真实接口所需且当前尚未提供的信息。"
    "用户要求分析、总结或简报时，再写成供律师和管理人员直接阅读的工作简报，"
    "先给出‘重点结论’，用两到四句话说明最重要的判断和下一步，不要写成数据库字段导出。"
    "之后只选择与问题相关的事实、风险和行动，不要机械输出所有栏目，也不要重复同一信息。"
    "风险最多列五项并按紧急程度排序；行动建议尽量写清谁处理、做什么、何时完成。"
    "必须区分已确认事实、合理判断和缺失信息，不能把推测写成事实。"
    "面向用户的回复不得展示接口、工具、path、query、body、files、inputSchema、参数分组或英文字段名；"
    "不要逐项复述技术参数。只用前端中文字段名称说明需要用户确认的信息，能直接确认时只给出简短的中文确认问题。"
    "使用短段落和编号清单，语气自然、直接、专业，避免空泛套话。"
    "不要输出 Markdown 标记字符，包括井号、星号、双星号和分隔线；直接输出标题和正文。"
)

DOCUMENT_READING_RULES = (
    "案件空间中的 document_readings 是系统在当前用户权限范围内实际解析的附件内容。"
    "status 为 parsed 时必须阅读 content；status 为 visual 时必须结合随本次消息提供的附件视觉页阅读。"
    "引用附件事实时注明文件名和页码；只有 status 为 unsupported、parse_failed 或内容确实为空时，才说明无法读取。"
    "不得在 document_readings 已有正文或视觉页时回答‘只看到了附件清单’。"
)

# 501289（陶国南 11-03 21:56）：改案件信息只看案件基本信息，不先读文档，更快。
CASE_INFO_EDIT_RULES = (
    "修改、编辑或新建案件信息时（基本信息、开庭律师、当事人信息、法院信息、公证信息、诉讼/判决金额、变更阶段、提醒、案件事件、"
    "内部费用、案件费用等），只依据上面的当前案件空间数据（案件基本信息）和对应的修改接口；"
    "不要读取案件文档、文书、附件或 AI 空间文件，也不要为此再查询整个案件空间或搜索文档类工具。"
    "只有用户明确要求按某份文件内容填写时，才读取那一份文件。"
    # 陶国南 11-05 07:44：所有请求默认只带案件基本信息。
    "所有请求默认只提供案件基本信息和系统案件检查结果，不提供整个案件空间；问题点到费用、文档、任务、期限、合同、客户、线索时，会一并附上那一部分，直接据此回答，不要再搜索工具；需要费用、合同、文档、任务、线索、期限等时，"
    "按需调用对应查询工具（案件费用、附件、任务、办案指引用 biz_case_overview，调用一次就直接据此回答，不要再搜索其他工具），只查回答本问题需要的部分；"
    "只有用户明确说“查全部案件空间”“看整个案件”时，才会提供全部资料。"
    # 陶国南 11-05：常改项一次出确认卡片，不在 25 组里逐个搜功能。
    "判决/调解金额、诉讼标的、法院信息（法院、案号、法庭、法官、书记员、立案/开庭/判决日期、判决文书号）、开庭律师、案件阶段，"
    "直接调用 biz_case_update_info（case_id 用当前案件 ID），第一次就带 confirm=true，直接生成确认卡片（卡片写明每项从多少改成多少），"
    "用户点批准才执行；不要先给文字计划、不要等用户回复“确认”，卡片就是确认；回复里一句话说明已生成卡片、请在卡片上批准即可；"
    "不要为这些项目调用 oa_list_tool_groups 或 oa_search_tools。"
    "一句话要改几块（例如同时加开庭律师和经办律师：开庭律师走 biz_case_update_info，经办律师走基本信息）时，同一轮把每一块的确认卡片都生成出来，"
    "回复里一句话说明共几项、在确认窗口里一起批准，不要只做其中一块（501634）。"
    + "\n" + "案件信息字段对照（陶国南 11-05：听到哪项就知道是案件详情哪个区块、哪个字段，直接办，不到处找）：" + "\n" + "{CASE_FIELD_MAP}"
)

# 用户说法 → 区块 → 字段 → 怎么改。不在 biz_case_update_info 里的区块，用 oa_search_tools 在给出的组里按工具名搜一次（组已预先开放），再 oa_call_tool。
CASE_FIELD_MAP_ROWS = (
    ("判决金额、调解金额、判决调解金额", "诉讼/判决金额", "判决/调解金额", "biz_case_update_info.judgment_amount"),
    ("诉讼标的、标的额、起诉金额", "诉讼/判决金额", "诉讼标的", "biz_case_update_info.litigation_amount"),
    ("一审法院、受理法院、法院案号、一审案号、法庭、法官、承办法官、书记员、立案日期、开庭时间、开庭日期、判决日期、判决书文号",
     "法院信息（一审）", "法院名称、案号、法庭、法官、书记员、立案日期、开庭日期时间、判决日期、判决文书号", "biz_case_update_info.court（level=first）"),
    ("二审法院、二审案号、上诉法院", "法院信息（二审）", "同上各项", "biz_case_update_info.court（level=second）"),
    ("执行法院、执行案号", "法院信息（执行）", "同上各项", "biz_case_update_info.court（level=execution）"),
    ("再审法院、再审案号", "法院信息（再审）", "同上各项", "biz_case_update_info.court（level=retrial）"),
    ("开庭律师、出庭律师", "开庭律师", "开庭律师（可多人）", "biz_case_update_info.hearing_lawyers"),
    ("案件阶段、阶段、进展到哪", "案件阶段", "案件阶段", "biz_case_update_info.case_phase_name"),
    ("执行状态", "执行状态", "执行状态", "biz_case_update_info.execution_status"),
    ("案件名称、案由、罪名、经办律师、承办律师、律师助理、文书、案源人、调查员、权利类型（民事、知产、行政等案件）",
     "基本信息", "案件名称、案由、经办律师、律师助理、案源人、调查员、调查辅助员、权利类型、案件阶段", "组 07 搜 oa_update_normal_case_basic_put（先读案件基本信息，没改的项照原值一起提交）"),
    ("法律顾问案件的顾问类型、顾问期限、案件名称、经办律师", "基本信息（法律顾问）", "案件名称、顾问类型、顾问起止日期、经办律师、律师助理、案由", "组 07 搜 oa_update_counsel_case_basic_put"),
    ("仲裁案件的名称、案由、经办律师", "基本信息（仲裁）", "案件名称、案由、经办律师、律师助理、调查员", "组 07 搜 oa_update_arbitration_case_basic_put"),
    ("原告、被告、第三人、申请人、被申请人、当事人、代理人、对方当事人", "当事人信息",
     "原告/被告/第三人名单、各自证件（组织类型、证件号）、代理人", "组 07 搜 oa_update_case_litigants_put（整份名单提交：先读现有名单，只改用户说的那一方）"),
    ("刑事案件的犯罪嫌疑人、被害人", "当事人信息（刑事）", "刑事当事人", "组 07 搜 oa_maintain_criminal_litigants_put"),
    ("公安机关、侦查机关", "公安信息（刑事）", "公安机关名称、案号、地址、电话、承办人", "组 07 搜 oa_maintain_criminal_public_security_put"),
    ("检察院、审查起诉", "检察院信息（刑事）", "一审/二审/再审检察院名称、案号、地址、电话、承办人", "组 07 搜 oa_maintain_criminal_procuratorates_put"),
    ("刑事案件的法院", "法院信息（刑事）", "一审/二审/执行/再审法院各项", "组 07 搜 oa_maintain_criminal_courts_put"),
    ("公证书号、公证信息、证物仓库位置", "公证信息", "公证书号、仓库库位", "组 14 搜 oa_update_case_notary_info_put（整份提交：先读现有公证书号和库位）"),
    ("提醒、到期提醒", "案件提醒", "提醒日期、截止日期、内容", "组 07 搜 oa_create_case_reminder_post"),
    ("案件事件、案件流水、记一件事", "案件事件", "事件类型、时间、内容、截止日期、是否提醒", "组 07 搜 oa_create_case_event_post（修改已有事件搜 oa_update_case_event_patch）"),
    ("案件日志、写日志", "案件日志", "日志内容", "组 07 搜 oa_create_case_log_post"),
    ("案件费用、内部费用、律师费、诉讼费", "费用", "费用范围、类型、金额、经办人等", "biz_case_fee_create_and_request_payment"),
)
# 501640（tgn 11-06）：页面“操作”菜单合并成 7 组，对照里写上每个区块在哪一组，智能体和用户说的是同一个入口。
CASE_MENU_GROUPS = (
    ("诉讼/判决金额", "修改基本信息 › 诉讼或判决金额"), ("案件阶段", "修改基本信息 › 案件阶段"), ("基本信息", "修改基本信息 › 基本信息"),
    ("开庭律师", "修改诉讼参与人 › 开庭律师"), ("当事人信息", "修改诉讼参与人 › 当事人"),
    ("法院信息", "修改法院和公证信息"), ("公证信息", "修改法院和公证信息 › 公证信息"),
    ("公安信息", "修改法院信息 › 公安信息"), ("检察院信息", "修改法院信息 › 检察院信息"),
)


def case_menu_group(block: str) -> str:
    for prefix, group in CASE_MENU_GROUPS:
        if block.startswith(prefix):
            return group
    return ""


CASE_FIELD_MAP = "\n".join(
    f"- {said} → {block} › {fields} → {how}" + (f"（页面“操作”：{group}）" if (group := case_menu_group(block)) else "")
    for said, block, fields, how in CASE_FIELD_MAP_ROWS)
CASE_INFO_EDIT_RULES = CASE_INFO_EDIT_RULES.replace("{CASE_FIELD_MAP}", CASE_FIELD_MAP)

# 陶国南 11-05：改、填案件信息时不带整个案件空间（费用、文档、任务、线索、检查等），只带案件基本信息，省时间也省费用。
_EDIT_VERBS = re.compile(r"(改|修改|填|填写|录入|更新|设为|设置为|变更|调整|补上|补填|写上|换成)")
_EDIT_FIELDS = re.compile(r"(判决金额|调解金额|诉讼标的|标的额|标的|金额|法院|案号|法庭|法官|书记员|开庭律师|出庭律师|开庭时间|开庭日期|立案日期|判决日期|"
                          r"判决文书|阶段|当事人|原告|被告|第三人|申请人|代理人|案由|罪名|提醒|案件事件|案件流水|案件日志|公证|仓库|库位|基本信息|案件名称|"
                          r"经办律师|承办律师|律师助理|案源人|调查员|执行状态|顾问期限|顾问类型|公安|检察院|犯罪嫌疑人|被害人)")


def is_case_info_edit_request(message: str) -> bool:
    """用户这一句是不是在改、填案件信息（要读文书、做分析的不算）。"""
    text = str(message or "")
    if len(text) > 200 or re.search(r"(分析|总结|归纳|起草|生成|审阅|读取|文书内容|根据.{0,6}(文件|附件|判决书|文书))", text):
        return False
    return bool(_EDIT_VERBS.search(text) and _EDIT_FIELDS.search(text))


# 问题点到哪部分就只附上那部分（11-05 实测“这个案件有哪些费用”：只给基本信息时模型找费用工具搜了 15 次、用了 2 分钟）。
CASE_TOPIC_SECTIONS = (
    ("finances", "费用", re.compile(r"(费用|收费|官费|诉讼费|律师费|代理费|付款|请款|开票|发票|退费|到账|回款|收款|欠款|账款|财务)")),
    ("documents", "文档", re.compile(r"(文档|附件|材料|文书|证据|判决书|裁定书|起诉状|答辩状|传票|通知书|文件)")),
    ("tasks", "任务", re.compile(r"(任务|待办)")),
    ("deadlines", "期限", re.compile(r"(期限|截止|到期|开庭|庭审|日程|提醒|时效|举证期|上诉期)")),
    ("contracts", "合同", re.compile(r"(合同|委托协议|签约)")),
    ("customer", "客户", re.compile(r"(客户|委托人|委托方)")),
    ("relationships", "线索和调查", re.compile(r"(线索|调查|取证)")),
)


def case_topics(message: str) -> list[str]:
    text = str(message or "")
    return [key for key, _, pattern in CASE_TOPIC_SECTIONS if pattern.search(text)]


def slim_case_snapshot(context: dict, *, keep_check: bool = False, topics: list[str] | tuple[str, ...] = ()) -> dict:
    """只保留案件基本信息、人员和本人能做的操作，加上问题点到的那部分资料（topics）；其余费用、文档、任务、线索等不带。
    keep_check=True 时带上系统算好的案件检查结果（“归纳案件情况”“优先待办事项”要用，内容很短）。"""
    keep = ("schema_version", "space", "case", "people", "capabilities", "document_readings", *(("case_check",) if keep_check else ()),
            *[key for key in topics if key in dict((k, 1) for k, _, _ in CASE_TOPIC_SECTIONS)])
    slim = {key: context[key] for key in keep if key in context}
    attached = [label for key, label, _ in CASE_TOPIC_SECTIONS if key in topics and key in context]
    slim["scope_note"] = (("本轮按问题附上了案件的" + "、".join(attached) + "资料，直接据此回答，不要再调用工具查同样的内容；" if attached else "本轮只提供案件基本信息。")
                          + "需要其他资料时，按需调用对应查询工具（如 biz_case_overview），不要一次查全部；用户说“查全部案件空间”时才会提供全部资料。")
    return slim


# 陶国南 11-05 07:44：除非用户让查全部案件空间，否则都不带整个案件空间。
_FULL_SPACE = re.compile(r"(全部案件空间|整个案件空间|案件空间全部|查全部|看整个案件|整个案件|全部资料|所有资料|全面分析|完整分析)")


def is_full_space_request(message: str) -> bool:
    """用户明确要看整个案件空间时才带全部资料。"""
    return bool(_FULL_SPACE.search(str(message or "")))

_MODEL_CHUNK_CALLBACK: ContextVar[Callable[[str], None] | None] = ContextVar("model_chunk_callback", default=None)
# 陶国南 11-05：等待时显示实际步骤（正在调用：修改案件信息…），不再只显示固定的“正在分析案件空间”。
_MODEL_PROGRESS_CALLBACK: ContextVar[Callable[[str], None] | None] = ContextVar("model_progress_callback", default=None)

_CASE_SELECTION: ContextVar[dict[str, Any] | None] = ContextVar("oa_case_selection", default=None)


class CaseAgentState(TypedDict, total=False):
    messages: list[dict[str, Any]]
    case_snapshot: dict[str, Any]
    pending_actions: list[dict[str, Any]]
    last_response: str
    last_operator: str
    updated_at: str
    active_skill: str
    request_images: list[dict[str, Any]]
    skill_override: dict[str, Any] | None
    legacy_migrated: bool
    structured_results: list[dict[str, Any]]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _case_summary(snapshot: dict[str, Any]) -> str:
    case = snapshot.get("case") or {}
    finances = snapshot.get("finances") or {}
    workflow = snapshot.get("standard_workflow") or {}
    phase = workflow.get("current_phase") or {}
    risks = workflow.get("risk_summary") or {}
    return (
        f"案件 {case.get('serial_no') or case.get('id') or '-'} 的空间已加载："
        f"合同 {len(snapshot.get('contracts') or [])} 份，"
        f"文档 {len(snapshot.get('documents') or [])} 份，"
        f"期限 {len(snapshot.get('deadlines') or [])} 项，"
        f"任务 {len(snapshot.get('tasks') or [])} 项，"
        f"费用记录 {len(finances.get('fees') or [])} 条，"
        f"发票 {len(finances.get('invoices') or [])} 条；"
        f"当前标准阶段为 {phase.get('name') or '待识别'}，"
        f"逾期 {risks.get('overdue', 0)} 项，缺少必备材料 {risks.get('missing_required_materials', 0)} 项。"
    )


def _normalize_proposed_action(value: object) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    action_type = str(value.get("type") or "").strip()
    summary = str(value.get("summary") or "").strip()
    payload = value.get("payload")
    if action_type not in ALLOWED_ACTION_TYPES or not summary or not isinstance(payload, dict):
        return None
    return {"type": action_type, "summary": summary[:500], "payload": payload}


def _extract_proposed_action(content: str) -> tuple[str, dict[str, Any] | None]:
    match = ACTION_BLOCK_PATTERN.search(content)
    if not match:
        return content.strip(), None
    cleaned = ACTION_BLOCK_PATTERN.sub("", content).strip()
    try:
        action = _normalize_proposed_action(json.loads(match.group(1)))
    except (json.JSONDecodeError, TypeError, ValueError):
        action = None
    return cleaned, action


def _case_agent_case_source(case: dict[str, Any]) -> dict[str, Any]:
    """将案件顶层字段与案件 data 合并为审批时使用的当前快照。"""
    case_data = case.get("data") or {}
    source = {**case_data, **case}
    handling_lawyers = case_data.get("handling_lawyers")
    handling_usernames = case_data.get("handling_lawyer_usernames")
    if isinstance(handling_lawyers, list):
        source["handling_lawyers"] = handling_lawyers
        source["case_lawyer_name"] = handling_lawyers[0] if handling_lawyers else None
    if isinstance(handling_usernames, list):
        source["handling_lawyer_usernames"] = handling_usernames
        source["case_lawyer"] = handling_usernames[0] if handling_usernames else None
    return source


def _action_preview(proposed_action: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    action_type = proposed_action["type"]
    if action_type == "mcp.call":
        return dict(proposed_action["preview"])
    payload = proposed_action.get("payload") or {}
    case = snapshot.get("case") or {}
    if action_type in {"case.update", "case.data.update", "customer.update", "contract.update"}:
        changes = payload.get("changes") if isinstance(payload.get("changes"), dict) else payload
        if action_type == "customer.update":
            source = snapshot.get("customer") or {}
        elif action_type == "contract.update":
            target_id = int(payload.get("target_id") or 0)
            source = next((item for item in snapshot.get("contracts") or [] if int(item.get("id") or 0) == target_id), {})
        else:
            source = _case_agent_case_source(case)
        return {
            "target": source.get("serial_no") or source.get("title") or case.get("serial_no") or case.get("id") or "当前案件",
            "changes": [
                {"field": key, "before": source.get(key), "before_read": key in source, "after": value}
                for key, value in changes.items() if key != "target_id"
            ],
        }
    if action_type in {"case.delete", "customer.delete", "contract.delete"}:
        if action_type == "customer.delete":
            source = snapshot.get("customer") or {}
        elif action_type == "contract.delete":
            target_id = int(payload.get("target_id") or 0)
            source = next((item for item in snapshot.get("contracts") or [] if int(item.get("id") or 0) == target_id), {})
        else:
            source = case
        return {
            "target": source.get("serial_no") or source.get("title") or case.get("serial_no") or case.get("id") or "当前案件",
            "before_status": source.get("status"),
            "logical_delete": True,
        }
    return {
        "target": case.get("serial_no") or case.get("id") or "当前案件",
        "create": payload,
    }


def _pending_action(proposed_action: dict[str, Any], latest: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": uuid4().hex,
        "type": proposed_action.get("type", "case.update"),
        "summary": proposed_action.get("summary") or "案件写操作",
        "payload": proposed_action.get("payload") or {},
        "preview": _action_preview(proposed_action, snapshot),
        "status": "pending",
        "requested_by": latest.get("operator", ""),
        "requested_at": _now(),
        "decided_by": "",
        "decided_at": "",
        "decision_comment": "",
        "execution_result": None,
    }


def _action_is_authorized(proposed_action: dict[str, Any], snapshot: dict[str, Any]) -> bool:
    if proposed_action.get("type") == "mcp.call":
        # 此能力只允许进入网关确认链，实际业务权限仍由原接口重新校验。
        return bool((snapshot.get("capabilities") or {}).get("can_use_mcp_tools"))
    capability = ACTION_CAPABILITY_BY_TYPE.get(str(proposed_action.get("type") or ""))
    capabilities = snapshot.get("capabilities") or {}
    return bool(capability and capabilities.get(capability))


def _checkpoint_url(database_url: str, explicit_url: str) -> str:
    value = (explicit_url or database_url).strip()
    if value.startswith("postgresql+asyncpg://"):
        return "postgresql://" + value.removeprefix("postgresql+asyncpg://")
    if value.startswith("postgres+asyncpg://"):
        return "postgresql://" + value.removeprefix("postgres+asyncpg://")
    return value


def build_case_model_messages(
    snapshot: dict[str, Any],
    messages: list[dict[str, Any]],
    skill: AgentSkill | None = None,
    request_images: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    from .agent_mcp.model_context import MODEL_QUERY_RULES, model_result_view
    scope = snapshot.get("_model_scope")
    if scope in ("basic", "basic_edit"):
        # 陶国南 11-05 07:44：除非用户让查全部案件空间，模型只看案件基本信息和问题点到的那部分（改信息时连检查结果也不带）。
        snapshot = slim_case_snapshot(snapshot, keep_check=scope == "basic", topics=snapshot.get("_model_topics") or ())
    prioritized_snapshot = {
        "document_readings": snapshot.get("document_readings") or [],
        # 501222：检查结果放前面，长案件截断时也保得住。
        "case_check": snapshot.get("case_check") or {},
        **{key: value for key, value in snapshot.items() if key not in {"document_readings", "case_check"}},
    }
    context = json.dumps(model_result_view(prioritized_snapshot, 80_000), ensure_ascii=False, default=str)
    skill_prompt = f"当前启用技能：{skill.name}。{skill.instruction}\n\n" if skill else ""
    prompt_messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "你是法律服务机构管理系统中的案件智能体。"
                "只能依据当前用户有权限查看的案件空间回答，信息不足时明确说明。"
                "不得声称已经修改、删除、提交或审批业务数据；任何写操作都必须进入人工审批。"
                "用户明确要求生成 Word、DOCX 或法律文书时，应直接输出可作为文档正文的完整内容，"
                "不要回答不能创建 Word；用户点击前端确认后可将完整正文生成 .docx 并保存到当前案件的案件智能体文件夹。"
                "生成正文不等于保存文档；保存案件智能体文件夹草稿和转入正式案件目录都必须由用户点击前端确认。"
                "不能自动保存，不能把聊天中的‘同意’当成前端确认。"
                f"{RESPONSE_STYLE_RULES}{DOCUMENT_READING_RULES}{CASE_INFO_EDIT_RULES}{QUICK_COMMAND_RULES}"
                "系统只提供 oa_list_tool_groups、oa_search_tools 与 oa_call_tool 三个工具门面。"
                "先用 oa_list_tool_groups 按业务发现组，再用 oa_search_tools 携带已发现的 group_id 组内搜索；"
                "25 组必须同时选择返回的 subgroup_id。跨组流程先发现目标组再搜索，不枚举全部工具。"
                "未指定 group_id 的搜索只返回组摘要。发现真实接口后严格按照返回的 inputSchema 调用，"
                "不能猜测工具名称、参数、账号或业务编号。查询工具可立即返回授权数据，写工具只生成待人工确认请求。"
                "不得调用、寻找或模拟人工确认接口，不得把用户的聊天文字当成系统确认。"
                "案件空间摘要可能受权限和数量限制，空费用、发票或回款列表不代表禁止新增费用；"
                "合同金额为空也不自动构成阻断。只依据真实接口的必填项、校验结果和业务规则判断。"
                "已有明确的案件、合同关联与用户提供的字段可直接使用；存在多个合法候选时才请用户选择。"
                "案件空间中的 standard_workflow 是按本案实际类型和案由选用的办案流程，manual 写明手册名称和适用类型"
                "（知识产权纠纷用《知识产权案件标准化操作手册》，合同纠纷、其他民商事案件用对应流程）；"
                "称呼手册时按 manual.name 说，不得把知识产权手册套用到合同纠纷等其他类型的案件；"
                "manual.cause_missing 为真时表示案由未填，回答开头先提醒用户确认并补填案由，暂按通用诉讼流程检查；"
                "应优先依据其中的阶段、材料、岗位与内部管理期限检查案件，"
                "但不得在缺少起算依据时自行推算法定期限。"
                "新的业务操作优先通过上述工具生成待确认请求，不要同时重复生成旧操作块。"
                "已有九类旧动作仍受支持；使用旧动作时可在回答末尾追加一个操作块，格式必须为："
                "<proposed_action>{\"type\":\"case.update\",\"summary\":\"操作摘要\",\"payload\":{\"changes\":{\"字段\":\"新值\"}}}</proposed_action>。"
                "允许的 type 仅有 case.update、case.data.update、case.task.create、case.reminder.create、customer.update、contract.update、case.delete、customer.delete、contract.delete。"
                "case.update 的 payload.changes 仅允许 title、customer、status、description、handling_lawyers、handling_lawyer_usernames。"
                "case.data.update 的 payload.changes 仅允许 court、first_instance_court、first_instance_case_no、second_instance_court、"
                "second_instance_case_no、cause_or_charge、case_stage、filing_date、acceptance_date、judgment_date、effective_date、"
                "archive_no、paper_archive_location、client_position、handling_lawyers、handling_lawyer_usernames。"
                "案件字段必须直接放在 changes 内，不得嵌套 data，不得添加名单外字段。"
                "客户或合同修改必须在 payload 中提供 target_id 和 changes；target_id 只能是当前案件空间已关联记录。"
                "案件任务 payload 使用 title、owner、deadline、priority、description；"
                "案件提醒 payload 使用 content、reminder_date、deadline。"
                "案件经办律师变更必须使用有序数组，优先只提交 handling_lawyer_usernames，填写真实员工 username 而非姓名；"
                "目标账号必须启用，先核对当前授权人员信息中的 username，不得按姓名猜测账号。"
                "缺少目标账号时先要求用户提供或核实账号，不得编造；姓名可能重名，只有确认唯一时才使用 handling_lawyers。"
                "如果同时提交两个数组，姓名和账号必须按相同顺序逐项对应，系统按账号解析并保存正式团队关系。"
                "case_lawyer 与 case_lawyer_name 仅用于读取历史兼容字段，新操作不得输出它们或与数组重复提交别名。"
                "不要声称操作已经执行；没有明确写操作要求时绝对不要输出 proposed_action。"
                "任何写操作都必须服从当前案件空间 capabilities；对应能力为 false 时，"
                "只能说明无权限，不能输出 proposed_action，也不能建议绕过权限。\n\n"
                f"{skill_prompt}"
                f"{MODEL_QUERY_RULES}\n当前案件空间数据：\n{context}"
            ),
        }
    ]
    recent_messages = messages
    for index, message in enumerate(recent_messages):
        role = str(message.get("role") or "").strip()
        content = str(message.get("content") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        if role == "user" and index == len(recent_messages) - 1 and request_images:
            multimodal_content: list[dict[str, Any]] = [{"type": "text", "text": content[:8_000]}]
            for image in request_images:
                multimodal_content.append({"type": "text", "text": f"[附件视觉页：{image.get('name') or '未命名附件'}]"})
                multimodal_content.append({"type": "image_url", "image_url": {"url": image["data_url"]}})
            prompt_messages.append({"role": role, "content": multimodal_content})
        else:
            prompt_messages.append({"role": role, "content": content[:8_000]})
    return prompt_messages


class CaseAgentRuntime:
    def __init__(
        self,
        *,
        enabled: bool,
        database_url: str,
        checkpoint_url: str = "",
        api_base_url: str = "",
        api_key: str = "",
        model_provider: str = "",
        model: str = "",
        max_concurrency: int = 4,
    ) -> None:
        self.enabled = enabled
        self.database_url = database_url
        self.checkpoint_url = checkpoint_url
        self.api_base_url = api_base_url.strip().rstrip("/")
        self.api_key = api_key.strip()
        self.model_provider = model_provider.strip()
        self.model = model.strip()
        self.max_concurrency = max(1, min(max_concurrency, 32))
        self.store: CaseStateStore | None = None
        self.backend = "disabled"
        self.error = ""
        self._semaphore = asyncio.Semaphore(self.max_concurrency)

    async def start(self) -> None:
        if not self.enabled or self.store is not None:
            return
        store = CaseStateStore(_checkpoint_url(self.database_url, self.checkpoint_url))
        try:
            await store.start()
            self.store = store
            self.backend = store.backend
            self.error = ""
        except Exception:
            self.error = "case_state_initialization_failed"
            self.backend = "unavailable"

    async def stop(self) -> None:
        if self.store:
            await self.store.close()
        self.store = None

    def status(self) -> dict[str, Any]:
        native = readiness()
        return {
            "enabled": self.enabled,
            "ready": self.store is not None and native["ready"],
            "agent_runtime_backend": "deepseek-harness",
            "harness_ready": native["ready"],
            "harness_version": native["version"],
            "checkpoint_backend": self.backend,
            "model_provider": self.model_provider,
            "model": self.model,
            "model_configured": bool(self.api_base_url and self.api_key and self.model),
            "max_concurrency": self.max_concurrency,
            "write_requires_approval": True,
            "error": self.error or native["error"],
        }

    async def _case_assistant_node(self, state: CaseAgentState) -> dict[str, Any]:
        messages = state.get("messages") or []
        latest = messages[-1] if messages else {}
        snapshot = state.get("case_snapshot") or {}
        pending_actions = list(state.get("pending_actions") or [])
        proposed_action = latest.get("proposed_action") or None
        request_images = list(state.get("request_images") or [])
        structured_results: list[dict[str, Any]] = []
        if proposed_action:
            action = _pending_action(proposed_action, latest, snapshot)
            pending_actions.append(action)
            response = f"已生成待审批操作：{action['summary']}。审批前不会写入业务数据。"
        elif self.status()["model_configured"]:
            skill_id = str(latest.get("skill_id") or "")
            skill_override = state.get("skill_override")
            if skill_id in SKILLS_BY_ID:
                selected_skill = await runtime_system_skill(skill_id)
            elif isinstance(skill_override, dict) and str(skill_override.get("id") or "") == skill_id:
                selected_skill = AgentSkill(
                    id=skill_id,
                    name=str(skill_override.get("name") or skill_id),
                    category=str(skill_override.get("category") or "Custom"),
                    description=str(skill_override.get("description") or ""),
                    source="user-custom",
                    available=True,
                    unavailable_reason="",
                    instruction=str(skill_override.get("instruction") or ""),
                    quick_prompts=tuple(skill_override.get("quick_prompts") or ()),
                )
            else:
                if skill_id:
                    raise ValueError("skill_definition_required")
                selected_skill = None
            if selected_skill is not None and not selected_skill.available:
                response = f"“{selected_skill.name}”已接入技能目录，但暂不可执行：{selected_skill.unavailable_reason}。"
            else:
                from .agent_mcp.model_tools import TOOL_RESULT_SINK

                token = TOOL_RESULT_SINK.set(structured_results)
                selection = _CASE_SELECTION.get()
                selection_token = _CASE_SELECTION.set({**selection, "actions": pending_actions}) if selection else None
                try:
                    model_result = await self._request_model(snapshot, messages, selected_skill, request_images)
                finally:
                    TOOL_RESULT_SINK.reset(token)
                    if selection_token is not None:
                        _CASE_SELECTION.reset(selection_token)
                if isinstance(model_result, tuple):
                    response, model_action = model_result
                else:
                    response, model_action = str(model_result), None
                model_actions = model_action if isinstance(model_action, list) else [model_action] if model_action else []
                for proposed in model_actions:
                    if _action_is_authorized(proposed, snapshot):
                        action = _pending_action(proposed, latest, snapshot)
                        pending_actions.append(action)
                        response = f"{response}\n\n已生成待确认操作：{action['summary']}。点击前端确认后才会写入系统。".strip()
                    else:
                        response = f"{response}\n\n当前账号原有业务权限不允许执行该操作，未生成审批。".strip()
        else:
            response = _case_summary(snapshot)
        return {
            "messages": [{"role": "assistant", "content": response, "created_at": _now()}],
            "pending_actions": pending_actions,
            "last_response": response,
            "last_operator": latest.get("operator", ""),
            "updated_at": _now(),
            "active_skill": str(latest.get("skill_id") or ""),
            "request_images": [],
            "structured_results": structured_results,
        }

    async def _request_model(
        self,
        snapshot: dict[str, Any],
        messages: list[dict[str, Any]],
        skill: AgentSkill | None = None,
        request_images: list[dict[str, Any]] | None = None,
    ) -> tuple[str, dict[str, Any] | list[dict[str, Any]] | None]:
        from .harness_agent.case_execution import request_case_model

        return await request_case_model(snapshot, messages, skill, request_images,
                                        selection=_CASE_SELECTION.get(), callback=_MODEL_CHUNK_CALLBACK.get(),
                                        progress=_MODEL_PROGRESS_CALLBACK.get())

    @staticmethod
    def thread_id(case_id: int, operator: str, agent_id: int | None = None, conversation_id: int | None = None) -> str:
        normalized_operator = str(operator or "").strip().casefold()
        if not normalized_operator:
            raise ValueError("operator_required")
        operator_key = hashlib.sha256(normalized_operator.encode("utf-8")).hexdigest()[:24]
        if agent_id and conversation_id:
            return f"case:{case_id}:agent:{agent_id}:conversation:{conversation_id}:user:{operator_key}"
        return f"case:{case_id}:user:{operator_key}"

    @classmethod
    def config(cls, case_id: int, operator: str, agent_id: int | None = None, conversation_id: int | None = None) -> dict[str, Any]:
        return {"configurable": {"thread_id": cls.thread_id(case_id, operator, agent_id, conversation_id)}}

    @staticmethod
    def legacy_config(case_id: int) -> dict[str, Any]:
        return {"configurable": {"thread_id": f"case:{case_id}"}}

    @staticmethod
    def _legacy_messages_for_operator(messages: list[dict[str, Any]], operator: str) -> list[dict[str, Any]]:
        normalized_operator = str(operator or "").strip().casefold()
        selected: list[dict[str, Any]] = []
        include_response = False
        for message in messages:
            item = dict(message)
            if item.get("role") == "user":
                include_response = str(item.get("operator") or "").strip().casefold() == normalized_operator
                if include_response:
                    selected.append(item)
            elif item.get("role") == "assistant" and include_response:
                selected.append(item)
        return selected

    async def _ensure_private_state(self, case_id: int, operator: str, agent_id: int | None = None, conversation_id: int | None = None) -> dict[str, Any]:
        private_config = self.config(case_id, operator, agent_id, conversation_id)
        private_state = await self.store.read(private_config["configurable"]["thread_id"])
        if private_state.get("legacy_migrated") or private_state.get("messages") or private_state.get("pending_actions"):
            return private_state

        # 带有明确智能体和会话标识的线程必须保持独立，不能把旧线程内容复制到每个新会话。
        # 未带标识的旧接口仍保留原有迁移行为。
        if agent_id or conversation_id:
            return private_state
        legacy_state = await self.store.read(self.legacy_config(case_id)["configurable"]["thread_id"])
        messages = self._legacy_messages_for_operator(list(legacy_state.get("messages") or []), operator)
        normalized_operator = str(operator or "").strip().casefold()
        actions = [
            dict(item)
            for item in (legacy_state.get("pending_actions") or [])
            if str(item.get("requested_by") or "").strip().casefold() == normalized_operator
        ]
        last_response = next(
            (str(item.get("content") or "") for item in reversed(messages) if item.get("role") == "assistant"),
            "",
        )
        last_user = next((item for item in reversed(messages) if item.get("role") == "user"), {})
        private_state = {
                "messages": messages,
                "pending_actions": actions,
                "last_response": last_response,
                "last_operator": operator if messages else "",
                "updated_at": str(legacy_state.get("updated_at") or ""),
                "active_skill": str(last_user.get("skill_id") or ""),
                "legacy_migrated": True,
            }
        await self.store.write(private_config["configurable"]["thread_id"], private_state)
        return private_state

    async def invoke(
        self, **kwargs: Any,
    ) -> dict[str, Any]:
        selection = {"operator": kwargs["operator"], "case_id": kwargs["case_id"],
                     "conversation": self.thread_id(kwargs["case_id"], kwargs["operator"], kwargs.get("agent_id"), kwargs.get("conversation_id"))}
        from .areas.personal_agent.mcp_chat_input import chat_connection_timeout, extract_chat_connection
        try:
            timeout = chat_connection_timeout(extract_chat_connection(kwargs.get("message") or ""))
        except Exception:
            timeout = 180  # 配置不合法时由 _invoke_impl 照常报错。
        token = _CASE_SELECTION.set(selection)
        try:
            return await asyncio.wait_for(self._invoke_impl(**kwargs), timeout=timeout)
        except asyncio.TimeoutError as exc:
            raise RuntimeError("model_request_timeout") from exc
        finally:
            _CASE_SELECTION.reset(token)

    async def _invoke_impl(
        self,
        *,
        case_id: int,
        operator: str,
        agent_id: int | None = None,
        conversation_id: int | None = None,
        message: str,
        case_snapshot: dict[str, Any],
        proposed_action: dict[str, Any] | None = None,
        images: list[dict[str, Any]] | None = None,
        skill_override: AgentSkill | None = None,
    ) -> dict[str, Any]:
        if self.store is None:
            raise RuntimeError(self.error or "DPH case agent state is not ready")
        from .areas.personal_agent.mcp_chat_input import extract_chat_connection
        from .areas.personal_agent.mcp_credentials import reject_mcp_chat_credentials
        submission = extract_chat_connection(message)
        if submission is None:
            reject_mcp_chat_credentials(message)
        marker_id, clean_message = split_skill_message(message)
        skill = None
        if marker_id in SKILLS_BY_ID:
            skill = await runtime_system_skill(marker_id)
        elif marker_id and (skill_override is None or skill_override.id != marker_id):
            raise ValueError("skill_definition_required")
        if skill_override is not None:
            if marker_id and marker_id != skill_override.id:
                raise ValueError("skill_selection_conflict")
            skill = skill_override
            if skill.id in SKILLS_BY_ID:
                skill = await runtime_system_skill(skill.id)
        user_message = {
            "id": uuid4().hex,
            "role": "user",
            "content": clean_message,
            "skill_id": skill.id if skill else "",
            "skill_name": skill.name if skill else "",
            "operator": operator,
            "created_at": _now(),
            "attachments": [
                {"id": image.get("id", ""), "name": image.get("name", ""), "mime_type": image.get("mime_type", "")}
                for image in (images or [])
            ],
        }
        if proposed_action:
            user_message["proposed_action"] = proposed_action
        skill_override_payload = None
        if skill_override is not None:
            skill_override_payload = {
                "id": skill_override.id,
                "name": skill_override.name,
                "category": skill_override.category,
                "description": skill_override.description,
                "instruction": skill_override.instruction,
                "quick_prompts": list(skill_override.quick_prompts),
            }
        thread = self.thread_id(case_id, operator, agent_id, conversation_id)
        async with self._semaphore, self.store.operation(thread):
            state = await self._ensure_private_state(case_id, operator, agent_id, conversation_id)
            state.update(case_snapshot=case_snapshot, request_images=list(images or []), skill_override=skill_override_payload)
            if submission is not None:
                from .areas.personal_agent.mcp_chat_connection import configure_chat_submission
                from .database import SessionLocal

                async def persist(_owner, value):
                    await self.store.write(thread, value)

                async def delta(value):
                    callback = _MODEL_CHUNK_CALLBACK.get()
                    if callback:
                        callback(value)

                async with SessionLocal() as db:
                    await configure_chat_submission(submission, {'username': operator}, db, state, delta, None,
                                                    save_state=persist, case_id=case_id)
                return self._public_state(case_id, operator, state, agent_id, conversation_id)
            state["messages"] = [*state.get("messages", []), user_message]
            await self.store.write(thread, state)
            response = await self._case_assistant_node(state)
            result = {**state, **response, "messages": [*state["messages"], *response.get("messages", [])]}
            await self.store.write(thread, result)
        return self._public_state(case_id, operator, result, agent_id, conversation_id)

    async def invoke_stream(self, **kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        async def run() -> None:
            token = _MODEL_CHUNK_CALLBACK.set(lambda content: queue.put_nowait({"type": "delta", "content": content}))
            progress_token = _MODEL_PROGRESS_CALLBACK.set(lambda text: queue.put_nowait({"type": "progress", "text": text}))
            from .agent_mcp.model_tools import PENDING_ACTION_SINK

            def announce(action: dict[str, Any]) -> None:
                # 先显示卡片（按钮在本轮回复写完、正式记录后才可点），最终 state 事件再替换成正式卡片。
                request_id = str((action.get("payload") or {}).get("request_id") or "")
                queue.put_nowait({"type": "pending_action", "action": {
                    "id": "preparing-" + request_id, "type": action.get("type"), "summary": action.get("summary"),
                    "preview": action.get("preview"), "status": "pending", "preparing": True, "requested_at": _now()}})
                queue.put_nowait({"type": "progress", "text": "已生成确认卡片，请在上方查看"})

            sink_token = PENDING_ACTION_SINK.set(announce)
            try:
                state = await self.invoke(**kwargs)
                await queue.put({"type": "state", "state": state})
            except Exception as exc:
                await queue.put({"type": "error", "detail": str(exc)})
            finally:
                _MODEL_CHUNK_CALLBACK.reset(token)
                _MODEL_PROGRESS_CALLBACK.reset(progress_token)
                PENDING_ACTION_SINK.reset(sink_token)
                await queue.put({"type": "done"})

        task = asyncio.create_task(run())
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield {"type": "heartbeat"}
                    continue
                if event["type"] == "done":
                    break
                yield event
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def get_state(self, case_id: int, operator: str, agent_id: int | None = None, conversation_id: int | None = None) -> dict[str, Any]:
        if self.store is None:
            raise RuntimeError(self.error or "DPH case agent state is not ready")
        async with self.store.operation(self.thread_id(case_id, operator, agent_id, conversation_id)):
            state = await self._ensure_private_state(case_id, operator, agent_id, conversation_id)
            return self._public_state(case_id, operator, state, agent_id, conversation_id)

    async def ensure_context(
        self,
        case_id: int,
        operator: str,
        case_snapshot: dict[str, Any],
        agent_id: int | None = None,
        conversation_id: int | None = None,
    ) -> None:
        """在当前用户的案件会话线程中预置最新授权案件底座。"""
        if self.store is None:
            raise RuntimeError(self.error or "DPH case agent state is not ready")
        thread = self.thread_id(case_id, operator, agent_id, conversation_id)
        async with self.store.operation(thread):
            state = await self._ensure_private_state(case_id, operator, agent_id, conversation_id)
            if state.get("case_snapshot") != case_snapshot:
                state.update(case_snapshot=case_snapshot, updated_at=_now())
                await self.store.write(thread, state)

    async def sync_tool_requests(
        self, case_id: int, operator: str, requests: dict[str, dict[str, Any]],
        agent_id: int | None = None, conversation_id: int | None = None,
    ) -> dict[str, Any] | None:
        """确认请求已在智能体中心（或别处）处理时，把案件窗口里同一张卡片改成同样的结果（调度 11-05）。
        requests：request_id → 确认请求的公开视图（status 为 pending/executing/succeeded/failed/rejected）。返回同步后的状态，没有变化时返回 None。"""
        if self.store is None or not requests:
            return None
        mapping = {"succeeded": "approved", "rejected": "rejected", "failed": "failed", "executing": "executing"}
        thread = self.thread_id(case_id, operator, agent_id, conversation_id)
        async with self.store.operation(thread):
            values = await self._ensure_private_state(case_id, operator, agent_id, conversation_id)
            actions = [dict(item) for item in values.get("pending_actions") or []]
            changed = False
            for action in actions:
                if action.get("type") != "mcp.call" or action.get("status") not in ("pending", "executing"):
                    continue
                view = requests.get(str((action.get("payload") or {}).get("request_id") or ""))
                status = mapping.get(str((view or {}).get("status") or ""))
                if not status or status == action.get("status"):
                    continue
                action.update({"status": status, "decided_by": action.get("decided_by") or operator,
                               "decided_at": str(view.get("finished_at") or view.get("decided_at") or _now()),
                               "decision_comment": str(view.get("comment") or "已在智能体中心处理"), "decided_via": "agent_center",
                               "execution_result": {"status": view.get("status"), "result": view.get("result"), "error": view.get("error")}
                               if status != "executing" else action.get("execution_result")})
                changed = True
            if not changed:
                return None
            values.update(pending_actions=actions, updated_at=_now())
            await self.store.write(thread, values)
            return self._public_state(case_id, operator, values, agent_id, conversation_id)

    async def decide_action(
        self,
        *,
        case_id: int,
        action_id: str,
        decision: str,
        operator: str,
        agent_id: int | None = None,
        conversation_id: int | None = None,
        comment: str = "",
        execution_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self.store is None:
            raise RuntimeError(self.error or "DPH case agent state is not ready")
        thread = self.thread_id(case_id, operator, agent_id, conversation_id)
        async with self.store.operation(thread):
            values = await self._ensure_private_state(case_id, operator, agent_id, conversation_id)
            actions = [dict(item) for item in values.get("pending_actions") or []]
            action = next((item for item in actions if item.get("id") == action_id), None)
            if not action:
                raise KeyError(action_id)
            if action.get("status") != "pending":
                raise ValueError("action_already_decided")
            action.update({
                "status": decision,
                "decided_by": operator,
                "decided_at": _now(),
                "decision_comment": comment,
                "execution_result": execution_result,
            })
            response = "待审批操作已批准并写入系统。" if decision == "approved" else "待审批操作已驳回，系统数据未修改。"
            values.update(pending_actions=actions,
                          messages=[*values.get("messages", []), {"role": "assistant", "content": response, "created_at": _now()}],
                          last_response=response, last_operator=operator, updated_at=_now())
            await self.store.write(thread, values)
            return self._public_state(case_id, operator, values, agent_id, conversation_id)

    @classmethod
    def _public_state(cls, case_id: int, operator: str, state: dict[str, Any], agent_id: int | None = None, conversation_id: int | None = None) -> dict[str, Any]:
        return {
            # thread_id 保持旧接口契约；真实隔离线程通过 conversation_thread_id 返回。
            "thread_id": cls.thread_id(case_id, operator),
            "conversation_thread_id": cls.thread_id(case_id, operator, agent_id, conversation_id),
            "agent_id": agent_id,
            "conversation_id": conversation_id,
            "thread_namespace": "sunhold.case-agent.private.v1",
            "shared_space_id": f"case:{case_id}",
            "messages": state.get("messages") or [],
            "pending_actions": state.get("pending_actions") or [],
            "last_response": state.get("last_response", ""),
            "last_operator": state.get("last_operator", ""),
            "updated_at": state.get("updated_at", ""),
            "active_skill": state.get("active_skill", ""),
            "structured_results": state.get("structured_results") or [],
        }
