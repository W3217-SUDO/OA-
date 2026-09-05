"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from app.core.dependencies import (
    BaseModel, Field, Literal, date, datetime,
    field_validator,
)


class DifyRequest(BaseModel):
    query: str
    conversation_id: str | None = None


class CaseAgentProposedAction(BaseModel):
    type: str = Field(default="case.update", pattern=r"^(case\.update|case\.data\.update|case\.task\.create|case\.reminder\.create|customer\.update|contract\.update)$")
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


class RecordInput(BaseModel):
    module: str
    serial_no: str
    title: str
    customer: str = ""
    status: str = "草稿"
    owner: str = "管理者"
    department: str = "上海分所"
    description: str = ""
    data: dict = Field(default_factory=dict)


class RecordUpdate(BaseModel):
    title: str | None = None
    customer: str | None = None
    status: str | None = None
    owner: str | None = None
    department: str | None = None
    description: str | None = None
    data: dict | None = None


class TransitionInput(BaseModel):
    to_status: str
    comment: str = ""


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


class HrTransitionInput(BaseModel):
    to_status: str
    effective_date: date = Field(default_factory=date.today)
    reason: str = ""
    handover_to: str = ""
    comment: str = ""


class HrEmployeeBatchDeleteInput(BaseModel):
    employee_ids: list[int] = Field(min_length=1, max_length=100)


class HrSubrecordInput(BaseModel):
    kind: str = Field(pattern="^(leave|matter|commission)$")
    data: dict = Field(default_factory=dict)


class HrPerformanceInput(BaseModel):
    employee_id: int = Field(gt=0)
    data: dict = Field(default_factory=dict)


class HrSubrecordUpdate(BaseModel):
    data: dict


class DepartmentInput(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    parent_department_id: int | None = Field(default=None, ge=1)
    manager: str = Field(default="", max_length=64)
    overdue_deduction: bool = False
    sort_order: int = Field(default=0, ge=0, le=99999)
    is_active: bool = True


class DepartmentUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=128)
    parent_department_id: int | None = Field(default=None, ge=1)
    manager: str | None = Field(default=None, max_length=64)
    overdue_deduction: bool | None = None
    sort_order: int | None = Field(default=None, ge=0, le=99999)
    is_active: bool | None = None


class JobRoleInput(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    permissions: list[str] = Field(default_factory=list, max_length=50)
    field_keys: list[str] = Field(default_factory=list, max_length=50)
    field_keys_configured: bool = False
    data_scope: str | None = Field(default=None, max_length=64)
    description: str = Field(default="", max_length=1000)
    sort_order: int = Field(default=0, ge=0, le=99999)
    is_active: bool = True


class JobRoleUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=128)
    permissions: list[str] | None = Field(default=None, max_length=50)
    field_keys: list[str] | None = Field(default=None, max_length=50)
    field_keys_configured: bool | None = None
    data_scope: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=1000)
    sort_order: int | None = Field(default=None, ge=0, le=99999)
    is_active: bool | None = None


class JobRolePermissionUpdate(BaseModel):
    permissions: list[str] = Field(default_factory=list)
    field_keys: list[str] | None = Field(default=None, max_length=50)
    field_keys_configured: bool | None = None
    data_scope: str | None = Field(default=None, max_length=64)


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


class ReceivableInput(BaseModel):
    contract_record_id: int
    phase: str
    due_date: date
    amount: float = Field(gt=0)
    payer: str = ""
    remark: str = ""


class ReceivePaymentInput(BaseModel):
    amount: float = Field(gt=0)
    comment: str = ""


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
    case_phase: str = Field(default="等待公证书", max_length=64)
    handling_lawyer: str = Field(default="", max_length=128)
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


class CaseAssignmentInput(BaseModel):
    customer_manager: str = ""
    hearing_lawyer: str
    handling_lawyers: list[str] = Field(default_factory=list)
    assistant: str = ""
    comment: str = ""


class CaseHearingLawyerInput(BaseModel):
    hearing_lawyer: str = Field(min_length=1, max_length=128)
    comment: str = Field(default="", max_length=500)


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


class CaseAssistedFeeCreateInput(BaseModel):
    assisted_type: str = Field(min_length=1, max_length=128)
    amount: float | None = Field(default=None, ge=0, le=100000000)
    remark: str = Field(default="", max_length=1000)


class CaseAssistedFeeUpdateInput(BaseModel):
    assisted_type: str | None = Field(default=None, min_length=1, max_length=128)
    amount: float | None = Field(default=None, ge=0, le=100000000)
    remark: str | None = Field(default=None, max_length=1000)


