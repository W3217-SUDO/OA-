"""ipr 领域请求数据契约。"""

from datetime import date
from pydantic import BaseModel, Field, field_validator
from typing import Literal


class IprCaseCreateInput(BaseModel):
    case_kind: str = Field(min_length=2, max_length=8)
    # Keep the pre-existing patent/trademark kind as a separate dimension.
    # A patent or trademark matter can independently be a litigation matter.
    case_category: str = Field(default="non_litigation", pattern="^(litigation|non_litigation)$")
    title: str = Field(min_length=1, max_length=255)
    customer: str = Field(min_length=1, max_length=255)
    application_no: str = Field(default="", max_length=128)
    application_type: str = Field(default="", max_length=128)
    applicant: str = Field(default="", max_length=255)
    case_manager: str = Field(default="", max_length=128)
    application_date: date | None = None
    deadline: date | None = None
    annual_fee_year: int | None = Field(default=None, ge=1, le=100)
    rate: float | None = Field(default=None, ge=0, le=1)
    court_case_no: str = Field(default="", max_length=128)
    court_name: str = Field(default="", max_length=256)
    judge: str = Field(default="", max_length=128)
    clerk: str = Field(default="", max_length=128)
    plaintiff: str = Field(default="", max_length=256)
    defendant: str = Field(default="", max_length=256)
    third_parties: str = Field(default="", max_length=512)
    description: str = Field(default="", max_length=2000)


class IprCaseUpdateInput(BaseModel):
    case_category: str | None = Field(default=None, pattern="^(litigation|non_litigation)$")
    title: str | None = Field(default=None, min_length=1, max_length=255)
    application_no: str | None = Field(default=None, max_length=128)
    application_type: str | None = Field(default=None, max_length=128)
    applicant: str | None = Field(default=None, max_length=255)
    case_manager: str | None = Field(default=None, max_length=128)
    application_date: date | None = None
    deadline: date | None = None
    annual_fee_year: int | None = Field(default=None, ge=1, le=100)
    rate: float | None = Field(default=None, ge=0, le=1)
    case_phase: str | None = Field(default=None, max_length=128)
    acceptance_date: date | None = None
    case_source: str | None = Field(default=None, max_length=255)
    source_date: date | None = None
    agent: str | None = Field(default=None, max_length=255)
    writer: str | None = Field(default=None, max_length=255)
    submitter: str | None = Field(default=None, max_length=255)
    inventor: str | None = Field(default=None, max_length=255)
    contract_record_id: int | None = Field(default=None, gt=0)
    court_case_no: str | None = Field(default=None, max_length=128)
    court_name: str | None = Field(default=None, max_length=256)
    judge: str | None = Field(default=None, max_length=128)
    clerk: str | None = Field(default=None, max_length=128)
    plaintiff: str | None = Field(default=None, max_length=256)
    defendant: str | None = Field(default=None, max_length=256)
    third_parties: str | None = Field(default=None, max_length=512)
    description: str | None = Field(default=None, max_length=2000)


class IprLitigationCourtInfoInput(BaseModel):
    court_case_no: str = Field(default="", max_length=128)
    court_name: str = Field(default="", max_length=256)
    judge: str = Field(default="", max_length=128)
    clerk: str = Field(default="", max_length=128)
    plaintiff: str = Field(default="", max_length=256)
    defendant: str = Field(default="", max_length=256)
    third_parties: str = Field(default="", max_length=512)


class IprLitigationCourtInput(BaseModel):
    court_level: str = Field(default="一审", pattern="^(一审|二审|执行|再审)$")
    court_name: str = Field(min_length=1, max_length=256)
    case_no: str = Field(default="", max_length=128)
    judge: str = Field(default="", max_length=128)
    clerk: str = Field(default="", max_length=128)
    courtroom: str = Field(default="", max_length=128)
    filing_date: date | None = None
    hearing_date: date | None = None
    remark: str = Field(default="", max_length=1000)


class IprLitigationPartyInput(BaseModel):
    party_type: str = Field(pattern="^(原告|被告|第三人)$")
    name: str = Field(min_length=1, max_length=256)
    contact_name: str = Field(default="", max_length=128)
    contact_phone: str = Field(default="", max_length=64)
    address: str = Field(default="", max_length=512)
    remark: str = Field(default="", max_length=1000)


