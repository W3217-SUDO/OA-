from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, JSON, Numeric, String, Table, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    parent_department_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    manager: Mapped[str] = mapped_column(String(64), default="")
    overdue_deduction: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by: Mapped[str] = mapped_column(String(64), default="system")
    updated_by: Mapped[str] = mapped_column(String(64), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class JobRole(Base):
    __tablename__ = "job_roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    permissions: Mapped[list] = mapped_column(JSON, default=list)
    field_keys: Mapped[list] = mapped_column(JSON, default=list)
    description: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by: Mapped[str] = mapped_column(String(64), default="system")
    updated_by: Mapped[str] = mapped_column(String(64), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class HrSubrecord(Base):
    """员工请假、事项及提成等结构化附属记录。"""

    __tablename__ = "hr_subrecords"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(64))
    updated_by: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(64), default="管理者")
    department: Mapped[str] = mapped_column(String(64), default="上海分所", index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="admin")
    role_ids: Mapped[list] = mapped_column(JSON, default=list)
    profile: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SecurityPolicy(Base):
    __tablename__ = "security_policies"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    min_password_length: Mapped[int] = mapped_column(Integer, default=8)
    max_failed_attempts: Mapped[int] = mapped_column(Integer, default=5)
    lock_minutes: Mapped[int] = mapped_column(Integer, default=30)
    token_minutes: Mapped[int] = mapped_column(Integer, default=720)
    updated_by: Mapped[str] = mapped_column(String(64), default="system")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SystemParameter(Base):
    """可由管理员维护的案件、费用、法院等基础字典。"""

    __tablename__ = "system_parameters"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(32), index=True)
    code: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    extra: Mapped[dict] = mapped_column(JSON, default=dict)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by: Mapped[str] = mapped_column(String(64), default="system")
    updated_by: Mapped[str] = mapped_column(String(64), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SystemConfig(Base):
    """公司资料、客户共享规则和运行配置等结构化系统设置。"""

    __tablename__ = "system_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(128))
    group: Mapped[str] = mapped_column(String(32), index=True, default="业务配置")
    value: Mapped[dict] = mapped_column(JSON, default=dict)
    description: Mapped[str] = mapped_column(Text, default="")
    updated_by: Mapped[str] = mapped_column(String(64), default="system")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


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


class SystemMenu(Base):
    """系统已注册页面的菜单配置。"""

    __tablename__ = "system_menus"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    parent_key: Mapped[str] = mapped_column(String(64), default="", index=True)
    label: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(String(255), default="")
    icon: Mapped[str] = mapped_column(String(64), default="file-text")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    updated_by: Mapped[str] = mapped_column(String(64), default="system")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RolePermission(Base):
    __tablename__ = "role_permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(64))
    data_scope: Mapped[str] = mapped_column(String(64), default="本人及共享数据")
    menu_keys: Mapped[list] = mapped_column(JSON, default=list)
    field_keys: Mapped[list] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BusinessRecord(Base):
    """统一业务记录底座。

    首期用稳定公共字段承载各中心的列表、检索与流程状态；模块专属字段进入
    ``data``，后续拆分专表时 API 契约保持不变，网页端和小程序无需一起重写。
    """

    __tablename__ = "business_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    module: Mapped[str] = mapped_column(String(32), index=True)
    serial_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    customer: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(32), index=True, default="草稿")
    owner: Mapped[str] = mapped_column(String(64), index=True, default="管理者")
    department: Mapped[str] = mapped_column(String(64), default="上海分所")
    description: Mapped[str] = mapped_column(Text, default="")
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class WorkflowEvent(Base):
    __tablename__ = "workflow_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(64))
    from_status: Mapped[str] = mapped_column(String(32), default="")
    to_status: Mapped[str] = mapped_column(String(32), default="")
    operator: Mapped[str] = mapped_column(String(64))
    comment: Mapped[str] = mapped_column(Text, default="")
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


