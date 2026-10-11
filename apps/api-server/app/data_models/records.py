"""跨业务记录与操作事件数据模型。"""

from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, event, func, inspect
from sqlalchemy.orm import Mapped, Session, mapped_column
from app.database import Base


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


@event.listens_for(Session, "before_flush")
def record_case_phase_visits(session: Session, flush_context: object, instances: object) -> None:
    """记录非顾问案件的阶段进入与离开时间，重复进入也单独计时。"""
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    for record in session.dirty.union(session.new):
        if not isinstance(record, BusinessRecord) or record.module != "case":
            continue
        state = inspect(record)
        status_change = state.attrs.status.history
        if not status_change.has_changes():
            continue
        old_status = str(status_change.deleted[0] or "") if status_change.deleted else ""
        new_status = str(record.status or "")
        if old_status == new_status:
            continue
        data = dict(record.data or {})
        if str(data.get("case_type") or "") == "法律顾问":
            continue
        previous_data = state.attrs.data.history.deleted
        previous_start = (previous_data[0] or {}).get("phase_changed_at") if previous_data else data.get("phase_changed_at")
        visits = list(data.get("phase_visits") or [])
        if old_status:
            visits.append({"phase": old_status, "entered_at": previous_start or None, "left_at": now})
        data["phase_visits"] = visits
        data["phase_changed_at"] = now
        record.data = data


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
