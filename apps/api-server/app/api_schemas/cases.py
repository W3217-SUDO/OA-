"""cases 领域请求数据契约。"""

from datetime import date, datetime
from pydantic import BaseModel, Field, field_validator
from typing import Literal


class CaseAssignmentInput(BaseModel):
    customer_manager: str = ""
    hearing_lawyer: str
    handling_lawyers: list[str] = Field(default_factory=list)
    assistant: str = ""
    comment: str = ""


class CaseHearingLawyerInput(BaseModel):
    hearing_lawyer: str = Field(min_length=1, max_length=128)
    comment: str = Field(default="", max_length=500)


class CaseBatchDeleteInput(BaseModel):
    case_ids: list[int] = Field(min_length=1, max_length=200)

    @field_validator("case_ids")
    @classmethod
    def validate_case_ids(cls, value: list[int]) -> list[int]:
        if any(case_id <= 0 for case_id in value) or len(set(value)) != len(value):
            raise ValueError("案件 ID 必须为正整数且不能重复")
        return value


class CaseBatchUpdateInput(BaseModel):
    case_ids: list[int] = Field(default_factory=list, max_length=100)
    case_nos: list[str] = Field(default_factory=list, max_length=100)
    hearing_lawyer: str | None = Field(default=None, max_length=128)
    handling_lawyers: list[str] | None = Field(default=None, max_length=20)
    assistant: str | None = Field(default=None, max_length=128)
    case_stage: str | None = Field(default=None, max_length=128)
    source_lawyer: str | None = Field(default=None, max_length=128)
    litigation_amount: float | None = Field(default=None, ge=0, le=1000000000)
    comment: str = Field(default="", max_length=500)


class CaseMergeInput(BaseModel):
    source_case_no: str = Field(min_length=1, max_length=64)
    comment: str = Field(default="", max_length=1000)


class CaseNotaryInfoInput(BaseModel):
    notary_nos: str = Field(min_length=1, max_length=1000)
    warehouse_location_ids: list[int] = Field(min_length=1, max_length=50)
    comment: str = Field(default="", max_length=1000)


class CaseSettlementAmountInput(BaseModel):
    litigation_amount: float = Field(ge=0, le=1000000000)
    settlement_amount: float = Field(ge=0, le=1000000000)
    comment: str = Field(default="", max_length=1000)


class CaseReminderInput(BaseModel):
    reminder_date: date
    deadline: date
    content: str = Field(min_length=1, max_length=1000)


class CaseEventInput(BaseModel):
    event_type_id: int = Field(default=0, ge=0)
    event_type: str = Field(min_length=1, max_length=128)
    event_time: datetime
    content: str = Field(min_length=1, max_length=500)
    deadline: date | None = None
    reminder_enabled: bool = False
    remind_at: datetime | None = None


class CaseEventUpdateInput(BaseModel):
    event_type_id: int | None = Field(default=None, ge=0)
    event_type: str | None = Field(default=None, min_length=1, max_length=128)
    event_time: datetime | None = None
    content: str | None = Field(default=None, min_length=1, max_length=500)
    deadline: date | None = None
    reminder_enabled: bool | None = None
    remind_at: datetime | None = None
    status: Literal["待处理", "已完成"] | None = None


class CaseEventBatchDeleteInput(BaseModel):
    event_ids: list[int] = Field(min_length=1, max_length=100)


class CaseLogInput(BaseModel):
    content: str = Field(min_length=1, max_length=1000)
    kind: Literal["case", "refund"] = "case"
    case_fee_id: int | None = Field(default=None, ge=1)


class CaseProgressInput(BaseModel):
    first_instance_court: str = ""
    first_instance_case_no: str = ""
    courtroom: str = ""
    judge: str = ""
    clerk: str = ""
    judgment_date: date | None = None
    judgment_document_no: str = ""
    second_instance_court: str = ""
    second_instance_case_no: str = ""
    first_court_name: str = ""
    first_court_case_no: str = ""
    first_court_courtroom: str = ""
    first_court_judge: str = ""
    first_court_clerk: str = ""
    first_court_filing_date: date | None = None
    first_court_hearing_date: datetime | None = None
    first_court_judgment_date: date | None = None
    second_court_name: str = ""
    second_court_case_no: str = ""
    second_court_courtroom: str = ""
    second_court_judge: str = ""
    second_court_clerk: str = ""
    second_court_filing_date: date | None = None
    second_court_hearing_date: datetime | None = None
    second_court_judgment_date: date | None = None
    execution_court_name: str = ""
    execution_court_case_no: str = ""
    execution_court_courtroom: str = ""
    execution_court_judge: str = ""
    execution_court_clerk: str = ""
    execution_court_filing_date: date | None = None
    execution_court_hearing_date: datetime | None = None
    execution_court_judgment_date: date | None = None
    retrial_court_name: str = ""
    retrial_court_case_no: str = ""
    retrial_court_courtroom: str = ""
    retrial_court_judge: str = ""
    retrial_court_clerk: str = ""
    retrial_court_filing_date: date | None = None
    retrial_court_hearing_date: datetime | None = None
    retrial_court_judgment_date: date | None = None
    comment: str = ""