class HearingSchedule(Base):
    __tablename__ = "hearing_schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    hearing_date: Mapped[date] = mapped_column(Date, index=True)
    hearing_time: Mapped[str] = mapped_column(String(16))
    court: Mapped[str] = mapped_column(String(255), index=True)
    courtroom: Mapped[str] = mapped_column(String(128), default="")
    hearing_type: Mapped[str] = mapped_column(String(64), default="开庭")
    hearing_lawyer: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="已排期")
    remark: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class FileAttachment(Base):
    __tablename__ = "file_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    record_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), nullable=True, index=True)
    communication_log_id: Mapped[int | None] = mapped_column(ForeignKey("communication_logs.id", ondelete="CASCADE"), nullable=True, index=True)
    law_firm_id: Mapped[int | None] = mapped_column(ForeignKey("law_firms.id", ondelete="CASCADE"), nullable=True, index=True)
    finance_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("finance_transactions.id", ondelete="CASCADE"), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(64), index=True, default="普通附件")
    file_type_code: Mapped[str] = mapped_column(String(64), index=True, default="")
    original_name: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(255), unique=True)
    content_type: Mapped[str] = mapped_column(String(128), default="application/octet-stream")
    size: Mapped[int] = mapped_column(Integer, default=0)
    path: Mapped[str] = mapped_column(String(512))
    uploader: Mapped[str] = mapped_column(String(64))
    remark: Mapped[str] = mapped_column(Text, default="")
    # IPR 案件文件沿用附件存储，但其日期和转文状态必须可审计，不能只靠备注文本。
    document_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    is_license: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    requires_transmission: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_transmitted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    transmitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    transmitted_by: Mapped[str] = mapped_column(String(64), default="")
    # CPC 申请文件包生成后锁定，防止在未解锁时重复生成或覆盖。
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IprOfficialImportBatch(Base):
    """A source-file parsing run. Candidates are not official records until confirmed."""

    __tablename__ = "ipr_official_import_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_filename: Mapped[str] = mapped_column(String(255))
    source_path: Mapped[str] = mapped_column(String(512))
    source_size: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), index=True, default="待确认")
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    imported_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str] = mapped_column(String(64), index=True)
    department: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class IprOfficialImportCandidate(Base):
    """One parsed source row awaiting an explicit case match and confirmation."""

    __tablename__ = "ipr_official_import_candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("ipr_official_import_batches.id", ondelete="CASCADE"), index=True)
    row_no: Mapped[int] = mapped_column(Integer)
    ipr_case_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="SET NULL"), nullable=True, index=True)
    application_no: Mapped[str] = mapped_column(String(128), default="", index=True)
    official_type: Mapped[str] = mapped_column(String(255), default="")
    official_no: Mapped[str] = mapped_column(String(128), default="")
    received_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)
    errors: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), index=True, default="待确认")
    official_record_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="SET NULL"), nullable=True, index=True)
    confirmed_by: Mapped[str] = mapped_column(String(64), default="")
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IprCaseFileCustomImportBatch(Base):
    """A legacy-style filename parsing run; it has no formal attachment effect until confirmation."""

    __tablename__ = "ipr_case_file_custom_import_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_filename: Mapped[str] = mapped_column(String(255))
    source_path: Mapped[str] = mapped_column(String(512))
    source_size: Mapped[int] = mapped_column(Integer, default=0)
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="待确认")
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    imported_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str] = mapped_column(String(64), index=True)
    department: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class IprCaseFileCustomImportCandidate(Base):
    """One source file awaiting a visible case match and editable legacy file metadata."""

    __tablename__ = "ipr_case_file_custom_import_candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("ipr_case_file_custom_import_batches.id", ondelete="CASCADE"), index=True)
    ipr_case_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="SET NULL"), nullable=True, index=True)
    custom_filename: Mapped[str] = mapped_column(String(255))
    parsed_case_no: Mapped[str] = mapped_column(String(128), default="", index=True)
    parsed_document_no: Mapped[str] = mapped_column(String(128), default="")
    case_kind: Mapped[str] = mapped_column(String(32), default="")
    application_no: Mapped[str] = mapped_column(String(128), default="", index=True)
    file_type: Mapped[str] = mapped_column(String(255), default="")
    document_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    case_officer: Mapped[str] = mapped_column(String(64), default="")
    fee_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    fee_type: Mapped[str] = mapped_column(String(128), default="")
    fee_response_user: Mapped[str] = mapped_column(String(64), default="")
    errors: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), index=True, default="待确认")
    attachment_id: Mapped[int | None] = mapped_column(ForeignKey("file_attachments.id", ondelete="SET NULL"), nullable=True, index=True)
    confirmed_by: Mapped[str] = mapped_column(String(64), default="")
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DocumentTemplate(Base):
    __tablename__ = "document_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[str] = mapped_column(String(32), default="1.0")
    description: Mapped[str] = mapped_column(Text, default="")
    fields: Mapped[list] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


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
    status: Mapped[str] = mapped_column(String(32), default="待办理", index=True)
    request_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    request_user: Mapped[str] = mapped_column(String(64), index=True)
    response_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    response_user: Mapped[str] = mapped_column(String(64), default="", index=True)
    receipt_attachment_id: Mapped[int | None] = mapped_column(ForeignKey("file_attachments.id", ondelete="SET NULL"), nullable=True)
    remark: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


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

    id: Mapped[int] = mapped_column(primary_key=True)
    receipt_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    received_date: Mapped[date] = mapped_column(Date, index=True)
    amount: Mapped[float] = mapped_column(Float)
    payer_name: Mapped[str] = mapped_column(String(255), index=True)
    bank_reference: Mapped[str] = mapped_column(String(128), unique=True, index=True)
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


