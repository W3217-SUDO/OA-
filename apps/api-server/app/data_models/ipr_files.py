"""知识产权文档导入批次数据模型。"""

from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


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
