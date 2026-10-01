"""warehouse 领域请求数据契约。"""

from datetime import date
from pydantic import BaseModel, Field


class WarehouseBorrowInput(BaseModel):
    borrower: str = Field(min_length=1, max_length=64)
    due_date: date
    purpose: str = ""
    comment: str = ""


class WarehouseReturnInput(BaseModel):
    comment: str = ""


class WarehouseReturnConfirmInput(BaseModel):
    condition: str = Field(default="完好", min_length=1, max_length=64)
    location: str = ""
    comment: str = ""


class WarehouseScrapInput(BaseModel):
    reason: str = Field(min_length=2, max_length=1000)


class WarehouseGoodsListSearchCondition(BaseModel):
    PageNo: int = Field(default=1, ge=0)
    PageSize: int = Field(default=15, ge=0, le=200)
    SerialNo: str = ""
    Name: str = ""
    WareHouseNo: str = ""
    DepositAddress: str = ""
    ClueNo: str = ""
    CaseNo: str = ""
    EvidenceNo: str = ""


class WarehouseGoodsListInput(BaseModel):
    SearchCondition: WarehouseGoodsListSearchCondition = WarehouseGoodsListSearchCondition()


class WarehouseEvidenceInput(BaseModel):
    serial_no: str = Field(min_length=1, max_length=128)
    warehouse_id: int | None = Field(default=None, gt=0)
    storage_location_id: int | None = Field(default=None, gt=0)
    # Kept only for callers on the previous API contract. The service resolves
    # these values to master data and never persists a free-text location.
    warehouse: str = Field(default="", max_length=128)
    location: str = Field(default="", max_length=128)
    notary_no: str = Field(default="", max_length=128)
    case_no: str = Field(default="", max_length=128)
    shop_name: str = Field(min_length=1, max_length=255)
    investigator: str = Field(min_length=1, max_length=128)
    notary_office: str = Field(default="", max_length=255)
    rights_holder: str = Field(min_length=1, max_length=255)
    evidence_date: date
    description: str = Field(default="", max_length=1000)


class WarehouseEvidenceCheckInInput(BaseModel):
    warehouse_id: int | None = Field(default=None, gt=0)
    storage_location_id: int | None = Field(default=None, gt=0)
    warehouse: str = Field(default="", max_length=128)
    location: str = Field(default="", max_length=128)
    comment: str = Field(default="", max_length=1000)


class WarehouseEvidenceCheckOutInput(BaseModel):
    recipient: str = Field(min_length=1, max_length=128)
    purpose: str = Field(min_length=1, max_length=500)
    comment: str = Field(default="", max_length=1000)


class WarehouseEvidenceRecheckInInput(BaseModel):
    warehouse_id: int | None = Field(default=None, gt=0)
    storage_location_id: int | None = Field(default=None, gt=0)
    warehouse: str = Field(default="", max_length=128)
    location: str = Field(default="", max_length=128)
    condition: str = Field(default="完好", min_length=1, max_length=128)
    comment: str = Field(default="", max_length=1000)


class WarehouseEvidenceDestroyInput(BaseModel):
    reason: str = Field(min_length=2, max_length=1000)


class EvidenceCreateInput(BaseModel):
    title: str
    owner: str
    source: str = "调查取证"
    description: str = ""
    notarization_no: str = Field(default="", max_length=128)
    invoice_no: str = Field(default="", max_length=128)
    storage_location: str = Field(default="", max_length=255)
    storage_state: str = Field(default="待整理", max_length=32)
    evidence_file_ids: list[int] = Field(default_factory=list, max_length=100)


class EvidenceRegistrationItem(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    owner: str = Field(default="", max_length=128)
    source: str = Field(default="调查取证", max_length=64)
    description: str = Field(default="", max_length=2000)
    clue_id: int | None = Field(default=None, gt=0)
    notarization_no: str = Field(default="", max_length=128)
    invoice_no: str = Field(default="", max_length=128)
    storage_location: str = Field(default="", max_length=255)
    storage_state: str = Field(default="待整理", max_length=32)
    evidence_file_ids: list[int] = Field(default_factory=list, max_length=100)


class EvidenceBatchRegistrationInput(BaseModel):
    items: list[EvidenceRegistrationItem] = Field(min_length=1, max_length=200)


class EvidenceUpdateInput(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    owner: str | None = Field(default=None, max_length=128)
    source: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=2000)
    notarization_no: str | None = Field(default=None, max_length=128)
    invoice_no: str | None = Field(default=None, max_length=128)
    storage_location: str | None = Field(default=None, max_length=255)
    storage_state: str | None = Field(default=None, max_length=32)
    notary_institution: str | None = Field(default=None, max_length=255)
    collected_at: date | None = None
    certificate_no: str | None = Field(default=None, max_length=128)
    evidence_status: str | None = Field(default=None, max_length=32)
