"""客户、联系人及客户历史数据模型。"""

from datetime import datetime
from sqlalchemy import BigInteger, Boolean, CHAR, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class LegacyCustomer(Base):
    """Compatibility projection of CRM_Customer, preserving legacy soft keys."""

    __tablename__ = "CRM_Customer"

    CustomerId: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    CustomerGuid: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    CompanyId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    DepartmentId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    CustomerNo: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    CustomerName: Mapped[str] = mapped_column(String(400), nullable=False, index=True)
    ContactAddress: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ContactPhone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    Fax: Mapped[str | None] = mapped_column(String(50), nullable=True)
    Zip: Mapped[str | None] = mapped_column(String(50), nullable=True)
    Province: Mapped[str | None] = mapped_column(String(20), nullable=True)
    City: Mapped[str | None] = mapped_column(String(20), nullable=True)
    Industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ProductionValue: Mapped[str | None] = mapped_column(String(100), nullable=True)
    CustomerTypeName: Mapped[str | None] = mapped_column(String(100), nullable=True)
    CooperatioSituation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    CustomerSourceType: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ApplicationSituation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    WebSite: Mapped[str | None] = mapped_column(String(200), nullable=True)
    BusinessOwner: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    IsAssisted: Mapped[str | None] = mapped_column(CHAR(1), nullable=True)
    CompanyTypeName: Mapped[str | None] = mapped_column(String(100), nullable=True)
    GBTypeName: Mapped[str | None] = mapped_column(String(100), nullable=True)
    RegisteredCapital: Mapped[str | None] = mapped_column(String(100), nullable=True)
    RegistrationDate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    RegistrationCity: Mapped[str | None] = mapped_column(String(100), nullable=True)
    RegistrationZip: Mapped[str | None] = mapped_column(String(100), nullable=True)
    RegistrationAddress: Mapped[str | None] = mapped_column(String(500), nullable=True)
    OrganizationCode: Mapped[str | None] = mapped_column(String(100), nullable=True)
    LicenseNo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    AccountBankName: Mapped[str | None] = mapped_column(String(100), nullable=True)
    BankAccount: Mapped[str | None] = mapped_column(String(100), nullable=True)
    InputDate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    Holder: Mapped[str | None] = mapped_column(String(20), nullable=True)
    CustomerOwner: Mapped[str | None] = mapped_column(String(20), nullable=True)
    IsShared: Mapped[str | None] = mapped_column(CHAR(1), nullable=True)
    IsActived: Mapped[str | None] = mapped_column(CHAR(1), nullable=True, index=True)
    CustomerStatus: Mapped[str | None] = mapped_column(String(100), nullable=True)
    PrePaidAmount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    LastContactTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    LastUpdateTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    IsFeeReducing: Mapped[str | None] = mapped_column(CHAR(1), nullable=True)
    CustomerLevelName: Mapped[str | None] = mapped_column(String(100), nullable=True)
    CreateUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    CreateTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ChangeTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    IsOpened: Mapped[str | None] = mapped_column(CHAR(1), nullable=True)
    CustomerType: Mapped[int | None] = mapped_column(Integer, nullable=True)
    LegalAgentName: Mapped[str | None] = mapped_column(String(200), nullable=True)
    LegalAgentIdNo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    LegalAgentTitle: Mapped[str | None] = mapped_column(String(200), nullable=True)
    CustomerShortName: Mapped[str | None] = mapped_column(String(100), nullable=True)


class LegacyCustomerContact(Base):
    __tablename__ = "CRM_Customer_Contacts"

    ContactsId: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ContactsGuid: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    CustomerId: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    CustomerNo: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    CompanyId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    DepartmentId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ContactsTitle: Mapped[str | None] = mapped_column(String(200), nullable=True)
    Contacts: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ProjectRole: Mapped[str | None] = mapped_column(String(100), nullable=True)
    FocusPoint: Mapped[str | None] = mapped_column(String(200), nullable=True)
    Intention: Mapped[str | None] = mapped_column(String(200), nullable=True)
    Email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    OfficePhone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    HomePhone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    Mobilephone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    IM: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ContactAddress: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ContactZip: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ContactFax: Mapped[str | None] = mapped_column(String(100), nullable=True)
    IsContacted: Mapped[str | None] = mapped_column(CHAR(1), nullable=True)
    IsPeopleBASE: Mapped[str | None] = mapped_column(CHAR(1), nullable=True)
    IsReceivedEmail: Mapped[str | None] = mapped_column(CHAR(1), nullable=True)
    PhotoFileName: Mapped[str | None] = mapped_column(String(200), nullable=True)
    IsDefault: Mapped[str | None] = mapped_column(CHAR(1), nullable=True)
    IsActived: Mapped[str | None] = mapped_column(CHAR(1), nullable=True)
    CreateTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    CreateUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ChangeTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    Password: Mapped[str | None] = mapped_column(String(50), nullable=True)
    OrgPassword: Mapped[str | None] = mapped_column(String(50), nullable=True)