class ContractApprovalStep(Base):
    __tablename__ = "contract_approval_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    step_order: Mapped[int] = mapped_column(Integer)
    approver: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="等待中")
    comment: Mapped[str] = mapped_column(Text, default="")
    acted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ContractEvent(Base):
    """合同办理过程中的独立事项记录，不与审批/状态流水混用。"""

    __tablename__ = "contract_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text)
    operator: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ContractObject(Base):
    """A contract's independently maintained case/fee subject line."""

    __tablename__ = "contract_objects"

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    case_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id"), index=True)
    fee_type: Mapped[str] = mapped_column(String(64), default="")
    amount: Mapped[float] = mapped_column(Float, default=0)
    remark: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(64), index=True)
    updated_by: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ContractObjectLog(Base):
    __tablename__ = "contract_object_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_object_id: Mapped[int] = mapped_column(ForeignKey("contract_objects.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(64))
    before: Mapped[dict] = mapped_column(JSON, default=dict)
    after: Mapped[dict] = mapped_column(JSON, default=dict)
    operator: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ContractPaymentLine(Base):
    """One selected payable amount from a contract subject line.

    Contract payment requests have their own detail rows: a free-form finance
    record must never be able to impersonate an approved contract payment.
    """

    __tablename__ = "contract_payment_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    contract_object_id: Mapped[int] = mapped_column(ForeignKey("contract_objects.id", ondelete="RESTRICT"), index=True)
    case_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id"), index=True)
    fee_type: Mapped[str] = mapped_column(String(64))
    requested_amount: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OfficialOutgoingDocument(Base):
    """Independent formal-outgoing document lifecycle, separate from receipts."""

    __tablename__ = "official_outgoing_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), unique=True, index=True)
    official_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source_type: Mapped[str] = mapped_column(String(16), default="")
    source_record_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    source_file_ids: Mapped[list] = mapped_column(JSON, default=list)
    need_audit: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    stamp_attachment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    source_type: Mapped[str] = mapped_column(String(32), index=True)
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sender: Mapped[str] = mapped_column(String(64), index=True, default="system")
    recipient: Mapped[str] = mapped_column(String(64), index=True)
    notification_type: Mapped[str] = mapped_column(String(32), index=True, default="系统通知")
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text, default="")
    level: Mapped[str] = mapped_column(String(16), default="info")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    recipient_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    sender_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dingtalk_status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    dingtalk_attempts: Mapped[int] = mapped_column(Integer, default=0)
    dingtalk_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dingtalk_error: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CommunicationLog(Base):
    __tablename__ = "communication_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    customer_name: Mapped[str] = mapped_column(String(255), index=True)
    contact: Mapped[str] = mapped_column(String(128), default="")
    phone: Mapped[str] = mapped_column(String(64), default="")
    content: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    operator: Mapped[str] = mapped_column(String(64), index=True)
    note_id: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AgentDocument(Base):
    __tablename__ = "agent_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("document_templates.id", ondelete="RESTRICT"), index=True)
    record_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    instruction: Mapped[str] = mapped_column(Text, default="")
    prompt: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="等待生成", index=True)
    dify_message_id: Mapped[str] = mapped_column(String(128), default="")
    conversation_id: Mapped[str] = mapped_column(String(128), default="")
    error: Mapped[str] = mapped_column(Text, default="")
    creator: Mapped[str] = mapped_column(String(64), index=True)
    content_version: Mapped[int] = mapped_column(default=1)
    confirmed_by: Mapped[str] = mapped_column(String(64), default="")
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_content_hash: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SealAsset(Base):
    """印章实物台账，和用印申请记录分离管理。"""

    __tablename__ = "seal_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    seal_type: Mapped[str] = mapped_column(String(64), index=True)
    custodian: Mapped[str] = mapped_column(String(64), index=True)
    location: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(32), index=True, default="可用")
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    remark: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SealAssetAudit(Base):
    """保留印章资产删除等不可逆台账操作的审计快照。"""

    __tablename__ = "seal_asset_audits"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(Integer, index=True)
    asset_code: Mapped[str] = mapped_column(String(64), index=True)
    asset_name: Mapped[str] = mapped_column(String(128), default="")
    action: Mapped[str] = mapped_column(String(64), index=True)
    operator: Mapped[str] = mapped_column(String(64), index=True)
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class LegacyOfficialDocument(Base):
    """Compatibility projection of the legacy AWS_OfficialDocument table.

    The new workflow tables remain authoritative for extensions, while these
    columns preserve the old field names, status codes, and text references.
    """

    __tablename__ = "AWS_OfficialDocument"

    OfficialDocumentId: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    OfficialDocumentNo: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    OfficialDocumentGuid: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    CaseNo: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    ContractNo: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    CustomerNo: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    OfficialDocumentName: Mapped[str | None] = mapped_column(String(200), nullable=True)
    CompanyId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    DepartmentId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    BusinessOwner: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    OfficialDocumentType: Mapped[int | None] = mapped_column(Integer, nullable=True)
    IsElectronicSeal: Mapped[str | None] = mapped_column(String(1), nullable=True)
    IsOfflinePrint: Mapped[str | None] = mapped_column(String(1), nullable=True)
    PrintQuantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    PrintTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    Printer: Mapped[str | None] = mapped_column(String(20), nullable=True)
    PrintStatus: Mapped[int | None] = mapped_column(Integer, nullable=True)
    SealType: Mapped[int | None] = mapped_column(Integer, nullable=True)
    OfficialDocumentStatus: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    ApplicationDate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    OfficialDocumentBeginDate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    OfficialDocumentEndDate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    AuditFlowId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    AuditDate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    AuditFlowNodeId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    AuditRoundId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    Remark: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    IsActived: Mapped[str | None] = mapped_column(String(1), nullable=True, index=True)
    CreateUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    CreateTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    Auditor: Mapped[str | None] = mapped_column(String(20), nullable=True)
    AuditStatus: Mapped[int | None] = mapped_column(Integer, nullable=True)
    AuditTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    AuditRemark: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class LegacyOfficialDocumentAudit(Base):
    __tablename__ = "AWS_OfficialDocument_Audit"

    AuditId: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    OfficialDocumentId: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    OfficialDocumentNo: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    AuditFlowId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    AuditFlowNodeId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    AuditRoundId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    Auditor: Mapped[str | None] = mapped_column(String(20), nullable=True)
    AuditDate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    AuditStatus: Mapped[int | None] = mapped_column(Integer, nullable=True)
    AuditContent: Mapped[str | None] = mapped_column(String(200), nullable=True)
    CreateUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    CreateTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeUser: Mapped[str | None] = mapped_column(String(20), nullable=True)


