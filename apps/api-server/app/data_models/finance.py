"""财务流水、费用及分配历史数据模型。"""

from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import BigInteger, Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class JarFeeAuditLog(Base):
    """Append-only JAR receivable audit trail that survives JAR row deletion."""

    __tablename__ = "jar_fee_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    jar_fee_record_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="SET NULL"), nullable=True, index=True)
    jar_fee_serial_no: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    operator: Mapped[str] = mapped_column(String(64), index=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReceivablePlan(Base):
    __tablename__ = "receivable_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    phase: Mapped[str] = mapped_column(String(64))
    due_date: Mapped[date] = mapped_column(Date, index=True)
    amount: Mapped[float] = mapped_column(Float)
    received_amount: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(32), index=True, default="待收款")
    payer: Mapped[str] = mapped_column(String(255), default="")
    remark: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CaseAssistedFee(Base):
    """A civil/ordinary case's standalone assistance-fee lifecycle.

    Assistance applications are case-detail records, rather than generic finance
    records: confirmation must remain attributable to the case and cannot be
    bypassed through finance draft or payment endpoints.
    """

    __tablename__ = "case_assisted_fees"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_record_id: Mapped[int] = mapped_column(
        ForeignKey("business_records.id", ondelete="CASCADE"), index=True,
    )
    assisted_type: Mapped[str] = mapped_column(String(128), index=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="待办理", index=True)
    request_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    request_user: Mapped[str] = mapped_column(String(64), index=True)
    confirmed_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    confirmed_user: Mapped[str] = mapped_column(String(64), default="", index=True)
    remark: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class FinanceTransaction(Base):
    __tablename__ = "finance_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    finance_record_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), nullable=True, index=True)
    transaction_type: Mapped[str] = mapped_column(String(32), index=True)
    amount: Mapped[float] = mapped_column(Float)
    transaction_date: Mapped[date] = mapped_column(Date, index=True)
    voucher_no: Mapped[str] = mapped_column(String(64), default="")
    counterparty: Mapped[str] = mapped_column(String(255), default="")
    operator: Mapped[str] = mapped_column(String(64))
    remark: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReconciliationBatch(Base):
    __tablename__ = "reconciliation_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    period_type: Mapped[str] = mapped_column(String(16), index=True)
    date_from: Mapped[date] = mapped_column(Date, index=True)
    date_to: Mapped[date] = mapped_column(Date, index=True)
    transaction_count: Mapped[int] = mapped_column(Integer, default=0)
    total_amount: Mapped[float] = mapped_column(Float, default=0)
    discrepancy_amount: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(32), default="待确认")
    operator: Mapped[str] = mapped_column(String(64))
    remark: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IncomingPayment(Base):
    """银行到账记录，认领后再分配到合同应收及案件。"""

    __tablename__ = "incoming_payments"

    source_kind: Mapped[str] = mapped_column(String(24), default="unknown")

    id: Mapped[int] = mapped_column(primary_key=True)
    receipt_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    received_date: Mapped[date] = mapped_column(Date, index=True)
    amount: Mapped[float] = mapped_column(Float)
    payer_name: Mapped[str] = mapped_column(String(255), index=True)
    bank_reference: Mapped[str | None] = mapped_column(String(128), unique=True, index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="待认领")
    claimed_customer: Mapped[str] = mapped_column(String(255), default="", index=True)
    contract_record_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="SET NULL"), nullable=True, index=True)
    contract_no: Mapped[str] = mapped_column(String(64), default="", index=True)
    case_no: Mapped[str] = mapped_column(String(64), default="", index=True)
    bank_source: Mapped[str] = mapped_column(String(64), default="", index=True)
    claimant: Mapped[str] = mapped_column(String(64), default="")
    allocated_amount: Mapped[float] = mapped_column(Float, default=0)
    allocations: Mapped[list] = mapped_column(JSON, default=list)
    operator: Mapped[str] = mapped_column(String(64))
    remark: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LegacyFinanceRecord(Base):
    """Read-only normalized ledger for legacy FAM financial headers.

    Historical FAM rows are not coerced into live finance workflows.  The
    source identity, lifecycle status, raw amounts and any unambiguous local
    business-record links remain auditable here until a future migration can
    prove that the modern live model is semantically equivalent.
    """

    __tablename__ = "legacy_finance_records"
    __table_args__ = (
        UniqueConstraint("source_table", "legacy_id", name="uq_legacy_finance_record_source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_table: Mapped[str] = mapped_column(String(64), index=True)
    legacy_id: Mapped[str] = mapped_column(String(128), index=True)
    record_kind: Mapped[str] = mapped_column(String(32), index=True)
    status_code: Mapped[str] = mapped_column(String(32), default="", index=True)
    status_label: Mapped[str] = mapped_column(String(64), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    primary_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), default=0)
    # The audited legacy FAM tables in scope do not contain a currency column.
    currency: Mapped[str] = mapped_column(String(32), default="UNRECORDED_IN_LEGACY_SCHEMA")
    legacy_contract_no: Mapped[str] = mapped_column(String(64), default="", index=True)
    legacy_case_no: Mapped[str] = mapped_column(String(64), default="", index=True)
    legacy_customer_no: Mapped[str] = mapped_column(String(64), default="", index=True)
    contract_record_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="SET NULL"), nullable=True, index=True)
    case_record_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_record_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="SET NULL"), nullable=True, index=True)
    mapping_status: Mapped[str] = mapped_column(String(32), default="unmapped", index=True)
    source_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LegacyFinanceAllocation(Base):
    """Legacy payment, receipt and invoice allocation line kept at source granularity."""

    __tablename__ = "legacy_finance_allocations"
    __table_args__ = (
        UniqueConstraint("source_table", "legacy_key", name="uq_legacy_finance_allocation_source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    legacy_finance_record_id: Mapped[int | None] = mapped_column(ForeignKey("legacy_finance_records.id", ondelete="SET NULL"), nullable=True, index=True)
    parent_source_table: Mapped[str] = mapped_column(String(64), default="", index=True)
    parent_legacy_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    orphan_reason: Mapped[str] = mapped_column(String(64), default="", index=True)
    source_table: Mapped[str] = mapped_column(String(64), index=True)
    legacy_key: Mapped[str] = mapped_column(String(160), index=True)
    allocation_kind: Mapped[str] = mapped_column(String(32), index=True)
    legacy_case_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    legacy_case_no: Mapped[str] = mapped_column(String(64), default="", index=True)
    legacy_case_fee_id: Mapped[str] = mapped_column(String(80), default="", index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), default=0)
    prepaid_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), default=0)
    settlement_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), default=0)
    archive_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), default=0)
    is_refund: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    case_record_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="SET NULL"), nullable=True, index=True)
    mapping_status: Mapped[str] = mapped_column(String(32), default="unmapped", index=True)
    source_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LegacyFinanceFile(Base):
    """Invoice-file metadata only; no legacy physical file is fabricated."""

    __tablename__ = "legacy_finance_files"
    __table_args__ = (
        UniqueConstraint("legacy_finance_record_id", "legacy_key", name="uq_legacy_finance_file_source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    legacy_finance_record_id: Mapped[int | None] = mapped_column(ForeignKey("legacy_finance_records.id", ondelete="SET NULL"), nullable=True, index=True)
    source_table: Mapped[str] = mapped_column(String(64), default="FAM_Invoice_File", index=True)
    parent_legacy_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    orphan_reason: Mapped[str] = mapped_column(String(64), default="", index=True)
    legacy_key: Mapped[str] = mapped_column(String(160), index=True)
    legacy_case_fee_id: Mapped[str] = mapped_column(String(80), default="", index=True)
    filename: Mapped[str] = mapped_column(String(255), default="")
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    file_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), default=0)
    invoice_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    physical_file_verified: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    source_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LegacyFinanceAudit(Base):
    """Immutable AP/invoice approval trail at the legacy audit-row granularity."""

    __tablename__ = "legacy_finance_audits"
    __table_args__ = (
        UniqueConstraint("source_table", "legacy_id", name="uq_legacy_finance_audit_source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    legacy_finance_record_id: Mapped[int | None] = mapped_column(ForeignKey("legacy_finance_records.id", ondelete="SET NULL"), nullable=True, index=True)
    parent_source_table: Mapped[str] = mapped_column(String(64), index=True)
    parent_legacy_id: Mapped[str] = mapped_column(String(128), index=True)
    orphan_reason: Mapped[str] = mapped_column(String(64), default="", index=True)
    source_table: Mapped[str] = mapped_column(String(64), index=True)
    legacy_id: Mapped[str] = mapped_column(String(128), index=True)
    audit_kind: Mapped[str] = mapped_column(String(32), index=True)
    audit_status_code: Mapped[str] = mapped_column(String(32), default="", index=True)
    audit_flow_id: Mapped[str] = mapped_column(String(64), default="")
    audit_flow_node_id: Mapped[str] = mapped_column(String(64), default="")
    audit_round_id: Mapped[str] = mapped_column(String(64), default="")
    auditor: Mapped[str] = mapped_column(String(64), default="", index=True)
    audit_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    audit_content: Mapped[str] = mapped_column(Text, default="")
    source_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
