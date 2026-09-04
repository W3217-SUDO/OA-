import { useEffect, useMemo, useRef, useState } from "react";
import {
  Button,
  Card,
  Checkbox,
  DatePicker,
  Descriptions,
  Drawer,
  Alert,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  message,
} from "antd";
import type { TableColumnsType } from "antd";
import dayjs from "dayjs";
import { api } from "./api";
import { rememberCustomerDetailTarget, resolveCustomerDetailTarget } from "./customerDetailNavigation";
import { IprLegacyHistoryRelations } from "./IprLegacyHistoryRelations";
import { formatRequiredDate } from "./formSafety";
import {
  buildIprCaseActionPayload,
  getIprCaseActionErrorMessage,
  getIprCaseActionValidationError,
  normalizeIprCaseActionResponse,
} from "./iprCaseWorkflowParity.mjs";
import {
  assertIprMutationSuccess,
  buildIprCaseContactPayload,
  buildIprCaseCustomerPayload,
  buildIprCaseLawFirmPayload,
  buildIprDeadlineFromOffset,
  getIprApiErrorMessage,
  getIprCompatibleFileCategory,
  getIprCaseCustomerValidationError,
  getIprCaseDeletionConfirmation,
  getIprSectionLoadError,
} from "./iprCaseDetailParity.mjs";

