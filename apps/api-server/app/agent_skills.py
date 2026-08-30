from __future__ import annotations

from dataclasses import asdict, dataclass


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

    def public_dict(self) -> dict:
        payload = asdict(self)
        payload.pop("instruction", None)
        payload["quick_prompts"] = list(self.quick_prompts)
        return payload


GENERAL_SKILL = AgentSkill(
    id="general-office",
    name="通用办公",
    category="办公",
    description="综合案件空间回答、摘要、清单与工作建议",
    source="system",
    available=True,
    unavailable_reason="",
    instruction="综合案件空间数据回答。先给重点结论，再给关键风险和可执行行动；不要堆砌字段或重复信息。",
    quick_prompts=("概括业务空间现状", "列出今日优先事项"),
)


AGENT_SKILLS: tuple[AgentSkill, ...] = (
    GENERAL_SKILL,
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


SKILLS_BY_ID = {skill.id: skill for skill in AGENT_SKILLS}


def public_skill_catalog() -> list[dict]:
    return [skill.public_dict() for skill in AGENT_SKILLS]


def encode_skill_message(skill_id: str, message: str) -> str:
    normalized = skill_id if skill_id in SKILLS_BY_ID else GENERAL_SKILL.id
    return f"{SKILL_MARKER_PREFIX}{normalized}]]\n{message.strip()}"


def parse_skill_message(message: str) -> tuple[AgentSkill, str]:
    content = str(message or "").strip()
    if content.startswith(SKILL_MARKER_PREFIX):
        marker_end = content.find("]]", len(SKILL_MARKER_PREFIX))
        if marker_end > 0:
            skill_id = content[len(SKILL_MARKER_PREFIX):marker_end].strip()
            skill = SKILLS_BY_ID.get(skill_id, GENERAL_SKILL)
            return skill, content[marker_end + 2:].lstrip()
    return GENERAL_SKILL, content
