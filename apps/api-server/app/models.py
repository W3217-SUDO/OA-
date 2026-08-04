from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
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
