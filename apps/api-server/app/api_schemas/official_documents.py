"""official_documents 领域请求数据契约。"""

from datetime import date
from pydantic import BaseModel, Field


class DocumentTransitionInput(BaseModel):
    to_status: str
    action_date: date = Field(default_factory=date.today)
    handler: str = ""
    archive_no: str = ""
    archive_location: str = ""
    comment: str = ""


class OfficialDocumentProcessInput(BaseModel):
    record_ids: list[int] = Field(min_length=1, max_length=100)
    processed: bool
    comment: str = Field(default="", max_length=1000)


class OfficialDocumentReceiptDateInput(BaseModel):
    """Dedicated command for the legacy official-receipt date correction."""
    record_ids: list[int] = Field(min_length=1, max_length=100)
    document_date: date
    comment: str = Field(default="", max_length=1000)


class OfficialDocumentDeleteInput(BaseModel):
    """Dedicated removal command for unprocessed official incoming documents."""
    record_ids: list[int] = Field(min_length=1, max_length=100)


class OfficialDocumentBatchCaseIdsInput(BaseModel):
    """Link selected official incoming documents to cases in one batch command.

    The document module keeps receipt metadata changes on dedicated endpoints so
    the generic record API cannot bypass lifecycle or audit controls.
    """
    record_ids: list[int] = Field(min_length=1, max_length=100)
    case_ids: list[int] = Field(min_length=1, max_length=100)


class OfficialOutgoingCreateInput(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    source_type: str = Field(pattern="^(contract|case)$")
    source_record_id: int = Field(gt=0)
    source_file_ids: list[int] = Field(default_factory=list, max_length=100)
    need_audit: bool = True
    seal_asset_id: int | None = Field(default=None, gt=0)
    is_electronic_seal: bool = False
    is_offline_print: bool = True
    print_quantity: int = Field(default=1, ge=1, le=9999)
    content: str = Field(default="", max_length=10000)
    remark: str = Field(default="", max_length=2000)


class OfficialOutgoingUpdateInput(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    need_audit: bool = True
    seal_asset_id: int = Field(gt=0)
    is_electronic_seal: bool = False
    is_offline_print: bool = True
    print_quantity: int = Field(default=1, ge=1, le=9999)
    content: str = Field(default="", max_length=10000)
    remark: str = Field(default="", max_length=2000)


class OfficialOutgoingReviewInput(BaseModel):
    approved: bool
    comment: str = Field(default="", max_length=1000)


class OfficialOutgoingRollbackInput(BaseModel):
    reason: str = Field(min_length=2, max_length=1000)


class OfficialOutgoingSubmitInput(BaseModel):
    comment: str = Field(default="", max_length=1000)


class OfficialOutgoingBatchInput(BaseModel):
    record_ids: list[int] = Field(min_length=1, max_length=100)
