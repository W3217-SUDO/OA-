"""知识产权费用及账单数据模型。"""

from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class IprCaseAssistedFee(Base):
    """A patent/trademark case's government-assistance application lifecycle.

    This is intentionally separate from generic finance records: the legacy IPR
    workflow tracks an application, its handling date/operator and a receipt
    document even when it never becomes a payable or receivable transaction.
    """

    __tablename__ = "ipr_case_assisted_fees"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    assisted_type: Mapped[str] = mapped_column(String(128), index=True)
    # New applications must be confirmed before a receipt-backed handling action.
    # Existing rows using the former "待办理" default remain valid and handleable.
    status: Mapped[str] = mapped_column(String(32), default="待确认", index=True)
    request_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    request_user: Mapped[str] = mapped_column(String(64), index=True)
    response_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    response_user: Mapped[str] = mapped_column(String(64), default="", index=True)
    receipt_attachment_id: Mapped[int | None] = mapped_column(ForeignKey("file_attachments.id", ondelete="SET NULL"), nullable=True)
    remark: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class IprFeeHeader(Base):
    """Dedicated IPR fee carrier; never a projection of a generic finance row."""

    __tablename__ = "ipr_fee_headers"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    law_firm_id: Mapped[int] = mapped_column(ForeignKey("law_firms.id", ondelete="RESTRICT"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="草稿", index=True)
    created_by: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class IprFeeItem(Base):
    """A typed IPR fee item with explicit confirmation state and amount fields."""

    __tablename__ = "ipr_fee_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    header_id: Mapped[int] = mapped_column(ForeignKey("ipr_fee_headers.id", ondelete="CASCADE"), index=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("ipr_case_type_file_fee_type_rules.id", ondelete="RESTRICT"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    status: Mapped[str] = mapped_column(String(32), default="待确认", index=True)
    payment_bank: Mapped[str] = mapped_column(String(128), default="")
    actual_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    gained_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    confirmed_by: Mapped[str] = mapped_column(String(64), default="")
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class IprFeeBill(Base):
    """One confirmed bill per IPR fee item, separate from generic invoices."""

    __tablename__ = "ipr_fee_bills"
    __table_args__ = (UniqueConstraint("fee_item_id", name="uq_ipr_fee_bill_item"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    fee_item_id: Mapped[int] = mapped_column(ForeignKey("ipr_fee_items.id", ondelete="CASCADE"), index=True)
    bill_no: Mapped[str] = mapped_column(String(128), index=True)
    bill_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    bill_date: Mapped[date] = mapped_column(Date, index=True)
    confirmed_by: Mapped[str] = mapped_column(String(64), index=True)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IprFeeBillAttachmentMetadata(Base):
    """Immutable metadata-only bill attachment carrier for unrecoverable source files."""

    __tablename__ = "ipr_fee_bill_attachment_metadata"
    __table_args__ = (UniqueConstraint("bill_id", name="uq_ipr_fee_bill_attachment_metadata"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey("ipr_fee_bills.id", ondelete="CASCADE"), index=True)
    original_name: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(128), default="application/octet-stream")
    size: Mapped[int] = mapped_column(Integer, default=0)
    recovery_state: Mapped[str] = mapped_column(String(32), default="unrecoverable", index=True)
    source_locator: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IprFeeAuditLog(Base):
    """Append-only IPR fee audit entries, retained independently of workflow text."""

    __tablename__ = "ipr_fee_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_record_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), nullable=True, index=True)
    header_id: Mapped[int | None] = mapped_column(ForeignKey("ipr_fee_headers.id", ondelete="SET NULL"), nullable=True, index=True)
    item_id: Mapped[int | None] = mapped_column(ForeignKey("ipr_fee_items.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    operator: Mapped[str] = mapped_column(String(64), index=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