class IprCaseFeeActionInput(BaseModel):
    comment: str = Field(default="", max_length=1000)


class IprCaseFeeArrivalInput(BaseModel):
    received_date: date
    amount: float = Field(gt=0)
    payer_name: str = Field(min_length=2, max_length=255)
    bank_reference: str = Field(min_length=2, max_length=128)
    remark: str = Field(default="", max_length=1000)


class IprCaseFeeCreateInput(BaseModel):
    title: str = Field(default="", max_length=255)
    customer: str = Field(default="", max_length=255)
    amount: float
    fee_type: str = Field(min_length=1, max_length=64)
    expense_scope: str | None = Field(default=None, pattern="^(律所|平台|内部)$")
    expense_subtype: str | None = Field(default=None, pattern="^(官费|检索费|公告费|担保费|鉴定费|公证服务费|第三方费用|律师代理费|律师咨询费|律师培训费|律师见证费|代理费|平台代理费|案源介绍费|权利人赔偿款|投资人分成|其他费用|内部费用)$")
    handler: str = Field(default="", max_length=64)
    court: str = Field(default="", max_length=255)
    document_no: str = Field(default="", max_length=128)
    payee: str = Field(default="", max_length=255)
    description: str = Field(default="", max_length=2000)
    contract_record_id: int | None = Field(default=None, gt=0)
    fee_date: date | None = None


class IprCaseFeeInvoiceInput(BaseModel):
    customer: str = Field(min_length=1, max_length=255)
    amount: float = Field(gt=0)
    invoice_title: str = Field(min_length=1, max_length=255)
    taxpayer_id: str = Field(min_length=1, max_length=128)
    invoice_phone: str = Field(default="", max_length=64)
    bank_account: str = Field(default="", max_length=128)
    bank_name: str = Field(default="", max_length=255)
    invoice_address: str = Field(default="", max_length=255)
    extra_amount: float = Field(default=0, ge=0)
    invoice_type: str = Field(default="增值税普通发票", max_length=64)
    invoice_content: str = Field(default="法律服务费", max_length=128)
    delivery_method: str = Field(default="电子发票", max_length=64)
    recipient: str = Field(default="", max_length=255)
    recipient_phone: str = Field(default="", max_length=64)
    email: str = Field(default="", max_length=255)
    delivery_address: str = Field(default="", max_length=255)
    remark: str = Field(default="", max_length=1000)
    contract_record_id: int | None = Field(default=None, gt=0)


class IprCaseFeePaymentApplicationInput(BaseModel):
    payment_type_id: int = Field(gt=0)
    application_date: date
    remark: str = Field(default="", max_length=1000)


class IprCaseCrossModuleLinkInput(BaseModel):
    contract_record_id: int | None = Field(default=None, gt=0)
    payment_record_id: int | None = Field(default=None, gt=0)


class IprCaseMaintenanceInput(BaseModel):
    deadline: date | None = None
    annual_fee_year: int | None = Field(default=None, ge=1, le=100)
    rate: float | None = Field(default=None, ge=0, le=1)
    comment: str = Field(default="", max_length=1000)


class IprCaseBatchMaintenanceInput(BaseModel):
    case_ids: list[int] = Field(min_length=1, max_length=100)
    case_manager: str | None = Field(default=None, max_length=128)
    deadline: date | None = None
    annual_fee_year: int | None = Field(default=None, ge=1, le=100)
    rate: float | None = Field(default=None, ge=0, le=1)
    comment: str = Field(default="", max_length=1000)


class IprCaseBatchCreateRow(BaseModel):
    """One editable row from legacy MultiCreate's case grid."""

    case_type: str = Field(default="", max_length=128)
    case_phase: str = Field(default="", max_length=128)
    case_register_date: str = Field(default="", max_length=32)
    deadline: str = Field(default="", max_length=32)
    title: str = Field(default="", max_length=255)
    application_no: str = Field(default="", max_length=128)
    application_type: str = Field(default="", max_length=128)
    applicant: str = Field(default="", max_length=255)
    description: str = Field(default="", max_length=2000)


