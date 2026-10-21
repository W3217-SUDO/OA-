"""当事人独立表：与委托客户分开存放，记录编号沿用 business_records.id。"""

from datetime import datetime
from sqlalchemy import DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Party(Base):
    """customer 记录中类型不是“客户”的行的独立副本，由数据库触发器随源记录同步。"""

    __tablename__ = "parties"

    # 与 business_records.id 相同，合同、案件、线索对它们的引用无需改动。
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    serial_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(Text, index=True, default="")
    party_type: Mapped[str] = mapped_column(String(64), index=True, default="")
    status: Mapped[str] = mapped_column(String(32), index=True, default="")
    owner: Mapped[str] = mapped_column(String(64), index=True, default="")
    department: Mapped[str] = mapped_column(String(64), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