class CaseCourtInfoInput(CaseProgressInput):
    """The detail-page court dialog may only update court information.

    It deliberately has the same typed court fields as the legacy dialog, but
    is handled by a separate endpoint so it cannot advance a case or inherit
    the case-creation approval gate used by litigation-progress registration.
    """


class CaseExecutionStatusInput(BaseModel):
    # The legacy dialog submits one comma-separated caseNos string; accepting
    # a list as well keeps direct API clients compatible with the local UI.
    case_nos: str | list[str] = Field(default="", max_length=6400)
    execution_status: str = Field(default="", max_length=64)
    comment: str = Field(default="", max_length=1000)


class CasePhaseChangeInput(BaseModel):
    case_nos: str | list[str] = Field(default="", max_length=6400)
    case_phase_id: int | None = Field(default=None, gt=0)
    case_phase_name: str = Field(default="", max_length=128)
    comment: str = Field(default="", max_length=1000)


class CaseCreateInput(BaseModel):
    contract_record_id: int = Field(gt=0)
    customer_record_id: int | None = Field(default=None, gt=0)
    customer_id: int | None = Field(default=None, gt=0)
    customer_no: str = Field(default="", max_length=128)
    customer: str = Field(default="", max_length=256)
    serial_no: str = Field(default="", max_length=64)
    title: str = Field(min_length=1, max_length=256)
    status: str = "新案待分配"
    owner: str = Field(default="", max_length=128)
    case_type: str = Field(default="刑事案件", min_length=1, max_length=64)
    opponent: str = ""
    court: str = ""
    client_position: str = ""
    cause_or_charge: str = Field(default="", max_length=256)
    right_type: str = ""
    counsel_type: str = ""
    counsel_start: date | None = None
    counsel_end: date | None = None
    handling_lawyers: list[str] = Field(default_factory=list, max_length=20)
    source_person: str = Field(default="", max_length=128)
    assistant: str = ""
    investigator: str = ""
    investigation_clue: str = ""
    party_type: str = ""
    party_id_type: str = ""
    party_id_no: str = ""
    party_contact: str = ""
    party_phone: str = ""
    party_address: str = ""
    legal_representative: str = ""
    party_remark: str = ""
    court_case_no: str = ""
    judge: str = ""
    judge_phone: str = ""
    filing_date: date | None = None
    hearing_date: date | None = None
    hearing_time: str = ""
    courtroom: str = ""
    judicial_remark: str = ""
    description: str = ""


class CaseLitigantAgentInput(BaseModel):
    """A case-specific litigation representative; it is not a staff account."""
    name: str = Field(min_length=1, max_length=256)
    law_firm: str = Field(default="", max_length=256)
    position: str = Field(default="", max_length=128)
    phone: str = Field(default="", max_length=64)
    authority: str = Field(default="", max_length=500)


