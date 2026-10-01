"""调查任务、线索及证据数据模型。"""

from datetime import datetime
from sqlalchemy import BigInteger, Boolean, CHAR, CheckConstraint, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class InvestigationHistoricalReference(Base):
    """A source identifier whose parent row no longer exists in the legacy DB.

    This is intentionally not a synthetic investigation, task, or clue.  It
    preserves the unresolved source key so child data remains referentially
    intact without inventing a business relationship.
    """

    __tablename__ = "investigation_historical_references"
    __table_args__ = (
        UniqueConstraint("entity_type", "legacy_key", name="uq_investigation_historical_reference"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(32), index=True)
    legacy_key: Mapped[str] = mapped_column(String(128), index=True)
    source_table: Mapped[str] = mapped_column(String(128), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    source_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class InvestigationTaskLink(Base):
    """Canonical task-to-investigation link for current and historical data."""

    __tablename__ = "investigation_task_links"
    __table_args__ = (
        UniqueConstraint("task_record_id", name="uq_investigation_task_link_record"),
        UniqueConstraint("legacy_task_id", name="uq_investigation_task_link_legacy_id"),
        UniqueConstraint("legacy_task_no", name="uq_investigation_task_link_legacy_no"),
        CheckConstraint(
            "(investigation_record_id IS NOT NULL) OR (missing_investigation_reference_id IS NOT NULL)",
            name="ck_investigation_task_link_has_parent",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    investigation_record_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="RESTRICT"), nullable=True, index=True)
    missing_investigation_reference_id: Mapped[int | None] = mapped_column(ForeignKey("investigation_historical_references.id", ondelete="RESTRICT"), nullable=True, index=True)
    legacy_task_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    legacy_task_no: Mapped[str] = mapped_column(String(64), default="", index=True)
    legacy_task_guid: Mapped[str] = mapped_column(String(50), default="", index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class InvestigationClueLink(Base):
    """Canonical clue-to-task and clue-to-investigation links."""

    __tablename__ = "investigation_clue_links"
    __table_args__ = (
        UniqueConstraint("clue_record_id", name="uq_investigation_clue_link_record"),
        UniqueConstraint("legacy_clue_id", name="uq_investigation_clue_link_legacy_id"),
        UniqueConstraint("legacy_clue_no", name="uq_investigation_clue_link_legacy_no"),
        CheckConstraint(
            "(task_record_id IS NOT NULL) OR (missing_task_reference_id IS NOT NULL)",
            name="ck_investigation_clue_link_has_task",
        ),
        CheckConstraint(
            "(investigation_record_id IS NOT NULL) OR (missing_investigation_reference_id IS NOT NULL)",
            name="ck_investigation_clue_link_has_investigation",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    clue_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    task_record_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="RESTRICT"), nullable=True, index=True)
    missing_task_reference_id: Mapped[int | None] = mapped_column(ForeignKey("investigation_historical_references.id", ondelete="RESTRICT"), nullable=True, index=True)
    investigation_record_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="RESTRICT"), nullable=True, index=True)
    missing_investigation_reference_id: Mapped[int | None] = mapped_column(ForeignKey("investigation_historical_references.id", ondelete="RESTRICT"), nullable=True, index=True)
    legacy_clue_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    legacy_clue_no: Mapped[str] = mapped_column(String(64), default="", index=True)
    legacy_clue_guid: Mapped[str] = mapped_column(String(50), default="", index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class InvestigationEvidence(Base):
    """One evidence item with an explicit source-clue relationship."""

    __tablename__ = "investigation_evidences"
    __table_args__ = (
        UniqueConstraint("record_id", name="uq_investigation_evidence_record"),
        UniqueConstraint("legacy_evidence_id", name="uq_investigation_evidence_legacy_id"),
        CheckConstraint(
            "(clue_record_id IS NOT NULL) OR (missing_clue_reference_id IS NOT NULL)",
            name="ck_investigation_evidence_has_clue",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    clue_record_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="RESTRICT"), nullable=True, index=True)
    missing_clue_reference_id: Mapped[int | None] = mapped_column(ForeignKey("investigation_historical_references.id", ondelete="RESTRICT"), nullable=True, index=True)
    legacy_evidence_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    legacy_evidence_no: Mapped[str] = mapped_column(String(200), default="", index=True)
    # The legacy database reuses EvidenceGuid, so EvidenceId is the only
    # stable evidence identity. Keep the GUID searchable, never unique.
    legacy_evidence_guid: Mapped[str] = mapped_column(String(50), default="", index=True)
    evidence_type: Mapped[str] = mapped_column(String(32), default="")
    evidence_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="待整理", index=True)
    source_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class InvestigationEvidenceFile(Base):
    """Evidence-file metadata, linked even when the old physical file is absent."""

    __tablename__ = "investigation_evidence_files"
    id: Mapped[int] = mapped_column(primary_key=True)
    __table_args__ = (
        UniqueConstraint("legacy_file_id", name="uq_investigation_evidence_file_legacy_id"),
        CheckConstraint(
            "(evidence_id IS NOT NULL) OR (missing_evidence_reference_id IS NOT NULL)",
            name="ck_investigation_evidence_file_has_evidence",
        ),
    )

    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("investigation_evidences.id", ondelete="CASCADE"), nullable=True, index=True)
    missing_evidence_reference_id: Mapped[int | None] = mapped_column(ForeignKey("investigation_historical_references.id", ondelete="RESTRICT"), nullable=True, index=True)
    attachment_id: Mapped[int | None] = mapped_column(ForeignKey("file_attachments.id", ondelete="SET NULL"), nullable=True, unique=True, index=True)
    legacy_file_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    file_name: Mapped[str] = mapped_column(String(255), default="")
    media_type: Mapped[str] = mapped_column(String(128), default="")
    file_type_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    source_path: Mapped[str] = mapped_column(String(1000), default="")
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    source_available: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    source_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LegacyInvestigation(Base):
    __tablename__ = "Legal_Investigation"

    InvestigationId: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    InvestigationNo: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    InvestigationGuid: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    InvestigationTitle: Mapped[str | None] = mapped_column(String(200), nullable=True)
    Remark: Mapped[str | None] = mapped_column(String(8000), nullable=True)
    Indicter: Mapped[str | None] = mapped_column(String(200), nullable=True)
    IndicterName: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    CaseTypeId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    AuthorizationBeginTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    AuthorizationEndTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    InvestigationScope: Mapped[str | None] = mapped_column(CHAR(1), nullable=True)
    City: Mapped[str | None] = mapped_column(Text, nullable=True)
    Province: Mapped[str | None] = mapped_column(Text, nullable=True)
    BusinessOwner: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    Auditor: Mapped[str | None] = mapped_column(String(20), nullable=True)
    Status: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    IsActived: Mapped[str | None] = mapped_column(CHAR(1), nullable=True, index=True)
    CreateUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    CreateTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    NeedToAuditOnCustomer: Mapped[str | None] = mapped_column(CHAR(1), nullable=True)
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
    IsActived: Mapped[str | None] = mapped_column(CHAR(1), nullable=True, index=True)
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
    HasProduct: Mapped[str | None] = mapped_column(CHAR(1), nullable=True)
    InvestigationDate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    HasTort: Mapped[str | None] = mapped_column(CHAR(1), nullable=True)
    Indictee: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    Status: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    IsActived: Mapped[str | None] = mapped_column(CHAR(1), nullable=True, index=True)
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
    AuditNeedMergeCase: Mapped[str | None] = mapped_column(CHAR(1), nullable=True)
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
    IsActived: Mapped[str | None] = mapped_column(CHAR(1), nullable=True, index=True)
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
    IsActived: Mapped[str | None] = mapped_column(CHAR(1), nullable=True, index=True)
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
    IsActived: Mapped[str | None] = mapped_column(CHAR(1), nullable=True, index=True)
    CreateUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    CreateTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
