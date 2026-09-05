import {
Alert,
Button,
Checkbox,
DatePicker,
Drawer,
Form,
Input,
InputNumber,
Modal,
Select,
Space,
Table,
Tag,
message
} from "antd";
import dayjs from "dayjs";
import { useEffect,useMemo,useRef,useState } from "react";
import { api } from "../api";
import { confirmOperation } from "../components/common/confirmOperation";
import { DetailTabs } from "../components/common/DetailTabs";
import {
getIprApiErrorMessage,
getIprCaseDeletionConfirmation,
getIprCompatibleFileCategory,
getIprSectionLoadError
} from "../iprCaseDetailParity.mjs";
import { IprLegacyHistoryRelations } from "../IprLegacyHistoryRelations";
import {
IPR_DETAIL_DEFAULT_PAGE,
IPR_DETAIL_DEFAULT_PAGE_SIZE,
IPR_ROLE_VIEW_BY_ROUTE,
IPR_WARNING_TARGET_STORAGE_KEY,
consumeCustomerIprRelationKeyword,
isIprLawsuit,
isLegacyIprRecord
} from "./constants";
import { IprBatchOperations } from "./IprBatchOperations";
import { IprCaseCreateModal } from "./IprCaseCreateModal";
import {
IprAnnualFeesPanel,
IprAssistedFeesPanel,
IprCaseDetailHeader,
IprContactsPanel,
IprCustomersPanel,
IprFilesPanel,
IprLawFirmsPanel,
IprLawsuitPanel,
IprLogsPanel,
IprMaintenancePanel,
IprRemindersPanel,
IprTasksPanel,
} from "./IprCaseDetail";
import { IprCaseList } from "./IprCaseList";
import { IprWarningRules } from "./IprWarningRules";
import { createIprDocumentsActions } from "./services/documentsActions";
import { createIprFinanceActions } from "./services/financeActions";
import { createIprQueriesActions } from "./services/queriesActions";
import { createIprWorkflowActions } from "./services/workflowActions";
import type {
AnnualFee,
AssistedFee,
Attachment,
CpcApplication,
Customer,
CustomerContact,
IprBatchCreateError,
IprBusinessLog,
IprCaseContact,
IprCaseCustomer,
IprCaseCustomerCandidate,
IprCaseEvent,
IprCaseTask,
IprDetailPageState,
IprFileType,
IprHistoryItem,
IprLawFirm,
IprLawFirmCandidate,
IprLawsuitCourt,
IprLawsuitFee,
IprLawsuitParty,
IprOperationLog,
IprRecord,
IprReminderEventOption,
IprReminderType,
IprReminderTypeQuery,
IprWarning,
IprWarningRule,
LegacyIprCaseListItem,
PeopleOption,
ReminderEventType
} from "./types";