class LegacyOfficialDocumentFile(Base):
    __tablename__ = "AWS_OfficialDocument_File"

    FileId: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    FileGuid: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    OfficialDocumentGuid: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    FileName: Mapped[str | None] = mapped_column(String(400), nullable=True)
    FilePath: Mapped[str | None] = mapped_column(String(500), nullable=True)
    FileSize: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    Uploader: Mapped[str | None] = mapped_column(String(20), nullable=True)
    UploadTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    IsActived: Mapped[str | None] = mapped_column(String(1), nullable=True, index=True)
    CreateUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    CreateTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeUser: Mapped[str | None] = mapped_column(String(20), nullable=True)


class LegacyContract(Base):
    """Compatibility projection of the legacy FCM_Contract table."""

    __tablename__ = "FCM_Contract"

    # SQLite only auto-increments an exact INTEGER primary key. SQL Server
    # promotes this projection to bigint when it is migrated there.
    ContractId: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ContractNo: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    ContractGuid: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    RefContractNo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ContractName: Mapped[str | None] = mapped_column(String(200), nullable=True)
    CustomerId: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    CustomerNo: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    CompanyId: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    DepartmentId: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    BusinessOwner: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    ContractType: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ChargingType: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ContractMoney: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    TaxRate: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    ContractStatus: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    ContractBeginDate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ContractEndDate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    AuditFlowId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    AuditDate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    AuditFlowNodeId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    AuditRoundId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    Remark: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    IsChanged: Mapped[str | None] = mapped_column(String(1), nullable=True)
    IsActived: Mapped[str | None] = mapped_column(String(1), nullable=True, index=True)
    CreateUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    CreateTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    GroupId: Mapped[int | None] = mapped_column(Integer, nullable=True)


