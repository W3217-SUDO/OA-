"""非诉申请人库（501187，思法汇成 2026-11-06）：手填的新申请人单独登记，不进当事人库，以后用于利益冲突检索。"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class IprApplicant(Base):
    __tablename__ = "ipr_applicants"

    id: Mapped[int] = mapped_column(primary_key=True)
    applicant_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(Text)
    # 同名只留一条：按规范化后的名称判断（去空格、全半角括号等，和客户同名判断一致）。
    normalized_name: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    created_by: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IprApplicantCase(Base):
    """申请人出现在哪些非诉案件（和当事人库一样按案件展开）。"""

    __tablename__ = "ipr_applicant_cases"
    __table_args__ = (UniqueConstraint("applicant_id", "case_id", name="uq_ipr_applicant_case"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    applicant_id: Mapped[int] = mapped_column(Integer, index=True)
    case_id: Mapped[int] = mapped_column(Integer, index=True)
    case_no: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