class CaseAssistedFeeConfirmInput(BaseModel):
    confirmed_date: date | None = None
    remark: str = Field(default="", max_length=1000)


class CaseBatchFeeInput(BaseModel):
    case_ids: list[int] = Field(min_length=1, max_length=100)
    amount: float = Field(gt=0, le=100000000)
    fee_type_id: int | None = Field(default=None, gt=0)
    expense_scope: str = Field(pattern="^(律所|平台|内部)$")
    expense_subtype: str = Field(min_length=1, max_length=128)
    handler: str = Field(default="", max_length=128)
    description: str = Field(default="", max_length=1000)


class RefundCaseFeeBatchItemInput(BaseModel):
    case_id: int = Field(gt=0)
    contract_record_id: int | None = Field(default=None, gt=0)
    fee_type_id: int | None = Field(default=None, gt=0)
    fee_type: str = Field(pattern="^(官方费用|代理费|其他费用|内部费用)$")
    amount: float
    remark: str = Field(default="", max_length=1000)
    deadline: date | None = None
    payment_type_id: int | None = Field(default=None, gt=0)
    payment_amount: float | None = Field(default=None, gt=0)
    payment_remark: str = Field(default="", max_length=1000)
    payee_username: str = Field(default="", max_length=64)
    base_amount: float = 0
    reference_commission: float = 0


class RefundCaseFeeBatchCreateInput(BaseModel):
    items: list[RefundCaseFeeBatchItemInput] = Field(min_length=1, max_length=100)
    handler: str = Field(default="", max_length=128)
    submit_payment: bool = False


class AttachmentBatchInput(BaseModel):
    attachment_ids: list[int] = Field(min_length=1, max_length=100)
    case_id: int | None = Field(default=None, gt=0)


class ContractAttachmentBatchDeleteInput(BaseModel):
    file_ids: list[int] = Field(default_factory=list, max_length=100)
    fileIds: list[int] = Field(default_factory=list, max_length=100)
    attachment_ids: list[int] = Field(default_factory=list, max_length=100)


class ContractWholeDeleteInput(BaseModel):
    """Legacy FCM ContractDelete body: accepts snake_case and camelCase ids."""
    contract_ids: list[int] = Field(default_factory=list, max_length=200)
    contractIds: list[int] = Field(default_factory=list, max_length=200)


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


class CaseLitigantAgentInput(BaseModel):
    """A case-specific litigation representative; it is not a staff account."""
    name: str = Field(min_length=1, max_length=256)
    law_firm: str = Field(default="", max_length=256)
    position: str = Field(default="", max_length=128)
    phone: str = Field(default="", max_length=64)
    authority: str = Field(default="", max_length=500)


class CaseLitigantsInput(BaseModel):
    plaintiffs: list[str] = Field(default_factory=list, max_length=50)
    # Strings remain accepted for historical case JSON and existing callers.
    plaintiff_agents: list[CaseLitigantAgentInput | str] = Field(default_factory=list, max_length=50)
    defendants: list[str] = Field(default_factory=list, max_length=50)
    defendant_agents: list[CaseLitigantAgentInput | str] = Field(default_factory=list, max_length=50)
    third_parties: list[str] = Field(default_factory=list, max_length=50)
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


class TaskInput(BaseModel):
    title: str
    customer: str = ""
    owner: str
    deadline: date
    priority: str = "普通"
    source: str = "日常任务"
    task_type: str = ""
    collaborators: list[str] = Field(default_factory=list, max_length=20)
    case_no: str = ""
    case_nos: list[str] = Field(default_factory=list, max_length=100)
    case_record_id: int | None = Field(default=None, gt=0)
    case_module: str = Field(default="case", pattern="^(case|ipr_case)$")
    start_at: datetime | None = None
    end_at: datetime | None = None
    description: str = ""
    is_vip: bool = False


