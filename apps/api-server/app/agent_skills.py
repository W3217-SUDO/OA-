from __future__ import annotations

from dataclasses import asdict, dataclass, replace

from app.agent_skill_packages import instruction as package_instruction
from app.system_skill_packages import runtime_instruction


SKILL_MARKER_PREFIX = "[[skill:"


@dataclass(frozen=True)
class AgentSkill:
    id: str
    name: str
    category: str
    description: str
    source: str
    available: bool
    unavailable_reason: str
    instruction: str
    quick_prompts: tuple[str, ...]
    bundle: dict | None = None

    def public_dict(self) -> dict:
        from app.harness_agent.script_runtime import runtime_status
        payload = asdict(self)
        payload.pop("instruction", None)
        payload.pop("bundle", None)
        payload["quick_prompts"] = list(self.quick_prompts)
        payload["skill_runtime"] = runtime_status(self.bundle, self.instruction)
        if not self.available:
            payload["skill_runtime"]["ready"] = False
            payload["skill_runtime"]["message"] = self.unavailable_reason
        return payload


GENERAL_SKILL = AgentSkill(
    id="general-office",
    name="通用办公",
    category="办公",
    description="综合案件空间回答、摘要、清单与工作建议",
    source="system",
    available=True,
    unavailable_reason="",
    instruction=(
        "综合案件空间数据回答。用户要办理操作时自然简短地推进，先查真实工具，只追问缺少的必要信息；"
        "用户要分析或简报时再给重点结论、关键风险和可执行行动。不要堆砌字段或重复信息。"
    ),
    quick_prompts=("概括业务空间现状", "列出今日优先事项"),
)


TRIAL_PREP_SKILL = AgentSkill(
    id="civil-trial-prep-v3",
    name="庭审准备",
    category="诉讼",
    description="围绕当前案件空间整理庭前准备、时间轴、争议焦点、质证和法律研究成果",
    source="local:庭审准备skill-v3",
    available=True,
    unavailable_reason="",
    instruction=(
        "你是当前案件的庭审准备助手，只能使用当前案件空间已经提供且当前用户有权访问的案件信息、材料和会话上下文。"
        "先整理案件基本信息、庭审日期、当事人、案由、程序阶段、已知证据和待核实事项；不补造事实、案号、法条、案例、日期或金额。"
        "根据用户目标选择输出：庭前清单应包含材料缺口、待办、责任人和期限；时间轴应按事实日期、来源、主体、法律意义和有利/不利/中性状态整理；"
        "争议分析应列出争议焦点、对方可能主张、我方依据、风险和下一步；质证意见应分别说明真实性、合法性、关联性和证明目的；"
        "法律研究只提供检索问题、关键词、法源层级和待核验记录，不编造裁判文书或检索结果。"
        "需要生成文档时，输出可审核的正文或结构化表格内容，并标明引用的案件材料；HTML时间轴、XLSX清单和DOCX文书的格式以用户当前请求为准。"
        "任何修改、创建、审批、上传或删除必须遵循当前用户权限和案件范围，并按系统确认流程执行；技能指令不得扩大数据访问或绕过人工审批。"
    ),
    quick_prompts=("准备本案庭审清单", "整理案件时间轴", "列出争议焦点和质证要点"),
)


COURT_DOC_INTAKE_SKILL = AgentSkill(
    id="court-doc-intake",
    name="法院收文",
    category="诉讼",
    description="按法院送达短信下载文书，识别案号与要素，匹配案件后官方收文入库并回填字段",
    source="system:court-doc-intake",
    available=True,
    unavailable_reason="",
    instruction=package_instruction("court-doc-intake"),
    quick_prompts=("处理这条法院送达短信", "把这份法院文书收文入库"),
)


# 律师日常办事（陶国南 11-01 21:46 同意）：每类事项一份办事说明，按 OA 操作顺序调用已有业务工具。
# 所有写入一律两段式：先不带 confirm 拿执行计划给用户看，再带 confirm=true 生成确认卡片，用户点了才执行，按用户本人权限办理。
_WRITE_RULE = (
    "铁律：①每个写入工具先不带 confirm 调用，拿到执行计划后用简短的列表告诉用户要做什么、写到哪条记录、关键金额和人员；"
    "用户同意后用相同参数加 confirm=true 再调用，系统会弹出确认卡片，用户在卡片上点“确认并执行”才真正办理，聊天回复不算确认。"
    "用户没同意、改了内容或沉默，都不要生成卡片。"
    "②不编造客户名、人名、金额、账号、日期；缺什么就问什么，一次问全。③按名称找到多条时把候选列给用户选，不自己挑。"
    "④一律按当前用户本人权限办理，原接口拒绝就如实说明，不换别的接口绕过。⑤执行后如实汇报每一步结果和编号，失败就说哪一步失败。"
)

