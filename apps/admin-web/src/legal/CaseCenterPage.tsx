import {
CloseOutlined,
CommentOutlined,
DownloadOutlined,
InfoCircleOutlined,
MinusCircleOutlined,
PlusOutlined,
ReloadOutlined,
RobotOutlined,
UploadOutlined
} from "@ant-design/icons";
import type { UploadFile } from "antd";
import {
Alert,
Button,
Card,
Checkbox,
DatePicker,
Descriptions,
Drawer,
Dropdown,
Form,
Input,
InputNumber,
List,
message,
Modal,
Radio,
Select,
Space,
Statistic,
Steps,
Table,
Tabs,
Tag,
TimePicker,
TreeSelect,
Upload
} from "antd";
import dayjs from "dayjs";
import type { Key } from "react";
import { useEffect,useMemo,useRef,useState,type ClipboardEvent } from "react";
import { DEFAULT_AGENT_SKILL } from "../agentSkillRouting";
import { api } from "../api";
import { rememberBusinessRecordDetailTarget } from "../businessRecordDetailNavigation";
import "../case-center.css";
import { caseAssistantDisplayValues } from "../caseAssistantDisplay";
import { buildCaseContractOptions } from "../caseContractPrefill";
import { buildCaseCounselSearchPayload } from "../caseCounselSearchParity.mjs";
import { rememberCaseDetailTarget } from "../caseDetailNavigation";
import { buildCaseFeeContractOptions } from "../caseFeeContractOptions.mjs";
import {
buildCaseFileTypeTreeOptions,
getCaseArchivePagination,
getCaseTaskPagination,
getCaseUnarchiveRequestValidationError,
resolveCaseFileTypeSelection
} from "../caseFifthBatchParity.mjs";
import {
getCaseAttachmentSelectionValidationError,
getCaseFilePagination,
hasCaseFileTypeOption
} from "../caseFileFrontendParity.mjs";
import {
getLegacyCaseListDefaults,
getLegacyCaseListOperationLabels,
getLegacyCaseListOperationState,
} from "../caseLegacyParity";
import {
buildLegacyCasePhaseTree,
createLatestRequestGuard,
dashboardCaseQueryForView,
LEGACY_DEFAULT_EXPANDED_PHASE_GROUPS,
legacyCasePhaseFilterValues,
ordinaryCaseQueueForView,
ordinaryCaseTypesForView,
ordinaryCustomerIdForView
} from "../caseOrdinarySearchParity.mjs";
import { buildCasePaymentTypeSelectOptions } from "../casePaymentUnitParity.mjs";
import {
filterCaseFileTypesForCaseType,
filterCasePhasesForCaseType,
normalizeFeeSubtypeForScope
} from "../caseRelationConsumption.mjs";
import {
CASE_EXECUTION_STATUSES,
prioritizeCaseAssistantSelection
} from "../caseSecondBatchParity";
import { buildWarehouseLocationOptions,resolveCaseWarehouseLocationIds } from "../caseWarehouseLocationParity.mjs";
import {
buildCaseUnarchiveReviewPayload,
getCaseHearingDeleteValidationError,
getCaseUnarchiveReviewValidationError
} from "../caseWorkflowFrontendParity.mjs";
import { AttachmentPreviewContent } from "../components/common/AttachmentContent";
import { ListFilterBar } from "../components/common/ListFilterBar";
import { rememberContractDetailTarget } from "../contractDetailNavigation";
import { consumeCustomerRelationTarget } from "../customerRelationNavigation";
import {
feeTypeSelection,
feeTypeTreeData,
initialFeeTypeId,
type FeeTypeCatalogItem,
} from "../feeTypeHierarchy.mjs";
import { readStoredGlobalCaseSearchContext } from "../globalCaseSearchParity.mjs";
import { incomingPaymentDetailRoute } from "../incomingPaymentDetailNavigation";
import { LegacyLsHistoryPanel } from "../LegacyLsHistoryPanel";
import "../task-center.css";
import { createArchiveColumns } from "./columns/archiveColumns";
import { createCaseColumns } from "./columns/caseColumns";
import { createExternalCaseFeeColumns } from "./columns/externalCaseFeeColumns";
import { createGroupedOriginalCaseColumns } from "./columns/groupedOriginalCaseColumns";
import { createHearingColumns } from "./columns/hearingColumns";
import { createOriginalArchiveColumns } from "./columns/originalArchiveColumns";
import { createSpecialColumns } from "./columns/specialColumns";
import { useCaseAgentDrawer } from "./hooks/useCaseAgentDrawer";
import { createCaseAssistantActions } from "./services/assistantActions";
import { createCaseDocumentsActions } from "./services/documentsActions";
import { createCaseFinanceActions } from "./services/financeActions";
import { createCaseQueriesActions } from "./services/queriesActions";
import { createCaseWorkflowActions } from "./services/workflowActions";

// ============================================================
// Types and constants imported from modular files
// ============================================================
import type {
AttachmentPreview,
AttachmentRow,
CaseAgentAttachment,
CaseAgentDocument,
CaseAgentState,
CaseAgentStatus,
CaseAiDraftEditor,
CaseAssistedFee,
CaseClueEvidenceRow,
CaseClueWorkspace,
CaseCommissionPreview,
CaseCommissionPreviewRow,
CaseCommissionResult,
CaseDetailCapabilities,
CaseDocumentFolderEditor,
CaseEventCapabilities,
CaseEventRow,
CaseFeeIncomingPaymentLink,
CaseFileTypeOption,
CaseLitigantAgentField,
CaseLitigantCandidate,
CaseLitigantPartyField,
CaseLogKind,
CaseLogRow,
CasePaymentTypeOption,
CasePhaseOption,
CasePhaseTreeItem,
CaseRelationCatalog,
CaseReminderRow,
CaseRow,
CaseTaskAttachment,
CaseTaskHistoryItem,
CaseTaskKind,
CaseWordEditor,
CompanyScheduleCourtLevel,
ContractRow,
Hearing,
PaymentTypeCreateTarget,
Profile,
TaskRow,
WarehouseCatalogOption
} from "./types";

import {
AGENT_CASE_DOCUMENT_FOLDERS,
AGENT_DOCUMENT_LIMIT,
AGENT_INVESTIGATION_DOCUMENT_FOLDERS,
ARCHIVE_FINAL_STATUSES,
ARCHIVE_LOCKED_STATUSES,
ARCHIVE_REVIEW_STATUSES,
buildCasePhaseItems,
buildCasePhaseItemsFromCounts,
CASE_LITIGANT_AGENT_LABELS,
CASE_LITIGANT_PARTY_LABELS,
CASE_PHASE_ROOT_LABELS,
CASE_TASK_DEFAULT_PAGE,
CASE_TASK_DEFAULT_PAGE_SIZE,
caseDetailDate,
caseDetailNames,
CasePhasePickerTree,
caseStatuses,
caseTaskTypeLabel,
DEFAULT_CASE_ATTACHMENT_CATEGORY,
getCaseDocumentMoveCategoryOptions,
getCasePhaseDefinitions,
getCompanyArbitrationColumnSchema,
getCompanyArbitrationQueryFields,
getCompanyCriminalColumnSchema,
getCompanyCriminalQueryFields,
getCompanyScheduleCourtLevels,
getCompanySchedulePageSizeOptions,
getCompanyScheduleQueryFields,
getCompanyScheduleQueryInitialValues,
getCustomCaseDocumentFolders,
getLegacyCaseDetailMoreOperationLabels,
getLegacyCaseDetailPrimaryOperationLabels,
isCivilCaseType,
isCompanyCaseListRoute,
isNormalCaseBasicType,
LEGACY_PHASE_GROUPS,
noCaseDetailWriteCapability,
noCaseEventCapabilities,
normalizeCaseLitigantAgents,
normalizeCaseTaskPageState,
renderCaseLitigantAgentSummary,
shouldShowCaseListActions,
shouldShowCompanyScheduleActions,
shouldShowCompanyScheduleSinglePageJumper,
shouldUseCompanyArbitrationColumns,
shouldUseCompanyArbitrationQueryFields,
shouldUseCompanyCriminalQueryFields,
shouldUseCompanySchedulePagination,
shouldUseCompanyScheduleQueryFields,
statusColors
} from "./constants";

import { CaseAgentDrawer } from "./CaseAgentDrawer";
import { CaseCreateWizard } from "./CaseCreateWizard";
import {
CaseAssistedFeesPanel,
CaseCaseLogsPanel,
CaseCaseTasksPanel,
CaseCluesPanel,
CaseCustomerTasksPanel,
CaseDetailHeader,
CaseDocumentsPanel,
CaseEventsPanel,
CaseFeesPanel,
CaseRemindersPanel,
CaseSystemLogsPanel,
} from "./CaseDetail";

// Re-export types and named exports for backward compatibility
export type {
AttachmentRow,
CaseAssistedFee,
CaseDetailCapabilities,CaseLitigantAgent,CasePhaseListItem,CasePhaseOption,CasePhaseTreeItem,CaseRow,CaseTaskPageState,ContractRow,
Hearing,
TaskRow
} from "./types";

export {
buildCasePhaseItems,
buildCasePhaseItemsFromCounts,CasePhasePickerTree,getCaseDocumentMoveCategoryOptions,getCasePhaseDefinitions,getCompanyArbitrationColumnSchema,getCompanyArbitrationQueryFields,getCompanyCriminalColumnSchema,getCompanyCriminalQueryFields,getCompanyScheduleCourtLevels,getCompanySchedulePageSizeOptions,getCompanyScheduleQueryFields,
getCompanyScheduleQueryInitialValues,getLegacyCaseDetailMoreOperationLabels,getLegacyCaseDetailPrimaryOperationLabels,getLegacyCaseDocumentGenerationItems,getLegacyGroupedCaseColumnSchema,isCivilCaseType,isCompanyCaseListRoute,isMyCaseListRoute,isNormalCaseBasicType,scopeCasesByListRoute,shouldShowCaseListActions,shouldShowCompanyScheduleActions,shouldShowCompanyScheduleSinglePageJumper,shouldUseCompanyArbitrationColumns,shouldUseCompanyArbitrationQueryFields,shouldUseCompanyCriminalQueryFields,shouldUseCompanySchedulePagination,shouldUseCompanyScheduleQueryFields
} from "./constants";

export default function CaseCenterPage({
  initialView,
  onNavigate,
}: {
  initialView: string;
  onNavigate?: (route: string) => void;
}) {
  const isCreateView = initialView === "case-new" || initialView.startsWith("case-new-");
  const isCaseDetailView = initialView.startsWith("case-detail-");
  const detailRouteMatch = initialView.match(/^case-detail-(\d+)-(.+)$/);
  const detailRouteId = Number(detailRouteMatch?.[1] || 0);
  const createRouteType = initialView.endsWith("criminal") ? "刑事案件"
    : initialView.endsWith("administrative") ? "行政案件及国家赔偿"
      : initialView.endsWith("counsel") ? "法律顾问"
        : initialView.endsWith("arbitration") ? "仲裁" : "民事案件";
  const [selectedCreateType, setSelectedCreateType] = useState(createRouteType);
  const effectiveCreateType = initialView === "case-new" ? selectedCreateType : createRouteType;
  const isCriminalCreate = effectiveCreateType === "刑事案件";
  const isAdministrativeCreate = effectiveCreateType === "行政案件及国家赔偿";
  const isCounselCreate = effectiveCreateType === "法律顾问";
  const createFlowToken = isCounselCreate ? "CASE_NEW_COUNSEL_STAGED_FLOW_OK"
    : isAdministrativeCreate ? "CASE_NEW_ADMINISTRATIVE_STAGED_FLOW_OK"
      : effectiveCreateType === "民事案件" ? "CASE_NEW_CIVIL_STAGED_FLOW_OK" : "CASE_NEW_CRIMINAL_STAGED_FLOW_OK";
  const createRedirectPage = isCounselCreate ? "case-company-counsel"
    : isAdministrativeCreate ? "case-company-administrative"
      : effectiveCreateType === "民事案件" ? "case-company-civil"
        : effectiveCreateType === "仲裁" ? "case-company-arbitration" : "case-company-criminal";
  const clientPositionOptions = isCriminalCreate ? ["被告人/犯罪嫌疑人", "被害人"] : ["原告/申请人", "被告/被申请人", "第三人"];
  const litigantLabels = isAdministrativeCreate
    ? { plaintiff: "原告/申请人", plaintiffAgent: "原告/申请人代理人", defendant: "被告/被申请人", defendantAgent: "被告/被申请人代理人", third: "第三人", thirdAgent: "第三人代理人" }
    : { plaintiff: "原告", plaintiffAgent: "原告代理人", defendant: "被告", defendantAgent: "被告代理人", third: "第三人", thirdAgent: "第三人代理人" };
  const [contractPrefill] = useState<{ id: number; serial_no: string; title: string; customer: string } | null>(() => {
    try {
      const value = JSON.parse(sessionStorage.getItem("sunhold:case-contract-context") || "null");
      sessionStorage.removeItem("sunhold:case-contract-context");
      return value;
    } catch {
      sessionStorage.removeItem("sunhold:case-contract-context");
      return null;
    }
  });
  const first =
    initialView.endsWith("-schedule") || initialView === "case-schedule"
      ? "hearing"
      : initialView.endsWith("-execution") || initialView === "case-execution"
        ? "execution"
        : initialView.startsWith("case-archive")
          ? "archive"
          : "cases";
  const [caseListReturnContext] = useState<{route?:string;page?:number;pageSize?:number;query?:Record<string,any>} | null>(() => {
    return readStoredGlobalCaseSearchContext(sessionStorage) as {route?:string;page?:number;pageSize?:number;query?:Record<string,any>} | null;
  });
  const pendingListReturnContext = useRef(caseListReturnContext);
  const [tab, setTab] = useState(first);
  const [cases, setCases] = useState<CaseRow[]>([]);
  const [pendingExecutionCases, setPendingExecutionCases] = useState<CaseRow[]>([]);
  const [pendingExecutionTotal, setPendingExecutionTotal] = useState(0);
  const [pendingExecutionPage, setPendingExecutionPage] = useState(1);
  const [pendingExecutionPageSize, setPendingExecutionPageSize] = useState(20);
  const [ordinaryCases, setOrdinaryCases] = useState<CaseRow[]>([]);
  const [ordinaryLoading, setOrdinaryLoading] = useState(true);
  const [ordinaryLoadError, setOrdinaryLoadError] = useState("");
  const [ordinaryTotal, setOrdinaryTotal] = useState(0);
  const [ordinaryPhaseCounts, setOrdinaryPhaseCounts] = useState<Record<string, number>>({});
  const ordinaryRequestGuard = useRef(createLatestRequestGuard()).current;
  const [counselCases, setCounselCases] = useState<CaseRow[]>([]);
  const [counselTotal, setCounselTotal] = useState(0);
  const [counselPage, setCounselPage] = useState(1);
  const [counselPageSize, setCounselPageSize] = useState(10);
  const [originalPage, setOriginalPage] = useState(caseListReturnContext?.page || 1);
  const [originalPageSize, setOriginalPageSize] = useState(caseListReturnContext?.pageSize || 15);
  const [companySchedulePage, setCompanySchedulePage] = useState(1);
  const [companySchedulePageSize, setCompanySchedulePageSize] = useState(20);
  const [contracts, setContracts] = useState<ContractRow[]>([]);
  const [caseCustomers, setCaseCustomers] = useState<CaseRow[]>([]);
  const [caseClues, setCaseClues] = useState<CaseRow[]>([]);
  const [caseTypeOptions, setCaseTypeOptions] = useState<{value:string;label:string}[]>([]);
  const [causeOptions, setCauseOptions] = useState<{value:string;label:string}[]>([]);
  const [rightTypeOptions, setRightTypeOptions] = useState<{value:string;label:string}[]>([]);
  const [caseLawyerOptions, setCaseLawyerOptions] = useState<{value:string;label:string}[]>([]);
  const [caseAssistantOptions, setCaseAssistantOptions] = useState<{value:string;label:string}[]>([]);
  const [profile, setProfile] = useState<Profile>(() => {
    try {
      const stored = JSON.parse(localStorage.getItem("user") || "{}");
      return {
        username: stored.username || "",
        display_name: stored.display_name || "",
        department: stored.department || "",
      };
    } catch {
      return { username: "", display_name: "", department: "" };
    }
  });
  const [hearings, setHearings] = useState<Hearing[]>([]);
  const [financeRows,setFinanceRows]=useState<CaseRow[]>([]);
  const [attachments,setAttachments]=useState<AttachmentRow[]>([]);
  const [summary, setSummary] = useState({
    total: 0,
    pending_assignment: 0,
    in_progress: 0,
    execution: 0,
    archived: 0,
  });
  const [loading, setLoading] = useState(false);
  const [showArchived, setShowArchived] = useState(false);
  const [createStep, setCreateStep] = useState(0);
  const [createdCaseId, setCreatedCaseId] = useState<number | null>(null);
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [assigning, setAssigning] = useState<CaseRow | null>(null);
  const [hearingOpen, setHearingOpen] = useState(false);
  const [archiving, setArchiving] = useState<CaseRow | null>(null);
  const [archiveType, setArchiveType] = useState<"normal" | "deficit">("normal");
  const [archiveChecks, setArchiveChecks] = useState<Record<string, boolean>>({});
  const [reviewing, setReviewing] = useState<{
    row: CaseRow;
    approved: boolean;
  } | null>(null);
  const [progressEditing, setProgressEditing] = useState<CaseRow | null>(null);
  const [phaseEditing, setPhaseEditing] = useState<CaseRow[] | null>(null);
  const [phaseOptions, setPhaseOptions] = useState<CasePhaseOption[]>([]);
  const [phaseCatalog, setPhaseCatalog] = useState<CasePhaseOption[]>([]);
  const [expandedPhaseGroups, setExpandedPhaseGroups] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(LEGACY_DEFAULT_EXPANDED_PHASE_GROUPS.map((label) => [label, true])),
  );
  const [executionStatusEditing, setExecutionStatusEditing] = useState<CaseRow[] | null>(null);
  const [companyScheduleCourtInfo, setCompanyScheduleCourtInfo] = useState<{ row: CaseRow; level: CompanyScheduleCourtLevel } | null>(null);
  const [taskCase, setTaskCase] = useState<CaseRow | null>(null);
  const [viewingCounselCase, setViewingCounselCase] = useState<CaseRow | null>(null);
  const [viewingFeeIncomingPayments, setViewingFeeIncomingPayments] = useState<CaseFeeIncomingPaymentLink[] | null>(null);
  const [legacyLsHistoryCaseIds, setLegacyLsHistoryCaseIds] = useState<Record<number, number>>({});
  const [legacyLsHistoryOpen, setLegacyLsHistoryOpen] = useState(false);
  const [activeCounselDetailTab, setActiveCounselDetailTab] = useState("documents");
  const [agentCase, setAgentCase] = useState<CaseRow | null>(null);
  const [agentOpen, setAgentOpen] = useState(false);
  const [agentStatus, setAgentStatus] = useState<CaseAgentStatus | null>(null);
  const [agentState, setAgentState] = useState<CaseAgentState | null>(null);
  const [agentLoading, setAgentLoading] = useState(false);
  const [agentSending, setAgentSending] = useState(false);
  const [agentDecisionLoading, setAgentDecisionLoading] = useState("");
  const [agentInput, setAgentInput] = useState("");
  const [agentSkillId, setAgentSkillId] = useState(DEFAULT_AGENT_SKILL);
  const [agentScreenshots, setAgentScreenshots] = useState<CaseAgentAttachment[]>([]);
  const [agentScreenshotUploading, setAgentScreenshotUploading] = useState(false);
  const [agentDocuments, setAgentDocuments] = useState<CaseAgentDocument[]>([]);
  const [agentDocumentIds, setAgentDocumentIds] = useState<number[]>([]);
  const [agentMaterialPickerOpen, setAgentMaterialPickerOpen] = useState(false);
  const { agentDrawerWidth, setAgentDrawerWidth, startAgentDrawerResize } = useCaseAgentDrawer();
  const [agentHistoryExpanded, setAgentHistoryExpanded] = useState(false);
  const agentMessagesEndRef = useRef<HTMLDivElement>(null);
  const agentScreenshotInputRef = useRef<HTMLInputElement>(null);
  const agentScreenshotPreviewUrlsRef = useRef(new Map<number, string>());
  const activeCaseAgentRequestRef = useRef<AbortController | null>(null);
  const stateWithAgentScreenshotPreviews = (nextState: CaseAgentState) => ({
    ...nextState,
    messages: (nextState.messages || []).map((item) => ({
      ...item,
      attachments: item.attachments?.map((attachment) => ({
        ...attachment,
        preview_url: agentScreenshotPreviewUrlsRef.current.get(attachment.id),
      })),
    })),
  });
  const clearAgentScreenshotPreviews = () => {
    agentScreenshotPreviewUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
    agentScreenshotPreviewUrlsRef.current.clear();
  };
  const removeAgentScreenshot = (attachment: CaseAgentAttachment) => {
    const previewUrl = agentScreenshotPreviewUrlsRef.current.get(attachment.id);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    agentScreenshotPreviewUrlsRef.current.delete(attachment.id);
    setAgentScreenshots((current) => current.filter((entry) => entry.id !== attachment.id));
  };
  const [mergingCase, setMergingCase] = useState<CaseRow | null>(null);
  const [notaryInfoCase, setNotaryInfoCase] = useState<CaseRow | null>(null);
  const [settlementAmountCase, setSettlementAmountCase] = useState<CaseRow | null>(null);
  const [counselDetailHistory, setCounselDetailHistory] = useState<any[]>([]);
  const [counselDetailTasks, setCounselDetailTasks] = useState<TaskRow[]>([]);
  const [counselDetailCustomerTasks, setCounselDetailCustomerTasks] = useState<TaskRow[]>([]);
  const [counselDetailFinance, setCounselDetailFinance] = useState<CaseRow[]>([]);
  const [counselDetailAssistedFees, setCounselDetailAssistedFees] = useState<CaseAssistedFee[]>([]);
  const [counselDetailAssistedFeePage, setCounselDetailAssistedFeePage] = useState(1);
  const [counselDetailAssistedFeePageSize, setCounselDetailAssistedFeePageSize] = useState(15);
  const [counselDetailAssistedFeeTotal, setCounselDetailAssistedFeeTotal] = useState(0);
  const [assistedFeeEditor, setAssistedFeeEditor] = useState<CaseAssistedFee | null>(null);
  const [assistedFeeModalOpen, setAssistedFeeModalOpen] = useState(false);
  const [assistedFeeConfirming, setAssistedFeeConfirming] = useState<CaseAssistedFee | null>(null);
  const [assistedFeeSaving, setAssistedFeeSaving] = useState(false);
  const [counselDetailClues, setCounselDetailClues] = useState<CaseRow[]>([]);
  const [counselDetailCluePage, setCounselDetailCluePage] = useState(1);
  const [counselDetailCluePageSize, setCounselDetailCluePageSize] = useState(10);
  const [counselDetailClueTotal, setCounselDetailClueTotal] = useState(0);
  const [counselDetailCluePages, setCounselDetailCluePages] = useState(0);
  const [counselDetailClueKeyword, setCounselDetailClueKeyword] = useState("");
  const [counselDetailClueSearchInput, setCounselDetailClueSearchInput] = useState("");
  const [counselDetailClueLoading, setCounselDetailClueLoading] = useState(false);
  const [viewingCaseClue, setViewingCaseClue] = useState<CaseClueWorkspace | null>(null);
  const [caseClueLoading, setCaseClueLoading] = useState(false);
  const [selectedCaseClueEvidenceId, setSelectedCaseClueEvidenceId] = useState<number | null>(null);
  const [editingCaseClueEvidence, setEditingCaseClueEvidence] = useState<CaseClueEvidenceRow | null>(null);
  const [counselDetailTaskPage, setCounselDetailTaskPage] = useState(CASE_TASK_DEFAULT_PAGE);
  const [counselDetailTaskPageSize, setCounselDetailTaskPageSize] = useState(CASE_TASK_DEFAULT_PAGE_SIZE);
  const [counselDetailTaskTotal, setCounselDetailTaskTotal] = useState(0);
  const [counselDetailTaskPages, setCounselDetailTaskPages] = useState(0);
  const [counselDetailCustomerTaskPage, setCounselDetailCustomerTaskPage] = useState(CASE_TASK_DEFAULT_PAGE);
  const [counselDetailCustomerTaskPageSize, setCounselDetailCustomerTaskPageSize] = useState(CASE_TASK_DEFAULT_PAGE_SIZE);
  const [counselDetailCustomerTaskTotal, setCounselDetailCustomerTaskTotal] = useState(0);
  const [counselDetailCustomerTaskPages, setCounselDetailCustomerTaskPages] = useState(0);
  const [counselDetailAttachments, setCounselDetailAttachments] = useState<AttachmentRow[]>([]);
  const [generatingCaseDocumentType, setGeneratingCaseDocumentType] = useState("");
  const [caseDocumentGenerationError, setCaseDocumentGenerationError] = useState("");
  const [caseDocumentGenerationMenuOpen, setCaseDocumentGenerationMenuOpen] = useState(false);
  const [counselDetailCustomerAttachments, setCounselDetailCustomerAttachments] = useState<AttachmentRow[]>([]);
  const [counselDetailContractAttachments, setCounselDetailContractAttachments] = useState<AttachmentRow[]>([]);
  const [attachmentPreview, setAttachmentPreview] = useState<AttachmentPreview | null>(null);
  const [attachmentPreviewLoading, setAttachmentPreviewLoading] = useState(false);
  const [renamingCounselAttachment, setRenamingCounselAttachment] = useState<AttachmentRow | null>(null);
  const [aiDraftEditor, setAiDraftEditor] = useState<CaseAiDraftEditor | null>(null);
  const [wordEditor, setWordEditor] = useState<CaseWordEditor | null>(null);
  const [wordEditorOpening, setWordEditorOpening] = useState(false);
  const [wordEditorSaving, setWordEditorSaving] = useState(false);
  const [wordEditorLockLost, setWordEditorLockLost] = useState(false);
  const wordEditorSavingRef = useRef(false);
  const wordEditorLockTokenRef = useRef("");
  const [promotingAiDraft, setPromotingAiDraft] = useState<AttachmentRow | null>(null);
  const [sealingCounselAttachment, setSealingCounselAttachment] = useState<AttachmentRow | null>(null);
  const [movingCounselAttachmentIds, setMovingCounselAttachmentIds] = useState<number[] | null>(null);
  const [caseSealAssets, setCaseSealAssets] = useState<{ id: number; status: string; seal_type: string; name: string }[]>([]);
  const [counselReminders, setCounselReminders] = useState<CaseReminderRow[]>([]);
  const [counselCaseEvents, setCounselCaseEvents] = useState<CaseEventRow[]>([]);
  const [counselCaseEventCapabilities, setCounselCaseEventCapabilities] = useState<CaseEventCapabilities>(noCaseEventCapabilities);
  const [counselCaseEventsError, setCounselCaseEventsError] = useState("");
  const [selectedCounselCaseEventKeys, setSelectedCounselCaseEventKeys] = useState<Key[]>([]);
  const [caseEventOpen, setCaseEventOpen] = useState(false);
  const [editingCaseEvent, setEditingCaseEvent] = useState<CaseEventRow | null>(null);
  const [caseEventSubmitting, setCaseEventSubmitting] = useState(false);
  const [counselLogs, setCounselLogs] = useState<CaseLogRow[]>([]);
  const [counselDetailCapabilities, setCounselDetailCapabilities] = useState<CaseDetailCapabilities>(noCaseDetailWriteCapability);
  const [caseActionCapabilities, setCaseActionCapabilities] = useState<Record<number, CaseDetailCapabilities>>({});
  const [selectedCounselAttachmentKeys, setSelectedCounselAttachmentKeys] = useState<Key[]>([]);
  const [selectedFirmFeeKeys, setSelectedFirmFeeKeys] = useState<Key[]>([]);
  const [selectedPlatformFeeKeys, setSelectedPlatformFeeKeys] = useState<Key[]>([]);
  const [selectedInternalFeeKeys, setSelectedInternalFeeKeys] = useState<Key[]>([]);
  const [informDateFeeKeys, setInformDateFeeKeys] = useState<Key[] | null>(null);
  const [caseCommissionPreview, setCaseCommissionPreview] = useState<CaseCommissionPreview | null>(null);
  const [caseCommissionRows, setCaseCommissionRows] = useState<CaseCommissionPreviewRow[]>([]);
  const [caseCommissionResult, setCaseCommissionResult] = useState<CaseCommissionResult | null>(null);
  const [caseCommissionLoading, setCaseCommissionLoading] = useState(false);
  const [caseCommissionSubmitting, setCaseCommissionSubmitting] = useState(false);
  const [activeCounselDocCategory, setActiveCounselDocCategory] = useState("");
  const [expandedCounselDocGroups, setExpandedCounselDocGroups] = useState<Record<string, boolean>>({
    "调查文档全部": true,
    "案件文档全部": true,
  });
  const [caseDocumentFolderEditor, setCaseDocumentFolderEditor] = useState<CaseDocumentFolderEditor | null>(null);
  const [counselUploadCategory, setCounselUploadCategory] = useState(DEFAULT_CASE_ATTACHMENT_CATEGORY);
  const [reminderOpen, setReminderOpen] = useState(false);
  const [caseLogOpen, setCaseLogOpen] = useState(false);
  const [caseLogKind, setCaseLogKind] = useState<CaseLogKind>("case");
  const [caseLogTarget, setCaseLogTarget] = useState<CaseRow | null>(null);
  const [batchUpdateOpen, setBatchUpdateOpen] = useState(false);
  const [batchFeeOpen, setBatchFeeOpen] = useState(false);
  const [clueConversionOpen, setClueConversionOpen] = useState(false);
  const [editingCounselCase, setEditingCounselCase] = useState<CaseRow | null>(null);
  const [editingNormalCase, setEditingNormalCase] = useState<CaseRow | null>(null);
  const [editingArbitrationCase, setEditingArbitrationCase] = useState<CaseRow | null>(null);
  const [editingCaseLitigants, setEditingCaseLitigants] = useState<CaseRow | null>(null);
  const [caseLitigantCandidates, setCaseLitigantCandidates] = useState<CaseLitigantCandidate[]>([]);
  const [caseLitigantCandidatesLoading, setCaseLitigantCandidatesLoading] = useState(false);
  const [creatingCasePartyRole, setCreatingCasePartyRole] = useState<CaseLitigantPartyField | null>(null);
  const [creatingCasePartySubmitting, setCreatingCasePartySubmitting] = useState(false);
  const [createDefendantEditorOpen, setCreateDefendantEditorOpen] = useState(false);
  const [editingCaseHearingLawyer, setEditingCaseHearingLawyer] = useState<CaseRow | null>(null);
  const [criminalMaintenance, setCriminalMaintenance] = useState<{row:CaseRow;kind:"litigants"|"public-security"|"procuratorates"|"courts"}|null>(null);
  const [feeCase, setFeeCase] = useState<CaseRow | null>(null);
  const [feeSubtypePreset, setFeeSubtypePreset] = useState<"official" | "third-party" | "agency" | "other" | "">("");
  const [editingFeeRow, setEditingFeeRow] = useState<CaseRow | null>(null);
  const [caseFeeCreateStep, setCaseFeeCreateStep] = useState(0);
  const [createdCaseFees, setCreatedCaseFees] = useState<CaseRow[]>([]);
  const [caseFeePaymentDrafts, setCaseFeePaymentDrafts] = useState<Array<{ payment_remark: string; payment_type_id?: number; payment_payee?: string; payment_account?: string }>>([]);
  const [caseFeeSubmitting, setCaseFeeSubmitting] = useState(false);
  const [paymentRequestFee, setPaymentRequestFee] = useState<CaseRow | null>(null);
  const [feeInformTarget, setFeeInformTarget] = useState<CaseRow | null>(null);
  const [feeInformRecord, setFeeInformRecord] = useState<any | null>(null);
  const [feeInformArrivalOpen, setFeeInformArrivalOpen] = useState(false);
  const [feeInformBillOpen, setFeeInformBillOpen] = useState(false);
  const [feeInformLinkOpen, setFeeInformLinkOpen] = useState(false);
  const [feeInformFile, setFeeInformFile] = useState<UploadFile[]>([]);
  const [feeInformSubmitting, setFeeInformSubmitting] = useState(false);
  const [casePaymentTypes, setCasePaymentTypes] = useState<CasePaymentTypeOption[]>([]);
  const [casePaymentTypesLoading, setCasePaymentTypesLoading] = useState(false);
  const [paymentTypeSearch, setPaymentTypeSearch] = useState("");
  const [paymentTypeCreateTarget, setPaymentTypeCreateTarget] = useState<PaymentTypeCreateTarget | null>(null);
  const [paymentTypeCreating, setPaymentTypeCreating] = useState(false);
  const [paymentPackagePreview, setPaymentPackagePreview] = useState<any | null>(null);
  const [paymentPackageLoading, setPaymentPackageLoading] = useState(false);
  const [caseTaskCreateCase, setCaseTaskCreateCase] = useState<CaseRow | null>(null);
  const [caseTaskMaterialFiles, setCaseTaskMaterialFiles] = useState<UploadFile[]>([]);
  const [caseTaskKind, setCaseTaskKind] = useState<CaseTaskKind>("案件任务");
  const [viewingCaseTask, setViewingCaseTask] = useState<TaskRow | null>(null);
  const [caseTaskHistory, setCaseTaskHistory] = useState<CaseTaskHistoryItem[]>([]);
  const [caseTaskDetailMaterials, setCaseTaskDetailMaterials] = useState<CaseTaskAttachment[]>([]);
  const [caseTaskDetailFeedbacks, setCaseTaskDetailFeedbacks] = useState<CaseTaskAttachment[]>([]);
  const [caseTaskFeedbackText, setCaseTaskFeedbackText] = useState("");
  const [caseTaskFeedbackFiles, setCaseTaskFeedbackFiles] = useState<UploadFile[]>([]);
  const [caseTaskDetailLoading, setCaseTaskDetailLoading] = useState(false);
  const [refundCompleting, setRefundCompleting] = useState<CaseRow | null>(null);
  const [caseTasks, setCaseTasks] = useState<TaskRow[]>([]);
  const [caseTaskVipFilter, setCaseTaskVipFilter] = useState<"all" | "vip" | "normal">("all");
  const [counselDetailTaskVipFilter, setCounselDetailTaskVipFilter] = useState<"all" | "vip" | "normal">("all");
  const [counselDetailCustomerTaskVipFilter, setCounselDetailCustomerTaskVipFilter] = useState<"all" | "vip" | "normal">("all");
  const [caseTaskPage, setCaseTaskPage] = useState(CASE_TASK_DEFAULT_PAGE);
  const [caseTaskPageSize, setCaseTaskPageSize] = useState(CASE_TASK_DEFAULT_PAGE_SIZE);
  const [caseTaskTotal, setCaseTaskTotal] = useState(0);
  const [caseTaskPages, setCaseTaskPages] = useState(0);
  const [selectedCaseKeys, setSelectedCaseKeys] = useState<Key[]>([]);
  const selectedCaseKeySet = useMemo(
    () => new Set(selectedCaseKeys.map((key) => String(key))),
    [selectedCaseKeys],
  );
  const [caseQuery, setCaseQuery] = useState<Record<string, any>>({});
  const legacyCaseListDefaults = getLegacyCaseListDefaults(initialView);
  const legacyCaseListOperationLabels = getLegacyCaseListOperationLabels();
  const [caseUploadCategory, setCaseUploadCategory] = useState(DEFAULT_CASE_ATTACHMENT_CATEGORY);
  const [caseUploadOpen, setCaseUploadOpen] = useState(false);
  const [caseFileTypeOptions, setCaseFileTypeOptions] = useState<CaseFileTypeOption[]>([{value:DEFAULT_CASE_ATTACHMENT_CATEGORY,label:DEFAULT_CASE_ATTACHMENT_CATEGORY}]);
  const [caseFileTypeCatalog, setCaseFileTypeCatalog] = useState<CaseFileTypeOption[]>([{value:DEFAULT_CASE_ATTACHMENT_CATEGORY,label:DEFAULT_CASE_ATTACHMENT_CATEGORY}]);
  const [caseRelations, setCaseRelations] = useState<CaseRelationCatalog | null>(null);
  const [feeTypeCatalog, setFeeTypeCatalog] = useState<FeeTypeCatalogItem[]>([]);
  const [courtOptions, setCourtOptions] = useState<{value:string;label:string;code?:string}[]>([]);
  const [courtOfficerOptions, setCourtOfficerOptions] = useState<{value:string;label:string;court_code?:string;role?:string;phone?:string}[]>([]);
  const [warehouseCatalog, setWarehouseCatalog] = useState<WarehouseCatalogOption[]>([]);
  const warehouseLocationOptions = useMemo(() => buildWarehouseLocationOptions(warehouseCatalog), [warehouseCatalog]);
  const caseUploadRef = useRef<HTMLInputElement>(null);
  const counselDetailUploadRef = useRef<HTMLInputElement>(null);
  const counselDetailClueRequestRef = useRef(0);
    const counselDetailCaseIdRef = useRef<number | null>(null);
  const counselDetailAssistedFeeRequestRef = useRef(0);  const caseLitigantSearchTimerRef = useRef<number | undefined>(undefined);
  const caseLitigantSearchRequestRef = useRef(0);
  const [createForm] = Form.useForm();
  const [createDefendantEditorForm] = Form.useForm();
  const [clueConversionForm] = Form.useForm();
  const createCustomer = Form.useWatch("customer", createForm);
  const createContractId = Form.useWatch("contract_record_id", createForm);
  const selectedCreateContract = useMemo(() => contracts.find((row) => row.id === createContractId), [contracts, createContractId]);
  const createContractOptions = useMemo(
    () => buildCaseContractOptions(contracts, contractPrefill, createCustomer),
    [contracts, contractPrefill, createCustomer],
  );
  const resolveCasePersonValue = (source: string) => {
    const normalized = String(source || "").trim();
    if (!normalized) return "";
    const option = caseAssistantOptions.find((item) =>
      item.value === normalized || item.label === normalized || item.label.startsWith(`${normalized}\uFF08`),
    );
    return option?.value || normalized;
  };
  const resolveCasePersonValues = (sources: unknown) => {
    const values = Array.isArray(sources) ? sources : [sources];
    return values.map((value) => resolveCasePersonValue(String(value || ""))).filter(Boolean);
  };
  const casePersonDisplayName = (source: unknown, displayName?: unknown) => {
    const explicitName = String(displayName || "").trim();
    if (explicitName && !["姓名待维护", "【待补充中文姓名】"].includes(explicitName)) return explicitName;
    const normalized = String(source || "").trim();
    if (!normalized) return "—";
    const option = caseAssistantOptions.find((item) => {
      const personName = item.label.replace(/（[^（）]*）$/, "").trim();
      return item.value === normalized || item.label === normalized || personName === normalized;
    });
    // Historical records can preserve a Chinese name without a current employee
    // account. Keep that evidence visible instead of replacing it with a generic
    // placeholder; account resolution remains authoritative for write actions.
    const matchedName = option?.label.replace(/（[^（）]*）$/, "").trim();
    if (matchedName) return matchedName;
    return /[\u3400-\u9fff]/.test(normalized) ? normalized : "姓名待维护";
  };
  const casePersonDisplayNames = (sources: unknown) => {
    const values = Array.isArray(sources) ? sources : [sources];
    const names = values.filter(Boolean).map((value) => casePersonDisplayName(value));
    return names.length ? names.join("、") : "—";
  };
  const caseAssistantDisplayNames = (data: Record<string, unknown> | null | undefined) =>
    casePersonDisplayNames(caseAssistantDisplayValues(data));
  const legacyCaseParticipantDisplayNames = (data: Record<string, any>) => {
    const resolved = data.legacy_participant_display_names;
    if (Array.isArray(resolved) && resolved.length) {
      return resolved.map((value) => String(value || "").trim()).filter(Boolean).join("、") || "—";
    }
    const participants = Array.isArray(data.legacy_participants) ? data.legacy_participants : [];
    const fallback = participants
      .map((participant: any) => participant?.display_name || participant?.staff_name)
      .filter(Boolean);
    return fallback.length ? casePersonDisplayNames(fallback) : "—";
  };
  const firstCourtEnabled = Form.useWatch("first_court_enabled", createForm);
  const secondCourtEnabled = Form.useWatch("second_court_enabled", createForm);
  const retrialCourtEnabled = Form.useWatch("retrial_court_enabled", createForm);
  const firstCourtName = Form.useWatch("first_court_name", createForm);
  const secondCourtName = Form.useWatch("second_court_name", createForm);
  const retrialCourtName = Form.useWatch("retrial_court_name", createForm);
  const officersForCourt = (courtName: string | undefined, role: string) => {
    const courtCode = courtOptions.find(item => item.value === courtName)?.code;
    return courtOfficerOptions
      .filter(item => (!courtCode || item.court_code === courtCode) && (!role || item.role === role))
      .map(item => ({value:item.value,label:item.phone ? `${item.label}（${item.phone}）` : item.label}));
  };
  const [assignForm] = Form.useForm();
  const [hearingForm] = Form.useForm();
  const [archiveForm] = Form.useForm();
  const [reviewForm] = Form.useForm();
  const [taskForm] = Form.useForm();
  const [feeForm] = Form.useForm();
  const [informDateForm] = Form.useForm();
  const [assistedFeeForm] = Form.useForm();
  const [assistedFeeConfirmForm] = Form.useForm();
  const [paymentRequestForm] = Form.useForm();
  const [feeInformForm] = Form.useForm();
  const [feeInformArrivalForm] = Form.useForm();
  const [feeInformBillForm] = Form.useForm();
  const [feeInformLinkForm] = Form.useForm();  const [paymentTypeCreateForm] = Form.useForm();
  const [courtRefundForm] = Form.useForm();
  const [progressForm] = Form.useForm();
  const [phaseForm] = Form.useForm();
  const [executionStatusForm] = Form.useForm();
  const [companyScheduleCourtInfoForm] = Form.useForm();
  const [counselEditForm] = Form.useForm();
  const [normalCaseEditForm] = Form.useForm();
  const [arbitrationBasicForm] = Form.useForm();
  const [criminalMaintenanceForm] = Form.useForm();
  const [caseLitigantsForm] = Form.useForm();
  const [casePartyCreateForm] = Form.useForm();
  const [caseHearingLawyerForm] = Form.useForm();
  const [caseQueryForm] = Form.useForm();
  const [refundCompleteForm] = Form.useForm();
  const [courtRefundFee, setCourtRefundFee] = useState<CaseRow | null>(null);
  const [reminderForm] = Form.useForm();
  const [caseEventForm] = Form.useForm();
  const [caseLogForm] = Form.useForm();
  const [attachmentRenameForm] = Form.useForm();
  const [aiDraftForm] = Form.useForm();
  const [aiDraftPromoteForm] = Form.useForm();
  const [aiDraftPromoteOptions, setAiDraftPromoteOptions] = useState<CaseFileTypeOption[]>([]);
  const [aiDraftPromoteOptionsLoading, setAiDraftPromoteOptionsLoading] = useState(false);
  const [counselDocumentFolderTree, setCounselDocumentFolderTree] = useState<CaseFileTypeOption[]>([]);
  const [caseDocumentFolderForm] = Form.useForm();
  const [caseAttachmentMoveForm] = Form.useForm();
  const [caseFileSealForm] = Form.useForm();
  const [batchUpdateForm] = Form.useForm();
  const [batchFeeForm] = Form.useForm();
  const [mergeCaseForm] = Form.useForm();
  const [notaryInfoForm] = Form.useForm();
  const [settlementAmountForm] = Form.useForm();
  const [caseClueEvidenceForm] = Form.useForm();
  const openCreateDefendantEditor = () => {
    createDefendantEditorForm.setFieldsValue({ defendants: createForm.getFieldValue("defendants") || [] });
    setCreateDefendantEditorOpen(true);
  };
  const { saveCreateDefendants, advanceCreateStep, saveLitigants, finishCreateFlow, assign, createHearing, openArchive, closeCase, archive, reviewArchive, reviewCaseCreation, deleteCompanyCase, reviewUnarchive, openCaseTasks, openCounselDetail, duplicateCase, submitCaseMerge, submitNotaryInfo, openCaseClueWorkspace, saveCaseClueEvidence, submitClueConversion, openSpecialCaseDetail, openSpecialCaseTasks, createCounselReminder, saveCaseEvent, createCounselLog, submitCounselBatchUpdate, saveCounselBasic, ensureCaseCustomerOption, openNormalCaseEdit, saveNormalCaseBasic, openArbitrationBasicEdit, saveArbitrationBasic, saveCriminalMaintenance, saveCaseParty, saveCaseLitigants, saveCaseHearingLawyer, createCaseTask, openPhaseChange, submitCompanyScheduleCourtInfo, saveProgress, savePhaseChange, saveExecutionStatus, downloadCaseExport, openSelectedScheduleHearing } = createCaseWorkflowActions({
    get createDefendantEditorForm() { return createDefendantEditorForm; },
    get createForm() { return createForm; },
    get setCreateDefendantEditorOpen() { return setCreateDefendantEditorOpen; },
    get createStep() { return createStep; },
    get isCounselCreate() { return isCounselCreate; },
    get setCreateSubmitting() { return setCreateSubmitting; },
    get createRouteType() { return createRouteType; },
    get profile() { return profile; },
    get setCreatedCaseId() { return setCreatedCaseId; },
    get setCreateStep() { return setCreateStep; },
    get createdCaseId() { return createdCaseId; },
    get redirectAfterCreate() { return redirectAfterCreate; },
    get assigning() { return assigning; },
    get assignForm() { return assignForm; },
    get setAssigning() { return setAssigning; },
    get load() { return load; },
    get hearingForm() { return hearingForm; },
    get setHearingOpen() { return setHearingOpen; },
    get getCaseCapability() { return getCaseCapability; },
    get archiveForm() { return archiveForm; },
    get setArchiveChecks() { return setArchiveChecks; },
    get setArchiveType() { return setArchiveType; },
    get setArchiving() { return setArchiving; },
    get archiving() { return archiving; },
    get archiveType() { return archiveType; },
    get reviewing() { return reviewing; },
    get reviewForm() { return reviewForm; },
    get setReviewing() { return setReviewing; },
    get setSelectedCaseKeys() { return setSelectedCaseKeys; },
    get initialView() { return initialView; },
    get loadOrdinaryCases() { return loadOrdinaryCases; },
    get caseQuery() { return caseQuery; },
    get originalPage() { return originalPage; },
    get originalPageSize() { return originalPageSize; },
    get loadCaseTasksPage() { return loadCaseTasksPage; },
    get taskForm() { return taskForm; },
    get setCaseTaskMaterialFiles() { return setCaseTaskMaterialFiles; },
    get setTaskCase() { return setTaskCase; },
    get isCaseDetailView() { return isCaseDetailView; },
    get onNavigate() { return onNavigate; },
    get counselDetailClueRequestRef() { return counselDetailClueRequestRef; },
    get setCounselDetailClues() { return setCounselDetailClues; },
    get setCounselDetailClueKeyword() { return setCounselDetailClueKeyword; },
    get setCounselDetailClueSearchInput() { return setCounselDetailClueSearchInput; },
    get setCounselDetailCluePage() { return setCounselDetailCluePage; },
    get setCounselDetailCluePageSize() { return setCounselDetailCluePageSize; },
    get setCounselDetailClueTotal() { return setCounselDetailClueTotal; },
    get setCounselDetailCluePages() { return setCounselDetailCluePages; },
    get setActiveCounselDetailTab() { return setActiveCounselDetailTab; },
    get setViewingCounselCase() { return setViewingCounselCase; },
    get counselDetailCaseIdRef() { return counselDetailCaseIdRef; },
    get setCounselDetailAssistedFees() { return setCounselDetailAssistedFees; },
    get setCounselDetailAssistedFeeTotal() { return setCounselDetailAssistedFeeTotal; },
    get loadCounselDetailAssistedFees() { return loadCounselDetailAssistedFees; },
    get counselDetailAssistedFeePageSize() { return counselDetailAssistedFeePageSize; },
    get setLegacyLsHistoryCaseIds() { return setLegacyLsHistoryCaseIds; },
    get setSelectedCounselAttachmentKeys() { return setSelectedCounselAttachmentKeys; },
    get setSelectedCounselCaseEventKeys() { return setSelectedCounselCaseEventKeys; },
    get setActiveCounselDocCategory() { return setActiveCounselDocCategory; },
    get setExpandedCounselDocGroups() { return setExpandedCounselDocGroups; },
    get contracts() { return contracts; },
    get caseCustomers() { return caseCustomers; },
    get counselDetailTaskVipFilter() { return counselDetailTaskVipFilter; },
    get counselDetailCustomerTaskVipFilter() { return counselDetailCustomerTaskVipFilter; },
    get setCounselDetailHistory() { return setCounselDetailHistory; },
    get applyCounselDetailTaskPageState() { return applyCounselDetailTaskPageState; },
    get applyCounselDetailCustomerTaskPageState() { return applyCounselDetailCustomerTaskPageState; },
    get setCounselDetailAttachments() { return setCounselDetailAttachments; },
    get setCounselDetailCustomerAttachments() { return setCounselDetailCustomerAttachments; },
    get setCounselDetailContractAttachments() { return setCounselDetailContractAttachments; },
    get setCounselDocumentFolderTree() { return setCounselDocumentFolderTree; },
    get setCounselReminders() { return setCounselReminders; },
    get setCounselCaseEvents() { return setCounselCaseEvents; },
    get setCounselCaseEventCapabilities() { return setCounselCaseEventCapabilities; },
    get setCounselCaseEventsError() { return setCounselCaseEventsError; },
    get setCounselLogs() { return setCounselLogs; },
    get setCounselDetailCapabilities() { return setCounselDetailCapabilities; },
    get setCounselDetailFinance() { return setCounselDetailFinance; },
    get applyCounselDetailCluePageState() { return applyCounselDetailCluePageState; },
    get mergingCase() { return mergingCase; },
    get mergeCaseForm() { return mergeCaseForm; },
    get setMergingCase() { return setMergingCase; },
    get notaryInfoCase() { return notaryInfoCase; },
    get notaryInfoForm() { return notaryInfoForm; },
    get setNotaryInfoCase() { return setNotaryInfoCase; },
    get setCaseClueLoading() { return setCaseClueLoading; },
    get setViewingCaseClue() { return setViewingCaseClue; },
    get setSelectedCaseClueEvidenceId() { return setSelectedCaseClueEvidenceId; },
    get editingCaseClueEvidence() { return editingCaseClueEvidence; },
    get viewingCaseClue() { return viewingCaseClue; },
    get caseClueEvidenceForm() { return caseClueEvidenceForm; },
    get setEditingCaseClueEvidence() { return setEditingCaseClueEvidence; },
    get clueConversionForm() { return clueConversionForm; },
    get caseClues() { return caseClues; },
    get setClueConversionOpen() { return setClueConversionOpen; },
    get resolveVisibleCase() { return resolveVisibleCase; },
    get viewingCounselCase() { return viewingCounselCase; },
    get reminderForm() { return reminderForm; },
    get setReminderOpen() { return setReminderOpen; },
    get caseEventSubmitting() { return caseEventSubmitting; },
    get caseEventForm() { return caseEventForm; },
    get editingCaseEvent() { return editingCaseEvent; },
    get setCaseEventSubmitting() { return setCaseEventSubmitting; },
    get setCaseEventOpen() { return setCaseEventOpen; },
    get setEditingCaseEvent() { return setEditingCaseEvent; },
    get loadCounselCaseEvents() { return loadCounselCaseEvents; },
    get caseLogTarget() { return caseLogTarget; },
    get caseLogForm() { return caseLogForm; },
    get caseLogKind() { return caseLogKind; },
    get setCaseLogOpen() { return setCaseLogOpen; },
    get setCaseLogTarget() { return setCaseLogTarget; },
    get batchUpdateForm() { return batchUpdateForm; },
    get selectedCaseKeys() { return selectedCaseKeys; },
    get setBatchUpdateOpen() { return setBatchUpdateOpen; },
    get counselListMode() { return counselListMode; },
    get loadCounselCases() { return loadCounselCases; },
    get counselPage() { return counselPage; },
    get counselPageSize() { return counselPageSize; },
    get editingCounselCase() { return editingCounselCase; },
    get counselEditForm() { return counselEditForm; },
    get setEditingCounselCase() { return setEditingCounselCase; },
    get setCaseCustomers() { return setCaseCustomers; },
    get isNormalEditableCase() { return isNormalEditableCase; },
    get normalCaseEditForm() { return normalCaseEditForm; },
    get resolveCasePersonValues() { return resolveCasePersonValues; },
    get resolveCasePersonValue() { return resolveCasePersonValue; },
    get setEditingNormalCase() { return setEditingNormalCase; },
    get editingNormalCase() { return editingNormalCase; },
    get loadCounselDetailCluesPage() { return loadCounselDetailCluesPage; },
    get counselDetailCluePageSize() { return counselDetailCluePageSize; },
    get arbitrationBasicForm() { return arbitrationBasicForm; },
    get setEditingArbitrationCase() { return setEditingArbitrationCase; },
    get editingArbitrationCase() { return editingArbitrationCase; },
    get criminalMaintenance() { return criminalMaintenance; },
    get criminalMaintenanceForm() { return criminalMaintenanceForm; },
    get setCriminalMaintenance() { return setCriminalMaintenance; },
    get creatingCasePartyRole() { return creatingCasePartyRole; },
    get casePartyCreateForm() { return casePartyCreateForm; },
    get setCreatingCasePartySubmitting() { return setCreatingCasePartySubmitting; },
    get setCaseLitigantCandidates() { return setCaseLitigantCandidates; },
    get caseLitigantsForm() { return caseLitigantsForm; },
    get setCreatingCasePartyRole() { return setCreatingCasePartyRole; },
    get editingCaseLitigants() { return editingCaseLitigants; },
    get setEditingCaseLitigants() { return setEditingCaseLitigants; },
    get editingCaseHearingLawyer() { return editingCaseHearingLawyer; },
    get caseHearingLawyerForm() { return caseHearingLawyerForm; },
    get setEditingCaseHearingLawyer() { return setEditingCaseHearingLawyer; },
    get taskCase() { return taskCase; },
    get caseTaskCreateCase() { return caseTaskCreateCase; },
    get caseTaskKind() { return caseTaskKind; },
    get caseTaskMaterialFiles() { return caseTaskMaterialFiles; },
    get setCaseTaskCreateCase() { return setCaseTaskCreateCase; },
    get setPhaseOptions() { return setPhaseOptions; },
    get phaseForm() { return phaseForm; },
    get setPhaseEditing() { return setPhaseEditing; },
    get companyScheduleCourtInfo() { return companyScheduleCourtInfo; },
    get companyScheduleCourtInfoForm() { return companyScheduleCourtInfoForm; },
    get cancelCompanyScheduleCourtInfo() { return cancelCompanyScheduleCourtInfo; },
    get progressEditing() { return progressEditing; },
    get progressForm() { return progressForm; },
    get setProgressEditing() { return setProgressEditing; },
    get phaseEditing() { return phaseEditing; },
    get phaseOptions() { return phaseOptions; },
    get executionStatusEditing() { return executionStatusEditing; },
    get executionStatusForm() { return executionStatusForm; },
    get setExecutionStatusEditing() { return setExecutionStatusEditing; },
    get selectedSpecialRow() { return selectedSpecialRow; },
    get openHearing() { return openHearing; },
  });
  const batchExpenseScope = Form.useWatch("expense_scope", batchFeeForm);
  const feeExpenseScope = Form.useWatch("expense_scope", feeForm);
  const feeBaseType = Form.useWatch("fee_type", feeForm);
  const selectedPaymentTypeId = Form.useWatch("payment_type_id", paymentRequestForm);
  const feeItems = Form.useWatch("items", feeForm) || [];
  const feeEmployeeOptions = caseAssistantOptions;
  const casePaymentTypeSelectOptions = buildCasePaymentTypeSelectOptions(casePaymentTypes);
  const selectedCasePaymentType = casePaymentTypes.find((item) => item.id === selectedPaymentTypeId);
  const activeFeeContractScope = editingFeeRow ? feeExpenseScope : String(feeItems[0]?.expense_scope || "");
  const feeContractOptions = useMemo(
    () => buildCaseFeeContractOptions(contracts, feeCase || viewingCounselCase, editingFeeRow, activeFeeContractScope),
    [activeFeeContractScope, contracts, editingFeeRow, feeCase, viewingCounselCase],
  );
  const fileTypeOptionsForCase = (caseType: unknown) => buildCaseFileTypeTreeOptions(
    filterCaseFileTypesForCaseType(String(caseType || ""), caseFileTypeCatalog, caseRelations?.caseTypeFileTypes),
  );
  const phaseOptionsForCaseType = (caseType: unknown, phases: CasePhaseOption[]) => {
    const normalizedCaseType = String(caseType || "").trim();
    const names = new Set([normalizedCaseType]);
    if (normalizedCaseType === "民事案件") names.add("民事争议");
    if (normalizedCaseType === "民事争议") names.add("民事案件");
    const configured = filterCasePhasesForCaseType(normalizedCaseType, phases, caseRelations?.caseTypePhases);
    const builtin = phases.filter((phase) => names.has(String(phase.case_type || "").trim()));
    return Array.from(new Map([...configured, ...builtin].map((phase) => [phase.id, phase])).values());
  };
  const normalEditPhaseOptions = useMemo(
    () => phaseOptionsForCaseType(editingNormalCase?.data.case_type, phaseCatalog),
    [caseRelations, editingNormalCase?.data.case_type, phaseCatalog],
  );
  const feeSourceCase = feeCase || viewingCounselCase;
  const feeSourceFileTypeOptions = useMemo(
    () => fileTypeOptionsForCase(feeSourceCase?.data.case_type),
    [caseFileTypeCatalog, caseRelations, feeSourceCase?.data.case_type],
  );
  const feeTypeTreeOptions = useMemo(
    () => feeTypeTreeData(feeTypeCatalog, activeFeeContractScope, feeSubtypePreset),
    [activeFeeContractScope, feeSubtypePreset, feeTypeCatalog],
  );
  const batchFeeTypeTreeOptions = useMemo(
    () => feeTypeTreeData(feeTypeCatalog, String(batchExpenseScope || "")),
    [batchExpenseScope, feeTypeCatalog],
  );
  const getCaseCapability = (row?: CaseRow | null) => {
    if (!row) return noCaseDetailWriteCapability;
    // A migrated case can be opened directly without first appearing in the
    // current list page. In that flow the list capability cache has no entry,
    // so detail actions must use the capability loaded with the detail itself.
    if (viewingCounselCase?.id === row.id) return counselDetailCapabilities;
    return caseActionCapabilities[row.id] || noCaseDetailWriteCapability;
  };
  const { loadCaseCapabilities, loadCaseRelations, load, loadOrdinaryCases, loadPendingExecutionCases, loadCounselCases, loadCaseTasksPage, loadCounselDetailTasksPage, loadCounselDetailCustomerTasksPage, loadCounselDetailCluesPage, openRelatedCustomer, loadCaseTaskDetail, openRelatedClue, resolveVisibleCase, loadCounselCaseEvents, loadCaseLitigantCandidates, exportCases, exportCounselCases, exportSpecialRecords } = createCaseQueriesActions({
    get setCaseActionCapabilities() { return setCaseActionCapabilities; },
    get setCaseRelations() { return setCaseRelations; },
    get setLoading() { return setLoading; },
    get setOrdinaryLoading() { return setOrdinaryLoading; },
    get setOrdinaryLoadError() { return setOrdinaryLoadError; },
    get initialView() { return initialView; },
    get setCases() { return setCases; },
    get isCreateView() { return isCreateView; },
    get openCounselDetail() { return openCounselDetail; },
    get isCaseDetailView() { return isCaseDetailView; },
    get detailRouteId() { return detailRouteId; },
    get setWarehouseCatalog() { return setWarehouseCatalog; },
    get setContracts() { return setContracts; },
    get setHearings() { return setHearings; },
    get setSummary() { return setSummary; },
    get setProfile() { return setProfile; },
    get setFinanceRows() { return setFinanceRows; },
    get setAttachments() { return setAttachments; },
    get setCaseTypeOptions() { return setCaseTypeOptions; },
    get setCauseOptions() { return setCauseOptions; },
    get setCaseFileTypeCatalog() { return setCaseFileTypeCatalog; },
    get setCaseFileTypeOptions() { return setCaseFileTypeOptions; },
    get setCaseUploadCategory() { return setCaseUploadCategory; },
    get setCounselUploadCategory() { return setCounselUploadCategory; },
    get setCourtOptions() { return setCourtOptions; },
    get setCourtOfficerOptions() { return setCourtOfficerOptions; },
    get setCaseLawyerOptions() { return setCaseLawyerOptions; },
    get setCaseAssistantOptions() { return setCaseAssistantOptions; },
    get setRightTypeOptions() { return setRightTypeOptions; },
    get setCaseCustomers() { return setCaseCustomers; },
    get setCaseClues() { return setCaseClues; },
    get setFeeTypeCatalog() { return setFeeTypeCatalog; },
    get contractPrefill() { return contractPrefill; },
    get createForm() { return createForm; },
    get resolveCasePersonValue() { return resolveCasePersonValue; },
    get caseQuery() { return caseQuery; },
    get originalPageSize() { return originalPageSize; },
    get ordinaryRequestGuard() { return ordinaryRequestGuard; },
    get ordinaryCaseQueue() { return ordinaryCaseQueue; },
    get ordinaryScope() { return ordinaryScope; },
    get ordinaryCaseTypes() { return ordinaryCaseTypes; },
    get setOrdinaryCases() { return setOrdinaryCases; },
    get setOrdinaryTotal() { return setOrdinaryTotal; },
    get setOrdinaryPhaseCounts() { return setOrdinaryPhaseCounts; },
    get setOriginalPage() { return setOriginalPage; },
    get setOriginalPageSize() { return setOriginalPageSize; },
    get setSelectedCaseKeys() { return setSelectedCaseKeys; },
    get pendingExecutionPageSize() { return pendingExecutionPageSize; },
    get setPendingExecutionCases() { return setPendingExecutionCases; },
    get setPendingExecutionTotal() { return setPendingExecutionTotal; },
    get setPendingExecutionPage() { return setPendingExecutionPage; },
    get setPendingExecutionPageSize() { return setPendingExecutionPageSize; },
    get counselPageSize() { return counselPageSize; },
    get counselSearchPayload() { return counselSearchPayload; },
    get setCounselCases() { return setCounselCases; },
    get setCounselTotal() { return setCounselTotal; },
    get setCounselPage() { return setCounselPage; },
    get setCounselPageSize() { return setCounselPageSize; },
    get caseTaskPage() { return caseTaskPage; },
    get caseTaskPageSize() { return caseTaskPageSize; },
    get caseTaskVipFilter() { return caseTaskVipFilter; },
    get applyCaseTaskPageState() { return applyCaseTaskPageState; },
    get counselDetailTaskPage() { return counselDetailTaskPage; },
    get counselDetailTaskPageSize() { return counselDetailTaskPageSize; },
    get counselDetailTaskVipFilter() { return counselDetailTaskVipFilter; },
    get applyCounselDetailTaskPageState() { return applyCounselDetailTaskPageState; },
    get counselDetailCustomerTaskPage() { return counselDetailCustomerTaskPage; },
    get counselDetailCustomerTaskPageSize() { return counselDetailCustomerTaskPageSize; },
    get counselDetailCustomerTaskVipFilter() { return counselDetailCustomerTaskVipFilter; },
    get applyCounselDetailCustomerTaskPageState() { return applyCounselDetailCustomerTaskPageState; },
    get counselDetailCluePage() { return counselDetailCluePage; },
    get counselDetailCluePageSize() { return counselDetailCluePageSize; },
    get counselDetailClueKeyword() { return counselDetailClueKeyword; },
    get counselDetailClueRequestRef() { return counselDetailClueRequestRef; },
    get setCounselDetailClueLoading() { return setCounselDetailClueLoading; },
    get viewingCounselCase() { return viewingCounselCase; },
    get applyCounselDetailCluePageState() { return applyCounselDetailCluePageState; },
    get onNavigate() { return onNavigate; },
    get setCaseTaskDetailLoading() { return setCaseTaskDetailLoading; },
    get setViewingCaseTask() { return setViewingCaseTask; },
    get setCaseTaskHistory() { return setCaseTaskHistory; },
    get setCaseTaskDetailMaterials() { return setCaseTaskDetailMaterials; },
    get setCaseTaskDetailFeedbacks() { return setCaseTaskDetailFeedbacks; },
    get setCaseClueLoading() { return setCaseClueLoading; },
    get cases() { return cases; },
    get setCounselCaseEvents() { return setCounselCaseEvents; },
    get setCounselCaseEventCapabilities() { return setCounselCaseEventCapabilities; },
    get setSelectedCounselCaseEventKeys() { return setSelectedCounselCaseEventKeys; },
    get setCounselCaseEventsError() { return setCounselCaseEventsError; },
    get caseLitigantSearchRequestRef() { return caseLitigantSearchRequestRef; },
    get setCaseLitigantCandidatesLoading() { return setCaseLitigantCandidatesLoading; },
    get setCaseLitigantCandidates() { return setCaseLitigantCandidates; },
    get originalCases() { return originalCases; },
    get selectedCaseKeys() { return selectedCaseKeys; },
  });

  const counselScope = initialView.startsWith("case-mine") ? "mine" : initialView.startsWith("case-dept") ? "department" : "company";
  const counselSearchPayload = (values:Record<string,any>, page:number, pageSize:number, extra:Record<string,any>={}) =>
    buildCaseCounselSearchPayload(values, counselScope, page, pageSize, extra);
  const ordinaryScope = initialView.startsWith("case-mine") ? "mine" : initialView.startsWith("case-dept") ? "department" : "company";
  const ordinaryCaseQueue = ordinaryCaseQueueForView(initialView);
  const ordinaryCaseTypes = ordinaryCaseTypesForView(initialView);

  const searchByPhase = (status: string) => {
    const nextQuery = { ...caseQuery, status, case_statuses: legacyCasePhaseFilterValues(status), sort_order: "updated_desc" };
    caseQueryForm.setFieldValue("status", status);
    setCaseQuery(nextQuery);
    setOriginalPage(1);
    if (initialView.includes("counsel")) {
      return loadCounselCases(nextQuery, 1, counselPageSize);
    }
    return loadOrdinaryCases(nextQuery, 1, originalPageSize);
  };
  const startCreate = () => {
    const operator = profile.display_name || profile.username || "管理者";
    setCreateStep(0);
    setCreatedCaseId(null);
    setSelectedCreateType(createRouteType);
    createForm.resetFields();
    createForm.setFieldsValue({
      status: "新案待分配",
      owner: profile.username || "admin",
      // A newly created case starts with the current creator as its sole handler.
      handling_lawyers: [profile.display_name || profile.username || "admin"],
      investigator: "",
      investigation_clue: "",
      assistant: undefined,
      case_type: createRouteType,
      client_position: isCounselCreate ? "" : isCriminalCreate ? "被告人/犯罪嫌疑人" : "原告/申请人",
      contract_record_id: contractPrefill?.id,
      customer: contractPrefill?.customer,
      source_person: "",
      title: contractPrefill ? `${contractPrefill.title}案件` : undefined,
      first_court_enabled: true,
      second_court_enabled: false,
      retrial_court_enabled: false,
      counsel_range: isCounselCreate ? [dayjs(), dayjs().add(1, "year")] : undefined,
    });
  };
  useEffect(() => {
    setTab(first);
    if (isCreateView) startCreate();
    let activeListReturnContext = pendingListReturnContext.current;
    if (!isCreateView && !isCaseDetailView) {
      const storedListReturnContext = readStoredGlobalCaseSearchContext(sessionStorage) as typeof activeListReturnContext;
      if (storedListReturnContext) pendingListReturnContext.current = storedListReturnContext;
      activeListReturnContext = storedListReturnContext || pendingListReturnContext.current;
      sessionStorage.removeItem("sunhold:case-list-return");
    }
    const dashboardQuery = dashboardCaseQueryForView(initialView);
    const hasDashboardQuery = Object.keys(dashboardQuery).length > 0;
    const relationTarget = consumeCustomerRelationTarget("civil-cases");
    const routeCustomerId = ordinaryCustomerIdForView(initialView);
    const relationQuery = routeCustomerId || relationTarget?.target === "civil-cases" ? {
      customer_id: routeCustomerId || relationTarget?.id,
      customer_no: relationTarget?.serial_no,
      customer: relationTarget?.title,
    } : {};
    let initialListQuery: Record<string, any> = hasDashboardQuery ? dashboardQuery : relationQuery;
    if (hasDashboardQuery) {
      caseQueryForm.setFieldsValue(dashboardQuery);
      setCaseQuery(dashboardQuery);
    } else if (relationQuery.customer_id || relationQuery.customer_no || relationQuery.customer) {
      caseQueryForm.setFieldsValue(relationQuery);
      setCaseQuery(relationQuery);
    }
    if (!hasDashboardQuery && !relationQuery.customer_id && !relationQuery.customer_no && !relationQuery.customer && !isCreateView && !isCaseDetailView && activeListReturnContext?.query) {
      caseQueryForm.setFieldsValue(activeListReturnContext.query);
      setCaseQuery(activeListReturnContext.query);
      initialListQuery = activeListReturnContext.query;
      sessionStorage.removeItem("sunhold:case-list-return");
    }
    void (async () => {
      const phaseLoad = api.get("/cases/phases")
        .then(({ data }) => setPhaseCatalog((Array.isArray(data?.items) ? data.items : []) as CasePhaseOption[]))
        .catch(() => setPhaseCatalog([]));
      const listLoad = isCreateView || isCaseDetailView
        ? Promise.resolve()
        : initialView === "case-company-execution"
          ? loadPendingExecutionCases(1, pendingExecutionPageSize)
        : initialView.includes("counsel")
          ? loadCounselCases(initialListQuery, 1, 10)
          : initialView.startsWith("case-mine") || initialView.startsWith("case-dept") || initialView.startsWith("case-company")
            ? loadOrdinaryCases(initialListQuery, 1, originalPageSize)
            : Promise.resolve();
      await Promise.all([phaseLoad, load(), listLoad]);
    })();
  }, [initialView]);
  const returnToCaseList = () => {
    let route = caseListReturnContext?.route || "case-mine";
    let page = originalPage;
    let pageSize = originalPageSize;
    try {
      const raw = sessionStorage.getItem("sunhold:case-list-return");
      if (raw) {
        const saved = JSON.parse(raw);
        route = saved?.route || route;
        page = Number(saved?.page) || page;
        pageSize = Number(saved?.pageSize) || pageSize;
      }
    } catch {
      // fall back to the standard list route
    }
    setOriginalPage(page);
    setOriginalPageSize(pageSize);
    onNavigate?.(route);
  };
  
  const redirectAfterCreate = () => {
    const params = new URLSearchParams(window.location.search);
    params.set("page", createRedirectPage);
    window.location.search = params.toString();
  };

  const deleteHearing = (row: Hearing) => {
    const permissionError = getCaseHearingDeleteValidationError(profile.role);
    if (permissionError) return message.warning(permissionError);
    Modal.confirm({
      title: `确认删除开庭排期：${row.case_no || row.id}`,
      content: "删除后不可恢复，并会刷新案件排期列表。",
      okText: "删除",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onOk: async () => {
        try {
          await api.delete(`/hearings/${row.id}`);
          message.success("排期已删除");
          await load();
        } catch (error: any) {
          message.error(error?.response?.data?.detail || "排期删除失败");
        }
      },
    });
  };

  const openArchiveReview = (row: CaseRow) => {
    reviewForm.resetFields();
    reviewForm.setFieldsValue({
      archive_no: row.data.archive_no || "",
      comment: row.data.archive_review_comment || "",
    });
    setReviewing({ row, approved: true });
  };

  const requestUnarchive = (row: CaseRow) => {
    let reason = "";
    Modal.confirm({
      title: `申请解档：${row.serial_no}`,
      content: <Input.TextArea rows={4} placeholder="请填写必须解档修改的具体原因" onChange={(event) => { reason = event.target.value; }} />,
      okText: "提交审批",
      cancelText: "取消",
      onOk: async () => {
        const validationError = getCaseUnarchiveRequestValidationError(reason);
        if (validationError) {
          message.warning(validationError);
          return Promise.reject(new Error(validationError));
        }
        try {
          await api.post(`/cases/${row.id}/unarchive/request`, { reason });
          message.success("解档申请已提交特殊审批");
          await load();
        } catch (error: any) {
          message.error(error?.response?.data?.detail || "解档申请失败");
          throw error;
        }
      },
    });
  };
  
  const openUnarchiveReview = (row: CaseRow, approved: boolean) => {
    if (approved) {
      void reviewUnarchive(row, true);
      return;
    }
    let comment = "";
    Modal.confirm({
      title: `驳回解档申请：${row.serial_no}`,
      content: <Input.TextArea rows={4} placeholder="请填写驳回解档的具体原因（至少2个字）" onChange={(event) => { comment = event.target.value; }} />,
      okText: "确认驳回",
      cancelText: "取消",
      onOk: async () => {
        const reviewPayload = buildCaseUnarchiveReviewPayload({ approved: false, comment });
        const validationError = getCaseUnarchiveReviewValidationError({
          role: profile.role,
          status: row.status,
          requestStatus: row.data.unarchive_request?.status,
          requestedBy: row.data.unarchive_request?.requested_by,
          currentUsername: profile.username,
          approved: false,
          comment: reviewPayload.comment,
        });
        if (validationError) {
          message.warning(validationError);
          return Promise.reject(new Error(validationError));
        }
        await reviewUnarchive(row, false, reviewPayload.comment);
      },
    });
  };
  const openAssign = (row: CaseRow) => {
    if (!getCaseCapability(row).can_assign_team) return message.warning("当前账号没有案件人员分配权限");
    setAssigning(row);
    assignForm.setFieldsValue({
      customer_manager: row.data.customer_manager || "",
      hearing_lawyer: row.data.hearing_lawyer || "",
      handling_lawyers: resolveCasePersonValues(row.data.handling_lawyers || []),
      assistants: resolveCasePersonValues(row.data.assistant_usernames || row.data.assistants || (row.data.assistant ? [row.data.assistant] : [])),
    });
  };
  const applyCaseTaskPageState = (payload: any, fallbackPage: number, fallbackPageSize: number) => {
    const normalized = normalizeCaseTaskPageState(payload, fallbackPage, fallbackPageSize);
    setCaseTasks(normalized.items);
    setCaseTaskPage(normalized.page);
    setCaseTaskPageSize(normalized.pageSize);
    setCaseTaskTotal(normalized.total);
    setCaseTaskPages(normalized.pages);
    return normalized;
  };
  const applyCounselDetailTaskPageState = (payload: any, fallbackPage: number, fallbackPageSize: number) => {
    const normalized = normalizeCaseTaskPageState(payload, fallbackPage, fallbackPageSize);
    setCounselDetailTasks(normalized.items);
    setCounselDetailTaskPage(normalized.page);
    setCounselDetailTaskPageSize(normalized.pageSize);
    setCounselDetailTaskTotal(normalized.total);
    setCounselDetailTaskPages(normalized.pages);
    return normalized;
  };
  const applyCounselDetailCustomerTaskPageState = (payload: any, fallbackPage: number, fallbackPageSize: number) => {
    const normalized = normalizeCaseTaskPageState(payload, fallbackPage, fallbackPageSize);
    setCounselDetailCustomerTasks(normalized.items);
    setCounselDetailCustomerTaskPage(normalized.page);
    setCounselDetailCustomerTaskPageSize(normalized.pageSize);
    setCounselDetailCustomerTaskTotal(normalized.total);
    setCounselDetailCustomerTaskPages(normalized.pages);
    return normalized;
  };

  const applyCounselDetailCluePageState = (payload: any, fallbackPage: number, fallbackPageSize: number) => {
    const items = Array.isArray(payload?.clues) ? payload.clues : [];
    const total = Number(payload?.clue_total ?? items.length) || 0;
    const page = Math.max(1, Number(payload?.clue_page ?? fallbackPage) || fallbackPage);
    const pageSize = Math.max(1, Number(payload?.clue_page_size ?? fallbackPageSize) || fallbackPageSize);
    const pages = Math.max(0, Number(payload?.clue_pages ?? Math.ceil(total / pageSize)) || 0);
    setCounselDetailClues(items);
    setCounselDetailClueTotal(total);
    setCounselDetailCluePage(page);
    setCounselDetailCluePageSize(pageSize);
    setCounselDetailCluePages(pages);
    return { items, total, page, pageSize, pages };
  };

  const applyCounselDocumentFolderPayload = (payload: any): CaseFileTypeOption[] => {
    const tree = Array.isArray(payload?.tree) ? payload.tree : [];
    setCounselDocumentFolderTree(tree);
    return tree;
  };
  const { refreshCounselDocumentFolderTree, refreshCounselDetailAttachments, uploadCaseAgentScreenshot, downloadCaseTaskAttachment, generateCaseDocument, openCounselAttachmentSeal, submitCounselAttachmentSeal, uploadCounselDetailAttachment, downloadCounselDetailAttachment, unlockCounselDetailAttachment, previewCounselDetailAttachment, loadAttachmentPdfPage, moveCounselAttachments, renameCounselAttachment, openEditAiDraft, releaseCaseWordEditorLock, finishClosingCaseWordEditor, openCaseWordEditor, saveCaseWordEditor, saveAiDraft, openPromoteAiDraft, promoteAiDraft, saveCaseDocumentFolder, generateSelectedCaseDocuments, uploadCaseFile, uploadCaseInvoiceFile } = createCaseDocumentsActions({
    get applyCounselDocumentFolderPayload() { return applyCounselDocumentFolderPayload; },
    get setCounselDetailAttachments() { return setCounselDetailAttachments; },
    get agentCase() { return agentCase; },
    get agentScreenshots() { return agentScreenshots; },
    get setAgentScreenshotUploading() { return setAgentScreenshotUploading; },
    get agentScreenshotPreviewUrlsRef() { return agentScreenshotPreviewUrlsRef; },
    get setAgentScreenshots() { return setAgentScreenshots; },
    get agentScreenshotInputRef() { return agentScreenshotInputRef; },
    get viewingCounselCase() { return viewingCounselCase; },
    get generatingCaseDocumentType() { return generatingCaseDocumentType; },
    get setCaseDocumentGenerationError() { return setCaseDocumentGenerationError; },
    get setGeneratingCaseDocumentType() { return setGeneratingCaseDocumentType; },
    get setExpandedCounselDocGroups() { return setExpandedCounselDocGroups; },
    get setActiveCounselDocCategory() { return setActiveCounselDocCategory; },
    get setCaseSealAssets() { return setCaseSealAssets; },
    get caseFileSealForm() { return caseFileSealForm; },
    get setSealingCounselAttachment() { return setSealingCounselAttachment; },
    get sealingCounselAttachment() { return sealingCounselAttachment; },
    get openCounselDetail() { return openCounselDetail; },
    get caseCustomers() { return caseCustomers; },
    get contracts() { return contracts; },
    get activeCounselDocCategory() { return activeCounselDocCategory; },
    get counselUploadCategory() { return counselUploadCategory; },
    get counselDetailUploadRef() { return counselDetailUploadRef; },
    get attachmentPreview() { return attachmentPreview; },
    get setAttachmentPreviewLoading() { return setAttachmentPreviewLoading; },
    get setAttachmentPreview() { return setAttachmentPreview; },
    get movingCounselAttachmentIds() { return movingCounselAttachmentIds; },
    get caseAttachmentMoveForm() { return caseAttachmentMoveForm; },
    get setMovingCounselAttachmentIds() { return setMovingCounselAttachmentIds; },
    get setSelectedCounselAttachmentKeys() { return setSelectedCounselAttachmentKeys; },
    get renamingCounselAttachment() { return renamingCounselAttachment; },
    get attachmentRenameForm() { return attachmentRenameForm; },
    get setRenamingCounselAttachment() { return setRenamingCounselAttachment; },
    get aiDraftForm() { return aiDraftForm; },
    get setAiDraftEditor() { return setAiDraftEditor; },
    get wordEditorLockTokenRef() { return wordEditorLockTokenRef; },
    get setWordEditor() { return setWordEditor; },
    get setWordEditorLockLost() { return setWordEditorLockLost; },
    get wordEditorOpening() { return wordEditorOpening; },
    get wordEditor() { return wordEditor; },
    get setWordEditorOpening() { return setWordEditorOpening; },
    get wordEditorChanged() { return wordEditorChanged; },
    get wordEditorSavingRef() { return wordEditorSavingRef; },
    get setWordEditorSaving() { return setWordEditorSaving; },
    get aiDraftEditor() { return aiDraftEditor; },
    get selectCounselDocCategory() { return selectCounselDocCategory; },
    get setPromotingAiDraft() { return setPromotingAiDraft; },
    get setAiDraftPromoteOptionsLoading() { return setAiDraftPromoteOptionsLoading; },
    get setAiDraftPromoteOptions() { return setAiDraftPromoteOptions; },
    get aiDraftPromoteForm() { return aiDraftPromoteForm; },
    get counselUploadCategoryOptions() { return counselUploadCategoryOptions; },
    get promotingAiDraft() { return promotingAiDraft; },
    get caseDocumentFolderEditor() { return caseDocumentFolderEditor; },
    get caseDocumentFolderForm() { return caseDocumentFolderForm; },
    get setViewingCounselCase() { return setViewingCounselCase; },
    get setCounselUploadCategory() { return setCounselUploadCategory; },
    get setCaseDocumentFolderEditor() { return setCaseDocumentFolderEditor; },
    get selectedCases() { return selectedCases; },
    get selectedCase() { return selectedCase; },
    get initialView() { return initialView; },
    get caseUploadCategory() { return caseUploadCategory; },
    get fileTypeOptionsForCase() { return fileTypeOptionsForCase; },
    get caseUploadRef() { return caseUploadRef; },
    get load() { return load; },
  });
  
  const { loadCounselDetailAssistedFees, saveCounselDetailAssistedFee, confirmCounselDetailAssistedFee, submitSettlementAmount, submitCaseTaskFeedback, openRelatedFee, submitCounselBatchFee, openCaseFee, loadCasePaymentTypes, createCasePaymentType, createCaseFee, submitCreatedCaseFeePayments, createCourtRefund, openPaymentRequest, submitPaymentRequest, previewInternalPayment, submitCaseFeePayment, submitInternalPayment, startCaseInvoiceImport, completeRefund, submitInformDateBatchUpdate, refreshCaseFeeDetail, createFeeInform, loadLatestFeeInform, openFeeInformArrival, confirmFeeInformArrival, openFeeInformBill, uploadFeeInformBill, downloadFeeInformBill, unlockFeeInform, openFeeInformLinks, saveFeeInformLinks, deleteFeeInform, handleExternalFeeOperation, openCaseCommission, submitCaseCommissions } = createCaseFinanceActions({
    get counselDetailAssistedFeePage() { return counselDetailAssistedFeePage; },
    get counselDetailAssistedFeePageSize() { return counselDetailAssistedFeePageSize; },
    get counselDetailAssistedFeeRequestRef() { return counselDetailAssistedFeeRequestRef; },
    get counselDetailCaseIdRef() { return counselDetailCaseIdRef; },
    get setCounselDetailAssistedFees() { return setCounselDetailAssistedFees; },
    get setCounselDetailAssistedFeePage() { return setCounselDetailAssistedFeePage; },
    get setCounselDetailAssistedFeePageSize() { return setCounselDetailAssistedFeePageSize; },
    get setCounselDetailAssistedFeeTotal() { return setCounselDetailAssistedFeeTotal; },
    get viewingCounselCase() { return viewingCounselCase; },
    get setAssistedFeeSaving() { return setAssistedFeeSaving; },
    get assistedFeeForm() { return assistedFeeForm; },
    get assistedFeeEditor() { return assistedFeeEditor; },
    get setCounselDetailHistory() { return setCounselDetailHistory; },
    get setAssistedFeeModalOpen() { return setAssistedFeeModalOpen; },
    get setAssistedFeeEditor() { return setAssistedFeeEditor; },
    get assistedFeeConfirming() { return assistedFeeConfirming; },
    get assistedFeeConfirmForm() { return assistedFeeConfirmForm; },
    get setAssistedFeeConfirming() { return setAssistedFeeConfirming; },
    get settlementAmountCase() { return settlementAmountCase; },
    get settlementAmountForm() { return settlementAmountForm; },
    get setSettlementAmountCase() { return setSettlementAmountCase; },
    get openCounselDetail() { return openCounselDetail; },
    get load() { return load; },
    get viewingCaseTask() { return viewingCaseTask; },
    get caseTaskFeedbackText() { return caseTaskFeedbackText; },
    get setCaseTaskDetailLoading() { return setCaseTaskDetailLoading; },
    get caseTaskFeedbackFiles() { return caseTaskFeedbackFiles; },
    get setCaseTaskFeedbackText() { return setCaseTaskFeedbackText; },
    get setCaseTaskFeedbackFiles() { return setCaseTaskFeedbackFiles; },
    get loadCaseTaskDetail() { return loadCaseTaskDetail; },
    get onNavigate() { return onNavigate; },
    get batchFeeForm() { return batchFeeForm; },
    get selectedCaseKeys() { return selectedCaseKeys; },
    get profile() { return profile; },
    get setBatchFeeOpen() { return setBatchFeeOpen; },
    get getCaseCapability() { return getCaseCapability; },
    get contracts() { return contracts; },
    get setContracts() { return setContracts; },
    get fileTypeOptionsForCase() { return fileTypeOptionsForCase; },
    get setFeeSubtypePreset() { return setFeeSubtypePreset; },
    get feeTypeCatalog() { return feeTypeCatalog; },
    get feeForm() { return feeForm; },
    get setCaseFeeCreateStep() { return setCaseFeeCreateStep; },
    get setCreatedCaseFees() { return setCreatedCaseFees; },
    get setCaseFeePaymentDrafts() { return setCaseFeePaymentDrafts; },
    get setFeeCase() { return setFeeCase; },
    get setCasePaymentTypesLoading() { return setCasePaymentTypesLoading; },
    get setCasePaymentTypes() { return setCasePaymentTypes; },
    get paymentTypeCreateTarget() { return paymentTypeCreateTarget; },
    get paymentTypeCreateForm() { return paymentTypeCreateForm; },
    get setPaymentTypeCreating() { return setPaymentTypeCreating; },
    get paymentRequestForm() { return paymentRequestForm; },
    get setPaymentTypeCreateTarget() { return setPaymentTypeCreateTarget; },
    get setPaymentTypeSearch() { return setPaymentTypeSearch; },
    get feeCase() { return feeCase; },
    get editingFeeRow() { return editingFeeRow; },
    get isInternalCaseFee() { return isInternalCaseFee; },
    get setEditingFeeRow() { return setEditingFeeRow; },
    get caseFeePaymentDrafts() { return caseFeePaymentDrafts; },
    get createdCaseFees() { return createdCaseFees; },
    get setCaseFeeSubmitting() { return setCaseFeeSubmitting; },
    get closeCaseFeeCreator() { return closeCaseFeeCreator; },
    get courtRefundFee() { return courtRefundFee; },
    get courtRefundForm() { return courtRefundForm; },
    get setCourtRefundFee() { return setCourtRefundFee; },
    get counselDetailCapabilities() { return counselDetailCapabilities; },
    get setPaymentRequestFee() { return setPaymentRequestFee; },
    get paymentRequestFee() { return paymentRequestFee; },
    get setPaymentPackageLoading() { return setPaymentPackageLoading; },
    get setPaymentPackagePreview() { return setPaymentPackagePreview; },
    get paymentPackagePreview() { return paymentPackagePreview; },
    get paymentPackageLoading() { return paymentPackageLoading; },
    get invoiceRows() { return invoiceRows; },
    get refundCompleting() { return refundCompleting; },
    get refundCompleteForm() { return refundCompleteForm; },
    get setRefundCompleting() { return setRefundCompleting; },
    get informDateForm() { return informDateForm; },
    get informDateFeeKeys() { return informDateFeeKeys; },
    get setInformDateFeeKeys() { return setInformDateFeeKeys; },
    get feeInformTarget() { return feeInformTarget; },
    get feeInformForm() { return feeInformForm; },
    get setFeeInformSubmitting() { return setFeeInformSubmitting; },
    get setFeeInformRecord() { return setFeeInformRecord; },
    get setFeeInformTarget() { return setFeeInformTarget; },
    get feeInformArrivalForm() { return feeInformArrivalForm; },
    get setFeeInformArrivalOpen() { return setFeeInformArrivalOpen; },
    get feeInformRecord() { return feeInformRecord; },
    get feeInformBillForm() { return feeInformBillForm; },
    get setFeeInformFile() { return setFeeInformFile; },
    get setFeeInformBillOpen() { return setFeeInformBillOpen; },
    get feeInformFile() { return feeInformFile; },
    get feeInformLinkForm() { return feeInformLinkForm; },
    get setFeeInformLinkOpen() { return setFeeInformLinkOpen; },
    get openInformDateBatchUpdate() { return openInformDateBatchUpdate; },
    get requireSingleFee() { return requireSingleFee; },
    get openFeeInformCreator() { return openFeeInformCreator; },
    get editCaseFee() { return editCaseFee; },
    get deleteCaseFee() { return deleteCaseFee; },
    get markCaseFeeNoPayment() { return markCaseFeeNoPayment; },
    get markCaseFeeRefundNotRequired() { return markCaseFeeRefundNotRequired; },
    get selectedFirmFeeKeys() { return selectedFirmFeeKeys; },
    get selectedFirmFee() { return selectedFirmFee; },
    get setCaseCommissionLoading() { return setCaseCommissionLoading; },
    get setCaseCommissionPreview() { return setCaseCommissionPreview; },
    get setCaseCommissionResult() { return setCaseCommissionResult; },
    get setCaseCommissionRows() { return setCaseCommissionRows; },
    get caseCommissionPreview() { return caseCommissionPreview; },
    get caseCommissionRows() { return caseCommissionRows; },
    get setCaseCommissionSubmitting() { return setCaseCommissionSubmitting; },
  });

  const deleteCounselDetailAssistedFee = (row: CaseAssistedFee) => {
    if (!viewingCounselCase) return;
    Modal.confirm({
      title: `删除资助费用：${row.assisted_type}`,
      content: "删除后不可恢复，是否继续？",
      okText: "确认删除",
      cancelText: "取消",
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await api.delete(`/cases/${viewingCounselCase.id}/assisted-fees/${row.id}`);
          const historyResponse = await api.get(`/records/${viewingCounselCase.id}/history`);
          setCounselDetailHistory(historyResponse.data.items || []);
          message.success("资助费用已删除");
          const nextPage = counselDetailAssistedFees.length === 1 && counselDetailAssistedFeePage > 1
            ? counselDetailAssistedFeePage - 1
            : counselDetailAssistedFeePage;
          await loadCounselDetailAssistedFees(viewingCounselCase.id, nextPage, counselDetailAssistedFeePageSize);
        } catch (error: any) {
          message.error(error?.response?.data?.detail || "删除资助费用失败");
        }
      },
    });
  };
  
  const { loadCaseAgent, sendCaseAgentMessage, decideCaseAgentAction } = createCaseAssistantActions({
    get setAgentLoading() { return setAgentLoading; },
    get setAgentStatus() { return setAgentStatus; },
    get setAgentState() { return setAgentState; },
    get setAgentDocuments() { return setAgentDocuments; },
    get setAgentDocumentIds() { return setAgentDocumentIds; },
    get setAgentSkillId() { return setAgentSkillId; },
    get agentCase() { return agentCase; },
    get agentInput() { return agentInput; },
    get agentSkillId() { return agentSkillId; },
    get agentScreenshots() { return agentScreenshots; },
    get agentState() { return agentState; },
    get agentSending() { return agentSending; },
    get activeCaseAgentRequestRef() { return activeCaseAgentRequestRef; },
    get agentDocumentIds() { return agentDocumentIds; },
    get agentDocuments() { return agentDocuments; },
    get setAgentInput() { return setAgentInput; },
    get setAgentScreenshots() { return setAgentScreenshots; },
    get setAgentMaterialPickerOpen() { return setAgentMaterialPickerOpen; },
    get setAgentSending() { return setAgentSending; },
    get stateWithAgentScreenshotPreviews() { return stateWithAgentScreenshotPreviews; },
    get viewingCounselCase() { return viewingCounselCase; },
    get refreshCounselDetailAttachments() { return refreshCounselDetailAttachments; },
    get selectCounselDocCategory() { return selectCounselDocCategory; },
    get agentDecisionLoading() { return agentDecisionLoading; },
    get setAgentDecisionLoading() { return setAgentDecisionLoading; },
  });
  const openCaseAgent = (row: CaseRow) => {
    clearAgentScreenshotPreviews();
    setAgentCase(row);
    setAgentOpen(true);
    setAgentInput("");
    setAgentScreenshots([]);
    setAgentDocuments([]);
    setAgentDocumentIds([]);
    setAgentMaterialPickerOpen(false);
    setAgentHistoryExpanded(false);
    void loadCaseAgent(row, true);
  };
  
  const updateAgentDocumentSelection = (checkedKeys: Key[] | { checked: Key[]; halfChecked: Key[] }) => {
    const keys = Array.isArray(checkedKeys) ? checkedKeys : checkedKeys.checked;
    const selectedIds = keys.map(String).filter((key) => key.startsWith("document:")).map((key) => Number(key.slice("document:".length))).filter((id) => id > 0);
    if (selectedIds.length > AGENT_DOCUMENT_LIMIT) message.warning(`单轮最多选择 ${AGENT_DOCUMENT_LIMIT} 份材料`);
    setAgentDocumentIds(selectedIds.slice(0, AGENT_DOCUMENT_LIMIT));
  };
  const stopCaseAgentResponse = () => {
    activeCaseAgentRequestRef.current?.abort();
    activeCaseAgentRequestRef.current = null;
    setAgentSending(false);
    message.info("已停止本轮生成，可以继续补充要求");
  };
  
  const pasteCaseAgentScreenshot = (event: ClipboardEvent<HTMLTextAreaElement>) => {
    const itemFile = Array.from(event.clipboardData.items)
      .find((item) => item.kind === "file" && item.type.startsWith("image/"))
      ?.getAsFile();
    const file = itemFile || Array.from(event.clipboardData.files).find((item) => item.type.startsWith("image/"));
    if (!file) return;
    event.preventDefault();
    if (agentSkillId !== "screenshot-evidence") setAgentSkillId("screenshot-evidence");
    void uploadCaseAgentScreenshot(file);
  };
  
  useEffect(() => {
    if (!agentOpen) return;
    requestAnimationFrame(() => agentMessagesEndRef.current?.scrollIntoView({ behavior: "auto", block: "end" }));
  }, [agentOpen, agentState?.messages.length]);
  
  useEffect(() => () => clearAgentScreenshotPreviews(), []);

  const openRelatedContract = (target: { id?: number; serial_no?: unknown } | unknown) => {
    const contractId = typeof target === "object" && target ? Number((target as { id?: number }).id || 0) || undefined : undefined;
    const serialNo = String(typeof target === "object" && target ? (target as { serial_no?: unknown }).serial_no || "" : target || "").trim();
    if (!contractId && (!serialNo || serialNo === "—")) {
      message.warning("当前记录未关联合同");
      return;
    }
    rememberContractDetailTarget({ id: contractId, serial_no: serialNo || undefined });
    onNavigate?.("contract-company");
  };
  
  const openRelatedTask = (task: TaskRow) => {
    if (!task.id) return message.warning("当前案件任务未生成可查看编号");
    setCaseTaskFeedbackText("");
    setCaseTaskFeedbackFiles([]);
    void loadCaseTaskDetail(task);
  };
  const closeCaseTaskDetail = () => {
    setViewingCaseTask(null);
    setCaseTaskHistory([]);
    setCaseTaskDetailMaterials([]);
    setCaseTaskDetailFeedbacks([]);
    setCaseTaskFeedbackText("");
    setCaseTaskFeedbackFiles([]);
  };
  const canWithdrawCaseTask = (task: TaskRow | null) => Boolean(
    task &&
    (profile.role === "admin" || task.initiator === profile.username) &&
    ["待接收", "待处理", "处理中", "进行中"].includes(task.workflow_status || task.status),
  );
  const withdrawCaseTask = (task: TaskRow) => {
    let reason = "";
    Modal.confirm({
      title: `撤回任务：${task.serial_no}`,
      content: <Input.TextArea rows={4} placeholder="请填写撤回原因" onChange={(event) => { reason = event.target.value; }} />,
      okText: "确认撤回",
      cancelText: "取消",
      okButtonProps: { danger: true },
      onOk: async () => {
        if (!reason.trim()) {
          message.warning("请填写撤回原因");
          throw new Error("撤回原因不能为空");
        }
        await api.post(`/tasks/${task.id}/withdraw`, { comment: reason.trim() });
        message.success("任务已撤回");
        setCaseTasks((items) => items.map((item) => item.id === task.id ? { ...item, status: "已撤回", workflow_status: "已撤回" } : item));
        setCounselDetailTasks((items) => items.map((item) => item.id === task.id ? { ...item, status: "已撤回", workflow_status: "已撤回" } : item));
        await loadCaseTaskDetail({ ...task, status: "已撤回", workflow_status: "已撤回" });
      },
    });
  };

  const openRelatedIncomingPayment = (fee: CaseRow) => {
    const payments = Array.isArray(fee.data.incoming_payments) ? fee.data.incoming_payments : [];
    if (!payments.length) {
      message.warning("当前费用未关联可查看的回款记录");
      return;
    }
    setViewingFeeIncomingPayments(payments);
  };
  const openIncomingPaymentDetail = (paymentId: number) => {
    if (!Number(paymentId || 0)) {
      message.warning("当前回款记录不存在或无权查看");
      return;
    }
    setViewingFeeIncomingPayments(null);
    onNavigate?.(incomingPaymentDetailRoute(paymentId));
  };
  const openRelatedInvoice = (fee: CaseRow) => {
    const invoiceId = Number(fee.data.invoice_record_id || 0);
    if (!rememberBusinessRecordDetailTarget({ id: invoiceId, module: "invoice" })) {
      message.warning("当前费用未关联可查看的发票记录");
      return;
    }
    onNavigate?.("finance-invoice-company");
  };

  const selectedCaseClueEvidence = viewingCaseClue?.evidence.find((item) => item.id === selectedCaseClueEvidenceId) || null;
  const openCaseClueEvidenceEditor = () => {
    if (!selectedCaseClueEvidence) return message.warning("请先选择一条取证信息");
    if (!selectedCaseClueEvidence.can_edit) return message.warning("当前账号无权修改该取证信息");
    caseClueEvidenceForm.setFieldsValue({
      notary_institution: selectedCaseClueEvidence.data.notary_institution || "",
      certificate_no: selectedCaseClueEvidence.data.notarization_no || selectedCaseClueEvidence.data.certificate_no || "",
      collected_at: selectedCaseClueEvidence.data.collected_at ? dayjs(selectedCaseClueEvidence.data.collected_at) : undefined,
      invoice_no: selectedCaseClueEvidence.data.invoice_no || "",
      storage_location: selectedCaseClueEvidence.data.storage_location || "",
      evidence_status: selectedCaseClueEvidence.data.storage_state || selectedCaseClueEvidence.data.evidence_status || "未入库",
    });
    setEditingCaseClueEvidence(selectedCaseClueEvidence);
  };
  
  const closeCaseClueWorkspace = () => {
    setViewingCaseClue(null);
    setSelectedCaseClueEvidenceId(null);
    setEditingCaseClueEvidence(null);
    caseClueEvidenceForm.resetFields();
  };
  const deleteCaseClueEvidence = () => {
    if (!selectedCaseClueEvidence) return message.warning("请先选择一条取证信息");
    if (!selectedCaseClueEvidence.can_delete) return message.warning("当前账号无权删除该取证信息");
    Modal.confirm({
      title: "删除取证信息",
      content: `确定删除 ${selectedCaseClueEvidence.serial_no || "当前取证记录"} 吗？`,
      okText: "确定",
      cancelText: "取消",
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await api.delete(`/investigations/evidence/${selectedCaseClueEvidence.id}`);
          if (!viewingCaseClue) return;
          const { data } = await api.get(`/investigations/clues/${viewingCaseClue.clue.id}/workspace`);
          setViewingCaseClue(data);
          setSelectedCaseClueEvidenceId(null);
          message.success("取证信息已删除");
        } catch (error: any) {
          message.error(error?.response?.data?.detail || "取证信息删除失败");
          throw error;
        }
      },
    });
  };
  const renderCaseClueWorkspace = () => viewingCaseClue ? (
    <aside className="case-clue-context-panel" aria-label="案件内线索信息" data-testid="case-clue-context-panel">
      <div className="case-clue-context-header">
        <strong>线索信息</strong>
        <Button type="text" size="small" icon={<CloseOutlined />} aria-label="关闭线索信息" onClick={closeCaseClueWorkspace}>关闭</Button>
      </div>
      <div className="case-clue-context-body">
        <Descriptions
          bordered
          size="small"
          column={2}
          items={[
            { key: "serial", label: "线索编号", children: viewingCaseClue.clue.serial_no || "—" },
            { key: "method", label: "侵权方式", children: viewingCaseClue.clue.data.infringement_method || viewingCaseClue.clue.data.infringement_type || "—" },
            { key: "investigated", label: "调查时间", children: String(viewingCaseClue.clue.data.investigated_at || viewingCaseClue.clue.data.investigation_time || viewingCaseClue.clue.data.investigation_date || "").replace("T", " ").slice(0, 19) || "—" },
            { key: "shop", label: "店铺名称", children: viewingCaseClue.clue.data.shop_name || viewingCaseClue.clue.data.store_name || viewingCaseClue.clue.title || "—" },
            { key: "shop-id", label: "店铺Id", children: viewingCaseClue.clue.data.shop_id || viewingCaseClue.clue.data.store_id || "—" },
            { key: "shop-link", label: "店铺链接", children: viewingCaseClue.clue.data.shop_link || viewingCaseClue.clue.data.store_link ? <a href={viewingCaseClue.clue.data.shop_link || viewingCaseClue.clue.data.store_link} target="_blank" rel="noreferrer">{viewingCaseClue.clue.data.shop_link || viewingCaseClue.clue.data.store_link}</a> : "—", span: 2 },
            { key: "region", label: "调查区域", children: viewingCaseClue.clue.data.investigation_region || viewingCaseClue.clue.data.region || "—" },
            { key: "address", label: "侵权地址", children: viewingCaseClue.clue.data.infringement_address || viewingCaseClue.clue.data.shop_address || viewingCaseClue.clue.data.address || "—" },
            { key: "investigator", label: "调查员", children: viewingCaseClue.clue.data.investigator_display_name || viewingCaseClue.clue.owner_display_name || viewingCaseClue.clue.owner || "—" },
            { key: "assistant", label: "调查辅助", children: viewingCaseClue.clue.data.investigation_assistant_display_name || viewingCaseClue.clue.data.investigation_assistant || "—" },
            { key: "remark", label: "调查员备注", children: viewingCaseClue.clue.data.investigator_comment || viewingCaseClue.clue.description || "—", span: 2 },
            { key: "status", label: "审批状态", children: viewingCaseClue.clue.status || "—" },
            { key: "manager-comment", label: "管理人审核备注", children: viewingCaseClue.clue.data.manager_review_comment || viewingCaseClue.clue.data.review_comment || "—" },
            { key: "customer-comment", label: "客户审核备注", children: viewingCaseClue.clue.data.customer_review_comment || "—", span: 2 },
          ]}
        />
        <section className="case-clue-context-section">
          <h3>线索文件</h3>
          <Table<AttachmentRow>
            rowKey="id"
            size="small"
            loading={caseClueLoading}
            pagination={false}
            dataSource={viewingCaseClue.clue_files || []}
            locale={{ emptyText: "没有查询到线索文件。" }}
            columns={[
              { title: "上传人", width: 110, render: (_, row) => row.uploader_display_name || row.uploader || "—" },
              { title: "文件名称", dataIndex: "original_name" },
              { title: "文档日期", width: 150, render: (_, row) => String(row.created_at || "").replace("T", " ").slice(0, 19) || "—" },
              { title: "操作", width: 70, render: (_, row) => <Button type="link" onClick={() => void downloadCounselDetailAttachment(row)}>下载</Button> },
            ]}
          />
        </section>
        <section className="case-clue-context-section">
          <h3>取证信息</h3>
          <Table<CaseClueEvidenceRow>
            rowKey="id"
            size="small"
            loading={caseClueLoading}
            pagination={false}
            rowSelection={{
              type: "radio",
              selectedRowKeys: selectedCaseClueEvidenceId ? [selectedCaseClueEvidenceId] : [],
              onChange: (keys) => setSelectedCaseClueEvidenceId(Number(keys[0]) || null),
            }}
            dataSource={viewingCaseClue.evidence || []}
            locale={{ emptyText: "没有查询到取证信息。" }}
            scroll={{ x: 1040 }}
            columns={[
              { title: "公证书号", width: 170, render: (_, row) => row.data.notarization_no || row.data.certificate_no || "—" },
              { title: "取证时间", width: 120, render: (_, row) => row.data.collected_at || "—" },
              { title: "取证机构", width: 180, render: (_, row) => row.data.notary_institution || "—" },
              { title: "发票号", width: 130, render: (_, row) => row.data.invoice_no || "—" },
              { title: "仓库", width: 130, render: (_, row) => row.data.warehouse_name || row.data.warehouse || row.data.storage_location || "—" },
              { title: "库位", width: 120, render: (_, row) => row.data.storage_location_name || row.data.location_name || row.data.storage_location || "—" },
              { title: "状态", width: 105, render: (_, row) => row.data.storage_state || row.data.evidence_status || row.status || "—" },
              { title: "文件", width: 70, render: (_, row) => row.files?.length || 0 },
            ]}
          />
          <Space className="case-clue-context-actions">
            <Button danger disabled={!selectedCaseClueEvidence?.can_delete} onClick={deleteCaseClueEvidence}>删除</Button>
            <Button disabled={!selectedCaseClueEvidence?.can_edit} onClick={openCaseClueEvidenceEditor}>修改</Button>
          </Space>
        </section>
      </div>
    </aside>
  ) : null;
  const openClueConversion = () => {
    clueConversionForm.resetFields();
    clueConversionForm.setFieldsValue({ case_type: "民事案件" });
    setClueConversionOpen(true);
  };
  
  const openRelatedOriginalCase = (target: { id?: number; serial_no?: unknown }) => {
    const id = Number(target.id || 0) || undefined;
    const serialNo = String(target.serial_no || "").trim();
    if (!rememberCaseDetailTarget({ id, serial_no: serialNo || undefined })) {
      message.warning("当前案件未关联原案件");
      return;
    }
    onNavigate?.("case-company");
  };

  const deleteCounselReminder = (reminder:CaseReminderRow) => {
    if (!viewingCounselCase) return;
    Modal.confirm({title:"删除案件提醒",content:`确认删除“${reminder.description}”吗？`,okText:"删除",okButtonProps:{danger:true},onOk:async()=>{
      try {
        await api.delete(`/cases/${viewingCounselCase.id}/reminders/${reminder.id}`);
        message.success("案件提醒已删除");
        await openCounselDetail(viewingCounselCase);
      } catch(error:any){message.error(error?.response?.data?.detail||"案件提醒删除失败");}
    }});
  };
  
  const openCaseEventEditor = (event?: CaseEventRow) => {
    setEditingCaseEvent(event || null);
    caseEventForm.resetFields();
    caseEventForm.setFieldsValue({
      event_type: event?.event_type || "",
      content: event?.content || "",
      event_time: event?.event_time ? dayjs(event.event_time) : dayjs(),
      deadline: event?.deadline ? dayjs(event.deadline) : undefined,
      reminder_enabled: Boolean(event?.reminder_enabled),
      remind_at: event?.remind_at ? dayjs(event.remind_at) : undefined,
      status: event?.status === "已完成" ? "已完成" : "待处理",
    });
    setCaseEventOpen(true);
  };
  
  const deleteCounselCaseEvent = (event: CaseEventRow) => {
    if (!viewingCounselCase) return;
    if (caseEventSubmitting) return;
    Modal.confirm({ title: "删除案件事件", content: `确认删除“${event.event_type}”吗？`, okText: "删除", okButtonProps: { danger: true }, onOk: async () => {
      try {
        setCaseEventSubmitting(true);
        await api.delete(`/cases/${viewingCounselCase.id}/events/${event.id}`);
        message.success("案件事件已删除");
        await loadCounselCaseEvents(viewingCounselCase);
      } catch (error: any) { message.error(error?.response?.data?.detail || "删除案件事件失败"); } finally { setCaseEventSubmitting(false); }
    }});
  };
  const deleteCounselCaseEvents = () => {
    if (!viewingCounselCase) return;
    if (caseEventSubmitting) return;
    const eventIds = selectedCounselCaseEventKeys.map(Number).filter((id) => counselCaseEvents.some((event) => event.id === id && event.can_delete));
    if (!eventIds.length) return message.warning("请选择需要删除的案件事件");
    Modal.confirm({ title: "批量删除案件事件", content: `确认删除选中的 ${eventIds.length} 个案件事件吗？`, okText: "删除", okButtonProps: { danger: true }, onOk: async () => {
      try {
        setCaseEventSubmitting(true);
        const { data } = await api.delete(`/cases/${viewingCounselCase.id}/events`, { data: { event_ids: eventIds } });
        message.success(`已删除 ${data.deleted ?? eventIds.length} 个案件事件`);
        await loadCounselCaseEvents(viewingCounselCase);
      } catch (error: any) { message.error(error?.response?.data?.detail || "批量删除案件事件失败"); } finally { setCaseEventSubmitting(false); }
    }});
  };
  const openCounselLogCreator = (kind: CaseLogKind) => {
    if (!viewingCounselCase) return;
    setCaseLogTarget(viewingCounselCase);
    setCaseLogKind(kind);
    caseLogForm.resetFields();
    setCaseLogOpen(true);
  };
  const openCaseLogViewer = (row: CaseRow) => {
    void openCounselDetail(row, "case-logs");
  };
  const openCaseListLogCreator = (row: CaseRow) => {
    if (!getCaseCapability(row).can_create_log) return message.warning("当前账号没有新增该案件日志的权限");
    setCaseLogTarget(row);
    setCaseLogKind("case");
    caseLogForm.resetFields();
    setCaseLogOpen(true);
  };

  const closeAttachmentPreview = () => {
    if (attachmentPreview?.url) URL.revokeObjectURL(attachmentPreview.url);
    setAttachmentPreview(null);
  };
  const deleteCounselAttachments = () => {
    const selectionValidationError = getCaseAttachmentSelectionValidationError(selectedCounselAttachmentKeys, "删除");
    if(selectionValidationError)return message.warning(selectionValidationError);
    if(!viewingCounselCase)return message.warning("请先打开案件详情");
    Modal.confirm({title:"批量删除案件文件",content:`确认删除选中的 ${selectedCounselAttachmentKeys.length} 个文件吗？该操作会记录审计日志。`,okText:"删除",okButtonProps:{danger:true},onOk:async()=>{
      try{
        const {data}=await api.post("/cases/attachments/delete",{attachment_ids:selectedCounselAttachmentKeys.map(Number),case_id:isRelatedDocumentFolder?viewingCounselCase.id:undefined});message.success(`已删除 ${data.deleted} 个文件`);await openCounselDetail(viewingCounselCase);
      }catch(error:any){message.error(error?.response?.data?.detail||"案件文件删除失败");}
    }});
  };
  const selectedCounselAttachments = () => {
    const selected = new Set(selectedCounselAttachmentKeys.map(Number));
    return [...counselDetailAttachments, ...counselDetailCustomerAttachments, ...counselDetailContractAttachments]
      .filter((item, index, all) => selected.has(item.id) && all.findIndex((candidate) => candidate.id === item.id) === index);
  };
  const canApplySealToCounselAttachment = (item: AttachmentRow) =>
    item.record_id === viewingCounselCase?.id && /\.docx?$/i.test(item.original_name);
  const handleCounselDocumentMoreAction = (key: string) => {
    if (key === "delete") return deleteCounselAttachments();
    const selected = selectedCounselAttachments();
    if (key === "seal") {
      if (selected.length !== 1) return message.warning("请先选择一个文件再申请用印");
      if (!canApplySealToCounselAttachment(selected[0])) return message.warning("仅案件中的 Word 文件可以申请用印");
      return void openCounselAttachmentSeal(selected[0]);
    }
    if (key === "move") {
      if (!selected.length) return message.warning("请先选择需要更改目录的文件");
      if (selected.some((item) => item.record_id !== viewingCounselCase?.id)) return message.warning("客户文档和合同文档不能移动到案件文档目录");
      caseAttachmentMoveForm.setFieldsValue({ category: activeCounselDocCategory === "案件文档全部" ? undefined : activeCounselDocCategory });
      setMovingCounselAttachmentIds(selected.map((item) => item.id));
    }
  };
  
  const openCounselAttachmentRename = (item: AttachmentRow) => {
    attachmentRenameForm.setFieldsValue({ original_name: item.original_name });
    setRenamingCounselAttachment(item);
  };
  
  const openCreateAiDraft = () => {
    aiDraftForm.setFieldsValue({ name: `AI文档-${dayjs().format("YYYYMMDD-HHmm")}.docx`, content: "" });
    setAiDraftEditor({ mode: "create" });
  };
  
  const wordEditorChanged = (editor: CaseWordEditor) => JSON.stringify(editor.blocks) !== JSON.stringify(editor.savedBlocks);

  const requestCloseCaseWordEditor = () => {
    if (!wordEditor) return;
    if (!wordEditorChanged(wordEditor)) {
      void finishClosingCaseWordEditor(wordEditor);
      return;
    }
    Modal.confirm({
      title: "尚有未保存的 Word 修改",
      content: "关闭后未保存的修改将不会写回案件文件。",
      okText: "放弃修改并关闭",
      okButtonProps: { danger: true },
      cancelText: "继续编辑",
      onOk: () => finishClosingCaseWordEditor(wordEditor),
    });
  };

  useEffect(() => {
    if (!wordEditor) return;
    const renew = async () => {
      if (wordEditorSavingRef.current) return;
      try {
        const { data } = await api.post(
          `/cases/${wordEditor.caseId}/attachments/${wordEditor.item.id}/word-editor/lock/renew`,
          { lock_token: wordEditor.lockToken },
        );
        setWordEditor((current) => current?.lockToken === wordEditor.lockToken ? { ...current, expiresAt: data.lock_expires_at || current.expiresAt } : current);
      } catch (error: any) {
        if (wordEditorLockTokenRef.current !== wordEditor.lockToken) return;
        const detail = error?.response?.data?.detail;
        message.error((typeof detail === "string" ? detail : detail?.message) || "Word 编辑锁续期失败，请尽快保存并重新打开文件");
      }
    };
    const timer = window.setInterval(() => void renew(), 120000);
    return () => {
      window.clearInterval(timer);
      void releaseCaseWordEditorLock(wordEditor);
    };
  }, [wordEditor?.caseId, wordEditor?.item.id, wordEditor?.lockToken]);
  useEffect(() => {
    if (!wordEditor || !wordEditorChanged(wordEditor)) return;
    const warnBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warnBeforeUnload);
    return () => window.removeEventListener("beforeunload", warnBeforeUnload);
  }, [wordEditor]);
  
  const deleteAiDraft = (item: AttachmentRow) => {
    if (!viewingCounselCase) return;
    Modal.confirm({
      title: `删除 AI 草稿：${item.original_name}`,
      content: "删除后无法恢复，且不会影响已经转入正式系统的文件。",
      okText: "删除",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onOk: async () => {
        try {
          await api.post("/cases/attachments/delete", { attachment_ids: [item.id] });
          message.success("AI 草稿已删除");
          await openCounselDetail(viewingCounselCase);
          selectCounselDocCategory("AI空间");
        } catch (error: any) {
          message.error(error?.response?.data?.detail || "AI 草稿删除失败");
          throw error;
        }
      },
    });
  };

  const selectCounselDocCategory = (category: string) => {
    const applicableOptions = fileTypeOptionsForCase(viewingCounselCase?.data.case_type);
    setActiveCounselDocCategory(category);
    if (category === "AI空间") {
      setCounselUploadCategory("AI空间");
      setSelectedCounselAttachmentKeys([]);
      if (viewingCounselCase) {
        void refreshCounselDetailAttachments(viewingCounselCase.id).catch(() => message.error("AI 空间材料刷新失败"));
      }
      return;
    }
    if (
      ["客户文档","合同文档",...AGENT_INVESTIGATION_DOCUMENT_FOLDERS].includes(category)
      || AGENT_CASE_DOCUMENT_FOLDERS.includes(category)
      || hasCaseFileTypeOption(category, applicableOptions)
      || getCustomCaseDocumentFolders(viewingCounselCase).includes(category)
    ) {
      setCounselUploadCategory(category);
      setSelectedCounselAttachmentKeys([]);
      return;
    }
    setCounselUploadCategory(hasCaseFileTypeOption(category, applicableOptions) ? category : DEFAULT_CASE_ATTACHMENT_CATEGORY);
    setSelectedCounselAttachmentKeys([]);
  };
  const toggleCounselDocGroup = (category: string) => {
    setExpandedCounselDocGroups((current) => ({ ...current, [category]: !current[category] }));
    selectCounselDocCategory(category);
  };
  const openCaseDocumentFolderEditor = (editor: CaseDocumentFolderEditor) => {
    caseDocumentFolderForm.setFieldValue("name", editor.originalName || "");
    setCaseDocumentFolderEditor(editor);
  };
  
  const deleteCaseDocumentFolder = (name:string) => {
    if (!viewingCounselCase) return;
    Modal.confirm({title:`删除目录：${name}`,content:"仅空目录可以删除。确认删除当前自定义目录吗？",okText:"删除",okButtonProps:{danger:true},cancelText:"取消",onOk:async()=>{
      try {
        const {data}=await api.delete(`/cases/${viewingCounselCase.id}/document-folders`,{data:{name}});
        const folders=Array.isArray(data?.folders)?data.folders:[];
        setViewingCounselCase((current)=>current?({...current,data:{...current.data,custom_case_document_folders:folders}}):current);
        await refreshCounselDocumentFolderTree(viewingCounselCase.id);
        if(activeCounselDocCategory===name)selectCounselDocCategory("案件文档全部");
        message.success("案件文档目录已删除");
      } catch(error:any) { message.error(error?.response?.data?.detail||"案件文档目录删除失败"); throw error; }
    }});
  };
  const openCounselEdit = (row: CaseRow) => {
    counselEditForm.setFieldsValue({
      title: row.title,
      customer: row.customer,
      counsel_type: row.data.counsel_type || "",
      counsel_range: row.data.counsel_start && row.data.counsel_end ? [dayjs(row.data.counsel_start), dayjs(row.data.counsel_end)] : undefined,
      handling_lawyers: resolveCasePersonValues(row.data.handling_lawyers || []),
      assistant: resolveCasePersonValue(row.data.assistant || ""),
      comment: "",
    });
    setEditingCounselCase(row);
  };
  
  const isNormalEditableCase = (row: CaseRow) => isNormalCaseBasicType(row.data.case_type);

  const openCriminalMaintenance = (row:CaseRow, kind:"litigants"|"public-security"|"procuratorates"|"courts") => {
    const dateFields=["first_court_filing_date","first_court_hearing_date","second_court_filing_date","second_court_hearing_date","execution_court_filing_date","execution_court_hearing_date","retrial_court_filing_date","retrial_court_hearing_date"];
    criminalMaintenanceForm.setFieldsValue({
      ...row.data,
      plaintiff_agents: normalizeCaseLitigantAgents(row.data.plaintiff_agents),
      defendant_agents: normalizeCaseLitigantAgents(row.data.defendant_agents),
      third_party_agents: normalizeCaseLitigantAgents(row.data.third_party_agents),
      ...Object.fromEntries(dateFields.map(key=>[key,row.data[key]?dayjs(row.data[key]):undefined])),
      comment:"",
    }); setCriminalMaintenance({row,kind});
  };

  const searchCaseLitigantCandidates = (keyword: string) => {
    window.clearTimeout(caseLitigantSearchTimerRef.current);
    caseLitigantSearchTimerRef.current = window.setTimeout(() => void loadCaseLitigantCandidates(keyword), 350);
  };
  const openCasePartyCreator = (role: CaseLitigantPartyField) => {
    casePartyCreateForm.resetFields();
    casePartyCreateForm.setFieldsValue({ title: "", credit_code: "", phone: "", legal_representative: "", registered_address: "" });
    setCreatingCasePartyRole(role);
  };
  
  const renderCasePartySelector = (role: CaseLitigantPartyField, required = false) => (
    <Form.Item label={CASE_LITIGANT_PARTY_LABELS[role]} required={required}>
      <Space.Compact block>
        <Form.Item name={role} noStyle rules={required ? [{ required: true, message: `请至少选择一名${CASE_LITIGANT_PARTY_LABELS[role]}` }] : undefined}>
          <Select
            mode="multiple"
            showSearch
            filterOption={false}
            onSearch={searchCaseLitigantCandidates}
            onOpenChange={(open) => { if (open) void loadCaseLitigantCandidates(""); }}
            loading={caseLitigantCandidatesLoading}
            placeholder={`输入关键字搜索${CASE_LITIGANT_PARTY_LABELS[role]}`}
            notFoundContent={caseLitigantCandidatesLoading ? "正在搜索..." : "未找到系统当事人，可点击右侧新增"}
            options={caseLitigantCandidates.map((item) => ({
              value: item.title,
              label: item.serial_no ? `${item.title}（${item.serial_no}）` : item.title,
            }))}
            style={{ flex: 1 }}
          />
        </Form.Item>
        <Button icon={<PlusOutlined />} aria-label={`新增${CASE_LITIGANT_PARTY_LABELS[role]}当事人`} title={`新增${CASE_LITIGANT_PARTY_LABELS[role]}当事人`} onClick={() => openCasePartyCreator(role)} />
      </Space.Compact>
    </Form.Item>
  );
  const renderCaseLitigantAgentEditor = (fieldName: CaseLitigantAgentField, label = CASE_LITIGANT_AGENT_LABELS[fieldName]) => (
    <Card
      key={fieldName}
      size="small"
      title={label}
      style={{ marginBottom: 12 }}
      extra={<span style={{ color: "#8c8c8c", fontSize: 12 }}>按本案独立维护</span>}
    >
      <Form.List name={fieldName}>
        {(fields, { add, remove }) => <>
          {fields.map((field) => <Card key={field.key} size="small" style={{ marginBottom: 10, background: "#fafafa" }}>
            <div className="form-grid">
              <Form.Item {...field} name={[field.name, "name"]} label="姓名" rules={[{ required: true, whitespace: true, message: "请输入代理人姓名" }]}><Input maxLength={256} /></Form.Item>
              <Form.Item {...field} name={[field.name, "law_firm"]} label="律所"><Input maxLength={256} /></Form.Item>
              <Form.Item {...field} name={[field.name, "position"]} label="职务"><Input maxLength={128} /></Form.Item>
              <Form.Item {...field} name={[field.name, "phone"]} label="电话"><Input maxLength={64} /></Form.Item>
            </div>
            <Form.Item {...field} name={[field.name, "authority"]} label="代理权限"><Input.TextArea autoSize={{ minRows: 2, maxRows: 4 }} maxLength={500} /></Form.Item>
            <Button danger type="link" icon={<MinusCircleOutlined />} onClick={() => remove(field.name)}>删除代理人</Button>
          </Card>)}
          <Button type="dashed" block icon={<PlusOutlined />} onClick={() => add({ name: "", law_firm: "", position: "", phone: "", authority: "" })}>新增{label}</Button>
        </>}
      </Form.List>
    </Card>
  );
  const openCaseLitigants = (row: CaseRow) => {
    if (ARCHIVE_LOCKED_STATUSES.includes(row.status)) return message.warning("归档中的案件不能修改当事人");
    caseLitigantsForm.setFieldsValue({
      plaintiffs: row.data.plaintiffs || (row.data.plaintiff ? [row.data.plaintiff] : row.customer ? [row.customer] : []),
      plaintiff_agents: normalizeCaseLitigantAgents(row.data.plaintiff_agents),
      defendants: row.data.defendants || (row.data.opponent ? [row.data.opponent] : []),
      defendant_agents: normalizeCaseLitigantAgents(row.data.defendant_agents),
      third_parties: row.data.third_parties || [],
      third_party_agents: normalizeCaseLitigantAgents(row.data.third_party_agents),
      comment: "",
    });
    setEditingCaseLitigants(row);
    void loadCaseLitigantCandidates("");
  };
  
  const openCaseHearingLawyer = (row: CaseRow) => {
    const capability = viewingCounselCase?.id === row.id ? counselDetailCapabilities : getCaseCapability(row);
    if (!capability.can_edit_hearing_lawyer) return message.warning("当前账号无权查看或修改该案件");
    if (ARCHIVE_LOCKED_STATUSES.includes(row.status)) return message.warning("归档中的案件不能修改开庭律师");
    caseHearingLawyerForm.setFieldsValue({ hearing_lawyer: row.data.hearing_lawyer || "", comment: "" });
    setEditingCaseHearingLawyer(row);
  };
  
  const openCaseTaskCreator = (row: CaseRow) => {
    if (!getCaseCapability(row).can_create_case_task) return message.warning("当前账号没有创建该案件任务的权限");
    taskForm.resetFields();
    const startAt = dayjs().second(0);
    taskForm.setFieldsValue({ owner: profile.username || row.owner, start_at: startAt, end_at: startAt.add(7, "day"), priority: "普通", collaborators: [], is_vip: false });
    setCaseTaskMaterialFiles([]);
    setCaseTaskKind("案件任务");
    setCaseTaskCreateCase(row);
  };
  
  const caseTaskBasePagination = getCaseTaskPagination();
  const caseTaskPagination = {
    current: caseTaskPage,
    pageSize: caseTaskPageSize,
    total: caseTaskTotal,
    pageSizeOptions: caseTaskBasePagination.pageSizeOptions,
    showSizeChanger: caseTaskBasePagination.showSizeChanger,
    showTotal: (total: number) => `共 ${total} 项${caseTaskPages ? ` / ${caseTaskPages} 页` : ""}`,
    onChange: (nextPage: number, nextPageSize: number) => {
      if (taskCase) void loadCaseTasksPage(taskCase, nextPage, nextPageSize);
    },
  };
  const counselDetailTaskPagination = {
    current: counselDetailTaskPage,
    pageSize: counselDetailTaskPageSize,
    total: counselDetailTaskTotal,
    pageSizeOptions: caseTaskBasePagination.pageSizeOptions,
    showSizeChanger: caseTaskBasePagination.showSizeChanger,
    showTotal: (total: number) => `共 ${total} 项${counselDetailTaskPages ? ` / ${counselDetailTaskPages} 页` : ""}`,
    onChange: (nextPage: number, nextPageSize: number) => {
      if (viewingCounselCase) void loadCounselDetailTasksPage(viewingCounselCase, nextPage, nextPageSize);
    },
  };
  const counselDetailCustomerTaskPagination = {
    current: counselDetailCustomerTaskPage,
    pageSize: counselDetailCustomerTaskPageSize,
    total: counselDetailCustomerTaskTotal,
    pageSizeOptions: caseTaskBasePagination.pageSizeOptions,
    showSizeChanger: caseTaskBasePagination.showSizeChanger,
    showTotal: (total: number) => `共 ${total} 项${counselDetailCustomerTaskPages ? ` / ${counselDetailCustomerTaskPages} 页` : ""}`,
    onChange: (nextPage: number, nextPageSize: number) => {
      if (viewingCounselCase) void loadCounselDetailCustomerTasksPage(viewingCounselCase, nextPage, nextPageSize);
    },
  };
  const counselDetailCluePagination = {
    current: counselDetailCluePage,
    pageSize: counselDetailCluePageSize,
    total: counselDetailClueTotal,
    pageSizeOptions: caseTaskBasePagination.pageSizeOptions,
    showSizeChanger: caseTaskBasePagination.showSizeChanger,
    showTotal: (total: number) => `共 ${total} 条${counselDetailCluePages ? ` / ${counselDetailCluePages} 页` : ""}`,
    onChange: (nextPage: number, nextPageSize: number) => {
      if (viewingCounselCase) void loadCounselDetailCluesPage(viewingCounselCase, nextPage, nextPageSize)
        .catch((error: any) => message.error(error?.response?.data?.detail || "关联线索加载失败"));
    },
  };

  const openPaymentTypeCreator = (feeId: number, draftIndex?: number) => {
    paymentTypeCreateForm.resetFields();
    paymentTypeCreateForm.setFieldsValue({ nature: "官费", payee: paymentTypeSearch.trim() });
    setPaymentTypeCreateTarget({ feeId, draftIndex });
  };

  const closeCaseFeeCreator = () => {
    setFeeCase(null);
    setFeeSubtypePreset("");
    setCaseFeeCreateStep(0);
    setCreatedCaseFees([]);
    setCaseFeePaymentDrafts([]);
    setCasePaymentTypes([]);
    setPaymentTypeSearch("");
    setPaymentTypeCreateTarget(null);
    feeForm.resetFields();
  };
  
  const openCourtRefund = (row: CaseRow) => {
    const amount = Number(row.data.amount || 0);
    const refunded = Number(row.data.refund_amount || row.data.refund_requested_amount || 0);
    courtRefundForm.resetFields();
    courtRefundForm.setFieldsValue({ amount: Math.max(amount - refunded, 0) });
    setCourtRefundFee(row);
  };
  
  const deleteCaseFee = (row: CaseRow) => {
    if (row.status !== "草稿") return message.warning("仅草稿费用可以删除");
    Modal.confirm({ title: `删除费用：${row.serial_no}`, content: "删除后不可恢复，是否继续？", okText: "确认删除", cancelText: "取消", onOk: async () => {
      try { await api.delete(isInternalCaseFee(row) ? `/finance/internal-fees/${row.id}` : `/finance/fees/${row.id}`); message.success("费用草稿已删除"); await load(); if (viewingCounselCase) await openCounselDetail(viewingCounselCase); }
      catch (error: any) { message.error(error?.response?.data?.detail || "费用删除失败"); }
    }});
  };
  const markCaseFeeNoPayment = (row: CaseRow) => {
    if (!["草稿", "已退回"].includes(row.status)) return message.warning("仅草稿或已退回费用可以标记不缴费");
    Modal.confirm({
      title: `标记不缴费：${row.serial_no}`,
      content: "标记后该费用不会再进入付款审批，是否继续？",
      okText: "确认标记",
      cancelText: "取消",
      onOk: async () => {
        try {
          await api.post(`/finance/fees/${row.id}/mark-no-payment`, { comment: "案件费用标记不缴费" });
          message.success("费用已标记为不缴费");
          await load();
          if (viewingCounselCase) await openCounselDetail(viewingCounselCase);
        } catch (error: any) {
          message.error(error?.response?.data?.detail || "标记不缴费失败");
        }
      },
    });
  };
  const canMarkCaseFeeRefundNotRequired = (row: CaseRow | undefined) => {
    if (!row || row.data.refund_status === "R100" || row.data.refund_not_required) return false;
    const legacyRefundStatus = row.data.legacy_record && typeof row.data.legacy_record === "object"
      ? row.data.legacy_record.RefundStatus
      : undefined;
    return Boolean(
      row.data.refund_status
      || row.data.refund_status_label
      || legacyRefundStatus
      || Number(row.data.refund_requested_amount || row.data.refund_amount || row.data.refunded_amount || 0) > 0
    );
  };
  const markCaseFeeRefundNotRequired = (row: CaseRow) => {
    if (!canMarkCaseFeeRefundNotRequired(row)) return message.warning("仅有退费记录且尚未终止退费的费用可以标记不再办理退费");
    let comment = "";
    Modal.confirm({
      title: `标记不再办理退费：${row.serial_no}`,
      content: <Input.TextArea rows={4} maxLength={1000} placeholder="请输入备注（可选）" onChange={(event) => { comment = event.target.value; }} />,
      okText: "确认标记",
      cancelText: "取消",
      onOk: async () => {
        try {
          await api.post(`/finance/fees/${row.id}/mark-refund-not-required`, { comment: comment.trim() });
          message.success("费用已标记为不再办理退费");
          await load();
          if (viewingCounselCase) await openCounselDetail(viewingCounselCase);
        } catch (error: any) {
          message.error(error?.response?.data?.detail || "标记不再办理退费失败");
        }
      },
    });
  };
  const editCaseFee = (row: CaseRow) => {
    if (row.status !== "草稿") return message.warning("仅草稿费用可以修改");
    setFeeSubtypePreset("");
    feeForm.setFieldValue("source_file_type", resolveCaseFileTypeSelection("", fileTypeOptionsForCase(viewingCounselCase?.data.case_type)));
    const expenseScope = row.data.expense_scope || "律所";
    const expenseSubtype = normalizeFeeSubtypeForScope(expenseScope, row.data.expense_subtype || "官费");
    const feeTypeId = Number(row.data.fee_type_id) || initialFeeTypeId(feeTypeCatalog, expenseScope, "", expenseSubtype);
    const feeType = feeTypeSelection(feeTypeCatalog, feeTypeId);
    feeForm.setFieldsValue({ title: row.title, amount: row.data.amount, contract_record_id: Number(row.data.contract_id || row.data.contract_record_id) || undefined, expense_scope: expenseScope, fee_type_id: feeTypeId, expense_subtype: feeType?.name || expenseSubtype, fee_type: feeType?.base_fee_type || row.data.fee_type || "官方费用", handler: row.data.handler || row.owner, court: row.data.court || "", payee: row.data.payee || "", base_amount: row.data.base_amount ?? 0, reference_commission: row.data.reference_commission ?? 0, document_no: row.data.document_no || "", deadline: row.data.deadline ? dayjs(row.data.deadline) : undefined, description: row.description || "", commission_details: isInternalCaseFee(row) ? [] : Array.isArray(row.data.commission_details) ? row.data.commission_details : [] });
    setEditingFeeRow(row);
  };

  const openProgress = (row: CaseRow) => {
    if (!getCaseCapability(row).can_update_progress) return message.warning("当前账号没有案件进展维护权限");
    if ([...ARCHIVE_LOCKED_STATUSES, "已合并"].includes(row.status)) return message.warning("归档中、已归档或已合并案件不能维护案件进展");
    progressForm.resetFields();
    progressForm.setFieldsValue({
      ...row.data,
      judgment_date: row.data.judgment_date
        ? dayjs(row.data.judgment_date)
        : undefined,
    });
    setProgressEditing(row);
  };
  
  const openExecutionStatus = (rows: CaseRow[]) => {
    const selected = rows.filter(Boolean);
    if (!selected.length) return message.warning("请先选择执行案件");
    if (selected.some((row) => !getCaseCapability(row).can_update_progress)) return message.warning("当前账号没有案件进展维护权限");
    if (selected.some((row) => [...ARCHIVE_LOCKED_STATUSES, "已合并"].includes(row.status))) return message.warning("归档中、已归档或已合并案件不能修改执行状态");
    executionStatusForm.resetFields();
    executionStatusForm.setFieldsValue({ execution_status: selected[0].data.execution_status || CASE_EXECUTION_STATUSES[0], comment: "" });
    setExecutionStatusEditing(selected);
  };
  const openCompanyScheduleCourtInfo = (row: CaseRow, level: CompanyScheduleCourtLevel) => {
    if (!getCaseCapability(row).can_edit_court_info) return message.warning("当前账号没有法院信息维护权限");
    if ([...ARCHIVE_LOCKED_STATUSES,"已合并"].includes(row.status)) return message.warning("当前案件阶段不能修改法院信息");
    const courtPrefix = `${level}_court`;
    const data = row.data || {};
    const firstInstance = level === "first";
    const secondInstance = level === "second";
    const filingDate = data[`${courtPrefix}_filing_date`] || (firstInstance ? data.filing_date : "");
    const hearingDate = data[`${courtPrefix}_hearing_date`] || (firstInstance ? data.hearing_date || data.next_hearing_date : "");
    const judgmentDate = data[`${courtPrefix}_judgment_date`] || (firstInstance ? data.judgment_date : "");
    companyScheduleCourtInfoForm.resetFields();
    companyScheduleCourtInfoForm.setFieldsValue({
      court: data[`${courtPrefix}_name`] || (firstInstance ? data.first_instance_court || data.court : secondInstance ? data.second_instance_court : ""),
      courtroom: data[`${courtPrefix}_courtroom`] || (firstInstance ? data.courtroom : ""),
      judge: data[`${courtPrefix}_judge`] || (firstInstance ? data.judge : ""),
      clerk: data[`${courtPrefix}_clerk`] || (firstInstance ? data.clerk : ""),
      case_no: data[`${courtPrefix}_case_no`] || (firstInstance ? data.first_instance_case_no || data.court_case_no : secondInstance ? data.second_instance_case_no : ""),
      filing_date: filingDate ? dayjs(filingDate) : undefined,
      hearing_date: hearingDate ? dayjs(hearingDate) : undefined,
      judgment_date: judgmentDate ? dayjs(judgmentDate) : undefined,
    });
    setCompanyScheduleCourtInfo({ row, level });
  };
  const cancelCompanyScheduleCourtInfo = () => {
    setCompanyScheduleCourtInfo(null);
    companyScheduleCourtInfoForm.resetFields();
  };
  
  const openHearing = (row: CaseRow) => {
    if (!getCaseCapability(row).can_manage_hearing) return message.warning("当前账号没有开庭排期权限");
    setHearingOpen(true);
    hearingForm.setFieldsValue({ case_record_id: row.id, court: row.data.court || "", hearing_lawyer: row.data.hearing_lawyer || "" });
  };

  const caseColumns = createCaseColumns({
    get openCounselDetail() { return openCounselDetail; },
    get openRelatedContract() { return openRelatedContract; },
    get openRelatedCustomer() { return openRelatedCustomer; },
    get casePersonDisplayName() { return casePersonDisplayName; },
    get casePersonDisplayNames() { return casePersonDisplayNames; },
    get caseAssistantDisplayNames() { return caseAssistantDisplayNames; },
    get getCaseCapability() { return getCaseCapability; },
    get openAssign() { return openAssign; },
    get openProgress() { return openProgress; },
    get openCaseTasks() { return openCaseTasks; },
    get openCaseFee() { return openCaseFee; },
    get openHearing() { return openHearing; },
    get openArchive() { return openArchive; },
    get caseActionCapabilities() { return caseActionCapabilities; },
    get cases() { return cases; },
  });
  const hearingColumns = createHearingColumns({
    get openSpecialCaseDetail() { return openSpecialCaseDetail; },
    get openRelatedCustomer() { return openRelatedCustomer; },
    get casePersonDisplayName() { return casePersonDisplayName; },
    get profile() { return profile; },
    get deleteHearing() { return deleteHearing; },
  });
  const canReview = ["admin", "manager"].includes(profile.role || "");
  const archiveColumns = createArchiveColumns({
    get caseColumns() { return caseColumns; },
    get canReview() { return canReview; },
    get openArchiveReview() { return openArchiveReview; },
    get getCaseCapability() { return getCaseCapability; },
    get openArchive() { return openArchive; },
  });
  const archiveRows = cases.filter((row) =>
    ARCHIVE_REVIEW_STATUSES.includes(row.status)
    || ARCHIVE_FINAL_STATUSES.includes(row.status)
    || row.status === "亏损归档拒绝"
    || Boolean(row.data.archive_reject_reason),
  );
  const scopedCases =
    initialView.startsWith("case-mine")
      ? cases.filter((r) =>
          [profile.username, profile.display_name].includes(r.owner),
        )
      : initialView.startsWith("case-dept")
        ? cases.filter((r) => r.department === profile.department)
        : cases;
  const shownSummary = ["case-mine", "case-dept"].includes(initialView)
    ? {
        total: scopedCases.length,
        pending_assignment: scopedCases.filter((x) => x.status === "新案待分配")
          .length,
        in_progress: scopedCases.filter(
          (x) => !["新案待分配", "已归档"].includes(x.status),
        ).length,
        execution: scopedCases.filter((x) => x.status === "执行").length,
        archived: scopedCases.filter((x) => x.status === "已归档").length,
      }
    : summary;
  const visibleCases =
    tab === "execution"
      ? scopedCases.filter((r) => r.status === "执行")
      : showArchived
        ? scopedCases
        : scopedCases.filter((r) => r.status !== "已归档");
  const originalListMode =
    tab === "cases" &&
    ["case-mine", "case-dept", "case-company"].some((prefix) =>
      initialView.startsWith(prefix),
    );
  const counselListMode = originalListMode && initialView.includes("counsel");
  const originalCases = ordinaryCases;
  const selectedBatchCases = useMemo(
    () => (counselListMode ? counselCases : originalCases).filter((row) => selectedCaseKeySet.has(String(row.id))),
    [counselCases, counselListMode, originalCases, selectedCaseKeySet],
  );
  const batchFeeSourceFileTypeOptions = useMemo(() => {
    const caseTypes = [...new Set(selectedBatchCases.map((row) => String(row.data.case_type || "")))];
    if (!caseTypes.length) return [];
    const optionsByType = caseTypes.map((caseType) =>
      filterCaseFileTypesForCaseType(caseType, caseFileTypeCatalog, caseRelations?.caseTypeFileTypes),
    );
    const first = optionsByType[0] || [];
    return buildCaseFileTypeTreeOptions(first.filter((option) =>
      optionsByType.every((options) => hasCaseFileTypeOption(option.value, options)),
    ));
  }, [caseFileTypeCatalog, caseRelations, selectedBatchCases]);
  const selectedCase = (counselListMode?counselCases:originalCases).find((row) => selectedCaseKeySet.has(String(row.id)));
  const selectedCaseCapability = getCaseCapability(selectedCase);
  const canDeleteSelectedCompanyCase = isCompanyCaseListRoute(initialView)
    && ["admin", "manager"].includes(profile.role || "")
    && selectedCaseCapability.can_delete_case;
  const selectedCases = (counselListMode ? counselCases : originalCases).filter((row) => selectedCaseKeySet.has(String(row.id)));
  const legacyCaseListOperationState = getLegacyCaseListOperationState({
    role: profile.role || "",
    status: selectedCase?.status || "",
    selectedCount: selectedCaseKeys.length,
    isCompanySchedule: initialView === "case-company-schedule",
  });
  const canCreateSelectedCaseFees = selectedCases.length > 0 && selectedCases.every((row) => getCaseCapability(row).can_create_finance);
  const isArchiveManager = ["admin", "manager"].includes(profile.role || "");

  const exportSelectedCasesExcel = (selectedOnly: boolean) => void downloadCaseExport(
    "/cases/export/excel",
    selectedOnly ? "普通案件-选中.xls" : "普通案件-当前查询.xls",
    selectedOnly ? selectedCaseKeys : originalCases.map((row) => row.id),
    selectedOnly ? "请选择需要导出的案件" : "当前查询没有可导出的案件",
  );
  const exportArchiveManifest = (selectedOnly: boolean) => {
    const currentArchiveIds = originalArchiveRows.map((row) => row.id);
    const currentArchiveIdSet = new Set(currentArchiveIds.map(String));
    const ids = selectedOnly
      ? selectedCaseKeys.filter((key) => currentArchiveIdSet.has(String(key)))
      : currentArchiveIds;
    void downloadCaseExport(
      "/cases/export/archive-manifest",
      selectedOnly ? "案件归档清单-选中.xls" : "案件归档清单-当前筛选.xls",
      ids,
      selectedOnly ? "请选择需要导出归档清单的案件" : "当前筛选没有可导出的归档案件",
    );
  };
  const exportCaseQrWord = () => void downloadCaseExport(
    "/cases/export/qr-word", "案件二维码清单.docx", selectedCaseKeys, "请选择需要生成二维码清单的案件",
  );

  const exportStageStatistics = () => {
    const escape = (value: unknown) => `"${String(value ?? "").replace(/"/g, '""')}"`;
    const lines = [
      ["姓名", "日期", "立案进度", "退费进度", "执行进度", "线索进度"],
      ...phaseRows.map((row) => [row.name, row.date, row.filing, row.refund, row.execution, row.clue]),
    ].map((row) => row.map(escape).join(","));
    const blob = new Blob([`\ufeff${lines.join("\r\n")}`], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob), link = document.createElement("a");
    link.href = url; link.download = "案件阶段统计.csv"; link.click(); URL.revokeObjectURL(url);
  };
  
  const openCaseFileUpload = () => {
    if (!selectedCase) return message.warning("请先选择案件再上传文件");
    const options = fileTypeOptionsForCase(selectedCase.data.case_type);
    if (!options.length) return message.warning("当前案件类型未配置可上传的材料类型，请先在系统参数中维护关联");
    setCaseUploadCategory((current) => resolveCaseFileTypeSelection(current, options));
    setCaseUploadOpen(true);
  };
  const confirmCaseFileUpload = () => {
    setCaseUploadOpen(false);
    window.setTimeout(() => caseUploadRef.current?.click(), 0);
  };

  const renderCompanyCriminalColumn = (key:string,row:CaseRow) => {
    switch (key) {
      case "serial_no": return <Button type="link" className="case-cell-link" onClick={()=>void openCounselDetail(row)}>{row.serial_no}</Button>;
      case "charge": return row.data.cause_or_charge||"";
      case "prosecutor": return row.data.prosecutor||row.data.first_procuratorate_name||row.data.procuratorate||"";
      case "plaintiff": return row.data.plaintiff||row.customer||"";
      case "defendant": return Array.isArray(row.data.defendants)?row.data.defendants.join(","):row.data.defendants||row.data.opponent||"";
      case "status": return row.status;
      case "court": return row.data.court||row.data.first_court_name||"";
      case "hearing_at": return row.data.hearing_date||row.data.first_court_hearing_date||"";
      case "handling_lawyer": return casePersonDisplayNames(row.data.handling_lawyers);
      case "assistant": return caseAssistantDisplayNames(row.data);
      case "source_person": return casePersonDisplayName(row.data.source_person||row.data.business_owner||row.owner, row.data.source_person_display_name||row.data.business_owner_display_name||row.owner_display_name);
      case "remaining_days": return row.data.remaining_days??0;
      default: return "";
    }
  };
  const companyCriminalCaseColumns = getCompanyCriminalColumnSchema().map(({key,title,width})=>({title,key,width,sorter:key==="serial_no"||key==="hearing_at",render:(_:unknown,row:CaseRow)=>renderCompanyCriminalColumn(key,row)}));
  const companyArbitrationCaseColumns = getCompanyArbitrationColumnSchema().map(({key,title,width})=>({title,key,width,sorter:key==="serial_no"||key==="hearing_at",render:(_:unknown,row:CaseRow)=>renderCompanyCriminalColumn(key,row)}));
  const groupedOriginalCaseColumns = createGroupedOriginalCaseColumns({
    get openCounselDetail() { return openCounselDetail; },
    get casePersonDisplayNames() { return casePersonDisplayNames; },
    get caseAssistantDisplayNames() { return caseAssistantDisplayNames; },
    get legacyCaseParticipantDisplayNames() { return legacyCaseParticipantDisplayNames; },
    get openCaseLogViewer() { return openCaseLogViewer; },
    get openCaseTasks() { return openCaseTasks; },
    get casePersonDisplayName() { return casePersonDisplayName; },
  });
  const originalCaseColumns=shouldUseCompanyArbitrationColumns(initialView)?companyArbitrationCaseColumns:groupedOriginalCaseColumns;
  const counselCaseColumns = [
    {title:"案件编号",dataIndex:"serial_no",width:170,sorter:true,render:(value:string,row:CaseRow)=><Button type="link" className="case-cell-link" onClick={()=>void openCounselDetail(row)}>{value}</Button>},
    {title:"顾问类型",key:"counsel_type",width:150,render:(_:unknown,row:CaseRow)=>row.data.counsel_type||"—"},
    {title:"客户",dataIndex:"customer",width:230,ellipsis:true,render:(value:string,row:CaseRow)=>value?<Button type="link" className="case-cell-link" onClick={()=>openRelatedCustomer({id:Number(row.data.customer_id)||undefined,serial_no:row.data.customer_no,title:value})}>{value}</Button>:"—"},
    {title:"顾问期限",key:"counsel_range",width:225,render:(_:unknown,row:CaseRow)=>row.data.counsel_start&&row.data.counsel_end?`${row.data.counsel_start} 至 ${row.data.counsel_end}`:"—"},
    {title:"经办律师",key:"handling_lawyers",width:150,render:(_:unknown,row:CaseRow)=>casePersonDisplayNames(row.data.handling_lawyers)},
    {title:"律师助理",key:"assistant",width:120,render:(_:unknown,row:CaseRow)=>caseAssistantDisplayNames(row.data)},
    {title:"案源人",key:"source_person",width:120,render:(_:unknown,row:CaseRow)=>casePersonDisplayName(row.data.source_person||row.data.business_owner||row.owner,row.data.source_person_display_name||row.data.business_owner_display_name||row.owner_display_name)},
    {title:"剩余时间",key:"remaining_days",width:105,render:(_:unknown,row:CaseRow)=>{const end=dayjs(String(row.data.counsel_end||""));const days=end.isValid()?Math.max(0,end.startOf("day").diff(dayjs().startOf("day"),"day")):0;return <span style={{color:days<10?"red":"green"}}>{days} 天</span>;}},
    {title:"操作",key:"actions",fixed:"right" as const,width:150,render:(_:unknown,row:CaseRow)=><Space size={0}><Button type="link" onClick={()=>void openCounselDetail(row)}>查看</Button>{getCaseCapability(row).can_edit_basic&&<Button type="link" disabled={ARCHIVE_LOCKED_STATUSES.includes(row.status)} onClick={()=>openCounselEdit(row)}>编辑</Button>}</Space>},
  ];
  const criminalPhaseItems=[{label:"待分配",value:"新案待分配"},{label:"公安侦查",value:"公安侦查"},{label:"批捕",value:"批捕"},{label:"检察院审查起诉",value:"检察院审查起诉"},{label:"一审阶段",value:"一审阶段"},{label:"二审阶段",value:"二审阶段"},{label:"再审阶段",value:"再审阶段"},{label:"归档阶段",value:"归档阶段"}];
  const phaseDefinitions=getCasePhaseDefinitions(initialView,CASE_PHASE_ROOT_LABELS.map(value=>({label:value,value})),criminalPhaseItems);
  const phaseItems = counselListMode
    ? buildCasePhaseItems(scopedCases,initialView,phaseDefinitions)
    : buildCasePhaseItemsFromCounts(ordinaryPhaseCounts,phaseDefinitions);
  const phaseTreeItems = buildLegacyCasePhaseTree(phaseItems, phaseCatalog, ordinaryPhaseCounts) as CasePhaseTreeItem[];
  const originalArchiveMode=initialView.startsWith("case-archive-");
  const archiveDone=initialView.includes("done"), archiveRefused=initialView.includes("refused");
  const originalArchiveRows=cases.filter(row=>archiveDone?ARCHIVE_FINAL_STATUSES.includes(row.status):archiveRefused?row.status==="亏损归档拒绝"||Boolean(row.data.archive_reject_reason):ARCHIVE_REVIEW_STATUSES.includes(row.status)).filter(row=>{
    const match=(value:unknown,key:string)=>!caseQuery[key]||String(value||"").toLowerCase().includes(String(caseQuery[key]).toLowerCase());
    return match(row.data.plaintiff||row.customer,"plaintiff")&&match(row.serial_no,"serial_no")&&match(row.data.assistant,"assistant")&&match(row.data.court,"court")&&match(row.data.opponent,"defendant")&&match(row.data.notary_no,"notary_no")&&match(row.data.hearing_lawyer,"hearing_lawyer")&&match((row.data.handling_lawyers||[]).join(","),"handling_lawyer")&&match(row.data.archive_submitter||row.owner,"submitter");
  });
  const selectedArchiveCase = originalArchiveRows.find((row) => selectedCaseKeySet.has(String(row.id)));
  const selectedArchiveCaseCapability = getCaseCapability(selectedArchiveCase);
  const originalArchiveColumns:any[]=createOriginalArchiveColumns({
    get casePersonDisplayName() { return casePersonDisplayName; },
    get archiveDone() { return archiveDone; },
    get archiveRefused() { return archiveRefused; },
    get openCounselDetail() { return openCounselDetail; },
    get casePersonDisplayNames() { return casePersonDisplayNames; },
    get caseAssistantDisplayNames() { return caseAssistantDisplayNames; },
  });
  // All data columns below declare their widths. Keep the selection column inside
  // the horizontal viewport so the fixed right action column never overlays data.
  const companyArbitrationCaseTableScrollX=1610;
  const originalCaseTableScrollX=shouldUseCompanyArbitrationColumns(initialView)?companyArbitrationCaseTableScrollX:undefined;
  const companyCriminalCaseTableScrollX=1610;
  const counselCaseTableScrollX=1460;
  const archiveCaseTableScrollX=archiveDone||archiveRefused?1700:1600;
  const specialMode=initialView.endsWith("-schedule")?"schedule":initialView.endsWith("-execution")?"execution":initialView.endsWith("-unclaimed")?"unclaimed":initialView.endsWith("-stage")?"stage":initialView.endsWith("-no-refund")?"refund":initialView==="case-files-receipt"?"receipt":initialView==="case-files-invoice"?"invoice":"";
  const specialTitle:Record<string,string>={schedule:"案件列表",execution:"案件列表",unclaimed:"内部提成-待结算",stage:"案件阶段统计",refund:"退费查询",receipt:"票据上传",invoice:"发票文件导入"};
  const specialFilters:Record<string,[string,string,string?,string?][]>= {
    schedule:shouldUseCompanyScheduleQueryFields(initialView)?getCompanyScheduleQueryFields():[["plaintiff","原告/申请人/公诉机关"],["serial_no","案号"],["handling_lawyer","经办律师"],["keyword","关键字"],["defendant","被告/被申请人"],["notary_no","公证书号"],["hearing_lawyer","开庭律师"],["court","法院/机构"],["third_party","第三人/受害人"],["investigator","调查员"],["assistant","律师助理"],["document_name","文档名称"],["source_range","案源时间","date"],["hearing_range","开庭时间","date"],["case_type","案件类型","select"],["log_content","日志内容"]],
    execution:[["plaintiff","原告"],["serial_no","案件编号"],["evidence_org","取证机构"],["keyword","关键字"],["defendant","被告"],["handling_lawyer","经办律师"],["notary_no","公证书号"],["execution_progress","执行进度"],["hearing_lawyer","开庭律师"],["assistant","律师助理"],["investigator","调查员"],["court","法院名称"],["source_range","案源时间","date"],["channel","侵权渠道"],["warehouse","仓库"],["document_name","文档名称"],["hearing_range","开庭时间","date"],["area","侵权区域"],["location","库位"],["log_content","日志内容"]],
    unclaimed:[["customer","客户名称"],["serial_no","案件编号"],["court_case_no","法院案号"],["notary_no","公证书号"],["hearing_lawyer","开庭律师"],["assistant","律师助理"],["status","案件阶段"],["investigator","调查员"],["source_person","案源人"]],
    refund:[["serial_no","案件编号"],["court_case_no","法院案号"],["court","法院名称"],["payment_range","付款时间","date"],["customer","客户名称"],["payee","收款单位"],["refund_status","退费状态"],["refund_amount","退费金额"],["hearing_lawyer","开庭律师"],["assistant","律师助理"],["status","案件阶段"],["fee_type","费用类型"]],
    receipt:[["serial_no","案件编号"],["customer","客户名称"],["contract_no","合同编号"],["fee_group","费用大类"],["case_type","案件类型"],["status","案件阶段"],["fee_type","费用类型"],["receipt_status","票据状态"],["notary_no","公证书号"],["package_no","打包号"]],
  };
  const caseMatches=(row:CaseRow)=>Object.entries(caseQuery).every(([key,value])=>{if(!value||Array.isArray(value))return true;const map:Record<string,unknown>={serial_no:row.serial_no,customer:row.customer,status:row.status,plaintiff:row.data.plaintiff||row.customer,defendant:row.data.opponent,keyword:`${row.serial_no}${row.title}${row.customer}${row.data.opponent||""}`,handling_lawyer:(row.data.handling_lawyers||[]).join(","),...row.data};return String(map[key]||"").toLowerCase().includes(String(value).toLowerCase())});
  const specialCases=(specialMode==="execution"?pendingExecutionCases:scopedCases).filter(caseMatches);
  const phaseRows:any[]=Object.values(specialCases.reduce((acc:Record<string,any>,row)=>{const name=row.owner||"未分配";if(!acc[name])acc[name]={id:name,name,date:dayjs().format("YYYY-MM-DD"),filing:0,refund:0,execution:0,clue:0};if(String(row.status).includes("立案"))acc[name].filing++;if(String(row.status).includes("退费"))acc[name].refund++;if(String(row.status).includes("执行"))acc[name].execution++;if(row.data.investigation_clue)acc[name].clue++;return acc},{}));
  const relatedCase=(id:number)=>cases.find(row=>row.id===id);
  const relatedFinance=(id:number)=>financeRows.find(row=>row.id===id);
  const invoiceCase=(row:AttachmentRow)=>{const finance=relatedFinance(row.record_id||0);return relatedCase(row.record_id||0)||cases.find(item=>item.serial_no===finance?.data?.case_no)};
  const scheduleRows=hearings.filter(row=>{const c=relatedCase(row.case_record_id);return c?caseMatches(c):true}).map(row=>({...row,case:relatedCase(row.case_record_id)}));
  const receiptRows=specialCases;
  const invoiceRows=attachments.filter(row=>row.category.includes("发票")||row.category.includes("票据"));
  const specialRows:any[]=specialMode==="schedule"?scheduleRows:specialMode==="execution"?specialCases:specialMode==="unclaimed"?specialCases.filter(row=>!row.data.commission_applied):specialMode==="stage"?phaseRows:specialMode==="refund"?financeRows.filter(row=>String(row.data.fee_type||row.title).includes("退费")&&caseMatches(row)):specialMode==="receipt"?receiptRows:specialMode==="invoice"?invoiceRows:[];
  const selectedSpecialRow:any=specialRows.find(row=>selectedCaseKeySet.has(String(row.id)));
  
  const markCommissionPaid=()=>{
    if(!selectedSpecialRow)return message.warning("请先选择一条到账案件");
    Modal.confirm({title:"标识提成已发",content:`确认将 ${selectedSpecialRow.serial_no} 标识为提成已发？`,onOk:async()=>{
      await api.patch(`/records/${selectedSpecialRow.id}`,{data:{...selectedSpecialRow.data,commission_applied:true,commission_paid_at:dayjs().format("YYYY-MM-DD")}});
      message.success("已标识提成已发");setSelectedCaseKeys([]);await load();
    }});
  };
  const operateRefund=()=>{
    if(!selectedSpecialRow)return message.warning("请先选择一条退费记录");
    if(["草稿","已驳回"].includes(selectedSpecialRow.status))return Modal.confirm({title:"提交退费申请",content:`确认提交 ${selectedSpecialRow.serial_no}？`,onOk:async()=>{await api.post(`/finance/refunds/${selectedSpecialRow.id}/submit`,{comment:"案件退费查询提交"});message.success("退费申请已提交");void load()}});
    if(selectedSpecialRow.status==="待审批")return Modal.confirm({title:"审核退费申请",content:`确认通过 ${selectedSpecialRow.serial_no}？`,onOk:async()=>{await api.post(`/finance/refunds/${selectedSpecialRow.id}/review`,{approved:true,comment:"案件退费查询审核通过"});message.success("退费申请已审核");void load()}});
    if(selectedSpecialRow.status==="退款办理中"){
      refundCompleteForm.setFieldsValue({actual_date:dayjs(),voucher_no:"",comment:""});
      setRefundCompleting(selectedSpecialRow);
      return;
    }
    message.info(`当前退费状态：${selectedSpecialRow.status}，无需重复办理`);
  };
  
  const specialColumns:Record<string,any[]>=createSpecialColumns({
    get openSpecialCaseDetail() { return openSpecialCaseDetail; },
    get casePersonDisplayName() { return casePersonDisplayName; },
    get casePersonDisplayNames() { return casePersonDisplayNames; },
    get caseAssistantDisplayNames() { return caseAssistantDisplayNames; },
    get getCaseCapability() { return getCaseCapability; },
    get openProgress() { return openProgress; },
    get openExecutionStatus() { return openExecutionStatus; },
    get openCaseLogViewer() { return openCaseLogViewer; },
    get openCaseListLogCreator() { return openCaseListLogCreator; },
    get openRelatedCustomer() { return openRelatedCustomer; },
    get invoiceCase() { return invoiceCase; },
    get relatedFinance() { return relatedFinance; },
  });
  const customCaseDocumentFolders=getCustomCaseDocumentFolders(viewingCounselCase);
  const counselCaseFileTypeOptions = fileTypeOptionsForCase(viewingCounselCase?.data.case_type);
  const fixedFormalCaseDocumentOptions=AGENT_CASE_DOCUMENT_FOLDERS.map(name=>({value:name,label:name}));
  const counselUploadCategoryOptions=[
    ...fixedFormalCaseDocumentOptions,
    ...counselCaseFileTypeOptions.filter(option=>!AGENT_CASE_DOCUMENT_FOLDERS.includes(option.value)),
    ...customCaseDocumentFolders.filter(name=>!AGENT_CASE_DOCUMENT_FOLDERS.includes(name)&&!hasCaseFileTypeOption(name,counselCaseFileTypeOptions)).map(name=>({value:name,label:name})),
    {value:"普通附件",label:"普通附件"},
  ];
  const activeCounselUploadCategoryOptions=activeCounselDocCategory==="AI空间"?[{value:"AI空间",label:"AI空间（草稿）"}]:counselUploadCategoryOptions;
  const caseDocumentTreeGroup=counselDocumentFolderTree.find(option=>option.value==="案件文档全部");
  const visibleFormalCaseDocumentFolders=Array.from(new Set([
    ...AGENT_CASE_DOCUMENT_FOLDERS,
    ...(caseDocumentTreeGroup?.options||[]).map(option=>option.value).filter(name=>name&&name!=="普通附件"),
    ...customCaseDocumentFolders,
  ]));
  const counselMoveCategoryOptions = getCaseDocumentMoveCategoryOptions(customCaseDocumentFolders);
  const counselDocTree:Array<{label:string;category:string;type:string;parent?:string;custom?:boolean}>=[
    {label:"AI空间",category:"AI空间",type:"folder"},
    {label:"客户文档",category:"客户文档",type:"folder"},
    {label:"合同文档",category:"合同文档",type:"folder"},
    {label:"调查文档",category:"调查文档全部",type:"group"},
    {label:"鉴别资料",category:"鉴别资料",type:"child",parent:"调查文档全部"},
    {label:"调查文档",category:"调查文档",type:"child",parent:"调查文档全部"},
    {label:"取证文档",category:"取证文档",type:"child",parent:"调查文档全部"},
    {label:"案件文档",category:"案件文档全部",type:"group"},
    ...visibleFormalCaseDocumentFolders.map(label=>({
      label,category:label,type:"child",parent:"案件文档全部",
      custom:customCaseDocumentFolders.includes(label),
    })),
  ].filter(item=>!item.parent||expandedCounselDocGroups[item.parent]);
  const counselDocCategoryGroups:Record<string,string[]>={
    调查文档全部:["调查文档","鉴别资料","取证文档"],
  };
  const activeCounselDocCategories=counselDocCategoryGroups[activeCounselDocCategory]||[activeCounselDocCategory];
  const nonCaseDocumentCategories=["AI空间","客户文档","合同文档",...counselDocCategoryGroups.调查文档全部];
  const filteredCounselDetailAttachments=activeCounselDocCategory
    ? activeCounselDocCategory==="客户文档"
      ? counselDetailCustomerAttachments
      : activeCounselDocCategory==="合同文档"
        ? counselDetailContractAttachments
        : counselDetailAttachments.filter(row=>activeCounselDocCategory==="案件文档全部"
          ? !nonCaseDocumentCategories.includes(String(row.category||""))
          : activeCounselDocCategories.some(category=>String(row.category||"")===category))
    : counselDetailAttachments;
  const isRelatedDocumentFolder=activeCounselDocCategory==="客户文档"||activeCounselDocCategory==="合同文档";
  const isAiSpaceFolder=activeCounselDocCategory==="AI空间";
  const activeCounselDocLabel=counselDocTree.find(item=>item.category===activeCounselDocCategory)?.label||activeCounselDocCategory;
  const selectedCounselDocumentAttachments=selectedCounselAttachments();
  const canApplySealToSelectedCounselDocument=selectedCounselDocumentAttachments.length===1&&canApplySealToCounselAttachment(selectedCounselDocumentAttachments[0]);
  const firmFeeRows=counselDetailFinance.filter(row=>row.data.expense_scope!=="平台"&&row.data.expense_scope!=="内部"&&!String(row.data.fee_type||"").includes("内部"));
  const platformFeeRows=counselDetailFinance.filter(row=>row.data.expense_scope==="平台");
  const internalFeeRows=counselDetailFinance.filter(row=>row.data.expense_scope==="内部"||String(row.data.fee_type||"").includes("内部"));
  const isInternalCaseFee=(row:CaseRow)=>row.data.expense_scope==="内部"||String(row.data.fee_type||"").includes("内部");
  const selectedFirmFee=firmFeeRows.find(row=>selectedFirmFeeKeys.includes(row.id));
  const selectedPlatformFee=platformFeeRows.find(row=>selectedPlatformFeeKeys.includes(row.id));
  const selectedInternalFee=internalFeeRows.find(row=>selectedInternalFeeKeys.includes(row.id));
  const editingInternalFee=Boolean(editingFeeRow&&isInternalCaseFee(editingFeeRow));
  const openCaseFeeBySubtype=(scope:"律所"|"平台"|"内部",subtype:string)=>{
    if(!viewingCounselCase)return;
    openCaseFee(viewingCounselCase,scope,subtype);
  };
  const renderCaseFeeEmptyState=(scope:"律所"|"平台")=><div className="case-fee-empty-state">
    <InfoCircleOutlined aria-hidden="true"/>
    <span>没有查询到费用信息。</span>
    {counselDetailCapabilities.can_create_finance&&<Space size={0} wrap>
      {["官费","第三方费用","代理费","其他费用"].map(subtype=><Button key={subtype} type="link" onClick={()=>openCaseFeeBySubtype(scope,subtype)}>新增{subtype}</Button>)}
    </Space>}
  </div>;
  const requireSingleFee=(keys:Key[],row:CaseRow|undefined,action:string)=>{
    if(keys.length!==1||!row){message.warning(`请先选择一条费用记录再${action}`);return false;}
    return true;
  };
  const openInformDateBatchUpdate=(keys:Key[])=>{
    if(!keys.length){message.warning("请先选择需要修改通知日期的费用记录");return;}
    informDateForm.resetFields();
    setInformDateFeeKeys([...keys]);
  };

  const openFeeInformCreator = (row: CaseRow) => {
    feeInformForm.resetFields();
    feeInformForm.setFieldsValue({ inform_date: dayjs(), remark: "" });
    setFeeInformTarget(row);
    setFeeInformRecord(null);
  };

  const externalCaseFeeColumns=createExternalCaseFeeColumns({
    get viewingCounselCase() { return viewingCounselCase; },
    get openRelatedContract() { return openRelatedContract; },
    get casePersonDisplayName() { return casePersonDisplayName; },
    get openRelatedIncomingPayment() { return openRelatedIncomingPayment; },
    get openRelatedInvoice() { return openRelatedInvoice; },
  });
  const closeCaseCommission = () => {
    setCaseCommissionPreview(null);
    setCaseCommissionRows([]);
    setCaseCommissionResult(null);
  };
  
  const cloneCaseCommissionRow = (source: CaseCommissionPreviewRow) => {
    setCaseCommissionRows((rows) => [
      ...rows,
      { ...source, client_key: `${source.preview_key}:${Date.now()}:${rows.length}`, remark: "" },
    ]);
  };
  const updateCaseCommissionRow = (clientKey: string, patch: Partial<CaseCommissionPreviewRow>) => {
    setCaseCommissionRows((rows) => rows.map((row) => row.client_key === clientKey ? { ...row, ...patch } : row));
  };
  
  const handleInternalFeeAction=(key:string)=>{
    if(key==="create")return openCaseFeeBySubtype("内部","内部费用");
    if(!requireSingleFee(selectedInternalFeeKeys,selectedInternalFee,key==="payment"?"申请付款":key==="edit"?"修改":"删除"))return;
    if(key==="payment")return void previewInternalPayment(selectedInternalFee!);
    if(key==="edit")return editCaseFee(selectedInternalFee!);
    deleteCaseFee(selectedInternalFee!);
  };
  const primaryOperationLabels = getLegacyCaseDetailPrimaryOperationLabels();
  const moreOperationLabels = getLegacyCaseDetailMoreOperationLabels();
  const detailEditLocked = Boolean(viewingCounselCase && [...ARCHIVE_LOCKED_STATUSES, "已合并"].includes(viewingCounselCase.status));
  const openLegacyBasicInfo = () => {
    if (!viewingCounselCase) return;
    if (viewingCounselCase.data.case_type === "法律顾问") return openCounselEdit(viewingCounselCase);
    if (viewingCounselCase.data.case_type === "仲裁") return openArbitrationBasicEdit(viewingCounselCase);
    if (isNormalEditableCase(viewingCounselCase)) return openNormalCaseEdit(viewingCounselCase);
    message.warning("当前案件类型暂不支持修改基本信息");
  };
  const openLegacyNotaryInfo = () => {
    if (!viewingCounselCase) return;
    notaryInfoForm.setFieldsValue({
      notary_nos: viewingCounselCase.data.notary_nos || viewingCounselCase.data.notary_no || "",
      warehouse_location_ids: resolveCaseWarehouseLocationIds(viewingCounselCase.data, warehouseLocationOptions),
      comment: "",
    });
    setNotaryInfoCase(viewingCounselCase);
  };
  const openLegacySettlementAmount = () => {
    if (!viewingCounselCase) return;
    settlementAmountForm.setFieldsValue({
      litigation_amount: viewingCounselCase.data.litigation_amount ?? 0,
      settlement_amount: viewingCounselCase.data.settlement_amount ?? 0,
      comment: "",
    });
    setSettlementAmountCase(viewingCounselCase);
  };
  const confirmLegacyDuplicateCase = () => {
    if (!viewingCounselCase) return;
    Modal.confirm({
      title: `复制案件：${viewingCounselCase.serial_no}`,
      content: "将只复制案件基础信息并生成新案号；任务、附件、费用、提醒、排期和历史记录不会复制。",
      okText: "确认复制",
      cancelText: "取消",
      onOk: () => duplicateCase(viewingCounselCase),
    });
  };
  const caseDetailMoreActionButtons = viewingCounselCase ? <>
    {counselDetailCapabilities.can_generate_document && !detailEditLocked && <>
      <Button type="text" block onClick={() => void generateCaseDocument("authorization-letter")}>{moreOperationLabels[0]}</Button>
      <Button type="text" block onClick={() => void generateCaseDocument("first-instance-appellant-lawyer-letter")}>{moreOperationLabels[1]}</Button>
      <Button type="text" block onClick={() => void generateCaseDocument("first-instance-appellee-lawyer-letter")}>{moreOperationLabels[2]}</Button>
      <Button type="text" block onClick={() => void generateCaseDocument("second-instance-appellant-lawyer-letter")}>{moreOperationLabels[3]}</Button>
      <Button type="text" block onClick={() => void generateCaseDocument("second-instance-appellee-lawyer-letter")}>{moreOperationLabels[4]}</Button>
      <Button type="text" block onClick={() => void generateCaseDocument("execution-lawyer-letter")}>{moreOperationLabels[5]}</Button>
      <Button type="text" block onClick={() => void generateCaseDocument("identity-certificate")}>{moreOperationLabels[6]}</Button>
    </>}
    {counselDetailCapabilities.can_merge_case && !detailEditLocked && <Button type="text" block onClick={() => { mergeCaseForm.resetFields(); setMergingCase(viewingCounselCase); }}>{moreOperationLabels[7]}</Button>}
    {counselDetailCapabilities.can_duplicate_case && <Button type="text" block onClick={confirmLegacyDuplicateCase}>{moreOperationLabels[8]}</Button>}
  </> : null;
  const caseDetailPrimaryActionButtons = viewingCounselCase ? <div className="case-detail-legacy-operation-menu">
    {counselDetailCapabilities.can_edit_basic && <Button type="text" block disabled={detailEditLocked} onClick={openLegacyBasicInfo}>{primaryOperationLabels[0]}</Button>}
    {counselDetailCapabilities.can_change_phase && <Button type="text" block disabled={detailEditLocked} onClick={() => void openPhaseChange([viewingCounselCase])}>{primaryOperationLabels[1]}</Button>}
    {counselDetailCapabilities.can_edit_basic && isCivilCaseType(viewingCounselCase.data.case_type) && <Button type="text" block disabled={detailEditLocked} onClick={openLegacyNotaryInfo}>{primaryOperationLabels[2]}</Button>}
    {counselDetailCapabilities.can_edit_hearing_lawyer && <Button type="text" block disabled={detailEditLocked} onClick={() => openCaseHearingLawyer(viewingCounselCase)}>{primaryOperationLabels[3]}</Button>}
    {counselDetailCapabilities.can_edit_basic && <Button type="text" block disabled={detailEditLocked} onClick={() => openCaseLitigants(viewingCounselCase)}>{primaryOperationLabels[4]}</Button>}
    {counselDetailCapabilities.can_edit_basic && viewingCounselCase.data.case_type === "刑事案件" && <Button type="text" block disabled={detailEditLocked} onClick={() => openCriminalMaintenance(viewingCounselCase, "public-security")}>修改公安信息</Button>}
    {counselDetailCapabilities.can_edit_basic && viewingCounselCase.data.case_type === "刑事案件" && <Button type="text" block disabled={detailEditLocked} onClick={() => openCriminalMaintenance(viewingCounselCase, "courts")}>修改法院信息</Button>}
    {counselDetailCapabilities.can_edit_court_info && <div className="case-detail-legacy-submenu">
      <Button type="text" block disabled={detailEditLocked} className="case-detail-legacy-submenu-trigger">{viewingCounselCase.data.case_type === "仲裁" ? "修改仲裁信息" : primaryOperationLabels[5]}</Button>
      <div className="case-detail-legacy-submenu-panel" data-testid="case-detail-court-submenu">
        {getCompanyScheduleCourtLevels().map(([key, label]) => <Button key={key} type="text" block onClick={() => openCompanyScheduleCourtInfo(viewingCounselCase, key)}>{label}</Button>)}
      </div>
    </div>}
    {counselDetailCapabilities.can_edit_basic && viewingCounselCase.data.case_type === "刑事案件" && <Button type="text" block disabled={detailEditLocked} onClick={() => openCriminalMaintenance(viewingCounselCase, "procuratorates")}>修改检察院信息</Button>}
    {counselDetailCapabilities.can_edit_basic && (isNormalCaseBasicType(viewingCounselCase.data.case_type) || viewingCounselCase.data.case_type === "仲裁") && <Button type="text" block disabled={detailEditLocked} onClick={openLegacySettlementAmount}>{primaryOperationLabels[6]}</Button>}
    {counselDetailCapabilities.can_archive && <div className="case-detail-legacy-submenu">
      <Button type="text" block disabled={ARCHIVE_LOCKED_STATUSES.includes(viewingCounselCase.status)} className="case-detail-legacy-submenu-trigger">{primaryOperationLabels[7]}</Button>
      <div className="case-detail-legacy-submenu-panel" data-testid="case-detail-archive-submenu">
        <Button type="text" block disabled={ARCHIVE_LOCKED_STATUSES.includes(viewingCounselCase.status)} onClick={() => void openArchive(viewingCounselCase, "normal")}>正常归档</Button>
        <Button type="text" block disabled={ARCHIVE_LOCKED_STATUSES.includes(viewingCounselCase.status)} onClick={() => void openArchive(viewingCounselCase, "deficit")}>亏损归档</Button>
      </div>
    </div>}
    {(counselDetailCapabilities.can_edit_basic || counselDetailCapabilities.can_merge_case || counselDetailCapabilities.can_duplicate_case) && <div className="case-detail-legacy-submenu case-detail-legacy-more-submenu" data-testid="case-detail-more-operation">
      <Button type="text" block className="case-detail-legacy-submenu-trigger">{primaryOperationLabels[8]}</Button>
      <div className="case-detail-legacy-submenu-panel" data-testid="case-detail-more-operation-panel">{caseDetailMoreActionButtons}</div>
    </div>}
  </div> : null;
  const companyScheduleCourtLevelLabel = getCompanyScheduleCourtLevels().find(([key]) => key === companyScheduleCourtInfo?.level)?.[1] || "";
  return (
    <div className={`case-center-page ${isCaseDetailView ? "case-detail-route" : ""}`}>
      {isCaseDetailView && !viewingCounselCase && <div className="case-detail-route-loading">正在加载案件详情...</div>}
      {isCreateView && (
        <CaseCreateWizard
          createFlowToken={createFlowToken}
          createStep={createStep}
          setCreateStep={setCreateStep}
          createForm={createForm}
          createSubmitting={createSubmitting}
          isCounselCreate={isCounselCreate}
          isCriminalCreate={isCriminalCreate}
          isAdministrativeCreate={isAdministrativeCreate}
          initialView={initialView}
          caseTypeOptions={caseTypeOptions}
          setSelectedCreateType={setSelectedCreateType}
          contractPrefill={contractPrefill}
          contracts={contracts}
          createCustomer={createCustomer}
          createContractOptions={createContractOptions}
          clientPositionOptions={clientPositionOptions}
          caseStatuses={caseStatuses}
          causeOptions={causeOptions}
          caseLawyerOptions={caseLawyerOptions}
          caseAssistantOptions={caseAssistantOptions}
          caseClues={caseClues}
          rightTypeOptions={rightTypeOptions}
          litigantLabels={litigantLabels}
          firstCourtEnabled={firstCourtEnabled}
          secondCourtEnabled={secondCourtEnabled}
          retrialCourtEnabled={retrialCourtEnabled}
          firstCourtName={firstCourtName}
          secondCourtName={secondCourtName}
          retrialCourtName={retrialCourtName}
          courtOptions={courtOptions}
          officersForCourt={officersForCourt}
          openCreateDefendantEditor={openCreateDefendantEditor}
          advanceCreateStep={advanceCreateStep}
          saveLitigants={saveLitigants}
          finishCreateFlow={finishCreateFlow}
        />
      )}
      {specialMode ? <Card className="panel case-original-panel case-special-panel" title={specialTitle[specialMode]} extra={specialMode==="execution"?<Space><Button type="link" onClick={()=>document.querySelector('.case-special-query')?.classList.remove('case-query-hidden')}>高级搜索</Button><Button type="link" onClick={()=>document.querySelector('.case-special-query')?.classList.add('case-query-hidden')}>普通搜索</Button></Space>:null}>
        {specialMode==="invoice"&&<div className="case-invoice-import"><input ref={caseUploadRef} hidden type="file" accept=".xlsx,.xls,.csv,.pdf,.zip" onChange={event=>uploadCaseInvoiceFile(event.target.files?.[0])}/><Space><Button onClick={()=>caseUploadRef.current?.click()}>上传文件</Button><Button type="primary" onClick={startCaseInvoiceImport}>开始导入</Button></Space></div>}
        {specialMode!=="invoice"&&specialMode!=="stage"&&<ListFilterBar form={caseQueryForm} className="case-special-query" initialValues={shouldUseCompanyScheduleQueryFields(initialView)?getCompanyScheduleQueryInitialValues(dayjs()):undefined} onFinish={values=>setCaseQuery(values)}>
          {(specialFilters[specialMode]||[]).map(([key,label,type,placeholder])=><Form.Item key={key} name={key} label={label}>{type==="date"?<DatePicker.RangePicker placeholder={placeholder!==undefined?[placeholder,placeholder]:undefined}/>:type==="select"?<Select allowClear placeholder={placeholder} options={["民事争议","刑事案件","行政案件及国家赔偿","法律顾问","仲裁"].map(value=>({value,label:value}))}/>:<Input placeholder={placeholder}/>}</Form.Item>)}
          <Form.Item className="case-special-query-actions"><Space><Button type="primary" htmlType="submit">查询</Button><Button onClick={()=>{caseQueryForm.resetFields();setCaseQuery({})}}>{["unclaimed","refund","receipt"].includes(specialMode)?"清空":"重置"}</Button></Space></Form.Item>
        </ListFilterBar>}
        {specialMode==="stage"&&<div className="case-stage-query"><DatePicker picker="month" defaultValue={dayjs()}/><Button type="primary" onClick={()=>void load()}>查询</Button><Button onClick={exportStageStatistics}>导出统计</Button></div>}
        {specialMode!=="invoice"&&<input ref={caseUploadRef} hidden type="file" onChange={event=>uploadCaseFile(event.target.files?.[0])}/>} 
        <Table className="case-original-table" rowKey="id" size="small" loading={loading} columns={specialColumns[specialMode]} dataSource={specialRows} rowSelection={specialMode==="invoice"||specialMode==="stage"?undefined:{selectedRowKeys:selectedCaseKeys,onChange:setSelectedCaseKeys}} scroll={{x:specialMode==="stage"?800:1500}} pagination={specialMode==="execution"?{current:pendingExecutionPage,pageSize:pendingExecutionPageSize,total:pendingExecutionTotal,showSizeChanger:true,pageSizeOptions:[10,20,50,100],showTotal:total=>`共有${total}条`,onChange:(page:number,pageSize:number)=>void loadPendingExecutionCases(page,pageSize)}:{...(shouldUseCompanySchedulePagination(initialView)?{defaultPageSize:20,showSizeChanger:true,pageSizeOptions:getCompanySchedulePageSizeOptions(),showQuickJumper:{goButton:<Button size="small">GO</Button>}}:{pageSize:20}),...(shouldUseCompanySchedulePagination(initialView)?{current:companySchedulePage,pageSize:companySchedulePageSize,onChange:(page:number,pageSize:number)=>{setCompanySchedulePage(page);setCompanySchedulePageSize(pageSize);}}:{}),showTotal:total=>`共有${total}条`}} />
        {shouldShowCompanyScheduleSinglePageJumper(initialView,specialRows.length,companySchedulePageSize)&&<Space style={{display:"flex",justifyContent:"flex-end",marginTop:8}}><InputNumber size="small" min={1} max={1} value={1} controls={false} readOnly aria-label="页码"/><Button size="small" onClick={()=>setCompanySchedulePage(1)}>GO</Button></Space>}
        {specialMode!=="invoice"&&specialMode!=="stage"&&shouldShowCompanyScheduleActions(initialView,specialRows.length)&&<div className="case-bottom-actions"><Space>
          {(specialMode==="schedule"||specialMode==="execution"||specialMode==="unclaimed")&&<Button onClick={exportCases}>导出{specialMode==="schedule"?"案件":""}</Button>}
          {specialMode==="refund"&&<Button onClick={()=>void exportSpecialRecords("refund","退费查询.csv")}>导出</Button>}
          {specialMode==="refund"&&<Dropdown menu={{items:[{key:"view",label:"案件任务"},{key:"export",label:"导出案件打印表"}],onClick:({key})=>{if(key==="export")void exportCases();else if(selectedSpecialRow)void openSpecialCaseTasks({case_record_id:selectedSpecialRow.data.case_record_id||selectedSpecialRow.data.case_id,case_no:selectedSpecialRow.data.case_no||selectedSpecialRow.serial_no});else message.warning("请先选择退费记录")}}}><Button>更多操作</Button></Dropdown>}
          {specialMode==="refund"&&<Button onClick={operateRefund}>退费操作</Button>}
          {specialMode==="receipt"&&<Button onClick={()=>selectedCase?caseUploadRef.current?.click():message.warning("请先选择案件")}>批量上传</Button>}
          {specialMode==="unclaimed"&&<Button onClick={markCommissionPaid}>标识提成已发</Button>}
          {specialMode==="schedule"&&<Button onClick={()=>void openSelectedScheduleHearing()}>更多操作</Button>}
          {specialMode==="execution"&&<><Button onClick={()=>openExecutionStatus(specialRows.filter((row:CaseRow)=>selectedCaseKeySet.has(String(row.id))))}>修改执行状态</Button><Button onClick={()=>selectedSpecialRow?openProgress(selectedSpecialRow):message.warning("请先选择案件")}>更多操作</Button></>}
          {specialMode==="unclaimed"&&<Button onClick={()=>selectedCase?openCaseTasks(selectedCase):message.warning("请先选择案件")}>更多操作</Button>}
        </Space></div>}
      </Card> : originalArchiveMode ? <Card className="panel case-original-panel" title={archiveDone?"已审核":archiveRefused?"已拒绝":"待审核"}>
        <ListFilterBar form={caseQueryForm} className="case-archive-query" layout="inline" onFinish={values=>setCaseQuery(values)}>
          <Form.Item label="原告/申请人/公诉机关" name="plaintiff"><Input /></Form.Item><Form.Item label="案号" name="serial_no"><Input /></Form.Item><Form.Item label="律师助理" name="assistant"><Input /></Form.Item><Form.Item label="法院/机构" name="court"><Input /></Form.Item>
          <Form.Item label="被告/被申请人" name="defendant"><Input /></Form.Item><Form.Item label="公证书号" name="notary_no"><Input /></Form.Item><Form.Item label="开庭律师" name="hearing_lawyer"><Input /></Form.Item><Form.Item label={archiveDone||archiveRefused?"审核时间":"开庭时间"} name="review_range"><DatePicker.RangePicker /></Form.Item>
          <Form.Item label="第三人/受害人" name="third_party"><Input /></Form.Item><Form.Item label="经办律师" name="handling_lawyer"><Input /></Form.Item><Form.Item label="提交人" name="submitter"><Input /></Form.Item><Form.Item label="提交时间" name="submit_range"><DatePicker.RangePicker /></Form.Item>
          <Form.Item className="case-archive-query-actions"><Space><Button type="primary" htmlType="submit">查询</Button><Button onClick={()=>{caseQueryForm.resetFields();setCaseQuery({})}}>重置</Button></Space></Form.Item>
        </ListFilterBar>
<Table className="case-original-table" rowKey="id" size="small" loading={loading} columns={originalArchiveColumns} dataSource={originalArchiveRows} rowSelection={{selectedRowKeys:selectedCaseKeys,onChange:setSelectedCaseKeys}} scroll={{x:archiveCaseTableScrollX}} pagination={getCaseArchivePagination(initialView)} />
        <div className="case-bottom-actions"><Space wrap>
          <Button onClick={exportCases}>导出全部（CSV）</Button>
          <Button onClick={()=>exportArchiveManifest(true)}>导出选中归档清单（Excel）</Button>
          <Button onClick={()=>exportArchiveManifest(false)}>导出当前筛选归档清单（Excel）</Button>
          <Dropdown
            menu={{
              items: selectedArchiveCase ? [
                { key: "tasks", label: "案件任务" },
                ...(selectedArchiveCaseCapability.can_archive ? [{ key: "archive", label: "归档检查" }] : []),
                ...(!archiveDone && !archiveRefused && isArchiveManager ? [{ key: "review", label: "归档审核" }] : []),
                ...(archiveDone && selectedArchiveCaseCapability.can_edit_basic ? [{ key: "unarchive-request", label: "申请解档" }] : []),
                ...(archiveDone && isArchiveManager ? [{ key: "unarchive-approve", label: "通过解档审批" }, { key: "unarchive-reject", label: "驳回解档审批" }] : []),
              ] : [{ key: "select", label: "请先选择一条案件", disabled: true }],
              onClick: ({ key }) => {
                if (!selectedArchiveCase) return message.warning("请先选择一条案件");
                if (key === "tasks") openCaseTasks(selectedArchiveCase);
                if (key === "archive") void openArchive(selectedArchiveCase);
                if (key === "review") {
                  if (!isArchiveManager) return message.warning("当前账号没有归档审核权限");
                  if (!ARCHIVE_REVIEW_STATUSES.includes(selectedArchiveCase.status)) return message.warning("只有待归档审核案件可执行审核");
                  openArchiveReview(selectedArchiveCase);
                }
                if (key === "unarchive-request") void requestUnarchive(selectedArchiveCase);
                if (key === "unarchive-approve" || key === "unarchive-reject") {
                  if (!isArchiveManager) return message.warning("当前账号没有解档审批权限");
                  if (selectedArchiveCase.data.unarchive_request?.status !== "待审批") return message.warning("该案件没有待审批的解档申请");
                  void openUnarchiveReview(selectedArchiveCase, key === "unarchive-approve");
                }
              },
            }}
          ><Button>更多操作</Button></Dropdown>
          {!archiveDone && !archiveRefused && isArchiveManager && <Button onClick={() => {
            if (!selectedArchiveCase) return message.warning("请先选择一条案件");
            openArchiveReview(selectedArchiveCase);
          }}>归档审核</Button>}
          {archiveDone && selectedArchiveCaseCapability.can_edit_basic && <Button onClick={() => selectedArchiveCase ? void requestUnarchive(selectedArchiveCase) : message.warning("请先选择一条案件")}>申请解档</Button>}
          {archiveDone && isArchiveManager && <Button onClick={() => {
            if (!selectedArchiveCase) return message.warning("请先选择一条案件");
            if (selectedArchiveCase.data.unarchive_request?.status !== "待审批") return message.warning("该案件没有待审批的解档申请");
            void reviewUnarchive(selectedArchiveCase, true);
          }}>解档审批</Button>}
        </Space></div>
      </Card> : originalListMode && <div className="case-original-layout">
        <aside className="case-phase-panel"><div className="case-phase-title">案件阶段</div><div className="case-phase-tree">{phaseTreeItems.map(({label,value,count,children})=>{
          const grouped = children.length > 0 || LEGACY_PHASE_GROUPS.has(label);
          const expanded = Boolean(expandedPhaseGroups[label]);
          return <div key={value} className={grouped ? "case-phase-group" : "case-phase-group case-phase-group-leaf"}>
            <div className="case-phase-row">
              {grouped ? <button type="button" className="case-phase-toggle" aria-label={`${expanded ? "收起" : "展开"}${label}`} onClick={()=>setExpandedPhaseGroups((current)=>({...current,[label]:!expanded}))}>{expanded ? "▾" : "▸"}</button> : <span className="case-phase-toggle-placeholder" />}
              <button type="button" className="case-phase-filter" onClick={()=>void searchByPhase(value)}>📁 {label}【{count}】</button>
            </div>
            {expanded && <div className="case-phase-children">{children.map((child)=><button key={`${label}-${child.value}`} type="button" className="case-phase-child" onClick={()=>void searchByPhase(child.value)}>📁 {child.label}【{child.count}】</button>)}</div>}
          </div>;
        })}</div></aside>
        <Card className="panel case-original-panel" title="案件列表" extra={<Button type="link" onClick={()=>document.querySelector('.case-advanced-query')?.classList.toggle('case-query-expanded')}>高级搜索</Button>}>
          <ListFilterBar form={caseQueryForm} className="case-advanced-query case-query-expanded" onFinish={(values)=>{setCaseQuery(values);setOriginalPage(1);if(counselListMode)void loadCounselCases(values,1,counselPageSize);else void loadOrdinaryCases(values,1,originalPageSize);}}>
            {counselListMode ? <>
              <Form.Item label="客户" name="customer"><Input placeholder="客户"/></Form.Item><Form.Item label="案号" name="serial_no"><Input placeholder="案号"/></Form.Item><Form.Item label="关键字" name="keyword"><Input placeholder="案号、案件名称、客户名称"/></Form.Item><Form.Item label="顾问期间" name="counsel_range"><DatePicker.RangePicker /></Form.Item>
              <Form.Item label="顾问类型" name="counsel_type"><Input placeholder="顾问类型"/></Form.Item><Form.Item label="案件阶段" name="status"><Input placeholder="案件阶段"/></Form.Item><Form.Item label="经办律师" name="handling_lawyer"><Input placeholder="经办律师"/></Form.Item><Form.Item label="律师助理" name="assistant"><Input placeholder="律师助理"/></Form.Item><Form.Item label="文档名称" name="document_name"><Input placeholder="文档名称"/></Form.Item>
            </> : shouldUseCompanyCriminalQueryFields(initialView) ? <>
              {getCompanyCriminalQueryFields().map(([name,label,placeholder])=><Form.Item key={name} label={label} name={name}><Input placeholder={placeholder}/></Form.Item>)}
            </> : shouldUseCompanyArbitrationQueryFields(initialView) ? <>
              {getCompanyArbitrationQueryFields().map(([name,label,placeholder])=><Form.Item key={name} label={label} name={name}><Input placeholder={placeholder}/></Form.Item>)}
            </> : <>
              <Form.Item label="原告" name="plaintiff"><Input placeholder="原告"/></Form.Item><Form.Item label="案件编号" name="serial_no"><Input placeholder="案件编号"/></Form.Item><Form.Item label="取证机构" name="evidence_org"><Input placeholder="取证机构"/></Form.Item><Form.Item label="关键字" name="keyword"><Input placeholder="案号、法院号、案件名、客户名"/></Form.Item>
              <Form.Item label="被告" name="defendant"><Input placeholder="被告"/></Form.Item><Form.Item label="经办律师" name="handling_lawyer"><Input placeholder="经办律师"/></Form.Item><Form.Item label="公证书号" name="notary_no"><Input placeholder="公证书号"/></Form.Item><Form.Item label="案件阶段" name="status"><Input placeholder="案件阶段"/></Form.Item>
              <Form.Item label="开庭律师" name="hearing_lawyer"><Input placeholder="开庭律师"/></Form.Item><Form.Item label="律师助理" name="assistant"><Input placeholder="律师助理"/></Form.Item><Form.Item label="调查员" name="investigator"><Input placeholder="调查员"/></Form.Item><Form.Item label="法院名称" name="court"><Input placeholder="法院名称"/></Form.Item>
              <Form.Item label="案源时间" name="source_range"><DatePicker.RangePicker /></Form.Item><Form.Item label="侵权渠道" name="channel"><Input placeholder="侵权渠道"/></Form.Item><Form.Item label="仓库" name="warehouse"><Input placeholder="仓库"/></Form.Item><Form.Item label="文档名称" name="document_name"><Input placeholder="文档名称"/></Form.Item>
              <Form.Item label="开庭时间" name="hearing_range"><DatePicker.RangePicker /></Form.Item><Form.Item label="侵权区域" name="area"><Input placeholder="侵权区域"/></Form.Item><Form.Item label="库位" name="location"><Input placeholder="库位"/></Form.Item><Form.Item label="日志内容" name="log_content"><Input placeholder="日志内容"/></Form.Item>
            </>}
            <Form.Item className="case-query-buttons"><Space><Button type="primary" htmlType="submit">{legacyCaseListOperationLabels.query}</Button><Button onClick={()=>{caseQueryForm.resetFields();setCaseQuery({});setOriginalPage(1);if(counselListMode)void loadCounselCases({},1,counselPageSize);else void loadOrdinaryCases({},1,originalPageSize);}}>{legacyCaseListOperationLabels.reset}</Button></Space></Form.Item>
          </ListFilterBar>
          <input ref={caseUploadRef} hidden type="file" onChange={event=>uploadCaseFile(event.target.files?.[0])}/>
          <Table className="case-original-table" rowKey="id" size="small" loading={counselListMode ? loading : ordinaryLoading} locale={counselListMode ? undefined : { emptyText: ordinaryLoading ? "案件加载中…" : ordinaryLoadError || "暂无案件" }} columns={counselListMode?counselCaseColumns:shouldUseCompanyCriminalQueryFields(initialView)?companyCriminalCaseColumns:originalCaseColumns} dataSource={counselListMode?counselCases:originalCases} rowSelection={{selectedRowKeys:selectedCaseKeys,onChange:setSelectedCaseKeys}} scroll={{x:counselListMode?counselCaseTableScrollX:shouldUseCompanyCriminalQueryFields(initialView)?companyCriminalCaseTableScrollX:originalCaseTableScrollX,y:"calc(100dvh - 465px)"}} pagination={counselListMode?{current:counselPage,pageSize:counselPageSize,total:counselTotal,showSizeChanger:true,pageSizeOptions:[10,15,20,50,100,200],showTotal:total=>`共有${total}条`}:{current:originalPage,pageSize:originalPageSize||legacyCaseListDefaults.pageSize,total:ordinaryTotal,showSizeChanger:true,pageSizeOptions:[10,15,20,50,100,200],showTotal:total=>`共有${total}条`}} onChange={(pagination,_filters,sorter:any)=>{const nextQuery={...caseQuery,sort_order:sorter?.order==="ascend"?"case_no_asc":sorter?.order==="descend"?"case_no_desc":"updated_desc"};setCaseQuery(nextQuery);if(!counselListMode){const nextPage=pagination.current||1;const nextPageSize=pagination.pageSize||originalPageSize;setOriginalPage(nextPage);setOriginalPageSize(nextPageSize);sessionStorage.setItem("sunhold:case-list-return", JSON.stringify({route:initialView,page:nextPage,pageSize:nextPageSize,query:nextQuery}));void loadOrdinaryCases(nextQuery,nextPage,nextPageSize);return;}void loadCounselCases(nextQuery,pagination.current||1,pagination.pageSize||counselPageSize);}}/>
          {shouldShowCaseListActions(initialView)&&<div className={`case-bottom-actions case-mine-list-actions${isCompanyCaseListRoute(initialView) ? " case-company-list-actions" : ""}`}><Space size={5} wrap>
            <Dropdown
              trigger={["click"]}
              menu={{
                items: [
                  ...(counselListMode ? [
                    { key: "selected-excel", label:"导出选中（CSV）", disabled: !selectedCaseKeys.length },
                    { key: "current-excel", label:"导出当前查询（CSV）", disabled: !counselCases.length },
                  ] : [
                    { key: "selected-excel", label:"导出选中（Excel）", disabled: !selectedCaseKeys.length },
                    { key: "current-excel", label:"导出当前查询（Excel）", disabled: !originalCases.length },
                  ]),
                  { key: "selected-manifest", label: "导出选中归档清单（Excel）", disabled: !selectedCaseKeys.length },
                  { key: "selected-qr-word", label: "导出选中二维码（Word）", disabled: !selectedCaseKeys.length },
                ],
                onClick: ({ key }) => {
                  if (key === "selected-excel") counselListMode ? void exportCounselCases(true) : exportSelectedCasesExcel(true);
                  if (key === "current-excel") counselListMode ? void exportCounselCases(false) : exportSelectedCasesExcel(false);
                  if (key === "selected-manifest") exportArchiveManifest(true);
                  if (key === "selected-qr-word") exportCaseQrWord();
                },
              }}
            ><Button aria-label="导出案件">导出</Button></Dropdown>
            <Button
              icon={<UploadOutlined />}
              disabled={selectedCaseKeys.length !== 1 || !selectedCaseCapability.can_upload_attachment}
              title={selectedCaseKeys.length !== 1 ? "请先选择一条案件" : "当前案件没有上传附件权限"}
              onClick={openCaseFileUpload}
            >上传文件</Button>
            {isCompanyCaseListRoute(initialView)&&<Button
              aria-label="删除案件"
              disabled={!canDeleteSelectedCompanyCase}
              title={!selectedCase ? "请先选择一条案件" : canDeleteSelectedCompanyCase ? "删除选中的公司案件" : "当前账号或案件状态不允许删除"}
              onClick={()=>selectedCase&&void deleteCompanyCase(selectedCase)}
            >删除案件</Button>}
            {["admin","manager"].includes(profile.role||"")&&selectedCase?.status==="待立案审批"&&<Button onClick={()=>void reviewCaseCreation(selectedCase,true)}>立案审批通过</Button>}
            {["admin","manager"].includes(profile.role||"")&&selectedCase?.status==="待立案审批"&&<Button danger onClick={()=>void reviewCaseCreation(selectedCase,false)}>立案审批驳回</Button>}
            {counselListMode&&<>
              <Button onClick={()=>selectedCase?void openCounselDetail(selectedCase):message.warning("请先选择案件")}>查看详情</Button>
              {(["admin","manager"].includes(profile.role||""))&&<Button onClick={()=>{if(!selectedCaseKeys.length)return message.warning("请选择需要修改的案件");batchUpdateForm.resetFields();setBatchUpdateOpen(true);}}>批量修改</Button>}
              {canCreateSelectedCaseFees&&<Button onClick={()=>{const feeTypeId=initialFeeTypeId(feeTypeCatalog,"律所");const feeType=feeTypeSelection(feeTypeCatalog,feeTypeId);batchFeeForm.resetFields();batchFeeForm.setFieldsValue({expense_scope:"律所",fee_type_id:feeTypeId,expense_subtype:feeType?.name,handler:profile.username});setBatchFeeOpen(true);}}>批量新增费用</Button>}
            </>}
            <Dropdown
              trigger={["click"]}
              menu={{
                items: selectedCase ? [
                  { key: "upload-document", label: "上传案件文档", disabled: !selectedCaseCapability.can_upload_attachment },
                  ...(selectedCaseCapability.can_create_finance ? [{ key: "firm-fees", label: "新增律所费用", children: [
                    { key: "firm-官费", label: "新增官费" },
                    { key: "firm-第三方费用", label: "新增第三方费用" },
                    { key: "firm-代理费", label: "新增代理费" },
                    { key: "firm-其他费用", label: "新增其他费用" },
                  ] }, { key: "platform-fees", label: "新增平台费用", children: [
                    { key: "platform-官费", label: "新增官费" },
                    { key: "platform-第三方费用", label: "新增第三方费用" },
                    { key: "platform-代理费", label: "新增代理费" },
                    { key: "platform-其他费用", label: "新增其他费用" },
                  ] }, { key: "internal-fee", label: "新增内部费用" }] : []),
                  ...(["admin","manager"].includes(profile.role||"") ? [{ key: "batch-update", label: "批量修改", children: [
                    { key: "batch-hearing-lawyer", label: "修改开庭律师" },
                    { key: "batch-handling-lawyer", label: "修改经办律师" },
                    { key: "batch-assistant", label: "修改律师助理" },
                    { key: "batch-stage", label: "修改案件阶段" },
                  ] }] : []),
                  { key: "document-authorization-letter", label: "生成授权委托书" },
                  { key: "document-law-firm-letter", label: "生成律所函" },
                  { key: "document-identity-certificate", label: "生成身份证明" },
                  { key: "document-settlement-list", label: "生成结算提成表" },
                  { key: "case-tasks", label: "案件任务" },
                  { key: "case-logs", label: "案件日志" },
                  { key: "export-print-table", label: "导出案件打印表" },
                ] : [{ key: "select", label: "请先选择案件", disabled: true }],
                onClick: ({ key }) => {
                  if (!selectedCase) return message.warning("请先选择案件");
                  if (key === "upload-document") openCaseFileUpload();
                  if (key.startsWith("firm-")) openCaseFee(selectedCase, "律所", key.slice("firm-".length));
                  if (key.startsWith("platform-")) openCaseFee(selectedCase, "平台", key.slice("platform-".length));
                  if (key === "internal-fee") openCaseFee(selectedCase, "内部", "内部费用");
                  if (key === "batch-stage") void openPhaseChange(selectedCases);
                  else if (key.startsWith("batch-")) { batchUpdateForm.resetFields(); setBatchUpdateOpen(true); }
                  if (key.startsWith("document-")) void generateSelectedCaseDocuments(key.slice("document-".length));
                  if (key === "case-tasks") openCaseTasks(selectedCase);
                  if (key === "case-logs") void openCounselDetail(selectedCase, "case-logs");
                  if (key === "export-print-table") exportSelectedCasesExcel(true);
                },
              }}
            ><Button aria-label="更多案件操作">更多操作 ▾</Button></Dropdown>
            {!counselListMode && initialView.includes("civil") && <Button onClick={() => setLegacyLsHistoryOpen(true)}>历史诉讼案件</Button>}
          </Space></div>}
        </Card>
      </div>}
      {!specialMode && !originalListMode && !originalArchiveMode && !isCreateView && <>
      <div className="case-stats">
        <Card>
          <Statistic title="案件总数" value={shownSummary.total} />
        </Card>
        <Card>
          <Statistic
            title="新案待分配"
            value={shownSummary.pending_assignment}
            styles={{ content: { color: "#f39c12" } }}
          />
        </Card>
        <Card>
          <Statistic
            title="办理中"
            value={shownSummary.in_progress}
            styles={{ content: { color: "#3c8dbc" } }}
          />
        </Card>
        <Card>
          <Statistic
            title="执行中"
            value={shownSummary.execution}
            styles={{ content: { color: "#dd4b39" } }}
          />
        </Card>
        <Card>
          <Statistic
            title="已归档"
            value={shownSummary.archived}
            styles={{ content: { color: "#00a65a" } }}
          />
        </Card>
      </div>
      <Card
        className="panel"
        title="案件中心"
        extra={
          <Space>
            {tab === "cases" && (
              <>
                <Checkbox
                  checked={showArchived}
                  onChange={(e) => setShowArchived(e.target.checked)}
                >
                  显示已归档
                </Checkbox>
              </>
            )}
            {tab === "cases" && <Button onClick={openClueConversion}>从线索转案件</Button>}
            <Button icon={<ReloadOutlined />} onClick={load}>
              刷新
            </Button>
          </Space>
        }
      >
        <Tabs
          activeKey={tab}
          onChange={setTab}
          items={[
            { key: "cases", label: "案件列表" },
            { key: "hearing", label: "开庭排期" },
            { key: "execution", label: "执行案件" },
            { key: "archive", label: "归档审核" },
          ]}
        />
        {tab === "hearing" ? (
          <Table
            rowKey="id"
            loading={loading}
            size="small"
            columns={hearingColumns}
            dataSource={hearings}
            scroll={{ x: 1200 }}
            pagination={{ pageSize: 20 }}
          />
        ) : tab === "archive" ? (
          <Table
            rowKey="id"
            loading={loading}
            size="small"
            columns={archiveColumns}
            dataSource={archiveRows}
            scroll={{ x: 1900 }}
            pagination={{ pageSize: 20 }}
          />
        ) : (
          <Table
            rowKey="id"
            loading={loading}
            size="small"
            columns={caseColumns}
            dataSource={visibleCases}
            scroll={{ x: 1900 }}
            pagination={{ pageSize: 20 }}
          />
        )}
      </Card>
      </>}
      <Modal open={Boolean(notaryInfoCase)} title="修改公证信息" okText="保存" cancelText="取消" onCancel={() => { setNotaryInfoCase(null); notaryInfoForm.resetFields(); }} onOk={() => void submitNotaryInfo()}>
        <Form form={notaryInfoForm} layout="vertical">
          <Form.Item label="公证书号" name="notary_nos" rules={[{ required: true, message: "请输入公证书号" }]}><Input placeholder="多个编号请用逗号分隔" /></Form.Item>
          <Form.Item
            label="仓库位置"
            name="warehouse_location_ids"
            rules={[{ required: true, message: "请从仓库库位中选择位置" }]}
            extra={notaryInfoCase?.data.deposit_address && !resolveCaseWarehouseLocationIds(notaryInfoCase.data, warehouseLocationOptions).length ? `历史位置：${notaryInfoCase.data.deposit_address}` : "多个库位可连续选择"}
          >
            <Select
              mode="multiple"
              showSearch
              optionFilterProp="label"
              placeholder="请选择仓库库位"
              options={warehouseLocationOptions}
            />
          </Form.Item>
          <Form.Item label="修改说明" name="comment"><Input.TextArea rows={2} maxLength={1000} /></Form.Item>
        </Form>
      </Modal>
      <Modal open={Boolean(settlementAmountCase)} title="修改诉讼或判决金额" okText="保存" cancelText="取消" onCancel={() => { setSettlementAmountCase(null); settlementAmountForm.resetFields(); }} onOk={() => void submitSettlementAmount()}>
        <Form form={settlementAmountForm} layout="vertical">
          <Form.Item label="诉讼标的金额" name="litigation_amount" rules={[{ required: true, message: "请输入诉讼标的金额" }]}><Input type="number" min={0} step="0.01" /></Form.Item>
          <Form.Item label="判决/和解金额" name="settlement_amount" rules={[{ required: true, message: "请输入判决或和解金额" }]}><Input type="number" min={0} step="0.01" /></Form.Item>
          <Form.Item label="修改说明" name="comment"><Input.TextArea rows={2} maxLength={1000} /></Form.Item>
        </Form>
      </Modal>
      <Modal
        width={760}
        open={Boolean(companyScheduleCourtInfo)}
        title={`修改法院信息 · ${companyScheduleCourtLevelLabel}`}
        okText="保存"
        cancelText="取消"
        okButtonProps={{disabled:false}}
        onOk={() => void submitCompanyScheduleCourtInfo()}
        onCancel={cancelCompanyScheduleCourtInfo}
        destroyOnHidden
      >
        <Form form={companyScheduleCourtInfoForm} layout="vertical">
          <div className="form-grid">
            <Form.Item label="法院" name="court"><Input placeholder="法院" /></Form.Item>
            <Form.Item label="法庭" name="courtroom"><Input /></Form.Item>
            <Form.Item label="法官" name="judge"><Input /></Form.Item>
            <Form.Item label="书记员" name="clerk"><Input /></Form.Item>
            <Form.Item label="案号" name="case_no"><Input /></Form.Item>
            <Form.Item label="立案日期" name="filing_date"><DatePicker style={{width:"100%"}} /></Form.Item>
            <Form.Item label="开庭日期" name="hearing_date"><DatePicker showTime style={{width:"100%"}} /></Form.Item>
            <Form.Item label="判决日期" name="judgment_date"><DatePicker style={{width:"100%"}} /></Form.Item>
          </div>
        </Form>
      </Modal>
      <Modal
        open={Boolean(assigning)}
        title={`案件人员分配：${assigning?.serial_no || ""}`}
        okText="保存分配"
        cancelText="取消"
        onOk={assign}
        onCancel={() => setAssigning(null)}
      >
        <Form form={assignForm} layout="vertical">
          <Form.Item label="客户管理人" name="customer_manager">
            <Input />
          </Form.Item>
          <Form.Item
            label="开庭律师"
            name="hearing_lawyer"
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label="经办律师" name="handling_lawyers">
            <Select
              mode="multiple"
              showSearch
              optionFilterProp="label"
              options={caseLawyerOptions}
              placeholder="请选择系统已创建的在职律师"
            />
          </Form.Item>
          <Form.Item label="律师助理" name="assistant">
            <Select allowClear showSearch optionFilterProp="label" options={caseAssistantOptions} placeholder="请选择系统已创建的在职人员" />
          </Form.Item>
          <Form.Item label="分配说明" name="comment">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        width={720}
        open={clueConversionOpen}
        title="从调查线索批量转案件"
        okText="生成案件"
        cancelText="取消"
        onOk={submitClueConversion}
        onCancel={() => { setClueConversionOpen(false); clueConversionForm.resetFields(); }}
        destroyOnHidden
      >
        <Alert type="info" showIcon title="仅可选择已完成取证且尚未转案的线索；系统会校验线索客户与合同客户一致。" style={{ marginBottom: 12 }} />
        <Form form={clueConversionForm} layout="vertical">
          <Form.Item label="调查线索" name="clue_ids" rules={[{ required: true, message: "请选择至少一条调查线索" }]}>
            <Select mode="multiple" showSearch optionFilterProp="label" options={caseClues.map((item) => ({ value: item.id, label: `${item.serial_no}｜${item.title}` }))} />
          </Form.Item>
          <Form.Item label="关联合同" name="contract_record_id" rules={[{ required: true, message: "请选择合同" }]}>
            <Select showSearch optionFilterProp="label" options={createContractOptions} />
          </Form.Item>
          <div className="form-grid">
            <Form.Item label="案件类型" name="case_type" rules={[{ required: true }]}>
              <Select options={caseTypeOptions.filter((item) => item.value !== "法律顾问")} />
            </Form.Item>
            <Form.Item label="法院" name="court"><Input /></Form.Item>
          </div>
        </Form>
      </Modal>
      <Modal
        width={520}
        open={Boolean(phaseEditing)}
        title={`变更阶段：${phaseEditing?.map((row) => row.serial_no).join("、") || ""}`}
        okText="确认变更"
        cancelText="取消"
        onOk={savePhaseChange}
        onCancel={() => { setPhaseEditing(null); phaseForm.resetFields(); }}
        destroyOnHidden
      >
        <Form form={phaseForm}>
          <Alert type="info" showIcon title="请选择一个末级阶段后确认变更；目录阶段不可直接选择。" style={{ marginBottom: 12 }} />
          <Form.Item name="case_phase_id" rules={[{ required: true, message: "请选择案件阶段" }]}>
            <CasePhasePickerTree options={phaseOptions} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        width={760}
        open={Boolean(progressEditing)}
        title={`登记案件进展：${progressEditing?.serial_no || ""}`}
        okText="保存并更新阶段"
        cancelText="取消"
        onOk={saveProgress}
        onCancel={() => setProgressEditing(null)}
      >
        <Alert
          type="info"
          showIcon
          title="填写一审案号后进入一审立案受理；新增一审开庭排期后进入一审准备开庭；填写裁判日期或文书号后进入待上诉；填写二审案号后进入二审。"
          style={{ marginBottom: 16 }}
        />
        <Form form={progressForm} layout="vertical">
          <div className="form-grid">
            <Form.Item label="一审法院" name="first_instance_court">
              <Input />
            </Form.Item>
            <Form.Item label="一审法院案号" name="first_instance_case_no">
              <Input />
            </Form.Item>
            <Form.Item label="法庭" name="courtroom">
              <Input />
            </Form.Item>
            <Form.Item label="审判人员/法官" name="judge">
              <Input />
            </Form.Item>
            <Form.Item label="书记员" name="clerk">
              <Input />
            </Form.Item>
            <Form.Item label="裁判日期" name="judgment_date">
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item label="裁判文书号" name="judgment_document_no">
              <Input />
            </Form.Item>
            <Form.Item label="二审法院" name="second_instance_court">
              <Input />
            </Form.Item>
            <Form.Item label="二审法院案号" name="second_instance_case_no">
              <Input />
            </Form.Item>
          </div>
          <Form.Item label="进展说明" name="comment">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={hearingOpen}
        title="新增开庭排期"
        okText="保存排期"
        cancelText="取消"
        onOk={createHearing}
        onCancel={() => setHearingOpen(false)}
      >
        <Form form={hearingForm} layout="vertical">
          <Form.Item
            label="关联案件"
            name="case_record_id"
            rules={[{ required: true }]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              options={cases.map((r) => ({
                value: r.id,
                label: `${r.serial_no}｜${r.title}`,
              }))}
            />
          </Form.Item>
          <div className="form-grid">
            <Form.Item
              label="开庭日期"
              name="hearing_date"
              rules={[{ required: true }]}
            >
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item
              label="开庭时间"
              name="hearing_time"
              rules={[{ required: true }]}
            >
              <TimePicker format="HH:mm" style={{ width: "100%" }} />
            </Form.Item>
          </div>
          <Form.Item label="开庭法院" name="court" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <div className="form-grid">
            <Form.Item label="法庭" name="courtroom">
              <Input />
            </Form.Item>
            <Form.Item label="开庭类型" name="hearing_type" initialValue="开庭">
              <Select
                options={[
                  "开庭",
                  "一审开庭",
                  "二审开庭",
                  "证据交换",
                  "听证",
                  "谈话",
                ].map((v) => ({ value: v, label: v }))}
              />
            </Form.Item>
          </div>
          <Form.Item
            label="开庭律师"
            name="hearing_lawyer"
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label="备注" name="remark">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={caseUploadOpen}
        title="上传案件材料"
        okText="选择文件"
        cancelText="取消"
        onOk={confirmCaseFileUpload}
        onCancel={() => setCaseUploadOpen(false)}
      >
        <Form layout="vertical">
          <Form.Item label="材料类型">
            <Select value={caseUploadCategory} options={selectedCase ? fileTypeOptionsForCase(selectedCase.data.case_type) : []} onChange={setCaseUploadCategory} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(feeInformTarget) && !feeInformArrivalOpen && !feeInformBillOpen && !feeInformLinkOpen}
        title={`新建费用通知：${feeInformTarget?.serial_no || ""}`}
        okText={feeInformRecord ? "已新建" : "新建费用通知"}
        okButtonProps={{ disabled: Boolean(feeInformRecord) }}
        confirmLoading={feeInformSubmitting}
        onOk={() => void createFeeInform()}
        onCancel={() => { setFeeInformTarget(null); setFeeInformRecord(null); feeInformForm.resetFields(); }}
      >
        <Alert type="info" showIcon style={{ marginBottom: 12 }} title="费用通知独立保存，不改变来源费用金额；到账和票据须在该通知内依次确认。" />
        <Form form={feeInformForm} layout="vertical">
          <Form.Item label="通知日期" name="inform_date" rules={[{ required: true, message: "请选择通知日期" }]}><DatePicker style={{ width: "100%" }} /></Form.Item>
          <Form.Item label="说明" name="remark"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>
      <Modal
        open={feeInformArrivalOpen}
        title="费用通知到账确认"
        okText="确认到账"
        confirmLoading={feeInformSubmitting}
        onOk={() => void confirmFeeInformArrival()}
        onCancel={() => { setFeeInformArrivalOpen(false); feeInformArrivalForm.resetFields(); }}
      >
        <Form form={feeInformArrivalForm} layout="vertical">
          <div className="form-grid"><Form.Item label="应收金额" name="receivable_amount" rules={[{ required: true }]}><InputNumber min={0.01} precision={2} style={{ width: "100%" }} /></Form.Item><Form.Item label="实收金额" name="received_amount" rules={[{ required: true }]}><InputNumber min={0.01} precision={2} style={{ width: "100%" }} /></Form.Item></div>
          <Form.Item label="到账日期" name="received_date" rules={[{ required: true }]}><DatePicker style={{ width: "100%" }} /></Form.Item>
          <Form.Item label="备注" name="remark"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
      <Modal
        open={feeInformBillOpen}
        title="上传费用通知票据"
        okText="上传票据"
        confirmLoading={feeInformSubmitting}
        onOk={() => void uploadFeeInformBill()}
        onCancel={() => { setFeeInformBillOpen(false); setFeeInformFile([]); feeInformBillForm.resetFields(); }}
      >
        <Form form={feeInformBillForm} layout="vertical">
          <div className="form-grid"><Form.Item label="票据编号" name="bill_no" rules={[{ required: true, whitespace: true, message: "请输入票据编号" }]}><Input /></Form.Item><Form.Item label="票据金额" name="bill_amount" rules={[{ required: true }]}><InputNumber min={0.01} precision={2} style={{ width: "100%" }} /></Form.Item></div>
          <Form.Item label="票据日期" name="bill_date" rules={[{ required: true }]}><DatePicker style={{ width: "100%" }} /></Form.Item>
          <Form.Item label="票据文件" required><Upload maxCount={1} fileList={feeInformFile} beforeUpload={(file) => { setFeeInformFile([file]); return false; }} onRemove={() => { setFeeInformFile([]); return true; }}><Button icon={<UploadOutlined />}>选择票据文件</Button></Upload></Form.Item>
        </Form>
      </Modal>
      <Modal
        open={feeInformLinkOpen}
        title="关联费用信息"
        okText="保存关联"
        confirmLoading={feeInformSubmitting}
        onOk={() => void saveFeeInformLinks()}
        onCancel={() => { setFeeInformLinkOpen(false); feeInformLinkForm.resetFields(); }}
      >
        <Alert type="info" showIcon style={{ marginBottom: 12 }} title="至少选择两条同案件费用；来源费用和已被其他通知占用的费用不可选择。" />
        <Form form={feeInformLinkForm} layout="vertical"><Form.Item label="关联费用" name="fee_ids" rules={[{ required: true, type: "array", min: 2, message: "请至少选择两条费用" }]}><Select mode="multiple" showSearch optionFilterProp="label" options={counselDetailFinance.filter((row) => row.id !== feeInformTarget?.id).map((row) => ({ value: row.id, label: `${row.serial_no}｜${row.data.expense_subtype || row.data.fee_type || row.title}｜${row.data.amount ?? 0}` }))} /></Form.Item></Form>
      </Modal>
      <Modal
        open={Boolean(editingFeeRow)}
        title={`${editingInternalFee ? "修改内部费用" : "修改案件费用"}：${editingFeeRow?.data.case_no || ""}`}
        okText="保存费用草稿"
        cancelText="取消"
        onOk={createCaseFee}
        onCancel={() => { setEditingFeeRow(null); feeForm.resetFields(); }}
      >
        <Form form={feeForm} layout="vertical">
          {editingInternalFee ? <>
            <Form.Item label="费用名称" name="title" rules={[{ required: true }]}><Input /></Form.Item>
            <div className="form-grid">
              <Form.Item label="费用类别" name="fee_type_id" rules={[{ required: true, message: "请选择末级费用类型" }]}><TreeSelect showSearch treeNodeFilterProp="title" treeDefaultExpandAll treeData={feeTypeTreeOptions} placeholder="请选择系统费用类型" onChange={(value) => { const option = feeTypeSelection(feeTypeCatalog, value); feeForm.setFieldsValue({ expense_subtype: option?.name, fee_type: option?.base_fee_type }); }} /></Form.Item>
              <Form.Item label="收款人" name="payee" rules={[{ required: true, message: "请选择收款人" }]}><Select showSearch optionFilterProp="label" options={feeEmployeeOptions} /></Form.Item>
              <Form.Item label="基数" name="base_amount"><InputNumber min={0} precision={2} style={{ width: "100%" }} /></Form.Item>
              <Form.Item label="参考提成" name="reference_commission"><InputNumber min={0} precision={2} style={{ width: "100%" }} /></Form.Item>
              <Form.Item label="实际金额" name="amount" rules={[{ required: true, message: "请输入实际金额" }]}><InputNumber precision={2} style={{ width: "100%" }} /></Form.Item>
              <Form.Item name="expense_scope" hidden><Input /></Form.Item><Form.Item name="expense_subtype" hidden><Input /></Form.Item><Form.Item name="fee_type" hidden><Input /></Form.Item><Form.Item name="handler" hidden><Input /></Form.Item>
            </div>
            <Form.Item label="备注" name="description"><Input.TextArea rows={2} /></Form.Item>
          </> : <>
            <Form.Item label="费用名称" name="title" rules={[{ required: true }]}><Input /></Form.Item>
            <div className="form-grid">
              <Form.Item label="合同号" name="contract_record_id" rules={[{ required: true, message: "请选择关联合同" }]}><Select showSearch optionFilterProp="label" placeholder="请选择当前客户合同" options={feeContractOptions} /></Form.Item>
              <Form.Item label="关联材料类型" name="source_file_type" rules={caseRelations ? [{ required: true, message: "请选择关联材料类型" }] : []}><Select allowClear options={feeSourceFileTypeOptions} onChange={() => feeForm.setFieldsValue({ fee_type_id: undefined, expense_subtype: undefined, fee_type: undefined })} /></Form.Item>
              <Form.Item label="费用归属" name="expense_scope" rules={[{ required: true }]}><Select options={["律所", "平台", "内部"].map(value => ({ value, label: value }))} onChange={() => feeForm.setFieldsValue({ fee_type_id: undefined, expense_subtype: undefined, fee_type: undefined })} /></Form.Item>
              <Form.Item label="费用类别" name="fee_type_id" rules={[{ required: true, message: "请选择末级费用类型" }]}><TreeSelect showSearch treeNodeFilterProp="title" treeDefaultExpandAll treeData={feeTypeTreeOptions} placeholder="请选择系统费用类型" onChange={(value) => { const option = feeTypeSelection(feeTypeCatalog, value); feeForm.setFieldsValue({ expense_subtype: option?.name, fee_type: option?.base_fee_type }); }} /></Form.Item>
              <Form.Item label="金额" name="amount" rules={[{ required: true }]}><InputNumber min={0.01} precision={2} style={{ width: "100%" }} /></Form.Item><Form.Item name="expense_subtype" hidden><Input /></Form.Item><Form.Item name="fee_type" hidden><Input /></Form.Item><Form.Item label="经办人员" name="handler" rules={[{ required: true }]}><Input /></Form.Item><Form.Item label="收款单位" name="payee"><Input /></Form.Item><Form.Item label="缴费法院/机构" name="court"><Input /></Form.Item><Form.Item label="缴费通知文号" name="document_no"><Input /></Form.Item><Form.Item label="截止日期" name="deadline"><DatePicker style={{ width: "100%" }} /></Form.Item>
            </div>
              <Form.Item label="说明" name="description"><Input.TextArea rows={2} /></Form.Item>
              {feeBaseType === "代理费" && <Form.List name="commission_details">{(fields, { add, remove }) => <section className="case-fee-commission-details"><div className="case-fee-commission-header"><strong>员工提成</strong><Button type="dashed" icon={<PlusOutlined />} onClick={() => add({ commission_type: "员工提成" })}>新建员工提成</Button></div>{fields.map((field) => <div className="case-fee-commission-row" key={field.key}><Form.Item {...field} name={[field.name, "employee_username"]} label="员工" rules={[{ required: true, message: "请选择员工" }]}><Select showSearch optionFilterProp="label" options={feeEmployeeOptions} /></Form.Item><Form.Item {...field} name={[field.name, "commission_type"]} label="提成类型" rules={[{ required: true }]}><Input /></Form.Item><Form.Item {...field} name={[field.name, "amount"]} label="提成金额" rules={[{ required: true, message: "请输入提成金额" }]}><InputNumber min={0.01} precision={2} style={{ width: "100%" }} /></Form.Item><Form.Item {...field} name={[field.name, "remark"]} label="备注"><Input /></Form.Item><Button danger type="text" aria-label="删除员工提成" icon={<MinusCircleOutlined />} onClick={() => remove(field.name)} /></div>)}</section>}</Form.List>}
          </>}
        </Form>
      </Modal>
      <Drawer
        open={Boolean(feeCase)}
        title={activeFeeContractScope === "平台" && feeSubtypePreset === "agency" ? "新增平台代理费" : "新增费用"}
        width={620}
        className="case-fee-create-drawer"
        onClose={closeCaseFeeCreator}
        footer={<Space className="case-fee-drawer-footer">
          <Button type="primary" loading={caseFeeSubmitting} onClick={() => caseFeeCreateStep === 0 ? void createCaseFee() : void submitCreatedCaseFeePayments()}>{caseFeeCreateStep === 0 ? "下一步" : "申请付款"}</Button>
          <Button onClick={closeCaseFeeCreator}>取消</Button>
        </Space>}
      >
        <Steps size="small" current={caseFeeCreateStep} items={[{ title: "新增费用" }, { title: "申请付款" }]} />
        {caseFeeCreateStep === 0 ? <>
          <Alert className="case-fee-legacy-tip" type="info" title="温馨提示" description={activeFeeContractScope === "内部" ? <ol><li>申请付款按照每个案号生成一个申请单。</li><li>点击表格头部可将第一行数据同步到各行。</li><li>基数用于计算提成参考值，实际金额可按业务调整。</li></ol> : <ol><li>同一付款单位可以申请付款，否则请按实际业务进行操作。</li><li>申请付款按照每个合同号生成一个申请单。</li><li>点击表格头部（费用类型、金额、备注、截止日期）可将第一行数据同步到各行。</li><li>截止日期默认为申请之日第5天，如有特殊情况，可在申请时修改。</li></ol>} />
          <Form form={feeForm} component={false}>
            <Form.List name="items" rules={[{ validator: async (_, items) => { if (!items?.length) throw new Error("请至少新增一条费用"); } }]}>{(fields, { add, remove }) => activeFeeContractScope === "内部" ? <div className="case-fee-entry-table case-internal-fee-entry-table">
              <div className="case-fee-entry-head"><span>案号</span><span>费用类型</span><span>支付对象</span><span>基数</span><span>参考提成</span><span>实际金额</span><span>备注</span><span>操作</span></div>
              {fields.map((field) => <div className="case-fee-entry-row" key={field.key}>
                <span className="case-fee-static-value">{feeCase?.serial_no || "—"}</span>
                <Form.Item name={[field.name, "fee_type_id"]} rules={[{ required: true, message: "请选择末级费用类型" }]}><TreeSelect showSearch treeNodeFilterProp="title" treeDefaultExpandAll popupMatchSelectWidth={180} treeData={feeTypeTreeOptions} onChange={(value) => { const option = feeTypeSelection(feeTypeCatalog, value); feeForm.setFieldValue(["items",field.name,"expense_subtype"],option?.name); feeForm.setFieldValue(["items",field.name,"fee_type"],option?.base_fee_type); feeForm.setFieldValue(["items",field.name,"title"],`${feeCase?.title || ""}${option?.name || ""}`); }} /></Form.Item>
                <Form.Item name={[field.name, "payee"]} rules={[{ required: true, message: "请选择收款人" }]}><Select showSearch optionFilterProp="label" placeholder="收款人" options={feeEmployeeOptions} /></Form.Item>
                <Form.Item name={[field.name, "base_amount"]}><InputNumber min={0} precision={2} className="case-fee-amount-input" /></Form.Item>
                <Form.Item name={[field.name, "reference_commission"]}><InputNumber min={0} precision={2} className="case-fee-amount-input" /></Form.Item>
                <Form.Item name={[field.name, "amount"]} rules={[{ required: true, message: "请输入实际金额" }]}><InputNumber precision={2} className="case-fee-amount-input" /></Form.Item>
                <Form.Item name={[field.name, "description"]}><Input /></Form.Item>
                <span className="case-fee-row-actions"><Button type="text" aria-label="新增费用行" icon={<PlusOutlined />} onClick={() => add({ ...feeForm.getFieldValue(["items", field.name]), amount: undefined })} /><Button type="text" danger aria-label="删除费用行" icon={<CloseOutlined />} disabled={fields.length === 1} onClick={() => remove(field.name)} /></span>
                <Form.Item name={[field.name, "title"]} hidden><Input /></Form.Item><Form.Item name={[field.name, "expense_scope"]} hidden><Input /></Form.Item><Form.Item name={[field.name, "expense_subtype"]} hidden><Input /></Form.Item><Form.Item name={[field.name, "fee_type"]} hidden><Input /></Form.Item><Form.Item name={[field.name, "handler"]} hidden><Input /></Form.Item>
              </div>)}
            </div> : <div className="case-fee-entry-table">
              <div className="case-fee-entry-head"><span>案号</span><span>合同号</span><span>费用类型</span><span>金额</span><span>备注</span><span>截止日期</span><span>操作</span></div>
              {fields.map((field) => <div className="case-fee-entry-row" key={field.key}>
                <span className="case-fee-static-value">{feeCase?.serial_no || "—"}</span>
                <Form.Item name={[field.name, "contract_record_id"]} rules={[{ required: true, message: "请选择合同" }]}><Select showSearch optionFilterProp="label" placeholder="请选择" options={feeContractOptions} /></Form.Item>
                <Form.Item name={[field.name, "fee_type_id"]} rules={[{ required: true, message: "请选择末级费用类型" }]}><TreeSelect showSearch treeNodeFilterProp="title" treeDefaultExpandAll popupMatchSelectWidth={180} treeData={feeTypeTreeOptions} onChange={(value) => { const option = feeTypeSelection(feeTypeCatalog, value); feeForm.setFieldValue(["items",field.name,"expense_subtype"],option?.name); feeForm.setFieldValue(["items",field.name,"fee_type"],option?.base_fee_type); feeForm.setFieldValue(["items",field.name,"title"],`${feeCase?.title || ""}${option?.name || ""}`); }} /></Form.Item>
                <Form.Item name={[field.name, "amount"]} rules={[{ required: true, message: "请输入金额" }]}><InputNumber min={0.01} precision={2} className="case-fee-amount-input" /></Form.Item>
                <Form.Item name={[field.name, "description"]}><Input /></Form.Item>
                <Form.Item name={[field.name, "deadline"]}><DatePicker /></Form.Item>
                <span className="case-fee-row-actions"><Button type="text" aria-label="新增费用行" icon={<PlusOutlined />} onClick={() => add({ ...feeForm.getFieldValue(["items", field.name]), amount: undefined })} /><Button type="text" danger aria-label="删除费用行" icon={<CloseOutlined />} disabled={fields.length === 1} onClick={() => remove(field.name)} /></span>
                <Form.Item name={[field.name, "title"]} hidden><Input /></Form.Item><Form.Item name={[field.name, "expense_scope"]} hidden><Input /></Form.Item><Form.Item name={[field.name, "expense_subtype"]} hidden><Input /></Form.Item><Form.Item name={[field.name, "fee_type"]} hidden><Input /></Form.Item><Form.Item name={[field.name, "handler"]} hidden><Input /></Form.Item>
              </div>)}
            </div>}</Form.List>
          </Form>
        </> : <>
          <Alert className="case-fee-legacy-tip" type="info" title="温馨提示" description={activeFeeContractScope === "内部" ? <ol><li>同一付款单位可以申请付款，否则请按实际业务进行操作。</li><li>申请付款按照每个案号生成一个申请单。</li></ol> : <ol><li>同一付款单位可以申请付款，否则请按实际业务进行操作。</li><li>申请付款按照每个合同号生成一个申请单。</li><li>代理费不允许付款。</li></ol>} />
          {activeFeeContractScope === "内部" ? <div className="case-fee-payment-table">
            <div className="case-fee-payment-head"><span>案号</span><span>费用类型</span><span>金额</span><span>收款人</span><span>付款账号</span></div>
            {createdCaseFees.map((row, index) => <div className="case-fee-payment-row" key={row.id}><span>{feeCase?.serial_no || "—"}</span><span>{row.data.expense_subtype || row.data.fee_type || "—"}</span><span>{row.data.amount ?? 0}</span><Input value={caseFeePaymentDrafts[index]?.payment_payee || ""} onChange={(event) => setCaseFeePaymentDrafts((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, payment_payee: event.target.value } : item))} /><Input value={caseFeePaymentDrafts[index]?.payment_account || ""} onChange={(event) => setCaseFeePaymentDrafts((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, payment_account: event.target.value } : item))} /></div>)}
          </div> : <div className="case-fee-payment-table case-fee-payment-unit-table">
            <div className="case-fee-payment-head"><span>合同号</span><span>案号</span><span>费用类型</span><span>金额</span><span>付款备注</span><span>收款单位</span><span>操作</span></div>
            {createdCaseFees.map((row, index) => <div className="case-fee-payment-row" key={row.id}>
              <span>{row.data.contract_no || "—"}</span><span>{feeCase?.serial_no || "—"}</span><span>{row.data.expense_subtype || row.data.fee_type || "—"}</span><span>{row.data.amount ?? 0}</span>
              <Input value={caseFeePaymentDrafts[index]?.payment_remark || ""} placeholder="付款备注" onChange={(event) => setCaseFeePaymentDrafts((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, payment_remark: event.target.value } : item))} />
              <Select showSearch optionFilterProp="label" loading={casePaymentTypesLoading} placeholder="输入关键字选择收款单位" options={casePaymentTypeSelectOptions} value={caseFeePaymentDrafts[index]?.payment_type_id} onSearch={setPaymentTypeSearch} onChange={(value) => setCaseFeePaymentDrafts((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, payment_type_id: value } : item))} notFoundContent={<Button type="link" icon={<PlusOutlined />} onClick={() => openPaymentTypeCreator(row.id, index)}>新增“{paymentTypeSearch || "付款单位"}”</Button>} />
              <Button type="text" title="新增付款单位" aria-label="新增付款单位" icon={<PlusOutlined />} onClick={() => openPaymentTypeCreator(row.id, index)} />
            </div>)}
          </div>}
        </>}
      </Drawer>
      <Drawer
        open={Boolean(caseCommissionPreview)}
        title="新增提成"
        placement="right"
        width={720}
        onClose={closeCaseCommission}
        destroyOnHidden
        className="case-commission-drawer"
        footer={<Space style={{ width: "100%", justifyContent: "flex-end" }}>
          <Button onClick={closeCaseCommission}>{caseCommissionResult ? "关闭" : "取消"}</Button>
          {!caseCommissionResult && <Button type="primary" loading={caseCommissionSubmitting} onClick={() => void submitCaseCommissions()}>申请付款</Button>}
        </Space>}
      >
        <Steps size="small" current={caseCommissionResult ? 1 : 0} items={[{ title: "新增提成" }, { title: "申请结果" }]} style={{ marginBottom: 16 }} />
        {caseCommissionResult ? <>
          <Alert type="success" showIcon title={`付款申请 ${caseCommissionResult.application_no} 已提交审批`} style={{ marginBottom: 12 }} />
          <Table
            rowKey="record_id"
            size="small"
            pagination={false}
            dataSource={caseCommissionResult.payment_items}
            columns={[
              { title: "申请单号", dataIndex: "application_no", width: 190 },
              { title: "收款人", dataIndex: "payee", width: 120 },
              { title: "提成类型", dataIndex: "commission_type", width: 150 },
              { title: "金额", dataIndex: "amount", width: 100, align: "right" },
              { title: "案号", dataIndex: "case_no", width: 150 },
              { title: "申请日期", dataIndex: "application_date", width: 120 },
            ]}
          />
        </> : <>
        <Alert
          className="case-fee-legacy-tip"
          type="info"
          title="温馨提示"
          description={<ol>
            <li>申请付款按照每个案号生成一个申请单。</li>
            <li>法院退费：{caseCommissionPreview?.source_fee.refund_amount ?? 0} 元。</li>
            <li>高开金额：{caseCommissionPreview?.source_fee.invoice_over_amount ?? 0} 元；高开成本：{caseCommissionPreview?.source_fee.cost_over_amount ?? 0} 元。</li>
            <li>提成基数取当前选中的代理费金额：{caseCommissionPreview?.source_fee.amount ?? 0} 元。</li>
            <li>人员及参考提成按案件日期有效的员工提成设置自动生成，实际金额可按业务调整。</li>
            <li>点击操作栏的加号可复制当前提成行；每一行单独生成一条内部提成记录。</li>
          </ol>}
        />
        {!!caseCommissionPreview?.missing_messages.length && <Alert
          type="warning"
          showIcon
          title="以下案件人员未配置对应提成"
          description={caseCommissionPreview.missing_messages.join("，")}
          style={{ marginBottom: 10 }}
        />}
        <Table<CaseCommissionPreviewRow>
          rowKey="client_key"
          size="small"
          pagination={false}
          scroll={{ x: 1030 }}
          locale={{ emptyText: caseCommissionLoading ? "正在读取案件人员提成设置..." : "没有可生成的提成项目" }}
          dataSource={caseCommissionRows}
          columns={[
            { title: "案号", dataIndex: "case_no", width: 145 },
            { title: "费用类型", dataIndex: "commission_type", width: 140 },
            { title: "支付对象", dataIndex: "employee_display_name", width: 120 },
            { title: "基数", dataIndex: "base_amount", width: 100, align: "right" },
            { title: "参考提成", dataIndex: "reference_commission", width: 110, align: "right" },
            { title: "实际金额", width: 120, render: (_, row) => <InputNumber
              min={0.01}
              precision={2}
              value={row.actual_amount}
              onChange={(value) => updateCaseCommissionRow(row.client_key, { actual_amount: Number(value || 0) })}
            /> },
            { title: "备注", width: 220, render: (_, row) => <Input
              value={row.remark}
              onChange={(event) => updateCaseCommissionRow(row.client_key, { remark: event.target.value })}
            /> },
            { title: "操作", width: 90, fixed: "right", render: (_, row) => <Space size={0}>
              <Button type="text" aria-label="新增提成行" icon={<PlusOutlined />} onClick={() => cloneCaseCommissionRow(row)} />
              <Button type="text" danger aria-label="删除提成行" icon={<CloseOutlined />} onClick={() => setCaseCommissionRows((rows) => rows.filter((item) => item.client_key !== row.client_key))} />
            </Space> },
          ]}
        />
        </>}
      </Drawer>
      <Modal
        open={Boolean(paymentPackagePreview)}
        title={`申请付款：${paymentPackagePreview?.source?.request_no || ""}`}
        okText="提交付款申请"
        cancelText="取消"
        confirmLoading={paymentPackageLoading}
        onOk={submitInternalPayment}
        onCancel={() => setPaymentPackagePreview(null)}
      >
        <Alert type="info" showIcon title="请确认付款申请来源与金额" style={{ marginBottom: 12 }} />
        <p>案件号：{paymentPackagePreview?.source?.case_no || "—"}</p>
        <p>客户：{paymentPackagePreview?.source?.customer || "—"}</p>
        <p>费用编号：{paymentPackagePreview?.source?.request_no || "—"}</p>
        <p>金额：{paymentPackagePreview?.total_amount ?? paymentPackagePreview?.source?.amount ?? "—"}</p>
        <p>付款包号：{paymentPackagePreview?.package_no || "—"}</p>
      </Modal>
      <Drawer
        open={Boolean(paymentRequestFee)}
        title="申请付款"
        width={860}
        className="case-fee-create-drawer case-fee-payment-request-drawer"
        onClose={() => { setPaymentRequestFee(null); paymentRequestForm.resetFields(); }}
        destroyOnClose
        footer={<Space className="case-fee-drawer-footer"><Button type="primary" onClick={submitPaymentRequest}>申请付款</Button><Button onClick={() => { setPaymentRequestFee(null); paymentRequestForm.resetFields(); }}>取消</Button></Space>}
      >
        <Steps size="small" current={1} items={[{ title: "新增费用" }, { title: "申请付款" }]} />
        <Alert className="case-fee-legacy-tip" type="info" title="温馨提示" description={paymentRequestFee?.data.expense_scope === "内部" ? <ol><li>同一收款单位可以申请付款，否则请按实际业务进行操作。</li><li>申请付款按照每个案号生成一个申请单。</li></ol> : <ol><li>同一收款单位可以申请付款，否则请按实际业务进行操作。</li><li>申请付款按照每个合同号生成一个申请单。</li><li>代理费不允许付款。</li></ol>} />
        <Form form={paymentRequestForm} component={false}>
          <div className="case-fee-payment-table case-fee-payment-request-table case-fee-payment-unit-table">
            <div className="case-fee-payment-head"><span>合同号</span><span>案号</span><span>费用类型</span><span>金额</span><span>付款备注</span><span>收款单位</span><span>操作</span></div>
            <div className="case-fee-payment-row">
              <span>{paymentRequestFee?.data.contract_no || "—"}</span>
              <span>{paymentRequestFee?.data.case_no || viewingCounselCase?.serial_no || "—"}</span>
              <span>{paymentRequestFee?.data.expense_subtype || paymentRequestFee?.data.fee_type || paymentRequestFee?.title || "—"}</span>
              <Form.Item name="amount" rules={[{ required: true, message: "请输入申请付款金额" }]}><InputNumber min={0.01} precision={2} style={{ width: "100%" }} /></Form.Item>
              <Form.Item name="payment_remark"><Input placeholder="付款备注" /></Form.Item>
              <Form.Item name="payment_type_id" rules={[{ required: true, message: "请选择系统付款单位" }]}><Select showSearch optionFilterProp="label" loading={casePaymentTypesLoading} placeholder="输入关键字选择收款单位" options={casePaymentTypeSelectOptions} onSearch={setPaymentTypeSearch} notFoundContent={<Button type="link" icon={<PlusOutlined />} onClick={() => paymentRequestFee && openPaymentTypeCreator(paymentRequestFee.id)}>新增“{paymentTypeSearch || "付款单位"}”</Button>} /></Form.Item>
              <Button type="text" title="新增付款单位" aria-label="新增付款单位" icon={<PlusOutlined />} onClick={() => paymentRequestFee && openPaymentTypeCreator(paymentRequestFee.id)} />
            </div>
          </div>
          {selectedCasePaymentType && <div className="case-payment-unit-summary">开户行：{selectedCasePaymentType.account_bank}　账号信息：{selectedCasePaymentType.account}</div>}
        </Form>
      </Drawer>
      <Modal
        open={Boolean(paymentTypeCreateTarget)}
        title="新增付款单位"
        okText="确定"
        cancelText="取消"
        confirmLoading={paymentTypeCreating}
        onOk={() => void createCasePaymentType()}
        onCancel={() => { setPaymentTypeCreateTarget(null); paymentTypeCreateForm.resetFields(); }}
        forceRender
      >
        <Form form={paymentTypeCreateForm} layout="vertical">
          <Form.Item label="性质" name="nature" rules={[{ required: true, message: "请选择付款性质" }]}><Select options={["官费", "其他费用", "代理费", "对公", "个人"].map((value) => ({ value, label: value }))} /></Form.Item>
          <Form.Item label="收款单位" name="payee" rules={[{ required: true, message: "请输入收款单位" }]}><Input /></Form.Item>
          <Form.Item label="开户行" name="account_bank" rules={[{ required: true, message: "请输入开户行" }]}><Input /></Form.Item>
          <Form.Item label="账号信息" name="account" rules={[{ required: true, message: "请输入账号信息" }]}><Input.TextArea rows={4} maxLength={1000} showCount /></Form.Item>
        </Form>
      </Modal>
      <Drawer
        open={Boolean(viewingCaseTask)}
        width={620}
        title="任务详情"
        onClose={closeCaseTaskDetail}
        destroyOnHidden
        footer={<Space>{viewingCaseTask && canWithdrawCaseTask(viewingCaseTask) && <Button danger onClick={() => withdrawCaseTask(viewingCaseTask)}>撤回任务</Button>}<Button onClick={closeCaseTaskDetail}>关闭</Button></Space>}
      >
        <div className="task-detail-flow" aria-label="任务流程">
          {["任务已分派", "任务处理中", "任务完成", "任务验收"].map((label, index) => {
            const statusIndex: Record<string, number> = { 待接收: 0, 待处理: 0, 进行中: 1, 处理中: 1, 已逾期: 1, 待确认: 2, 已完成: 2, 已验收: 3, 已撤回: 0, 已停止: 0, 已拒绝: 0 };
            const current = statusIndex[viewingCaseTask?.workflow_status || viewingCaseTask?.status || ""] ?? 0;
            return <span key={label} className={index <= current ? "active" : ""}>{label}</span>;
          })}
        </div>
        <div className="task-detail-meta">
          <span><b>任务标题：</b>{viewingCaseTask?.title || "—"}</span>
          <span><b>任务编号：</b>{viewingCaseTask?.serial_no || "—"}</span>
          <span><b>当前负责人：</b>{casePersonDisplayName(viewingCaseTask?.owner, viewingCaseTask?.owner_display_name)}</span>
          <span><b>发布人：</b>{casePersonDisplayName(viewingCaseTask?.initiator, viewingCaseTask?.initiator_display_name)}</span>
          <span><b>关联案号：</b>{viewingCaseTask?.case_no || "—"}</span>
          <span><b>开始时间：</b>{viewingCaseTask?.start_at ? new Date(viewingCaseTask.start_at).toLocaleString("zh-CN") : "—"}</span>
          <span><b>结束时间：</b>{viewingCaseTask?.end_at ? new Date(viewingCaseTask.end_at).toLocaleString("zh-CN") : viewingCaseTask?.deadline || "—"}</span>
          <span><b>状态：</b><Tag color={statusColors[viewingCaseTask?.status || ""] || "blue"}>{viewingCaseTask?.status || "—"}</Tag></span>
          <span><b>协作人：</b>{viewingCaseTask?.collaborator_display_names?.join("、") || casePersonDisplayNames(viewingCaseTask?.collaborators) || "—"}</span>
          <span><b>任务描述：</b>{viewingCaseTask?.description || "—"}</span>
        </div>
        <div className="task-detail-section-title">过程记录</div>
        <List
          className="task-history"
          loading={caseTaskDetailLoading}
          dataSource={[...caseTaskHistory].reverse()}
          locale={{ emptyText: "暂无过程记录" }}
          renderItem={(item) => <List.Item><List.Item.Meta title={<Space><Tag>{item.action}</Tag><b>{casePersonDisplayName(item.operator, item.operator_display_name)}</b><span>{new Date(item.created_at).toLocaleString("zh-CN")}</span></Space>} description={<><div>{item.from_status && item.to_status ? `${item.from_status} → ${item.to_status}` : item.to_status || ""}</div><p>{item.comment || "—"}</p></>} /></List.Item>}
        />
        <div className="task-detail-section-title">任务资料附件</div>
        <Table size="small" rowKey="id" pagination={false} dataSource={caseTaskDetailMaterials} locale={{ emptyText: "暂无任务资料附件" }} columns={[{ title: "文件名", dataIndex: "original_name", ellipsis: true }, { title: "上传人", width: 110, render: (_: unknown, item: CaseTaskAttachment) => casePersonDisplayName(item.uploader, item.uploader_display_name) }, { title: "操作", width: 80, render: (_: unknown, item: CaseTaskAttachment) => <Button type="link" icon={<DownloadOutlined />} onClick={() => void downloadCaseTaskAttachment(item)}>下载</Button> }]} />
        <div className="task-detail-section-title" style={{ marginTop: 12 }}>留言附件</div>
        <Table size="small" rowKey="id" pagination={false} dataSource={caseTaskDetailFeedbacks} locale={{ emptyText: "暂无留言附件" }} columns={[{ title: "文件名", dataIndex: "original_name", ellipsis: true }, { title: "上传人", width: 110, render: (_: unknown, item: CaseTaskAttachment) => casePersonDisplayName(item.uploader, item.uploader_display_name) }, { title: "操作", width: 80, render: (_: unknown, item: CaseTaskAttachment) => <Button type="link" icon={<DownloadOutlined />} onClick={() => void downloadCaseTaskAttachment(item)}>下载</Button> }]} />
        <div className="task-detail-section-title" style={{ marginTop: 12 }}>留言</div>
        <Input.TextArea rows={3} value={caseTaskFeedbackText} placeholder="请输入留言内容" onChange={(event) => setCaseTaskFeedbackText(event.target.value)} style={{ marginBottom: 8 }} />
        <Upload multiple fileList={caseTaskFeedbackFiles} beforeUpload={(file) => { setCaseTaskFeedbackFiles((items) => [...items, file]); return false; }} onRemove={(file) => setCaseTaskFeedbackFiles((items) => items.filter((item) => item.uid !== file.uid))}>
          <Button icon={<UploadOutlined />}>上传附件</Button>
        </Upload>
        <Button type="primary" icon={<CommentOutlined />} loading={caseTaskDetailLoading} onClick={() => void submitCaseTaskFeedback()} style={{ marginTop: 8 }}>提交留言</Button>
      </Drawer>
      <Drawer open={Boolean(caseTaskCreateCase)} width={620} title="案件任务" onClose={() => { setCaseTaskCreateCase(null); taskForm.resetFields(); setCaseTaskMaterialFiles([]); }} destroyOnHidden footer={<Space><Button type="primary" onClick={createCaseTask}>确定</Button><Button onClick={() => { setCaseTaskCreateCase(null); taskForm.resetFields(); setCaseTaskMaterialFiles([]); }}>取消</Button></Space>}>
        <Steps size="small" current={0} items={[{title:"任务填写"},{title:"任务分派"},{title:"任务处理"},{title:"任务完成"}]} style={{ marginBottom: 20 }} />
        <Form form={taskForm} layout="vertical">
          <Form.Item label="案件编号"><Input value={caseTaskCreateCase?.serial_no || ""} disabled /></Form.Item>
          <Form.Item label="任务主标题" name="title" rules={[{ required: true, message: "请输入任务主标题" }]}><Input placeholder="请输入任务主标题" /></Form.Item>
          <Form.Item label="优先级" name="priority"><Radio.Group options={[{value:"重要",label:"重要"},{value:"普通",label:"一般"}]} /></Form.Item>
          <Form.Item label="VIP任务" name="is_vip" valuePropName="checked"><Checkbox>标记为VIP任务</Checkbox></Form.Item>
          <div className="form-grid">
            <Form.Item label="负责人" name="owner" rules={[{ required: true, message: "请选择负责人" }]}><Select showSearch optionFilterProp="label" options={caseAssistantOptions} placeholder="输入中文姓名检索" /></Form.Item>
            <Form.Item label="协作人" name="collaborators"><Select mode="multiple" showSearch optionFilterProp="label" options={caseAssistantOptions} placeholder="输入中文姓名检索" /></Form.Item>
            <Form.Item label="任务开始时间" name="start_at" rules={[{ required: true, message: "请选择开始时间" }]}><DatePicker showTime={{format:"HH:mm"}} format="YYYY-MM-DD HH:mm" style={{ width: "100%" }} /></Form.Item>
            <Form.Item label="结束时间" name="end_at" rules={[{ required: true, message: "请选择结束时间" }]}><DatePicker showTime={{format:"HH:mm"}} format="YYYY-MM-DD HH:mm" style={{ width: "100%" }} /></Form.Item>
          </div>
          <Form.Item label="任务描述" name="description"><Input.TextArea rows={4} /></Form.Item>
          <Form.Item label="任务附件（可多选，单个不超过20MB）"><Upload multiple fileList={caseTaskMaterialFiles} beforeUpload={(file) => { setCaseTaskMaterialFiles((items) => [...items, file]); return false; }} onRemove={(file) => setCaseTaskMaterialFiles((items) => items.filter((item) => item.uid !== file.uid))}><Button icon={<UploadOutlined />}>上传附件</Button></Upload></Form.Item>
        </Form>
      </Drawer>
      <Modal
        open={Boolean(mergingCase)}
        title={`合并案件至：${mergingCase?.serial_no || ""}`}
        okText="确认合并"
        cancelText="取消"
        onCancel={() => { setMergingCase(null); mergeCaseForm.resetFields(); }}
        onOk={() => void submitCaseMerge()}
      >
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="仅可合并同一客户、同一案件类型且未归档的案件"
          description="将迁移待合并案件的案件费用、内部费用和案件文件；任务、提醒、开庭排期及历史记录不会迁移。待合并案件会保留为“已合并”以便审计回看。"
        />
        <Form form={mergeCaseForm} layout="vertical">
          <Form.Item label="待合并案件编号" name="source_case_no" rules={[{ required: true, message: "请输入待合并案件编号" }]}>
            <Input placeholder="输入同一客户下待合并的案件编号" />
          </Form.Item>
          <Form.Item label="合并说明" name="comment"><Input.TextArea rows={3} maxLength={1000} /></Form.Item>
        </Form>
      </Modal>
      <Modal
        open={assistedFeeModalOpen}
        title={assistedFeeEditor ? `修改资助费用：${assistedFeeEditor.assisted_type}` : "新建资助费用"}
        okText={assistedFeeEditor ? "保存修改" : "提交"}
        cancelText="取消"
        confirmLoading={assistedFeeSaving}
        onOk={() => void saveCounselDetailAssistedFee()}
        onCancel={() => { setAssistedFeeModalOpen(false); setAssistedFeeEditor(null); assistedFeeForm.resetFields(); }}
        destroyOnHidden
      >
        <Form form={assistedFeeForm} layout="vertical">
          <Form.Item label="资助类别" name="assisted_type" rules={[{required:true,whitespace:true,message:"请输入资助类别"},{max:128,message:"资助类别不能超过128个字符"}]}><Input maxLength={128} placeholder="例如：专利资助、商标资助" /></Form.Item>
          <Form.Item label="金额" name="amount"><InputNumber min={0} max={100000000} precision={2} style={{width:"100%"}} placeholder="未明确金额时可留空" /></Form.Item>
          <Form.Item label="说明" name="remark" rules={[{max:1000,message:"说明不能超过1000个字符"}]}><Input.TextArea rows={3} maxLength={1000} showCount /></Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(assistedFeeConfirming)}
        title={assistedFeeConfirming ? `办理确认：${assistedFeeConfirming.assisted_type}` : "办理确认"}
        okText="确认办理"
        cancelText="取消"
        confirmLoading={assistedFeeSaving}
        onOk={() => void confirmCounselDetailAssistedFee()}
        onCancel={() => { setAssistedFeeConfirming(null); assistedFeeConfirmForm.resetFields(); }}
        destroyOnHidden
      >
        <Form form={assistedFeeConfirmForm} layout="vertical">
          <Form.Item label="办理日期" name="confirmed_date" rules={[{required:true,message:"请选择办理日期"}]}><DatePicker style={{width:"100%"}} /></Form.Item>
          <Form.Item label="办理说明" name="remark" rules={[{max:1000,message:"办理说明不能超过1000个字符"}]}><Input.TextArea rows={3} maxLength={1000} showCount /></Form.Item>
        </Form>
      </Modal>
      <Drawer
        width="100%"
        rootClassName={isCaseDetailView ? "case-detail-static-root" : undefined}
        className="case-detail-drawer"
        getContainer={false}
        mask={false}
        rootStyle={{position:"absolute",inset:0,height:"calc(100vh - 88px)"}}
        open={Boolean(viewingCounselCase)}
        title={`${viewingCounselCase?.data.case_type || "案件"}详情：${viewingCounselCase?.serial_no || ""}`}
        onClose={() => isCaseDetailView ? returnToCaseList() : setViewingCounselCase(null)}
        extra={viewingCounselCase&&<Space wrap>
          {isCaseDetailView && <Button data-testid="case-detail-back" onClick={returnToCaseList}>返回案件列表</Button>}
          <Button type="primary" icon={<RobotOutlined />} onClick={() => openCaseAgent(viewingCounselCase)}>案件智能体</Button>
          <Dropdown
            trigger={["click"]}
            placement="bottomRight"
            data-testid="case-detail-operation-menu"
            dropdownRender={() => caseDetailPrimaryActionButtons}
          >
            <Button>操作</Button>
          </Dropdown>
        </Space>}
      >
        {viewingCounselCase&&<div className="case-detail-workbench">
          <CaseDetailHeader
            viewingCase={viewingCounselCase}
            casePersonDisplayName={casePersonDisplayName}
            casePersonDisplayNames={casePersonDisplayNames}
            caseAssistantDisplayNames={caseAssistantDisplayNames}
            renderCaseLitigantAgentSummary={renderCaseLitigantAgentSummary}
            caseDetailDate={caseDetailDate}
            caseDetailNames={caseDetailNames}
            legacyCaseParticipantDisplayNames={legacyCaseParticipantDisplayNames}
            openRelatedCustomer={openRelatedCustomer}
            openRelatedContract={openRelatedContract}
            openRelatedClue={openRelatedClue}
            openRelatedOriginalCase={openRelatedOriginalCase}
            isCaseDetailView={isCaseDetailView}
            returnToCaseList={returnToCaseList}
          />
          <div className="case-detail-body-grid">
            <div className="case-detail-tab-area">
          <Tabs
            activeKey={activeCounselDetailTab}
            onChange={(key) => {
              setActiveCounselDetailTab(key);
              if (key === "tasks" && viewingCounselCase) {
                void loadCounselDetailTasksPage(viewingCounselCase, CASE_TASK_DEFAULT_PAGE, CASE_TASK_DEFAULT_PAGE_SIZE);
              }
              if (key === "customer-tasks" && viewingCounselCase) {
                void loadCounselDetailCustomerTasksPage(viewingCounselCase, CASE_TASK_DEFAULT_PAGE, CASE_TASK_DEFAULT_PAGE_SIZE);
              }
              if (key === "clues" && viewingCounselCase) {
                void loadCounselDetailCluesPage(viewingCounselCase, 1, counselDetailCluePageSize, counselDetailClueKeyword)
                  .catch((error: any) => message.error(error?.response?.data?.detail || "关联线索加载失败"));
              }
            }}
            items={[
              ...(legacyLsHistoryCaseIds[viewingCounselCase.id] ? [{ key: "legacy-ls-history", label: "历史诉讼", children: <LegacyLsHistoryPanel initialCaseId={legacyLsHistoryCaseIds[viewingCounselCase.id]} currentCaseRecordId={viewingCounselCase.id} /> }] : []),
              {key:"documents",label:"文档信息",children:<CaseDocumentsPanel
                viewingCase={viewingCounselCase}
                counselDocTree={counselDocTree}
                expandedCounselDocGroups={expandedCounselDocGroups}
                activeCounselDocCategory={activeCounselDocCategory}
                activeCounselDocLabel={activeCounselDocLabel}
                isAiSpaceFolder={isAiSpaceFolder}
                toggleCounselDocGroup={toggleCounselDocGroup}
                selectCounselDocCategory={selectCounselDocCategory}
                counselDetailCapabilities={counselDetailCapabilities}
                openCaseDocumentFolderEditor={openCaseDocumentFolderEditor}
                deleteCaseDocumentFolder={deleteCaseDocumentFolder}
                counselDetailUploadRef={counselDetailUploadRef}
                uploadCounselDetailAttachment={uploadCounselDetailAttachment}
                filteredCounselDetailAttachments={filteredCounselDetailAttachments}
                selectedCounselAttachmentKeys={selectedCounselAttachmentKeys}
                setSelectedCounselAttachmentKeys={setSelectedCounselAttachmentKeys}
                getCaseFilePagination={getCaseFilePagination}
                previewCounselDetailAttachment={previewCounselDetailAttachment}
                downloadCounselDetailAttachment={downloadCounselDetailAttachment}
                openEditAiDraft={openEditAiDraft}
                openCaseWordEditor={openCaseWordEditor}
                openCounselAttachmentRename={openCounselAttachmentRename}
                openPromoteAiDraft={openPromoteAiDraft}
                deleteAiDraft={deleteAiDraft}
                unlockCounselDetailAttachment={unlockCounselDetailAttachment}
                canApplySealToCounselAttachment={canApplySealToCounselAttachment}
                openCounselAttachmentSeal={openCounselAttachmentSeal}
                caseDocumentGenerationError={caseDocumentGenerationError}
                setCaseDocumentGenerationError={setCaseDocumentGenerationError}
                counselUploadCategory={counselUploadCategory}
                setCounselUploadCategory={setCounselUploadCategory}
                activeCounselUploadCategoryOptions={activeCounselUploadCategoryOptions}
                openCreateAiDraft={openCreateAiDraft}
                caseDocumentGenerationMenuOpen={caseDocumentGenerationMenuOpen}
                setCaseDocumentGenerationMenuOpen={setCaseDocumentGenerationMenuOpen}
                generatingCaseDocumentType={generatingCaseDocumentType}
                generateCaseDocument={generateCaseDocument}
                handleCounselDocumentMoreAction={handleCounselDocumentMoreAction}
                canApplySealToSelectedCounselDocument={canApplySealToSelectedCounselDocument}
              />},
              {key:"firm-fees",label:"律所费用",children:<CaseFeesPanel
                scope="firm"
                feeRows={firmFeeRows}
                selectedFeeKeys={selectedFirmFeeKeys}
                setSelectedFeeKeys={setSelectedFirmFeeKeys}
                selectedFee={selectedFirmFee}
                counselDetailCapabilities={counselDetailCapabilities}
                externalCaseFeeColumns={externalCaseFeeColumns}
                casePersonDisplayName={casePersonDisplayName}
                renderCaseFeeEmptyState={renderCaseFeeEmptyState}
                openCaseFeeBySubtype={openCaseFeeBySubtype}
                openCourtRefund={openCourtRefund}
                requireSingleFee={requireSingleFee}
                handleExternalFeeOperation={handleExternalFeeOperation}
                openCaseCommission={openCaseCommission}
                canMarkCaseFeeRefundNotRequired={canMarkCaseFeeRefundNotRequired}
                editCaseFee={editCaseFee}
                deleteCaseFee={deleteCaseFee}
                handleInternalFeeAction={handleInternalFeeAction}
                openInformDateBatchUpdate={openInformDateBatchUpdate}
              />},
              {key:"platform-fees",label:"平台费用",children:<CaseFeesPanel
                scope="platform"
                feeRows={platformFeeRows}
                selectedFeeKeys={selectedPlatformFeeKeys}
                setSelectedFeeKeys={setSelectedPlatformFeeKeys}
                selectedFee={selectedPlatformFee}
                counselDetailCapabilities={counselDetailCapabilities}
                externalCaseFeeColumns={externalCaseFeeColumns}
                casePersonDisplayName={casePersonDisplayName}
                renderCaseFeeEmptyState={renderCaseFeeEmptyState}
                openCaseFeeBySubtype={openCaseFeeBySubtype}
                openCourtRefund={openCourtRefund}
                requireSingleFee={requireSingleFee}
                handleExternalFeeOperation={handleExternalFeeOperation}
                openCaseCommission={openCaseCommission}
                canMarkCaseFeeRefundNotRequired={canMarkCaseFeeRefundNotRequired}
                editCaseFee={editCaseFee}
                deleteCaseFee={deleteCaseFee}
                handleInternalFeeAction={handleInternalFeeAction}
                openInformDateBatchUpdate={openInformDateBatchUpdate}
              />},
              {key:"internal-fees",label:"内部结算",children:<CaseFeesPanel
                scope="internal"
                feeRows={internalFeeRows}
                selectedFeeKeys={selectedInternalFeeKeys}
                setSelectedFeeKeys={setSelectedInternalFeeKeys}
                selectedFee={selectedInternalFee}
                counselDetailCapabilities={counselDetailCapabilities}
                casePersonDisplayName={casePersonDisplayName}
                editCaseFee={editCaseFee}
                deleteCaseFee={deleteCaseFee}
                handleInternalFeeAction={handleInternalFeeAction}
                openInformDateBatchUpdate={openInformDateBatchUpdate}
              />},
              {key:"assisted-fees",label:"资助费用",children:<CaseAssistedFeesPanel
                assistedFees={counselDetailAssistedFees}
                assistedFeePage={counselDetailAssistedFeePage}
                assistedFeePageSize={counselDetailAssistedFeePageSize}
                assistedFeeTotal={counselDetailAssistedFeeTotal}
                capabilities={counselDetailCapabilities}
                caseId={viewingCounselCase?.id}
                onRefresh={loadCounselDetailAssistedFees}
                onPageChange={loadCounselDetailAssistedFees}
                casePersonDisplayName={casePersonDisplayName}
                onCreateClick={() => { assistedFeeForm.resetFields(); setAssistedFeeEditor(null); setAssistedFeeModalOpen(true); }}
                onEditClick={(row) => { assistedFeeForm.setFieldsValue({assisted_type:row.assisted_type,amount:row.amount ?? undefined,remark:row.remark}); setAssistedFeeEditor(row); setAssistedFeeModalOpen(true); }}
                onConfirmClick={(row) => { assistedFeeConfirmForm.setFieldsValue({confirmed_date:dayjs(),remark:""}); setAssistedFeeConfirming(row); }}
                onDeleteClick={deleteCounselDetailAssistedFee}
              />},
              {key:"case-events",label:"案件事件",children:<CaseEventsPanel
                casePersonDisplayName={casePersonDisplayName}
                events={counselCaseEvents}
                selectedKeys={selectedCounselCaseEventKeys}
                setSelectedKeys={setSelectedCounselCaseEventKeys}
                capabilities={counselCaseEventCapabilities}
                submitting={caseEventSubmitting}
                error={counselCaseEventsError}
                onRefresh={loadCounselCaseEvents}
                onCreate={() => openCaseEventEditor()}
                onEdit={(row) => openCaseEventEditor(row)}
                onDelete={deleteCounselCaseEvent}
                onBatchDelete={deleteCounselCaseEvents}
              />},
              {key:"reminders",label:"案件提醒",children:<CaseRemindersPanel
                reminders={counselReminders}
                capabilities={counselDetailCapabilities}
                casePersonDisplayName={casePersonDisplayName}
                onCreate={() => { reminderForm.resetFields(); setReminderOpen(true); }}
                onDelete={deleteCounselReminder}
              />},
              {key:"case-logs",label:"案件日志",children:<CaseCaseLogsPanel
                logs={counselLogs}
                capabilities={counselDetailCapabilities}
                casePersonDisplayName={casePersonDisplayName}
                onCreateLog={openCounselLogCreator}
              />},
              {key:"logs",label:"系统日志",children:<CaseSystemLogsPanel
                logs={counselDetailHistory}
                capabilities={counselDetailCapabilities}
                casePersonDisplayName={casePersonDisplayName}
                onCreateLog={openCounselLogCreator}
              />},
              {key:"tasks",label:"案件任务",children:<CaseCaseTasksPanel
                tasks={counselDetailTasks}
                pagination={counselDetailTaskPagination}
                vipFilter={counselDetailTaskVipFilter}
                setVipFilter={setCounselDetailTaskVipFilter}
                capabilities={counselDetailCapabilities}
                viewingCase={viewingCounselCase}
                casePersonDisplayName={casePersonDisplayName}
                onVipFilterChange={loadCounselDetailTasksPage}
                taskPageSize={counselDetailTaskPageSize}
                onOpenTask={openRelatedTask}
                onCreateTask={openCaseTaskCreator}
              />},
              {key:"customer-tasks",label:"客户任务",children:<CaseCustomerTasksPanel
                tasks={counselDetailCustomerTasks}
                pagination={counselDetailCustomerTaskPagination}
                vipFilter={counselDetailCustomerTaskVipFilter}
                setVipFilter={setCounselDetailCustomerTaskVipFilter}
                viewingCase={viewingCounselCase}
                casePersonDisplayName={casePersonDisplayName}
                onVipFilterChange={loadCounselDetailCustomerTasksPage}
                taskPageSize={counselDetailCustomerTaskPageSize}
                onOpenTask={openRelatedTask}
              />},
              {key:"clues",label:"线索信息",children:<CaseCluesPanel
                clues={counselDetailClues}
                pagination={counselDetailCluePagination}
                loading={counselDetailClueLoading}
                searchInput={counselDetailClueSearchInput}
                setSearchInput={setCounselDetailClueSearchInput}
                clueKeyword={counselDetailClueKeyword}
                setClueKeyword={setCounselDetailClueKeyword}
                cluePage={counselDetailCluePage}
                cluePageSize={counselDetailCluePageSize}
                capabilities={counselDetailCapabilities}
                viewingCase={viewingCounselCase}
                onSearch={loadCounselDetailCluesPage}
                onRefresh={loadCounselDetailCluesPage}
                onOpenClue={openRelatedClue}
                onOpenClueWorkspace={openCaseClueWorkspace}
                onCreateTask={openCaseTaskCreator}
              />},
            ]}
          />
            </div>
            <aside className="case-detail-side-panel">
              <section>
                <div className="case-detail-side-title"><span>案件提醒</span>{counselDetailCapabilities.can_create_reminder && <Button type="link" size="small" icon={<PlusOutlined />} onClick={()=>{reminderForm.resetFields();setReminderOpen(true);}}>新增提醒</Button>}</div>
                {counselReminders.length?counselReminders.slice(0,5).map((item)=><p key={item.id}>{item.data.reminder_date || item.data.deadline}　{item.description}</p>):<p className="case-detail-empty">暂无提醒</p>}
              </section>
              <section>
                <div className="case-detail-side-title"><span>案件日志</span>{counselDetailCapabilities.can_create_log && <Space size={0}><Button type="link" size="small" icon={<PlusOutlined />} onClick={()=>openCounselLogCreator("case")}>新增日志</Button><Button type="link" size="small" onClick={()=>openCounselLogCreator("refund")}>退费日志</Button></Space>}</div>
                {counselLogs.length?counselLogs.slice(0,5).map((item)=><p key={item.id}>{item.created_at}　{item.content}</p>):<p className="case-detail-empty">暂无日志</p>}
              </section>
            </aside>
          </div>
          {renderCaseClueWorkspace()}
        </div>}
      </Drawer>
      <Drawer
        width="min(1280px, 96vw)"
        open={legacyLsHistoryOpen}
        title="历史诉讼案件（只读）"
        onClose={() => setLegacyLsHistoryOpen(false)}
        destroyOnHidden
      >
        <LegacyLsHistoryPanel />
      </Drawer>
      <CaseAgentDrawer
        agentOpen={agentOpen}
        agentCase={agentCase}
        agentDrawerWidth={agentDrawerWidth}
        agentStatus={agentStatus}
        agentLoading={agentLoading}
        agentSending={agentSending}
        agentSkillId={agentSkillId}
        agentState={agentState}
        agentDecisionLoading={agentDecisionLoading}
        counselDetailCapabilities={counselDetailCapabilities}
        agentHistoryExpanded={agentHistoryExpanded}
        agentMaterialPickerOpen={agentMaterialPickerOpen}
        agentDocuments={agentDocuments}
        agentDocumentIds={agentDocumentIds}
        agentScreenshots={agentScreenshots}
        agentScreenshotUploading={agentScreenshotUploading}
        agentInput={agentInput}
        agentMessagesEndRef={agentMessagesEndRef}
        agentScreenshotInputRef={agentScreenshotInputRef}
        setAgentOpen={setAgentOpen}
        startAgentDrawerResize={startAgentDrawerResize}
        setAgentSkillId={setAgentSkillId}
        loadCaseAgent={loadCaseAgent}
        decideCaseAgentAction={decideCaseAgentAction}
        setAgentHistoryExpanded={setAgentHistoryExpanded}
        sendCaseAgentMessage={sendCaseAgentMessage}
        setAgentMaterialPickerOpen={setAgentMaterialPickerOpen}
        setAgentDocumentIds={setAgentDocumentIds}
        updateAgentDocumentSelection={updateAgentDocumentSelection}
        removeAgentScreenshot={removeAgentScreenshot}
        uploadCaseAgentScreenshot={uploadCaseAgentScreenshot}
        setAgentInput={setAgentInput}
        pasteCaseAgentScreenshot={pasteCaseAgentScreenshot}
        stopCaseAgentResponse={stopCaseAgentResponse}
      />
      <Modal
        open={Boolean(attachmentPreview)}
        title={`在线查看：${attachmentPreview?.name || ""}`}
        footer={<Button onClick={closeAttachmentPreview}>关闭</Button>}
        onCancel={closeAttachmentPreview}
        width={attachmentPreview?.kind === "pdf" ? 1000 : 760}
        destroyOnHidden
      >
        <AttachmentPreviewContent preview={attachmentPreview} pdfContent={attachmentPreview?.kind === "pdf" && <div>
          <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 12, marginBottom: 12 }}>
            <Button disabled={attachmentPreviewLoading || (attachmentPreview.page || 1) <= 1} onClick={() => void loadAttachmentPdfPage((attachmentPreview.page || 1) - 1)}>上一页</Button>
            <span>第 {attachmentPreview.page || 1} / {attachmentPreview.pageCount || 1} 页</span>
            <Button disabled={attachmentPreviewLoading || (attachmentPreview.page || 1) >= (attachmentPreview.pageCount || 1)} onClick={() => void loadAttachmentPdfPage((attachmentPreview.page || 1) + 1)}>下一页</Button>
          </div>
          <div style={{ height: "66vh", overflow: "auto", background: "#f0f2f5", padding: 12, textAlign: "center" }}>
            <img src={attachmentPreview.url} alt={`${attachmentPreview.name} 第 ${attachmentPreview.page || 1} 页`} style={{ display: "inline-block", maxWidth: "100%", background: "#fff", boxShadow: "0 1px 4px rgba(0,0,0,.18)" }} />
          </div>
        </div>} />

      </Modal>
      <Modal open={Boolean(caseDocumentFolderEditor)} title={caseDocumentFolderEditor?.mode==="rename"?"重命名案件文档目录":"新增案件文档目录"} okText="保存" cancelText="取消" onOk={saveCaseDocumentFolder} onCancel={()=>{setCaseDocumentFolderEditor(null);caseDocumentFolderForm.resetFields();}}>
        <Form form={caseDocumentFolderForm} layout="vertical"><Form.Item label="目录名称" name="name" rules={[{required:true,message:"请输入目录名称"},{max:64,message:"目录名称不能超过 64 个字符"},{validator:async(_rule,value)=>{const name=String(value||"").trim();if(!name||/[\\/]/.test(name))throw new Error("目录名称不能为空且不能包含路径字符");}}]}><Input autoFocus placeholder="请输入当前案件的自定义目录名称" /></Form.Item></Form>
      </Modal>
      <Modal open={Boolean(movingCounselAttachmentIds)} title={`更改文档目录（已选 ${movingCounselAttachmentIds?.length || 0} 个文件）`} okText="移动" cancelText="取消" onOk={moveCounselAttachments} onCancel={()=>{setMovingCounselAttachmentIds(null);caseAttachmentMoveForm.resetFields();}}>
        <Form form={caseAttachmentMoveForm} layout="vertical">
          <Form.Item label="目标目录" name="category" rules={[{required:true,message:"请选择目标目录"}]}><Select placeholder="请选择案件文档目录" options={counselMoveCategoryOptions}/></Form.Item>
          <Alert type="info" showIcon title="只更改当前案件内文件的所属目录，不修改文件内容。" />
        </Form>
      </Modal>
      <Modal open={Boolean(renamingCounselAttachment)} title={`重命名案件文件：${renamingCounselAttachment?.original_name || ""}`} okText="保存" cancelText="取消" onOk={renameCounselAttachment} onCancel={()=>{setRenamingCounselAttachment(null);attachmentRenameForm.resetFields();}}>
        <Form form={attachmentRenameForm} layout="vertical">
          <Form.Item label="文件名称" name="original_name" rules={[{required:true,message:"请输入文件名称"},{max:255,message:"文件名称不能超过 255 个字符"},{validator:async(_rule,value)=>{const name=String(value||"").trim();if(!name||/[\\\\/]/.test(name))throw new Error("文件名不能为空且不能包含路径");}}]}><Input autoFocus /></Form.Item>
          <Alert type="info" showIcon title="仅修改展示和下载文件名，不会移动或改写原文件内容；保存后会写入案件审计日志。"/>
        </Form>
      </Modal>
      <Modal width={820} open={Boolean(aiDraftEditor)} title={aiDraftEditor?.mode==="create"?"新建 AI 空间 Word 文档":"编辑 AI 空间 Word 文档"} okText="保存 Word 文档" cancelText="取消" onOk={saveAiDraft} onCancel={()=>{setAiDraftEditor(null);aiDraftForm.resetFields();}}>
        <Alert style={{marginBottom:12}} type="info" showIcon title="AI空间是案件草稿箱" description="AI生成文件默认保存在这里；只有点击“转入正式系统”后，文件才进入正式案件文档目录。"/>
        <Form form={aiDraftForm} layout="vertical">
          <Form.Item label="Word 文件名" name="name" rules={[{required:true,message:"请输入文件名"},{pattern:/\.(docx|md|txt)$/i,message:"新建 Word 文档请使用 .docx 格式"}]}><Input maxLength={255} disabled={aiDraftEditor?.mode==="edit"}/></Form.Item>
          <Form.Item label="文档正文" name="content"><Input.TextArea autoSize={{minRows:16,maxRows:28}} placeholder="在这里编辑 Word 文档正文；保存后可查看、下载或转入正式系统"/></Form.Item>
        </Form>
      </Modal>
      <Modal
        width={920}
        open={Boolean(wordEditor)}
        title={`在线编辑 Word：${wordEditor?.item.original_name || ""}`}
        okText="保存回案件文件"
        cancelText="关闭"
        confirmLoading={wordEditorSaving}
        maskClosable={false}
        keyboard={false}
        onOk={() => void saveCaseWordEditor()}
        onCancel={requestCloseCaseWordEditor}
        destroyOnHidden
      >
        <Alert
          style={{ marginBottom: 12 }}
          type="info"
          showIcon
          title="正在编辑原案件 Word 文件"
          description={`支持正文与表格文字；修改的段落沿用该段首文字样式，图片、域、超链接等复杂内容只读。${wordEditor?.expiresAt ? ` 当前编辑锁有效至 ${wordEditor.expiresAt}，页面会自动续期。` : ""}`}
        />
        {wordEditorLockLost && <Alert
          style={{ marginBottom: 12 }}
          type="error"
          showIcon
          title="编辑锁已失效"
          description="当前修改仍保留在此页面。请先复制未保存内容，关闭后重新打开文件以获取新的编辑锁。"
        />}
        {wordEditor?.blocks.map((block, index) => (
          <Form.Item key={block.id} label={wordEditor.blocks.length > 1 ? `文档内容 ${index + 1}` : "文档正文"} extra={!block.editable ? block.readOnlyReason || "此处包含不支持的 Word 内容，已设为只读以保护原文件。" : undefined}>
            <Input.TextArea
              value={block.text}
              disabled={wordEditorSaving || !block.editable}
              autoSize={{ minRows: index === 0 ? 16 : 4, maxRows: 28 }}
              onChange={(event) => setWordEditor((current) => current ? {
                ...current,
                blocks: current.blocks.map((currentBlock) => currentBlock.id === block.id ? { ...currentBlock, text: event.target.value } : currentBlock),
              } : current)}
              placeholder="在此修改 Word 正文；保存后将写回原案件文件"
            />
          </Form.Item>
        ))}
        <Alert type="warning" showIcon title="旧版 .doc 文件不支持在线编辑" description="请先转换为 .docx 后重新上传或替换，再使用本入口编辑。" />
      </Modal>
      <Modal open={Boolean(promotingAiDraft)} title={`转入正式系统：${promotingAiDraft?.original_name || ""}`} okText="确认转入" cancelText="取消" onOk={promoteAiDraft} onCancel={()=>{setPromotingAiDraft(null);aiDraftPromoteForm.resetFields();}}>
        <Alert style={{marginBottom:12}} type="warning" showIcon title="转入后将成为正式案件文件" description="该文件会从 AI 空间移出，并进入所选正式目录；操作将写入案件日志。"/>
        <Form form={aiDraftPromoteForm} layout="vertical">
          <Form.Item label="正式案件文档目录" name="category" rules={[{required:true,message:"请选择正式目录"}]}><Select showSearch optionFilterProp="label" loading={aiDraftPromoteOptionsLoading} options={aiDraftPromoteOptions}/></Form.Item>
        </Form>
      </Modal>
      <Modal width={720} open={Boolean(sealingCounselAttachment)} title="用印申请" okText="提交用印申请" cancelText="取消" onOk={submitCounselAttachmentSeal} onCancel={()=>{setSealingCounselAttachment(null);caseFileSealForm.resetFields();}} destroyOnHidden>
        <Alert type="info" showIcon message="案件用印" description="已带入当前案件、客户、合同和所选案件文件；申请仍在当前案件页面完成。" style={{ marginBottom: 12 }} />
        <Form form={caseFileSealForm} layout="vertical">
          <div className="form-grid">
            <Form.Item label="用印类型" name="use_type"><Input disabled /></Form.Item>
            <Form.Item label="案件号" name="case_no"><Input disabled /></Form.Item>
            <Form.Item label="合同号" name="contract_no"><Input disabled /></Form.Item>
            <Form.Item label="客户名称" name="customer"><Input disabled /></Form.Item>
          </div>
          <Form.Item label="申请标题" name="title" rules={[{ required: true, message: "请输入申请标题" }]}><Input maxLength={255} /></Form.Item>
          <div className="form-grid">
            <Form.Item label="选择印章" name="seal_asset_id" rules={[{ required: true, message: "请选择可用印章" }]}><Select placeholder="请选择可用印章" options={caseSealAssets.map((asset) => ({ value: asset.id, label: `${asset.name}（${asset.seal_type}）` }))} /></Form.Item>
            <Form.Item label="计划用印日期" name="use_date" rules={[{ required: true, message: "请选择计划用印日期" }]}><DatePicker style={{ width: "100%" }} /></Form.Item>
            <Form.Item label="用印份数" name="copies" rules={[{ required: true }]}><InputNumber min={1} max={999} style={{ width: "100%" }} /></Form.Item>
            <Form.Item label="办理方式" name="delivery_method"><Select options={["现场用印", "邮寄用印", "外带用印"].map((value) => ({ value, label: value }))} /></Form.Item>
            <Form.Item label="是否电子印章" name="is_electronic_seal"><Select options={[{ value: true, label: "是" }, { value: false, label: "否" }]} /></Form.Item>
            <Form.Item label="是否打印盖章" name="is_offline_print"><Select options={[{ value: true, label: "需要" }, { value: false, label: "不需要" }]} /></Form.Item>
          </div>
          <Form.Item label="用印事由" name="purpose" rules={[{ required: true, message: "请输入用印事由" }]}><Input maxLength={500} /></Form.Item>
          <Form.Item label="用印备注" name="remark" rules={[{ max: 2000 }]}><Input.TextArea rows={3} maxLength={2000} showCount /></Form.Item>
          <Form.Item label="附件"><Input value={sealingCounselAttachment?.original_name || ""} disabled /></Form.Item>
        </Form>
      </Modal>
      <Modal
        open={informDateFeeKeys!==null}
        title={`修改通知日期（已选 ${informDateFeeKeys?.length||0} 条）`}
        okText="确定"
        cancelText="取消"
        onOk={submitInformDateBatchUpdate}
        onCancel={()=>{setInformDateFeeKeys(null);informDateForm.resetFields();}}
      >
        <Form form={informDateForm} layout="vertical">
          <Form.Item label="通知日期" name="inform_date" rules={[{required:true,message:"请选择通知日期"}]}>
            <DatePicker style={{width:"100%"}} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal open={reminderOpen} title={`新增案件提醒：${viewingCounselCase?.serial_no||""}`} okText="确定" cancelText="取消" onOk={createCounselReminder} onCancel={()=>setReminderOpen(false)}>
        <Form form={reminderForm} layout="vertical">
          <div className="form-grid"><Form.Item label="提醒日期" name="reminder_date" rules={[{required:true,message:"请选择提醒日期"}]}><DatePicker style={{width:"100%"}}/></Form.Item><Form.Item label="截止日期" name="deadline" rules={[{required:true,message:"请选择截止日期"}]}><DatePicker style={{width:"100%"}}/></Form.Item></div>
          <Form.Item label="提醒内容" name="content" rules={[{required:true,message:"请输入提醒内容"},{max:1000}]}><Input.TextArea rows={4}/></Form.Item>
          <Alert type="info" showIcon title="提醒日期不能晚于截止日期；保存和删除都会写入案件审计记录。"/>
        </Form>
      </Modal>
      <Modal width={680} open={caseEventOpen} title={`${editingCaseEvent ? "编辑" : "新增"}案件事件：${viewingCounselCase?.serial_no || ""}`} okText={editingCaseEvent ? "保存修改" : "创建事件"} cancelText="取消" confirmLoading={caseEventSubmitting} cancelButtonProps={{disabled:caseEventSubmitting}} onOk={saveCaseEvent} onCancel={()=>{setCaseEventOpen(false);setEditingCaseEvent(null);caseEventForm.resetFields();}} destroyOnHidden>
        <Form form={caseEventForm} layout="vertical">
          <div className="form-grid">
            <Form.Item label="事件类型" name="event_type" rules={[{required:true,message:"请输入事件类型"},{max:100}]}><Input placeholder="例如：举证期限、答辩期限" maxLength={100}/></Form.Item>
            <Form.Item label="事件时间" name="event_time" rules={[{required:true,message:"请选择事件时间"}]}><DatePicker showTime={{format:"HH:mm"}} format="YYYY-MM-DD HH:mm" style={{width:"100%"}}/></Form.Item>
            <Form.Item label="截止日期" name="deadline"><DatePicker style={{width:"100%"}}/></Form.Item>
            {editingCaseEvent && <Form.Item label="事件状态" name="status" rules={[{required:true}]}><Select options={[{value:"待处理",label:"待处理"},{value:"已完成",label:"已完成"}]}/></Form.Item>}
          </div>
          <Form.Item label="事件内容" name="content" rules={[{required:true,message:"请输入事件内容"},{max:2000}]}><Input.TextArea rows={4} maxLength={2000} showCount/></Form.Item>
          <Form.Item name="reminder_enabled" valuePropName="checked"><Checkbox>启用提醒</Checkbox></Form.Item>
          <Form.Item noStyle shouldUpdate={(previous, current) => previous.reminder_enabled !== current.reminder_enabled}>{({getFieldValue})=><Form.Item label="提醒时间" name="remind_at"><DatePicker disabled={!getFieldValue("reminder_enabled")} showTime={{format:"HH:mm"}} format="YYYY-MM-DD HH:mm" style={{width:"100%"}} placeholder="启用提醒后可设置"/></Form.Item>}</Form.Item>
          <Alert type="info" showIcon title="已逾期状态由系统根据未完成事件和截止日期自动计算；创建、修改和删除均会写入案件操作日志。"/>
        </Form>
      </Modal>
      <Modal open={caseLogOpen} title={`${caseLogKind === "refund" ? "新增退费日志" : "新增案件日志"}：${caseLogTarget?.serial_no || viewingCounselCase?.serial_no||""}`} okText="确定" cancelText="取消" onOk={createCounselLog} onCancel={()=>{setCaseLogOpen(false);setCaseLogTarget(null);}}>
        <Form form={caseLogForm} layout="vertical"><Form.Item label="日志内容" name="content" rules={[{required:true,message:"请输入日志内容"},{max:1000}]}><Input.TextArea rows={5}/></Form.Item></Form>
      </Modal>
      <Modal width={680} open={batchUpdateOpen} title={`批量修改案件（已选 ${selectedCaseKeys.length} 个）`} okText="确定" cancelText="取消" onOk={submitCounselBatchUpdate} onCancel={()=>setBatchUpdateOpen(false)}>
        <Alert type="warning" showIcon title="只填写需要统一修改的字段；未填写字段保持原值。已进入归档流程的案件会被整体阻断。" style={{marginBottom:12}}/>
        <Form form={batchUpdateForm} layout="vertical">
          <Form.Item label="开庭律师" name="hearing_lawyer"><Input placeholder="不修改则留空" /></Form.Item>
          <Form.Item label="经办律师" name="handling_lawyers"><Select mode="multiple" showSearch optionFilterProp="label" options={caseLawyerOptions} placeholder="不修改则留空"/></Form.Item>
          <div className="form-grid"><Form.Item label="律师助理" name="assistant"><Select allowClear showSearch optionFilterProp="label" options={caseAssistantOptions} placeholder="不修改则留空"/></Form.Item><Form.Item label="案件阶段" name="case_stage"><Input placeholder="不修改则留空"/></Form.Item></div>
          <Form.Item label="修改说明" name="comment"><Input.TextArea rows={3}/></Form.Item>
        </Form>
      </Modal>
      <Modal width={680} open={batchFeeOpen} title={`批量新增案件费用（已选 ${selectedCaseKeys.length} 个）`} okText="创建费用草稿" cancelText="取消" onOk={submitCounselBatchFee} onCancel={()=>setBatchFeeOpen(false)}>
        <Alert type="info" showIcon title="系统会为每个案件分别创建一条费用草稿，并分别写入案件与费用审计记录。" style={{marginBottom:12}}/>
        <Form form={batchFeeForm} layout="vertical">
          <div className="form-grid">
            <Form.Item label="关联材料类型" name="source_file_type" rules={caseRelations ? [{required:true,message:"请选择关联材料类型"}] : []}><Select allowClear options={batchFeeSourceFileTypeOptions} onChange={()=>batchFeeForm.setFieldsValue({fee_type_id:undefined,expense_subtype:undefined})}/></Form.Item>
            <Form.Item label="费用归属" name="expense_scope" rules={[{required:true}]}><Select options={["律所","平台","内部"].map(value=>({value,label:value}))} onChange={()=>batchFeeForm.setFieldsValue({fee_type_id:undefined,expense_subtype:undefined})}/></Form.Item>
            <Form.Item label="费用类型" name="fee_type_id" rules={[{required:true,message:"请选择末级费用类型"}]}><TreeSelect showSearch treeNodeFilterProp="title" treeDefaultExpandAll treeData={batchFeeTypeTreeOptions} placeholder="请选择系统费用类型" onChange={(value)=>{const option=feeTypeSelection(feeTypeCatalog,value);batchFeeForm.setFieldValue("expense_subtype",option?.name);}}/></Form.Item>
            <Form.Item name="expense_subtype" hidden><Input /></Form.Item>
            <Form.Item label="单案金额" name="amount" rules={[{required:true,message:"请输入单案金额"}]}><InputNumber min={0.01} max={100000000} precision={2} style={{width:"100%"}}/></Form.Item>
            <Form.Item label="经办人账号" name="handler" rules={[{required:true,message:"请输入经办人账号"}]}><Input/></Form.Item>
          </div>
          <Form.Item label="费用说明" name="description"><Input.TextArea rows={3}/></Form.Item>
        </Form>
      </Modal>
      <Modal
        width={700}
        open={Boolean(editingCounselCase)}
        title={`修改法律顾问案件基本信息：${editingCounselCase?.serial_no||""}`}
        okText="确定"
        cancelText="取消"
        onOk={saveCounselBasic}
        onCancel={()=>setEditingCounselCase(null)}
      >
        <Form form={counselEditForm} layout="vertical">
          <Form.Item label="客户" name="customer"><Input disabled /></Form.Item>
          <Form.Item label="顾问类型" name="counsel_type" rules={[{required:true,message:"请输入顾问类型"}]}><Input /></Form.Item>
          <Form.Item label="案件名称" name="title" rules={[{required:true,message:"请输入案件名称"}]}><Input /></Form.Item>
          <Form.Item label="顾问期限" name="counsel_range" rules={[{required:true,message:"请选择顾问期限"}]}><DatePicker.RangePicker style={{width:"100%"}} /></Form.Item>
          <Form.Item label="经办律师" name="handling_lawyers" rules={[{required:true,message:"请选择系统已创建的在职律师"}]}><Select mode="multiple" showSearch optionFilterProp="label" options={caseLawyerOptions}/></Form.Item>
          <Form.Item label="律师助理" name="assistant"><Select allowClear showSearch optionFilterProp="label" options={caseAssistantOptions}/></Form.Item>
          <Form.Item label="修改说明" name="comment"><Input.TextArea rows={3}/></Form.Item>
        </Form>
      </Modal>
      <Modal
        width={760}
        open={Boolean(editingNormalCase)}
        title={`修改${editingNormalCase?.data.case_type||"案件"}基本信息：${editingNormalCase?.serial_no||""}`}
        okText="确定"
        cancelText="取消"
        onOk={saveNormalCaseBasic}
        onCancel={()=>setEditingNormalCase(null)}
        destroyOnHidden
      >
        <Alert type="info" showIcon title="此表单对应旧系统民事、刑事、行政及国家赔偿案件的基本信息修改；归档案件和无办理权限账号不能保存。" style={{marginBottom:12}}/>
        <Form form={normalCaseEditForm} layout="vertical">
          <Form.Item label="案件阶段" name="case_phase" rules={[{required:true,message:"请选择案件阶段"}]}>
            <Select showSearch optionFilterProp="label" options={normalEditPhaseOptions.map((option) => ({
              value: option.canonical_name || option.name,
              label: option.name,
            }))} />
          </Form.Item>
          <Form.Item label="客户" name="customer_record_id" rules={[{required:true,message:"请选择可见且有效的客户"}]}><Select disabled={!Number(editingNormalCase?.data.customer_record_id || editingNormalCase?.data.customer_id)} showSearch optionFilterProp="label" options={caseCustomers.filter(item=>!["公海","已回收"].includes(item.status)).map(item=>({value:item.id,label:`${item.serial_no}｜${item.title}`}))}/></Form.Item>
          <Form.Item label={editingNormalCase?.data.case_type === "刑事案件" ? "罪名/案由" : "案由"} name="cause_or_charge" rules={[{required:true,message:"请输入案由或罪名"}]}><Input/></Form.Item>
          <Form.Item label="案件名称" name="title" rules={[{required:true,message:"请输入案件名称"}]}><Input/></Form.Item>
          <div className="form-grid">
            <Form.Item label="经办律师" name="handling_lawyers" rules={[{required:true,message:"请选择系统已创建的在职律师"}]}><Select mode="multiple" showSearch optionFilterProp="label" options={caseLawyerOptions}/></Form.Item>
            <Form.Item label="律师助理" name="assistants" normalize={prioritizeCaseAssistantSelection}><Select mode="multiple" showSearch optionFilterProp="label" options={caseAssistantOptions} placeholder="可选择多人；最新选择的助理排在最前" /></Form.Item>
            <Form.Item label="调查员" name="investigator"><Select allowClear showSearch optionFilterProp="label" options={caseAssistantOptions} placeholder="请选择系统已创建的在职人员" /></Form.Item>
            {isCivilCaseType(editingNormalCase?.data.case_type) && <Form.Item label="案源人" name="business_owner"><Select allowClear showSearch optionFilterProp="label" options={caseAssistantOptions} placeholder="请选择系统已创建的在职人员" /></Form.Item>}
            {editingNormalCase?.data.case_type === "行政案件及国家赔偿" && <Form.Item label="权利类型" name="right_type"><Select allowClear options={rightTypeOptions}/></Form.Item>}
          </div>
          <Form.Item label="关联调查线索" name="investigation_clue_ids"><Select mode="multiple" showSearch optionFilterProp="label" options={caseClues.map(item=>({value:item.id,label:`${item.serial_no}｜${item.title}`}))}/></Form.Item>
          <Form.Item label="修改说明" name="comment"><Input.TextArea rows={3}/></Form.Item>
        </Form>
      </Modal>
      <Modal width={720} open={Boolean(editingArbitrationCase)} title={`修改仲裁案件基本信息：${editingArbitrationCase?.serial_no||""}`} okText="确定" cancelText="取消" onOk={saveArbitrationBasic} onCancel={()=>setEditingArbitrationCase(null)} destroyOnHidden>
        <Alert type="info" showIcon title="仲裁案件使用独立基本信息流程，不复用民事、刑事、行政或法律顾问案件接口。" style={{marginBottom:12}}/>
        <Form form={arbitrationBasicForm} layout="vertical">
          <Form.Item name="case_phase" hidden><Input /></Form.Item>
          <Form.Item label="客户" name="customer_record_id" rules={[{required:true,message:"请选择可见且有效的客户"}]}><Select disabled={!Number(editingArbitrationCase?.data.customer_record_id || editingArbitrationCase?.data.customer_id)} showSearch optionFilterProp="label" options={caseCustomers.filter(item=>!["公海","已回收"].includes(item.status)).map(item=>({value:item.id,label:`${item.serial_no}｜${item.title}`}))}/></Form.Item>
          <Form.Item label="案由" name="cause_or_charge" rules={[{required:true,message:"请输入案由"}]}><Input/></Form.Item><Form.Item label="案件名称" name="title" rules={[{required:true,message:"请输入案件名称"}]}><Input/></Form.Item>
          <div className="form-grid"><Form.Item label="经办律师" name="handling_lawyers" rules={[{required:true,message:"请选择系统已创建的在职律师"}]}><Select mode="multiple" showSearch optionFilterProp="label" options={caseLawyerOptions}/></Form.Item><Form.Item label="律师助理" name="assistant"><Select allowClear showSearch optionFilterProp="label" options={caseAssistantOptions}/></Form.Item><Form.Item label="调查员" name="investigator"><Select allowClear showSearch optionFilterProp="label" options={caseAssistantOptions} placeholder="请选择系统已创建的在职人员" /></Form.Item></div>
          <Form.Item label="关联调查线索" name="investigation_clue_ids"><Select mode="multiple" showSearch optionFilterProp="label" options={caseClues.map(item=>({value:item.id,label:`${item.serial_no}｜${item.title}`}))}/></Form.Item><Form.Item label="修改说明" name="comment"><Input.TextArea rows={3}/></Form.Item>
        </Form>
      </Modal>
      <Modal width={760} open={Boolean(criminalMaintenance)} title={`维护刑事案件资料：${criminalMaintenance?.row.serial_no||""}`} okText="确定" cancelText="取消" onOk={saveCriminalMaintenance} onCancel={()=>setCriminalMaintenance(null)} destroyOnHidden>
        <Form form={criminalMaintenanceForm} layout="vertical">
          {criminalMaintenance?.kind==="litigants"&&<><div className="form-grid">{[["plaintiffs","受害人"],["defendants","被告/犯罪嫌疑人"],["third_parties","第三人"]].map(([name,label])=><Form.Item key={name} label={label} name={name}><Select mode="tags" tokenSeparators={[",","，"]}/></Form.Item>)}</div>{renderCaseLitigantAgentEditor("plaintiff_agents", "受害人代理人")}{renderCaseLitigantAgentEditor("defendant_agents")}{renderCaseLitigantAgentEditor("third_party_agents")}</>}
          {criminalMaintenance?.kind==="public-security"&&<div className="form-grid">{[["public_security_name","公安机关"],["public_security_case_no","公安案件号"],["public_security_address","地址"],["public_security_phone","联系电话"],["public_security_operator","承办人"]].map(([name,label])=><Form.Item key={name} label={label} name={name}><Input/></Form.Item>)}</div>}
          {criminalMaintenance?.kind==="procuratorates"&&["first","second","retrial"].map(level=><div className="form-grid" key={level}>{[[`${level}_procuratorate_name`,`${level==="first"?"一审":level==="second"?"二审":"再审"}检察院`],[`${level}_procuratorate_case_no`,`案件号`],[`${level}_procuratorate_address`,`地址`],[`${level}_procuratorate_phone`,`联系电话`],[`${level}_procuratorate_operator`,`承办人`]].map(([name,label])=><Form.Item key={name} label={label} name={name}><Input/></Form.Item>)}</div>)}
          {criminalMaintenance?.kind==="courts"&&["first","second","execution","retrial"].map(level=>{
            const levelLabel=level==="first"?"一审":level==="second"?"二审":level==="execution"?"执行":"再审";
            const fieldRows=level==="execution"?[["execution_court_name","执行法院"],["execution_court_case_no","案号"],["execution_court_courtroom","法庭"],["execution_court_judge","法官"],["execution_court_clerk","书记员"]]:[[`${level}_court_name`,`${levelLabel}法院`],[`${level}_court_case_no`,`案号`],[`${level}_court_courtroom`,`法庭`],[`${level}_court_judge`,`法官`],[`${level}_court_clerk`,`书记员`]];
            const filingDateName=level==="execution"?"execution_court_filing_date":`${level}_court_filing_date`;
            const hearingDateName=level==="execution"?"execution_court_hearing_date":`${level}_court_hearing_date`;
            return <div key={level}><Form.Item name={`${level}_court_enabled`} valuePropName="checked"><Checkbox>{`${levelLabel}法院信息`}</Checkbox></Form.Item><div className="form-grid">{fieldRows.map(([name,label])=><Form.Item key={name} label={label} name={name}><Input/></Form.Item>)}<Form.Item label="立案日期" name={filingDateName}><DatePicker style={{width:"100%"}}/></Form.Item><Form.Item label="开庭日期" name={hearingDateName}><DatePicker style={{width:"100%"}}/></Form.Item></div></div>;
          })}
          <Form.Item label="修改说明" name="comment"><Input.TextArea rows={3}/></Form.Item>
        </Form>
      </Modal>
      <Modal width={960} open={Boolean(editingCaseLitigants)} title={`修改当事人：${editingCaseLitigants?.serial_no || ""}`} okText="确定" cancelText="取消" onOk={saveCaseLitigants} onCancel={()=>setEditingCaseLitigants(null)} forceRender destroyOnHidden>
        <Alert type="info" showIcon title="输入关键字可搜索系统已有当事人；点击字段右侧加号可新增并立即选中。下方三组代理人按本案独立维护，保存后仅更新本案当事人。" style={{marginBottom:12}} />
        <Form form={caseLitigantsForm} layout="vertical">
          <div className="form-grid">
            {renderCasePartySelector("plaintiffs", true)}
            {renderCasePartySelector("defendants", true)}
            {renderCasePartySelector("third_parties")}
          </div>
          {renderCaseLitigantAgentEditor("plaintiff_agents")}
          {renderCaseLitigantAgentEditor("defendant_agents")}
          {renderCaseLitigantAgentEditor("third_party_agents")}
          <Form.Item label="修改说明" name="comment"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>
      <Modal
        width={620}
        open={Boolean(creatingCasePartyRole)}
        title={`新增${creatingCasePartyRole ? CASE_LITIGANT_PARTY_LABELS[creatingCasePartyRole] : ""}当事人`}
        okText="保存并选中"
        cancelText="取消"
        confirmLoading={creatingCasePartySubmitting}
        onOk={() => void saveCaseParty()}
        onCancel={() => { setCreatingCasePartyRole(null); casePartyCreateForm.resetFields(); }}
        forceRender
        destroyOnHidden
      >
        <Form form={casePartyCreateForm} layout="vertical">
          <Form.Item label="当事人名称" name="title" rules={[{ required: true, whitespace: true, message: "请输入当事人名称" }]}><Input maxLength={256} /></Form.Item>
          <div className="form-grid">
            <Form.Item label="统一社会信用代码/证件号" name="credit_code"><Input maxLength={128} /></Form.Item>
            <Form.Item label="联系电话" name="phone"><Input maxLength={64} /></Form.Item>
            <Form.Item label="法定代表人" name="legal_representative"><Input maxLength={128} /></Form.Item>
            <Form.Item label="注册地址" name="registered_address"><Input maxLength={256} /></Form.Item>
          </div>
        </Form>
      </Modal>
      <Modal
        width={560}
        open={createDefendantEditorOpen}
        title="编辑被告"
        okText="确定"
        cancelText="取消"
        onOk={() => void saveCreateDefendants()}
        onCancel={() => setCreateDefendantEditorOpen(false)}
        destroyOnHidden
      >
        <Alert type="info" showIcon title="可选择已有客户，或输入名称后回车添加多个被告。" style={{ marginBottom: 12 }} />
        <Form form={createDefendantEditorForm} layout="vertical">
          <Form.Item label="被告" name="defendants" rules={[{ required: true, message: "请输入至少一名被告" }]}>
            <Select
              mode="tags"
              tokenSeparators={[",", "，"]}
              showSearch
              optionFilterProp="label"
              placeholder="输入名称后回车，可添加多人"
              options={caseCustomers.filter((item) => !["公海", "已回收"].includes(item.status)).map((item) => ({ value: item.title, label: item.title }))}
            />
          </Form.Item>
        </Form>
      </Modal>
      <Modal width={560} open={Boolean(editingCaseHearingLawyer)} title={`修改开庭律师：${editingCaseHearingLawyer?.serial_no || ""}`} okText="确定" cancelText="取消" onOk={saveCaseHearingLawyer} onCancel={()=>setEditingCaseHearingLawyer(null)} destroyOnHidden>
        <Form form={caseHearingLawyerForm} layout="vertical">
          <Form.Item label="开庭律师" name="hearing_lawyer" rules={[{required:true,message:"请选择系统已创建的在职律师"}]}>
            <Select allowClear showSearch optionFilterProp="label" options={caseLawyerOptions} placeholder="输入关键词选择在职律师" notFoundContent="暂无在职律师；请先在人事中心创建并启用律师账号" />
          </Form.Item>
          <Form.Item label="修改说明" name="comment"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>
      <Drawer
        size={900}
        className="case-subpage-drawer"
        getContainer={false}
        mask={false}
        rootStyle={{position:"absolute",inset:0,height:"calc(100vh - 150px)"}}
        open={Boolean(taskCase)}
        title={`案件任务：${taskCase?.serial_no || ""}`}
        onClose={() => { setTaskCase(null); taskForm.resetFields(); setCaseTaskMaterialFiles([]); }}
      >
        <Alert
          type="info"
          showIcon
          title="分配包含公证材料的案件时，系统会自动生成公证书及公证费发票原件交接任务。扫描文员提交完成后，文书人员 5 日内可退回重启。"
          style={{ marginBottom: 16 }}
        />
        <Space style={{ marginBottom: 12 }}>
          <span>VIP筛选</span>
          <Select
            value={caseTaskVipFilter}
            style={{ width: 130 }}
            options={[{ value: "all", label: "全部任务" }, { value: "vip", label: "仅VIP任务" }, { value: "normal", label: "非VIP任务" }]}
            onChange={(value: "all" | "vip" | "normal") => {
              setCaseTaskVipFilter(value);
              if (taskCase) void loadCaseTasksPage(taskCase, CASE_TASK_DEFAULT_PAGE, caseTaskPageSize, value).catch((error: any) => message.error(error?.response?.data?.detail || "VIP任务筛选失败"));
            }}
          />
        </Space>
        <Table
          rowKey="id"
          size="small"
          pagination={caseTaskPagination}
          tableLayout="fixed"
          scroll={{ x: 890 }}
          dataSource={caseTasks}
          columns={[
            { title: "任务编号", dataIndex: "serial_no", width: 175, render: (value: string, row: TaskRow) => <Button type="link" className="case-cell-link" onClick={() => openRelatedTask(row)}>{value || "—"}</Button> },
            { title: "任务名称", dataIndex: "title", width: 230, ellipsis: true, render: (value: string, row: TaskRow) => <Button type="link" className="case-cell-link" onClick={() => openRelatedTask(row)}>{value || "—"}</Button> },
            {
              title: "类型",
              dataIndex: "creation_mode",
              width: 90,
              render: (_: string, row: TaskRow) => {
                const mode = caseTaskTypeLabel(row);
                return (
                <Tag color={mode === "自动" ? "purple" : "blue"}>{mode}</Tag>
                );
              },
            },
            { title: "发起/验收人", dataIndex: "initiator", width: 105 },
            { title: "负责人", width: 90, render: (_:unknown,row:TaskRow) => casePersonDisplayName(row.owner,row.owner_display_name) },
            { title: "截止日", dataIndex: "deadline", width: 110 },
            { title: "优先级", dataIndex: "priority", width: 90 },
            { title: "是否VIP", width: 90, render: (_: unknown, row: TaskRow) => row.is_vip ? <Tag color="gold">VIP</Tag> : <Tag>否</Tag> },
            {
              title: "状态",
              dataIndex: "status",
              width: 90,
              render: (v: string) => <Tag>{v}</Tag>,
            },
          ]}
        />
        {taskCase && getCaseCapability(taskCase).can_create_case_task && <Card size="small" title="新建案件任务" style={{ marginTop: 16 }}>
          <Form form={taskForm} layout="vertical">
            <Form.Item
              label="任务名称"
              name="title"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <div className="form-grid">
              <Form.Item
                label="负责人"
                name="owner"
                rules={[{ required: true }]}
              >
                <Select showSearch optionFilterProp="label" options={caseAssistantOptions} placeholder="输入中文姓名检索" />
              </Form.Item>
              <Form.Item
                label="开始时间"
                name="start_at"
                rules={[{ required: true, message: "请选择开始时间" }]}
              >
                <DatePicker showTime={{format:"HH:mm"}} format="YYYY-MM-DD HH:mm" style={{ width: "100%" }} />
              </Form.Item>
              <Form.Item
                label="结束时间"
                name="end_at"
                rules={[{ required: true, message: "请选择结束时间" }]}
              >
                <DatePicker showTime={{format:"HH:mm"}} format="YYYY-MM-DD HH:mm" style={{ width: "100%" }} />
              </Form.Item>
              <Form.Item label="优先级" name="priority">
                <Select
                  options={["普通", "重要"].map((v) => ({
                    value: v,
                    label: v,
                  }))}
                />
              </Form.Item>
              <Form.Item label="VIP任务" name="is_vip" valuePropName="checked">
                <Checkbox>标记为VIP任务</Checkbox>
              </Form.Item>
              <Form.Item label="协作人" name="collaborators">
                <Select
                  mode="multiple"
                  showSearch
                  optionFilterProp="label"
                  options={caseAssistantOptions}
                  placeholder="输入中文姓名检索"
                />
              </Form.Item>
            </div>
            <Form.Item label="任务说明" name="description">
              <Input.TextArea rows={3} />
            </Form.Item>
            <Form.Item label="任务附件（可多选，单个不超过20MB）"><Upload multiple fileList={caseTaskMaterialFiles} beforeUpload={(file) => { setCaseTaskMaterialFiles((items) => [...items, file]); return false; }} onRemove={(file) => setCaseTaskMaterialFiles((items) => items.filter((item) => item.uid !== file.uid))}><Button icon={<UploadOutlined />}>上传附件</Button></Upload></Form.Item>
            <Button type="primary" onClick={createCaseTask}>
              创建案件任务
            </Button>
          </Form>
        </Card>}
      </Drawer>
      <Drawer
        width={620}
        open={Boolean(archiving)}
        title={archiveType === "deficit" ? "亏损归档申请" : "正常归档申请"}
        onClose={() => { setArchiving(null); archiveForm.resetFields(); }}
        destroyOnHidden
        footer={(
          <div className="case-archive-application-footer">
            <Button type="primary" onClick={() => void archive(true)}>申请归档</Button>
            <Button onClick={() => { setArchiving(null); archiveForm.resetFields(); }}>取消</Button>
          </div>
        )}
      >
        <Alert
          type="info"
          showIcon
          title="温馨提示：请检查待归档案件材料是否齐全，退费是否有退完。"
          className="case-archive-application-alert"
        />
        <Form form={archiveForm} component={false}>
          <Table
            rowKey="id"
            size="small"
            pagination={false}
            tableLayout="fixed"
            className="case-archive-application-table"
            dataSource={archiving ? [archiving] : []}
            columns={[
              { title: "案号", dataIndex: "serial_no", width: 145 },
              { title: "案件阶段", width: 110, render: (_: unknown, row: CaseRow) => row.data.case_phase || row.status || "—" },
              {
                title: "备注",
                render: () => (
                  <Form.Item
                    name="comment"
                    rules={archiveType === "deficit" ? [{ required: true, whitespace: true, message: "请填写亏损原因" }] : []}
                    noStyle
                  >
                    <Input aria-label={archiveType === "deficit" ? "亏损原因" : "归档备注"} />
                  </Form.Item>
                ),
              },
              {
                title: "操作",
                width: 64,
                align: "center" as const,
                render: () => <Button type="text" danger icon={<CloseOutlined />} title="移除" onClick={() => setArchiving(null)} />,
              },
            ]}
          />
        </Form>
      </Drawer>
      <Modal
        open={Boolean(editingCaseClueEvidence)}
        title={`修改取证信息：${editingCaseClueEvidence?.serial_no || ""}`}
        okText="确定"
        cancelText="取消"
        onOk={() => void saveCaseClueEvidence()}
        onCancel={() => { setEditingCaseClueEvidence(null); caseClueEvidenceForm.resetFields(); }}
        destroyOnHidden
      >
        <Form form={caseClueEvidenceForm} layout="vertical">
          <Form.Item label="取证机构" name="notary_institution" rules={[{ required: true, message: "请输入取证机构" }]}><Input /></Form.Item>
          <div className="form-grid">
            <Form.Item label="公证书号" name="certificate_no"><Input /></Form.Item>
            <Form.Item label="取证时间" name="collected_at" rules={[{ required: true, message: "请选择取证时间" }]}><DatePicker style={{ width: "100%" }} /></Form.Item>
            <Form.Item label="发票号码" name="invoice_no"><Input /></Form.Item>
            <Form.Item label="证物状态" name="evidence_status"><Select options={["未入库", "已入库", "已出库", "已重新入库", "已销毁"].map((value) => ({ value, label: value }))} /></Form.Item>
          </div>
          <Form.Item label="证物存放处" name="storage_location"><Input /></Form.Item>
          <Form.Item label="证据文件"><Input disabled value={editingCaseClueEvidence?.files?.map((file) => file.original_name).join("、") || "无"} /></Form.Item>
        </Form>
      </Modal>
      <Modal
        width="calc(100vw - 64px)"
        open={Boolean(viewingFeeIncomingPayments)}
        title="回款信息"
        footer={<Button onClick={() => setViewingFeeIncomingPayments(null)}>关闭</Button>}
        onCancel={() => setViewingFeeIncomingPayments(null)}
      >
        <Table
          rowKey="id"
          size="small"
          pagination={false}
          dataSource={viewingFeeIncomingPayments || []}
          columns={[
            {title:"回款流水号",dataIndex:"receipt_no",width:180,render:(value:string,row:CaseFeeIncomingPaymentLink)=><Button type="link" className="case-cell-link" onClick={()=>openIncomingPaymentDetail(row.id)}>{value}</Button>},
            {title:"合同编号",dataIndex:"contract_no",width:150},
            {title:"客户名称",dataIndex:"customer_name",width:180},
            {title:"回款单位",dataIndex:"payer_name",width:180},
            {title:"回款日期",dataIndex:"received_date",width:120},
            {title:"回款金额",dataIndex:"amount",width:120,align:"right" as const,render:(value:number)=>Number(value||0).toFixed(2)},
            {title:"回款官费",dataIndex:"assigned_official_fee",width:120,align:"right" as const,render:(value:number)=>Number(value||0).toFixed(2)},
            {title:"回款代理费",dataIndex:"assigned_agency_fee",width:120,align:"right" as const,render:(value:number)=>Number(value||0).toFixed(2)},
            {title:"回款方式",dataIndex:"payment_method",width:120},
            {title:"银行单据号",dataIndex:"bank_reference",width:180},
          ]}
        />
      </Modal>
      <Modal
        open={Boolean(courtRefundFee)}
        title={`法院退费：${courtRefundFee?.serial_no || ""}`}
        okText="确定"
        cancelText="取消"
        onOk={createCourtRefund}
        onCancel={() => { setCourtRefundFee(null); courtRefundForm.resetFields(); }}
      >
        <Alert type="info" showIcon title={`原案：${viewingCounselCase?.serial_no || ""}；原官费：${courtRefundFee?.serial_no || ""}；原金额：${courtRefundFee?.data.amount ?? 0}`} style={{ marginBottom: 16 }} />
        <Form form={courtRefundForm} layout="vertical">
          <Form.Item label="退费金额" name="amount" rules={[{ required: true, message: "请输入退费金额" }]}>
            <InputNumber min={0.01} max={Math.max(Number(courtRefundFee?.data.amount || 0) - Number(courtRefundFee?.data.refund_amount || courtRefundFee?.data.refund_requested_amount || 0), 0)} precision={2} style={{ width: "100%" }} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(reviewing)}
        title={reviewing?.row.status === "亏损内审" ? "内部审核" : "归档审核"}
        width={860}
        footer={[
          <Button key="approve" type="primary" onClick={() => void reviewArchive(true)}>同意</Button>,
          <Button key="reject" danger onClick={() => void reviewArchive(false)}>拒绝</Button>,
          <Button key="cancel" onClick={() => setReviewing(null)}>取消</Button>,
        ]}
        onCancel={() => setReviewing(null)}
      >
        <Alert
          type="info"
          showIcon
          title="请检查待归档案件材料是否齐全。"
          style={{ marginBottom: 16 }}
        />
        <Form form={reviewForm} layout="vertical">
          <Table
            className="case-archive-review-table"
            rowKey="id"
            size="small"
            pagination={false}
            dataSource={reviewing ? [reviewing.row] : []}
            columns={[
              { title: "案号", dataIndex: "serial_no", width: 150 },
              { title: "案件阶段", dataIndex: "status", width: 110 },
              {
                title: "归档号",
                key: "archive_no",
                width: 180,
                render: () => <Form.Item name="archive_no" noStyle><Input maxLength={100} placeholder="请输入归档号" /></Form.Item>,
              },
              {
                title: "审核备注",
                key: "comment",
                render: () => <Form.Item name="comment" noStyle rules={[{ required: true, whitespace: true, message: "请输入审核备注" }]}><Input.TextArea autoSize={{ minRows: 1, maxRows: 3 }} /></Form.Item>,
              },
              {
                title: "操作",
                key: "operation",
                width: 80,
                render: () => <Button type="link" onClick={() => reviewing && void openCounselDetail(reviewing.row)}>查看</Button>,
              },
            ]}
          />
        </Form>
      </Modal>
      <Modal
        open={Boolean(refundCompleting)}
        title={`登记退款到账：${refundCompleting?.serial_no || ""}`}
        okText="确认完成"
        cancelText="取消"
        onOk={completeRefund}
        onCancel={() => {
          setRefundCompleting(null);
          refundCompleteForm.resetFields();
        }}
      >
        <Alert
          type="info"
          showIcon
          title="登记后将生成退款交易流水，并把申请状态更新为已退款。"
          style={{ marginBottom: 16 }}
        />
        <Form form={refundCompleteForm} layout="vertical">
          <Form.Item label="实际退款日期" name="actual_date" rules={[{ required: true, message: "请选择实际退款日期" }]}>
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="退款凭证号" name="voucher_no" rules={[{ required: true, min: 2, message: "请输入至少 2 个字符的退款凭证号" }]}>
            <Input placeholder="银行流水号或退款凭证编号" />
          </Form.Item>
          <Form.Item label="办理说明" name="comment">
            <Input.TextArea rows={3} placeholder="可填写退款方式、到账说明等" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