class LegacyContractAudit(Base):
    __tablename__ = "FCM_Contract_Audit"

    AuditId: Mapped[int] = mapped_column(Integer, primary_key=True)
    ContractId: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    ContractNo: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    AuditFlowId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    AuditFlowNodeId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    AuditRoundId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    Auditor: Mapped[str | None] = mapped_column(String(20), nullable=True)
    AuditDate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    AuditStatus: Mapped[int | None] = mapped_column(Integer, nullable=True)
    AuditContent: Mapped[str | None] = mapped_column(String(200), nullable=True)
    CreateUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    CreateTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeUser: Mapped[str | None] = mapped_column(String(20), nullable=True)


class LegacyContractFile(Base):
    __tablename__ = "FCM_Contract_File"

    FileId: Mapped[int] = mapped_column(Integer, primary_key=True)
    FileGuid: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    ContractGuid: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    FileName: Mapped[str | None] = mapped_column(String(400), nullable=True)
    FilePath: Mapped[str | None] = mapped_column(String(500), nullable=True)
    FileSize: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    UploadUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    UploadTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    IsActived: Mapped[str | None] = mapped_column(String(1), nullable=True, index=True)
    CreateUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    CreateTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeUser: Mapped[str | None] = mapped_column(String(20), nullable=True)


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
    IsAssisted: Mapped[str | None] = mapped_column(String(1), nullable=True)
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
    IsShared: Mapped[str | None] = mapped_column(String(1), nullable=True)
    IsActived: Mapped[str | None] = mapped_column(String(1), nullable=True, index=True)
    CustomerStatus: Mapped[str | None] = mapped_column(String(100), nullable=True)
    PrePaidAmount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    LastContactTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    LastUpdateTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    IsFeeReducing: Mapped[str | None] = mapped_column(String(1), nullable=True)
    CustomerLevelName: Mapped[str | None] = mapped_column(String(100), nullable=True)
    CreateUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    CreateTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ChangeTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    IsOpened: Mapped[str | None] = mapped_column(String(1), nullable=True)
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
    IsContacted: Mapped[str | None] = mapped_column(String(1), nullable=True)
    IsPeopleBASE: Mapped[str | None] = mapped_column(String(1), nullable=True)
    IsReceivedEmail: Mapped[str | None] = mapped_column(String(1), nullable=True)
    PhotoFileName: Mapped[str | None] = mapped_column(String(200), nullable=True)
    IsDefault: Mapped[str | None] = mapped_column(String(1), nullable=True)
    IsActived: Mapped[str | None] = mapped_column(String(1), nullable=True)
    CreateTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    CreateUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ChangeTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    Password: Mapped[str | None] = mapped_column(String(50), nullable=True)
    OrgPassword: Mapped[str | None] = mapped_column(String(50), nullable=True)