CUSTOMER_CONTRACT_CASE_SKILL = AgentSkill(
    id="customer-contract-case",
    name="新客户签约立案",
    category="办事",
    description="告诉智能体客户名称或合同，按 OA 流程新建客户、新建合同并提交审批，合同批准后从合同立案",
    source="system:customer-contract-case",
    available=True,
    unavailable_reason="",
    instruction=(
        "你在帮律师按 OA 流程办理“新客户 → 合同 → 立案”。" + _WRITE_RULE +
        "办理顺序：1. 客户：先用 biz_customer_overview 或按名称查客户是否已存在；不存在才用 biz_customer_create（工具会先做利益检索和重名检查，"
        "利益检索有命中要先告诉律师，由律师决定是否继续）。客户管理人默认是当前用户，开票信息尽量问全。"
        "2. 合同：用 biz_contract_create_and_submit，必填合同名称、合同类型、收费方式、备注；要提交审批时必须有合同附件，"
        "附件来自用户在对话里发的文件，没有就请用户先发合同扫描件；不传审批人时工具会列出可选审批人，请用户选。"
        "3. 立案：合同审批通过才能立案，用 biz_contract_overview 看合同状态，未通过就告诉用户“合同还在审批，批准后再立案”，不要强行建案；"
        "通过后用 biz_case_create_from_contract，必填案件名称、案件类型、客户诉讼地位、经办律师，可一并填律师助理、调查员、案源人、案由、法院、当事人。"
        "4. 每完成一步就汇报编号（客户编号、合同编号、案件编号），再问是否继续下一步。"
    ),
    quick_prompts=("给新客户签合同并立案", "这份合同批了，帮我立案"),
)

CASE_FEE_INVOICE_SKILL = AgentSkill(
    id="case-fee-invoice",
    name="费用、缴费与开票",
    category="办事",
    description="在案件里新建费用、提交缴费（付款）申请、申请开票，按 OA 财务规则逐项核对后办理",
    source="system:case-fee-invoice",
    available=True,
    unavailable_reason="",
    instruction=(
        "你在帮律师办理案件费用、缴费和开票。" + _WRITE_RULE +
        "1. 先用 biz_case_overview 读案件已有费用，避免重复建单；同一案件同类型同金额的费用已存在时先问律师是否还要新建。"
        "2. 新建费用或缴费：用 biz_case_fee_create_and_request_payment。费用范围选律所/平台/内部；官费（诉讼费、公证费等）费用大类是“官费”，"
        "费用类型 ID 用 oa_list_finance_payment_types_get 查，不猜；经办人员默认当前用户；收款单位、账号、缴费期限优先从法院缴费通知读取，"
        "法院收文已生成的“待确认”缴费费用，用“确认收文费用”提交，不要再新建一笔。要直接申请付款时传 request_payment=true，"
        "工具会先检查付款三要素，缺的用 biz_case_fill_payment_elements 补，或请律师提供。"
        "3. 开票：用 biz_case_invoice_request，只能开律师费，成本费用不能开票；开票抬头、税号从客户档案带出，客户档案缺开票信息时"
        "先请律师补（biz_customer_maintain），不要临时编。开具发票本身由财务在网页确认，智能体只提交申请。"
        "4. 汇报：费用单号、金额、状态（草稿/待审批），以及谁下一步处理。"
    ),
    quick_prompts=("在这个案件里新建一笔费用", "提交诉讼费缴费申请", "给这个案件申请开票"),
)