type IprRecord = {
  id: number;
  serial_no: string;
  title: string;
  customer: string;
  owner: string;
  owner_display_name?: string;
  status: string;
  description: string;
  data: Record<string, any>;
  updated_at: string;
};
type IprLawsuitCourt = { id: string; court_level: string; court_name: string; case_no?: string; judge?: string; clerk?: string; courtroom?: string; filing_date?: string; hearing_date?: string; remark?: string };
type IprLawsuitParty = { id: string; party_type: string; name: string; contact_name?: string; contact_phone?: string; address?: string; remark?: string };
type IprLawsuitFee = { id: number; fee_type?: string; title?: string; amount?: number; status?: string; fee_date?: string; remark?: string };
type LegacyIprCaseListItem = {
  legacy_case_id: number;
  case_no: string;
  title: string;
  case_type: string;
  applicant: string;
  deadline?: string | null;
  relationship_state: string;
  current_case_record_id: number | null;
};
type Customer = { id: number; title: string; serial_no: string };
type PeopleOption = { username: string; label: string };
type Attachment = {
  id: number;
  original_name: string;
  size: number;
  uploader: string;
  uploader_display_name?: string;
  category?: string;
  document_date?: string | null;
  requires_transmission?: boolean;
  is_transmitted?: boolean;
  transmitted_by?: string;
  transmitted_by_display_name?: string;
};
type IprFileType = {
  code: string;
  name: string;
  case_kinds: string[];
  is_official: boolean;
  requires_transmission: boolean;
  allow_repeat: boolean;
};
type AssistedFee = {
  id: number;
  assisted_type: string;
  status: string;
  request_date: string;
  request_user: string;
  request_user_display_name?: string;
  response_date: string | null;
  response_user: string;
  response_user_display_name?: string;
  remark: string;
  receipt: Attachment | null;
};
type IprCaseEvent = {
  id: number;
  event_type_id: number;
  event_type: string;
  event_date: string;
  deadline: string;
  content: string;
  creator: string;
  creator_display_name?: string;
};
type IprCaseTask = {
  id: number;
  serial_no: string;
  title: string;
  customer: string;
  owner: string;
  owner_display_name?: string;
  status: string;
  deadline?: string;
  priority?: string;
  description?: string;
  case_record_id?: number;
  case_module?: string;
  case_no?: string;
};
type IprReminderTypeQuery = {
  case_kind?: string;
  case_type?: string;
  case_phase?: string;
  statuses?: string[];
  event_type_ids?: number[];
  annual_fee_monitoring?: boolean | null;
  deadline_from?: string;
  deadline_to?: string;
  deadline_within_days?: number | null;
};
type IprReminderType = {
  id: number;
  name: string;
  query_object: IprReminderTypeQuery;
  is_default: boolean;
  is_active: boolean;
  sort_order: number;
  case_count: number;
  created_by: string;
  updated_by: string;
};
type IprReminderEventOption = { id: number; name: string };
type ReminderEventType = { id: number; name: string; suppressed: boolean };
type IprLawFirm = { id: number; law_firm_id: number; code: string; name: string; phone: string; email: string };
type IprLawFirmCandidate = { id: number; code: string; name: string; phone: string; email: string; selected: boolean };
type IprCaseCustomer = { id: number | null; customer_id: number; customer_no: string; name: string; status: string; is_primary: boolean };
type IprCaseCustomerCandidate = { id: number; customer_no: string; name: string; status: string; selected: boolean };
type CustomerContact = { id: string; name: string; phone?: string; email?: string; position?: string; is_valid?: boolean };
type IprCaseContact = CustomerContact & { customer_id: number; customer_name: string; contact_id: string; contact_role: "document" | "technology" };
type IprBusinessLog = { id: number; content: string; created_by: string; created_by_display_name?: string; created_at: string };
type IprOperationLog = { id: number; action: string; operator: string; operator_display_name?: string; comment: string; from_status?: string; to_status?: string; created_at: string };
type IprHistoryItem = { id: number; action: string; operator: string; operator_display_name?: string; comment?: string; from_status?: string; to_status?: string; created_at: string };
type IprBatchCreateError = { row_no: number; message: string; errors: Record<string, string> };
type IprDetailPageState = { page: number; pageSize: number; total: number; pages: number };
type IprDetailPagePayload<T> = { items?: T[]; total?: number; page?: number; page_size?: number; pages?: number; capabilities?: Record<string, boolean> };
const IPR_DETAIL_DEFAULT_PAGE = 1;
const IPR_DETAIL_DEFAULT_PAGE_SIZE = 15;
const isLegacyIprRecord = (record: IprRecord) => Number(record.data?.legacy_ipr_case_id || record.data?.legacy_case_id || 0) > 0;
const isIprLawsuit = (record: IprRecord | null) => record?.data?.case_category === "litigation";
const IPR_LAWSUIT_FIELDS = ["court_case_no", "court_name", "judge", "clerk", "plaintiff", "defendant", "third_parties"] as const;
type IprFinanceFeeType = "官方费用" | "代理费" | "其他费用" | "内部费用" | "结算费用" | "预损费用" | "归档费用";
const IPR_LAWSUIT_FEE_OPTIONS = [
  { value: "诉讼费", label: "诉讼费", feeType: "官方费用" },
  { value: "保全费", label: "保全费", feeType: "官方费用" },
  { value: "公告费", label: "公告费", feeType: "官方费用" },
  { value: "鉴定费", label: "鉴定费", feeType: "官方费用" },
  { value: "执行费", label: "执行费", feeType: "官方费用" },
  { value: "其他", label: "其他", feeType: "其他费用" },
] as const satisfies ReadonlyArray<{ value: string; label: string; feeType: IprFinanceFeeType }>;
const lawsuitFeeFromRecord = (record: IprRecord): IprLawsuitFee => ({
  id: record.id,
  title: record.title,
  fee_type: record.data?.fee_type,
  amount: record.data?.amount,
  fee_date: record.data?.fee_date,
  status: record.status,
  remark: record.description,
});
const personDisplayName = (value?: unknown) => String(value || "").trim() || "姓名待维护";
const statusColor: Record<string, string> = {
  草稿: "default",
  待立案审核: "gold",
  在办: "blue",
  已驳回: "red",
  已结案: "green",
};
const CUSTOMER_IPR_RELATION_STORAGE_KEY = "sunhold:customer-ipr-relation";
const IPR_ROLE_VIEW_BY_ROUTE: Record<string, { roleView: string; label: string }> = {
  "ipr-source-person": { roleView: "source_person", label: "我是案源人" },
  "ipr-procurator": { roleView: "procurator", label: "我是代理人" },
  "ipr-copywriter": { roleView: "copywriter", label: "我是撰稿人" },
  "ipr-officer": { roleView: "officer", label: "我是处理人" },
  "ipr-business-owner": { roleView: "business_owner", label: "我是案件管理人" },
};
const consumeCustomerIprRelationKeyword = () => {
  try {
    const raw = window.sessionStorage.getItem(CUSTOMER_IPR_RELATION_STORAGE_KEY);
    window.sessionStorage.removeItem(CUSTOMER_IPR_RELATION_STORAGE_KEY);
    if (!raw) return "";
    const parsed = JSON.parse(raw) as { serial_no?: string; title?: string; at?: number };
    if (!parsed || (parsed.at && Date.now() - Number(parsed.at) > 60 * 60 * 1000)) return "";
    return String(parsed.title || parsed.serial_no || "").trim();
  } catch {
    return "";
  }
};

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
    [caseCategoryFilter, setCaseCategoryFilter] = useState<"" | "litigation" | "non_litigation">(""),
    [annualFeeMonitoringFilter, setAnnualFeeMonitoringFilter] = useState<"" | "true" | "false">(""),
    [reminderTypeId, setReminderTypeId] = useState<number | null>(null),
    [reminderTypeName, setReminderTypeName] = useState(""),
    [form] = Form.useForm(),
    [createOpen, setCreateOpen] = useState(false),
    [detail, setDetail] = useState<IprRecord | null>(null),
    [legacyHistoryOpen, setLegacyHistoryOpen] = useState(false),
    [legacyHistoryItems, setLegacyHistoryItems] = useState<LegacyIprCaseListItem[]>([]),
    [legacyHistoryTotal, setLegacyHistoryTotal] = useState(0),
    [legacyHistoryLoading, setLegacyHistoryLoading] = useState(false),
    [legacyHistoryKeyword, setLegacyHistoryKeyword] = useState(""),
    [legacyHistoryCaseId, setLegacyHistoryCaseId] = useState<number | null>(null),
    [editing, setEditing] = useState<IprRecord | null>(null),
    [attachments, setAttachments] = useState<Attachment[]>([]);
  const [iprSectionErrors, setIprSectionErrors] = useState({
    files: "",
    logs: "",
    reminders: "",
    tasks: "",
    assistedFees: "",
  });
  const [filesPageState, setFilesPageState] = useState<IprDetailPageState>({
    page: IPR_DETAIL_DEFAULT_PAGE,
    pageSize: IPR_DETAIL_DEFAULT_PAGE_SIZE,
    total: 0,
    pages: 0,
  });
  const [remindersPageState, setRemindersPageState] = useState<IprDetailPageState>({
    page: IPR_DETAIL_DEFAULT_PAGE,
    pageSize: IPR_DETAIL_DEFAULT_PAGE_SIZE,
    total: 0,
    pages: 0,
  });
  const [iprTasksPageState, setIprTasksPageState] = useState<IprDetailPageState>({
    page: IPR_DETAIL_DEFAULT_PAGE,
    pageSize: IPR_DETAIL_DEFAULT_PAGE_SIZE,
    total: 0,
    pages: 0,
  });
  const [assistedFeesPageState, setAssistedFeesPageState] = useState<IprDetailPageState>({
    page: IPR_DETAIL_DEFAULT_PAGE,
    pageSize: IPR_DETAIL_DEFAULT_PAGE_SIZE,
    total: 0,
    pages: 0,
  });
  const [customers, setCustomers] = useState<Customer[]>([]),
    [peopleOptions, setPeopleOptions] = useState<PeopleOption[]>([]),
    [profile, setProfile] = useState<{ role?: string; username?: string }>({}),
    [maintenanceTarget, setMaintenanceTarget] = useState<IprRecord | null>(
      null,
    ),
    [maintenanceForm] = Form.useForm(),
    [assistedFees, setAssistedFees] = useState<AssistedFee[]>([]),
    [canManageAssistedFees, setCanManageAssistedFees] = useState(false),
    [assistedOpen, setAssistedOpen] = useState(false),
    [assistedForm] = Form.useForm(),
    [editingAssistedFee, setEditingAssistedFee] = useState<AssistedFee | null>(null),
    [assistedEditForm] = Form.useForm(),
    [transactTarget, setTransactTarget] = useState<AssistedFee | null>(null),
    [transactForm] = Form.useForm(),
    [receiptFile, setReceiptFile] = useState<File | null>(null),
    [iprCaseEvents, setIprCaseEvents] = useState<IprCaseEvent[]>([]),
    [iprEventOpen, setIprEventOpen] = useState(false),
    [editingIprEvent, setEditingIprEvent] = useState<IprCaseEvent | null>(null),
    [iprEventDetail, setIprEventDetail] = useState<IprCaseEvent | null>(null),
    [iprEventForm] = Form.useForm(),
    [iprCaseTasks, setIprCaseTasks] = useState<IprCaseTask[]>([]),
    [iprTaskOpen, setIprTaskOpen] = useState(false),
    [iprTaskForm] = Form.useForm(),
    [reminderTypeWorkbenchOpen, setReminderTypeWorkbenchOpen] = useState(false),
    [reminderTypeEditorOpen, setReminderTypeEditorOpen] = useState(false),
    [reminderTypes, setReminderTypes] = useState<IprReminderType[]>([]),
    [editingReminderType, setEditingReminderType] = useState<IprReminderType | null>(null),
    [reminderTypeLoading, setReminderTypeLoading] = useState(false),
    [reminderTypeEventOptions, setReminderTypeEventOptions] = useState<IprReminderEventOption[]>([]),
    [reminderTypeForm] = Form.useForm(),
    [suppressionOpen, setSuppressionOpen] = useState(false),
    [reminderEventTypes, setReminderEventTypes] = useState<ReminderEventType[]>(
      [],
    ),
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
    [lawFirmCandidates, setLawFirmCandidates] = useState<IprLawFirmCandidate[]>([]),
    [lawFirmOpen, setLawFirmOpen] = useState(false),
    [lawFirmSelection, setLawFirmSelection] = useState<number[]>([]),
    [caseCustomers, setCaseCustomers] = useState<IprCaseCustomer[]>([]),
    [customerCandidates, setCustomerCandidates] = useState<IprCaseCustomerCandidate[]>([]),
    [customerOpen, setCustomerOpen] = useState(false),
    [customerSelection, setCustomerSelection] = useState<number[]>([]),
    [primaryCustomerId, setPrimaryCustomerId] = useState<number | null>(null),
    [caseContacts, setCaseContacts] = useState<IprCaseContact[]>([]),
    [contactOpen, setContactOpen] = useState(false),
    [contactCustomer, setContactCustomer] = useState<IprCaseCustomer | null>(null),
    [contactCandidates, setContactCandidates] = useState<CustomerContact[]>([]),
    [documentContactIds, setDocumentContactIds] = useState<string[]>([]),
    [technologyContactIds, setTechnologyContactIds] = useState<string[]>([]);
  const [iprBusinessLogs, setIprBusinessLogs] = useState<IprBusinessLog[]>([]),
    [iprOperationLogs, setIprOperationLogs] = useState<IprOperationLog[]>([]),
    [iprHistory, setIprHistory] = useState<IprHistoryItem[]>([]),
    [iprLogOpen, setIprLogOpen] = useState(false),
    [iprBusinessLogDetail, setIprBusinessLogDetail] = useState<IprBusinessLog | null>(null),
    [iprOperationLogDetail, setIprOperationLogDetail] = useState<IprOperationLog | null>(null),
    [iprHistoryDetail, setIprHistoryDetail] = useState<IprHistoryItem | null>(null),
    [iprLogForm] = Form.useForm();
  const [deadlineOffsetOpen, setDeadlineOffsetOpen] = useState(false);
  const [deadlineOffsetForm] = Form.useForm();
  const [iprBatchCreateOpen, setIprBatchCreateOpen] = useState(false);
  const [iprBatchCreateForm] = Form.useForm();
  const [iprBatchCreateErrors, setIprBatchCreateErrors] = useState<IprBatchCreateError[]>([]);
  const [iprRebootOpen, setIprRebootOpen] = useState(false);
  const [iprRebootForm] = Form.useForm();
  const [iprRebootPreview, setIprRebootPreview] = useState<{ source_case_id: number; source_case_no: string; source_title: string; source_status: string; next_serial_no: string } | null>(null);
  const [iprDetailTab, setIprDetailTab] = useState<string>("files");
  const [lawsuitCourts, setLawsuitCourts] = useState<IprLawsuitCourt[]>([]);
  const [lawsuitParties, setLawsuitParties] = useState<IprLawsuitParty[]>([]);
  const [lawsuitFees, setLawsuitFees] = useState<IprLawsuitFee[]>([]);
  const [courtInfoOpen, setCourtInfoOpen] = useState(false);
  const [lawsuitCourtOpen, setLawsuitCourtOpen] = useState(false);
  const [lawsuitPartyOpen, setLawsuitPartyOpen] = useState(false);
  const [lawsuitFeeOpen, setLawsuitFeeOpen] = useState(false);
  const [editingLawsuitCourt, setEditingLawsuitCourt] = useState<IprLawsuitCourt | null>(null);
  const [editingLawsuitParty, setEditingLawsuitParty] = useState<IprLawsuitParty | null>(null);
  const [courtInfoForm] = Form.useForm();
  const [lawsuitCourtForm] = Form.useForm();
  const [lawsuitPartyForm] = Form.useForm();
  const [lawsuitFeeForm] = Form.useForm();
  const batchCaseIds = Form.useWatch("case_ids", iprBatchForm) as number[] | undefined;
  const batchSelectedKinds = useMemo(() => {
    const ids = new Set((batchCaseIds || []).map(Number));
    return [...new Set(items.filter((item) => ids.has(item.id)).map((item) => String(item.data?.case_kind || "")).filter(Boolean))];
  }, [batchCaseIds, items]);
  const batchAvailableFileTypes = useMemo(() => iprFileTypes.filter((item) => {
    const applicableKinds = item.case_kinds || [];
    return !applicableKinds.length || batchSelectedKinds.every((caseKind) => applicableKinds.includes(caseKind));
  }), [iprFileTypes, batchSelectedKinds]);
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
  const clearIprSectionError = (section: keyof typeof iprSectionErrors) => {
    setIprSectionErrors((current) => ({ ...current, [section]: "" }));
  };
  const setIprSectionError = (section: keyof typeof iprSectionErrors, error: unknown) => {
    setIprSectionErrors((current) => ({
      ...current,
      [section]: section === "tasks"
        ? getIprApiErrorMessage(error, "案件任务加载失败")
        : getIprSectionLoadError(section, error),
    }));
  };
  const handledDetailTarget = useRef("");
  const reviewView = initialView === "ipr-review";
  const load = async (
    nextPage = page,
    nextPageSize = pageSize,
    nextKeyword = keyword,
    nextReminderTypeId = reminderTypeId,
  ) => {
    setLoading(true);
    try {
      const { data } = await api.get("/ipr/cases", {
        params: {
          case_kind: kind,
          case_category: caseCategoryFilter || undefined,
          record_status: reviewView ? "待立案审核" : "",
          role_view: roleView?.roleView,
          keyword: nextKeyword,
          annual_fee_monitoring: annualFeeMonitoringFilter || undefined,
          reminder_type_id: nextReminderTypeId || undefined,
          page: nextPage,
          page_size: nextPageSize,
        },
      });
      setItems(data.items || []);
      setTotal(data.total);
      setPage(data.page ?? nextPage);
      setPageSize(data.page_size ?? nextPageSize);
      setPages(data.pages ?? (data.total ? Math.ceil(data.total / nextPageSize) : 0));
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "知识产权案件加载失败");
    } finally {
      setLoading(false);
    }
  };
  const loadLegacyHistory = async (nextKeyword = legacyHistoryKeyword) => {
    setLegacyHistoryLoading(true);
    try {
      const { data } = await api.get<{ items: LegacyIprCaseListItem[]; total: number }>("/legacy-ipr-history/cases", {
        params: { keyword: nextKeyword, page: 1, page_size: 100 },
      });
      setLegacyHistoryItems(data.items || []);
      setLegacyHistoryTotal(data.total || 0);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Historical IPR cases are unavailable");
    } finally {
      setLegacyHistoryLoading(false);
    }
  };
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
      .get<{ items: Customer[] }>("/customers", { params: { page_size: 100 } })
      .then(({ data }) => setCustomers(data.items || []))
      .catch(() => setCustomers([]));
    void api
      .get<{ role?: string; username?: string }>("/auth/me")
      .then(({ data }) => setProfile(data))
      .catch(() => setProfile({}));
    void api
      .get<{ items: Array<{ username?: string; label?: string; value?: string }> }>("/people/options")
      .then(({ data }) => setPeopleOptions((data.items || [])
        .map((item) => ({
          username: String(item.username || "").trim(),
          label: String(item.label || item.value || "").trim(),
        }))
        .filter((item) => item.username && item.label)))
      .catch(() => setPeopleOptions([]));
  }, [initialView, annualFeeMonitoringFilter, caseCategoryFilter]);
  const resetMainListSearch = () => {
    setKeyword("");
    setAnnualFeeMonitoringFilter("");
    setCaseCategoryFilter("");
    setPage(1);
    setReminderTypeId(null);
    setReminderTypeName("");
  };
  const canManageReminderTypes = ["admin", "manager"].includes(profile.role || "");
  const loadReminderTypes = async () => {
    setReminderTypeLoading(true);
    try {
      const { data } = await api.get<{ items: IprReminderType[] }>("/ipr/reminder-types", {
        params: { include_inactive: canManageReminderTypes || undefined },
      });
      setReminderTypes(data.items || []);
    } catch (error: any) {
      setReminderTypes([]);
      message.error(error?.response?.data?.detail || "案件提醒类型加载失败");
    } finally {
      setReminderTypeLoading(false);
    }
  };
  const loadReminderEventTypes = async () => {
    try {
      const { data } = await api.get<{ items: IprReminderEventOption[] }>("/ipr/reminder-event-types");
      setReminderTypeEventOptions(data.items || []);
    } catch (error: any) {
      setReminderTypeEventOptions([]);
      message.error(error?.response?.data?.detail || "案件提醒事件类型加载失败");
    }
  };
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
      deadline_from: query.deadline_from ? dayjs(query.deadline_from) : undefined,
      deadline_to: query.deadline_to ? dayjs(query.deadline_to) : undefined,
      deadline_within_days: query.deadline_within_days ?? undefined,
      is_default: item?.is_default || false,
      is_active: item?.is_active ?? true,
      sort_order: item?.sort_order ?? 0,
    });
    setReminderTypeEditorOpen(true);
  };
  const saveReminderType = async () => {
    try {
      const values = await reminderTypeForm.validateFields();
      const payload = {
        name: String(values.name || "").trim(),
        query_object: {
          case_kind: values.case_kind || "",
          case_type: String(values.case_type || "").trim(),
          case_phase: String(values.case_phase || "").trim(),
          statuses: values.statuses || [],
          event_type_ids: values.event_type_ids || [],
          annual_fee_monitoring: values.annual_fee_monitoring ?? null,
          deadline_from: values.deadline_from ? formatRequiredDate(values.deadline_from, "起始期限") : null,
          deadline_to: values.deadline_to ? formatRequiredDate(values.deadline_to, "结束期限") : null,
          deadline_within_days: values.deadline_within_days ?? null,
        },
        is_default: !!values.is_default,
        is_active: !!values.is_active,
        sort_order: Number(values.sort_order || 0),
      };
      if (editingReminderType) {
        await api.patch(`/ipr/reminder-types/${editingReminderType.id}`, payload);
        message.success("案件提醒类型已更新");
      } else {
        await api.post("/ipr/reminder-types", payload);
        message.success("案件提醒类型已创建");
      }
      setReminderTypeEditorOpen(false);
      setEditingReminderType(null);
      await loadReminderTypes();
    } catch (error: any) {
      if (!error?.errorFields) message.error(error?.response?.data?.detail || "保存案件提醒类型失败");
    }
  };
  const deleteReminderType = (item: IprReminderType) => {
    Modal.confirm({
      title: `删除案件提醒类型：${item.name}`,
      content: "删除后不能恢复，已按该类型筛选的案件不会被删除。",
      okButtonProps: { danger: true },
      onOk: async () => {
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
          message.error(error?.response?.data?.detail || "删除案件提醒类型失败");
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
      query.statuses?.length ? query.statuses.join("、") : "",
      query.event_type_ids?.length ? `提醒事件：${query.event_type_ids.map((id) => reminderTypeEventOptions.find((item) => item.id === id)?.name || id).join("、")}` : "",
      query.annual_fee_monitoring == null ? "" : query.annual_fee_monitoring ? "年费监控" : "未监控年费",
      query.deadline_within_days == null ? "" : `${query.deadline_within_days} 天内到期`,
      query.deadline_from || query.deadline_to ? `${query.deadline_from || "不限"} 至 ${query.deadline_to || "不限"}` : "",
    ].filter(Boolean);
    return summary.join("｜") || "全部可见知识产权案件";
  };
  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ case_kind: kind || "专利", case_category: "non_litigation", rate: 0 });
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
      deadline: record.data.deadline ? dayjs(record.data.deadline) : undefined,
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
      deadline: record.data.deadline ? dayjs(record.data.deadline) : undefined,
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
      deadline: record.data.deadline ? dayjs(record.data.deadline) : dayjs().add(7, "day"),
      priority: "普通",
    });
    setIprTaskOpen(true);
  };
  const applyDeadlineOffset = async () => {
    try {
      const values = await deadlineOffsetForm.validateFields();
      const deadline = buildIprDeadlineFromOffset({
        baseDate: values.base_date?.format("YYYY-MM-DD"),
        years: values.years,
        months: values.months,
        days: values.days,
      });
      if (!deadline) {
        message.warning("请选择基准日期");
        return;
      }
      form.setFieldValue("deadline", dayjs(deadline));
      setDeadlineOffsetOpen(false);
    } catch (error: any) {
      if (!error?.errorFields) message.error(getIprApiErrorMessage(error, "截止日期计算失败"));
    }
  };
  const create = async () => {
    try {
      const values = await form.validateFields();
      const payload = {
        ...values,
        application_date: values.application_date?.format("YYYY-MM-DD"),
        deadline: values.deadline?.format("YYYY-MM-DD"),
      };
      if (payload.case_category !== "litigation") {
        IPR_LAWSUIT_FIELDS.forEach((field) => delete payload[field]);
      }
      if (editing) {
        await api.patch(`/ipr/cases/${editing.id}`, payload);
        message.success("Draft updated");
      } else {
        await api.post("/ipr/cases", payload);
        message.success("Draft created");
      }
      setCreateOpen(false);
      setEditing(null);
      void load();
    } catch (e: any) {
      if (!e?.errorFields)
        message.error(
          e?.response?.data?.detail ||
            (editing ? "Update failed" : "Create failed"),
        );
    }
  };
  const loadLawsuitManagement = async (caseId: number) => {
    const results = await Promise.allSettled([
        api.get<{ items: IprLawsuitCourt[] }>(`/ipr/lawsuit/cases/${caseId}/courts`),
        api.get<{ items: IprLawsuitParty[] }>(`/ipr/lawsuit/cases/${caseId}/parties`),
        api.get<IprDetailPagePayload<IprRecord>>(`/ipr/cases/${caseId}/fees`),
    ]);
    const [courtsResult, partiesResult, feesResult] = results;
    if (courtsResult.status === "fulfilled") setLawsuitCourts(courtsResult.value.data.items || []);
    else message.error((courtsResult.reason as any)?.response?.data?.detail || "诉讼法院信息加载失败");
    if (partiesResult.status === "fulfilled") setLawsuitParties(partiesResult.value.data.items || []);
    else message.error((partiesResult.reason as any)?.response?.data?.detail || "诉讼当事人加载失败");
    if (feesResult.status === "fulfilled") setLawsuitFees((feesResult.value.data.items || []).map(lawsuitFeeFromRecord));
    else message.error((feesResult.reason as any)?.response?.data?.detail || "诉讼费用加载失败");
  };
  const saveCourtInfo = async () => {
    if (!detail) return;
    try {
      const values = await courtInfoForm.validateFields();
      await api.put(`/ipr/lawsuit/cases/${detail.id}/court-info`, values);
      message.success("诉讼基本信息已保存");
      setCourtInfoOpen(false);
      const { data } = await api.get<IprRecord>(`/ipr/cases/${detail.id}`);
      setDetail(data);
    } catch (error: any) { if (!error?.errorFields) message.error(error?.response?.data?.detail || "诉讼基本信息保存失败"); }
  };
  const saveLawsuitCourt = async () => {
    if (!detail) return;
    try {
      const values = await lawsuitCourtForm.validateFields();
      const payload = { ...values, filing_date: values.filing_date?.format("YYYY-MM-DD"), hearing_date: values.hearing_date?.format("YYYY-MM-DD") };
      if (editingLawsuitCourt) await api.put(`/ipr/lawsuit/cases/${detail.id}/courts/${editingLawsuitCourt.id}`, payload);
      else await api.post(`/ipr/lawsuit/cases/${detail.id}/courts`, payload);
      message.success(editingLawsuitCourt ? "法院信息已更新" : "法院信息已添加");
      setLawsuitCourtOpen(false); setEditingLawsuitCourt(null); await loadLawsuitManagement(detail.id);
    } catch (error: any) { if (!error?.errorFields) message.error(error?.response?.data?.detail || "法院信息保存失败"); }
  };
  const saveLawsuitParty = async () => {
    if (!detail) return;
    try {
      const values = await lawsuitPartyForm.validateFields();
      if (editingLawsuitParty) await api.put(`/ipr/lawsuit/cases/${detail.id}/parties/${editingLawsuitParty.id}`, values);
      else await api.post(`/ipr/lawsuit/cases/${detail.id}/parties`, values);
      message.success(editingLawsuitParty ? "当事人已更新" : "当事人已添加");
      setLawsuitPartyOpen(false); setEditingLawsuitParty(null); await loadLawsuitManagement(detail.id);
    } catch (error: any) { if (!error?.errorFields) message.error(error?.response?.data?.detail || "当事人保存失败"); }
  };
  const createLawsuitFee = async () => {
    if (!detail) return;
    try {
      const values = await lawsuitFeeForm.validateFields();
      const feeOption = IPR_LAWSUIT_FEE_OPTIONS.find((item) => item.value === values.lawsuit_fee_kind);
      if (!feeOption) throw new Error("诉讼费用类型无效");
      await api.post(`/ipr/cases/${detail.id}/fees`, {
        title: feeOption.label,
        fee_type: feeOption.feeType,
        amount: values.amount,
        fee_date: values.fee_date?.format("YYYY-MM-DD"),
        description: values.remark || "",
      });
      message.success("诉讼费用已登记"); setLawsuitFeeOpen(false); await loadLawsuitManagement(detail.id);
    } catch (error: any) { if (!error?.errorFields) message.error(error?.response?.data?.detail || "诉讼费用登记失败"); }
  };
  const deleteLawsuitCourt = (row: IprLawsuitCourt) => {
    if (!detail) return;
    Modal.confirm({ title: "删除诉讼法院信息", content: `确认删除${row.court_level}法院“${row.court_name}”吗？`, okButtonProps: { danger: true }, onOk: async () => {
      await api.delete(`/ipr/lawsuit/cases/${detail.id}/courts/${row.id}`); message.success("法院信息已删除"); await loadLawsuitManagement(detail.id);
    }});
  };
  const deleteLawsuitParty = (row: IprLawsuitParty) => {
    if (!detail) return;
    Modal.confirm({ title: "删除诉讼当事人", content: `确认删除${row.party_type}“${row.name}”吗？`, okButtonProps: { danger: true }, onOk: async () => {
      await api.delete(`/ipr/lawsuit/cases/${detail.id}/parties/${row.id}`); message.success("当事人已删除"); await loadLawsuitManagement(detail.id);
    }});
  };
  const loadAssistedFees = async (
    caseId: number,
    nextPage = assistedFeesPageState.page,
    nextPageSize = assistedFeesPageState.pageSize,
  ) => {
    try {
      const { data } = await api.get<IprDetailPagePayload<AssistedFee>>(
        `/ipr/cases/${caseId}/assisted-fees`,
        { params: { page: nextPage, page_size: nextPageSize } },
      );
      setAssistedFees(data.items || []);
      setCanManageAssistedFees(Boolean(data.capabilities?.can_manage));
      setAssistedFeesPageState({
        page: data.page ?? nextPage,
        pageSize: data.page_size ?? nextPageSize,
        total: data.total ?? data.items?.length ?? 0,
        pages: data.pages ?? 0,
      });
      clearIprSectionError("assistedFees");
    } catch (error) {
      setIprSectionError("assistedFees", error);
    }
  };
  const refreshAssistedFees = () => {
    if (detail) void loadAssistedFees(detail.id, assistedFeesPageState.page, assistedFeesPageState.pageSize);
  };
  const refreshAssistedFeesAndLogs = async (caseId: number) => {
    await Promise.all([loadAssistedFees(caseId), loadIprLogs(caseId)]);
  };
  const loadIprCaseEvents = async (
    caseId: number,
    nextPage = remindersPageState.page,
    nextPageSize = remindersPageState.pageSize,
  ) => {
    try {
      const { data } = await api.get<IprDetailPagePayload<IprCaseEvent>>(
        `/ipr/cases/${caseId}/events`,
        { params: { page: nextPage, page_size: nextPageSize } },
      );
      setIprCaseEvents(data.items || []);
      setRemindersPageState({
        page: data.page ?? nextPage,
        pageSize: data.page_size ?? nextPageSize,
        total: data.total ?? data.items?.length ?? 0,
        pages: data.pages ?? 0,
      });
      clearIprSectionError("reminders");
    } catch (error) {
      setIprSectionError("reminders", error);
    }
  };
  const openBatchCreate = () => {
    iprBatchCreateForm.resetFields();
    iprBatchCreateForm.setFieldsValue({
      case_kind: kind || "专利",
      rows: [{ case_register_date: dayjs(), deadline: dayjs().add(30, "day") }],
    });
    setIprBatchCreateErrors([]);
    setIprBatchCreateOpen(true);
  };
  const createIprCasesBatch = async () => {
    try {
      const values = await iprBatchCreateForm.validateFields();
      const payload = {
        customer: values.customer,
        case_kind: values.case_kind,
        rows: (values.rows || []).map((row: Record<string, any>) => ({
          ...row,
          case_register_date: row.case_register_date?.format("YYYY-MM-DD") || "",
          deadline: row.deadline?.format("YYYY-MM-DD") || "",
        })),
      };
      const { data } = await api.post("/ipr/cases/batch-create", payload);
      const rowErrors = data.errors || [];
      setIprBatchCreateErrors(rowErrors);
      if (data.created_count) {
        message.success(`已创建 ${data.created_count} 件知识产权案件`);
        void load(1, pageSize);
      }
      if (!rowErrors.length) setIprBatchCreateOpen(false);
      else {
        // Successful rows have already committed. Keep only failed rows in the
        // editor so a correction cannot accidentally create the valid rows twice.
        const failedRows = rowErrors
          .map((item: IprBatchCreateError) => values.rows?.[item.row_no - 1])
          .filter(Boolean);
        iprBatchCreateForm.setFieldsValue({ ...values, rows: failedRows });
        message.warning(`${rowErrors.length} 行未创建，请按行提示修改后重新提交`);
      }
    } catch (error: any) {
      const detail = error?.response?.data?.detail;
      const rowErrors = Array.isArray(detail?.errors) ? detail.errors : [];
      if (rowErrors.length) setIprBatchCreateErrors(rowErrors);
      message.error(detail?.message || detail || "批量创建知识产权案件失败");
    }
  };
  const openIprReboot = async (record: IprRecord) => {
    try {
      const { data } = await api.get(`/ipr/cases/${record.id}/reboot-preview`);
      setIprRebootPreview(data);
      iprRebootForm.resetFields();
      setIprRebootOpen(true);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "无法获取案件重提信息");
    }
  };
  const createIprReboot = async () => {
    if (!iprRebootPreview) return;
    try {
      const values = await iprRebootForm.validateFields();
      const { data } = await api.post(`/ipr/cases/${iprRebootPreview.source_case_id}/reboot`, {
        reason: String(values.reason || "").trim(),
      });
      message.success(`已重提为新案件 ${data.serial_no}`);
      setIprRebootOpen(false);
      setIprRebootPreview(null);
      await openDetail(data);
      void load(1, pageSize);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "案件重提失败");
    }
  };
  const loadIprCaseTasks = async (
    caseId: number,
    nextPage = iprTasksPageState.page,
    nextPageSize = iprTasksPageState.pageSize,
  ) => {
    try {
      const { data } = await api.get<IprDetailPagePayload<IprCaseTask>>(
        `/ipr/cases/${caseId}/tasks`,
        { params: { page: nextPage, page_size: nextPageSize } },
      );
      setIprCaseTasks(data.items || []);
      setIprTasksPageState({
        page: data.page ?? nextPage,
        pageSize: data.page_size ?? nextPageSize,
        total: data.total ?? data.items?.length ?? 0,
        pages: data.pages ?? 0,
      });
      clearIprSectionError("tasks");
    } catch (error) {
      setIprSectionError("tasks", error);
    }
  };
  const loadReminderSuppressions = async (caseId: number) => {
    try {
      const { data } = await api.get<{
        event_types: ReminderEventType[];
        suppressed_ids: number[];
      }>(`/ipr/cases/${caseId}/reminder-suppressions`);
      setReminderEventTypes(data.event_types || []);
      setSuppressedIds(data.suppressed_ids || []);
    } catch {
      setReminderEventTypes([]);
      setSuppressedIds([]);
    }
  };
  const loadIprFiles = async (
    caseId: number,
    nextPage = filesPageState.page,
    nextPageSize = filesPageState.pageSize,
  ) => {
    try {
      const { data } = await api.get<IprDetailPagePayload<Attachment>>(
        `/ipr/cases/${caseId}/files`,
        { params: { page: nextPage, page_size: nextPageSize } },
      );
      setAttachments(data.items || []);
      setFilesPageState({
        page: data.page ?? nextPage,
        pageSize: data.page_size ?? nextPageSize,
        total: data.total ?? data.items?.length ?? 0,
        pages: data.pages ?? 0,
      });
      clearIprSectionError("files");
    } catch (error) {
      setIprSectionError("files", error);
    }
  };
  const refreshIprFiles = () => {
    if (detail) void loadIprFiles(detail.id, filesPageState.page, filesPageState.pageSize);
  };
  const loadCaseLawFirms = async (caseId: number) => {
    try {
      const { data } = await api.get<{ items: IprLawFirm[] }>(`/ipr/cases/${caseId}/law-firms`);
      setCaseLawFirms(data.items || []);
    } catch {
      setCaseLawFirms([]);
    }
  };
  const openLawFirmSelector = async () => {
    if (!detail) return;
    try {
      const { data } = await api.get<{ items: IprLawFirmCandidate[]; selected_ids: number[] }>(`/ipr/cases/${detail.id}/law-firms/candidates`);
      setLawFirmCandidates(data.items || []);
      setLawFirmSelection(data.selected_ids || []);
      setLawFirmOpen(true);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "协作律所候选加载失败");
    }
  };
  const saveCaseLawFirms = async () => {
    if (!detail) return;
    try {
      await api.put(`/ipr/cases/${detail.id}/law-firms`, buildIprCaseLawFirmPayload({ lawFirmIds: lawFirmSelection }));
      message.success("协作律所已保存");
      setLawFirmOpen(false);
      await loadCaseLawFirms(detail.id);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "协作律所保存失败");
    }
  };
  const loadCaseCustomers = async (caseId: number) => {
    try {
      const { data } = await api.get<{ items: IprCaseCustomer[] }>(`/ipr/cases/${caseId}/customers`);
      setCaseCustomers(data.items || []);
    } catch {
      setCaseCustomers([]);
    }
  };
  const loadCaseContacts = async (caseId: number) => {
    try {
      const { data } = await api.get<{ items: IprCaseContact[] }>(`/ipr/cases/${caseId}/customer-contacts`);
      setCaseContacts(data.items || []);
    } catch {
      setCaseContacts([]);
    }
  };
  const loadIprLogs = async (caseId: number) => {
    try {
      const { data } = await api.get<{ business_logs: IprBusinessLog[]; operation_logs: IprOperationLog[] }>(`/ipr/cases/${caseId}/logs`);
      setIprBusinessLogs(data.business_logs || []);
      setIprOperationLogs(data.operation_logs || []);
      clearIprSectionError("logs");
    } catch (error) {
      setIprSectionError("logs", error);
    }
  };
  const loadIprHistory = async (caseId: number) => {
    try {
      const { data } = await api.get<{ items: IprHistoryItem[] }>(`/records/${caseId}/history`);
      setIprHistory(data.items || []);
    } catch (e: any) {
      setIprHistory([]);
      message.error(e?.response?.data?.detail || "案件事项记录加载失败");
    }
  };
  const createIprLog = async () => {
    if (!detail) return;
    try {
      const values = await iprLogForm.validateFields();
      await api.post(`/ipr/cases/${detail.id}/logs`, { content: values.content });
      message.success("案件业务日志已保存");
      setIprLogOpen(false); iprLogForm.resetFields();
      await loadIprLogs(detail.id);
    } catch (e: any) {
      if (!e?.errorFields) message.error(e?.response?.data?.detail || "案件业务日志保存失败");
    }
  };
  const deleteIprLog = async (logId: number) => {
    if (!detail) return;
    try {
      await api.delete(`/ipr/cases/${detail.id}/logs/${logId}`);
      message.success("案件业务日志已删除");
      await loadIprLogs(detail.id);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "案件业务日志删除失败");
    }
  };
  const openCustomerSelector = async () => {
    if (!detail) return;
    try {
      const { data } = await api.get<{ items: IprCaseCustomerCandidate[]; selected_ids: number[]; primary_customer_id: number | null }>(`/ipr/cases/${detail.id}/customers/candidates`);
      setCustomerCandidates(data.items || []);
      setCustomerSelection(data.selected_ids || []);
      setPrimaryCustomerId(data.primary_customer_id || data.selected_ids?.[0] || null);
      setCustomerOpen(true);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "客户候选加载失败");
    }
  };
  const saveCaseCustomers = async () => {
    if (!detail) return;
    const validationError = getIprCaseCustomerValidationError({ customerIds: customerSelection, primaryCustomerId });
    if (validationError) { message.warning(validationError); return; }
    try {
      await api.put(`/ipr/cases/${detail.id}/customers`, buildIprCaseCustomerPayload({ customerIds: customerSelection, primaryCustomerId }));
      message.success("案件客户已保存");
      setCustomerOpen(false);
      await Promise.all([loadCaseCustomers(detail.id), loadCaseContacts(detail.id)]);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "案件客户保存失败");
    }
  };
  const openLinkedCaseCustomer = async (customer: IprCaseCustomer) => {
    try {
      const target = await resolveCustomerDetailTarget({
        id: customer.customer_id,
        serial_no: customer.customer_no,
        title: customer.name,
      });
      if (!target) {
        message.warning("未找到关联客户或当前账号无权查看");
        return;
      }
      rememberCustomerDetailTarget(target);
      onNavigate?.("customer-company");
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "关联客户加载失败");
    }
  };
  const openLegacyIprCurrentCustomer = async (customerRecordId: number) => {
    try {
      const target = await resolveCustomerDetailTarget({ id: customerRecordId });
      if (!target) {
        message.warning("关联客户不存在或无权查看");
        return;
      }
      rememberCustomerDetailTarget(target);
      onNavigate?.("customer-company");
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "关联客户加载失败");
    }
  };
  const openLinkedCaseCustomerCases = (customer: IprCaseCustomer) => {
    const customerKeyword = customer.customer_no || customer.name || "";
    setDetail(null);
    setKeyword(customerKeyword);
    void load(1, pageSize, customerKeyword);
  };
  const openMainListCustomerCases = (record: IprRecord) => {
    const customerKeyword = String(record.customer || record.data.customer_no || "").trim();
    if (!customerKeyword) {
      message.warning("当前案件未关联客户");
      return;
    }
    setKeyword(customerKeyword);
    setPage(1);
    void load(1, pageSize, customerKeyword);
  };
  const openContactSelector = async (customer: IprCaseCustomer) => {
    if (!detail) return;
    try {
      const { data } = await api.get<{ items: CustomerContact[]; document_contact_ids: string[]; technology_contact_ids: string[] }>(`/ipr/cases/${detail.id}/customers/${customer.customer_id}/contact-candidates`);
      setContactCustomer(customer);
      setContactCandidates(data.items || []);
      setDocumentContactIds(data.document_contact_ids || []);
      setTechnologyContactIds(data.technology_contact_ids || []);
      setContactOpen(true);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "案件联系人候选加载失败");
    }
  };
  const saveCaseContacts = async () => {
    if (!detail || !contactCustomer) return;
    try {
      await api.put(`/ipr/cases/${detail.id}/customer-contacts`, buildIprCaseContactPayload({ customerId: contactCustomer.customer_id, documentContactIds, technologyContactIds }));
      message.success("案件联系人已保存");
      setContactOpen(false);
      await loadCaseContacts(detail.id);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "案件联系人保存失败");
    }
  };
  const loadIprFileTypes = async (caseKind: string) => {
    try {
      const { data } = await api.get<{ items: IprFileType[] }>(
        "/ipr/case-file-types",
        { params: { case_kind: caseKind } },
      );
      setIprFileTypes(data.items || []);
    } catch (e: any) {
      setIprFileTypes([]);
      message.error(e?.response?.data?.detail || "案件文档类型加载失败");
    }
  };
  const openDetail = async (record: IprRecord) => {
    setDetail(record);
    setIprDetailTab("files");
    setLawsuitCourts([]); setLawsuitParties([]); setLawsuitFees([]);
    setAttachments([]);
    setIprBusinessLogs([]);
    setIprOperationLogs([]);
    setAssistedFees([]);
    setCanManageAssistedFees(false);
    setIprCaseEvents([]);
    setIprCaseTasks([]);
    setFilesPageState({ page: IPR_DETAIL_DEFAULT_PAGE, pageSize: IPR_DETAIL_DEFAULT_PAGE_SIZE, total: 0, pages: 0 });
    setRemindersPageState({ page: IPR_DETAIL_DEFAULT_PAGE, pageSize: IPR_DETAIL_DEFAULT_PAGE_SIZE, total: 0, pages: 0 });
    setIprTasksPageState({ page: IPR_DETAIL_DEFAULT_PAGE, pageSize: IPR_DETAIL_DEFAULT_PAGE_SIZE, total: 0, pages: 0 });
    setAssistedFeesPageState({ page: IPR_DETAIL_DEFAULT_PAGE, pageSize: IPR_DETAIL_DEFAULT_PAGE_SIZE, total: 0, pages: 0 });
    setIprSectionErrors({ files: "", logs: "", reminders: "", tasks: "", assistedFees: "" });
    try {
      await Promise.all([
        loadIprFiles(record.id, IPR_DETAIL_DEFAULT_PAGE, IPR_DETAIL_DEFAULT_PAGE_SIZE),
        loadCaseLawFirms(record.id),
        loadCaseCustomers(record.id),
        loadCaseContacts(record.id),
        loadIprLogs(record.id),
        loadIprHistory(record.id),
        loadAssistedFees(record.id, IPR_DETAIL_DEFAULT_PAGE, IPR_DETAIL_DEFAULT_PAGE_SIZE),
        loadIprCaseEvents(record.id, IPR_DETAIL_DEFAULT_PAGE, IPR_DETAIL_DEFAULT_PAGE_SIZE),
        loadIprCaseTasks(record.id, IPR_DETAIL_DEFAULT_PAGE, IPR_DETAIL_DEFAULT_PAGE_SIZE),
        loadReminderSuppressions(record.id),
        ...(isIprLawsuit(record) ? [loadLawsuitManagement(record.id)] : []),
      ]);
    } catch (error) {
      message.error(getIprApiErrorMessage(error, "案件详情加载失败"));
    }
  };
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const legacyRecordId = new URLSearchParams(window.location.search).get("record_id");
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
            "未找到关联知识产权案件或当前账号无权查看",
        ),
      );
  }, [items, initialView, kind]);
  const generateDocument = async (documentType: string) => {
    if (!detail) return;
    try {
      const { data } = await api.post(
        `/ipr/cases/${detail.id}/documents/${documentType}`,
      );
      setAttachments((items) => [data, ...items]);
      message.success("案件文书已生成并归入案件附件");
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "案件文书生成失败");
    }
  };
  const downloadAttachment = async (item: Attachment) => {
    try {
      const response = await api.get(`/attachments/${item.id}/download`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = item.original_name;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch {
      message.error("案件附件下载失败");
    }
  };
  const previewAttachment = async (item: Attachment) => {
    const previewWindow = window.open("", "_blank");
    if (!previewWindow) {
      message.warning("预览窗口被浏览器拦截");
      return;
    }
    previewWindow.opener = null;
    try {
      const response = await api.get(`/attachments/${item.id}/download`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(response.data);
      previewWindow.location.href = url;
    } catch {
      previewWindow.close();
      message.error("案件附件预览失败");
    }
  };
  const uploadIprFile = async () => {
    if (!detail) return;
    try {
      const values = await iprFileForm.validateFields();
      if (!iprUploadFile) {
        message.warning("请选择案件文档");
        return;
      }
      const payload = new FormData();
      payload.append("file", iprUploadFile);
      payload.append("category", values.category);
      payload.append(
        "document_date",
        formatRequiredDate(values.document_date, "文档日期"),
      );
      payload.append("remark", values.remark || "");
      const uploadResponse = await api.post(`/ipr/cases/${detail.id}/files`, payload);
      const uploadResult = assertIprMutationSuccess(uploadResponse, "案件文档已上传");
      message.success(uploadResult);
      setIprFileOpen(false);
      setIprUploadFile(null);
      iprFileForm.resetFields();
      await loadIprFiles(detail.id);
    } catch (e: any) {
      if (!e?.errorFields)
        message.error(getIprApiErrorMessage(e, "上传案件文档失败"));
    }
  };
  const uploadIprBatchFile = async () => {
    try {
      const values = await iprBatchForm.validateFields();
      if (!iprBatchFile) { message.warning("请选择案件文档"); return; }
      const payload = new FormData();
      payload.append("file", iprBatchFile); payload.append("case_ids", JSON.stringify(values.case_ids));
      payload.append("category", values.category); payload.append("document_date", formatRequiredDate(values.document_date, "文档日期")); payload.append("remark", values.remark || "");
      const batchUploadResponse = await api.post("/ipr/cases/files/batch-upload", payload);
      const batchUploadResult = assertIprMutationSuccess(
        batchUploadResponse,
        `已向 ${batchUploadResponse.data.created} 个案件上传文档`,
      );
      message.success(batchUploadResult); setIprBatchOpen(false); setIprBatchFile(null); iprBatchForm.resetFields();
    } catch (e: any) { if (!e?.errorFields) message.error(getIprApiErrorMessage(e, "批量上传案件文档失败")); }
  };
  const markIprFileTransmitted = async (row: Attachment) => {
    if (!detail) return;
    try {
      const markResponse = await api.post(
        `/ipr/cases/${detail.id}/files/${row.id}/mark-transmitted`,
        { comment: "" },
      );
      const markResult = assertIprMutationSuccess(markResponse, "已标记为已转");
      message.success(markResult);
      await loadIprFiles(detail.id);
    } catch (e: any) {
      message.error(getIprApiErrorMessage(e, "标记已转失败"));
    }
  };
  const markSelectedIprFilesTransmitted = async () => {
    if (!detail || !selectedIprFileIds.length) return;
    try {
      const batchMarkResponse = await api.post(`/ipr/cases/${detail.id}/files/mark-transmitted`, { attachment_ids: selectedIprFileIds, comment: "" });
      const batchMarkResult = assertIprMutationSuccess(
        batchMarkResponse,
        `已标记 ${batchMarkResponse.data.updated} 份文档为已转`,
      );
      message.success(batchMarkResult);
      setSelectedIprFileIds([]);
      await loadIprFiles(detail.id);
    } catch (e: any) {
      message.error(getIprApiErrorMessage(e, "批量标记已转失败"));
    }
  };
  const deleteIprFile = async (row: Attachment) => {
    if (!detail) return;
    try {
      const deleteResponse = await api.delete(`/ipr/cases/${detail.id}/files/${row.id}`);
      const deleteResult = assertIprMutationSuccess(deleteResponse, "案件文档已删除");
      message.success(deleteResult);
      await loadIprFiles(detail.id);
    } catch (e: any) {
      message.error(getIprApiErrorMessage(e, "删除案件文档失败"));
    }
  };
  const createAssistedFee = async () => {
    if (!detail) return;
    try {
      const values = await assistedForm.validateFields();
      await api.post(`/ipr/cases/${detail.id}/assisted-fees`, values);
      message.success("协助费已提交，等待确认");
      setAssistedOpen(false);
      assistedForm.resetFields();
      await refreshAssistedFeesAndLogs(detail.id);
    } catch (e: any) {
      if (!e?.errorFields)
        message.error(e?.response?.data?.detail || "新增协助费失败");
    }
  };
  const updateAssistedFee = async () => {
    if (!detail || !editingAssistedFee) return;
    try {
      const values = await assistedEditForm.validateFields();
      await api.patch(
        `/ipr/cases/${detail.id}/assisted-fees/${editingAssistedFee.id}`,
        values,
      );
      message.success("协助费已更新");
      setEditingAssistedFee(null);
      assistedEditForm.resetFields();
      await refreshAssistedFeesAndLogs(detail.id);
    } catch (e: any) {
      if (!e?.errorFields)
        message.error(e?.response?.data?.detail || "编辑协助费失败");
    }
  };
  const confirmAssistedFee = async (row: AssistedFee) => {
    if (!detail) return;
    try {
      await api.post(
        `/ipr/cases/${detail.id}/assisted-fees/${row.id}/confirm`,
        {},
      );
      message.success("协助费已确认，等待办理");
      await refreshAssistedFeesAndLogs(detail.id);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "确认协助费失败");
    }
  };
  const transactAssistedFee = async () => {
    if (!detail || !transactTarget) return;
    try {
      const values = await transactForm.validateFields();
      if (!receiptFile) {
        message.warning("请上传协助费回执文件");
        return;
      }
      const payload = new FormData();
      payload.append(
        "response_date",
        formatRequiredDate(values.response_date, "办理日期"),
      );
      payload.append("file", receiptFile);
      payload.append("remark", values.remark || "");
      await api.post(
        `/ipr/cases/${detail.id}/assisted-fees/${transactTarget.id}/transact`,
        payload,
      );
      message.success("协助费已办理并保存回执");
      setTransactTarget(null);
      setReceiptFile(null);
      transactForm.resetFields();
      await refreshAssistedFeesAndLogs(detail.id);
    } catch (e: any) {
      if (!e?.errorFields)
        message.error(e?.response?.data?.detail || "办理协助费失败");
    }
  };
  const deleteAssistedFee = async (row: AssistedFee) => {
    if (!detail) return;
    try {
      await api.delete(`/ipr/cases/${detail.id}/assisted-fees/${row.id}`);
      message.success("协助费已删除");
      await loadAssistedFees(detail.id);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "删除协助费失败");
    }
  };
  const saveIprCaseEvent = async () => {
    if (!detail) return;
    try {
      const values = await iprEventForm.validateFields();
      const payload = {
        event_type_id: Number(values.event_type_id),
        event_date: formatRequiredDate(values.event_date, "事件日期"),
        deadline: formatRequiredDate(values.deadline, "截止日期"),
        content: String(values.content || "").trim(),
      };
      if (editingIprEvent) {
        await api.patch(`/ipr/cases/${detail.id}/events/${editingIprEvent.id}`, payload);
        message.success("案件事件已更新");
      } else {
        await api.post(`/ipr/cases/${detail.id}/events`, payload);
        message.success("案件事件已创建");
      }
      setIprEventOpen(false);
      setEditingIprEvent(null);
      iprEventForm.resetFields();
      await loadIprCaseEvents(detail.id);
    } catch (e: any) {
      if (!e?.errorFields)
        message.error(e?.response?.data?.detail || (editingIprEvent ? "更新案件事件失败" : "创建案件事件失败"));
    }
  };
  const deleteIprCaseEvent = async (row: IprCaseEvent) => {
    if (!detail) return;
    try {
      await api.delete(`/ipr/cases/${detail.id}/events/${row.id}`);
      message.success("案件事件已删除");
      await loadIprCaseEvents(detail.id);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "删除案件事件失败");
    }
  };
  const openIprCaseEvent = (event?: IprCaseEvent) => {
    setEditingIprEvent(event || null);
    iprEventForm.resetFields();
    iprEventForm.setFieldsValue({
      event_type_id: event?.event_type_id,
      event_date: event?.event_date ? dayjs(event.event_date) : dayjs(),
      deadline: event?.deadline ? dayjs(event.deadline) : detail?.data.deadline ? dayjs(detail.data.deadline) : undefined,
      content: event?.content || "",
    });
    setIprEventOpen(true);
  };
  const canManageIprCaseEvent = (row: IprCaseEvent) => row.creator === profile.username || ["admin", "manager"].includes(profile.role || "");
  const createIprCaseTask = async () => {
    if (!detail) return;
    try {
      const values = await iprTaskForm.validateFields();
      await api.post(`/ipr/cases/${detail.id}/tasks`, {
        title: String(values.title || "").trim(),
        owner: String(values.owner || "").trim(),
        deadline: formatRequiredDate(values.deadline, "任务截止日期"),
        priority: values.priority || "普通",
        description: String(values.description || "").trim(),
        source: "案件任务",
        case_record_id: detail.id,
        case_module: "ipr_case",
      });
      message.success("案件任务已创建");
      setIprTaskOpen(false);
      iprTaskForm.resetFields();
      await loadIprCaseTasks(detail.id);
    } catch (e: any) {
      if (!e?.errorFields) message.error(e?.response?.data?.detail || "创建案件任务失败");
    }
  };
  const confirmIprDeletion = (kind: string, label: string, operation: () => Promise<void>) => {
    const prompt = getIprCaseDeletionConfirmation(kind, label);
    Modal.confirm({ ...prompt, onOk: operation });
  };
  const saveSuppressions = async () => {
    if (!detail) return;
    try {
      await api.put(`/ipr/cases/${detail.id}/reminder-suppressions`, {
        event_type_ids: suppressedIds,
      });
      message.success("不监控提醒类型已保存");
      setSuppressionOpen(false);
      await loadReminderSuppressions(detail.id);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "保存不监控设置失败");
    }
  };
  const exportExcel = async () => {
    try {
      const response = await api.get("/ipr/cases/export/excel", {
        params: {
          case_kind: kind,
          record_status: reviewView ? "待立案审核" : "",
          role_view: roleView?.roleView,
          keyword,
          annual_fee_monitoring: annualFeeMonitoringFilter || undefined,
          reminder_type_id: reminderTypeId || undefined,
        },
        responseType: "blob",
      });
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${roleView?.label || kind || "知识产权"}案件清单.xls`;
      anchor.click();
      URL.revokeObjectURL(url);
      message.success("案件清单已导出");
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "案件清单导出失败");
    }
  };
  const openMaintenance = (record: IprRecord) => {
    maintenanceForm.setFieldsValue({
      deadline: record.data.deadline ? dayjs(record.data.deadline) : undefined,
      annual_fee_year: record.data.annual_fee_year,
      rate: record.data.rate,
      comment: "",
    });
    setMaintenanceTarget(record);
  };
  const saveMaintenance = async () => {
    if (!maintenanceTarget) return;
    try {
      const values = await maintenanceForm.validateFields();
      await api.post(`/ipr/cases/${maintenanceTarget.id}/maintenance`, {
        ...values,
        deadline: values.deadline
          ? formatRequiredDate(values.deadline, "办理期限")
          : undefined,
      });
      message.success("期限、年费和费率已维护");
      setMaintenanceTarget(null);
      setDetail(null);
      void load();
    } catch (e: any) {
      if (!e?.errorFields)
        message.error(e?.response?.data?.detail || "案件维护失败");
    }
  };
  const openBatchMaintenance = () => {
    const selected = items.filter((item) => selectedIprCaseIds.includes(item.id));
    if (!selected.length) { message.warning("请先选择至少一个知识产权案件"); return; }
    if (selected.some((item) => item.status !== "在办")) { message.warning("批量维护仅支持在办案件"); return; }
    iprMaintenanceForm.resetFields();
    setIprMaintenanceOpen(true);
  };
  const setAnnualFeeMonitoring = (enabled: boolean) => {
    const selected = items.filter((item) => selectedIprCaseIds.includes(item.id));
    if (!selected.length) { message.warning("请先选择至少一个知识产权案件"); return; }
    if (selected.some((item) => item.status !== "在办")) { message.warning("年费监控仅支持在办案件"); return; }
    Modal.confirm({
      title: enabled ? "加入年费监控" : "放弃年费监控",
      content: `将对已选 ${selected.length} 件在办案件执行${enabled ? "加入" : "放弃"}年费监控。系统会先校验整批权限，任一案件不符合即不会修改任何案件。`,
      okText: "确认",
      onOk: async () => {
        try {
          const { data } = await api.post(`/ipr/cases/annual-fee-monitoring/${enabled ? "add" : "remove"}`, { case_ids: selectedIprCaseIds });
          message.success(`已${enabled ? "加入" : "放弃"} ${data.updated} 件案件的年费监控`);
          setSelectedIprCaseIds([]);
          void load();
        } catch (e: any) {
          message.error(e?.response?.data?.detail || "年费监控调整失败");
          throw e;
        }
      },
    });
  };
  const saveBatchMaintenance = async () => {
    try {
      const values = await iprMaintenanceForm.validateFields();
      const hasValue = Object.entries(values).some(([key, value]) => key !== "comment" && value !== undefined && value !== null && value !== "");
      if (!hasValue) { message.warning("请至少填写一项批量维护字段"); return; }
      const { data } = await api.post("/ipr/cases/batch-maintenance", {
        ...values,
        case_ids: selectedIprCaseIds,
        deadline: values.deadline ? formatRequiredDate(values.deadline, "办理期限") : undefined,
      });
      message.success(`已维护 ${data.updated} 个案件`);
      setIprMaintenanceOpen(false);
      setSelectedIprCaseIds([]);
      void load();
    } catch (e: any) {
      if (!e?.errorFields) message.error(e?.response?.data?.detail || "批量维护失败");
    }
  };
  const action = async (
    record: IprRecord,
    name: "submit" | "close" | "reopen" | "review",
    approved?: boolean,
  ) => {
    let comment = "";
    if (name === "review" && !approved) {
      const prompted = window.prompt("请填写驳回原因");
      if (prompted === null) return;
      comment = prompted;
    }
    const validationError = getIprCaseActionValidationError({
      action: name,
      role: profile.role,
      status: record.status,
      applicationNo: record.data?.application_no,
      approved,
      comment,
    });
    if (validationError) {
      message.warning(validationError);
      return;
    }
    const payload = buildIprCaseActionPayload({ action: name, approved, comment });
    try {
      const response = await api.post(
        `/ipr/cases/${record.id}/${name}`,
        payload,
      );
      const actionResult = normalizeIprCaseActionResponse(response, "操作成功");
      if (!actionResult.ok) throw new Error(actionResult.message);
      message.success(actionResult.message);
      setDetail(null);
      void load();
    } catch (e: any) {
      message.error(getIprCaseActionErrorMessage(e, "操作失败"));
    }
  };
  const columns: TableColumnsType<IprRecord> = useMemo(
    () => [
      {
        title: "案件编号",
        dataIndex: "serial_no",
        width: 195,
        ellipsis: true,
        render: (v: string, row) => (
          <Button type="link" onClick={() => void openDetail(row)}>
            {v}
          </Button>
        ),
      },
      {
        title: "类型",
        width: 80,
        render: (_, row) => (
          <Tag color={row.data.case_kind === "专利" ? "blue" : "purple"}>
            {row.data.case_kind}
          </Tag>
        ),
      },
      { title: "案件名称", dataIndex: "title", width: 220, ellipsis: true },
      {
        title: "申请号/注册号",
        width: 160,
        ellipsis: true,
        render: (_, row) => row.data.application_no || "—",
      },
      {
        title: "申请日",
        width: 110,
        render: (_, row) => row.data.application_date || "—",
      },
      {
        title: "客户",
        dataIndex: "customer",
        width: 160,
        ellipsis: true,
        render: (_, row) => (
          <Button type="link" size="small" onClick={() => openMainListCustomerCases(row)}>
            {row.customer || "-"}
          </Button>
        ),
      },
      {
        title: "处理人",
        width: 110,
        render: (_, row) => row.data.case_manager || "—",
      },
      {
        title: "期限",
        width: 110,
        render: (_, row) => row.data.deadline || "—",
      },
      {
        title: "年费监控",
        width: 100,
        render: (_, row) => row.data.annual_fee_monitoring ? <Tag color="green">监控中</Tag> : <Tag>未监控</Tag>,
      },
      {
        title: "状态",
        width: 110,
        render: (_, row) => (
          <Tag color={statusColor[row.status] || "default"}>{row.status}</Tag>
        ),
      },
      {
        title: "操作",
        fixed: "right",
        width: 250,
        render: (_, row) => (
          <Space size={0}>
            {["草稿", "已驳回"].includes(row.status) && (
              <Button type="link" onClick={() => openEdit(row)}>
                编辑
              </Button>
            )}
            {["草稿", "已驳回"].includes(row.status) && (
              <Button type="link" onClick={() => action(row, "submit")}>
                提交审核
              </Button>
            )}
            {row.status === "在办" && (
              <Button type="link" danger onClick={() => action(row, "close")}>
                结案
              </Button>
            )}
            {row.status === "已结案" &&
              ["admin", "manager"].includes(profile.role || "") && (
                <Button type="link" onClick={() => action(row, "reopen")}>
                  重新开启
                </Button>
              )}
            {!isLegacyIprRecord(row) && <Button type="link" onClick={() => void openIprReboot(row)}>
              案件重提
            </Button>}
            {reviewView &&
              row.status === "待立案审核" &&
              ["admin", "manager"].includes(profile.role || "") && (
                <>
                  <Button
                    type="link"
                    onClick={() => action(row, "review", true)}
                  >
                    通过
                  </Button>
                  <Button
                    type="link"
                    danger
                    onClick={() => action(row, "review", false)}
                  >
                    驳回
                  </Button>
                </>
              )}
          </Space>
        ),
      },
    ],
    [pageSize, profile.role, reviewView],
  );
  const filesPagination = {
    current: filesPageState.page,
    pageSize: filesPageState.pageSize,
    total: filesPageState.total,
    showSizeChanger: true,
    pageSizeOptions: ["15", "20", "50"],
    onChange: (nextPage: number, nextPageSize: number) => {
      if (detail) void loadIprFiles(detail.id, nextPage, nextPageSize);
    },
  };
  const assistedFeesPagination = {
    current: assistedFeesPageState.page,
    pageSize: assistedFeesPageState.pageSize,
    total: assistedFeesPageState.total,
    showSizeChanger: true,
    pageSizeOptions: ["15", "20", "50"],
    onChange: (nextPage: number, nextPageSize: number) => {
      if (detail) void loadAssistedFees(detail.id, nextPage, nextPageSize);
    },
  };
  const remindersPagination = {
    current: remindersPageState.page,
    pageSize: remindersPageState.pageSize,
    total: remindersPageState.total,
    showSizeChanger: true,
    pageSizeOptions: ["15", "20", "50"],
    onChange: (nextPage: number, nextPageSize: number) => {
      if (detail) void loadIprCaseEvents(detail.id, nextPage, nextPageSize);
    },
  };
  const iprTasksPagination = {
    current: iprTasksPageState.page,
    pageSize: iprTasksPageState.pageSize,
    total: iprTasksPageState.total,
    showSizeChanger: true,
    pageSizeOptions: ["15", "20", "50"],
    onChange: (nextPage: number, nextPageSize: number) => {
      if (detail) void loadIprCaseTasks(detail.id, nextPage, nextPageSize);
    },
  };
  return (
    <div className="page-shell">
      <Card
        title={reviewView ? "知识产权立案审核" : `${roleView?.label || kind || "全部"}案件台账`}
        extra={
          !reviewView && (
            <Space>
              {roleView ? <Tag color="blue">身份筛选：{roleView.label}</Tag> : null}
              <Input
                allowClear
                placeholder="编号、名称、客户、申请号"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                onPressEnter={() => void load(1, pageSize)}
                style={{ width: 220 }}
              />
              <Button onClick={() => void load(1, pageSize)}>查询</Button>
              <Select
                value={caseCategoryFilter}
                onChange={setCaseCategoryFilter}
                style={{ width: 120 }}
                options={[{ value: "", label: "全部案件" }, { value: "litigation", label: "诉讼案件" }, { value: "non_litigation", label: "非诉案件" }]}
              />
              <Button onClick={resetMainListSearch}>重置</Button>
              <Button onClick={openReminderTypeWorkbench}>案件提醒类型</Button>
              <Button onClick={openLegacyHistory}>Historical read-only cases</Button>
              {reminderTypeId ? <Tag closable onClose={() => { setReminderTypeId(null); setReminderTypeName(""); void load(1, pageSize, keyword, null); }}>提醒类型：{reminderTypeName || reminderTypeId}</Tag> : null}
              <Select
                value={annualFeeMonitoringFilter}
                onChange={setAnnualFeeMonitoringFilter}
                style={{ width: 112 }}
                options={[{ value: "", label: "全部年费" }, { value: "true", label: "监控中" }, { value: "false", label: "未监控" }]}
              />
              <Button onClick={() => void exportExcel()}>导出Excel</Button>
              <Button onClick={openBatchCreate}>批量新建案件</Button>
              <Button onClick={() => { iprBatchForm.resetFields(); iprBatchForm.setFieldsValue({ document_date: dayjs() }); void loadIprFileTypes(""); setIprBatchFile(null); setIprBatchOpen(true); }}>批量上传文档</Button>
              <Button onClick={() => onNavigate?.("ipr-custom-file-import")}>案件自定义文件导入</Button>
              <Button onClick={() => onNavigate?.("case-files-receipt")}>案件票据导入</Button>
              <Button onClick={() => onNavigate?.("case-files-invoice")}>案件发票导入</Button>
              <Button disabled={!selectedIprCaseIds.length} onClick={openBatchMaintenance}>批量维护</Button>
              <Button disabled={!selectedIprCaseIds.length} onClick={() => setAnnualFeeMonitoring(true)}>加入年费监控</Button>
              <Button disabled={!selectedIprCaseIds.length} onClick={() => setAnnualFeeMonitoring(false)}>放弃年费监控</Button>
              <Button type="primary" onClick={openCreate}>
                新建{kind || "知识产权"}案件
              </Button>
            </Space>
          )
        }
      >
        <Table
          rowKey="id"
          size="small"
          loading={loading}
          columns={columns}
          dataSource={items}
          rowSelection={{ selectedRowKeys: selectedIprCaseIds, onChange: (keys) => setSelectedIprCaseIds(keys.map(Number)) }}
          scroll={{ x: 1250 }}
          pagination={{
            current: page,
            pageSize: pageSize,
            total,
            showSizeChanger: true,
            pageSizeOptions: ["15", "20", "50", "100"],
            showQuickJumper: { goButton: <Button size="small">GO</Button> },
            showTotal: (t) => "共 " + t + " 条" + (pages ? " / " + pages + " 页" : ""),
            onChange: (nextPage, nextPageSize) => void load(nextPage, nextPageSize),
          }}
        />
      </Card>
      <Drawer
        open={legacyHistoryOpen}
        title="Historical IPR cases (read-only)"
        width={980}
        onClose={() => { setLegacyHistoryOpen(false); setLegacyHistoryCaseId(null); }}
      >
        <Space style={{ marginBottom: 12 }}>
          <Input
            allowClear
            value={legacyHistoryKeyword}
            placeholder="Legacy case number or name"
            onChange={(event) => setLegacyHistoryKeyword(event.target.value)}
            onPressEnter={() => void loadLegacyHistory()}
            style={{ width: 280 }}
          />
          <Button onClick={() => void loadLegacyHistory()}>Search</Button>
          <Tag>{legacyHistoryTotal} historical cases</Tag>
        </Space>
        <Table<LegacyIprCaseListItem>
          rowKey="legacy_case_id"
          size="small"
          loading={legacyHistoryLoading}
          pagination={false}
          dataSource={legacyHistoryItems}
          columns={[
            { title: "Legacy case", dataIndex: "case_no", width: 180, ellipsis: true },
            { title: "Title", dataIndex: "title", width: 240, ellipsis: true },
            { title: "Type", dataIndex: "case_type", width: 120 },
            { title: "Applicant", dataIndex: "applicant", width: 180, ellipsis: true },
            { title: "State", dataIndex: "relationship_state", width: 110 },
            {
              title: "Open",
              fixed: "right",
              width: 190,
              render: (_, row) => <Space size={0}>
                {row.current_case_record_id ? <Button type="link" onClick={() => void api.get<IprRecord>(`/ipr/cases/${row.current_case_record_id}`).then(({ data }) => void openDetail(data))}>Current case</Button> : null}
                <Button type="link" onClick={() => setLegacyHistoryCaseId(row.legacy_case_id)}>Read-only relations</Button>
              </Space>,
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
        {legacyHistoryCaseId !== null ? <IprLegacyHistoryRelations legacyCaseId={legacyHistoryCaseId} onOpenCurrentCustomer={(customerRecordId) => void openLegacyIprCurrentCustomer(customerRecordId)} /> : null}
      </Drawer>
      <Drawer
        open={reminderTypeWorkbenchOpen}
        title="案件提醒类型工作台"
        width={920}
        onClose={() => setReminderTypeWorkbenchOpen(false)}
        extra={
          <Space>
            <Button onClick={() => void loadReminderTypes()}>刷新</Button>
            {canManageReminderTypes ? <Button type="primary" onClick={() => openReminderTypeEditor()}>新建类型</Button> : null}
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
              render: (value: string, row) => <Space><Button type="link" onClick={() => applyReminderType(row)}>{value}</Button>{row.is_default ? <Tag color="blue">默认</Tag> : null}{row.is_active ? null : <Tag>已停用</Tag>}</Space>,
            },
            { title: "筛选条件", width: 300, render: (_, row) => reminderTypeQuerySummary(row.query_object) },
            { title: "当前可见案件", dataIndex: "case_count", width: 125, render: (count: number, row) => <Button type="link" onClick={() => applyReminderType(row)}>{count} 件</Button> },
            { title: "排序", dataIndex: "sort_order", width: 75 },
            {
              title: "操作",
              width: 155,
              render: (_, row) => canManageReminderTypes ? <Space size={0}><Button type="link" onClick={() => openReminderTypeEditor(row)}>编辑</Button><Button type="link" danger disabled={row.is_default} onClick={() => deleteReminderType(row)}>删除</Button></Space> : "—",
            },
          ]}
        />
      </Drawer>
      <Modal
        open={reminderTypeEditorOpen}
        title={editingReminderType ? `编辑提醒类型：${editingReminderType.name}` : "新建案件提醒类型"}
        width={700}
        onCancel={() => { setReminderTypeEditorOpen(false); setEditingReminderType(null); }}
        onOk={() => void saveReminderType()}
        okText="保存"
      >
        <Form form={reminderTypeForm} layout="vertical">
          <div className="form-grid">
            <Form.Item name="name" label="提醒类型名称" rules={[{ required: true, message: "请输入提醒类型名称" }]}>
              <Input maxLength={128} />
            </Form.Item>
            <Form.Item name="sort_order" label="排序" initialValue={0}>
              <InputNumber min={0} max={100000} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item name="case_kind" label="案件类型">
              <Select allowClear options={["专利", "商标"].map((value) => ({ value, label: value }))} />
            </Form.Item>
            <Form.Item name="annual_fee_monitoring" label="年费监控">
              <Select allowClear options={[{ value: true, label: "仅监控中" }, { value: false, label: "仅未监控" }]} />
            </Form.Item>
            <Form.Item name="case_type" label="案件子类型"><Input maxLength={128} /></Form.Item>
            <Form.Item name="case_phase" label="案件阶段"><Input maxLength={128} /></Form.Item>
            <Form.Item name="event_type_ids" label="关联提醒事件">
              <Select mode="multiple" allowClear optionFilterProp="label" options={reminderTypeEventOptions.map((item) => ({ value: item.id, label: item.name }))} />
            </Form.Item>
            <Form.Item name="deadline_from" label="期限起始"><DatePicker style={{ width: "100%" }} /></Form.Item>
            <Form.Item name="deadline_to" label="期限结束"><DatePicker style={{ width: "100%" }} /></Form.Item>
            <Form.Item name="deadline_within_days" label="未来到期天数"><InputNumber min={0} max={3650} style={{ width: "100%" }} /></Form.Item>
            <Form.Item name="statuses" label="案件状态">
              <Select mode="multiple" options={["草稿", "待立案审核", "在办", "已驳回", "已结案"].map((value) => ({ value, label: value }))} />
            </Form.Item>
          </div>
          <Space>
            <Form.Item name="is_default" valuePropName="checked" noStyle><Checkbox>默认类型</Checkbox></Form.Item>
            <Form.Item name="is_active" valuePropName="checked" noStyle><Checkbox>启用</Checkbox></Form.Item>
          </Space>
        </Form>
      </Modal>
      <Modal
        open={iprBatchCreateOpen}
        title="批量新建知识产权案件"
        width={1120}
        onCancel={() => setIprBatchCreateOpen(false)}
        onOk={() => void createIprCasesBatch()}
        okText="提交创建"
      >
        <Alert
          type="info"
          showIcon
          message="与旧系统一致：先选择客户，再逐行填写案件类型、案件阶段、立案日期和处理期限。"
          description="系统先校验全部行；有效行会在同一事务内创建，错误行不会落库，并在下方按行提示。"
          style={{ marginBottom: 16 }}
        />
        {iprBatchCreateErrors.length ? <Alert type="warning" showIcon style={{ marginBottom: 16 }} message="以下行未创建" description={<ul style={{ margin: 0, paddingLeft: 18 }}>{iprBatchCreateErrors.map((item) => <li key={item.row_no}>第 {item.row_no} 行：{item.message}</li>)}</ul>} /> : null}
        <Form form={iprBatchCreateForm} layout="vertical">
          <div className="form-grid">
            <Form.Item name="customer" label="客户" rules={[{ required: true, message: "请选择客户" }]}>
              <Select showSearch optionFilterProp="label" options={customers.map((row) => ({ value: row.title, label: `${row.title}（${row.serial_no}）` }))} />
            </Form.Item>
            <Form.Item name="case_kind" label="案件类别" rules={[{ required: true }]}>
              <Select options={["专利", "商标"].map((value) => ({ value, label: value }))} />
            </Form.Item>
          </div>
          <Form.List name="rows" rules={[{ validator: async (_, rows) => { if (!rows?.length) throw new Error("请至少新增一行案件"); } }]}>
            {(fields, { add, remove }) => <>
              {fields.map((field, index) => (
                <Card key={field.key} size="small" title={`第 ${index + 1} 行`} style={{ marginBottom: 12 }} extra={<Button danger type="link" disabled={fields.length === 1} onClick={() => remove(field.name)}>移除</Button>}>
                  <div className="form-grid">
                    <Form.Item {...field} name={[field.name, "case_type"]} label="案件类型" rules={[{ required: true, message: "请输入案件类型" }]}><Input placeholder="如发明专利申请、商标注册" /></Form.Item>
                    <Form.Item {...field} name={[field.name, "case_phase"]} label="案件阶段" rules={[{ required: true, message: "请输入案件阶段" }]}><Input placeholder="如申请阶段" /></Form.Item>
                    <Form.Item {...field} name={[field.name, "case_register_date"]} label="立案日期" rules={[{ required: true, message: "请选择立案日期" }]}><DatePicker style={{ width: "100%" }} /></Form.Item>
                    <Form.Item {...field} name={[field.name, "deadline"]} label="处理期限" rules={[{ required: true, message: "请选择处理期限" }]}><DatePicker style={{ width: "100%" }} /></Form.Item>
                    <Form.Item {...field} name={[field.name, "title"]} label="案件名称"><Input placeholder="未填写时按案件类型生成" /></Form.Item>
                    <Form.Item {...field} name={[field.name, "application_no"]} label="申请号/注册号"><Input /></Form.Item>
                    <Form.Item {...field} name={[field.name, "application_type"]} label="申请类型"><Input /></Form.Item>
                    <Form.Item {...field} name={[field.name, "applicant"]} label="申请人/权利人"><Input /></Form.Item>
                  </div>
                  <Form.Item {...field} name={[field.name, "description"]} label="说明"><Input.TextArea rows={2} maxLength={2000} /></Form.Item>
                </Card>
              ))}
              <Button onClick={() => add({ case_register_date: dayjs(), deadline: dayjs().add(30, "day") })}>新增一行</Button>
            </>}
          </Form.List>
        </Form>
      </Modal>
      <Modal
        open={iprRebootOpen}
        title="知识产权案件重提"
        onCancel={() => { setIprRebootOpen(false); setIprRebootPreview(null); }}
        onOk={() => void createIprReboot()}
        okText="确认重提"
      >
        {iprRebootPreview ? <>
          <Descriptions bordered size="small" column={1} items={[
            { key: "source", label: "原案件", children: `${iprRebootPreview.source_case_no}｜${iprRebootPreview.source_title}` },
            { key: "status", label: "原案件状态", children: iprRebootPreview.source_status },
            { key: "target", label: "新案件编号", children: iprRebootPreview.next_serial_no },
          ]} />
          <Alert type="info" showIcon style={{ marginTop: 16 }} message="重提会复制业务信息和客户、联系人、协作律所关联，原案件不会被覆盖。新旧案件均会写入可追溯的审计事件。" />
          <Form form={iprRebootForm} layout="vertical" style={{ marginTop: 16 }}>
            <Form.Item name="reason" label="重提说明"><Input.TextArea rows={3} maxLength={1000} /></Form.Item>
          </Form>
        </> : null}
      </Modal>
      <Modal open={iprBatchOpen} title="批量上传知识产权案件文档" onCancel={() => setIprBatchOpen(false)} onOk={() => void uploadIprBatchFile()} okText="批量上传">
        <Form form={iprBatchForm} layout="vertical"><Form.Item name="case_ids" label="目标案件" rules={[{ required: true, message: "请选择至少一个在办案件" }]}><Select mode="multiple" options={items.filter((item) => item.status === "在办").map((item) => ({ value: item.id, label: `${item.serial_no}｜${item.title}` }))}/></Form.Item>{batchSelectedKinds.length > 1 && <div style={{ marginTop: -14, marginBottom: 12, color: "#666" }}>已选择{batchSelectedKinds.join("、")}案件，仅显示同时适用的文档类型。</div>}<Form.Item name="category" label="文档类型" rules={[{ required: true }]}><Select notFoundContent={batchCaseIds?.length ? "没有同时适用于所选案件的文档类型" : "请先选择目标案件"} options={batchAvailableFileTypes.map((item) => ({ value: item.name, label: `${item.name}${item.requires_transmission ? "（待转文）" : ""}` }))}/></Form.Item><Form.Item name="document_date" label="文档日期" rules={[{ required: true }]}><DatePicker style={{ width: "100%" }}/></Form.Item><Form.Item label="案件文档" required><input type="file" accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.png,.jpg,.jpeg,.zip,.rar" onChange={(event) => setIprBatchFile(event.target.files?.[0] || null)}/>{iprBatchFile && <div>{iprBatchFile.name}</div>}</Form.Item><Form.Item name="remark" label="说明"><Input.TextArea rows={2} maxLength={1000}/></Form.Item></Form>
      </Modal>
      <Modal open={iprMaintenanceOpen} title={`批量维护知识产权案件（已选 ${selectedIprCaseIds.length} 件）`} onCancel={() => setIprMaintenanceOpen(false)} onOk={() => void saveBatchMaintenance()} okText="确认维护">
        <p style={{ color: "#666" }}>仅会更新填写的字段；系统会在写入前校验全部目标案件均为当前账号可维护的在办案件，任一案件不符合时不会修改任何案件。</p>
        <Form form={iprMaintenanceForm} layout="vertical">
          <Form.Item name="case_manager" label="案件经办人"><Input placeholder="填写有效系统用户名" /></Form.Item>
          <Form.Item name="deadline" label="办理期限"><DatePicker style={{ width: "100%" }} /></Form.Item>
          <Form.Item name="annual_fee_year" label="首年缴费年度"><InputNumber min={1} max={100} style={{ width: "100%" }} /></Form.Item>
          <Form.Item name="rate" label="减缓比例"><InputNumber min={0} max={1} step={0.01} style={{ width: "100%" }} /></Form.Item>
          <Form.Item name="comment" label="维护说明"><Input.TextArea rows={2} maxLength={1000} /></Form.Item>
        </Form>
      </Modal>
      <Modal
        open={createOpen}
        title={
          editing
            ? `编辑知识产权案件草稿：${editing.serial_no}`
            : "新建知识产权案件草稿"
        }
        width={760}
        onCancel={() => {
          setCreateOpen(false);
          setEditing(null);
        }}
        onOk={create}
        okText={editing ? "保存修改" : "保存草稿"}
      >
        <Form form={form} layout="vertical">
          <div className="form-grid">
            <Form.Item
              name="case_kind"
              label="案件类型"
              rules={[{ required: true }]}
            >
              <Select
                disabled={!!editing}
                options={["专利", "商标"].map((value) => ({
                  value,
                  label: value,
                }))}
              />
            </Form.Item>
            <Form.Item name="case_category" label="案件属性" rules={[{ required: true }]}>
              <Select options={[{ value: "non_litigation", label: "非诉案件" }, { value: "litigation", label: "诉讼案件" }]} />
            </Form.Item>
            <Form.Item
              name="customer"
              label="客户"
              rules={[{ required: true }]}
            >
              <Select
                disabled={!!editing}
                showSearch
                optionFilterProp="label"
                options={customers.map((row) => ({
                  value: row.title,
                  label: `${row.title}（${row.serial_no}）`,
                }))}
              />
            </Form.Item>
            <Form.Item
              name="title"
              label="案件名称"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <Form.Item name="application_no" label="申请号/注册号">
              <Input />
            </Form.Item>
            <Form.Item name="application_type" label="申请类型">
              <Input placeholder="如发明、实用新型、外观设计、注册商标" />
            </Form.Item>
            <Form.Item name="applicant" label="申请人/权利人">
              <Input />
            </Form.Item>
            <Form.Item name="case_manager" label="案件负责人">
              <Input />
            </Form.Item>
            <Form.Item noStyle shouldUpdate={(previous, current) => previous.case_category !== current.case_category}>
              {({ getFieldValue }) => getFieldValue("case_category") === "litigation" ? <>
                <Form.Item name="court_case_no" label="法院案号"><Input /></Form.Item>
                <Form.Item name="court_name" label="受理法院"><Input /></Form.Item>
                <Form.Item name="judge" label="承办法官"><Input /></Form.Item>
                <Form.Item name="clerk" label="书记员"><Input /></Form.Item>
                <Form.Item name="plaintiff" label="原告"><Input /></Form.Item>
                <Form.Item name="defendant" label="被告"><Input /></Form.Item>
                <Form.Item name="third_parties" label="第三人"><Input /></Form.Item>
              </> : null}
            </Form.Item>
            <Form.Item name="application_date" label="申请日期">
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item name="deadline" label="办理期限">
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Button
              type="link"
              onClick={() => {
                deadlineOffsetForm.resetFields();
                deadlineOffsetForm.setFieldValue("base_date", dayjs());
                setDeadlineOffsetOpen(true);
              }}
            >
              按基准日计算截止日期
            </Button>
            <Form.Item name="annual_fee_year" label="年费年度">
              <InputNumber min={1} max={100} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item name="rate" label="费率">
              <InputNumber
                min={0}
                max={1}
                step={0.01}
                style={{ width: "100%" }}
              />
            </Form.Item>
          </div>
          <Form.Item name="description" label="说明">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={deadlineOffsetOpen}
        title="案件截止日期设定"
        onCancel={() => setDeadlineOffsetOpen(false)}
        onOk={() => void applyDeadlineOffset()}
        okText="确定"
      >
        <Form form={deadlineOffsetForm} layout="vertical">
          <Form.Item name="base_date" label="基准日期" rules={[{ required: true }]}>
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Space.Compact block>
            <Form.Item name="years" label="年" initialValue={0} style={{ flex: 1 }}>
              <InputNumber style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item name="months" label="月" initialValue={0} style={{ flex: 1 }}>
              <InputNumber style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item name="days" label="日" initialValue={0} style={{ flex: 1 }}>
              <InputNumber style={{ width: "100%" }} />
            </Form.Item>
          </Space.Compact>
        </Form>
      </Modal>
      <Drawer
        open={!!detail}
        title={
          detail ? `${detail.data.case_kind}案件详情：${detail.serial_no}` : ""
        }
        width={820}
        extra={detail && !isLegacyIprRecord(detail) ? <Space size={0}><Button onClick={() => openCopy(detail)}>复制案件</Button><Button onClick={() => void openIprReboot(detail)}>案件重提</Button><Button onClick={() => openIprCaseTask(detail)}>案件任务</Button></Space> : null}
        onClose={() => setDetail(null)}
      >
        {detail && (
          <>
            {isLegacyIprRecord(detail) ? <Alert type="info" showIcon message="Historical IPR record: read-only" style={{ marginBottom: 12 }} /> : null}
            <Descriptions
              bordered
              size="small"
              column={2}
              items={[
                {
                  key: "serial",
                  label: "案件编号",
                  children: detail.serial_no,
                },
                { key: "status", label: "状态", children: detail.status },
                { key: "customer", label: "客户", children: detail.customer },
                {
                  key: "application",
                  label: "申请号/注册号",
                  children: detail.data.application_no || "—",
                },
                ...(isIprLawsuit(detail) ? [
                  { key: "case-category", label: "案件属性", children: <Tag color="red">诉讼案件</Tag> },
                  { key: "court-case-no", label: "法院案号", children: detail.data.court_case_no || "—" },
                  { key: "court", label: "受理法院", children: detail.data.court_name || "—" },
                  { key: "judge", label: "承办法官 / 书记员", children: [detail.data.judge, detail.data.clerk].filter(Boolean).join(" / ") || "—" },
                  { key: "plaintiff", label: "原告", children: detail.data.plaintiff || "—" },
                  { key: "defendant", label: "被告", children: detail.data.defendant || "—" },
                  { key: "third-parties", label: "第三人", children: detail.data.third_parties || "—" },
                ] : [{ key: "case-category", label: "案件属性", children: <Tag>非诉案件</Tag> }]),
                {
                  key: "type",
                  label: "申请类型",
                  children: detail.data.application_type || "—",
                },
                {
                  key: "applicant",
                  label: "申请人/权利人",
                  children: detail.data.applicant || "—",
                },
                {
                  key: "manager",
                  label: "案件负责人",
                  children: detail.data.case_manager || "—",
                },
                {
                  key: "date",
                  label: "申请日期",
                  children: detail.data.application_date || "—",
                },
                {
                  key: "deadline",
                  label: "办理期限",
                  children: detail.data.deadline || "—",
                },
                {
                  key: "annual",
                  label: "年费年度",
                  children: detail.data.annual_fee_year || "—",
                },
                {
                  key: "annual-monitoring",
                  label: "年费监控",
                  children: detail.data.annual_fee_monitoring ? <Tag color="green">监控中</Tag> : <Tag>未监控</Tag>,
                },
                {
                  key: "rate",
                  label: "费率",
                  children: detail.data.rate ?? "—",
                },
                {
                  key: "reboot-source",
                  label: "重提原案件",
                  children: detail.data.reboot_source_case_id ? <Button type="link" size="small" onClick={() => void api.get(`/ipr/cases/${detail.data.reboot_source_case_id}`).then(({ data }) => openDetail(data))}>{detail.data.reboot_source_case_no || detail.data.reboot_source_case_id}</Button> : "—",
                },
                {
                  key: "reboot-targets",
                  label: "已重提案件",
                  children: Array.isArray(detail.data.reboot_case_ids) && detail.data.reboot_case_ids.length ? <Space size={0} wrap>{detail.data.reboot_case_ids.map((caseId: number, index: number) => <Button key={caseId} type="link" size="small" onClick={() => void api.get(`/ipr/cases/${caseId}`).then(({ data }) => openDetail(data))}>{detail.data.reboot_case_nos?.[index] || caseId}</Button>)}</Space> : "—",
                },
                {
                  key: "description",
                  label: "说明",
                  children: detail.description || "—",
                  span: 2,
                },
              ]}
            />
            <Card
              size="small"
              title="案件业务日志与操作日志"
              style={{ marginTop: 16 }}
              extra={detail.status === "草稿" || detail.status === "已驳回" || detail.status === "在办" ? <Button size="small" onClick={() => { iprLogForm.resetFields(); setIprLogOpen(true); }}>新增业务日志</Button> : null}
            >
              {iprSectionErrors.logs ? <Alert type="error" showIcon message={iprSectionErrors.logs} style={{ marginBottom: 12 }} /> : null}
              <Table
                rowKey="id"
                size="small"
                pagination={false}
                locale={{ emptyText: "暂未填写业务日志" }}
                dataSource={iprBusinessLogs}
                columns={[
                  {
                    title: "内容",
                    dataIndex: "content",
                    ellipsis: true,
                    render: (content: string, row: IprBusinessLog) => (
                      <Button type="link" onClick={() => setIprBusinessLogDetail(row)}>
                        {content}
                      </Button>
                    ),
                  },
                  { title: "创建人", dataIndex: "created_by_display_name", width: 110, render: personDisplayName },
                  { title: "时间", dataIndex: "created_at", width: 170, render: (value) => value ? dayjs(value).format("YYYY-MM-DD HH:mm") : "—" },
                  { title: "操作", width: 90, render: (_, row) => row.created_by === profile.username || ["admin", "manager"].includes(profile.role || "") ? <Button danger type="link" size="small" onClick={() => confirmIprDeletion("log", row.content, () => deleteIprLog(row.id))}>删除</Button> : "—" },
                ]}
              />
              <Table
                rowKey="id"
                size="small"
                pagination={false}
                style={{ marginTop: 12 }}
                locale={{ emptyText: "暂未产生操作日志" }}
                dataSource={iprOperationLogs}
                columns={[
                  {
                    title: "操作",
                    dataIndex: "action",
                    width: 180,
                    render: (action: string, row: IprOperationLog) => (
                      <Button type="link" onClick={() => setIprOperationLogDetail(row)}>
                        {action}
                      </Button>
                    ),
                  },
                  { title: "说明", dataIndex: "comment", ellipsis: true, render: (value) => value || "—" },
                  { title: "操作人", dataIndex: "operator_display_name", width: 110, render: personDisplayName },
                  { title: "时间", dataIndex: "created_at", width: 170, render: (value) => value ? dayjs(value).format("YYYY-MM-DD HH:mm") : "—" },
                ]}
              />
            </Card>
            <Card
              size="small"
              title="案件事项记录"
              style={{ marginTop: 16 }}
            >
              <Table
                rowKey="id"
                size="small"
                pagination={false}
                dataSource={iprHistory}
                locale={{ emptyText: "暂无案件事项记录" }}
                columns={[
                  {
                    title: "事项",
                    dataIndex: "action",
                    width: 160,
                    render: (action: string, row: IprHistoryItem) => (
                      <Button type="link" onClick={() => setIprHistoryDetail(row)}>
                        {action}
                      </Button>
                    ),
                  },
                  { title: "状态变化", width: 180, render: (_, row: IprHistoryItem) => row.from_status || row.to_status ? `${row.from_status || "—"} → ${row.to_status || "—"}` : "—" },
                  { title: "说明", dataIndex: "comment", ellipsis: true },
                  { title: "操作人", dataIndex: "operator_display_name", width: 110, render: personDisplayName },
                  { title: "时间", dataIndex: "created_at", width: 170, render: (value) => value ? dayjs(value).format("YYYY-MM-DD HH:mm") : "—" },
                ]}
              />
            </Card>
            <Card
              size="small"
              title="案件客户与联系人"
              style={{ marginTop: 16 }}
              extra={detail.status === "草稿" || detail.status === "已驳回" || detail.status === "在办" ? <Button size="small" onClick={() => void openCustomerSelector()}>维护案件客户</Button> : null}
            >
              <Table
                rowKey="customer_id"
                size="small"
                pagination={false}
                locale={{ emptyText: "暂未关联案件客户" }}
                dataSource={caseCustomers}
                columns={[
                  { title: "客户编号", dataIndex: "customer_no", width: 150, render: (value, row) => <Button type="link" size="small" onClick={() => void openLinkedCaseCustomer(row)}>{value || "—"}</Button> },
                  { title: "客户名称", dataIndex: "name", render: (value, row) => <Space><Button type="link" size="small" onClick={() => openLinkedCaseCustomerCases(row)}>{value || "—"}</Button>{row.is_primary ? <Tag color="blue">主客户</Tag> : null}</Space> },
                  { title: "状态", dataIndex: "status", width: 110 },
                  { title: "联系人", width: 130, render: (_, row) => <Button type="link" size="small" onClick={() => void openContactSelector(row)}>维护联系人</Button> },
                ]}
              />
              <Table
                rowKey="id"
                size="small"
                pagination={false}
                style={{ marginTop: 12 }}
                locale={{ emptyText: "尚未选择文书联系人或技术联系人" }}
                dataSource={caseContacts}
                columns={[
                  { title: "客户", dataIndex: "customer_name", width: 150 },
                  { title: "联系人", dataIndex: "name", width: 120 },
                  { title: "角色", dataIndex: "contact_role", width: 100, render: (value) => value === "document" ? "文书联系人" : "技术联系人" },
                  { title: "电话", dataIndex: "phone", width: 140, render: (value) => value || "—" },
                  { title: "邮箱", dataIndex: "email", ellipsis: true, render: (value) => value || "—" },
                ]}
              />
            </Card>
            <Card
              size="small"
              title="协作律所"
              style={{ marginTop: 16 }}
              extra={detail.status === "草稿" || detail.status === "已驳回" || detail.status === "在办" ? <Button size="small" onClick={() => void openLawFirmSelector()}>维护协作律所</Button> : null}
            >
              {caseLawFirms.length ? <Table
                rowKey="id"
                size="small"
                pagination={false}
                dataSource={caseLawFirms}
                columns={[
                  { title: "律所编号", dataIndex: "code", width: 140 },
                  { title: "律所名称", dataIndex: "name", width: 220 },
                  { title: "电话", dataIndex: "phone", width: 150, render: (value) => value || "—" },
                  { title: "邮箱", dataIndex: "email", ellipsis: true, render: (value) => value || "—" },
                ]}
              /> : "暂未选择协作律所"}
            </Card>
            {Number(detail.data?.legacy_ipr_case_id || detail.data?.legacy_case_id || 0) > 0 ? (
              <div style={{ marginTop: 16 }}>
                <IprLegacyHistoryRelations
                  legacyCaseId={Number(detail.data?.legacy_ipr_case_id || detail.data?.legacy_case_id)}
                  onOpenCurrentCustomer={(customerRecordId) => void openLegacyIprCurrentCustomer(customerRecordId)}
                />
              </div>
            ) : null}
            <Tabs
              activeKey={iprDetailTab}
              onChange={setIprDetailTab}
              items={[
                ...(isIprLawsuit(detail) ? [{
                  key: "lawsuit",
                  label: "诉讼管理",
                  children: <>
                    <Alert type="info" showIcon message="诉讼案件文件在“文档信息”页签中统一管理，可上传、下载及标记转文。" style={{ marginBottom: 16 }} />
                    <Card size="small" title="诉讼基本信息" extra={<Button size="small" onClick={() => { courtInfoForm.setFieldsValue(detail.data); setCourtInfoOpen(true); }}>维护诉讼信息</Button>}>
                      <Descriptions size="small" column={2} items={[
                        { key: "caseNo", label: "法院案号", children: detail.data.court_case_no || "—" }, { key: "court", label: "受理法院", children: detail.data.court_name || "—" },
                        { key: "judge", label: "承办法官", children: detail.data.judge || "—" }, { key: "clerk", label: "书记员", children: detail.data.clerk || "—" },
                        { key: "plaintiff", label: "原告", children: detail.data.plaintiff || "—" }, { key: "defendant", label: "被告", children: detail.data.defendant || "—" },
                        { key: "third", label: "第三人", children: detail.data.third_parties || "—", span: 2 },
                      ]} />
                    </Card>
                    <Card size="small" title="诉讼法院信息" style={{ marginTop: 16 }} extra={<Space><Button size="small" onClick={() => void loadLawsuitManagement(detail.id)}>刷新</Button>{detail.status === "在办" ? <Button size="small" type="primary" onClick={() => { setEditingLawsuitCourt(null); lawsuitCourtForm.resetFields(); lawsuitCourtForm.setFieldsValue({ court_level: "一审" }); setLawsuitCourtOpen(true); }}>新增法院</Button> : null}</Space>}>
                      <Table<IprLawsuitCourt> rowKey="id" size="small" pagination={false} dataSource={lawsuitCourts} scroll={{ x: 780 }} columns={[
                        { title: "审级", dataIndex: "court_level", width: 80 }, { title: "法院", dataIndex: "court_name", width: 180 }, { title: "案号", dataIndex: "case_no", width: 160, render: value => value || "—" }, { title: "法官 / 书记员", width: 150, render: (_, row) => [row.judge, row.clerk].filter(Boolean).join(" / ") || "—" }, { title: "开庭日期", dataIndex: "hearing_date", width: 110, render: value => value || "—" },
                        { title: "操作", fixed: "right", width: 140, render: (_, row) => detail.status === "在办" ? <Space size={0}><Button type="link" onClick={() => { setEditingLawsuitCourt(row); lawsuitCourtForm.setFieldsValue({ ...row, filing_date: row.filing_date ? dayjs(row.filing_date) : undefined, hearing_date: row.hearing_date ? dayjs(row.hearing_date) : undefined }); setLawsuitCourtOpen(true); }}>编辑</Button><Button type="link" danger onClick={() => deleteLawsuitCourt(row)}>删除</Button></Space> : "—" },
                      ]} />
                    </Card>
                    <Card size="small" title="诉讼当事人" style={{ marginTop: 16 }} extra={detail.status === "在办" ? <Button size="small" type="primary" onClick={() => { setEditingLawsuitParty(null); lawsuitPartyForm.resetFields(); lawsuitPartyForm.setFieldsValue({ party_type: "原告" }); setLawsuitPartyOpen(true); }}>新增当事人</Button> : null}>
                      <Table<IprLawsuitParty> rowKey="id" size="small" pagination={false} dataSource={lawsuitParties} columns={[
                        { title: "身份", dataIndex: "party_type", width: 90 }, { title: "名称", dataIndex: "name", width: 190 }, { title: "联系人", dataIndex: "contact_name", width: 110, render: value => value || "—" }, { title: "联系电话", dataIndex: "contact_phone", width: 135, render: value => value || "—" }, { title: "地址", dataIndex: "address", ellipsis: true, render: value => value || "—" },
                        { title: "操作", width: 140, render: (_, row) => detail.status === "在办" ? <Space size={0}><Button type="link" onClick={() => { setEditingLawsuitParty(row); lawsuitPartyForm.setFieldsValue(row); setLawsuitPartyOpen(true); }}>编辑</Button><Button type="link" danger onClick={() => deleteLawsuitParty(row)}>删除</Button></Space> : "—" },
                      ]} />
                    </Card>
                    <Card size="small" title="诉讼费用管理" style={{ marginTop: 16 }} extra={detail.status === "在办" ? <Button size="small" type="primary" onClick={() => { lawsuitFeeForm.resetFields(); lawsuitFeeForm.setFieldsValue({ fee_date: dayjs() }); setLawsuitFeeOpen(true); }}>登记诉讼费用</Button> : null}>
                      <Table<IprLawsuitFee> rowKey="id" size="small" pagination={false} dataSource={lawsuitFees} columns={[
                        { title: "费用类型", width: 160, render: (_, row) => row.title || row.fee_type || "—" }, { title: "金额", dataIndex: "amount", width: 120, render: value => value == null ? "—" : Number(value).toFixed(2) }, { title: "费用日期", dataIndex: "fee_date", width: 120, render: value => value || "—" }, { title: "状态", dataIndex: "status", width: 100, render: value => value || "—" }, { title: "备注", dataIndex: "remark", ellipsis: true, render: value => value || "—" },
                      ]} />
                    </Card>
                  </>,
                }] : []),
                {
                  key: "files",
                  label: "文档信息",
                  children: (
                    <>
            <Card
              size="small"
              title="案件文书与附件"
              style={{ marginTop: 16 }}
              extra={<Button size="small" onClick={refreshIprFiles}>刷新</Button>}
            >
              {iprSectionErrors.files ? <Alert type="error" showIcon message={iprSectionErrors.files} style={{ marginBottom: 12 }} /> : null}
              <Space wrap>
                {detail.status !== "草稿" &&
                  detail.status !== "待立案审核" &&
                  detail.status !== "已驳回" && (
                    <>
                      <Button
                        onClick={() => void generateDocument("case-summary")}
                      >
                        生成案件信息表（DOCX）
                      </Button>
                      <Button
                        onClick={() =>
                          void generateDocument("authorization-letter")
                        }
                      >
                        生成授权委托书（DOCX）
                      </Button>
                      <Button
                        onClick={() => void generateDocument("law-firm-letter")}
                      >
                        生成律所函（DOCX）
                      </Button>
                      <Button
                        onClick={() =>
                          void generateDocument("identity-certificate")
                        }
                      >
                        生成主体核对单（DOCX）
                      </Button>
                    </>
                  )}
              </Space>
              <div style={{ marginTop: 12 }}>
                {attachments.length
                  ? attachments.map((item) => (
                      <Space key={item.id} size={0}>
                        <Button type="link" onClick={() => void previewAttachment(item)}>
                          {item.original_name}
                        </Button>
                        <Button type="link" onClick={() => void downloadAttachment(item)}>
                          下载
                        </Button>
                      </Space>
                    ))
                  : "暂无案件附件"}
              </div>
          </Card>
          <Card
            size="small"
            title="案件文档目录"
            style={{ marginTop: 16 }}
            extra={
              detail.status === "在办" ? <Space><Button disabled={!selectedIprFileIds.length} onClick={() => void markSelectedIprFilesTransmitted()}>批量标记已转</Button><Button size="small" type="primary" onClick={() => { iprFileForm.resetFields(); iprFileForm.setFieldsValue({ document_date: dayjs() }); setIprUploadFile(null); void loadIprFileTypes(String(detail.data?.case_kind || "")); setIprFileOpen(true); }}>上传文档</Button></Space> : null
            }
          >
            {iprSectionErrors.files ? <Alert type="error" showIcon message={iprSectionErrors.files} style={{ marginBottom: 12 }} /> : null}
            <Table
              rowKey="id"
              size="small"
              pagination={filesPagination}
              dataSource={attachments}
              rowSelection={{ selectedRowKeys: selectedIprFileIds, onChange: (keys) => setSelectedIprFileIds(keys.map(Number)), getCheckboxProps: (row: Attachment) => ({ disabled: !row.requires_transmission || !!row.is_transmitted }) }}
              scroll={{ x: 760 }}
              columns={[
                { title: "文档类型", dataIndex: "category", width: 140, ellipsis: true },
                {
                  title: "文件名称",
                  dataIndex: "original_name",
                  width: 220,
                  ellipsis: true,
                  render: (_, row: Attachment) => (
                    <Space size={0}>
                      <Button type="link" onClick={() => void previewAttachment(row)}>{row.original_name}</Button>
                      <Button type="link" onClick={() => void downloadAttachment(row)}>下载</Button>
                    </Space>
                  ),
                },
                { title: "上传人", dataIndex: "uploader_display_name", width: 95, render: personDisplayName },
                { title: "文档日期", dataIndex: "document_date", width: 110, render: (value) => value || "—" },
                {
                  title: "待转文",
                  width: 100,
                  render: (_, row: Attachment) => row.requires_transmission ? (row.is_transmitted ? <Tag color="green">已转</Tag> : <Tag color="gold">是</Tag>) : "否",
                },
                {
                  title: "操作",
                  fixed: "right",
                  width: 150,
                  render: (_, row: Attachment) => <Space size={0}>{detail.status === "在办" && row.requires_transmission && !row.is_transmitted && <Button type="link" onClick={() => void markIprFileTransmitted(row)}>标记已转</Button>}{detail.status === "在办" && <Button type="link" danger onClick={() => confirmIprDeletion("file", row.original_name, () => deleteIprFile(row))}>删除</Button>}</Space>,
                },
              ]}
            />
          </Card>
                    </>
                  ),
                },
                {
                  key: "assistedFees",
                  label: "协助费",
                  children: (
          <Card
            size="small"
              title="协助费"
              style={{ marginTop: 16 }}
              extra={
                <Space size={0}>
                  <Button size="small" onClick={refreshAssistedFees}>刷新</Button>
                  {detail.status === "在办" && canManageAssistedFees ? (
                    <Button
                      type="primary"
                      size="small"
                      onClick={() => {
                        assistedForm.resetFields();
                        setAssistedOpen(true);
                      }}
                    >
                      新增协助费
                    </Button>
                  ) : null}
                </Space>
              }
            >
              {iprSectionErrors.assistedFees ? <Alert type="error" showIcon message={iprSectionErrors.assistedFees} style={{ marginBottom: 12 }} /> : null}
              <Table
                rowKey="id"
                size="small"
                pagination={assistedFeesPagination}
                dataSource={assistedFees}
                scroll={{ x: 980 }}
                columns={[
                  { title: "协助类别", dataIndex: "assisted_type", width: 150 },
                  {
                    title: "提交",
                    width: 145,
                    render: (_, row: AssistedFee) =>
                    `${row.request_date || "—"} / ${personDisplayName(row.request_user_display_name)}`,
                  },
                  {
                    title: "办理",
                    width: 145,
                    render: (_, row: AssistedFee) =>
                      row.response_date
                      ? `${row.response_date} / ${personDisplayName(row.response_user_display_name)}`
                        : "—",
                  },
                  {
                    title: "回执文件",
                    width: 180,
                    render: (_, row: AssistedFee) =>
                      row.receipt ? (
                        <Space size={0}>
                          <Button
                            type="link"
                            onClick={() => void previewAttachment(row.receipt!)}
                          >
                            {row.receipt.original_name}
                          </Button>
                          <Button
                            type="link"
                            onClick={() => void downloadAttachment(row.receipt!)}
                          >
                            下载
                          </Button>
                        </Space>
                      ) : (
                        "—"
                      ),
                  },
                  {
                    title: "状态",
                    dataIndex: "status",
                    width: 90,
                    render: (value) => (
                      <Tag color={value === "已办理" ? "green" : "gold"}>
                        {value}
                      </Tag>
                    ),
                  },
                  {
                    title: "操作",
                    fixed: "right",
                    width: 190,
                    render: (_, row: AssistedFee) => (
                      <Space size={0}>
                        {row.status === "待确认" &&
                          detail.status === "在办" && canManageAssistedFees && (
                            <Button
                              type="link"
                              onClick={() => {
                                assistedEditForm.setFieldsValue({
                                  assisted_type: row.assisted_type,
                                  remark: row.remark,
                                });
                                setEditingAssistedFee(row);
                              }}
                            >
                              编辑
                            </Button>
                          )}
                        {row.status === "待确认" &&
                          detail.status === "在办" && canManageAssistedFees && (
                            <Button
                              type="link"
                              onClick={() => void confirmAssistedFee(row)}
                            >
                              确认
                            </Button>
                          )}
                        {row.status === "待办理" &&
                          detail.status === "在办" && canManageAssistedFees && (
                            <Button
                              type="link"
                              onClick={() => {
                                transactForm.resetFields();
                                transactForm.setFieldsValue({
                                  response_date: dayjs(),
                                });
                                setReceiptFile(null);
                                setTransactTarget(row);
                              }}
                            >
                              办理
                            </Button>
                          )}
                        {(row.status === "待确认" || row.status === "待办理") &&
                          detail.status === "在办" && canManageAssistedFees && (
                          <Button
                            type="link"
                            danger
                            onClick={() => confirmIprDeletion("assisted-fee", row.assisted_type, () => deleteAssistedFee(row))}
                          >
                            删除
                          </Button>
                        )}
                      </Space>
                    ),
                  },
                ]}
              />
            </Card>
                  ),
                },
              ]}
            />
            <Card
              size="small"
              title="案件事件"
              style={{ marginTop: 16 }}
              extra={
                <Space>
                  <Button size="small" onClick={() => detail && void loadIprCaseEvents(detail.id)}>
                    刷新
                  </Button>
                  {detail.status === "在办" && (
                    <Button size="small" type="primary" onClick={() => openIprCaseEvent()}>
                      新增事件
                    </Button>
                  )}
                  {detail.status === "在办" && (
                    <Button size="small" onClick={() => setSuppressionOpen(true)}>
                      设定不监控
                    </Button>
                  )}
                </Space>
              }
            >
              {iprSectionErrors.reminders ? <Alert type="error" showIcon message={iprSectionErrors.reminders} style={{ marginBottom: 12 }} /> : null}
              <Table
                rowKey="id"
                size="small"
                pagination={remindersPagination}
                dataSource={iprCaseEvents}
                scroll={{ x: 790 }}
                columns={[
                  { title: "事件类型", dataIndex: "event_type", width: 140 },
                  { title: "事件日期", dataIndex: "event_date", width: 110 },
                  { title: "截止日期", dataIndex: "deadline", width: 110 },
                  {
                    title: "事件内容",
                    dataIndex: "content",
                    ellipsis: true,
                    render: (content: string, row: IprCaseEvent) => (
                      <Button type="link" onClick={() => setIprEventDetail(row)}>{content}</Button>
                    ),
                  },
                  { title: "创建人", dataIndex: "creator_display_name", width: 100, render: personDisplayName },
                  {
                    title: "操作",
                    width: 130,
                    render: (_, row: IprCaseEvent) =>
                      detail.status === "在办" && canManageIprCaseEvent(row) ? (
                        <Space size={0}>
                          <Button type="link" onClick={() => openIprCaseEvent(row)}>编辑</Button>
                          <Button type="link" danger onClick={() => confirmIprDeletion("event", row.content, () => deleteIprCaseEvent(row))}>删除</Button>
                        </Space>
                      ) : "—",
                  },
                ]}
              />
              <div style={{ marginTop: 8, color: "#777" }}>
                不监控类型：{reminderEventTypes.filter((item) => suppressedIds.includes(item.id)).map((item) => item.name).join("、") || "未设置"}
              </div>
            </Card>
            <Card
              size="small"
              title="关联任务"
              style={{ marginTop: 16 }}
              extra={
                <Space>
                  <Button size="small" onClick={() => detail && void loadIprCaseTasks(detail.id)}>刷新</Button>
                  {detail.status === "在办" && <Button size="small" type="primary" onClick={() => openIprCaseTask(detail)}>新建案件任务</Button>}
                </Space>
              }
            >
              {iprSectionErrors.tasks ? <Alert type="error" showIcon message={iprSectionErrors.tasks} style={{ marginBottom: 12 }} /> : null}
              <Table
                rowKey="id"
                size="small"
                pagination={iprTasksPagination}
                dataSource={iprCaseTasks}
                scroll={{ x: 760 }}
                columns={[
                  { title: "任务编号", dataIndex: "serial_no", width: 170, ellipsis: true },
                  { title: "标题", dataIndex: "title", ellipsis: true },
                  { title: "负责人", dataIndex: "owner_display_name", width: 110, render: personDisplayName },
                  { title: "截止日期", dataIndex: "deadline", width: 110, render: (value) => value || "—" },
                  { title: "状态", dataIndex: "status", width: 105, render: (value) => <Tag>{value}</Tag> },
                ]}
              />
            </Card>
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
                <Button type="primary" onClick={() => action(detail, "submit")}>
                  提交立案审核
                </Button>
              )}
              {detail.status === "在办" && (
                <Button onClick={() => openMaintenance(detail)}>
                  维护期限/年费/费率
                </Button>
              )}
              {detail.status === "在办" && (
                <Button danger onClick={() => action(detail, "close")}>
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
      <Modal
        open={iprFileOpen}
        title="上传知识产权案件文档"
        onCancel={() => {
          setIprFileOpen(false);
          setIprUploadFile(null);
        }}
        onOk={() => void uploadIprFile()}
        okText="上传"
      >
        <Form form={iprFileForm} layout="vertical">
          <Form.Item
            name="category"
            label="文档类型"
            rules={[{ required: true, message: "请选择文档类型" }]}
          >
            <Select
              placeholder="请选择管理员配置且适用于本案件的文档类型"
              options={iprFileTypes.map((item) => ({
                value: item.name,
                label: `${item.name}${item.requires_transmission ? "（待转文）" : ""}`,
              }))}
            />
          </Form.Item>
          <Form.Item
            name="document_date"
            label="文档日期"
            rules={[{ required: true }]}
          >
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <div style={{ marginBottom: 16, color: "#666" }}>
            待转文属性由管理员配置的文件类型决定，上传人不能自行绕过。
          </div>
          <Form.Item label="案件文档" required>
            <input
              type="file"
              accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.png,.jpg,.jpeg,.zip,.rar"
              onChange={(event) =>
                setIprUploadFile(event.target.files?.[0] || null)
              }
            />
            {iprUploadFile && <div>{iprUploadFile.name}</div>}
          </Form.Item>
          <Form.Item name="remark" label="说明">
            <Input.TextArea rows={2} maxLength={1000} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={!!maintenanceTarget}
        title={
          maintenanceTarget
            ? `维护知识产权案件：${maintenanceTarget.serial_no}`
            : "维护知识产权案件"
        }
        onCancel={() => setMaintenanceTarget(null)}
        onOk={() => void saveMaintenance()}
        okText="保存维护"
      >
        <Form form={maintenanceForm} layout="vertical">
          <Form.Item name="deadline" label="办理期限">
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="annual_fee_year" label="年费年度">
            <InputNumber min={1} max={100} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="rate" label="费率">
            <InputNumber
              min={0}
              max={1}
              step={0.01}
              style={{ width: "100%" }}
            />
          </Form.Item>
          <Form.Item name="comment" label="维护说明">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={iprEventOpen}
        title={editingIprEvent ? "编辑知识产权案件事件" : "新增知识产权案件事件"}
        onCancel={() => { setIprEventOpen(false); setEditingIprEvent(null); }}
        onOk={() => void saveIprCaseEvent()}
        okText={editingIprEvent ? "保存修改" : "创建事件"}
      >
        <Form form={iprEventForm} layout="vertical">
          <Form.Item
            name="event_type_id"
            label="事件类型"
            rules={[{ required: true }]}
          >
            <Select
              placeholder="选择事件类型"
              options={reminderEventTypes.map((item) => ({ value: item.id, label: item.name }))}
            />
          </Form.Item>
          <Form.Item
            name="event_date"
            label="事件日期"
            rules={[{ required: true }]}
          >
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item
            name="deadline"
            label="截止日期"
            rules={[{ required: true }]}
          >
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item
            name="content"
            label="事件内容"
            rules={[{ required: true, message: "请输入事件内容" }]}
          >
            <Input.TextArea rows={3} maxLength={1000} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={!!iprEventDetail}
        title="案件事件详情"
        footer={null}
        onCancel={() => setIprEventDetail(null)}
      >
        {iprEventDetail && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="事件类型">{iprEventDetail.event_type}</Descriptions.Item>
            <Descriptions.Item label="事件日期">{iprEventDetail.event_date}</Descriptions.Item>
            <Descriptions.Item label="截止日期">{iprEventDetail.deadline}</Descriptions.Item>
            <Descriptions.Item label="创建人">{personDisplayName(iprEventDetail.creator_display_name)}</Descriptions.Item>
            <Descriptions.Item label="事件内容">{iprEventDetail.content}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
      <Modal
        open={iprTaskOpen}
        title={detail ? `新建案件任务：${detail.serial_no}` : "新建案件任务"}
        onCancel={() => setIprTaskOpen(false)}
        onOk={() => void createIprCaseTask()}
        okText="创建任务"
      >
        <Form form={iprTaskForm} layout="vertical">
          <Form.Item name="title" label="任务标题" rules={[{ required: true, message: "请输入任务标题" }]}>
            <Input maxLength={255} />
          </Form.Item>
          <Form.Item name="owner" label="负责人" rules={[{ required: true, message: "请选择负责人" }]}>
            <Select
              showSearch
              optionFilterProp="label"
              placeholder="请选择系统员工"
              options={peopleOptions.map((item) => ({ value: item.username, label: item.label }))}
            />
          </Form.Item>
          <Form.Item name="deadline" label="截止日期" rules={[{ required: true }]}>
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="priority" label="优先级">
            <Select options={["普通", "重要", "紧急"].map((value) => ({ value, label: value }))} />
          </Form.Item>
          <Form.Item name="description" label="任务说明">
            <Input.TextArea rows={3} maxLength={2000} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={suppressionOpen}
        title="案件提醒不监控"
        onCancel={() => setSuppressionOpen(false)}
        onOk={() => void saveSuppressions()}
        okText="保存设置"
      >
        <p style={{ color: "#777" }}>
          已勾选的类型不会参与后续自动提醒生成；手工新增提醒不受此设置影响。
        </p>
        <Checkbox.Group
          value={suppressedIds}
          onChange={(values) => setSuppressedIds(values.map(Number))}
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2,minmax(0,1fr))",
            gap: 8,
          }}
          options={reminderEventTypes.map((item) => ({
            label: item.name,
            value: item.id,
          }))}
        />
      </Modal>
      <Modal
        open={iprLogOpen}
        title="新增案件业务日志"
        onCancel={() => setIprLogOpen(false)}
        onOk={() => void createIprLog()}
        okText="保存日志"
      >
        <Form form={iprLogForm} layout="vertical">
          <Form.Item name="content" label="业务日志内容" rules={[{ required: true, message: "请填写业务日志内容" }]}>
            <Input.TextArea rows={5} maxLength={4000} showCount />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={!!iprBusinessLogDetail}
        title="案件业务日志详情"
        footer={null}
        onCancel={() => setIprBusinessLogDetail(null)}
      >
        {iprBusinessLogDetail && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="日志内容">{iprBusinessLogDetail.content}</Descriptions.Item>
            <Descriptions.Item label="创建人">{personDisplayName(iprBusinessLogDetail.created_by_display_name)}</Descriptions.Item>
            <Descriptions.Item label="创建时间">{iprBusinessLogDetail.created_at}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
      <Modal
        open={!!iprOperationLogDetail}
        title="案件操作日志详情"
        footer={null}
        onCancel={() => setIprOperationLogDetail(null)}
      >
        {iprOperationLogDetail && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="操作">{iprOperationLogDetail.action}</Descriptions.Item>
            <Descriptions.Item label="说明">{iprOperationLogDetail.comment || "—"}</Descriptions.Item>
            <Descriptions.Item label="操作人">{personDisplayName(iprOperationLogDetail.operator_display_name)}</Descriptions.Item>
            <Descriptions.Item label="原状态">{iprOperationLogDetail.from_status || "—"}</Descriptions.Item>
            <Descriptions.Item label="目标状态">{iprOperationLogDetail.to_status || "—"}</Descriptions.Item>
            <Descriptions.Item label="时间">{iprOperationLogDetail.created_at}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
      <Modal
        open={!!iprHistoryDetail}
        title="案件事项详情"
        footer={null}
        onCancel={() => setIprHistoryDetail(null)}
      >
        {iprHistoryDetail && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="事项">{iprHistoryDetail.action}</Descriptions.Item>
            <Descriptions.Item label="状态变化">
              {iprHistoryDetail.from_status || iprHistoryDetail.to_status
                ? `${iprHistoryDetail.from_status || "—"} → ${iprHistoryDetail.to_status || "—"}`
                : "—"}
            </Descriptions.Item>
            <Descriptions.Item label="说明">{iprHistoryDetail.comment || "—"}</Descriptions.Item>
            <Descriptions.Item label="操作人">{personDisplayName(iprHistoryDetail.operator_display_name)}</Descriptions.Item>
            <Descriptions.Item label="时间">{iprHistoryDetail.created_at}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
      <Modal
        open={customerOpen}
        title="维护案件客户"
        onCancel={() => setCustomerOpen(false)}
        onOk={() => void saveCaseCustomers()}
        okText="保存关联"
        width={760}
      >
        <p style={{ color: "#666" }}>案件可以关联多个客户；必须在已选客户中指定一个主客户，主客户会同步用于案件概览及后续关联流程。</p>
        <Table
          rowKey="id"
          size="small"
          pagination={false}
          dataSource={customerCandidates}
          rowSelection={{
            selectedRowKeys: customerSelection,
            onChange: (keys) => {
              const selected = keys.map(Number);
              setCustomerSelection(selected);
              if (!selected.includes(Number(primaryCustomerId))) setPrimaryCustomerId(selected[0] || null);
            },
          }}
          columns={[
            { title: "客户编号", dataIndex: "customer_no", width: 150 },
            { title: "客户名称", dataIndex: "name" },
            { title: "状态", dataIndex: "status", width: 110 },
            { title: "主客户", width: 110, render: (_, row) => <Checkbox checked={primaryCustomerId === row.id} disabled={!customerSelection.includes(row.id)} onChange={() => setPrimaryCustomerId(row.id)}>主客户</Checkbox> },
          ]}
        />
      </Modal>
      <Modal
        open={contactOpen}
        title={contactCustomer ? `维护案件联系人：${contactCustomer.name}` : "维护案件联系人"}
        onCancel={() => setContactOpen(false)}
        onOk={() => void saveCaseContacts()}
        okText="保存联系人"
        width={860}
      >
        <p style={{ color: "#666" }}>同一客户联系人可以同时承担文书联系人和技术联系人两种角色；已失效联系人不可再选择。</p>
        <Table
          rowKey="id"
          size="small"
          pagination={false}
          dataSource={contactCandidates}
          columns={[
            { title: "姓名", dataIndex: "name", width: 130 },
            { title: "职务", dataIndex: "position", width: 140, render: (value) => value || "—" },
            { title: "电话", dataIndex: "phone", width: 160, render: (value) => value || "—" },
            { title: "邮箱", dataIndex: "email", ellipsis: true, render: (value) => value || "—" },
            { title: "文书联系人", width: 120, render: (_, row) => <Checkbox checked={documentContactIds.includes(row.id)} onChange={(event) => setDocumentContactIds((ids) => event.target.checked ? [...new Set([...ids, row.id])] : ids.filter((id) => id !== row.id))} /> },
            { title: "技术联系人", width: 120, render: (_, row) => <Checkbox checked={technologyContactIds.includes(row.id)} onChange={(event) => setTechnologyContactIds((ids) => event.target.checked ? [...new Set([...ids, row.id])] : ids.filter((id) => id !== row.id))} /> },
          ]}
        />
      </Modal>
      <Modal
        open={lawFirmOpen}
        title="选择协作律所"
        onCancel={() => setLawFirmOpen(false)}
        onOk={() => void saveCaseLawFirms()}
        okText="保存关联"
        width={760}
      >
        <p style={{ color: "#666" }}>仅显示启用的律所；保存时会以当前勾选结果替换本案件的协作律所。</p>
        <Table
          rowKey="id"
          size="small"
          pagination={false}
          dataSource={lawFirmCandidates}
          rowSelection={{ selectedRowKeys: lawFirmSelection, onChange: (keys) => setLawFirmSelection(keys.map(Number)) }}
          columns={[
            { title: "编号", dataIndex: "code", width: 130 },
            { title: "律所名称", dataIndex: "name", width: 230 },
            { title: "电话", dataIndex: "phone", width: 150, render: (value) => value || "—" },
            { title: "邮箱", dataIndex: "email", ellipsis: true, render: (value) => value || "—" },
          ]}
        />
      </Modal>
      <Modal
        open={assistedOpen}
        title="新增知识产权协助费"
        onCancel={() => setAssistedOpen(false)}
        onOk={() => void createAssistedFee()}
        okText="提交"
      />
      <Modal open={courtInfoOpen} title="维护诉讼基本信息" onCancel={() => setCourtInfoOpen(false)} onOk={() => void saveCourtInfo()} okText="保存">
        <Form form={courtInfoForm} layout="vertical"><div className="form-grid">
          <Form.Item name="court_case_no" label="法院案号"><Input /></Form.Item><Form.Item name="court_name" label="受理法院"><Input /></Form.Item>
          <Form.Item name="judge" label="承办法官"><Input /></Form.Item><Form.Item name="clerk" label="书记员"><Input /></Form.Item>
          <Form.Item name="plaintiff" label="原告"><Input /></Form.Item><Form.Item name="defendant" label="被告"><Input /></Form.Item>
        </div><Form.Item name="third_parties" label="第三人"><Input /></Form.Item></Form>
      </Modal>
      <Modal open={lawsuitCourtOpen} title={editingLawsuitCourt ? "编辑诉讼法院" : "新增诉讼法院"} onCancel={() => { setLawsuitCourtOpen(false); setEditingLawsuitCourt(null); }} onOk={() => void saveLawsuitCourt()} okText="保存">
        <Form form={lawsuitCourtForm} layout="vertical"><div className="form-grid">
          <Form.Item name="court_level" label="审级" rules={[{ required: true }]}><Select options={["一审", "二审", "执行", "再审"].map(value => ({ value, label: value }))} /></Form.Item><Form.Item name="court_name" label="法院名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="case_no" label="本审案号"><Input /></Form.Item><Form.Item name="courtroom" label="法庭"><Input /></Form.Item>
          <Form.Item name="judge" label="承办法官"><Input /></Form.Item><Form.Item name="clerk" label="书记员"><Input /></Form.Item>
          <Form.Item name="filing_date" label="立案日期"><DatePicker style={{ width: "100%" }} /></Form.Item><Form.Item name="hearing_date" label="开庭日期"><DatePicker style={{ width: "100%" }} /></Form.Item>
        </div><Form.Item name="remark" label="备注"><Input.TextArea rows={2} /></Form.Item></Form>
      </Modal>
      <Modal open={lawsuitPartyOpen} title={editingLawsuitParty ? "编辑诉讼当事人" : "新增诉讼当事人"} onCancel={() => { setLawsuitPartyOpen(false); setEditingLawsuitParty(null); }} onOk={() => void saveLawsuitParty()} okText="保存">
        <Form form={lawsuitPartyForm} layout="vertical"><div className="form-grid">
          <Form.Item name="party_type" label="当事人身份" rules={[{ required: true }]}><Select options={["原告", "被告", "第三人"].map(value => ({ value, label: value }))} /></Form.Item><Form.Item name="name" label="名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="contact_name" label="联系人"><Input /></Form.Item><Form.Item name="contact_phone" label="联系电话"><Input /></Form.Item>
        </div><Form.Item name="address" label="地址"><Input /></Form.Item><Form.Item name="remark" label="备注"><Input.TextArea rows={2} /></Form.Item></Form>
      </Modal>
      <Modal open={lawsuitFeeOpen} title="登记诉讼费用" onCancel={() => setLawsuitFeeOpen(false)} onOk={() => void createLawsuitFee()} okText="登记">
        <Form form={lawsuitFeeForm} layout="vertical"><div className="form-grid">
          <Form.Item name="lawsuit_fee_kind" label="费用类型" rules={[{ required: true }]}><Select options={IPR_LAWSUIT_FEE_OPTIONS.map(({ value, label }) => ({ value, label }))} /></Form.Item><Form.Item name="amount" label="金额" rules={[{ required: true }]}><InputNumber min={0.01} precision={2} style={{ width: "100%" }} /></Form.Item>
          <Form.Item name="fee_date" label="费用日期" rules={[{ required: true }]}><DatePicker style={{ width: "100%" }} /></Form.Item><Form.Item name="remark" label="备注"><Input /></Form.Item>
        </div></Form>
      </Modal>
      <Modal open={assistedOpen} title="新建知识产权资助费用" onCancel={() => setAssistedOpen(false)} onOk={() => void createAssistedFee()} okText="提交">
        <Form form={assistedForm} layout="vertical">
          <Form.Item
            name="assisted_type"
            label="协助类别"
            rules={[{ required: true, message: "请选择或填写协助类别" }]}
          >
            <Select
              showSearch
              allowClear
              options={["专利资助", "商标资助", "高新技术资助", "其他资助"].map(
                (value) => ({ value, label: value }),
              )}
            />
          </Form.Item>
          <Form.Item name="remark" label="说明">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={!!editingAssistedFee}
        title={editingAssistedFee ? `编辑协助费：${editingAssistedFee.assisted_type}` : "编辑协助费"}
        onCancel={() => {
          setEditingAssistedFee(null);
          assistedEditForm.resetFields();
        }}
        onOk={() => void updateAssistedFee()}
        okText="保存"
      >
        <Form form={assistedEditForm} layout="vertical">
          <Form.Item
            name="assisted_type"
            label="协助类别"
            rules={[{ required: true, message: "请选择或填写协助类别" }]}
          >
            <Select
              showSearch
              allowClear
              options={["专利资助", "商标资助", "高新技术资助", "其他资助"].map(
                (value) => ({ value, label: value }),
              )}
            />
          </Form.Item>
          <Form.Item name="remark" label="说明">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={!!transactTarget}
        title={
          transactTarget
            ? `办理协助费：${transactTarget.assisted_type}`
            : "办理协助费"
        }
        onCancel={() => {
          setTransactTarget(null);
          setReceiptFile(null);
        }}
        onOk={() => void transactAssistedFee()}
        okText="保存办理"
      >
        <Form form={transactForm} layout="vertical">
          <Form.Item
            name="response_date"
            label="办理日期"
            rules={[{ required: true }]}
          >
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="回执文件" required>
            <input
              type="file"
              accept=".pdf,.doc,.docx,.xls,.xlsx,.zip,.jpg,.jpeg,.png"
              onChange={(event) =>
                setReceiptFile(event.target.files?.[0] || null)
              }
            />
            {receiptFile && <div>{receiptFile.name}</div>}
          </Form.Item>
          <Form.Item name="remark" label="办理说明">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