# Legal_Case is intentionally a complete compatibility table.  The new case
# API remains the write surface, while this projection preserves the legacy
# field names and text-number relationships used by reporting integrations.
class LegacyCase(Base):
    __table__ = Table(
        "Legal_Case", Base.metadata,
        # SQLite requires an exact INTEGER PRIMARY KEY for generated IDs; the
        # SQL Server migration keeps the legacy bigint semantic.
        Column("CaseId", BigInteger, primary_key=True),
        Column("CaseNo", String(20), index=True), Column("CaseName", String(500)),
        Column("CompanyId", Integer), Column("DepartmentId", Integer),
        Column("CustomerNo", String(20), index=True), Column("CustomerTypeId", Integer),
        Column("CaseTypeId", Integer), Column("CaseRightTypeId", Integer), Column("CauseName", String(400)),
        Column("CasePhaseId", Integer), Column("CaseOriginPeople", String(200)), Column("CaseRegisterDate", DateTime),
        Column("CaseLawyer", String(200)), Column("CaseLawyerName", String(400)),
        Column("CaseAssistant", String(200)), Column("CaseAssistantName", String(400)),
        Column("AppellantNos", String(2000)), Column("AppellantNames", String(2000)), Column("AppellantAgent", String(2000)),
        Column("AppelleeNos", String(2000)), Column("AppelleeNames", String(2000)), Column("AppelleeAgent", String(2000)),
        Column("TheThirdNos", String(2000)), Column("TheThirdNames", String(2000)), Column("TheThirdAgent", String(2000)),
        *[Column(f"{stage}{field}", kind) for stage in ("FirstIntance", "SecondIntance", "LastIntance", "ExecutionIntance") for field, kind in (
            ("Court", String(20)), ("Judge", String(200)), ("Clerk", String(200)), ("CaseNo", String(50)),
            ("RegisterDate", DateTime), ("LawfulDay", DateTime), ("JudgmentDate", DateTime), ("CourtRoom", String(200)),
        )],
        Column("BusinessOwner", String(50)), Column("ContractNo", String(30), index=True), Column("InvestigationClueNos", String(2000)),
        Column("Deadline", DateTime), Column("SettlementAmount", Numeric(18, 2)), Column("IsActived", String(1), index=True),
        Column("CreateUser", String(20)), Column("CreateTime", DateTime), Column("ChangeUser", String(20)), Column("ChangeTime", DateTime),
        Column("Investigator", String(200)), Column("InvestigatorName", String(200)), Column("NotarialNos", String(800)), Column("DepositAddress", String(1000)),
        *[Column(f"{stage}ProcuratorateUnit{field}", String(200)) for stage in ("FirstIntance", "SecondIntance", "LastIntance") for field in ("Name", "CaseNo", "Address", "Operator", "Phone")],
        Column("PublicSecurityUnitName", String(200)), Column("PublicSecurityUnitCaseNo", String(200)), Column("PublicSecurityUnitAddress", String(200)), Column("PublicSecurityUnitOperator", String(200)), Column("PublicSecurityUnitPhone", String(200)),
        Column("ConsultantTypeId", Integer), Column("ConsultantBeginDate", DateTime), Column("ConsultantEndDate", DateTime),
        Column("CustomerAddInCaseNo", String(200)), Column("CustomerAddInOperator", String(500)), Column("CustomerAddInOperatorName", String(500)), Column("CustomerAddInRemark", String(2000)),
        Column("CourtLawyer", String(200)), Column("CourtLawyerName", String(200)), Column("LitigationAmount", Numeric(18, 2)),
        Column("CaseDivisionalDate", DateTime), Column("ArchiveStatus", Integer), Column("ToAuditTime", DateTime), Column("ToAuditRemark", String(2000)),
        Column("ToAuditApplicant", String(20)), Column("Auditor", String(20)), Column("AuditedTime", DateTime), Column("AuditedRemark", String(2000)),
        Column("ArchiveTypeId", Integer), Column("FileNo", String(20)), Column("InternalAuditor", String(20)), Column("InternalAuditedTime", DateTime),
        Column("InternalAuditedRemark", String(200)), Column("ArchivedFileNo", String(100)), Column("FilingTime", DateTime), Column("ClosingTime", DateTime),
        Column("ExecutionAcceptanceTime", DateTime), Column("ExecutionStatus", Integer),
        *[Column(f"ExecutionStatus{code}{edge}Time", DateTime) for code in range(10, 111, 10) for edge in ("Start", "End")],
        Column("OriginalCaseNo", String(20)),
    )