class IprCaseBatchCreateInput(BaseModel):
    customer: str = Field(min_length=1, max_length=255)
    case_kind: str = Field(min_length=2, max_length=8)
    rows: list[IprCaseBatchCreateRow] = Field(min_length=1, max_length=100)


class IprCaseRebootInput(BaseModel):
    reason: str = Field(default="", max_length=1000)


class IprCaseAnnualFeeMonitoringInput(BaseModel):
    """Legacy CaseAddInAFM / CaseRemoveAFM batch targets."""
    case_ids: list[int] = Field(min_length=1, max_length=100)
    comment: str = Field(default="", max_length=1000)


class IprCaseLogInput(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class IprCaseReviewInput(BaseModel):
    approved: bool
    comment: str = Field(default="", max_length=1000)


class IprCaseLifecycleInput(BaseModel):
    comment: str = Field(default="", max_length=1000)


class IprCaseLawFirmReplaceInput(BaseModel):
    law_firm_ids: list[int] = Field(default_factory=list, max_length=100)


class IprCaseCustomerReplaceInput(BaseModel):
    customer_ids: list[int] = Field(min_length=1, max_length=100)
    primary_customer_id: int = Field(gt=0)


class IprCaseCustomerContactReplaceInput(BaseModel):
    customer_id: int = Field(gt=0)
    document_contact_ids: list[str] = Field(default_factory=list, max_length=100)
    technology_contact_ids: list[str] = Field(default_factory=list, max_length=100)


class IprCaseAssistedFeeCreateInput(BaseModel):
    assisted_type: str = Field(min_length=1, max_length=128)
    remark: str = Field(default="", max_length=1000)

    @field_validator("assisted_type")
    @classmethod
    def assisted_type_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("协助类别不能为空")
        return value


class IprCaseAssistedFeeUpdateInput(BaseModel):
    assisted_type: str = Field(min_length=1, max_length=128)
    remark: str = Field(default="", max_length=1000)

    @field_validator("assisted_type")
    @classmethod
    def assisted_type_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("协助类别不能为空")
        return value


class IprCaseAssistedFeeConfirmInput(BaseModel):
    remark: str = Field(default="", max_length=1000)


class IprCaseAnnualFeeCreateInput(BaseModel):
    """Annual-fee year is a Gregorian payment year, never the legacy year sequence."""

    fee_year: int = Field(ge=2000, le=2100)
    fee_name: str = Field(min_length=1, max_length=255)
    amount: float = Field(ge=0, le=999999999999.99)
    currency: str = Field(default="CNY", min_length=3, max_length=8)
    due_date: date
    paid_date: date | None = None
    status: Literal["待缴", "已缴", "未缴"] = "待缴"
    reminder_date: date | None = None
    notes: str = Field(default="", max_length=2000)


class IprCaseAnnualFeeUpdateInput(BaseModel):
    fee_year: int | None = Field(default=None, ge=2000, le=2100)
    fee_name: str | None = Field(default=None, min_length=1, max_length=255)
    amount: float | None = Field(default=None, ge=0, le=999999999999.99)
    currency: str | None = Field(default=None, min_length=3, max_length=8)
    due_date: date | None = None
    paid_date: date | None = None
    status: Literal["待缴", "已缴", "未缴"] | None = None
    reminder_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)


class IprCaseReminderInput(BaseModel):
    event_type_id: int = Field(default=0, ge=0)
    reminder_date: date | None = None
    event_date: date | None = None
    deadline: date
    content: str = Field(min_length=1, max_length=1000)


class IprCaseReminderUpdate(BaseModel):
    event_type_id: int | None = Field(default=None, ge=0)
    reminder_date: date | None = None
    event_date: date | None = None
    deadline: date | None = None
    content: str | None = Field(default=None, min_length=1, max_length=1000)


class IprCaseReminderSuppressionInput(BaseModel):
    event_type_ids: list[int] = Field(default_factory=list, max_length=24)


