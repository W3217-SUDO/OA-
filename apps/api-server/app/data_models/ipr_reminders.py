"""知识产权提醒、年费及预警数据模型。"""

from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class IprCaseReminder(Base):
    """Dedicated IPR case reminder, kept separate from ordinary lawsuit reminders."""

    __tablename__ = "ipr_case_reminders"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    event_type_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    event_type: Mapped[str] = mapped_column(String(128), default="自定义提醒", index=True)
    reminder_date: Mapped[date] = mapped_column(Date, index=True)
    deadline: Mapped[date] = mapped_column(Date, index=True)
    content: Mapped[str] = mapped_column(Text)
    creator: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class IprCaseReminderSuppression(Base):
    """Event types explicitly excluded from automatic IPR case monitoring."""

    __tablename__ = "ipr_case_reminder_suppressions"
    __table_args__ = (UniqueConstraint("case_record_id", "event_type_id", name="uq_ipr_case_reminder_suppression"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    event_type_id: Mapped[int] = mapped_column(Integer, index=True)
    event_type: Mapped[str] = mapped_column(String(128))
    operator: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IprCaseReminderType(Base):
    """Legacy Case_ReminderType projection for the IPR reminder workbench.

    This is a saved case query, not the event type stored on an individual
    IPR case reminder.  Its matching cases are evaluated against the caller's
    visible IPR records whenever the workbench or filtered case list is read.
    """

    __tablename__ = "ipr_case_reminder_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Keep the original IPR_Case_ReminderType identity so imported worklists
    # remain traceable and can be applied repeatedly without duplicates.
    legacy_reminder_type_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    query_object: Mapped[dict] = mapped_column(JSON, default=dict)
    legacy_query_object: Mapped[str] = mapped_column(Text, default="")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    owner: Mapped[str] = mapped_column(String(64), default="system", index=True)
    created_by: Mapped[str] = mapped_column(String(64), default="system")
    updated_by: Mapped[str] = mapped_column(String(64), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class IprCaseAnnualFee(Base):
    """One annual-fee obligation for an IPR case, with an optional real reminder."""

    __tablename__ = "ipr_case_annual_fees"
    __table_args__ = (UniqueConstraint("case_record_id", "fee_year", name="uq_ipr_case_annual_fee_year"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    fee_year: Mapped[int] = mapped_column(Integer, index=True)
    fee_name: Mapped[str] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(8), default="CNY")
    due_date: Mapped[date] = mapped_column(Date, index=True)
    paid_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default="待缴", index=True)
    reminder_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    reminder_id: Mapped[int | None] = mapped_column(ForeignKey("ipr_case_reminders.id", ondelete="SET NULL"), nullable=True, index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(64), index=True)


class IprCaseWarningRule(Base):
    """Configurable, deadline-driven IPR warning rule."""

    __tablename__ = "ipr_case_warning_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    case_kind: Mapped[str] = mapped_column(String(16), default="", index=True)
    case_type: Mapped[str] = mapped_column(String(128), default="")
    case_phase: Mapped[str] = mapped_column(String(128), default="")
    time_node: Mapped[str] = mapped_column(String(32), default="case_deadline", index=True)
    event_type_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    days_before: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by: Mapped[str] = mapped_column(String(64), index=True)
    updated_by: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class IprCaseWarning(Base):
    """One materialized warning per rule, deadline source and assignee."""

    __tablename__ = "ipr_case_warnings"
    __table_args__ = (UniqueConstraint("source_key", name="uq_ipr_case_warning_source"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("ipr_case_warning_rules.id", ondelete="CASCADE"), index=True)
    case_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    reminder_id: Mapped[int | None] = mapped_column(ForeignKey("ipr_case_reminders.id", ondelete="CASCADE"), nullable=True, index=True)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    recipient: Mapped[str] = mapped_column(String(64), index=True)
    source_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default="未读", index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_by: Mapped[str] = mapped_column(String(64), default="")
    process_comment: Mapped[str] = mapped_column(Text, default="")
    notification_id: Mapped[int | None] = mapped_column(ForeignKey("notifications.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
