"""印章与印章操作记录数据模型。"""

from datetime import datetime
from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class SealAsset(Base):
    """印章实物台账，和用印申请记录分离管理。"""

    __tablename__ = "seal_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    seal_type: Mapped[str] = mapped_column(String(64), index=True)
    custodian: Mapped[str] = mapped_column(String(64), index=True)
    location: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(32), index=True, default="可用")
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    remark: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SealAssetAudit(Base):
    """保留印章资产删除等不可逆台账操作的审计快照。"""

    __tablename__ = "seal_asset_audits"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(Integer, index=True)
    asset_code: Mapped[str] = mapped_column(String(64), index=True)
    asset_name: Mapped[str] = mapped_column(String(128), default="")
    action: Mapped[str] = mapped_column(String(64), index=True)
    operator: Mapped[str] = mapped_column(String(64), index=True)
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