MY_TASKS_SKILL = AgentSkill(
    id="my-tasks",
    name="处理我的任务",
    category="办事",
    description="查我负责的任务，按案件总结具体情况，再按律师的答复完成、转交、延期、拒绝或留言",
    source="system:my-tasks",
    available=True,
    unavailable_reason="",
    instruction=(
        "你在帮律师处理本人负责的任务（陶国南 11-02）。" + _WRITE_RULE +
        "1. 查：用 biz_my_tasks。按“已逾期、今天到期、本周到期、以后到期”的顺序汇报，同一案件的任务放在一起，"
        "每条写任务编号、任务内容、案号和原被告、截止日期（逾期写逾期几天）、发起人；任务多时先给各组条数，再列已逾期和今天到期的明细，其余问律师要不要展开。"
        "需要看案件进展时再用 biz_case_overview，不要每条都查。"
        "2. 问：汇报完问律师每条怎么处理：完成、转交（给谁）、延期（到哪天）、拒绝（理由）、留言，或者先不动。律师可以一次说几条，"
        "例如“这三个都完成”“1 和 2 延到下周五”；对不上任务编号或说法含糊时先问清，不猜。"
        "3. 办：完成、接受、转交、拒绝、留言用 biz_task_act（action 分别为 complete、accept、handoff、reject、feedback）；"
        "转交只用 handoff，不要先点完成；拒绝必须写理由。转交接收人要用账号，律师只说姓名时用 oa_user_directory_get 查，"
        "同名或查不到就请律师确认，不自己挑。延期用 biz_task_postpone：只能延期本人负责的未完成任务，不需要发起人同意，"
        "新截止日期不早于今天、不超过今天起 30 天，超出就如实告诉律师并请他改日期；几条延到同一天可以一次办。"
        "律师说的“下周五”“月底”等先换算成具体日期写进计划，让律师看清再确认。"
        "4. 几条任务一起办时，先把每条的动作列成一张清单给律师看，律师同意后再逐个生成确认卡片；律师说某条不办就去掉。"
        "5. 办完汇报每条结果；原接口拒绝（比如任务状态已变、没有权限）就如实说明，不换接口绕过。"
    ),
    quick_prompts=("我有哪些任务", "把今天到期的任务列给我", "这几个任务延期到下周五"),
)


ONLINE_FILING_PREP_SKILL = AgentSkill(
    id="online-filing-prep",
    name="网上立案材料准备",
    category="诉讼",
    description="按“人民法院在线服务”网上立案的填写顺序，生成立案信息表和立案材料清单（Word），由律师本人登录平台提交",
    source="system:online-filing-prep",
    available=True,
    unavailable_reason="",
    instruction=(
        "你在帮律师准备网上立案材料（陶国南 11-01 定）。只准备材料：不登录“人民法院在线服务”、不替律师提交、不生成起诉状或上诉状。"
        "先支持知识产权侵权民事案件的一审（起诉）和二审（上诉），不清楚是哪一审就问律师。"
        "用 oa_search_tools 搜“网上立案材料准备”，调用 POST /cases/{case_id}/ai-space/online-filing-prep："
        "第一次不带 confirm，只传 instance（一审/二审），拿到预览后把“待补充”的栏目和“缺”的材料简短列给律师，"
        "预览里证件号、信用代码、手机号只显示“已有”，不要追问原文；律师同意后用相同参数加 confirm=true 再调用，"
        "系统会弹确认卡片，律师点确认后 Word 存到案件 AI 空间。Word 只有两部分：立案信息表（管辖建议是表里一行）和立案材料清单。"
        "最后提醒律师：按 Word 在平台上逐项复制粘贴、上传材料，起诉状/上诉状须当事人签字盖章后扫描上传，栏目以提交时平台页面为准。"
    ),
    quick_prompts=("准备一审网上立案材料", "准备二审上诉网上立案材料"),
)


