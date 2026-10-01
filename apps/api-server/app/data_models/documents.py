"""附件、文档模板与智能文档数据模型。"""

from datetime import date, datetime
from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class FileAttachment(Base):
    __tablename__ = "file_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    record_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), nullable=True, index=True)
    invoice_record_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="SET NULL"), nullable=True, index=True)
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
    # This short-lived lease is separate from the IPR application-package lock.
    word_editor_lock_token: Mapped[str] = mapped_column(String(96), default="", index=True)
    word_editor_lock_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    word_editor_locked_by: Mapped[str] = mapped_column(String(64), default="")
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


class LegacyHistoricalAttachment(Base):
    """Immutable metadata projection for legacy contract and official files.

    This table intentionally does not reference ``file_attachments``.  A legacy
    row is valuable audit evidence even when its source volume is unavailable;
    creating a live upload entry would incorrectly expose download and preview
    behavior that the legacy source cannot support.
    """

    __tablename__ = "legacy_historical_attachments"
    __table_args__ = (
        UniqueConstraint(
            "source_system", "legacy_entity_type", "legacy_file_id",
            name="uq_legacy_historical_attachment_source",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_system: Mapped[str] = mapped_column(String(32), index=True)
    legacy_entity_type: Mapped[str] = mapped_column(String(96), index=True)
    legacy_file_id: Mapped[int] = mapped_column(BigInteger, index=True)
    legacy_file_guid: Mapped[str] = mapped_column(String(64), default="", index=True)
    legacy_parent_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    legacy_parent_guid: Mapped[str] = mapped_column(String(64), default="", index=True)
    legacy_parent_no: Mapped[str] = mapped_column(String(64), default="", index=True)
    legacy_parent_tuple: Mapped[dict] = mapped_column(JSON, default=dict)
    file_name: Mapped[str] = mapped_column(String(400), default="")
    legacy_declared_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    legacy_file_path: Mapped[str] = mapped_column(String(1000), default="")
    legacy_is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    source_physical_exists: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    source_physical_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    source_recovery_status: Mapped[str] = mapped_column(String(96), index=True)
    # A row can be both parentless and a controller-path collision. Keep every
    # quarantine cause rather than allowing the primary status to hide one.
    source_quarantine_reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    source_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
