"""case_documents 领域请求数据契约。"""

from pydantic import BaseModel, Field


class AttachmentBatchInput(BaseModel):
    attachment_ids: list[int] = Field(min_length=1, max_length=100)
    case_id: int | None = Field(default=None, gt=0)


class CaseAttachmentRenameInput(BaseModel):
    original_name: str = Field(min_length=1, max_length=255)


class CaseAttachmentMoveInput(BaseModel):
    attachment_ids: list[int] = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=64)


class CaseAiDraftCreateInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    content: str = Field(default="", max_length=2_000_000)


class CaseAiDraftUpdateInput(BaseModel):
    content: str = Field(max_length=2_000_000)


class CaseAiDraftPromoteInput(BaseModel):
    category: str = Field(min_length=1, max_length=64)


class WordEditorTextBlockInput(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    text: str = Field(max_length=200_000)


class CaseWordEditorSaveInput(BaseModel):
    lock_token: str = Field(min_length=24, max_length=96)
    version: str = Field(min_length=64, max_length=64)
    blocks: list[WordEditorTextBlockInput] = Field(min_length=1, max_length=10_000)


class CaseWordEditorLockInput(BaseModel):
    lock_token: str = Field(min_length=24, max_length=96)


class CaseDocumentFolderInput(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class CaseDocumentFolderRenameInput(CaseDocumentFolderInput):
    original_name: str = Field(min_length=1, max_length=64)


class TemplateInput(BaseModel):
    name: str
    category: str
    version: str = "1.0"
    description: str = ""
    fields: list[str] = Field(default_factory=list)


class TemplateUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    version: str | None = None
    description: str | None = None
    fields: list[str] | None = None
    is_active: bool | None = None