class VipTaskInput(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    customer: str = Field(default="", max_length=255)
    owner: str = Field(min_length=1, max_length=64)
    priority: str = Field(default="普通", max_length=32)
    status: str = Field(default="待处理", max_length=32)
    start_at: datetime | None = None
    deadline: date | None = None
    end_at: datetime | None = None
    description: str = Field(default="", max_length=10000)
    collaborators: list[str] = Field(default_factory=list, max_length=20)


class VipTaskUpdateInput(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    customer: str | None = Field(default=None, max_length=255)
    owner: str | None = Field(default=None, min_length=1, max_length=64)
    priority: str | None = Field(default=None, max_length=32)
    status: str | None = Field(default=None, max_length=32)
    start_at: datetime | None = None
    deadline: date | None = None
    end_at: datetime | None = None
    description: str | None = Field(default=None, max_length=10000)
    collaborators: list[str] | None = Field(default=None, max_length=20)


class VipTaskNodeInput(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    owner: str = Field(min_length=1, max_length=64)
    priority: str = Field(default="普通", max_length=32)
    status: str = Field(default="待处理", max_length=32)
    start_at: datetime | None = None
    deadline: date | None = None
    end_at: datetime | None = None
    description: str = Field(default="", max_length=10000)
    participants: list[str] = Field(default_factory=list, max_length=20)


class VipTaskNodeUpdateInput(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    owner: str | None = Field(default=None, min_length=1, max_length=64)
    priority: str | None = Field(default=None, max_length=32)
    status: str | None = Field(default=None, max_length=32)
    start_at: datetime | None = None
    deadline: date | None = None
    end_at: datetime | None = None
    description: str | None = Field(default=None, max_length=10000)
    participants: list[str] | None = Field(default=None, max_length=20)


class VipTaskMessageInput(BaseModel):
    content: str = Field(min_length=1, max_length=10000)
    recipients: list[str] = Field(default_factory=list, max_length=30)
    node_id: int | None = Field(default=None, gt=0)


class VipTaskMessageReadInput(BaseModel):
    message_ids: list[int] = Field(default_factory=list, max_length=100)


class TaskHandoffInput(BaseModel):
    recipient: str
    comment: str = ""


class TaskActionInput(BaseModel):
    comment: str = ""


class ClueBatchSubmitInput(BaseModel):
    clue_ids: list[int] = Field(min_length=1, max_length=100)
    comment: str = Field(default="", max_length=1000)


class ClueTurnOnAuditInput(BaseModel):
    reviewer: str = Field(min_length=1, max_length=128)
    comment: str = Field(default="", max_length=1000)


class TaskExceptionRequestInput(BaseModel):
    action: str = Field(pattern="^(挂起|取消)$")
    reason: str = Field(min_length=2, max_length=1000)


class TaskExceptionReviewInput(BaseModel):
    approved: bool
    comment: str = Field(default="", max_length=1000)


class TaskBatchUpdateInput(BaseModel):
    task_ids: list[int] = Field(min_length=1, max_length=100)
    owner: str | None = Field(default=None, max_length=128)
    deadline: date | None = None
    priority: str | None = None
    is_vip: bool | None = None
    comment: str = Field(default="", max_length=1000)


class TaskBatchLifecycleInput(BaseModel):
    task_ids: list[int] = Field(min_length=1, max_length=100)
    action: str = Field(pattern="^(accept|complete|confirm|handoff|withdraw)$")
    recipient: str = Field(default="", max_length=128)
    comment: str = Field(default="", max_length=1000)


class TaskBatchReadInput(BaseModel):
    """Selected task rows on the personal unread-message page."""
    task_ids: list[int] = Field(min_length=1, max_length=100)


class CaseTaskFinishedInput(BaseModel):
    """Legacy CaseTaskController.Finished payload: cases, never task ids."""
    case_ids: list[int] = Field(min_length=1, max_length=100)
    comment: str = Field(default="", max_length=1000)


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


class FinanceFeeCommissionDetailInput(BaseModel):
    employee_username: str = Field(min_length=1, max_length=64)
    commission_type: str = Field(default="员工提成", min_length=1, max_length=64)
    amount: float = Field(gt=0)
    remark: str = Field(default="", max_length=1000)


class FinanceFeeInput(BaseModel):
    title: str
    customer: str = ""
    amount: float
    fee_type_id: int | None = Field(default=None, gt=0)
    fee_type: str
    expense_scope: str | None = Field(default=None, pattern="^(律所|平台|内部)$")
    expense_subtype: str | None = None
    case_no: str = ""
    handler: str
    court: str = ""
    document_no: str = ""
    payee: str = ""
    base_amount: float = 0
    reference_commission: float = 0
    description: str = ""
    contract_record_id: int | None = None
    case_record_id: int | None = None
    deadline: date | None = None
    commission_details: list[FinanceFeeCommissionDetailInput] = Field(default_factory=list)


class FinanceFeeUpdateInput(FinanceFeeInput):
    """Editable draft fee fields; lifecycle records are immutable."""
    pass


class JarFeeInput(BaseModel):
    """Dedicated JAR (交案费) receivable, deliberately separate from payable fees."""
    contract_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=255)
    customer: str = Field(default="", max_length=255)
    payer_name: str = Field(default="", max_length=255)
    bank_voucher_no: str = Field(default="", max_length=128)
    received_date: date | None = None
    amount: float = Field(gt=0, le=1_000_000_000)
    official_fee_amount: float = Field(default=0, ge=0, le=1_000_000_000)
    agency_fee_amount: float = Field(default=0, ge=0, le=1_000_000_000)
    other_fee_amount: float = Field(default=0, ge=0, le=1_000_000_000)
    payment_method: str = Field(default="", max_length=64)
    handler: str = Field(default="", max_length=128)
    remark: str = Field(default="", max_length=2000)

    @field_validator("title")
    @classmethod
    def jar_fee_title_required_after_trim(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("交案费名称不能为空")
        return value


class JarFeeStatusInput(BaseModel):
    # Legacy JAR had no independent lifecycle action.  This is the smallest
    # explicit new lifecycle for the requested modern management screen.
    status: Literal["待确认", "已确认", "已入账", "已作废"]
    comment: str = Field(default="", max_length=1000)


class CaseFeeBatchUpdateInput(BaseModel):
    fee_ids: list[int] = Field(min_length=1, max_length=100)
    inform_date: date


class FinanceFeeInformInput(BaseModel):
    """The independent fee-notice step that precedes payment arrival."""
    inform_date: date = Field(default_factory=date.today)
    remark: str = Field(default="", max_length=1000)


class FinanceFeeArrivalInput(BaseModel):
    receivable_amount: float = Field(gt=0)
    received_amount: float = Field(gt=0)
    received_date: date = Field(default_factory=date.today)
    remark: str = Field(default="", max_length=1000)


class FinanceFeeInformLinksInput(BaseModel):
    fee_ids: list[int] = Field(min_length=2, max_length=100)


class CaseCommissionCreateItemInput(BaseModel):
    preview_key: str = Field(min_length=1, max_length=256)
    actual_amount: float = Field(gt=0)
    remark: str = Field(default="", max_length=1000)


class CaseCommissionBatchInput(BaseModel):
    source_fee_id: int = Field(gt=0)
    items: list[CaseCommissionCreateItemInput] = Field(min_length=1, max_length=100)


class FinanceActionInput(BaseModel):
    comment: str = ""
    amount: float | None = Field(default=None, gt=0)
    payment_type_id: int | None = Field(default=None, gt=0)
    payment_account: str = Field(default="", max_length=128)
    payment_payee: str = Field(default="", max_length=256)
    payment_remark: str = Field(default="", max_length=1000)


class FinancePaymentTypeCreateInput(BaseModel):
    nature: str = Field(min_length=1, max_length=64)
    payee: str = Field(min_length=1, max_length=255)
    account_bank: str = Field(min_length=1, max_length=255)
    account: str = Field(min_length=1, max_length=1000)


class FinancePaymentCancelInput(BaseModel):
    """Reason required when an ordinary finance payment is withdrawn."""

    reason: str = Field(min_length=1, max_length=1000)


class FinancePaymentRollbackInput(BaseModel):
    """Optional operator note for returning a pre-payment request to draft."""

    comment: str = Field(default="", max_length=1000)


class FinanceSettlementMarkInput(BaseModel):
    fee_ids: list[int] = Field(min_length=1, max_length=100)
    comment: str = Field(default="", max_length=500)


class FinanceFeeReviewInput(BaseModel):
    approved: bool
    comment: str = Field(default="", max_length=1000)


class FinanceFeeBatchReviewInput(FinanceFeeReviewInput):
    fee_ids: list[int] = Field(min_length=1, max_length=100)


class FinancePaymentPackagePreviewInput(BaseModel):
    fee_ids: list[int] = Field(min_length=1, max_length=100)


class FinancePaymentPackageCreateInput(FinancePaymentPackagePreviewInput):
    package_no: str = Field(pattern=r"^P\d{6}-\d{8}$")
    comment: str = Field(default="", max_length=500)


class FinancePaymentPackageUpdateInput(FinancePaymentPackagePreviewInput):
    """Editable pending package composition and its operator note."""
    comment: str = Field(default="", max_length=500)


class FinancePaymentPackageWriteoffInput(BaseModel):
    amount: float
    paid_date: date
    payment_method: str
    invoice_no: str = Field(min_length=1, max_length=128)
    remark: str = Field(default="", max_length=500)


class InvoiceApplicationInput(BaseModel):
    customer: str
    case_no: str = ""
    amount: float = Field(gt=0)
    invoice_title: str
    taxpayer_id: str
    invoice_phone: str = ""
    bank_account: str = ""
    bank_name: str = ""
    invoice_address: str = ""
    extra_amount: float = Field(default=0, ge=0)
    invoice_type: str = "增值税普通发票"
    invoice_content: str = "法律服务费"
    delivery_method: str = "电子发票"
    recipient: str = ""
    recipient_phone: str = ""
    email: str = ""
    delivery_address: str = ""
    remark: str = ""
    contract_record_id: int | None = None
    case_record_id: int | None = None
    case_fee_ids: list[int] = Field(default_factory=list, max_length=100)


class InvoiceIssueInput(BaseModel):
    invoice_no: str = Field(min_length=3, max_length=128)
    invoice_date: date
    invoice_holder: str = Field(default="", max_length=128)
    extra_amount: float = Field(default=0, ge=0)
    comment: str = ""


class InvoiceVoidInput(BaseModel):
    reason: str = Field(min_length=2, max_length=1000)


class InvoiceNumberChangeInput(BaseModel):
    invoice_no: str = Field(min_length=1, max_length=128)


class InvoiceDateChangeInput(BaseModel):
    application_date: date
    invoice_date: date


class FinanceReviewInput(BaseModel):
    approved: bool
    comment: str = Field(min_length=2, max_length=1000)


class LitigationRefundInput(BaseModel):
    fee_record_id: int | None = Field(default=None, ge=1)
    customer: str
    case_no: str
    court: str
    original_payment_no: str
    amount: float = Field(gt=0)
    applicant: str
    refund_account_name: str = ""
    refund_bank: str = ""
    refund_account: str = ""
    expected_date: date | None = None
    reason: str = "诉讼费退费"
    remark: str = ""


class RefundCompleteInput(BaseModel):
    actual_date: date
    voucher_no: str = Field(min_length=2, max_length=128)
    comment: str = ""


class RefundAmountUpdateInput(BaseModel):
    amount: float = Field(gt=0)
    comment: str = ""


class RefundBatchStatusInput(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=200)
    status: str = Field(min_length=2, max_length=32)
    comment: str = ""


class CaseFeeRefundLogInput(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=200)
    kind: Literal["court", "received", "other"]
    content: str = Field(min_length=2, max_length=1000)


class FinanceTransactionInput(BaseModel):
    finance_record_id: int | None = None
    transaction_type: str
    amount: float = Field(gt=0)
    transaction_date: date
    voucher_no: str = ""
    counterparty: str = ""
    remark: str = ""


class FinanceWriteoffInput(BaseModel):
    voucher_no: str = Field(min_length=2, max_length=128)
    comment: str = ""


class IncomingPaymentInput(BaseModel):
    received_date: date
    amount: float = Field(gt=0)
    payer_name: str = Field(min_length=2, max_length=255)
    bank_reference: str = Field(default="", max_length=128)
    customer: str = Field(default="", max_length=255)
    contract_no: str = Field(default="", max_length=64)
    case_no: str = Field(default="", max_length=64)
    bank_source: str = Field(default="", max_length=64)
    claim: bool = False
    remark: str = ""


class IncomingPaymentClaimInput(BaseModel):
    customer: str = Field(min_length=2, max_length=255)
    comment: str = ""


class IncomingPaymentSettlementItem(BaseModel):
    fee_record_id: int | None = None
    fee_type: str = Field(min_length=1, max_length=64)
    amount: float = Field(gt=0)
    settlement_amount: float = Field(ge=0)
    archive_fee: float = Field(ge=0)


class IncomingPaymentAllocationItem(BaseModel):
    receivable_plan_id: int | None = None
    fee_record_id: int | None = None
    amount: float = Field(gt=0)
    case_no: str = ""
    payment_method: str = Field(default="", max_length=64)
    settlement_items: list[IncomingPaymentSettlementItem] = Field(default_factory=list, max_length=50)


class IncomingPaymentAllocateInput(BaseModel):
    allocations: list[IncomingPaymentAllocationItem] = Field(min_length=1, max_length=50)
    comment: str = ""


class IncomingPaymentUpdateInput(BaseModel):
    received_date: date
    amount: float = Field(gt=0)
    payer_name: str = Field(min_length=2, max_length=255)
    bank_reference: str = Field(default="", max_length=128)
    customer: str = Field(default="", max_length=255)
    contract_no: str = Field(default="", max_length=64)
    case_no: str = Field(default="", max_length=64)
    bank_source: str = Field(default="", max_length=64)
    remark: str = ""


class IncomingPaymentRefundClaimInput(BaseModel):
    customer: str = Field(min_length=2, max_length=255)
    fee_record_id: int | None = Field(default=None, ge=1)
    comment: str = ""


class IncomingPaymentRevokeInput(BaseModel):
    payment_ids: list[int] = Field(min_length=1, max_length=100)
    comment: str = Field(default="", max_length=2000)


class FinanceSettlementApplyInput(BaseModel):
    receipt_ids: list[int] = Field(min_length=1, max_length=100)
    comment: str = ""


class FinanceSettlementReviewInput(BaseModel):
    application_ids: list[int] = Field(min_length=1, max_length=100)
    approved: bool
    comment: str = Field(default="", max_length=2000)


class FinanceSettlementPaymentInput(BaseModel):
    application_ids: list[int] = Field(min_length=1, max_length=100)
    action: str = Field(pattern="^(paid|rollback)$")
    comment: str = Field(default="", max_length=2000)


class FinanceSettlementReapplyInput(BaseModel):
    application_ids: list[int] = Field(min_length=1, max_length=100)
    comment: str = Field(min_length=1, max_length=2000)


class ArchiveSettlementPaymentReviewInput(BaseModel):
    settlement_ids: list[str] = Field(min_length=1, max_length=100)
    approved: bool
    comment: str = Field(default="", max_length=2000)


class ArchiveSettlementRollbackInput(BaseModel):
    record_ids: list[int] = Field(min_length=1, max_length=100)
    comment: str = Field(min_length=1, max_length=2000)


class ArchiveSettlementRejectedActionInput(BaseModel):
    record_ids: list[int] = Field(min_length=1, max_length=100)
    comment: str = Field(default="", max_length=2000)


class ReconciliationInput(BaseModel):
    period_type: str
    date_from: date
    date_to: date
    discrepancy_amount: float = 0
    remark: str = ""


class SystemUserInput(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    display_name: str = Field(min_length=1, max_length=64)
    department: str = Field(default="上海分所", min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    role: str | None = None
    role_ids: list[str] | None = None
    is_active: bool = True
    # An administrator-issued password is always one-time.  Keep accepting
    # this legacy request field for API compatibility, but never allow a
    # caller to opt a newly created account out of the first-login change.
    must_change_password: bool = True
    manager_id: int | None = Field(default=None, gt=0)
    access_level: str = Field(default="", max_length=64)
    lead_rate: str = Field(default="", max_length=32)
    copy_rate: str = Field(default="", max_length=32)
    profile: dict = Field(default_factory=dict)


class CacheBatchClearInput(BaseModel):
    cache_keys: list[str] = Field(default_factory=list, max_length=50)


class SystemUserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=2, max_length=64)
    display_name: str | None = Field(default=None, min_length=1, max_length=64)
    department: str | None = Field(default=None, min_length=1, max_length=64)
    role: str | None = None
    role_ids: list[str] | None = None
    manager_id: int | None = Field(default=None, ge=0)
    access_level: str | None = Field(default=None, max_length=64)
    lead_rate: str | None = Field(default=None, max_length=32)
    copy_rate: str | None = Field(default=None, max_length=32)
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    profile: dict | None = None


class UserPermissionOverrideUpdate(BaseModel):
    menu_keys: list[str] | None = None
    field_keys: list[str] | None = None
    data_scope: str | None = None
    clear: bool = False


class SystemUserPasswordResetInput(BaseModel):
    """Administrator-issued one-time password for an existing account."""

    new_password: str = Field(min_length=8, max_length=128)


class HrEmployeeUpdateInput(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    display_name: str = Field(min_length=1, max_length=64)
    department: str = Field(min_length=1, max_length=64)
    role: str
    position: str = Field(min_length=1, max_length=128)
    is_active: bool = True
    email: str = Field(default="", max_length=128)
    mobile: str = Field(default="", max_length=32)
    office_phone: str = Field(default="", max_length=32)
    joined_at: date
    left_at: date | None = None
    data: dict = Field(default_factory=dict)


class HrEmployeeLoginStatusInput(BaseModel):
    is_active: bool


class HrEmployeeContractApprovalStatusInput(BaseModel):
    contract_approval_enabled: bool


class HrEmployeeCreateInput(BaseModel):
    # Only an "employee account" has a system-login counterpart.  Keeping this
    # optional lets HR retain customer/external personnel files without creating
    # a privileged or orphaned system account by accident.
    username: str = Field(default="", max_length=64)
    display_name: str = Field(min_length=1, max_length=64)
    employee_no: str = Field(min_length=1, max_length=64)
    company: str = Field(min_length=1, max_length=255)
    department: str = Field(min_length=1, max_length=64)
    password: str = Field(default="", max_length=128)
    role: str = "user"
    position: str = Field(min_length=1, max_length=128)
    is_active: bool = True
    account_type: str = Field(default="员工账号", max_length=32)
    data: dict = Field(default_factory=dict)


class CurrentUserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=64)
    email: str | None = Field(default=None, max_length=128)
    office_phone: str | None = Field(default=None, max_length=32)
    mobile: str | None = Field(default=None, max_length=32)
    menu_auto_collapse: str | None = Field(default=None, pattern="^(yes|no)$")
    current_password: str | None = Field(default=None, min_length=1, max_length=128)
    new_password: str | None = Field(default=None, min_length=8, max_length=128)


class DingTalkLoginInput(BaseModel):
    auth_code: str = Field(min_length=1, max_length=512)


class DingTalkBindInput(DingTalkLoginInput):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class DingTalkBindingInput(BaseModel):
    user_id: str = Field(default="", max_length=128)


class UserMessageInput(BaseModel):
    recipients: list[str] = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, max_length=4000)


class CommunicationLogInput(BaseModel):
    customer_record_id: int
    contact: str = Field(default="", max_length=128)
    phone: str = Field(default="", max_length=64)
    content: str = Field(min_length=1, max_length=4000)
    occurred_at: datetime


class CommunicationLogUpdate(BaseModel):
    contact: str | None = Field(default=None, max_length=128)
    phone: str | None = Field(default=None, max_length=64)
    content: str | None = Field(default=None, min_length=1, max_length=4000)
    occurred_at: datetime | None = None


class RolePermissionUpdate(BaseModel):
    data_scope: str = Field(min_length=1, max_length=64)
    menu_keys: list[str]
    field_keys: list[str]
    action_keys: list[str] | None = None


class SecurityPolicyUpdate(BaseModel):
    min_password_length: int = Field(ge=8, le=32)
    max_failed_attempts: int = Field(ge=3, le=10)
    lock_minutes: int = Field(ge=1, le=1440)
    token_minutes: int = Field(ge=15, le=1440)


class SystemParameterInput(BaseModel):
    category: str = Field(min_length=2, max_length=32)
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    extra: dict = Field(default_factory=dict)
    sort_order: int = Field(default=0, ge=0, le=99999)
    is_active: bool = True


class SystemParameterUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    extra: dict | None = None
    sort_order: int | None = Field(default=None, ge=0, le=99999)
    is_active: bool | None = None


class SystemParameterRelationReplaceInput(BaseModel):
    source_id: int = Field(gt=0)
    target_ids: list[int] = Field(default_factory=list, max_length=1000)


class SystemConfigUpdate(BaseModel):
    value: dict


class LawFirmInput(BaseModel):
    code: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=2, max_length=255)
    registered_address: str = Field(default="", max_length=255)
    business_address: str = Field(default="", max_length=255)
    detail_address: str = Field(default="", max_length=255)
    postal_code: str = Field(default="", max_length=32)
    phone: str = Field(default="", max_length=64)
    fax: str = Field(default="", max_length=64)
    email: str = Field(default="", max_length=128)
    organization_code: str = Field(default="", max_length=64)
    company_code: str = Field(default="", max_length=64)
    firm_type: str = Field(default="", max_length=64)
    firm_level: str = Field(default="", max_length=32)
    country: str = Field(default="中国", max_length=64)
    is_active: bool = True
    default_contact: "LawFirmContactInput | None" = None


class LawFirmContactInput(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    address: str = Field(default="", max_length=255)
    postal_code: str = Field(default="", max_length=32)
    phone: str = Field(default="", max_length=64)
    fax: str = Field(default="", max_length=64)
    email: str = Field(default="", max_length=128)
    is_active: bool = True


LawFirmInput.model_rebuild()


class SystemMenuUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=255)
    icon: str | None = Field(default=None, max_length=64)
    sort_order: int | None = Field(default=None, ge=0, le=99999)
    is_visible: bool | None = None
    is_active: bool | None = None


class SystemMenuInput(BaseModel):
    key: str | None = Field(default=None, max_length=128, pattern=r"^[a-z0-9][a-z0-9-]*$")
    parent_key: str = Field(default="", max_length=128)
    label: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=255)
    icon: str = Field(default="", max_length=64)
    sort_order: int = Field(default=0, ge=0, le=99999)
    is_visible: bool = True
    is_active: bool = True


class ReportInput(BaseModel):
    title: str
    report_type: str
    period: str
    format: str = "CSV"
    description: str = ""


class CustomerShareInput(BaseModel):
    recipients: list[str] = Field(min_length=1, max_length=200)
    comment: str = ""


class CustomerActionInput(BaseModel):
    comment: str = ""


class CustomerContactInput(BaseModel):
    name: str
    project_role: str = ""
    phone: str = ""
    office_phone: str = ""
    im_account: str = ""
    email: str = ""
    position: str = ""
    contact_status: str = "正常联系"
    is_valid: bool = True
    is_primary: bool = False
    is_received_email: bool = True
    is_contacted: bool = True
    is_people_base: bool = True
    remark: str = ""


class CustomerManagersInput(BaseModel):
    managers: list[str] = Field(min_length=1, max_length=20)
    comment: str = ""


class CustomerPatchInput(BaseModel):
    description: str | None = Field(default=None, max_length=2000)
    data: dict = Field(default_factory=dict)


class CustomerEventInput(BaseModel):
    action: str = Field(min_length=1, max_length=64)
    comment: str = Field(default="", max_length=4000)


class CustomerContactStatusInput(BaseModel):
    is_valid: bool | None = None
    is_primary: bool | None = None


class CustomerNoteInput(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    note_type: str = Field(default="跟进记录", max_length=32)


class CustomerLevelChangeInput(BaseModel):
    level: str = Field(min_length=2, max_length=32)
    comment: str = Field(default="", max_length=1000)


class CustomerLevelReviewInput(BaseModel):
    approved: bool
    comment: str = Field(default="", max_length=1000)


class CustomerKeyChangeInput(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    credit_code: str = Field(default="", max_length=64)
    comment: str = Field(min_length=2, max_length=1000)


class CustomerKeyChangeReviewInput(BaseModel):
    approved: bool
    comment: str = Field(default="", max_length=1000)


class CustomerPortalActionInput(BaseModel):
    account: str = Field(default="", max_length=128)
    comment: str = Field(default="", max_length=1000)


class CustomerPortalLoginInput(BaseModel):
    account: str = Field(min_length=3, max_length=128)
    password: str = Field(min_length=8, max_length=128)


class CustomerPortalDemandInput(CustomerPortalLoginInput):
    title: str = Field(min_length=2, max_length=200)
    content: str = Field(min_length=2, max_length=2000)
    case_no: str = Field(default="", max_length=128)


class CustomerPortalActivationInput(BaseModel):
    account: str = Field(min_length=3, max_length=128)
    activation_code: str = Field(min_length=16, max_length=128)
    password: str = Field(min_length=8, max_length=128)


class CustomerCreateInput(BaseModel):
    serial_no: str = ""
    title: str = ""
    status: str = ""
    owner: str = ""
    department: str = ""
    description: str = ""
    customer_managers: list[str] = Field(default_factory=list, max_length=20)
    customer_type: str | None = None
    level: str | None = None
    is_shared: str | bool | None = None
    is_assisted: str | bool | None = None
    fee_reduction: str | bool | None = None
    contact: str | list[str] | None = None
    contact_accounts: list[str] = Field(default_factory=list, max_length=20)
    phone: str | None = None
    credit_code: str | None = None
    legal_representative: str | None = None
    registered_address: str | None = None
    invoice_title: str | None = None
    taxpayer_id: str | None = None
    invoice_address: str | None = None
    invoice_phone: str | None = None
    bank_name: str | None = None
    bank_account: str | None = None
    short_name: str | None = None
    fax: str | None = None
    legal_agent_id_no: str | None = None
    legal_agent_title: str | None = None
    customer_source: str | None = None
    file_date: str | None = None
    province: str | None = None
    postal_code: str | None = None
    patent_customer_type: str | None = None
    industry: str | None = None
    output_value: str | None = None
    cooperation_status: str | None = None
    gb_classification: str | None = None
    website: str | None = None
    organization_nature: str | None = None
    organization_code: str | None = None
    registration_region: str | None = None
    registration_postal_code: str | None = None
    registered_capital: str | None = None
    registration_year: str | None = None
    data: dict = Field(default_factory=dict)


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


class CaseCreationReviewInput(BaseModel):
    approved: bool
    comment: str = Field(default="", max_length=1000)


class CaseUnarchiveRequestInput(BaseModel):
    reason: str = Field(min_length=2, max_length=1000)


class CaseUnarchiveReviewInput(BaseModel):
    approved: bool
    comment: str = Field(default="", max_length=1000)


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
    contract_object_id: int = Field(gt=0)
    amount: float = Field(gt=0, le=999999999)


class ContractPaymentApplicationInput(BaseModel):
    payment_type_id: int = Field(gt=0)
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
