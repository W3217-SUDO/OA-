"""知识产权案件及合作机构数据模型。"""

from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class LawFirm(Base):
    """独立的律所主体档案，不与客户或运行配置混用。"""

    __tablename__ = "law_firms"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    registered_address: Mapped[str] = mapped_column(String(255), default="")
    business_address: Mapped[str] = mapped_column(String(255), default="")
    detail_address: Mapped[str] = mapped_column(String(255), default="")
    postal_code: Mapped[str] = mapped_column(String(32), default="")
    phone: Mapped[str] = mapped_column(String(64), default="")
    fax: Mapped[str] = mapped_column(String(64), default="")
    email: Mapped[str] = mapped_column(String(128), default="")
    organization_code: Mapped[str] = mapped_column(String(64), default="")
    company_code: Mapped[str] = mapped_column(String(64), default="")
    country: Mapped[str] = mapped_column(String(64), default="中国")
    firm_type: Mapped[str] = mapped_column(String(64), default="", index=True)
    firm_level: Mapped[str] = mapped_column(String(32), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    default_contact_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    license_attachment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[str] = mapped_column(String(64), default="system")
    updated_by: Mapped[str] = mapped_column(String(64), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LawFirmContact(Base):
    __tablename__ = "law_firm_contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    law_firm_id: Mapped[int] = mapped_column(ForeignKey("law_firms.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    address: Mapped[str] = mapped_column(String(255), default="")
    postal_code: Mapped[str] = mapped_column(String(32), default="")
    phone: Mapped[str] = mapped_column(String(64), default="")
    fax: Mapped[str] = mapped_column(String(64), default="")
    email: Mapped[str] = mapped_column(String(128), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by: Mapped[str] = mapped_column(String(64), default="system")
    updated_by: Mapped[str] = mapped_column(String(64), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LawFirmAudit(Base):
    __tablename__ = "law_firm_audits"

    id: Mapped[int] = mapped_column(primary_key=True)
    law_firm_id: Mapped[int] = mapped_column(ForeignKey("law_firms.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(64))
    operator: Mapped[str] = mapped_column(String(64))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IprCaseLawFirm(Base):
    """An explicit collaboration-law-firm link for a patent or trademark case."""

    __tablename__ = "ipr_case_law_firms"
    __table_args__ = (UniqueConstraint("case_record_id", "law_firm_id", name="uq_ipr_case_law_firm"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    law_firm_id: Mapped[int] = mapped_column(ForeignKey("law_firms.id", ondelete="RESTRICT"), index=True)
    created_by: Mapped[str] = mapped_column(String(64), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IprCaseCustomer(Base):
    """A customer explicitly linked to an IPR case, including its primary customer."""

    __tablename__ = "ipr_case_customers"
    __table_args__ = (UniqueConstraint("case_record_id", "customer_record_id", name="uq_ipr_case_customer"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    customer_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="RESTRICT"), index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    sorting_index: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    created_by: Mapped[str] = mapped_column(String(64), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IprCaseCustomerContact(Base):
    """A selected customer contact and its legacy document/technical role on an IPR case."""

    __tablename__ = "ipr_case_customer_contacts"
    __table_args__ = (UniqueConstraint("case_record_id", "customer_record_id", "contact_id", "contact_role", name="uq_ipr_case_customer_contact_role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    customer_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="RESTRICT"), index=True)
    contact_id: Mapped[str] = mapped_column(String(64), index=True)
    contact_role: Mapped[str] = mapped_column(String(32), index=True)
    created_by: Mapped[str] = mapped_column(String(64), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IprCaseLog(Base):
    """User-authored IPR business notes; deliberately separate from immutable workflow events."""

    __tablename__ = "ipr_case_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IprCaseBatch(Base):
    """One successful legacy-style IPR batch-create submission."""

    __tablename__ = "ipr_case_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    customer_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="RESTRICT"), index=True)
    case_kind: Mapped[str] = mapped_column(String(16), index=True)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    created_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str] = mapped_column(String(64), index=True)
    department: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IprCaseBatchItem(Base):
    """A persisted, successfully-created row in an IPR batch."""

    __tablename__ = "ipr_case_batch_items"
    __table_args__ = (UniqueConstraint("batch_id", "row_no", name="uq_ipr_case_batch_item_row"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("ipr_case_batches.id", ondelete="CASCADE"), index=True)
    row_no: Mapped[int] = mapped_column(Integer)
    case_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    input_data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IprCaseRebootLink(Base):
    """Immutable source-to-new-case trace for legacy CaseRebooting."""

    __tablename__ = "ipr_case_reboot_links"
    __table_args__ = (UniqueConstraint("source_case_id", "reboot_case_id", name="uq_ipr_case_reboot_link"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_case_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    reboot_case_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IprCaseTypeAssignment(Base):
    __tablename__ = "ipr_case_type_assignments"
    __table_args__ = (UniqueConstraint("case_record_id", name="uq_ipr_case_type_assignment_case"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id"), nullable=False, index=True)
    case_type_id: Mapped[int] = mapped_column(ForeignKey("system_parameters.id"), nullable=False, index=True)
    assigned_by: Mapped[str] = mapped_column(String(128), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class IprCaseTypeFileFeeTypeRule(Base):
    """The IPR-only applicability rule for one case type/file type/fee type tuple."""

    __tablename__ = "ipr_case_type_file_fee_type_rules"
    __table_args__ = (
        UniqueConstraint("case_type_id", "file_type_id", "fee_type_id", name="uq_ipr_case_file_fee_rule"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    case_type_id: Mapped[int] = mapped_column(ForeignKey("system_parameters.id", ondelete="RESTRICT"), index=True)
    file_type_id: Mapped[int] = mapped_column(ForeignKey("system_parameters.id", ondelete="RESTRICT"), index=True)
    fee_type_id: Mapped[int] = mapped_column(ForeignKey("system_parameters.id", ondelete="RESTRICT"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by: Mapped[str] = mapped_column(String(64), default="system")
    updated_by: Mapped[str] = mapped_column(String(64), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
