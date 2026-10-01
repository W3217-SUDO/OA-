"""agents 领域请求数据契约。"""

from pydantic import BaseModel, Field


class DifyRequest(BaseModel):
    query: str
    conversation_id: str | None = None


class CaseAgentProposedAction(BaseModel):
    type: str = Field(default="case.update", pattern=r"^(case\.update|case\.data\.update|case\.task\.create|case\.reminder\.create|customer\.update|contract\.update|case\.delete|customer\.delete|contract\.delete)$")
    summary: str = Field(min_length=2, max_length=500)
    payload: dict = Field(default_factory=dict)


class CaseAgentMessageInput(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    skill_id: str = Field(default="general-office", min_length=1, max_length=100)
    proposed_action: CaseAgentProposedAction | None = None
    attachment_ids: list[int] = Field(default_factory=list, max_length=4)
    document_ids: list[int] | None = Field(default=None, max_length=12)
    stream: bool = False


class UserAgentSkillInput(BaseModel):
    name: str = Field(min_length=2, max_length=64)
    category: str = Field(default="自定义", min_length=1, max_length=32)
    description: str = Field(min_length=2, max_length=500)
    instruction: str = Field(min_length=10, max_length=6000)
    quick_prompts: list[str] = Field(default_factory=list, max_length=5)
    enabled: bool = True


class UserAgentSkillUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=64)
    category: str | None = Field(default=None, min_length=1, max_length=32)
    description: str | None = Field(default=None, min_length=2, max_length=500)
    instruction: str | None = Field(default=None, min_length=10, max_length=6000)
    quick_prompts: list[str] | None = Field(default=None, max_length=5)
    enabled: bool | None = None


class CaseAgentDecisionInput(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    comment: str = Field(default="", max_length=1000)


class AgentDocumentInput(BaseModel):
    template_id: int
    record_id: int | None = None
    title: str
    instruction: str = ""


class AgentDocumentUpdate(BaseModel):
    title: str | None = None
    content: str | None = None


class AgentDocumentConfirmInput(BaseModel):
    comment: str = Field(default="", max_length=1000)
