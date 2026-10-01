"""seals 领域请求数据契约。"""

from datetime import date
from pydantic import BaseModel, Field


class SealApplicationInput(BaseModel):
    title: str
    customer: str = ""
    case_no: str = ""
    contract_no: str = ""
    use_type: str = ""
    seal_asset_id: int
    copies: int = Field(ge=1, le=999)
    print_quantity: int | None = Field(default=None, ge=1, le=999)
    remark: str = ""
    seal_types: list[str] = Field(default_factory=list)
    purpose: str
    use_date: date
    delivery_method: str = "现场用印"
    is_electronic_seal: bool = False
    is_offline_print: bool = False
    document_names: str = ""
    description: str = ""
    source_attachment_ids: list[int] = Field(default_factory=list)
    contract_file_ids: list[int] = Field(default_factory=list)
    case_file_ids: list[int] = Field(default_factory=list)


class SealPackageDownloadInput(BaseModel):
    application_ids: list[int] = Field(min_length=1, max_length=100)


class SealBatchApplicationInput(BaseModel):
    application_ids: list[int] = Field(min_length=1, max_length=100)
    comment: str = Field(default="", max_length=1000)


class SealApprovalInput(BaseModel):
    approved: bool
    comment: str = ""


class SealStampInput(BaseModel):
    actual_copies: int = Field(ge=1, le=999)
    operator: str = ""
    archive_no: str = ""
    comment: str = ""
    stamp_attachment_id: int | None = Field(default=None, gt=0)
    stamp_attachment_ids: list[int] = Field(default_factory=list, max_length=100)


class SealBatchStampInput(SealBatchApplicationInput):
    actual_copies: int = Field(ge=1, le=999)
    operator: str = ""
    archive_no: str = ""
    stamp_attachment_id: int | None = Field(default=None, gt=0)


class SealAssetInput(BaseModel):
    code: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=2, max_length=128)
    seal_type: str
    custodian: str
    location: str = ""
    remark: str = ""


class SealAssetUpdate(BaseModel):
    name: str | None = None
    seal_type: str | None = None
    custodian: str | None = None
    location: str | None = None
    status: str | None = None
    remark: str | None = None
