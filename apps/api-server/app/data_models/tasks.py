"""任务、节点及任务历史数据模型。"""

from datetime import date, datetime
from sqlalchemy import BigInteger, Boolean, CHAR, Date, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class VipTask(Base):
    """Independent VIP task root, kept separate from the ordinary task workflow."""

    __tablename__ = "vip_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    serial_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    customer: Mapped[str] = mapped_column(String(255), default="", index=True)
    status: Mapped[str] = mapped_column(String(32), default="待处理", index=True)
    priority: Mapped[str] = mapped_column(String(32), default="普通", index=True)
    owner: Mapped[str] = mapped_column(String(64), index=True)
    department: Mapped[str] = mapped_column(String(64), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    collaborators: Mapped[list] = mapped_column(JSON, default=list)
    created_by: Mapped[str] = mapped_column(String(64), index=True)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class VipTaskNode(Base):
    __tablename__ = "vip_task_nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    vip_task_id: Mapped[int] = mapped_column(ForeignKey("vip_tasks.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="待处理", index=True)
    priority: Mapped[str] = mapped_column(String(32), default="普通")
    owner: Mapped[str] = mapped_column(String(64), index=True)
    participants: Mapped[list] = mapped_column(JSON, default=list)
    description: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(64), index=True)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class VipTaskMessage(Base):
    __tablename__ = "vip_task_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    vip_task_id: Mapped[int] = mapped_column(ForeignKey("vip_tasks.id", ondelete="CASCADE"), index=True)
    vip_task_node_id: Mapped[int | None] = mapped_column(ForeignKey("vip_task_nodes.id", ondelete="CASCADE"), nullable=True, index=True)
    sender: Mapped[str] = mapped_column(String(64), index=True)
    recipient: Mapped[str] = mapped_column(String(64), index=True)
    content: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LegacyCaseTaskHistory(Base):
    """Immutable, dedicated projection of ordinary-case task roots.

    This table deliberately does not reuse ``BusinessRecord(module='task')``.
    A historical root is only linked to a current case after an exact legacy
    CaseId/CaseNo reconciliation; unresolved source references remain explicit.
    """

    __tablename__ = "legacy_case_task_histories"
    __table_args__ = (
        UniqueConstraint("legacy_task_id", name="uq_legacy_case_task_history_task_id"),
        UniqueConstraint("legacy_task_guid", name="uq_legacy_case_task_history_task_guid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    case_record_id: Mapped[int | None] = mapped_column(ForeignKey("business_records.id", ondelete="RESTRICT"), nullable=True, index=True)
    legacy_task_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    legacy_task_guid: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    legacy_task_no: Mapped[str] = mapped_column(String(64), default="", index=True)
    legacy_case_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    legacy_case_no: Mapped[str] = mapped_column(String(64), default="", index=True)
    case_mapping_state: Mapped[str] = mapped_column(String(32), default="unresolved", index=True)
    task_title: Mapped[str] = mapped_column(String(255), default="")
    task_sub_title: Mapped[str] = mapped_column(String(255), default="")
    task_priority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    task_type_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    task_status: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    is_active: Mapped[str] = mapped_column(CHAR(1), default="")
    task_begin_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    task_finished_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    task_end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    initiator: Mapped[str] = mapped_column(String(64), default="")
    officer: Mapped[str] = mapped_column(String(64), default="")
    first_officer: Mapped[str] = mapped_column(String(64), default="")
    associates: Mapped[str] = mapped_column(Text, default="")
    associate_names: Mapped[str] = mapped_column(Text, default="")
    current_node_guid: Mapped[str] = mapped_column(String(50), default="", index=True)
    first_node_guid: Mapped[str] = mapped_column(String(50), default="", index=True)
    task_content: Mapped[str] = mapped_column(Text, default="")
    source_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LegacyCaseTaskHistoryNode(Base):
    """Node source rows, including rows whose legacy task root is absent."""

    __tablename__ = "legacy_case_task_history_nodes"
    __table_args__ = (
        UniqueConstraint("legacy_node_id", name="uq_legacy_case_task_history_node_id"),
        UniqueConstraint("legacy_task_guid", "legacy_node_guid", name="uq_legacy_case_task_history_node_guid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_history_id: Mapped[int | None] = mapped_column(ForeignKey("legacy_case_task_histories.id", ondelete="RESTRICT"), nullable=True, index=True)
    legacy_node_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    legacy_task_guid: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    legacy_node_guid: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    task_relationship_state: Mapped[str] = mapped_column(String(40), default="unresolved", index=True)
    node_begin_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    node_finished_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    node_end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    node_type_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    node_type_name: Mapped[str] = mapped_column(String(128), default="")
    node_status: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    is_active: Mapped[str] = mapped_column(CHAR(1), default="")
    initiator: Mapped[str] = mapped_column(String(64), default="")
    officer: Mapped[str] = mapped_column(String(64), default="")
    associates: Mapped[str] = mapped_column(Text, default="")
    associate_names: Mapped[str] = mapped_column(Text, default="")
    node_content: Mapped[str] = mapped_column(Text, default="")
    source_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LegacyCaseTaskHistoryNodeParticipant(Base):
    __tablename__ = "legacy_case_task_history_node_participants"
    __table_args__ = (UniqueConstraint("legacy_seq_id", name="uq_legacy_case_task_history_node_participant_seq"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_history_id: Mapped[int | None] = mapped_column(ForeignKey("legacy_case_task_histories.id", ondelete="RESTRICT"), nullable=True, index=True)
    node_history_id: Mapped[int | None] = mapped_column(ForeignKey("legacy_case_task_history_nodes.id", ondelete="RESTRICT"), nullable=True, index=True)
    legacy_seq_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    legacy_task_guid: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    legacy_node_guid: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    task_relationship_state: Mapped[str] = mapped_column(String(40), default="unresolved", index=True)
    node_relationship_state: Mapped[str] = mapped_column(String(40), default="unresolved", index=True)
    participant: Mapped[str] = mapped_column(String(128), default="")
    sorting_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LegacyCaseTaskHistoryMessage(Base):
    __tablename__ = "legacy_case_task_history_messages"
    __table_args__ = (UniqueConstraint("legacy_message_id", name="uq_legacy_case_task_history_message_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_history_id: Mapped[int | None] = mapped_column(ForeignKey("legacy_case_task_histories.id", ondelete="RESTRICT"), nullable=True, index=True)
    node_history_id: Mapped[int | None] = mapped_column(ForeignKey("legacy_case_task_history_nodes.id", ondelete="RESTRICT"), nullable=True, index=True)
    legacy_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    legacy_message_guid: Mapped[str] = mapped_column(String(50), default="", index=True)
    legacy_task_guid: Mapped[str] = mapped_column(String(50), default="", index=True)
    legacy_node_guid: Mapped[str] = mapped_column(String(50), default="", index=True)
    task_relationship_state: Mapped[str] = mapped_column(String(40), default="unresolved", index=True)
    node_relationship_state: Mapped[str] = mapped_column(String(40), default="unresolved", index=True)
    message_type_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message_type_name: Mapped[str] = mapped_column(String(128), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    sender: Mapped[str] = mapped_column(String(128), default="")
    send_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    source_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LegacyCaseTaskHistoryNotification(Base):
    __tablename__ = "legacy_case_task_history_notifications"
    __table_args__ = (UniqueConstraint("legacy_seq_id", name="uq_legacy_case_task_history_notification_seq"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_history_id: Mapped[int | None] = mapped_column(ForeignKey("legacy_case_task_histories.id", ondelete="RESTRICT"), nullable=True, index=True)
    message_history_id: Mapped[int | None] = mapped_column(ForeignKey("legacy_case_task_history_messages.id", ondelete="RESTRICT"), nullable=True, index=True)
    legacy_seq_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    legacy_task_guid: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    legacy_message_guid: Mapped[str] = mapped_column(String(50), default="", index=True)
    task_relationship_state: Mapped[str] = mapped_column(String(40), default="unresolved", index=True)
    message_relationship_state: Mapped[str] = mapped_column(String(40), default="unresolved", index=True)
    notification_type_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notification_type_name: Mapped[str] = mapped_column(String(128), default="")
    notification_object: Mapped[str] = mapped_column(String(128), default="", index=True)
    have_read: Mapped[str] = mapped_column(CHAR(1), default="", index=True)
    source_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LegacyCaseTaskHistoryReadReceipt(Base):
    __tablename__ = "legacy_case_task_history_read_receipts"
    __table_args__ = (UniqueConstraint("legacy_seq_id", name="uq_legacy_case_task_history_read_receipt_seq"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_history_id: Mapped[int | None] = mapped_column(ForeignKey("legacy_case_task_histories.id", ondelete="RESTRICT"), nullable=True, index=True)
    message_history_id: Mapped[int | None] = mapped_column(ForeignKey("legacy_case_task_history_messages.id", ondelete="RESTRICT"), nullable=True, index=True)
    legacy_seq_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    legacy_task_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    legacy_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    task_relationship_state: Mapped[str] = mapped_column(String(40), default="unresolved", index=True)
    message_relationship_state: Mapped[str] = mapped_column(String(40), default="unresolved", index=True)
    reader: Mapped[str] = mapped_column(String(128), default="")
    have_read: Mapped[str] = mapped_column(CHAR(1), default="", index=True)
    source_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LegacyCaseTaskHistoryFile(Base):
    """Historical file metadata only.  No source binary is materialized here."""

    __tablename__ = "legacy_case_task_history_files"
    __table_args__ = (UniqueConstraint("legacy_file_id", name="uq_legacy_case_task_history_file_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_history_id: Mapped[int | None] = mapped_column(ForeignKey("legacy_case_task_histories.id", ondelete="RESTRICT"), nullable=True, index=True)
    message_history_id: Mapped[int | None] = mapped_column(ForeignKey("legacy_case_task_history_messages.id", ondelete="RESTRICT"), nullable=True, index=True)
    legacy_file_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    legacy_file_guid: Mapped[str] = mapped_column(String(50), default="", index=True)
    legacy_task_guid: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    legacy_message_guid: Mapped[str] = mapped_column(String(50), default="", index=True)
    task_relationship_state: Mapped[str] = mapped_column(String(40), default="unresolved", index=True)
    message_relationship_state: Mapped[str] = mapped_column(String(40), default="unresolved", index=True)
    file_name: Mapped[str] = mapped_column(String(255), default="")
    source_path: Mapped[str] = mapped_column(String(1024), default="")
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    upload_user: Mapped[str] = mapped_column(String(128), default="")
    upload_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[str] = mapped_column(CHAR(1), default="")
    source_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
