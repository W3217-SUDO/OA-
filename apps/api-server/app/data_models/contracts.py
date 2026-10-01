"""合同标的、请付款与合同历史数据模型。"""

from datetime import datetime
from sqlalchemy import BigInteger, CHAR, DateTime, Float, ForeignKey, Identity, Integer, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ContractApprovalStep(Base):
    __tablename__ = "contract_approval_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    step_order: Mapped[int] = mapped_column(Integer)
    approver: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="等待中")
    comment: Mapped[str] = mapped_column(Text, default="")
    acted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ContractEvent(Base):
    """合同办理过程中的独立事项记录，不与审批/状态流水混用。"""

    __tablename__ = "contract_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text)
    operator: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ContractObject(Base):
    """A contract's independently maintained case/fee subject line."""

    __tablename__ = "contract_objects"

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    case_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id"), index=True)
    fee_type: Mapped[str] = mapped_column(String(64), default="")
    amount: Mapped[float] = mapped_column(Float, default=0)
    remark: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(64), index=True)
    updated_by: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ContractObjectLog(Base):
    __tablename__ = "contract_object_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_object_id: Mapped[int] = mapped_column(ForeignKey("contract_objects.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(64))
    before: Mapped[dict] = mapped_column(JSON, default=dict)
    after: Mapped[dict] = mapped_column(JSON, default=dict)
    operator: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ContractPaymentLine(Base):
    """One selected payable amount from a contract subject line.

    Contract payment requests have their own detail rows: a free-form finance
    record must never be able to impersonate an approved contract payment.
    """

    __tablename__ = "contract_payment_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id", ondelete="CASCADE"), index=True)
    contract_object_id: Mapped[int] = mapped_column(ForeignKey("contract_objects.id", ondelete="RESTRICT"), index=True)
    case_record_id: Mapped[int] = mapped_column(ForeignKey("business_records.id"), index=True)
    fee_type: Mapped[str] = mapped_column(String(64))
    requested_amount: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LegacyContract(Base):
    """Compatibility projection of the legacy FCM_Contract table."""

    __tablename__ = "FCM_Contract"

    # SQLite only auto-increments an exact INTEGER primary key. SQL Server
    # promotes this projection to bigint when it is migrated there.
    ContractId: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ContractNo: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    ContractGuid: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    RefContractNo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ContractName: Mapped[str | None] = mapped_column(String(200), nullable=True)
    CustomerId: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    CustomerNo: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    CompanyId: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    DepartmentId: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    BusinessOwner: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    ContractType: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ChargingType: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ContractMoney: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    TaxRate: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    ContractStatus: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    ContractBeginDate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ContractEndDate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    AuditFlowId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    AuditDate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    AuditFlowNodeId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    AuditRoundId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    Remark: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    IsChanged: Mapped[str | None] = mapped_column(CHAR(1), nullable=True)
    IsActived: Mapped[str | None] = mapped_column(CHAR(1), nullable=True, index=True)
    CreateUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    CreateTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    GroupId: Mapped[int | None] = mapped_column(Integer, nullable=True)


class LegacyContractAudit(Base):
    __tablename__ = "FCM_Contract_Audit"

    AuditId: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ContractId: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    ContractNo: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    AuditFlowId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    AuditFlowNodeId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    AuditRoundId: Mapped[int | None] = mapped_column(Integer, nullable=True)
    Auditor: Mapped[str | None] = mapped_column(String(20), nullable=True)
    AuditDate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    AuditStatus: Mapped[int | None] = mapped_column(Integer, nullable=True)
    AuditContent: Mapped[str | None] = mapped_column(String(200), nullable=True)
    CreateUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    CreateTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeUser: Mapped[str | None] = mapped_column(String(20), nullable=True)


class LegacyContractFile(Base):
    __tablename__ = "FCM_Contract_File"

    FileId: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    FileGuid: Mapped[str] = mapped_column(String(36), primary_key=True)
    ContractGuid: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    FileName: Mapped[str | None] = mapped_column(String(400), nullable=True)
    FilePath: Mapped[str | None] = mapped_column(String(500), nullable=True)
    FileSize: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    UploadUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    UploadTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    IsActived: Mapped[str | None] = mapped_column(CHAR(1), nullable=True, index=True)
    CreateUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
    CreateTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ChangeUser: Mapped[str | None] = mapped_column(String(20), nullable=True)
