"""正式收发文及历史附件数据模型。"""

from datetime import datetime
from sqlalchemy import BigInteger, Boolean, CHAR, DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


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
    IsElectronicSeal: Mapped[str | None] = mapped_column(CHAR(1), nullable=True)
    IsOfflinePrint: Mapped[str | None] = mapped_column(CHAR(1), nullable=True)
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
    IsActived: Mapped[str | None] = mapped_column(CHAR(1), nullable=True, index=True)
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
    IsActived: Mapped[str | None] = mapped_column(CHAR(1), nullable=True, index=True)
    CreateUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    CreateTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
