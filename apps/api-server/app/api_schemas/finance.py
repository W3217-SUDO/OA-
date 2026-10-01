"""finance 领域请求数据契约。"""

from datetime import date
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal


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


class CaseBatchFeeContractInput(BaseModel):
    case_id: int = Field(gt=0)
    contract_record_id: int = Field(gt=0)


class CaseBatchFeeInput(BaseModel):
    case_ids: list[int] = Field(min_length=1, max_length=100)
    case_contracts: list[CaseBatchFeeContractInput] = Field(default_factory=list, max_length=100)
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
    commission_mode: Literal["automatic", "manual"] | None = None
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
    base_amount: float | None = Field(default=None, gt=0)
    actual_amount: float = Field(gt=0)
    remark: str = Field(default="", max_length=1000)


class CaseCommissionBatchInput(BaseModel):
    source_fee_id: int = Field(gt=0)
    items: list[CaseCommissionCreateItemInput] = Field(min_length=1, max_length=100)


class CaseCommissionPreviewInput(BaseModel):
    """Preview server-derived commission rows before the agency fee exists."""
    amount: float = Field(gt=0)


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
    # Itemized service lines from the legacy invoice page. Kept as JSON so
    # different fee catalogs can carry their own description/unit/tax fields.
    service_items: list[dict] = Field(default_factory=list, max_length=100)
    case_fee_allocations: list[dict] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_invoice_lines(self):
        from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
        supplied_fields = set(self.model_fields_set)

        def number(value, label, *, positive=False, money=False):
            try:
                result = Decimal(str(value))
                if not result.is_finite() or result < 0 or (positive and result <= 0):
                    raise ValueError(f"{label}必须为有限{'正' if positive else '非负'}数")
                if money:
                    result = result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    if positive and result <= 0:
                        raise ValueError(f"{label}不能小于0.01")
                return result
            except (InvalidOperation, TypeError):
                raise ValueError(f"{label}不是有效数值") from None

        total = number(self.amount, "开票金额", positive=True, money=True)
        self.amount = float(total)
        self.extra_amount = float(number(self.extra_amount, "附加金额", money=True))
        normalized = []
        for index, raw in enumerate(self.service_items, 1):
            row = dict(raw)
            name = str(row.get("service_name") or "").strip()
            if not name:
                raise ValueError(f"第{index}项服务名称不能为空")
            quantity = number(row.get("quantity", 1), "服务数量", positive=True)
            price = number(row.get("unit_price", 0), "服务单价")
            expected = number(quantity * price, "服务金额", money=True)
            amount = number(row.get("amount", expected), "服务金额", money=True)
            if amount != expected:
                raise ValueError(f"第{index}项金额必须等于数量乘单价")
            rate = number(row.get("tax_rate", 0), "税率")
            if rate > 100:
                raise ValueError("税率必须在0至100之间")
            tax = number(row.get("tax_amount", 0), "税额", money=True)
            # Legacy tax fields are entered independently; do not invent a tax formula.
            row.update(service_name=name, quantity=float(quantity), unit_price=float(price),
                       amount=float(amount), tax_rate=float(rate), tax_amount=float(tax))
            normalized.append(row)
        if normalized and sum((Decimal(str(row["amount"])) for row in normalized), Decimal(0)) != total:
            raise ValueError("服务项金额合计必须等于开票金额")
        self.service_items = normalized
        allocations = []
        seen = set()
        for raw in self.case_fee_allocations:
            fee_id = number(raw.get("fee_id"), "费用ID", positive=True)
            if fee_id != fee_id.to_integral_value() or int(fee_id) in seen:
                raise ValueError("费用分配ID必须是唯一正整数")
            seen.add(int(fee_id))
            allocations.append({"fee_id": int(fee_id), "amount": float(number(raw.get("amount"), "本次开票金额", money=True))})
        if allocations:
            if seen != set(self.case_fee_ids):
                raise ValueError("费用分配必须与所选费用逐项一致")
            if sum((Decimal(str(row["amount"])) for row in allocations), Decimal(0)) != total:
                raise ValueError("费用分配金额合计必须等于开票金额")
        self.case_fee_allocations = allocations
        if "专用" in self.invoice_type and not all(value.strip() for value in (
            self.invoice_address, self.invoice_phone, self.bank_name, self.bank_account,
        )):
            raise ValueError("增值税专用发票必须填写注册地址、注册电话、开户银行和银行账号")
        self.__pydantic_fields_set__.intersection_update(supplied_fields)
        return self


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
    request_key: str = Field(default="", max_length=64)
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
    settlement_amount: float | None = Field(default=None, ge=0)
    archive_fee: float | None = Field(default=None, ge=0)


class IncomingPaymentAllocationItem(BaseModel):
    is_refund: bool = False
    receivable_plan_id: int | None = None
    fee_record_id: int | None = None
    amount: float = Field(gt=0)
    case_no: str = ""
    payment_method: str = Field(default="", max_length=64)
    settlement_items: list[IncomingPaymentSettlementItem] = Field(default_factory=list, max_length=50)


class IncomingPaymentAllocateInput(BaseModel):
    case_fees_only: bool = False
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