class LegacyCustomerHistoryCoordinator(Base):
    """Immutable CRM_Customer_Coordinator rows, isolated from live sharing."""

    __tablename__ = "legacy_customer_history_coordinators"
    __table_args__ = (UniqueConstraint("source_system", "source_table", "source_primary_key", name="uq_legacy_customer_coordinator_source"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_system: Mapped[str] = mapped_column(String(32), default="legacy_crm", index=True)
    source_table: Mapped[str] = mapped_column(String(96), default="CRM_Customer_Coordinator", index=True)
    source_primary_key: Mapped[str] = mapped_column(String(128), index=True)
    legacy_customer_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    legacy_customer_no: Mapped[str] = mapped_column(String(64), default="", index=True)
    legacy_customer_guid: Mapped[str] = mapped_column(String(36), default="", index=True)
    customer_record_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="SET NULL"), nullable=True, index=True)
    parent_mapping_status: Mapped[str] = mapped_column(String(32), default="unmapped", index=True)
    orphan_reason: Mapped[str] = mapped_column(String(96), default="", index=True)
    source_username: Mapped[str] = mapped_column(String(64), default="", index=True)
    mapped_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user_mapping_status: Mapped[str] = mapped_column(String(32), default="unmapped", index=True)
    relation_type_id: Mapped[str] = mapped_column(String(32), default="")
    source_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LegacyCustomerHistoryContact(Base):
    """Immutable CRM_Customer_Contacts rows; live contact JSON is never reused."""

    __tablename__ = "legacy_customer_history_contacts"
    __table_args__ = (UniqueConstraint("source_system", "source_table", "source_primary_key", name="uq_legacy_customer_contact_history_source"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_system: Mapped[str] = mapped_column(String(32), default="legacy_crm", index=True)
    source_table: Mapped[str] = mapped_column(String(96), default="CRM_Customer_Contacts", index=True)
    source_primary_key: Mapped[str] = mapped_column(String(128), index=True)
    legacy_contact_guid: Mapped[str] = mapped_column(String(36), default="", index=True)
    legacy_customer_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    legacy_customer_no: Mapped[str] = mapped_column(String(64), default="", index=True)
    legacy_customer_guid: Mapped[str] = mapped_column(String(36), default="", index=True)
    customer_record_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="SET NULL"), nullable=True, index=True)
    parent_mapping_status: Mapped[str] = mapped_column(String(32), default="unmapped", index=True)
    orphan_reason: Mapped[str] = mapped_column(String(96), default="", index=True)
    contact_name: Mapped[str] = mapped_column(String(200), default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    mobile_phone: Mapped[str] = mapped_column(String(64), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    photo_recovery_status: Mapped[str] = mapped_column(String(48), default="not_declared", index=True)
    source_username: Mapped[str] = mapped_column(String(64), default="", index=True)
    mapped_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user_mapping_status: Mapped[str] = mapped_column(String(32), default="unmapped", index=True)
    source_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LegacyCustomerHistoryEvent(Base):
    """CRM_Customer_Event history.  Unresolved parents stay quarantined."""

    __tablename__ = "legacy_customer_history_events"
    __table_args__ = (UniqueConstraint("source_system", "source_table", "source_primary_key", name="uq_legacy_customer_event_source"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_system: Mapped[str] = mapped_column(String(32), default="legacy_crm", index=True)
    source_table: Mapped[str] = mapped_column(String(96), default="CRM_Customer_Event", index=True)
    source_primary_key: Mapped[str] = mapped_column(String(128), index=True)
    legacy_customer_guid: Mapped[str] = mapped_column(String(36), default="", index=True)
    customer_record_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="SET NULL"), nullable=True, index=True)
    parent_mapping_status: Mapped[str] = mapped_column(String(32), default="unmapped", index=True)
    orphan_reason: Mapped[str] = mapped_column(String(96), default="", index=True)
    operator_username: Mapped[str] = mapped_column(String(64), default="", index=True)
    mapped_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user_mapping_status: Mapped[str] = mapped_column(String(32), default="unmapped", index=True)
    operated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    content: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    source_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LegacyCustomerHistoryFile(Base):
    """CRM_Customer_File metadata only.  Missing source bytes remain non-downloadable."""

    __tablename__ = "legacy_customer_history_files"
    __table_args__ = (UniqueConstraint("source_system", "source_table", "source_primary_key", name="uq_legacy_customer_file_source"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_system: Mapped[str] = mapped_column(String(32), default="legacy_crm", index=True)
    source_table: Mapped[str] = mapped_column(String(96), default="CRM_Customer_File", index=True)
    source_primary_key: Mapped[str] = mapped_column(String(128), index=True)
    legacy_file_guid: Mapped[str] = mapped_column(String(36), default="", index=True)
    legacy_customer_guid: Mapped[str] = mapped_column(String(36), default="", index=True)
    customer_record_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="SET NULL"), nullable=True, index=True)
    parent_mapping_status: Mapped[str] = mapped_column(String(32), default="unmapped", index=True)
    orphan_reason: Mapped[str] = mapped_column(String(96), default="", index=True)
    original_name: Mapped[str] = mapped_column(String(400), default="")
    source_path: Mapped[str] = mapped_column(String(1000), default="")
    declared_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    is_license: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    uploader_username: Mapped[str] = mapped_column(String(64), default="", index=True)
    mapped_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user_mapping_status: Mapped[str] = mapped_column(String(32), default="unmapped", index=True)
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    physical_recovery_status: Mapped[str] = mapped_column(String(48), default="missing_local_file", index=True)
    physical_checksum: Mapped[str] = mapped_column(String(128), default="")
    physical_path: Mapped[str] = mapped_column(String(1000), default="")
    source_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LegacyCustomerHistoryBaseline(Base):
    """Records audited zero-row CRM sources so zero is explicit, not an omission."""

    __tablename__ = "legacy_customer_history_baselines"
    __table_args__ = (UniqueConstraint("source_system", "source_table", name="uq_legacy_customer_baseline_source"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_system: Mapped[str] = mapped_column(String(32), default="legacy_crm", index=True)
    source_table: Mapped[str] = mapped_column(String(96), index=True)
    source_row_count: Mapped[int] = mapped_column(Integer, default=0)
    audit_status: Mapped[str] = mapped_column(String(32), default="zero_baseline", index=True)
    source_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
