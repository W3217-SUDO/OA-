"""站内通知、持久发件箱及生成调度数据模型。"""

from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


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


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"
    __table_args__ = (
        UniqueConstraint("channel", "business_key", name="uq_notification_delivery_business"),
        UniqueConstraint("channel", "notification_id", name="uq_notification_delivery_notification"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    channel: Mapped[str] = mapped_column(String(16), index=True)
    business_key: Mapped[str] = mapped_column(String(255))
    notification_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    source_record_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    destination: Mapped[str] = mapped_column(String(255), default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    state: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    claim_token: Mapped[str] = mapped_column(String(64), default="")
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_reference: Mapped[str] = mapped_column(String(500), default="")
    error: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NotificationSyncSchedule(Base):
    __tablename__ = "notification_sync_schedules"

    username: Mapped[str] = mapped_column(String(64), primary_key=True)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    claim_token: Mapped[str] = mapped_column(String(64), default="")
    last_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str] = mapped_column(String(500), default="")