class LegacyInvestigation(Base):
    __tablename__ = "Legal_Investigation"

    InvestigationId: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    InvestigationNo: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    InvestigationGuid: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    InvestigationTitle: Mapped[str | None] = mapped_column(String(200), nullable=True)
    Remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    Indicter: Mapped[str | None] = mapped_column(String(200), nullable=True)
    IndicterName: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    CaseTypeId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    AuthorizationBeginTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    AuthorizationEndTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    InvestigationScope: Mapped[str | None] = mapped_column(String(1), nullable=True)
    City: Mapped[str | None] = mapped_column(Text, nullable=True)
    Province: Mapped[str | None] = mapped_column(Text, nullable=True)
    BusinessOwner: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    Auditor: Mapped[str | None] = mapped_column(String(20), nullable=True)
    Status: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    IsActived: Mapped[str | None] = mapped_column(String(1), nullable=True, index=True)
    CreateUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    CreateTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    NeedToAuditOnCustomer: Mapped[str | None] = mapped_column(String(1), nullable=True)
    ContractNo: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)


class LegacyInvestigationTask(Base):
    __tablename__ = "Legal_Investigation_Task"

    TaskId: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    TaskNo: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    TaskGuid: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    TaskName: Mapped[str | None] = mapped_column(String(200), nullable=True)
    TaskType: Mapped[str | None] = mapped_column(String(10), nullable=True)
    InvestigationNo: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    Investigator: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    Assistant: Mapped[str | None] = mapped_column(String(200), nullable=True)
    BeginTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    EndTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    InvestigationScope: Mapped[str | None] = mapped_column(String(10), nullable=True)
    Province: Mapped[str | None] = mapped_column(Text, nullable=True)
    City: Mapped[str | None] = mapped_column(Text, nullable=True)
    District: Mapped[str | None] = mapped_column(String(200), nullable=True)
    TaskStatus: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    IsActived: Mapped[str | None] = mapped_column(String(1), nullable=True, index=True)
    Remark: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    CreateUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    CreateTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeUser: Mapped[str | None] = mapped_column(String(20), nullable=True)


class LegacyInvestigationClue(Base):
    __tablename__ = "Legal_Investigation_Clue"

    ClueId: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ClueNo: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    ClueGuid: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    InvestigationTaskNo: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    InvestigationNo: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    BusinessType: Mapped[str | None] = mapped_column(String(10), nullable=True)
    ChannelType: Mapped[str | None] = mapped_column(String(10), nullable=True)
    PlatformName: Mapped[str | None] = mapped_column(String(200), nullable=True)
    StoreName: Mapped[str | None] = mapped_column(String(200), nullable=True)
    StoreUrl: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    LocationAddress: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    Address: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    Province: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ProvinceZh: Mapped[str | None] = mapped_column(String(100), nullable=True)
    City: Mapped[str | None] = mapped_column(String(20), nullable=True)
    CityZh: Mapped[str | None] = mapped_column(String(100), nullable=True)
    District: Mapped[str | None] = mapped_column(String(20), nullable=True)
    DistrictZh: Mapped[str | None] = mapped_column(String(100), nullable=True)
    HasProduct: Mapped[str | None] = mapped_column(String(1), nullable=True)
    InvestigationDate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    HasTort: Mapped[str | None] = mapped_column(String(1), nullable=True)
    Indictee: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    Status: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    IsActived: Mapped[str | None] = mapped_column(String(1), nullable=True, index=True)
    Remark: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    ToAuditTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    Auditor: Mapped[str | None] = mapped_column(String(20), nullable=True)
    TurnOnAuditTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    TurnOnAuditor: Mapped[str | None] = mapped_column(String(20), nullable=True)
    AuditTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    AuditRemark: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    CreateUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    CreateTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    AuditNeedMergeCase: Mapped[str | None] = mapped_column(String(1), nullable=True)
    AuditNeedMergeCaseNo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    Investigators: Mapped[str | None] = mapped_column(String(200), nullable=True)
    InvestigatorNames: Mapped[str | None] = mapped_column(String(200), nullable=True)
    CaseNo: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    CustomerAuditor: Mapped[str | None] = mapped_column(String(20), nullable=True)
    CustomerAuditTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    CustomerAuditRemark: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    StoreId: Mapped[str | None] = mapped_column(String(100), nullable=True)