export default function IprCenterPage({
  initialView,
  onNavigate,
}: {
  initialView: string;
  onNavigate?: (route: string) => void;
}) {
  const kind =
    initialView === "ipr-trademark"
      ? "商标"
      : initialView === "ipr-patent"
        ? "专利"
        : "";
  const roleView = IPR_ROLE_VIEW_BY_ROUTE[initialView];
  const [items, setItems] = useState<IprRecord[]>([]),
    [total, setTotal] = useState(0),
    [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);
  const [pages, setPages] = useState(0);
  const [keyword, setKeyword] = useState(""),
    [caseCategoryFilter, setCaseCategoryFilter] = useState<
      "" | "litigation" | "non_litigation"
    >(""),
    [annualFeeMonitoringFilter, setAnnualFeeMonitoringFilter] = useState<
      "" | "true" | "false"
    >(""),
    [reminderTypeId, setReminderTypeId] = useState<number | null>(null),
    [reminderTypeName, setReminderTypeName] = useState(""),
    [form] = Form.useForm(),
    [createOpen, setCreateOpen] = useState(false),
    [detail, setDetail] = useState<IprRecord | null>(null),
    [legacyHistoryOpen, setLegacyHistoryOpen] = useState(false),
    [legacyHistoryItems, setLegacyHistoryItems] = useState<
      LegacyIprCaseListItem[]
    >([]),
    [legacyHistoryTotal, setLegacyHistoryTotal] = useState(0),
    [legacyHistoryLoading, setLegacyHistoryLoading] = useState(false),
    [legacyHistoryKeyword, setLegacyHistoryKeyword] = useState(""),
    [legacyHistoryCaseId, setLegacyHistoryCaseId] = useState<number | null>(
      null
    ),
    [editing, setEditing] = useState<IprRecord | null>(null),
    [attachments, setAttachments] = useState<Attachment[]>([]);
  const [iprSectionErrors, setIprSectionErrors] = useState({
    files: "",
    logs: "",
    reminders: "",
    tasks: "",
    assistedFees: "",
    annualFees: "",
  });
  const [filesPageState, setFilesPageState] = useState<IprDetailPageState>({
    page: IPR_DETAIL_DEFAULT_PAGE,
    pageSize: IPR_DETAIL_DEFAULT_PAGE_SIZE,
    total: 0,
    pages: 0,
  });
  const [remindersPageState, setRemindersPageState] =
    useState<IprDetailPageState>({
      page: IPR_DETAIL_DEFAULT_PAGE,
      pageSize: IPR_DETAIL_DEFAULT_PAGE_SIZE,
      total: 0,
      pages: 0,
    });
  const [iprTasksPageState, setIprTasksPageState] =
    useState<IprDetailPageState>({
      page: IPR_DETAIL_DEFAULT_PAGE,
      pageSize: IPR_DETAIL_DEFAULT_PAGE_SIZE,
      total: 0,
      pages: 0,
    });
  const [assistedFeesPageState, setAssistedFeesPageState] =
    useState<IprDetailPageState>({
      page: IPR_DETAIL_DEFAULT_PAGE,
      pageSize: IPR_DETAIL_DEFAULT_PAGE_SIZE,
      total: 0,
      pages: 0,
    });
  const [annualFeesPageState, setAnnualFeesPageState] =
    useState<IprDetailPageState>({
      page: IPR_DETAIL_DEFAULT_PAGE,
      pageSize: IPR_DETAIL_DEFAULT_PAGE_SIZE,
      total: 0,
      pages: 0,
    });
  const [customers, setCustomers] = useState<Customer[]>([]),
    [peopleOptions, setPeopleOptions] = useState<PeopleOption[]>([]),
    [profile, setProfile] = useState<{ role?: string; username?: string }>({}),
    [maintenanceTarget, setMaintenanceTarget] =
      useState<IprRecord | null>(null),
    [maintenanceForm] = Form.useForm(),
    [assistedFees, setAssistedFees] = useState<AssistedFee[]>([]),
    [canManageAssistedFees, setCanManageAssistedFees] = useState(false),
    [assistedOpen, setAssistedOpen] = useState(false),
    [assistedForm] = Form.useForm(),
    [editingAssistedFee, setEditingAssistedFee] =
      useState<AssistedFee | null>(null),
    [assistedEditForm] = Form.useForm(),
    [transactTarget, setTransactTarget] = useState<AssistedFee | null>(null),
    [transactForm] = Form.useForm(),
    [receiptFile, setReceiptFile] = useState<File | null>(null),
    [annualFees, setAnnualFees] = useState<AnnualFee[]>([]),
    [annualFeeYearFilter, setAnnualFeeYearFilter] = useState<
      number | undefined
    >(undefined),
    [annualFeesCanManage, setAnnualFeesCanManage] = useState(false),
    [annualFeeOpen, setAnnualFeeOpen] = useState(false),
    [editingAnnualFee, setEditingAnnualFee] = useState<AnnualFee | null>(null),
    [annualFeeForm] = Form.useForm(),
    [iprCaseEvents, setIprCaseEvents] = useState<IprCaseEvent[]>([]),
    [iprEventOpen, setIprEventOpen] = useState(false),
    [editingIprEvent, setEditingIprEvent] = useState<IprCaseEvent | null>(null),
    [iprEventDetail, setIprEventDetail] = useState<IprCaseEvent | null>(null),
    [iprEventForm] = Form.useForm(),
    [iprCaseTasks, setIprCaseTasks] = useState<IprCaseTask[]>([]),
    [iprTaskOpen, setIprTaskOpen] = useState(false),
    [iprTaskForm] = Form.useForm(),
    [reminderTypeWorkbenchOpen, setReminderTypeWorkbenchOpen] =
      useState(false),
    [reminderTypeEditorOpen, setReminderTypeEditorOpen] = useState(false),
    [reminderTypes, setReminderTypes] = useState<IprReminderType[]>([]),
    [editingReminderType, setEditingReminderType] =
      useState<IprReminderType | null>(null),
    [reminderTypeLoading, setReminderTypeLoading] = useState(false),
    [reminderTypeEventOptions, setReminderTypeEventOptions] = useState<
      IprReminderEventOption[]
    >([]),
    [reminderTypeForm] = Form.useForm(),
    [suppressionOpen, setSuppressionOpen] = useState(false),
    [reminderEventTypes, setReminderEventTypes] = useState<
      ReminderEventType[]
    >([]),
    [suppressedIds, setSuppressedIds] = useState<number[]>([]),
    [iprFileOpen, setIprFileOpen] = useState(false),
    [iprFileForm] = Form.useForm(),
    [iprBatchOpen, setIprBatchOpen] = useState(false),
    [iprBatchForm] = Form.useForm(),
    [iprMaintenanceOpen, setIprMaintenanceOpen] = useState(false),
    [iprMaintenanceForm] = Form.useForm(),
    [selectedIprCaseIds, setSelectedIprCaseIds] = useState<number[]>([]),
    [iprBatchFile, setIprBatchFile] = useState<File | null>(null),
    [iprFileTypes, setIprFileTypes] = useState<IprFileType[]>([]),
    [iprUploadFile, setIprUploadFile] = useState<File | null>(null),
    [selectedIprFileIds, setSelectedIprFileIds] = useState<number[]>([]),
    [caseLawFirms, setCaseLawFirms] = useState<IprLawFirm[]>([]),
    [lawFirmCandidates, setLawFirmCandidates] = useState<
      IprLawFirmCandidate[]
    >([]),
    [lawFirmOpen, setLawFirmOpen] = useState(false),
    [lawFirmSelection, setLawFirmSelection] = useState<number[]>([]),
    [caseCustomers, setCaseCustomers] = useState<IprCaseCustomer[]>([]),
    [customerCandidates, setCustomerCandidates] = useState<
      IprCaseCustomerCandidate[]
    >([]),
    [customerOpen, setCustomerOpen] = useState(false),
    [customerSelection, setCustomerSelection] = useState<number[]>([]),
    [primaryCustomerId, setPrimaryCustomerId] = useState<number | null>(null),
    [caseContacts, setCaseContacts] = useState<IprCaseContact[]>([]),
    [contactOpen, setContactOpen] = useState(false),
    [contactCustomer, setContactCustomer] =
      useState<IprCaseCustomer | null>(null),
    [contactCandidates, setContactCandidates] = useState<CustomerContact[]>(
      []
    ),
    [documentContactIds, setDocumentContactIds] = useState<string[]>([]),
    [technologyContactIds, setTechnologyContactIds] = useState<string[]>([]);
  const [iprBusinessLogs, setIprBusinessLogs] = useState<IprBusinessLog[]>(
      [],
    ),
    [iprOperationLogs, setIprOperationLogs] = useState<IprOperationLog[]>(
      [],
    ),
    [iprHistory, setIprHistory] = useState<IprHistoryItem[]>([]),
    [cpcApplications, setCpcApplications] = useState<CpcApplication[]>([]),
    [cpcApplicationsLoading, setCpcApplicationsLoading] = useState(false),
    [cpcApplicationsError, setCpcApplicationsError] = useState(""),
    [cpcGenerating, setCpcGenerating] = useState(false),
    [iprLogOpen, setIprLogOpen] = useState(false),
    [iprBusinessLogDetail, setIprBusinessLogDetail] =
      useState<IprBusinessLog | null>(null),
    [iprOperationLogDetail, setIprOperationLogDetail] =
      useState<IprOperationLog | null>(null),
    [iprHistoryDetail, setIprHistoryDetail] =
      useState<IprHistoryItem | null>(null),
    [iprLogForm] = Form.useForm();
  const [deadlineOffsetOpen, setDeadlineOffsetOpen] = useState(false);
  const [deadlineOffsetForm] = Form.useForm();
  const [warningWorkbenchOpen, setWarningWorkbenchOpen] = useState(false);
  const [warningRuleEditorOpen, setWarningRuleEditorOpen] = useState(false);
  const [warningRules, setWarningRules] = useState<IprWarningRule[]>([]);
  const [warnings, setWarnings] = useState<IprWarning[]>([]);
  const [warningLoading, setWarningLoading] = useState(false);
  const [warningRulesLoading, setWarningRulesLoading] = useState(false);
  const [warningTotal, setWarningTotal] = useState(0);
  const [warningUnread, setWarningUnread] = useState(0);
  const [warningPage, setWarningPage] = useState(1);
  const [warningStatus, setWarningStatus] = useState<
    "" | "未读" | "已读" | "已处理"
  >(""),
    [warningCaseKind, setWarningCaseKind] = useState<
      "" | "专利" | "商标"
    >(""),
    [editingWarningRule, setEditingWarningRule] =
      useState<IprWarningRule | null>(null),
    [processingWarning, setProcessingWarning] = useState<IprWarning | null>(
      null,
    ),
    [warningRuleForm] = Form.useForm(),
    [warningProcessForm] = Form.useForm();
  const [iprBatchCreateOpen, setIprBatchCreateOpen] = useState(false);
  const [iprBatchCreateForm] = Form.useForm();
  const [iprBatchCreateErrors, setIprBatchCreateErrors] = useState<
    IprBatchCreateError[]
  >([]);
  const [iprRebootOpen, setIprRebootOpen] = useState(false);
  const [iprRebootForm] = Form.useForm();
  const [iprRebootPreview, setIprRebootPreview] = useState<{
    source_case_id: number;
    source_case_no: string;
    source_title: string;
    source_status: string;
    next_serial_no: string;
  } | null>(null);
  const [iprDetailTab, setIprDetailTab] = useState<string>("files");
  const [lawsuitCourts, setLawsuitCourts] = useState<IprLawsuitCourt[]>([]);
  const [lawsuitParties, setLawsuitParties] = useState<IprLawsuitParty[]>([]);
  const [lawsuitFees, setLawsuitFees] = useState<IprLawsuitFee[]>([]);
  const [courtInfoOpen, setCourtInfoOpen] = useState(false);
  const [lawsuitCourtOpen, setLawsuitCourtOpen] = useState(false);
  const [lawsuitPartyOpen, setLawsuitPartyOpen] = useState(false);
  const [lawsuitFeeOpen, setLawsuitFeeOpen] = useState(false);
  const [editingLawsuitCourt, setEditingLawsuitCourt] =
    useState<IprLawsuitCourt | null>(null);
  const [editingLawsuitParty, setEditingLawsuitParty] =
    useState<IprLawsuitParty | null>(null);
  const [courtInfoForm] = Form.useForm();
  const [lawsuitCourtForm] = Form.useForm();
  const [lawsuitPartyForm] = Form.useForm();
  const [lawsuitFeeForm] = Form.useForm();
  const batchCaseIds = Form.useWatch("case_ids", iprBatchForm) as
    | number[]
    | undefined;
  const batchSelectedKinds = useMemo(() => {
    const ids = new Set((batchCaseIds || []).map(Number));
    return [
      ...new Set(
        items
          .filter((item) => ids.has(item.id))
          .map((item) => String(item.data?.case_kind || ""))
          .filter(Boolean)
      ),
    ];
  }, [batchCaseIds, items]);
  const batchAvailableFileTypes = useMemo(
    () =>
      iprFileTypes.filter((item) => {
        const applicableKinds = item.case_kinds || [];
        return !applicableKinds.length ||
          batchSelectedKinds.every((caseKind) =>
            applicableKinds.includes(caseKind)
          );
      }),
    [iprFileTypes, batchSelectedKinds]
  );
  useEffect(() => {
    const selectedType = iprBatchForm.getFieldValue("category");
    const compatibleType = getIprCompatibleFileCategory({
      category: selectedType,
      caseKinds: batchSelectedKinds,
      fileTypes: batchAvailableFileTypes,
    });
    if (selectedType && !compatibleType) {
      iprBatchForm.setFieldValue("category", undefined);
    }
  }, [batchAvailableFileTypes, batchSelectedKinds, iprBatchForm]);
  useEffect(() => {
    const selectedType = iprFileForm.getFieldValue("category");
    const compatibleType = getIprCompatibleFileCategory({
      category: selectedType,
      caseKinds: [String(detail?.data?.case_kind || "")],
      fileTypes: iprFileTypes,
    });
    if (selectedType && !compatibleType) {
      iprFileForm.setFieldValue("category", undefined);
    }
  }, [detail, iprFileForm, iprFileTypes]);
  const clearIprSectionError = (
    section: keyof typeof iprSectionErrors
  ) => {
    setIprSectionErrors((current) => ({ ...current, [section]: "" }));
  };
  const setIprSectionError = (
    section: keyof typeof iprSectionErrors,
    error: unknown
  ) => {
    setIprSectionErrors((current) => ({
      ...current,
      [section]:
        section === "tasks"
          ? getIprApiErrorMessage(error, "案件任务加载失败")
          : section === "annualFees"
            ? getIprApiErrorMessage(error, "年费明细加载失败")
            : getIprSectionLoadError(section, error),
    }));
  };
  const handledDetailTarget = useRef("");
  const cpcHistoryRequest = useRef(0);
  const activeIprDetailId = useRef<number | null>(null);
  const reviewView = initialView === "ipr-review";

  // ==================== 列表加载 ====================
  const { load, loadLegacyHistory, loadReminderTypes, loadReminderEventTypes, loadLawsuitManagement, loadIprCaseEvents, loadIprCaseTasks, loadReminderSuppressions, loadCaseLawFirms, loadCaseCustomers, loadCaseContacts, loadIprLogs, loadIprHistory, openLinkedCaseCustomer, openLegacyIprCurrentCustomer, openDetail, exportExcel, loadWarningRules, loadWarnings, openWarningCase, openRebootCase } = createIprQueriesActions({
    get page() { return page; },
    get pageSize() { return pageSize; },
    get keyword() { return keyword; },
    get reminderTypeId() { return reminderTypeId; },
    get setLoading() { return setLoading; },
    get kind() { return kind; },
    get caseCategoryFilter() { return caseCategoryFilter; },
    get reviewView() { return reviewView; },
    get roleView() { return roleView; },
    get annualFeeMonitoringFilter() { return annualFeeMonitoringFilter; },
    get setItems() { return setItems; },
    get setTotal() { return setTotal; },
    get setPage() { return setPage; },
    get setPageSize() { return setPageSize; },
    get setPages() { return setPages; },
    get legacyHistoryKeyword() { return legacyHistoryKeyword; },
    get setLegacyHistoryLoading() { return setLegacyHistoryLoading; },
    get setLegacyHistoryItems() { return setLegacyHistoryItems; },
    get setLegacyHistoryTotal() { return setLegacyHistoryTotal; },
    get setReminderTypeLoading() { return setReminderTypeLoading; },
    get canManageReminderTypes() { return canManageReminderTypes; },
    get setReminderTypes() { return setReminderTypes; },
    get setReminderTypeEventOptions() { return setReminderTypeEventOptions; },
    get setLawsuitCourts() { return setLawsuitCourts; },
    get setLawsuitParties() { return setLawsuitParties; },
    get setLawsuitFees() { return setLawsuitFees; },
    get remindersPageState() { return remindersPageState; },
    get setIprCaseEvents() { return setIprCaseEvents; },
    get setRemindersPageState() { return setRemindersPageState; },
    get clearIprSectionError() { return clearIprSectionError; },
    get setIprSectionError() { return setIprSectionError; },
    get iprTasksPageState() { return iprTasksPageState; },
    get setIprCaseTasks() { return setIprCaseTasks; },
    get setIprTasksPageState() { return setIprTasksPageState; },
    get setReminderEventTypes() { return setReminderEventTypes; },
    get setSuppressedIds() { return setSuppressedIds; },
    get setCaseLawFirms() { return setCaseLawFirms; },
    get setCaseCustomers() { return setCaseCustomers; },
    get setCaseContacts() { return setCaseContacts; },
    get setIprBusinessLogs() { return setIprBusinessLogs; },
    get setIprOperationLogs() { return setIprOperationLogs; },
    get setIprHistory() { return setIprHistory; },
    get onNavigate() { return onNavigate; },
    get activeIprDetailId() { return activeIprDetailId; },
    get cpcHistoryRequest() { return cpcHistoryRequest; },
    get setDetail() { return setDetail; },
    get setIprDetailTab() { return setIprDetailTab; },
    get setAttachments() { return setAttachments; },
    get setCpcApplications() { return setCpcApplications; },
    get setCpcApplicationsError() { return setCpcApplicationsError; },
    get setAssistedFees() { return setAssistedFees; },
    get setCanManageAssistedFees() { return setCanManageAssistedFees; },
    get setAnnualFees() { return setAnnualFees; },
    get setAnnualFeesCanManage() { return setAnnualFeesCanManage; },
    get setAnnualFeeYearFilter() { return setAnnualFeeYearFilter; },
    get setFilesPageState() { return setFilesPageState; },
    get setAssistedFeesPageState() { return setAssistedFeesPageState; },
    get setAnnualFeesPageState() { return setAnnualFeesPageState; },
    get setIprSectionErrors() { return setIprSectionErrors; },
    get loadIprFiles() { return loadIprFiles; },
    get loadCpcApplications() { return loadCpcApplications; },
    get loadAssistedFees() { return loadAssistedFees; },
    get loadAnnualFees() { return loadAnnualFees; },
    get setWarningRulesLoading() { return setWarningRulesLoading; },
    get setWarningRules() { return setWarningRules; },
    get warningPage() { return warningPage; },
    get setWarningLoading() { return setWarningLoading; },
    get warningStatus() { return warningStatus; },
    get warningCaseKind() { return warningCaseKind; },
    get setWarnings() { return setWarnings; },
    get setWarningTotal() { return setWarningTotal; },
    get setWarningUnread() { return setWarningUnread; },
    get setWarningPage() { return setWarningPage; },
    get profile() { return profile; },
    get markWarningRead() { return markWarningRead; },
  });

  const openLegacyHistory = () => {
    setLegacyHistoryOpen(true);
    setLegacyHistoryCaseId(null);
    void loadLegacyHistory();
  };

  useEffect(() => {
    const relationKeyword = consumeCustomerIprRelationKeyword();
    if (relationKeyword) {
      setKeyword(relationKeyword);
      setPage(1);
    }
    void load(1, pageSize, relationKeyword || keyword);
    void api
      .get<{ items: Customer[] }>("/customers", {
        params: { page_size: 100 },
      })
      .then(({ data }) => setCustomers(data.items || []))
      .catch(() => setCustomers([]));
    void api
      .get<{ role?: string; username?: string }>("/auth/me")
      .then(({ data }) => setProfile(data))
      .catch(() => setProfile({}));
    void api
      .get<{
        items: Array<{
          username?: string;
          label?: string;
          value?: string;
        }>;
      }>("/people/options")
      .then(({ data }) =>
        setPeopleOptions(
          (data.items || [])
            .map((item) => ({
              username: String(item.username || "").trim(),
              label: String(item.label || item.value || "").trim(),
            }))
            .filter((item) => item.username && item.label)
        )
      )
      .catch(() => setPeopleOptions([]));
  }, [initialView, annualFeeMonitoringFilter, caseCategoryFilter]);

  useEffect(() => {
    const openStoredWarningTarget = () => {
      try {
        const raw = window.sessionStorage.getItem(
          IPR_WARNING_TARGET_STORAGE_KEY
        );
        window.sessionStorage.removeItem(
          IPR_WARNING_TARGET_STORAGE_KEY
        );
        const caseId = Number(raw || 0);
        if (caseId > 0) {
          void api
            .get<IprRecord>(`/ipr/cases/${caseId}`)
            .then(({ data }) => void openDetail(data))
            .catch(() =>
              message.error(
                "关联知识产权案件不可查看或已不存在"
              )
            );
        }
      } catch {
        /* Ignore unavailable session storage. */
      }
    };
    openStoredWarningTarget();
    window.addEventListener(
      "sunhold:ipr-warning-target",
      openStoredWarningTarget
    );
    return () =>
      window.removeEventListener(
        "sunhold:ipr-warning-target",
        openStoredWarningTarget
      );
  }, [initialView]);

  const resetMainListSearch = () => {
    setKeyword("");
    setAnnualFeeMonitoringFilter("");
    setCaseCategoryFilter("");
    setPage(1);
    setReminderTypeId(null);
    setReminderTypeName("");
  };

  // ==================== 提醒类型 ====================
  const canManageReminderTypes = ["admin", "manager"].includes(
    profile.role || ""
  );

  const openReminderTypeWorkbench = () => {
    setReminderTypeWorkbenchOpen(true);
    void loadReminderTypes();
    void loadReminderEventTypes();
  };
  const openReminderTypeEditor = (item?: IprReminderType) => {
    const query = item?.query_object || {};
    setEditingReminderType(item || null);
    void loadReminderEventTypes();
    reminderTypeForm.resetFields();
    reminderTypeForm.setFieldsValue({
      name: item?.name || "",
      case_kind: query.case_kind || undefined,
      case_type: query.case_type || "",
      case_phase: query.case_phase || "",
      statuses: query.statuses || [],
      event_type_ids: query.event_type_ids || [],
      annual_fee_monitoring: query.annual_fee_monitoring ?? undefined,
      deadline_from: query.deadline_from
        ? dayjs(query.deadline_from)
        : undefined,
      deadline_to: query.deadline_to
        ? dayjs(query.deadline_to)
        : undefined,
      deadline_within_days: query.deadline_within_days ?? undefined,
      is_default: item?.is_default || false,
      is_active: item?.is_active ?? true,
      sort_order: item?.sort_order ?? 0,
    });
    setReminderTypeEditorOpen(true);
  };
  const { saveReminderType, applyDeadlineOffset, create, saveCourtInfo, saveLawsuitCourt, saveLawsuitParty, createIprCasesBatch, openIprReboot, createIprReboot, openLawFirmSelector, saveCaseLawFirms, createIprLog, deleteIprLog, openCustomerSelector, saveCaseCustomers, openContactSelector, saveCaseContacts, saveIprCaseEvent, deleteIprCaseEvent, createIprCaseTask, saveSuppressions, saveMaintenance, saveBatchMaintenance, action, generateWarnings, saveWarningRule, markWarningRead, processWarning } = createIprWorkflowActions({
    get reminderTypeForm() { return reminderTypeForm; },
    get editingReminderType() { return editingReminderType; },
    get setReminderTypeEditorOpen() { return setReminderTypeEditorOpen; },
    get setEditingReminderType() { return setEditingReminderType; },
    get loadReminderTypes() { return loadReminderTypes; },
    get deadlineOffsetForm() { return deadlineOffsetForm; },
    get form() { return form; },
    get setDeadlineOffsetOpen() { return setDeadlineOffsetOpen; },
    get editing() { return editing; },
    get setCreateOpen() { return setCreateOpen; },
    get setEditing() { return setEditing; },
    get load() { return load; },
    get detail() { return detail; },
    get courtInfoForm() { return courtInfoForm; },
    get setCourtInfoOpen() { return setCourtInfoOpen; },
    get setDetail() { return setDetail; },
    get lawsuitCourtForm() { return lawsuitCourtForm; },
    get editingLawsuitCourt() { return editingLawsuitCourt; },
    get setLawsuitCourtOpen() { return setLawsuitCourtOpen; },
    get setEditingLawsuitCourt() { return setEditingLawsuitCourt; },
    get loadLawsuitManagement() { return loadLawsuitManagement; },
    get lawsuitPartyForm() { return lawsuitPartyForm; },
    get editingLawsuitParty() { return editingLawsuitParty; },
    get setLawsuitPartyOpen() { return setLawsuitPartyOpen; },
    get setEditingLawsuitParty() { return setEditingLawsuitParty; },
    get iprBatchCreateForm() { return iprBatchCreateForm; },
    get setIprBatchCreateErrors() { return setIprBatchCreateErrors; },
    get pageSize() { return pageSize; },
    get setIprBatchCreateOpen() { return setIprBatchCreateOpen; },
    get setIprRebootPreview() { return setIprRebootPreview; },
    get iprRebootForm() { return iprRebootForm; },
    get setIprRebootOpen() { return setIprRebootOpen; },
    get iprRebootPreview() { return iprRebootPreview; },
    get openDetail() { return openDetail; },
    get setLawFirmCandidates() { return setLawFirmCandidates; },
    get setLawFirmSelection() { return setLawFirmSelection; },
    get setLawFirmOpen() { return setLawFirmOpen; },
    get lawFirmSelection() { return lawFirmSelection; },
    get loadCaseLawFirms() { return loadCaseLawFirms; },
    get iprLogForm() { return iprLogForm; },
    get setIprLogOpen() { return setIprLogOpen; },
    get loadIprLogs() { return loadIprLogs; },
    get setCustomerCandidates() { return setCustomerCandidates; },
    get setCustomerSelection() { return setCustomerSelection; },
    get setPrimaryCustomerId() { return setPrimaryCustomerId; },
    get setCustomerOpen() { return setCustomerOpen; },
    get customerSelection() { return customerSelection; },
    get primaryCustomerId() { return primaryCustomerId; },
    get loadCaseCustomers() { return loadCaseCustomers; },
    get loadCaseContacts() { return loadCaseContacts; },
    get setContactCustomer() { return setContactCustomer; },
    get setContactCandidates() { return setContactCandidates; },
    get setDocumentContactIds() { return setDocumentContactIds; },
    get setTechnologyContactIds() { return setTechnologyContactIds; },
    get setContactOpen() { return setContactOpen; },
    get contactCustomer() { return contactCustomer; },
    get documentContactIds() { return documentContactIds; },
    get technologyContactIds() { return technologyContactIds; },
    get iprEventForm() { return iprEventForm; },
    get editingIprEvent() { return editingIprEvent; },
    get setIprEventOpen() { return setIprEventOpen; },
    get setEditingIprEvent() { return setEditingIprEvent; },
    get loadIprCaseEvents() { return loadIprCaseEvents; },
    get iprTaskForm() { return iprTaskForm; },
    get setIprTaskOpen() { return setIprTaskOpen; },
    get loadIprCaseTasks() { return loadIprCaseTasks; },
    get suppressedIds() { return suppressedIds; },
    get setSuppressionOpen() { return setSuppressionOpen; },
    get loadReminderSuppressions() { return loadReminderSuppressions; },
    get maintenanceTarget() { return maintenanceTarget; },
    get maintenanceForm() { return maintenanceForm; },
    get setMaintenanceTarget() { return setMaintenanceTarget; },
    get iprMaintenanceForm() { return iprMaintenanceForm; },
    get selectedIprCaseIds() { return selectedIprCaseIds; },
    get setIprMaintenanceOpen() { return setIprMaintenanceOpen; },
    get setSelectedIprCaseIds() { return setSelectedIprCaseIds; },
    get profile() { return profile; },
    get loadWarnings() { return loadWarnings; },
    get warningRuleForm() { return warningRuleForm; },
    get editingWarningRule() { return editingWarningRule; },
    get setWarningRuleEditorOpen() { return setWarningRuleEditorOpen; },
    get loadWarningRules() { return loadWarningRules; },
    get processingWarning() { return processingWarning; },
    get warningProcessForm() { return warningProcessForm; },
    get setProcessingWarning() { return setProcessingWarning; },
  });
  const deleteReminderType = (item: IprReminderType) => {
    confirmOperation({
      title: `删除案件提醒类型：${item.name}`,
      content: "删除后不能恢复，已按该类型筛选的案件不会被删除。",
      okButtonProps: { danger: true },
      onConfirm: async () => {
        try {
          await api.delete(`/ipr/reminder-types/${item.id}`);
          if (reminderTypeId === item.id) {
            setReminderTypeId(null);
            setReminderTypeName("");
            void load(1, pageSize, keyword, null);
          }
          message.success("案件提醒类型已删除");
          await loadReminderTypes();
        } catch (error: any) {
          message.error(
            error?.response?.data?.detail ||
              "删除案件提醒类型失败"
          );
        }
      },
    });
  };
  const applyReminderType = (item: IprReminderType) => {
    setReminderTypeId(item.id);
    setReminderTypeName(item.name);
    setPage(1);
    setReminderTypeWorkbenchOpen(false);
    void load(1, pageSize, keyword, item.id);
  };
  const reminderTypeQuerySummary = (query: IprReminderTypeQuery) => {
    const summary = [
      query.case_kind,
      query.case_type,
      query.case_phase,
      query.statuses?.length
        ? query.statuses.join("、")
        : "",
      query.event_type_ids?.length
        ? `提醒事件：${query.event_type_ids
            .map(
              (id) =>
                reminderTypeEventOptions.find(
                  (item) => item.id === id
                )?.name || id
            )
            .join("、")}`
        : "",
      query.annual_fee_monitoring == null
        ? ""
        : query.annual_fee_monitoring
          ? "年费监控"
          : "未监控年费",
      query.deadline_within_days == null
        ? ""
        : `${query.deadline_within_days} 天内到期`,
      query.deadline_from || query.deadline_to
        ? `${query.deadline_from || "不限"} 至 ${
            query.deadline_to || "不限"
          }`
        : "",
    ].filter(Boolean);
    return summary.join("｜") || "全部可见知识产权案件";
  };

  // ==================== 创建/编辑案件 ====================
  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({
      case_kind: kind || "专利",
      case_category: "non_litigation",
      rate: 0,
    });
    setCreateOpen(true);
  };
  const openEdit = (record: IprRecord) => {
    setEditing(record);
    form.resetFields();
    form.setFieldsValue({
      case_kind: record.data.case_kind,
      case_category: record.data.case_category || "non_litigation",
      customer: record.customer,
      title: record.title,
      application_no: record.data.application_no,
      application_type: record.data.application_type,
      applicant: record.data.applicant,
      case_manager: record.data.case_manager,
      application_date: record.data.application_date
        ? dayjs(record.data.application_date)
        : undefined,
      deadline: record.data.deadline
        ? dayjs(record.data.deadline)
        : undefined,
      annual_fee_year: record.data.annual_fee_year,
      court_case_no: record.data.court_case_no,
      court_name: record.data.court_name,
      judge: record.data.judge,
      clerk: record.data.clerk,
      plaintiff: record.data.plaintiff,
      defendant: record.data.defendant,
      third_parties: record.data.third_parties,
      rate: record.data.rate ?? 0,
      description: record.description,
    });
    setCreateOpen(true);
  };
  const openCopy = (record: IprRecord) => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({
      case_kind: record.data.case_kind,
      case_category: record.data.case_category || "non_litigation",
      customer: record.customer,
      title: `${record.title}（复制）`,
      application_no: record.data.application_no,
      application_type: record.data.application_type,
      applicant: record.data.applicant,
      case_manager: record.data.case_manager,
      application_date: record.data.application_date
        ? dayjs(record.data.application_date)
        : undefined,
      deadline: record.data.deadline
        ? dayjs(record.data.deadline)
        : undefined,
      annual_fee_year: record.data.annual_fee_year,
      court_case_no: record.data.court_case_no,
      court_name: record.data.court_name,
      judge: record.data.judge,
      clerk: record.data.clerk,
      plaintiff: record.data.plaintiff,
      defendant: record.data.defendant,
      third_parties: record.data.third_parties,
      rate: record.data.rate ?? 0,
      description: record.description,
    });
    setDetail(null);
    setCreateOpen(true);
  };
  const openIprCaseTask = (record: IprRecord) => {
    iprTaskForm.resetFields();
    iprTaskForm.setFieldsValue({
      title: `案件任务—${record.serial_no}`,
      owner: profile.username || record.owner,
      deadline: record.data.deadline
        ? dayjs(record.data.deadline)
        : dayjs().add(7, "day"),
      priority: "普通",
    });
    setIprTaskOpen(true);
  };

  // ==================== 诉讼管理 ====================

  const { createLawsuitFee, loadAssistedFees, refreshAssistedFeesAndLogs, loadAnnualFees, createAssistedFee, updateAssistedFee, confirmAssistedFee, transactAssistedFee, deleteAssistedFee, saveAnnualFee, deleteAnnualFee } = createIprFinanceActions({
    get detail() { return detail; },
    get lawsuitFeeForm() { return lawsuitFeeForm; },
    get setLawsuitFeeOpen() { return setLawsuitFeeOpen; },
    get loadLawsuitManagement() { return loadLawsuitManagement; },
    get assistedFeesPageState() { return assistedFeesPageState; },
    get setAssistedFees() { return setAssistedFees; },
    get setCanManageAssistedFees() { return setCanManageAssistedFees; },
    get setAssistedFeesPageState() { return setAssistedFeesPageState; },
    get clearIprSectionError() { return clearIprSectionError; },
    get setIprSectionError() { return setIprSectionError; },
    get loadIprLogs() { return loadIprLogs; },
    get annualFeesPageState() { return annualFeesPageState; },
    get annualFeeYearFilter() { return annualFeeYearFilter; },
    get setAnnualFees() { return setAnnualFees; },
    get setAnnualFeesPageState() { return setAnnualFeesPageState; },
    get setAnnualFeesCanManage() { return setAnnualFeesCanManage; },
    get assistedForm() { return assistedForm; },
    get setAssistedOpen() { return setAssistedOpen; },
    get editingAssistedFee() { return editingAssistedFee; },
    get assistedEditForm() { return assistedEditForm; },
    get setEditingAssistedFee() { return setEditingAssistedFee; },
    get transactTarget() { return transactTarget; },
    get transactForm() { return transactForm; },
    get receiptFile() { return receiptFile; },
    get setTransactTarget() { return setTransactTarget; },
    get setReceiptFile() { return setReceiptFile; },
    get annualFeeForm() { return annualFeeForm; },
    get editingAnnualFee() { return editingAnnualFee; },
    get setAnnualFeeOpen() { return setAnnualFeeOpen; },
    get setEditingAnnualFee() { return setEditingAnnualFee; },
  });
  const deleteLawsuitCourt = (row: IprLawsuitCourt) => {
    if (!detail) return;
    confirmOperation({
      title: "删除诉讼法院信息",
      content: `确认删除${row.court_level}法院"${row.court_name}"吗？`,
      okButtonProps: { danger: true },
      onConfirm: async () => {
        await api.delete(
          `/ipr/lawsuit/cases/${detail.id}/courts/${row.id}`
        );
        message.success("法院信息已删除");
        await loadLawsuitManagement(detail.id);
      },
    });
  };
  const deleteLawsuitParty = (row: IprLawsuitParty) => {
    if (!detail) return;
    confirmOperation({
      title: "删除诉讼当事人",
      content: `确认删除${row.party_type}"${row.name}"吗？`,
      okButtonProps: { danger: true },
      onConfirm: async () => {
        await api.delete(
          `/ipr/lawsuit/cases/${detail.id}/parties/${row.id}`
        );
        message.success("当事人已删除");
        await loadLawsuitManagement(detail.id);
      },
    });
  };

  // ==================== 协助费 ====================

  const refreshAssistedFees = () => {
    if (detail)
      void loadAssistedFees(
        detail.id,
        assistedFeesPageState.page,
        assistedFeesPageState.pageSize
      );
  };

  // ==================== 年费 ====================

  const refreshAnnualFees = () => {
    if (detail)
      void loadAnnualFees(
        detail.id,
        annualFeesPageState.page,
        annualFeesPageState.pageSize
      );
  };

  // ==================== 案件事件/提醒 ====================

  // ==================== 批量创建 ====================
  const openBatchCreate = () => {
    iprBatchCreateForm.resetFields();
    iprBatchCreateForm.setFieldsValue({
      case_kind: kind || "专利",
      rows: [
        {
          case_register_date: dayjs(),
          deadline: dayjs().add(30, "day"),
        },
      ],
    });
    setIprBatchCreateErrors([]);
    setIprBatchCreateOpen(true);
  };

  // ==================== 案件重提 ====================

  // ==================== 案件任务 ====================

  // ==================== 提醒抑制 ====================

  // ==================== 文档/附件 ====================
  const { loadIprFiles, loadCpcApplications, generateCpcApplication, downloadCpcApplication, loadIprFileTypes, openCpcApplicationWorkbench, generateDocument, downloadAttachment, previewAttachment, uploadIprFile, uploadIprBatchFile, markIprFileTransmitted, markSelectedIprFilesTransmitted, deleteIprFile } = createIprDocumentsActions({
    get filesPageState() { return filesPageState; },
    get setAttachments() { return setAttachments; },
    get setFilesPageState() { return setFilesPageState; },
    get clearIprSectionError() { return clearIprSectionError; },
    get setIprSectionError() { return setIprSectionError; },
    get cpcHistoryRequest() { return cpcHistoryRequest; },
    get setCpcApplicationsLoading() { return setCpcApplicationsLoading; },
    get setCpcApplicationsError() { return setCpcApplicationsError; },
    get activeIprDetailId() { return activeIprDetailId; },
    get setCpcApplications() { return setCpcApplications; },
    get setCpcGenerating() { return setCpcGenerating; },
    get setIprFileTypes() { return setIprFileTypes; },
    get openDetail() { return openDetail; },
    get detail() { return detail; },
    get iprFileForm() { return iprFileForm; },
    get iprUploadFile() { return iprUploadFile; },
    get setIprFileOpen() { return setIprFileOpen; },
    get setIprUploadFile() { return setIprUploadFile; },
    get iprBatchForm() { return iprBatchForm; },
    get iprBatchFile() { return iprBatchFile; },
    get setIprBatchOpen() { return setIprBatchOpen; },
    get setIprBatchFile() { return setIprBatchFile; },
    get selectedIprFileIds() { return selectedIprFileIds; },
    get setSelectedIprFileIds() { return setSelectedIprFileIds; },
  });
  const refreshIprFiles = () => {
    if (detail)
      void loadIprFiles(
        detail.id,
        filesPageState.page,
        filesPageState.pageSize
      );
  };

  // ==================== 律所 ====================

  // ==================== 客户 ====================

  // ==================== 联系人 ====================

  // ==================== 日志 ====================

  // ==================== CPC申报 ====================

  // ==================== 业务日志操作 ====================

  // ==================== 客户选择器 ====================

  const openLinkedCaseCustomerCases = (customer: IprCaseCustomer) => {
    const customerKeyword =
      customer.customer_no || customer.name || "";
    setDetail(null);
    setKeyword(customerKeyword);
    void load(1, pageSize, customerKeyword);
  };
  const openMainListCustomerCases = (record: IprRecord) => {
    const customerKeyword = String(
      record.customer || record.data.customer_no || ""
    ).trim();
    if (!customerKeyword) {
      message.warning("当前案件未关联客户");
      return;
    }
    setKeyword(customerKeyword);
    setPage(1);
    void load(1, pageSize, customerKeyword);
  };

  // ==================== 联系人选择器 ====================

  // ==================== 文档类型 ====================

  // ==================== 详情打开 ====================

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const legacyRecordId = new URLSearchParams(
      window.location.search
    ).get("record_id");
    const targetId = Number(legacyRecordId || 0);
    const shouldOpenLog = params.get("open_log") === "1";
    const logContent = params.get("log_content") || "";
    const targetKey = `${initialView}:${targetId}`;
    if (!targetId || handledDetailTarget.current === targetKey) return;
    handledDetailTarget.current = targetKey;
    const openDetailAndMaybeLog = async (record: IprRecord) => {
      await openDetail(record);
      if (shouldOpenLog) {
        iprLogForm.setFieldsValue({ content: logContent });
        setIprLogOpen(true);
      }
    };
    const listed = items.find((item) => item.id === targetId);
    if (listed) {
      void openDetailAndMaybeLog(listed);
      return;
    }
    void api
      .get(`/ipr/cases/${targetId}`)
      .then(({ data }) => {
        if (kind && data?.data?.case_kind !== kind) {
          message.warning("关联案件类型与当前页面不一致");
          return;
        }
        void openDetailAndMaybeLog(data);
      })
      .catch((error: any) =>
        message.warning(
          error?.response?.data?.detail ||
            "未找到关联知识产权案件或当前账号无权查看"
        )
      );
  }, [items, initialView, kind]);

  // ==================== 文档生成/上传 ====================

  // ==================== 协助费操作 ====================

  // ==================== 年费操作 ====================
  const openAnnualFeeEditor = (row?: AnnualFee) => {
    setEditingAnnualFee(row || null);
    annualFeeForm.resetFields();
    annualFeeForm.setFieldsValue({
      fee_year: row?.fee_year ?? dayjs().year(),
      fee_name: row?.fee_name ?? "年费",
      amount: row?.amount ?? undefined,
      currency: row?.currency || "CNY",
      due_date: row?.due_date ? dayjs(row.due_date) : dayjs(),
      paid_date: row?.paid_date ? dayjs(row.paid_date) : undefined,
      status: row?.status || "待缴",
      reminder_date: row?.reminder_date
        ? dayjs(row.reminder_date)
        : undefined,
      notes: row?.notes || "",
    });
    setAnnualFeeOpen(true);
  };

  // ==================== 案件事件操作 ====================

  const openIprCaseEvent = (event?: IprCaseEvent) => {
    setEditingIprEvent(event || null);
    iprEventForm.resetFields();
    iprEventForm.setFieldsValue({
      event_type_id: event?.event_type_id,
      event_date: event?.event_date
        ? dayjs(event.event_date)
        : dayjs(),
      deadline: event?.deadline
        ? dayjs(event.deadline)
        : detail?.data.deadline
          ? dayjs(detail.data.deadline)
          : undefined,
      content: event?.content || "",
    });
    setIprEventOpen(true);
  };
  const canManageIprCaseEvent = (row: IprCaseEvent) =>
    row.creator === profile.username ||
    ["admin", "manager"].includes(profile.role || "");

  // ==================== 案件任务操作 ====================

  // ==================== 删除确认 ====================
  const confirmIprDeletion = (
    kind: string,
    label: string,
    operation: () => Promise<void>
  ) => {
    const prompt = getIprCaseDeletionConfirmation(kind, label);
    confirmOperation({ ...prompt, onConfirm: operation });
  };

  // ==================== 提醒抑制保存 ====================

  // ==================== 导出 ====================

  // ==================== 维护/批量维护 ====================
  const openMaintenance = (record: IprRecord) => {
    maintenanceForm.setFieldsValue({
      deadline: record.data.deadline
        ? dayjs(record.data.deadline)
        : undefined,
      annual_fee_year: record.data.annual_fee_year,
      rate: record.data.rate,
      comment: "",
    });
    setMaintenanceTarget(record);
  };

  const openBatchMaintenance = () => {
    const selected = items.filter((item) =>
      selectedIprCaseIds.includes(item.id)
    );
    if (!selected.length) {
      message.warning("请先选择至少一个知识产权案件");
      return;
    }
    if (selected.some((item) => item.status !== "在办")) {
      message.warning("批量维护仅支持在办案件");
      return;
    }
    iprMaintenanceForm.resetFields();
    setIprMaintenanceOpen(true);
  };
  const setAnnualFeeMonitoring = (enabled: boolean) => {
    const selected = items.filter((item) =>
      selectedIprCaseIds.includes(item.id)
    );
    if (!selected.length) {
      message.warning("请先选择至少一个知识产权案件");
      return;
    }
    if (selected.some((item) => item.status !== "在办")) {
      message.warning("年费监控仅支持在办案件");
      return;
    }
    confirmOperation({
      title: enabled ? "加入年费监控" : "放弃年费监控",
      content: `将对已选 ${selected.length} 件在办案件执行${
        enabled ? "加入" : "放弃"
      }年费监控。系统会先校验整批权限，任一案件不符合即不会修改任何案件。`,
      okText: "确认",
      onConfirm: async () => {
        try {
          const { data } = await api.post(
            `/ipr/cases/annual-fee-monitoring/${
              enabled ? "add" : "remove"
            }`,
            { case_ids: selectedIprCaseIds }
          );
          message.success(
            `已${enabled ? "加入" : "放弃"} ${data.updated} 件案件的年费监控`
          );
          setSelectedIprCaseIds([]);
          void load();
        } catch (e: any) {
          message.error(
            e?.response?.data?.detail || "年费监控调整失败"
          );
          throw e;
        }
      },
    });
  };

  // ==================== 案件操作 ====================

  // ==================== 预警规则 ====================
  const canManageWarningRules = ["admin", "manager"].includes(
    profile.role || ""
  );

  const openWarningWorkbench = () => {
    setWarningWorkbenchOpen(true);
    void Promise.all([
      loadWarningRules(),
      loadWarnings(1),
      loadReminderEventTypes(),
    ]);
  };

  const openWarningRuleEditor = (rule?: IprWarningRule) => {
    setEditingWarningRule(rule || null);
    warningRuleForm.resetFields();
    warningRuleForm.setFieldsValue({
      name: rule?.name || "",
      case_kind: rule?.case_kind || undefined,
      case_type: rule?.case_type || "",
      case_phase: rule?.case_phase || "",
      time_node: rule?.time_node || "case_deadline",
      event_type_id: rule?.event_type_id ?? 0,
      days_before: rule?.days_before ?? 7,
      is_active: rule?.is_active ?? true,
    });
    setWarningRuleEditorOpen(true);
  };

  const deleteWarningRule = (rule: IprWarningRule) =>
    confirmOperation({
      title: `删除预警规则：${rule.name}`,
      content:
        "删除规则会一并清理该规则已生成的预警记录及其站内通知，且不能恢复。",
      okButtonProps: { danger: true },
      onConfirm: async () => {
        try {
          await api.delete(`/ipr/warning-rules/${rule.id}`);
          message.success("预警规则及其关联预警已删除");
          await Promise.all([loadWarningRules(), loadWarnings(1)]);
          window.dispatchEvent(
            new Event("sunhold:notifications-updated")
          );
        } catch (error: any) {
          message.error(
            error?.response?.data?.detail || "删除预警规则失败"
          );
        }
      },
    });

  // ==================== 打开批量上传文档 ====================
  const openBatchUpload = () => {
    iprBatchForm.resetFields();
    iprBatchForm.setFieldsValue({ document_date: dayjs() });
    void loadIprFileTypes("");
    setIprBatchFile(null);
    setIprBatchOpen(true);
  };

  const openUploadFile = () => {
    iprFileForm.resetFields();
    iprFileForm.setFieldsValue({ document_date: dayjs() });
    setIprUploadFile(null);
    void loadIprFileTypes(String(detail?.data?.case_kind || ""));
    setIprFileOpen(true);
  };

  const openEditCourt = (row: IprLawsuitCourt) => {
    setEditingLawsuitCourt(row);
    lawsuitCourtForm.setFieldsValue({
      ...row,
      filing_date: row.filing_date
        ? dayjs(row.filing_date)
        : undefined,
      hearing_date: row.hearing_date
        ? dayjs(row.hearing_date)
        : undefined,
    });
    setLawsuitCourtOpen(true);
  };

  const openAddCourt = () => {
    setEditingLawsuitCourt(null);
    lawsuitCourtForm.resetFields();
    lawsuitCourtForm.setFieldsValue({ court_level: "一审" });
    setLawsuitCourtOpen(true);
  };

  const openEditParty = (row: IprLawsuitParty) => {
    setEditingLawsuitParty(row);
    lawsuitPartyForm.setFieldsValue(row);
    setLawsuitPartyOpen(true);
  };

  const openAddParty = () => {
    setEditingLawsuitParty(null);
    lawsuitPartyForm.resetFields();
    lawsuitPartyForm.setFieldsValue({ party_type: "原告" });
    setLawsuitPartyOpen(true);
  };

  const openAddFee = () => {
    lawsuitFeeForm.resetFields();
    lawsuitFeeForm.setFieldsValue({ fee_date: dayjs() });
    setLawsuitFeeOpen(true);
  };

  const openCourtInfoEditor = () => {
    courtInfoForm.setFieldsValue(detail?.data);
    setCourtInfoOpen(true);
  };

  const openEditAssistedFee = (row: AssistedFee) => {
    assistedEditForm.setFieldsValue({
      assisted_type: row.assisted_type,
      remark: row.remark,
    });
    setEditingAssistedFee(row);
  };

  const openTransactAssistedFee = (row: AssistedFee) => {
    transactForm.resetFields();
    transactForm.setFieldsValue({
      response_date: dayjs(),
    });
    setReceiptFile(null);
    setTransactTarget(row);
  };

  const handleAnnualFeeYearFilterChange = (
    feeYear: number | undefined
  ) => {
    setAnnualFeeYearFilter(feeYear);
    if (detail)
      void loadAnnualFees(
        detail.id,
        IPR_DETAIL_DEFAULT_PAGE,
        annualFeesPageState.pageSize,
        feeYear
      );
  };

  const handleFilesPageChange = (
    nextPage: number,
    nextPageSize: number
  ) => {
    if (detail) void loadIprFiles(detail.id, nextPage, nextPageSize);
  };

  const handleAssistedFeesPageChange = (
    nextPage: number,
    nextPageSize: number
  ) => {
    if (detail)
      void loadAssistedFees(detail.id, nextPage, nextPageSize);
  };

  const handleRemindersPageChange = (
    nextPage: number,
    nextPageSize: number
  ) => {
    if (detail)
      void loadIprCaseEvents(detail.id, nextPage, nextPageSize);
  };

  const handleTasksPageChange = (
    nextPage: number,
    nextPageSize: number
  ) => {
    if (detail)
      void loadIprCaseTasks(detail.id, nextPage, nextPageSize);
  };

  const handleAnnualFeesPageChange = (
    nextPage: number,
    nextPageSize: number
  ) => {
    if (detail)
      void loadAnnualFees(detail.id, nextPage, nextPageSize);
  };

  const handleReminderTypeClose = () => {
    setReminderTypeId(null);
    setReminderTypeName("");
    void load(1, pageSize, keyword, null);
  };

  return (
    <div className="page-shell">
      <IprCaseList
        items={items}
        total={total}
        page={page}
        pageSize={pageSize}
        pages={pages}
        loading={loading}
        keyword={keyword}
        caseCategoryFilter={caseCategoryFilter}
        annualFeeMonitoringFilter={annualFeeMonitoringFilter}
        reminderTypeId={reminderTypeId}
        reminderTypeName={reminderTypeName}
        selectedIprCaseIds={selectedIprCaseIds}
        kind={kind}
        reviewView={reviewView}
        roleView={roleView}
        warningUnread={warningUnread}
        profile={profile}
        onKeywordChange={setKeyword}
        onSearch={() => void load(1, pageSize)}
        onCaseCategoryChange={setCaseCategoryFilter}
        onAnnualFeeMonitoringChange={setAnnualFeeMonitoringFilter}
        onResetSearch={resetMainListSearch}
        onReminderTypeClose={handleReminderTypeClose}
        onOpenWarning={openWarningWorkbench}
        onOpenReminderTypes={openReminderTypeWorkbench}
        onOpenLegacyHistory={openLegacyHistory}
        onExportExcel={exportExcel}
        onOpenBatchCreate={openBatchCreate}
        onOpenBatchUpload={openBatchUpload}
        onNavigate={(route) => onNavigate?.(route)}
        onOpenBatchMaintenance={openBatchMaintenance}
        onSetAnnualFeeMonitoring={setAnnualFeeMonitoring}
        onOpenCreate={openCreate}
        onSelectedIdsChange={setSelectedIprCaseIds}
        onPageChange={(nextPage, nextPageSize) =>
          void load(nextPage, nextPageSize)
        }
        onOpenDetail={(record) => void openDetail(record)}
        onOpenMainListCustomerCases={openMainListCustomerCases}
        onEdit={openEdit}
        onAction={action}
        onOpenIprReboot={(record) => void openIprReboot(record)}
        onOpenCpcApplication={(record) =>
          void openCpcApplicationWorkbench(record)
        }
      />

      <IprCaseCreateModal
        open={createOpen}
        editing={editing}
        form={form}
        customers={customers}
        deadlineOffsetOpen={deadlineOffsetOpen}
        deadlineOffsetForm={deadlineOffsetForm}
        kind={kind}
        onClose={() => {
          setCreateOpen(false);
          setEditing(null);
        }}
        onCreate={create}
        onOpenDeadlineOffset={() => {
          deadlineOffsetForm.resetFields();
          deadlineOffsetForm.setFieldsValue({
            base_date: dayjs(),
          });
          setDeadlineOffsetOpen(true);
        }}
        onCloseDeadlineOffset={() => setDeadlineOffsetOpen(false)}
        onApplyDeadlineOffset={applyDeadlineOffset}
      />

      <IprBatchOperations
        iprBatchCreateOpen={iprBatchCreateOpen}
        iprBatchCreateForm={iprBatchCreateForm}
        iprBatchCreateErrors={iprBatchCreateErrors}
        customers={customers}
        onCloseBatchCreate={() => setIprBatchCreateOpen(false)}
        onCreateBatch={createIprCasesBatch}
        iprBatchOpen={iprBatchOpen}
        iprBatchForm={iprBatchForm}
        iprBatchFile={iprBatchFile}
        items={items}
        batchSelectedKinds={batchSelectedKinds}
        batchAvailableFileTypes={batchAvailableFileTypes}
        iprFileTypes={iprFileTypes}
        onCloseBatchUpload={() => setIprBatchOpen(false)}
        onUploadBatchFile={uploadIprBatchFile}
        onBatchFileChange={setIprBatchFile}
        iprMaintenanceOpen={iprMaintenanceOpen}
        iprMaintenanceForm={iprMaintenanceForm}
        selectedIprCaseIds={selectedIprCaseIds}
        onCloseBatchMaintenance={() => setIprMaintenanceOpen(false)}
        onSaveBatchMaintenance={saveBatchMaintenance}
        iprRebootOpen={iprRebootOpen}
        iprRebootForm={iprRebootForm}
        iprRebootPreview={iprRebootPreview}
        onCloseReboot={() => {
          setIprRebootOpen(false);
          setIprRebootPreview(null);
        }}
        onCreateReboot={createIprReboot}
      />

      <IprWarningRules isAdmin={profile.role === "admin"}
        warningWorkbenchOpen={warningWorkbenchOpen}
        warningRuleEditorOpen={warningRuleEditorOpen}
        warningRules={warningRules}
        warnings={warnings}
        warningLoading={warningLoading}
        warningRulesLoading={warningRulesLoading}
        warningTotal={warningTotal}
        warningUnread={warningUnread}
        warningPage={warningPage}
        warningStatus={warningStatus}
        warningCaseKind={warningCaseKind}
        editingWarningRule={editingWarningRule}
        processingWarning={processingWarning}
        warningRuleForm={warningRuleForm}
        warningProcessForm={warningProcessForm}
        canManageWarningRules={canManageWarningRules}
        reminderTypeEventOptions={reminderTypeEventOptions}
        onCloseWorkbench={() => setWarningWorkbenchOpen(false)}
        onNavigateMessages={() => onNavigate?.("user-messages")}
        onGenerateWarnings={generateWarnings}
        onLoadWarnings={loadWarnings}
        onLoadWarningRules={loadWarningRules}
        onOpenRuleEditor={openWarningRuleEditor}
        onCloseRuleEditor={() => setWarningRuleEditorOpen(false)}
        onSaveRule={saveWarningRule}
        onDeleteRule={deleteWarningRule}
        onStatusChange={setWarningStatus}
        onCaseKindChange={setWarningCaseKind}
        onMarkRead={markWarningRead}
        onOpenWarningCase={openWarningCase}
        onOpenProcess={(warning) => {
          warningProcessForm.resetFields();
          setProcessingWarning(warning);
        }}
        onCloseProcess={() => setProcessingWarning(null)}
        onProcessWarning={processWarning}
      />

      {/* 历史案件 Drawer */}
      <Drawer
        open={legacyHistoryOpen}
        title="Historical IPR cases (read-only)"
        width={980}
        onClose={() => {
          setLegacyHistoryOpen(false);
          setLegacyHistoryCaseId(null);
        }}
      >
        <Space style={{ marginBottom: 12 }}>
          <Input
            allowClear
            value={legacyHistoryKeyword}
            placeholder="Legacy case number or name"
            onChange={(event) =>
              setLegacyHistoryKeyword(event.target.value)
            }
            onPressEnter={() => void loadLegacyHistory()}
            style={{ width: 280 }}
          />
          <Button onClick={() => void loadLegacyHistory()}>
            Search
          </Button>
          <Tag>{legacyHistoryTotal} historical cases</Tag>
        </Space>
        <Table<LegacyIprCaseListItem>
          rowKey="legacy_case_id"
          size="small"
          loading={legacyHistoryLoading}
          pagination={false}
          dataSource={legacyHistoryItems}
          columns={[
            {
              title: "Legacy case",
              dataIndex: "case_no",
              width: 180,
              ellipsis: true,
            },
            {
              title: "Title",
              dataIndex: "title",
              width: 240,
              ellipsis: true,
            },
            { title: "Type", dataIndex: "case_type", width: 120 },
            {
              title: "Applicant",
              dataIndex: "applicant",
              width: 180,
              ellipsis: true,
            },
            {
              title: "State",
              dataIndex: "relationship_state",
              width: 110,
            },
            {
              title: "Open",
              fixed: "right",
              width: 190,
              render: (_, row) => (
                <Space size={0}>
                  {row.current_case_record_id ? (
                    <Button
                      type="link"
                      onClick={async () => {
                        const { data } = await api.get<IprRecord>(
                          `/ipr/cases/${row.current_case_record_id}`
                        );
                        void openDetail(data);
                      }}
                    >
                      Current case
                    </Button>
                  ) : null}
                  <Button
                    type="link"
                    onClick={() =>
                      setLegacyHistoryCaseId(row.legacy_case_id)
                    }
                  >
                    Read-only relations
                  </Button>
                </Space>
              ),
            },
          ]}
          scroll={{ x: 1000 }}
        />
      </Drawer>
      <Drawer
        open={legacyHistoryCaseId !== null}
        title="Historical IPR relations (read-only)"
        width={900}
        onClose={() => setLegacyHistoryCaseId(null)}
      >
        {legacyHistoryCaseId !== null ? (
          <IprLegacyHistoryRelations
            legacyCaseId={legacyHistoryCaseId}
            onOpenCurrentCustomer={(customerRecordId) =>
              void openLegacyIprCurrentCustomer(customerRecordId)
            }
          />
        ) : null}
      </Drawer>

      {/* 提醒类型工作台 Drawer */}
      <Drawer
        open={reminderTypeWorkbenchOpen}
        title="案件提醒类型工作台"
        width={920}
        onClose={() => setReminderTypeWorkbenchOpen(false)}
        extra={
          <Space>
            <Button onClick={() => void loadReminderTypes()}>刷新</Button>
            {canManageReminderTypes ? (
              <Button
                type="primary"
                onClick={() => openReminderTypeEditor()}
              >
                新建类型
              </Button>
            ) : null}
          </Space>
        }
      >
        <Alert
          type="info"
          showIcon
          message="提醒类型是保存的案件筛选条件"
          description="案件数和点入后的清单均按当前账号的数据范围实时计算；它不等同于单条案件事件的事件类型。"
          style={{ marginBottom: 16 }}
        />
        <Table<IprReminderType>
          rowKey="id"
          size="small"
          loading={reminderTypeLoading}
          pagination={false}
          dataSource={reminderTypes}
          scroll={{ x: 860 }}
          columns={[
            {
              title: "提醒类型",
              dataIndex: "name",
              width: 180,
              render: (value: string, row) => (
                <Space>
                  <Button
                    type="link"
                    onClick={() => applyReminderType(row)}
                  >
                    {value}
                  </Button>
                  {row.is_default ? (
                    <Tag color="blue">默认</Tag>
                  ) : null}
                  {row.is_active ? null : <Tag>已停用</Tag>}
                </Space>
              ),
            },
            {
              title: "筛选条件",
              width: 300,
              render: (_, row) =>
                reminderTypeQuerySummary(row.query_object),
            },
            {
              title: "当前可见案件",
              dataIndex: "case_count",
              width: 125,
              render: (count: number, row) => (
                <Button
                  type="link"
                  onClick={() => applyReminderType(row)}
                >
                  {count} 件
                </Button>
              ),
            },
            { title: "排序", dataIndex: "sort_order", width: 75 },
            {
              title: "操作",
              width: 155,
              render: (_, row) =>
                canManageReminderTypes ? (
                  <Space size={0}>
                    <Button
                      type="link"
                      onClick={() => openReminderTypeEditor(row)}
                    >
                      编辑
                    </Button>
                    <Button
                      type="link"
                      danger
                      disabled={row.is_default}
                      onClick={() => deleteReminderType(row)}
                    >
                      删除
                    </Button>
                  </Space>
                ) : (
                  "—"
                ),
            },
          ]}
        />
      </Drawer>

      {/* 提醒类型编辑 Modal */}
      <Modal
        open={reminderTypeEditorOpen}
        title={
          editingReminderType
            ? `编辑提醒类型：${editingReminderType.name}`
            : "新建案件提醒类型"
        }
        width={700}
        onCancel={() => {
          setReminderTypeEditorOpen(false);
          setEditingReminderType(null);
        }}
        onOk={() => void saveReminderType()}
        okText="保存"
      >
        <Form form={reminderTypeForm} layout="vertical">
          <div className="form-grid">
            <Form.Item
              name="name"
              label="提醒类型名称"
              rules={[
                { required: true, message: "请输入提醒类型名称" },
              ]}
            >
              <Input maxLength={128} />
            </Form.Item>
            <Form.Item name="sort_order" label="排序" initialValue={0}>
              <InputNumber
                min={0}
                max={100000}
                style={{ width: "100%" }}
              />
            </Form.Item>
            <Form.Item name="case_kind" label="案件类型">
              <Select
                allowClear
                options={["专利", "商标"].map((value) => ({
                  value,
                  label: value,
                }))}
              />
            </Form.Item>
            <Form.Item name="annual_fee_monitoring" label="年费监控">
              <Select
                allowClear
                options={[
                  { value: true, label: "仅监控中" },
                  { value: false, label: "仅未监控" },
                ]}
              />
            </Form.Item>
            <Form.Item name="case_type" label="案件子类型">
              <Input maxLength={128} />
            </Form.Item>
            <Form.Item name="case_phase" label="案件阶段">
              <Input maxLength={128} />
            </Form.Item>
            <Form.Item name="event_type_ids" label="关联提醒事件">
              <Select
                mode="multiple"
                allowClear
                optionFilterProp="label"
                options={reminderTypeEventOptions.map((item) => ({
                  value: item.id,
                  label: item.name,
                }))}
              />
            </Form.Item>
            <Form.Item name="deadline_from" label="期限起始">
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item name="deadline_to" label="期限结束">
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item name="deadline_within_days" label="未来到期天数">
              <InputNumber
                min={0}
                max={3650}
                style={{ width: "100%" }}
              />
            </Form.Item>
            <Form.Item name="statuses" label="案件状态">
              <Select
                mode="multiple"
                options={[
                  "草稿",
                  "待立案审核",
                  "在办",
                  "已驳回",
                  "已结案",
                ].map((value) => ({ value, label: value }))}
              />
            </Form.Item>
          </div>
          <Space>
            <Form.Item name="is_default" valuePropName="checked" noStyle>
              <Checkbox>默认类型</Checkbox>
            </Form.Item>
            <Form.Item name="is_active" valuePropName="checked" noStyle>
              <Checkbox>启用</Checkbox>
            </Form.Item>
          </Space>
        </Form>
      </Modal>

      {/* 案件详情 Drawer */}
      <Drawer
        open={!!detail}
        title={
          detail
            ? `${detail.data.case_kind}案件详情：${detail.serial_no}`
            : ""
        }
        width={820}
        extra={
          detail && !isLegacyIprRecord(detail) ? (
            <Space size={0}>
              <Button onClick={() => openCopy(detail)}>复制案件</Button>
              <Button onClick={() => void openIprReboot(detail)}>
                案件重提
              </Button>
              <Button onClick={() => openIprCaseTask(detail)}>
                案件任务
              </Button>
            </Space>
          ) : null
        }
        onClose={() => {
          activeIprDetailId.current = null;
          cpcHistoryRequest.current += 1;
          setDetail(null);
        }}
      >
        {detail && (
          <>
            <IprCaseDetailHeader
              detail={detail}
              cpcApplications={cpcApplications}
              cpcApplicationsLoading={cpcApplicationsLoading}
              cpcApplicationsError={cpcApplicationsError}
              cpcGenerating={cpcGenerating}
              onCopyCase={() => openCopy(detail)}
              onIprReboot={() => void openIprReboot(detail)}
              onOpenCaseTask={() => openIprCaseTask(detail)}
              onOpenRebootCase={openRebootCase}
              onLoadCpcApplications={() =>
                void loadCpcApplications(detail.id)
              }
              onGenerateCpcApplication={() =>
                void generateCpcApplication(detail)
              }
              onDownloadCpcApplication={(app) =>
                void downloadCpcApplication(detail, app)
              }
            />

            <IprLogsPanel
              detail={detail}
              iprSectionErrors={iprSectionErrors}
              iprBusinessLogs={iprBusinessLogs}
              iprOperationLogs={iprOperationLogs}
              iprHistory={iprHistory}
              profile={profile}
              iprLogOpen={iprLogOpen}
              iprLogForm={iprLogForm}
              iprBusinessLogDetail={iprBusinessLogDetail}
              iprOperationLogDetail={iprOperationLogDetail}
              iprHistoryDetail={iprHistoryDetail}
              onOpenLog={() => {
                iprLogForm.resetFields();
                setIprLogOpen(true);
              }}
              onCloseLog={() => setIprLogOpen(false)}
              onCreateLog={createIprLog}
              onDeleteLog={deleteIprLog}
              onSetBusinessLogDetail={setIprBusinessLogDetail}
              onSetOperationLogDetail={setIprOperationLogDetail}
              onSetHistoryDetail={setIprHistoryDetail}
              confirmIprDeletion={confirmIprDeletion}
            />

            <IprCustomersPanel
              detail={detail}
              caseCustomers={caseCustomers}
              customerOpen={customerOpen}
              customerCandidates={customerCandidates}
              customerSelection={customerSelection}
              primaryCustomerId={primaryCustomerId}
              onOpenCustomerSelector={openCustomerSelector}
              onCloseCustomerSelector={() => setCustomerOpen(false)}
              onSaveCustomers={saveCaseCustomers}
              onCustomerSelectionChange={(selected) => {
                setCustomerSelection(selected);
                if (!selected.includes(Number(primaryCustomerId)))
                  setPrimaryCustomerId(selected[0] || null);
              }}
              onPrimaryCustomerChange={setPrimaryCustomerId}
              onOpenLinkedCustomer={openLinkedCaseCustomer}
              onOpenLinkedCustomerCases={openLinkedCaseCustomerCases}
              onOpenContactSelector={openContactSelector}
            />

            <IprContactsPanel
              detail={detail}
              caseContacts={caseContacts}
              contactOpen={contactOpen}
              contactCustomer={contactCustomer}
              contactCandidates={contactCandidates}
              documentContactIds={documentContactIds}
              technologyContactIds={technologyContactIds}
              onCloseContactSelector={() => setContactOpen(false)}
              onSaveContacts={saveCaseContacts}
              onDocumentContactChange={setDocumentContactIds}
              onTechnologyContactChange={setTechnologyContactIds}
            />

            <IprLawFirmsPanel
              detail={detail}
              caseLawFirms={caseLawFirms}
              lawFirmOpen={lawFirmOpen}
              lawFirmCandidates={lawFirmCandidates}
              lawFirmSelection={lawFirmSelection}
              onOpenLawFirmSelector={openLawFirmSelector}
              onCloseLawFirmSelector={() => setLawFirmOpen(false)}
              onSaveLawFirms={saveCaseLawFirms}
              onLawFirmSelectionChange={setLawFirmSelection}
            />

            {Number(
              detail.data?.legacy_ipr_case_id ||
                detail.data?.legacy_case_id ||
                0
            ) > 0 ? (
              <div style={{ marginTop: 16 }}>
                <IprLegacyHistoryRelations
                  legacyCaseId={Number(
                    detail.data?.legacy_ipr_case_id ||
                      detail.data?.legacy_case_id
                  )}
                  onOpenCurrentCustomer={(customerRecordId) =>
                    void openLegacyIprCurrentCustomer(customerRecordId)
                  }
                />
              </div>
            ) : null}

            <DetailTabs
              activeKey={iprDetailTab}
              onChange={setIprDetailTab}
              sections={[
                ...(isIprLawsuit(detail)
                  ? [
                      {
                        key: "lawsuit",
                        label: "诉讼管理",
                        children: (
                          <IprLawsuitPanel
                            detail={detail}
                            lawsuitCourts={lawsuitCourts}
                            lawsuitParties={lawsuitParties}
                            lawsuitFees={lawsuitFees}
                            courtInfoOpen={courtInfoOpen}
                            lawsuitCourtOpen={lawsuitCourtOpen}
                            lawsuitPartyOpen={lawsuitPartyOpen}
                            lawsuitFeeOpen={lawsuitFeeOpen}
                            editingLawsuitCourt={editingLawsuitCourt}
                            editingLawsuitParty={editingLawsuitParty}
                            courtInfoForm={courtInfoForm}
                            lawsuitCourtForm={lawsuitCourtForm}
                            lawsuitPartyForm={lawsuitPartyForm}
                            lawsuitFeeForm={lawsuitFeeForm}
                            onLoadManagement={() =>
                              void loadLawsuitManagement(detail.id)
                            }
                            onSaveCourtInfo={saveCourtInfo}
                            onCloseCourtInfo={() =>
                              setCourtInfoOpen(false)
                            }
                            onSaveLawsuitCourt={saveLawsuitCourt}
                            onCloseLawsuitCourt={() => {
                              setLawsuitCourtOpen(false);
                              setEditingLawsuitCourt(null);
                            }}
                            onSaveLawsuitParty={saveLawsuitParty}
                            onCloseLawsuitParty={() => {
                              setLawsuitPartyOpen(false);
                              setEditingLawsuitParty(null);
                            }}
                            onCreateLawsuitFee={createLawsuitFee}
                            onCloseLawsuitFee={() =>
                              setLawsuitFeeOpen(false)
                            }
                            onDeleteLawsuitCourt={deleteLawsuitCourt}
                            onDeleteLawsuitParty={deleteLawsuitParty}
                            onOpenEditCourt={openEditCourt}
                            onOpenEditParty={openEditParty}
                            onOpenAddCourt={openAddCourt}
                            onOpenAddParty={openAddParty}
                            onOpenAddFee={openAddFee}
                            onOpenCourtInfo={openCourtInfoEditor}
                          />
                        ),
                      },
                    ]
                  : []),
                {
                  key: "files",
                  label: "文档信息",
                  children: (
                    <IprFilesPanel
                      detail={detail}
                      iprSectionErrors={iprSectionErrors}
                      attachments={attachments}
                      filesPageState={filesPageState}
                      iprFileTypes={iprFileTypes}
                      iprFileOpen={iprFileOpen}
                      iprFileForm={iprFileForm}
                      iprUploadFile={iprUploadFile}
                      selectedIprFileIds={selectedIprFileIds}
                      onRefresh={refreshIprFiles}
                      onGenerateDocument={generateDocument}
                      onPreviewAttachment={previewAttachment}
                      onDownloadAttachment={downloadAttachment}
                      onOpenUpload={openUploadFile}
                      onCloseUpload={() => {
                        setIprFileOpen(false);
                        setIprUploadFile(null);
                      }}
                      onUploadFile={uploadIprFile}
                      onUploadFileChange={setIprUploadFile}
                      onMarkTransmitted={markIprFileTransmitted}
                      onMarkSelectedTransmitted={
                        markSelectedIprFilesTransmitted
                      }
                      onDeleteFile={deleteIprFile}
                      onSelectedFileIdsChange={setSelectedIprFileIds}
                      confirmIprDeletion={confirmIprDeletion}
                      onPageChange={handleFilesPageChange}
                    />
                  ),
                },
                {
                  key: "assistedFees",
                  label: "协助费",
                  children: (
                    <IprAssistedFeesPanel
                      detail={detail}
                      iprSectionErrors={iprSectionErrors}
                      assistedFees={assistedFees}
                      assistedFeesPageState={assistedFeesPageState}
                      canManageAssistedFees={canManageAssistedFees}
                      assistedOpen={assistedOpen}
                      assistedForm={assistedForm}
                      editingAssistedFee={editingAssistedFee}
                      assistedEditForm={assistedEditForm}
                      transactTarget={transactTarget}
                      transactForm={transactForm}
                      receiptFile={receiptFile}
                      onRefresh={refreshAssistedFees}
                      onOpenCreate={() => {
                        assistedForm.resetFields();
                        setAssistedOpen(true);
                      }}
                      onCloseCreate={() => setAssistedOpen(false)}
                      onCreate={createAssistedFee}
                      onOpenEdit={openEditAssistedFee}
                      onCloseEdit={() => {
                        setEditingAssistedFee(null);
                        assistedEditForm.resetFields();
                      }}
                      onUpdate={updateAssistedFee}
                      onConfirm={confirmAssistedFee}
                      onOpenTransact={openTransactAssistedFee}
                      onCloseTransact={() => {
                        setTransactTarget(null);
                        setReceiptFile(null);
                      }}
                      onTransact={transactAssistedFee}
                      onReceiptFileChange={setReceiptFile}
                      onDelete={deleteAssistedFee}
                      onPreviewAttachment={previewAttachment}
                      onDownloadAttachment={downloadAttachment}
                      confirmIprDeletion={confirmIprDeletion}
                      onPageChange={handleAssistedFeesPageChange}
                    />
                  ),
                },
                {
                  key: "annualFees",
                  label: "年费管理",
                  children: (
                    <IprAnnualFeesPanel
                      detail={detail}
                      iprSectionErrors={iprSectionErrors}
                      annualFees={annualFees}
                      annualFeesPageState={annualFeesPageState}
                      annualFeeYearFilter={annualFeeYearFilter}
                      annualFeesCanManage={annualFeesCanManage}
                      annualFeeOpen={annualFeeOpen}
                      editingAnnualFee={editingAnnualFee}
                      annualFeeForm={annualFeeForm}
                      onRefresh={refreshAnnualFees}
                      onYearFilterChange={
                        handleAnnualFeeYearFilterChange
                      }
                      onOpenEditor={openAnnualFeeEditor}
                      onCloseEditor={() => {
                        setAnnualFeeOpen(false);
                        setEditingAnnualFee(null);
                        annualFeeForm.resetFields();
                      }}
                      onSave={saveAnnualFee}
                      onDelete={deleteAnnualFee}
                      confirmIprDeletion={confirmIprDeletion}
                    />
                  ),
                },
              ]}
            />

            <IprRemindersPanel
              detail={detail}
              iprSectionErrors={iprSectionErrors}
              iprCaseEvents={iprCaseEvents}
              remindersPageState={remindersPageState}
              reminderEventTypes={reminderEventTypes}
              suppressedIds={suppressedIds}
              iprEventOpen={iprEventOpen}
              editingIprEvent={editingIprEvent}
              iprEventDetail={iprEventDetail}
              iprEventForm={iprEventForm}
              suppressionOpen={suppressionOpen}
              profile={profile}
              onRefresh={() => detail && void loadIprCaseEvents(detail.id)}
              onOpenEvent={openIprCaseEvent}
              onCloseEvent={() => {
                setIprEventOpen(false);
                setEditingIprEvent(null);
              }}
              onSaveEvent={saveIprCaseEvent}
              onDeleteEvent={deleteIprCaseEvent}
              onSetEventDetail={setIprEventDetail}
              onOpenSuppression={() => setSuppressionOpen(true)}
              onCloseSuppression={() => setSuppressionOpen(false)}
              onSaveSuppressions={saveSuppressions}
              onSuppressedIdsChange={setSuppressedIds}
              canManageIprCaseEvent={canManageIprCaseEvent}
              confirmIprDeletion={confirmIprDeletion}
            />

            <IprTasksPanel
              detail={detail}
              iprSectionErrors={iprSectionErrors}
              iprCaseTasks={iprCaseTasks}
              iprTasksPageState={iprTasksPageState}
              iprTaskOpen={iprTaskOpen}
              iprTaskForm={iprTaskForm}
              peopleOptions={peopleOptions}
              onRefresh={() => detail && void loadIprCaseTasks(detail.id)}
              onOpenTask={openIprCaseTask}
              onCloseTask={() => setIprTaskOpen(false)}
              onCreateTask={createIprCaseTask}
            />

            <IprMaintenancePanel
              maintenanceTarget={maintenanceTarget}
              maintenanceForm={maintenanceForm}
              onClose={() => setMaintenanceTarget(null)}
              onSave={saveMaintenance}
            />

            <Space style={{ marginTop: 16 }}>
              {["草稿", "已驳回"].includes(detail.status) && (
                <Button
                  onClick={() => {
                    openEdit(detail);
                    setDetail(null);
                  }}
                >
                  编辑草稿
                </Button>
              )}
              {["草稿", "已驳回"].includes(detail.status) && (
                <Button
                  type="primary"
                  onClick={() => action(detail, "submit")}
                >
                  提交立案审核
                </Button>
              )}
              {detail.status === "在办" && (
                <Button onClick={() => openMaintenance(detail)}>
                  维护期限/年费/费率
                </Button>
              )}
              {detail.status === "在办" && (
                <Button
                  danger
                  onClick={() => action(detail, "close")}
                >
                  结案
                </Button>
              )}
              {detail.status === "已结案" &&
                ["admin", "manager"].includes(profile.role || "") && (
                  <Button onClick={() => action(detail, "reopen")}>
                    重新开启
                  </Button>
                )}
            </Space>
          </>
        )}
      </Drawer>
    </div>
  );
}