class IprCaseReminderTypeQueryInput(BaseModel):
    """Structured successor to legacy Case_ReminderType.QueryObject."""

    case_kind: str = Field(default="", max_length=16)
    case_type: str = Field(default="", max_length=128)
    case_phase: str = Field(default="", max_length=128)
    statuses: list[str] = Field(default_factory=list, max_length=20)
    event_type_ids: list[int] = Field(default_factory=list, max_length=24)
    annual_fee_monitoring: bool | None = None
    deadline_from: date | None = None
    deadline_to: date | None = None
    deadline_within_days: int | None = Field(default=None, ge=0, le=3650)

    @field_validator("deadline_from", "deadline_to", mode="before")
    @classmethod
    def normalize_empty_deadline(cls, value):
        return None if value == "" else value


class IprCaseReminderTypeInput(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    query_object: IprCaseReminderTypeQueryInput = Field(default_factory=IprCaseReminderTypeQueryInput)
    is_default: bool = False
    is_active: bool = True
    sort_order: int = Field(default=0, ge=0, le=100000)


class IprCaseReminderTypeUpdateInput(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    query_object: IprCaseReminderTypeQueryInput | None = None
    is_default: bool | None = None
    is_active: bool | None = None
    sort_order: int | None = Field(default=None, ge=0, le=100000)


class IprCaseWarningRuleInput(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    case_kind: str = Field(default="", max_length=16)
    case_type: str = Field(default="", max_length=128)
    case_phase: str = Field(default="", max_length=128)
    time_node: str = Field(default="case_deadline", max_length=32)
    event_type_id: int = Field(default=0, ge=0)
    days_before: int = Field(default=0, ge=0, le=3650)
    is_active: bool = True


class IprCaseWarningRuleUpdateInput(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    case_kind: str | None = Field(default=None, max_length=16)
    case_type: str | None = Field(default=None, max_length=128)
    case_phase: str | None = Field(default=None, max_length=128)
    time_node: str | None = Field(default=None, max_length=32)
    event_type_id: int | None = Field(default=None, ge=0)
    days_before: int | None = Field(default=None, ge=0, le=3650)
    is_active: bool | None = None


class IprCaseWarningProcessInput(BaseModel):
    comment: str = Field(default="", max_length=1000)


class IprCaseFileTransmitInput(BaseModel):
    comment: str = Field(default="", max_length=1000)


class IprCaseFileBatchTransmitInput(IprCaseFileTransmitInput):
    attachment_ids: list[int] = Field(min_length=1, max_length=100)


class IprOfficialFileActionInput(BaseModel):
    comment: str = Field(default="", max_length=1000)


class IprOfficialFileBatchActionInput(IprOfficialFileActionInput):
    official_ids: list[int] = Field(min_length=1, max_length=100)


class IprOfficialCandidateMatchInput(BaseModel):
    ipr_case_id: int = Field(gt=0)
    comment: str = Field(default="", max_length=1000)


class IprOfficialCandidateCorrectInput(BaseModel):
    application_no: str | None = Field(default=None, max_length=128)
    official_type: str | None = Field(default=None, max_length=255)
    official_no: str | None = Field(default=None, max_length=128)
    received_date: date | None = None
    due_date: date | None = None
    comment: str = Field(default="", max_length=1000)


class IprOfficialCandidateConfirmInput(BaseModel):
    candidate_ids: list[int] = Field(min_length=1, max_length=100)
    comment: str = Field(default="", max_length=1000)


class IprCaseFileCustomCandidateMatchInput(BaseModel):
    ipr_case_id: int = Field(gt=0)


class IprCaseFileCustomCandidateCorrectInput(BaseModel):
    file_type: str | None = Field(default=None, max_length=255)
    document_date: date | None = None
    case_officer: str | None = Field(default=None, max_length=64)
    fee_amount: float | None = Field(default=None, ge=0, le=999999999)
    fee_type: str | None = Field(default=None, max_length=128)
    fee_response_user: str | None = Field(default=None, max_length=64)


class IprCaseFileCustomCandidateConfirmInput(BaseModel):
    candidate_ids: list[int] = Field(min_length=1, max_length=100)
    comment: str = Field(default="", max_length=1000)


class IprOfficialDualStatusInput(BaseModel):
    status: str = Field(min_length=2, max_length=16)
    comment: str = Field(default="", max_length=1000)