class CasePartyIdentityInput(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    organization_type: str = Field(min_length=1, max_length=32)
    identity_no: str = Field(min_length=1, max_length=64)


class CaseLitigantsInput(BaseModel):
    plaintiffs: list[str] = Field(default_factory=list, max_length=50)
    plaintiff_identities: list[CasePartyIdentityInput] = Field(default_factory=list, max_length=50)
    # Strings remain accepted for historical case JSON and existing callers.
    plaintiff_agents: list[CaseLitigantAgentInput | str] = Field(default_factory=list, max_length=50)
    defendants: list[str] = Field(default_factory=list, max_length=50)
    defendant_identities: list[CasePartyIdentityInput] = Field(default_factory=list, max_length=50)
    defendant_agents: list[CaseLitigantAgentInput | str] = Field(default_factory=list, max_length=50)
    third_parties: list[str] = Field(default_factory=list, max_length=50)
    third_party_identities: list[CasePartyIdentityInput] = Field(default_factory=list, max_length=50)
    third_party_agents: list[CaseLitigantAgentInput | str] = Field(default_factory=list, max_length=50)
    comment: str = Field(default="", max_length=500)


class CaseCreationCompleteInput(BaseModel):
    comment: str = Field(default="", max_length=500)


class CaseCounselBasicInput(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    counsel_type: str = Field(min_length=1, max_length=128)
    counsel_start: date
    counsel_end: date
    handling_lawyers: list[str] = Field(min_length=1, max_length=20)
    assistant: str = Field(default="", max_length=128)
    comment: str = Field(default="", max_length=500)


class CaseNormalBasicInput(BaseModel):
    """Old-system type-specific basic-information editor for ordinary cases.

    This deliberately does not reuse the legal-counsel endpoint: ordinary cases
    have a case phase, cause/charge and clue/investigator fields instead.
    """
    customer_record_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=256)
    case_phase: str = Field(min_length=1, max_length=64)
    cause_or_charge: str = Field(min_length=1, max_length=256)
    handling_lawyers: list[str] = Field(min_length=1, max_length=20)
    assistant: str = Field(default="", max_length=128)
    assistants: list[str] | None = Field(default=None, max_length=20)
    business_owner: str = Field(default="", max_length=128)
    investigator: str = Field(default="", max_length=128)
    investigation_clue_ids: list[int] = Field(default_factory=list, max_length=50)
    right_type: str = Field(default="", max_length=128)
    source_person: str = Field(default="", max_length=128)
    comment: str = Field(default="", max_length=500)


class CaseArbitrationBasicInput(BaseModel):
    """Dedicated legacy arbitration basic-information branch (not normal/counsel)."""
    customer_record_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=256)
    case_phase: str = Field(min_length=1, max_length=64)
    cause_or_charge: str = Field(min_length=1, max_length=256)
    handling_lawyers: list[str] = Field(min_length=1, max_length=20)
    assistant: str = Field(default="", max_length=128)
    investigator: str = Field(default="", max_length=128)
    investigation_clue_ids: list[int] = Field(default_factory=list, max_length=50)
    comment: str = Field(default="", max_length=500)


class CriminalPublicSecurityMaintenanceInput(BaseModel):
    public_security_name: str = Field(default="", max_length=256)
    public_security_case_no: str = Field(default="", max_length=128)
    public_security_address: str = Field(default="", max_length=500)
    public_security_phone: str = Field(default="", max_length=64)
    public_security_operator: str = Field(default="", max_length=128)
    comment: str = Field(default="", max_length=500)


class CriminalProcuratorateMaintenanceInput(BaseModel):
    first_procuratorate_name: str = Field(default="", max_length=256); first_procuratorate_case_no: str = Field(default="", max_length=128); first_procuratorate_address: str = Field(default="", max_length=500); first_procuratorate_phone: str = Field(default="", max_length=64); first_procuratorate_operator: str = Field(default="", max_length=128)
    second_procuratorate_name: str = Field(default="", max_length=256); second_procuratorate_case_no: str = Field(default="", max_length=128); second_procuratorate_address: str = Field(default="", max_length=500); second_procuratorate_phone: str = Field(default="", max_length=64); second_procuratorate_operator: str = Field(default="", max_length=128)
    retrial_procuratorate_name: str = Field(default="", max_length=256); retrial_procuratorate_case_no: str = Field(default="", max_length=128); retrial_procuratorate_address: str = Field(default="", max_length=500); retrial_procuratorate_phone: str = Field(default="", max_length=64); retrial_procuratorate_operator: str = Field(default="", max_length=128)
    comment: str = Field(default="", max_length=500)


class CriminalCourtMaintenanceInput(BaseModel):
    first_court_enabled: bool = False; first_court_name: str = Field(default="", max_length=256); first_court_case_no: str = Field(default="", max_length=128); first_court_courtroom: str = Field(default="", max_length=128); first_court_judge: str = Field(default="", max_length=128); first_court_clerk: str = Field(default="", max_length=128); first_court_filing_date: date | None = None; first_court_hearing_date: date | None = None
    second_court_enabled: bool = False; second_court_name: str = Field(default="", max_length=256); second_court_case_no: str = Field(default="", max_length=128); second_court_courtroom: str = Field(default="", max_length=128); second_court_judge: str = Field(default="", max_length=128); second_court_clerk: str = Field(default="", max_length=128); second_court_filing_date: date | None = None; second_court_hearing_date: date | None = None
    execution_court_enabled: bool = False; execution_court_name: str = Field(default="", max_length=256); execution_court_case_no: str = Field(default="", max_length=128); execution_court_courtroom: str = Field(default="", max_length=128); execution_court_judge: str = Field(default="", max_length=128); execution_court_clerk: str = Field(default="", max_length=128); execution_court_filing_date: date | None = None; execution_court_hearing_date: date | None = None
    retrial_court_enabled: bool = False; retrial_court_name: str = Field(default="", max_length=256); retrial_court_case_no: str = Field(default="", max_length=128); retrial_court_courtroom: str = Field(default="", max_length=128); retrial_court_judge: str = Field(default="", max_length=128); retrial_court_clerk: str = Field(default="", max_length=128); retrial_court_filing_date: date | None = None; retrial_court_hearing_date: date | None = None
    comment: str = Field(default="", max_length=500)


