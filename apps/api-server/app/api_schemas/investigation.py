"""investigation 领域请求数据契约。"""

from datetime import date
from pydantic import BaseModel, Field


class NotaryReviewInput(BaseModel):
    approved: bool
    comment: str = ""
    case_type: str = "民事案件"
    court: str = ""


class ClueReviewInput(BaseModel):
    approved: bool
    comment: str = Field(min_length=2, max_length=1000)
    suspected_conflict_clue_nos: list[str] = Field(default_factory=list, max_length=100)
    suspected_conflict_case_nos: list[str] = Field(default_factory=list, max_length=100)
    supplement_evidence: str = Field(default="", max_length=2000)
    merge_into_case_no: str = Field(default="", max_length=64)


class ClueCollectionInput(BaseModel):
    collected_at: date
    notary_institution: str = Field(min_length=2, max_length=255)
    notarization_no: str = Field(default="", max_length=128)
    invoice_no: str = Field(default="", max_length=128)
    storage_location: str = Field(default="", max_length=255)
    warehouse_id: int | None = Field(default=None, gt=0)
    storage_location_id: int | None = Field(default=None, gt=0)
    evidence_status: str = Field(default="未入库", max_length=32)
    evidence_file_ids: list[int] = Field(default_factory=list, max_length=100)
    comment: str = ""


class ClueBatchCollectionInput(ClueCollectionInput):
    clue_ids: list[int] = Field(min_length=2, max_length=200)


class InvestigationPartyInput(BaseModel):
    producers: list[dict] = Field(default_factory=list, max_length=100)
    indictees: list[dict] = Field(default_factory=list, max_length=100)


class NotaryCertificateInput(BaseModel):
    certificate_no: str = Field(min_length=2, max_length=128)
    issued_date: date
    storage_location: str = Field(default="", max_length=255)
    warehouse_id: int | None = Field(default=None, gt=0)
    storage_location_id: int | None = Field(default=None, gt=0)
    physical_received: bool = False
    comment: str = ""


class InvestigationTaskInput(BaseModel):
    title: str
    owner: str
    deadline: date
    start_date: date | None = None
    end_date: date | None = None
    province: str = Field(default="", max_length=100)
    city: str = Field(default="", max_length=100)
    district: str = Field(default="", max_length=100)
    investigation_regions: list[list[str]] | None = Field(default=None, min_length=1, max_length=500)
    priority: str = "普通"
    parent_task_id: int | None = None
    contract_record_id: int | None = Field(default=None, gt=0)
    description: str = ""
    contract_no: str = Field(default="", max_length=64)
    contract_name: str = Field(default="", max_length=255)
    authorization_scope: str = Field(default="", max_length=1000)
    attachment_ids: list[int] = Field(default_factory=list, max_length=100)


class BatchClueCaseInput(BaseModel):
    clue_ids: list[int] = Field(min_length=1, max_length=100)
    # Contracts are resolved from the source investigation task.  Keeping this
    # optional preserves compatibility with callers that sent the old field,
    # while preventing the UI from binding an unrelated contract by hand.
    contract_record_id: int | None = None
    case_type: str = "民事案件"
    court: str = ""
    client_position: str = Field(default="原告", max_length=64)
    cause_or_charge: str = Field(default="", max_length=255)
    case_phase: str = Field(default="新案待分配", max_length=64)
    handling_lawyer: str = Field(default="system", max_length=128)
    assistant: str = Field(default="", max_length=128)


class ClueCaseContractResolveInput(BaseModel):
    clue_ids: list[int] = Field(min_length=1, max_length=100)


class ClueSourceContractBindingInput(BaseModel):
    contract_record_id: int = Field(gt=0)


class InvestigationAssignmentInput(BaseModel):
    investigator: str = Field(min_length=1, max_length=128)
    comment: str = ""


class InvestigationBatchDeleteInput(BaseModel):
    record_ids: list[int] = Field(min_length=1, max_length=100)
    comment: str = ""


class InvestigationFeeInput(BaseModel):
    amount: float = Field(gt=0, le=100000000)
    fee_type: str = Field(min_length=1, max_length=64)
    description: str = ""


class ClueBatchSubmitInput(BaseModel):
    clue_ids: list[int] = Field(min_length=1, max_length=100)
    comment: str = Field(default="", max_length=1000)


class ClueTurnOnAuditInput(BaseModel):
    reviewer: str = Field(min_length=1, max_length=128)
    comment: str = Field(default="", max_length=1000)
