"""数据变更留痕：每次新增、修改、删除、恢复记录变更前后的值、操作人和来源，供管理员查看和一键还原。"""

from datetime import datetime
from sqlalchemy import JSON, BigInteger, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class DataChangeLog(Base):
    __tablename__ = "data_change_logs"
    __table_args__ = (Index("ix_data_change_logs_table_row", "table_name", "row_id"),)

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    table_name: Mapped[str] = mapped_column(String(64))
    row_id: Mapped[str] = mapped_column(String(128))  # 按字符串存：旧系统导入表的主键是字符串；"0" 表示批量摘要
    action: Mapped[str] = mapped_column(String(16), index=True)  # insert / update / delete / restore
    changes: Mapped[dict] = mapped_column(JSON, default=dict)  # {列名: [变更前, 变更后]}；JSON 列只记变动的键
    summary: Mapped[str] = mapped_column(String(255), default="")
    actor: Mapped[str] = mapped_column(String(64), index=True, default="system")
    source: Mapped[str] = mapped_column(String(16), index=True, default="system")  # web / mcp / agent / system
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    reverted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reverted_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    revert_of: Mapped[int | None] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), nullable=True)