class CounselCaseSearchInput(BaseModel):
    scope: str = "company"
    case_queue: str = Field(default="", max_length=64)
    dashboard_queue: str = Field(default="", max_length=64)
    case_types: list[str] = Field(default_factory=list, max_length=20)
    case_type: str = Field(default="", max_length=128)
    customer_id: int | None = Field(default=None, gt=0)
    customer_no: str = Field(default="", max_length=128)
    customer: str = Field(default="", max_length=256)
    serial_no: str = Field(default="", max_length=128)
    keyword: str = Field(default="", max_length=256)
    # Ordinary CaseSearchCondition fields.  Keep them explicit so unknown
    # frontend keys cannot be silently discarded by the API.
    plaintiff: str = Field(default="", max_length=256)
    prosecutor: str = Field(default="", max_length=256)
    defendant: str = Field(default="", max_length=256)
    evidence_org: str = Field(default="", max_length=256)
    notary_no: str = Field(default="", max_length=128)
    hearing_lawyer: str = Field(default="", max_length=128)
    investigator: str = Field(default="", max_length=128)
    court: str = Field(default="", max_length=256)
    source_from: date | None = None
    source_to: date | None = None
    hearing_from: date | None = None
    hearing_to: date | None = None
    channel: str = Field(default="", max_length=128)
    warehouse: str = Field(default="", max_length=128)
    area: str = Field(default="", max_length=128)
    location: str = Field(default="", max_length=256)
    log_content: str = Field(default="", max_length=1000)
    counsel_start: date | None = None
    counsel_end: date | None = None
    counsel_type: str = Field(default="", max_length=128)
    case_status: str = Field(default="", max_length=64)
    case_statuses: list[str] = Field(default_factory=list, max_length=100)
    status: str = Field(default="", max_length=64)
    handling_lawyer: str = Field(default="", max_length=128)
    assistant: str = Field(default="", max_length=128)
    document_name: str = Field(default="", max_length=255)
    sort_order: str = "updated_desc"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=15, ge=1, le=200)
    selected_ids: list[int] = Field(default_factory=list, max_length=200)
    selected_only: bool = False
    # 旧 CaseSearchCondition 的资助/财务/文档高级条件。布尔 not 字段保留旧端的“排除”语义。
    advanced_logic: str = "and"
    assisted_response_user: str = Field(default="", max_length=128)
    assisted_response_user_not: bool = False
    assisted_request_date_from: date | None = None
    assisted_request_date_to: date | None = None
    assisted_request_date_not: bool = False
    assisted_response_date_from: date | None = None
    assisted_response_date_to: date | None = None
    assisted_response_date_not: bool = False
    finance_inform_date_from: date | None = None
    finance_inform_date_to: date | None = None
    finance_inform_date_not: bool = False
    finance_gained_date_from: date | None = None
    finance_gained_date_to: date | None = None
    finance_gained_date_not: bool = False
    finance_response_user: str = Field(default="", max_length=128)
    finance_response_user_not: bool = False
    finance_bill_no: str = Field(default="", max_length=128)
    finance_bill_no_not: bool = False
    finance_bill_statuses: list[str] = Field(default_factory=list, max_length=50)
    finance_bill_status_not: bool = False
    finance_bill_date_from: date | None = None
    finance_bill_date_to: date | None = None
    finance_bill_date_not: bool = False
    finance_fee_type_ids: list[str] = Field(default_factory=list, max_length=50)
    finance_fee_type_not: bool = False
    file_uploading_user: str = Field(default="", max_length=128)
    file_uploading_user_not: bool = False
    file_uploading_time_from: date | None = None
    file_uploading_time_to: date | None = None
    file_uploading_time_not: bool = False
    file_type_ids: list[str] = Field(default_factory=list, max_length=50)
    file_type_not: bool = False


