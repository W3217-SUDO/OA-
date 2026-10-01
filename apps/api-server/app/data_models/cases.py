"""案件、日程及案件历史关联数据模型。"""

from datetime import date, datetime
from sqlalchemy import BigInteger, Boolean, CHAR, Date, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.legacy_schema import legacy_table_from_manifest


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


class CaseEvent(Base):
    """A material ordinary-case date, kept apart from workflow audit entries.

    The linked reminder record is optional.  It lets an event participate in the
    existing case-reminder workbench without turning the event itself into a
    generic business record.
    """

    __tablename__ = "case_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    event_type_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    event_type: Mapped[str] = mapped_column(String(128), default="其他", index=True)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    content: Mapped[str] = mapped_column(Text)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    remind_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    reminder_record_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="待处理", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    creator: Mapped[str] = mapped_column(String(64), index=True)
    updated_by: Mapped[str] = mapped_column(String(64), default="", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LegacyCase(Base):
    __table__ = legacy_table_from_manifest(Base.metadata, "Legal_Case")


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
    Actived: Mapped[str | None] = mapped_column(CHAR(1), nullable=True, index=True)
    HasHedgingFile: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    HedgingFileId: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    HedgingFileTypeId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    SortingIndex: Mapped[int | None] = mapped_column(Integer, nullable=True)
    TrackingNo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    PatentOfficeFileSeqNo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    PatentOfficeFileId: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    IsTransmitted: Mapped[str | None] = mapped_column(CHAR(1), nullable=True)
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
    IsActived: Mapped[str | None] = mapped_column(CHAR(1), nullable=True, index=True)


class LegacyCasePhaseHistory(Base):
    """Immutable per-case phase history imported from ``Legal_Case_Phase``.

    The legacy phase row is kept even when its case cannot be resolved.  This
    prevents a later parent repair from inventing or losing historical phase
    transitions.
    """

    __tablename__ = "legacy_case_phase_histories"

    id: Mapped[int] = mapped_column(primary_key=True)
    legacy_phase_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    case_record_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="RESTRICT"), nullable=True, index=True)
    legacy_case_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    legacy_case_no: Mapped[str] = mapped_column(String(64), default="", index=True)
    legacy_last_phase_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    legacy_phase_code: Mapped[str] = mapped_column(String(64), default="", index=True)
    phase_parameter_id: Mapped[int | None] = mapped_column(ForeignKey("system_parameters.id", ondelete="SET NULL"), nullable=True, index=True)
    case_mapping_state: Mapped[str] = mapped_column(String(40), default="unresolved", index=True)
    phase_mapping_state: Mapped[str] = mapped_column(String(40), default="unresolved", index=True)
    content: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[str] = mapped_column(CHAR(1), default="")
    created_by: Mapped[str] = mapped_column(String(64), default="")
    legacy_created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    legacy_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LegacyCaseParticipantRelation(Base):
    """Case-participant relation with an explicit current-user mapping state."""

    __tablename__ = "legacy_case_participant_relations"
    __table_args__ = (UniqueConstraint("legacy_case_no", "legacy_staff_name", name="uq_legacy_case_participant_relation"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_record_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="RESTRICT"), nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    legacy_case_no: Mapped[str] = mapped_column(String(64), index=True)
    legacy_staff_name: Mapped[str] = mapped_column(String(64), index=True)
    case_mapping_state: Mapped[str] = mapped_column(String(40), default="unresolved", index=True)
    user_mapping_state: Mapped[str] = mapped_column(String(40), default="unresolved", index=True)
    source_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LegacyCaseAttachmentRelation(Base):
    """Source-file identity mapped to a canonical attachment without copying binaries."""

    __tablename__ = "legacy_case_attachment_relations"

    id: Mapped[int] = mapped_column(primary_key=True)
    legacy_file_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    case_record_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="RESTRICT"), nullable=True, index=True)
    attachment_id: Mapped[int | None] = mapped_column(ForeignKey("file_attachments.id", ondelete="SET NULL"), nullable=True, index=True)
    legacy_case_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    legacy_case_no: Mapped[str] = mapped_column(String(64), default="", index=True)
    mapping_state: Mapped[str] = mapped_column(String(48), default="unresolved", index=True)
    source_path: Mapped[str] = mapped_column(String(1024), default="")
    source_available: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    source_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LegacyCaseLogProjection(Base):
    """One idempotent UI-log projection for each legacy ``Legal_Case_Log`` row."""

    __tablename__ = "legacy_case_log_projections"

    id: Mapped[int] = mapped_column(primary_key=True)
    legacy_log_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    case_record_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="RESTRICT"), nullable=True, index=True)
    workflow_event_id: Mapped[int | None] = mapped_column(ForeignKey("workflow_events.id", ondelete="SET NULL"), nullable=True, unique=True, index=True)
    mapping_state: Mapped[str] = mapped_column(String(40), default="unresolved", index=True)
    source_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LegacyCaseMigrationQuarantine(Base):
    """Unresolved source rows retained separately instead of being mislinked."""

    __tablename__ = "legacy_case_migration_quarantine"
    __table_args__ = (UniqueConstraint("source_table", "legacy_key", name="uq_legacy_case_migration_quarantine"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_table: Mapped[str] = mapped_column(String(96), index=True)
    legacy_key: Mapped[str] = mapped_column(String(128), index=True)
    reason: Mapped[str] = mapped_column(String(255), default="")
    source_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
