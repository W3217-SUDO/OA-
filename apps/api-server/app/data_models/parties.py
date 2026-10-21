"""当事人表：当事人的独立档案，不占用客户表。"""

from datetime import datetime
from sqlalchemy import DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class PartyRecord(Base):
    __tablename__ = "parties"

    id: Mapped[int] = mapped_column(primary_key=True)
    # 从客户挪来的沿用原客户编号；新建的用 DSR + 两位年份 + 5 位流水（如 DSR2600001）。
    party_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(Text, index=True)
    # 原客户类型（申请人、未设置、当事人…）；新建的为“当事人”。
    party_type: Mapped[str] = mapped_column(String(32), index=True, default="当事人")
    # 挪自哪条客户记录；新建的为空。老案件按客户编号/编号引用时靠它对应。
    source_customer_id: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True, index=True)
    owner: Mapped[str] = mapped_column(String(64), default="")
    department: Mapped[str] = mapped_column(String(64), default="")
    managers: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), index=True, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(64), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