class CaseJudicialInput(BaseModel):
    # 当前网页端使用的兼容法院字段。
    court: str = Field(default="", max_length=256)
    court_case_no: str = Field(default="", max_length=128)
    courtroom: str = Field(default="", max_length=128)
    judge: str = Field(default="", max_length=128)
    clerk: str = Field(default="", max_length=128)
    judge_phone: str = Field(default="", max_length=64)
    filing_date: date | None = None
    hearing_date: date | None = None
    hearing_time: str = Field(default="", max_length=8)
    judicial_remark: str = Field(default="", max_length=1000)
    description: str = Field(default="", max_length=4000)

    # 刑事案件原站脚本中出现的公安机关和三级检察院字段。
    public_security_name: str = Field(default="", max_length=256)
    public_security_case_no: str = Field(default="", max_length=128)
    public_security_address: str = Field(default="", max_length=500)
    public_security_phone: str = Field(default="", max_length=64)
    public_security_operator: str = Field(default="", max_length=128)
    first_procuratorate_name: str = Field(default="", max_length=256)
    first_procuratorate_case_no: str = Field(default="", max_length=128)
    first_procuratorate_address: str = Field(default="", max_length=500)
    first_procuratorate_phone: str = Field(default="", max_length=64)
    first_procuratorate_operator: str = Field(default="", max_length=128)
    second_procuratorate_name: str = Field(default="", max_length=256)
    second_procuratorate_case_no: str = Field(default="", max_length=128)
    second_procuratorate_address: str = Field(default="", max_length=500)
    second_procuratorate_phone: str = Field(default="", max_length=64)
    second_procuratorate_operator: str = Field(default="", max_length=128)
    retrial_procuratorate_name: str = Field(default="", max_length=256)
    retrial_procuratorate_case_no: str = Field(default="", max_length=128)
    retrial_procuratorate_address: str = Field(default="", max_length=500)
    retrial_procuratorate_phone: str = Field(default="", max_length=64)
    retrial_procuratorate_operator: str = Field(default="", max_length=128)

    # 原站法院页可勾选一审、二审和再审；字段分别保存，避免后续互相覆盖。
    first_court_enabled: bool = False
    first_court_name: str = Field(default="", max_length=256)
    first_court_case_no: str = Field(default="", max_length=128)
    first_court_courtroom: str = Field(default="", max_length=128)
    first_court_judge: str = Field(default="", max_length=128)
    first_court_clerk: str = Field(default="", max_length=128)
    first_court_filing_date: date | None = None
    first_court_hearing_date: date | None = None
    second_court_enabled: bool = False
    second_court_name: str = Field(default="", max_length=256)
    second_court_case_no: str = Field(default="", max_length=128)
    second_court_courtroom: str = Field(default="", max_length=128)
    second_court_judge: str = Field(default="", max_length=128)
    second_court_clerk: str = Field(default="", max_length=128)
    second_court_filing_date: date | None = None
    second_court_hearing_date: date | None = None
    retrial_court_enabled: bool = False
    retrial_court_name: str = Field(default="", max_length=256)
    retrial_court_case_no: str = Field(default="", max_length=128)
    retrial_court_courtroom: str = Field(default="", max_length=128)
    retrial_court_judge: str = Field(default="", max_length=128)
    retrial_court_clerk: str = Field(default="", max_length=128)
    retrial_court_filing_date: date | None = None
    retrial_court_hearing_date: date | None = None


class HearingInput(BaseModel):
    case_record_id: int
    hearing_date: date
    hearing_time: str
    court: str
    courtroom: str = ""
    hearing_type: str = "开庭"
    hearing_lawyer: str
    remark: str = ""


class ArchiveCheckInput(BaseModel):
    case_closed: bool = False
    fees_settled: bool = False
    documents_complete: bool = False
    finance_complete: bool = False
    archive_no: str = ""
    paper_archive_location: str = ""
    paper_volume_count: int = Field(default=1, ge=1, le=999)
    archive_type: str = "normal"
    comment: str = ""
    submit: bool = False


class ArchiveReviewInput(BaseModel):
    approved: bool
    comment: str = Field(min_length=2, max_length=1000)
    archive_no: str = Field(default="", max_length=100)


class CaseCreationReviewInput(BaseModel):
    approved: bool
    comment: str = Field(default="", max_length=1000)


class CaseUnarchiveRequestInput(BaseModel):
    reason: str = Field(min_length=2, max_length=1000)


class CaseUnarchiveReviewInput(BaseModel):
    approved: bool
    comment: str = Field(default="", max_length=1000)
