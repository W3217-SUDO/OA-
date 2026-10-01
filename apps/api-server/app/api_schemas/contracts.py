"""contracts 领域请求数据契约。"""

from datetime import date
from pydantic import BaseModel, Field, model_validator


class ContractAttachmentBatchDeleteInput(BaseModel):
    file_ids: list[int] = Field(default_factory=list, max_length=100)
    fileIds: list[int] = Field(default_factory=list, max_length=100)
    attachment_ids: list[int] = Field(default_factory=list, max_length=100)


class ContractWholeDeleteInput(BaseModel):
    """Legacy FCM ContractDelete body: accepts snake_case and camelCase ids."""
    contract_ids: list[int] = Field(default_factory=list, max_length=200)
    contractIds: list[int] = Field(default_factory=list, max_length=200)


class ContractSubmitInput(BaseModel):
    approvers: list[str] = Field(min_length=1, max_length=10)
    comment: str = ""
    sync_seal: bool = False


class ContractApproverSettingsInput(BaseModel):
    usernames: list[str] = Field(default_factory=list, max_length=200)


class ContractDraftInput(BaseModel):
    serial_no: str = Field(default="", max_length=128)
    title: str = Field(min_length=1, max_length=255)
    customer: str = Field(min_length=1, max_length=255)
    owner: str = Field(min_length=1, max_length=64)
    department: str = Field(min_length=1, max_length=64)
    staff_id: int | None = Field(default=None, gt=0)
    description: str = Field(default="", max_length=2000)
    data: dict = Field(default_factory=dict)


class ContractApprovalInput(BaseModel):
    approved: bool
    comment: str = ""
    action_key: str = Field(default="", max_length=128)


class ContractSealApplicationInput(BaseModel):
    approver: str = Field(min_length=1, max_length=100)
    seal_asset_id: int
    copies: int = Field(ge=1, le=999)
    purpose: str = Field(min_length=1, max_length=500)
    use_date: date
    delivery_method: str = "现场用印"
    document_names: str = ""
    source_attachment_ids: list[int] = Field(default_factory=list, max_length=100)
    description: str = ""
    submit: bool = False


class ContractInvestigationInput(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    owner: str = Field(default="", max_length=100)
    authorized_from: date
    authorized_to: date
    region: str = Field(default="", max_length=300)
    authorization_scope: str = Field(default="", max_length=1000)
    attachment_ids: list[int] = Field(default_factory=list, max_length=100)
    right_type: str = Field(default="商标", max_length=50)
    customer_review: bool = False
    description: str = Field(default="", max_length=2000)


class ContractChangeInput(BaseModel):
    change_type: str
    reason: str = Field(min_length=2, max_length=1000)
    contract_body: str | None = None
    contract_type: str | None = None
    fee_type: str | None = None
    title: str | None = None
    amount: float | None = Field(default=None, ge=0)
    description: str | None = None
    external_contract_no: str | None = None
    external_contract_numbers: list[str] | None = Field(default=None, max_length=50)
    end_date: date | None = None
    signed_at: date | None = None
    owner: str | None = Field(default=None, max_length=64)
    department: str | None = Field(default=None, max_length=128)


class ContractChangeReviewInput(BaseModel):
    approved: bool
    comment: str = Field(default="", max_length=1000)


class ContractEventInput(BaseModel):
    content: str = Field(min_length=1, max_length=1000)


class ContractObjectInput(BaseModel):
    case_record_id: int
    fee_type: str = Field(min_length=1, max_length=64)
    amount: float = Field(ge=0, le=999999999)
    remark: str = Field(default="", max_length=2000)


class ContractArchiveClosureInput(BaseModel):
    case_fee_ids: list[int] = Field(min_length=1, max_length=200)
    fee_archived: bool = True
    comment: str = Field(default="", max_length=1000)


class ContractPaymentLineInput(BaseModel):
    # Legacy contract payment screens select individual case-fee rows. Keep
    # contract_object_id for backwards compatibility, while allowing the
    # precise fee row to be submitted when available.
    contract_object_id: int | None = Field(default=None, gt=0)
    case_fee_id: int | None = Field(default=None, gt=0)
    amount: float = Field(gt=0, le=999999999)
    remark: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def require_target(self):
        if not self.contract_object_id and not self.case_fee_id:
            raise ValueError("必须选择合同标的或案件费用")
        return self


class ContractPaymentApplicationInput(BaseModel):
    payment_type_id: int = Field(gt=0)
    payer_name: str = Field(default="", max_length=200)
    application_date: date
    remark: str = Field(default="", max_length=2000)
    lines: list[ContractPaymentLineInput] = Field(min_length=1, max_length=100)


class ContractPaymentReviewInput(BaseModel):
    approved: bool
    comment: str = Field(default="", max_length=1000)


class ContractPaymentPayInput(BaseModel):
    paid_date: date
    voucher_no: str = Field(min_length=1, max_length=128)
    comment: str = Field(default="", max_length=1000)


class ContractPaymentWriteoffInput(BaseModel):
    writeoff_date: date
    voucher_no: str = Field(min_length=2, max_length=128)
    comment: str = Field(default="", max_length=1000)
