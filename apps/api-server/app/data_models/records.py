"""跨业务记录与操作事件数据模型。"""

from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
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