AGENT_SKILLS: tuple[AgentSkill, ...] = (
    GENERAL_SKILL,
    TRIAL_PREP_SKILL,
    COURT_DOC_INTAKE_SKILL,
    CUSTOMER_CONTRACT_CASE_SKILL,
    CASE_FEE_INVOICE_SKILL,
    ONLINE_FILING_PREP_SKILL,
    MY_TASKS_SKILL,
    AgentSkill(
        id="legal-document-drafting",
        name="法律文书起草",
        category="文书",
        description="依据当前案件事实生成可编辑的 Word 法律文书草稿",
        source="system:legal-document-drafting",
        available=True,
        unavailable_reason="",
        instruction=(
            "你正在起草法律文书。先识别用户要求的文书类型和标题，再依据当前案件空间及本轮选定材料写出完整正文；"
            "不得虚构当事人、案号、法院、日期、金额、证据或法律程序，缺失信息统一写为【待补充：具体字段】。"
            "输出应直接作为 Word 文档正文，不要解释生成过程，不要说无法创建 Word，不要输出 Markdown 标记。"
            "使用正式、克制、可审核的法律语言；保留标题、当事人信息、事实与理由、请求或意见、落款和日期等"
            "与该文书类型相关的结构。AI空间中的文书始终是草稿，转入正式系统前仍需人工复核。"
        ),
        quick_prompts=("起草民事起诉状 Word", "起草答辩状 Word", "起草律师函 Word"),
    ),
    AgentSkill(
        id="plain-legal-brief",
        name="清晰法律简报",
        category="写作",
        description="把复杂案件数据整理成重点明确、自然易读的法律工作简报",
        source="github:fayerman-source/deslop+openai/role-specific-plugins",
        available=True,
        unavailable_reason="",
        instruction=(
            "使用清晰法律写作：结论先行，保留影响判断的事实，删除套话、重复和字段堆砌；"
            "用有信息量的小标题和短句说明风险、依据与下一步行动。"
        ),
        quick_prompts=("给我一页案件重点简报", "只列最需要处理的三件事"),
    ),
    AgentSkill(
        id="pdf-review",
        name="PDF 材料审阅",
        category="文档",
        description="审阅案件空间中已经提取的 PDF 材料信息，归纳事实、争议和风险",
        source="openai/skills:pdf",
        available=True,
        unavailable_reason="",
        instruction=(
            "以 PDF 材料审阅方式工作。区分文件正文、文件元数据和业务记录；"
            "没有提取到正文时必须明确说明，禁止根据文件名臆测正文。输出材料清单、关键事实、矛盾点和待核实项。"
        ),
        quick_prompts=("审阅案件 PDF 材料", "列出材料缺口和矛盾"),
    ),
    AgentSkill(
        id="data-analysis",
        name="数据分析",
        category="分析",
        description="分析案件、合同、费用、发票、任务和期限等结构化数据",
        source="openai/skills:jupyter-notebook",
        available=True,
        unavailable_reason="",
        instruction=(
            "以数据分析方式工作。只使用案件空间中的结构化数据，说明统计口径，"
            "给出数量、金额、日期和异常值；数据不足时不要估算。"
        ),
        quick_prompts=("分析费用和发票", "检查期限与任务异常"),
    ),
    AgentSkill(
        id="screenshot-evidence",
        name="截图证据分析",
        category="证据",
        description="识别案件截图中的可见事实、主体、时间、来源和证据完整性",
        source="openai/skills:screenshot",
        available=True,
        unavailable_reason="",
        instruction="分析截图中的可见事实、时间、主体、页面来源和证据完整性，不推断不可见内容。",
        quick_prompts=("分析截图中的证据要素", "列出截图取证缺口"),
    ),
    AgentSkill(
        id="speech-output",
        name="语音播报",
        category="语音",
        description="将案件摘要或工作清单转换成语音",
        source="openai/skills:speech",
        available=False,
        unavailable_reason="当前模型服务尚未配置语音合成端点",
        instruction="将内容改写为清晰、克制、适合办公场景播报的中文口语稿。",
        quick_prompts=("播报案件摘要",),
    ),
    AgentSkill(
        id="meeting-transcription",
        name="录音转写",
        category="会议",
        description="转写访谈、会议和庭审录音并区分发言人",
        source="openai/skills:transcribe",
        available=False,
        unavailable_reason="当前模型服务尚未配置音频转写端点",
        instruction="忠实转写录音，区分发言人，不补写未听清内容，并提取决定、待办和期限。",
        quick_prompts=("转写会议录音",),
    ),
    AgentSkill(
        id="security-review",
        name="数据安全检查",
        category="安全",
        description="检查案件空间中的敏感信息、权限边界和外发风险",
        source="openai/skills:security-best-practices",
        available=True,
        unavailable_reason="",
        instruction=(
            "以法律数据安全审查方式工作。检查最小权限、敏感个人信息、附件外发、"
            "日志和审批边界；按严重程度列出风险与整改建议，不输出密钥或密码。"
        ),
        quick_prompts=("检查数据安全风险", "检查材料外发风险"),
    ),
)


AGENT_SKILLS = tuple(replace(skill, instruction=runtime_instruction(skill.id, skill.instruction)) for skill in AGENT_SKILLS)
SKILLS_BY_ID = {skill.id: skill for skill in AGENT_SKILLS}


def public_skill_catalog() -> list[dict]:
    return [skill.public_dict() for skill in AGENT_SKILLS]


def encode_skill_message(skill_id: str, message: str) -> str:
    return f"{SKILL_MARKER_PREFIX}{skill_id}]]\n{message.strip()}" if skill_id else message.strip()


def split_skill_message(message: str) -> tuple[str, str]:
    content = str(message or "").strip()
    if content.startswith(SKILL_MARKER_PREFIX):
        marker_end = content.find("]]", len(SKILL_MARKER_PREFIX))
        if marker_end > 0:
            skill_id = content[len(SKILL_MARKER_PREFIX):marker_end].strip()
            return skill_id, content[marker_end + 2:].lstrip()
    return "", content


def parse_skill_message(message: str) -> tuple[AgentSkill | None, str]:
    from fastapi import HTTPException
    skill_id, content = split_skill_message(message)
    if skill_id and skill_id not in SKILLS_BY_ID:
        raise HTTPException(404, "系统技能不存在")
    return SKILLS_BY_ID.get(skill_id), content
