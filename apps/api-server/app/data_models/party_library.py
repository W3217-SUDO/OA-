"""当事人库：把案件中的主体（客户/当事人）按所在案件展开成一行一人，由案件数据重建。"""

from datetime import datetime
from sqlalchemy import DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class PartyLibraryEntry(Base):
    __tablename__ = "party_library"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(Integer, index=True)
    case_no: Mapped[str] = mapped_column(String(64), index=True)
    # 民事 / 行政 / 刑事 / 仲裁 / 其他（法律顾问等），由案件类型归并。
    case_category: Mapped[str] = mapped_column(String(16), index=True, default="其他")
    # 当事人编号：从客户挪来的沿用原客户编号，新建的用 DSR 编号；案件里尚无档案的为空。
    party_no: Mapped[str] = mapped_column(String(64), index=True, default="")
    customer_record_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    party_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    subject_name: Mapped[str] = mapped_column(Text, index=True)
    # 客户：案件委托人或已登记的客户；当事人：案件中的其他主体。
    subject_type: Mapped[str] = mapped_column(String(16), index=True)
    subject_position: Mapped[str] = mapped_column(String(32), default="")
    our_parties: Mapped[list] = mapped_column(JSON, default=list)
    our_position: Mapped[str] = mapped_column(String(32), default="")
    opponent_parties: Mapped[list] = mapped_column(JSON, default=list)
    opponent_position: Mapped[str] = mapped_column(String(32), default="")
    managers: Mapped[list] = mapped_column(JSON, default=list)
    # "|u1|u2|" 形式，便于按用户名精确匹配“我的/部门”范围。
    manager_key: Mapped[str] = mapped_column(Text, default="")
    # 已删除的案件只在回收站范围显示。
    # 案件阶段与归档/结案日期（利益冲突检索要看案件是否结案）。
    case_phase: Mapped[str] = mapped_column(String(64), default="")
    closed_at: Mapped[str] = mapped_column(String(32), default="")
    case_status: Mapped[str] = mapped_column(String(32), index=True, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
