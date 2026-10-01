"""系统参数及业务类型关系数据模型。"""

from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class SystemParameter(Base):
    """可由管理员维护的案件、费用、法院等基础字典。"""

    __tablename__ = "system_parameters"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(32), index=True)
    code: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    extra: Mapped[dict] = mapped_column(JSON, default=dict)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by: Mapped[str] = mapped_column(String(64), default="system")
    updated_by: Mapped[str] = mapped_column(String(64), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CaseTypeFileTypeRelation(Base):
    """Applicability of an ordinary case-file type to a case type."""

    __tablename__ = "case_type_file_type_relations"
    __table_args__ = (
        UniqueConstraint("case_type_id", "file_type_id", name="uq_case_type_file_type_relation"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    case_type_id: Mapped[int] = mapped_column(
        ForeignKey("system_parameters.id", ondelete="CASCADE"), index=True,
    )
    file_type_id: Mapped[int] = mapped_column(
        ForeignKey("system_parameters.id", ondelete="CASCADE"), index=True,
    )
    created_by: Mapped[str] = mapped_column(String(64), default="system")
    updated_by: Mapped[str] = mapped_column(String(64), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CaseFileTypeFeeTypeRelation(Base):
    """Applicability of a fee type to an ordinary case-file type."""

    __tablename__ = "case_file_type_fee_type_relations"
    __table_args__ = (
        UniqueConstraint("file_type_id", "fee_type_id", name="uq_case_file_type_fee_type_relation"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    file_type_id: Mapped[int] = mapped_column(
        ForeignKey("system_parameters.id", ondelete="CASCADE"), index=True,
    )
    fee_type_id: Mapped[int] = mapped_column(
        ForeignKey("system_parameters.id", ondelete="CASCADE"), index=True,
    )
    created_by: Mapped[str] = mapped_column(String(64), default="system")
    updated_by: Mapped[str] = mapped_column(String(64), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CaseTypeCasePhaseRelation(Base):
    """Allowed case phases for a case type."""

    __tablename__ = "case_type_case_phase_relations"
    __table_args__ = (
        UniqueConstraint("case_type_id", "case_phase_id", name="uq_case_type_case_phase_relation"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    case_type_id: Mapped[int] = mapped_column(
        ForeignKey("system_parameters.id", ondelete="CASCADE"), index=True,
    )
    case_phase_id: Mapped[int] = mapped_column(
        ForeignKey("system_parameters.id", ondelete="CASCADE"), index=True,
    )
    created_by: Mapped[str] = mapped_column(String(64), default="system")
    updated_by: Mapped[str] = mapped_column(String(64), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SystemConfig(Base):
    """公司资料、客户共享规则和运行配置等结构化系统设置。"""

    __tablename__ = "system_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(128))
    group: Mapped[str] = mapped_column(String(32), index=True, default="业务配置")
    value: Mapped[dict] = mapped_column(JSON, default=dict)
    description: Mapped[str] = mapped_column(Text, default="")
    updated_by: Mapped[str] = mapped_column(String(64), default="system")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
