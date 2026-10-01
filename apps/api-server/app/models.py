"""领域模型的稳定聚合入口，保留既有导入与完整 metadata 注册。"""

from datetime import date as date, datetime as datetime
from decimal import Decimal as Decimal
from sqlalchemy import BigInteger as BigInteger, Boolean as Boolean, CHAR as CHAR, CheckConstraint as CheckConstraint, Date as Date, DateTime as DateTime, Float as Float, ForeignKey as ForeignKey, Identity as Identity, Integer as Integer, JSON as JSON, Numeric as Numeric, String as String, Text as Text, UniqueConstraint as UniqueConstraint, func as func
from sqlalchemy.orm import Mapped as Mapped, mapped_column as mapped_column
from app.database import Base as Base
from app.legacy_schema import legacy_table_from_manifest as legacy_table_from_manifest

from app.data_models.identity import (
    Department as Department,
    JobRole as JobRole,
    HrSubrecord as HrSubrecord,
    User as User,
    SecurityPolicy as SecurityPolicy,
    SystemMenu as SystemMenu,
    RolePermission as RolePermission,
)
from app.data_models.parameters import (
    SystemParameter as SystemParameter,
    CaseTypeFileTypeRelation as CaseTypeFileTypeRelation,
    CaseFileTypeFeeTypeRelation as CaseFileTypeFeeTypeRelation,
    CaseTypeCasePhaseRelation as CaseTypeCasePhaseRelation,
    SystemConfig as SystemConfig,
)
from app.data_models.records import (
    BusinessRecord as BusinessRecord,
    WorkflowEvent as WorkflowEvent,
    CommunicationLog as CommunicationLog,
)
from app.data_models.tasks import (
    VipTask as VipTask,
    VipTaskNode as VipTaskNode,
    VipTaskMessage as VipTaskMessage,
    LegacyCaseTaskHistory as LegacyCaseTaskHistory,
    LegacyCaseTaskHistoryNode as LegacyCaseTaskHistoryNode,
    LegacyCaseTaskHistoryNodeParticipant as LegacyCaseTaskHistoryNodeParticipant,
    LegacyCaseTaskHistoryMessage as LegacyCaseTaskHistoryMessage,
    LegacyCaseTaskHistoryNotification as LegacyCaseTaskHistoryNotification,
    LegacyCaseTaskHistoryReadReceipt as LegacyCaseTaskHistoryReadReceipt,
    LegacyCaseTaskHistoryFile as LegacyCaseTaskHistoryFile,
)
from app.data_models.investigation import (
    InvestigationHistoricalReference as InvestigationHistoricalReference,
    InvestigationTaskLink as InvestigationTaskLink,
    InvestigationClueLink as InvestigationClueLink,
    InvestigationEvidence as InvestigationEvidence,
    InvestigationEvidenceFile as InvestigationEvidenceFile,
    LegacyInvestigation as LegacyInvestigation,
    LegacyInvestigationTask as LegacyInvestigationTask,
    LegacyInvestigationClue as LegacyInvestigationClue,
    LegacyInvestigationClueEvidence as LegacyInvestigationClueEvidence,
    LegacyInvestigationClueEvidenceFile as LegacyInvestigationClueEvidenceFile,
    LegacyInvestigationClueFile as LegacyInvestigationClueFile,
)
from app.data_models.warehouse import (
    Warehouse as Warehouse,
    WarehouseStorageLocation as WarehouseStorageLocation,
    WarehouseEvidenceLocation as WarehouseEvidenceLocation,
    WarehouseLegacyEvidenceMapping as WarehouseLegacyEvidenceMapping,
)
from app.data_models.finance import (
    JarFeeAuditLog as JarFeeAuditLog,
    ReceivablePlan as ReceivablePlan,
    CaseAssistedFee as CaseAssistedFee,
    FinanceTransaction as FinanceTransaction,
    ReconciliationBatch as ReconciliationBatch,
    IncomingPayment as IncomingPayment,
    LegacyFinanceRecord as LegacyFinanceRecord,
    LegacyFinanceAllocation as LegacyFinanceAllocation,
    LegacyFinanceFile as LegacyFinanceFile,
    LegacyFinanceAudit as LegacyFinanceAudit,
)
from app.data_models.contracts import (
    ContractApprovalStep as ContractApprovalStep,
    ContractEvent as ContractEvent,
    ContractObject as ContractObject,
    ContractObjectLog as ContractObjectLog,
    ContractPaymentLine as ContractPaymentLine,
    LegacyContract as LegacyContract,
    LegacyContractAudit as LegacyContractAudit,
    LegacyContractFile as LegacyContractFile,
)
from app.data_models.cases import (
    HearingSchedule as HearingSchedule,
    CaseEvent as CaseEvent,
    LegacyCase as LegacyCase,
    LegacyCaseFile as LegacyCaseFile,
    LegacyCaseParticipant as LegacyCaseParticipant,
    LegacyCaseLog as LegacyCaseLog,
    LegacyCasePhaseHistory as LegacyCasePhaseHistory,
    LegacyCaseParticipantRelation as LegacyCaseParticipantRelation,
    LegacyCaseAttachmentRelation as LegacyCaseAttachmentRelation,
    LegacyCaseLogProjection as LegacyCaseLogProjection,
    LegacyCaseMigrationQuarantine as LegacyCaseMigrationQuarantine,
)
from app.data_models.ipr_cases import (
    LawFirm as LawFirm,
    LawFirmContact as LawFirmContact,
    LawFirmAudit as LawFirmAudit,
    IprCaseLawFirm as IprCaseLawFirm,
    IprCaseCustomer as IprCaseCustomer,
    IprCaseCustomerContact as IprCaseCustomerContact,
    IprCaseLog as IprCaseLog,
    IprCaseBatch as IprCaseBatch,
    IprCaseBatchItem as IprCaseBatchItem,
    IprCaseRebootLink as IprCaseRebootLink,
    IprCaseTypeAssignment as IprCaseTypeAssignment,
    IprCaseTypeFileFeeTypeRule as IprCaseTypeFileFeeTypeRule,
)
from app.data_models.ipr_files import (
    IprOfficialImportBatch as IprOfficialImportBatch,
    IprOfficialImportCandidate as IprOfficialImportCandidate,
    IprCaseFileCustomImportBatch as IprCaseFileCustomImportBatch,
    IprCaseFileCustomImportCandidate as IprCaseFileCustomImportCandidate,
)
from app.data_models.ipr_fees import (
    IprCaseAssistedFee as IprCaseAssistedFee,
    IprFeeHeader as IprFeeHeader,
    IprFeeItem as IprFeeItem,
    IprFeeBill as IprFeeBill,
    IprFeeBillAttachmentMetadata as IprFeeBillAttachmentMetadata,
    IprFeeAuditLog as IprFeeAuditLog,
)
from app.data_models.ipr_reminders import (
    IprCaseReminder as IprCaseReminder,
    IprCaseReminderSuppression as IprCaseReminderSuppression,
    IprCaseReminderType as IprCaseReminderType,
    IprCaseAnnualFee as IprCaseAnnualFee,
    IprCaseWarningRule as IprCaseWarningRule,
    IprCaseWarning as IprCaseWarning,
)
from app.data_models.documents import (
    FileAttachment as FileAttachment,
    DocumentTemplate as DocumentTemplate,
    AgentDocument as AgentDocument,
    LegacyHistoricalAttachment as LegacyHistoricalAttachment,
)
from app.data_models.official_documents import (
    OfficialOutgoingDocument as OfficialOutgoingDocument,
    LegacyOfficialDocument as LegacyOfficialDocument,
    LegacyOfficialDocumentAudit as LegacyOfficialDocumentAudit,
    LegacyOfficialDocumentFile as LegacyOfficialDocumentFile,
)
from app.data_models.seals import (
    SealAsset as SealAsset,
    SealAssetAudit as SealAssetAudit,
)
from app.data_models.customers import (
    LegacyCustomer as LegacyCustomer,
    LegacyCustomerContact as LegacyCustomerContact,
    LegacyCustomerHistoryCoordinator as LegacyCustomerHistoryCoordinator,
    LegacyCustomerHistoryContact as LegacyCustomerHistoryContact,
    LegacyCustomerHistoryEvent as LegacyCustomerHistoryEvent,
    LegacyCustomerHistoryFile as LegacyCustomerHistoryFile,
    LegacyCustomerHistoryBaseline as LegacyCustomerHistoryBaseline,
)
from app.data_models.notifications import (
    Notification as Notification,
    NotificationDelivery as NotificationDelivery,
    NotificationSyncSchedule as NotificationSyncSchedule,
)