class LegacyInvestigationClueEvidence(Base):
    __tablename__ = "Legal_Investigation_Clue_Evidence"

    EvidenceId: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    EvidenceNo: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    EvidenceGuid: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    EvidenceType: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ClueGuid: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    EvidenceDate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    EvidenceAddress: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    NotaryOrganization: Mapped[str | None] = mapped_column(String(200), nullable=True)
    NotarialNo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    NotarialObtainDate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    Remark: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    IsActived: Mapped[str | None] = mapped_column(String(1), nullable=True, index=True)
    CreateUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    CreateTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    DepositAddress: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    InvoiceNo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    EvidenceStatus: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    StorageLocationName: Mapped[str | None] = mapped_column(String(20), nullable=True)
    StorageLocationNo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    WarehouseNo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    PaymentStatus: Mapped[int | None] = mapped_column(Integer, nullable=True)
    Amount: Mapped[float | None] = mapped_column(Numeric(18, 0), nullable=True)


class LegacyInvestigationClueEvidenceFile(Base):
    __tablename__ = "Legal_Investigation_Clue_Evidence_File"

    FileId: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    EvidenceGuid: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    ClueGuid: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    FileName: Mapped[str | None] = mapped_column(String(200), nullable=True)
    MediaType: Mapped[str | None] = mapped_column(String(20), nullable=True)
    FileTypeId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    FullPath: Mapped[str | None] = mapped_column(String(500), nullable=True)
    FileSize: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    UploadingUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    UploadingTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    IsActived: Mapped[str | None] = mapped_column(String(1), nullable=True, index=True)
    CreateUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    CreateTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeUser: Mapped[str | None] = mapped_column(String(20), nullable=True)


class LegacyInvestigationClueFile(Base):
    __tablename__ = "Legal_Investigation_Clue_File"

    FileId: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ClueGuid: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    FileName: Mapped[str | None] = mapped_column(String(200), nullable=True)
    MediaType: Mapped[str | None] = mapped_column(String(20), nullable=True)
    FileTypeId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    FullPath: Mapped[str | None] = mapped_column(String(500), nullable=True)
    FileSize: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    UploadingUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    UploadingTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    IsActived: Mapped[str | None] = mapped_column(String(1), nullable=True, index=True)
    CreateUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    CreateTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeUser: Mapped[str | None] = mapped_column(String(20), nullable=True)


class LegacyCaseFile(Base):
    __tablename__ = "Legal_Case_File"

    FileId: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    CaseId: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    CaseNo: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    CompanyId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    FileName: Mapped[str | None] = mapped_column(String(200), nullable=True)
    FileTypeId: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    FullPath: Mapped[str | None] = mapped_column(String(500), nullable=True)
    FileSize: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    UploadingUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    UploadingTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    Actived: Mapped[str | None] = mapped_column(String(1), nullable=True, index=True)
    HasHedgingFile: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    HedgingFileId: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    HedgingFileTypeId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    SortingIndex: Mapped[int | None] = mapped_column(Integer, nullable=True)
    TrackingNo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    PatentOfficeFileSeqNo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    PatentOfficeFileId: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    IsTransmitted: Mapped[str | None] = mapped_column(String(1), nullable=True)
    CreateUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    CreateTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    CaseFileTypeId: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    FileGuid: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)


class LegacyCaseParticipant(Base):
    __tablename__ = "Legal_Case_Participant"

    CaseNo: Mapped[str] = mapped_column(String(20), primary_key=True)
    CompanyId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    StaffName: Mapped[str] = mapped_column(String(20), primary_key=True)
    CreateUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    CreateTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    SortingIndex: Mapped[int | None] = mapped_column(Integer, nullable=True)


class LegacyCaseLog(Base):
    __tablename__ = "Legal_Case_Log"

    LogId: Mapped[int] = mapped_column(Integer, primary_key=True)
    CaseId: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    CaseNo: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    Content: Mapped[str | None] = mapped_column(String(8000), nullable=True)
    LogType: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    CreateUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    CreateTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ChangeTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    IsActived: Mapped[str | None] = mapped_column(String(1), nullable=True, index=True)


