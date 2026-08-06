import { useEffect, useMemo, useRef, useState } from "react";
import type { Key } from "react";
import {
  Alert,
  Button,
  Card,
  Checkbox,
  DatePicker,
  Descriptions,
  Divider,
  Empty,
  Form,
  Input,
  InputNumber,
  message,
  Modal,
  Select,
  Space,
  Steps,
  Table,
  Tabs,
  Tag,
  Timeline,
  Popconfirm,
  Pagination,
  Radio,
} from "antd";
import { CheckOutlined, CloseOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { api } from "./api";
import { rememberCaseDetailTarget } from "./caseDetailNavigation";
import { resolveDetailRelation } from "./detailRelationResolver";
import { buildContractDetailRoute, consumeContractDetailTarget, sortContractObjectLogs, type ContractDetailNavigationContext } from "./contractDetailNavigation";
import { rememberCustomerDetailTarget, resolveCustomerDetailTarget } from "./customerDetailNavigation";
import { consumeCustomerRelationTarget } from "./customerRelationNavigation";
import { buildContractCustomerQueryFromRelation, openContractCustomerCreation } from "./contractCenterCustomerNavigation";
import {
  CONTRACT_CUSTOMER_ROUTE_SOURCE_KEY,
  clearContractCustomerContext,
  createContractCustomerContextConsumer,
  createContractNumber,
  type LinkedCustomerContext,
} from "./contractCreateContext";
import { filterPendingContractApprovals } from "./contractAuditScope";
import { readContractListQuery, saveContractListQuery } from "./contractListQuery";
import { readContractListPagination, saveContractListPagination } from "./contractListPagination.mjs";
import { buildContractPaymentNavigation } from "./contractPaymentNavigation";
import { selectContractCurrentApprovalStep } from "./contractApprovalCurrentStep.mjs";
import { normalizeContractPaymentApplications } from "./contractPaymentApplicationPresentation.mjs";
import { buildChinesePersonOptions, displayChinesePersonName, displayChinesePersonNames } from "./contractPeoplePresentation.mjs";
import { createContractMutationGate } from "./contractMutationGate.mjs";
import { buildContractAttachmentDeletePlan } from "./contractAttachmentBatch.mjs";
import {
  CONTRACT_OBJECT_DEFAULT_PAGE_SIZE,
  CONTRACT_OBJECT_PAGE_SIZES,
  paginateContractObjectRows,
  sortContractObjectRows,
  sortContractRecordRows,
} from "./contractObjectListPolicy.mjs";
import {
  contractObjectActionPolicy,
  filterContractIncomingPayments,
  normalizeIncomingPaymentForContract,
  normalizeInvoiceObject,
  normalizePaidObject,
  contractObjectHasLogs,
} from "./contractObjectPresentation.mjs";
import {
  CONTRACT_ATTACHMENT_ACCEPT,
  CONTRACT_EVENT_PAGE_SIZES,
  buildContractApprovalPayload,
  createContractEventRequestTracker,
  createContractEventSubmitGate,
  buildContractDraftDefaults,
  buildContractListRequestParams,
  canActOnContractApproval,
  canAccessContractView,
  canMutateContractAttachments,
  contractAttachmentActionPolicy,
  contractAuditActionPolicy,
  contractAuditViewConfig,
  contractListActionPolicy,
  contractListViewConfig,
  contractSecondaryActionPolicy,
  extractContractErrorMessage,
  filterContractCaseOptions,
  filterContractLinkedRows,
  normalizeContractActionResponse,
  normalizeContractApprovalHistory,
  normalizeContractAttachment,
  buildContractEventsRequest,
  normalizeContractEventsResponse,
  normalizeContractQuery,
  normalizeContractDetailReturnView,
  resolveContractCustomerSelection,
  validateContractApprovalSubmission,
  validateContractAttachment,
  validateContractDraftValues,
} from "./contractWorkflowPolicy.mjs";
import { formatRequiredDate } from "./formSafety";
import RecordImportButton from "./RecordImportButton";
import "./contract-center.css";
type Contract = {
  id: number;
  contract_guid?: string;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
  owner: string;
  department: string;
  description: string;
  data: {
    amount: number;
    signed_at: string;
    type: string;
    fee_type?: string;
    case_no?: string;
    contract_no?: string;
    source_person?: string;
    contract_body?: string;
    official_paid?: number;
    official_received?: number;
    official_unreceived?: number;
    official_loss?: number;
    agency_total?: number;
    agency_received?: number;
    agency_due?: number;
    other_total?: number;
    other_paid?: number;
    other_due?: number;
    invoice_opened?: number;
    invoice_should?: number;
    invoice_excess?: number;
    external_contract_no?: string;
    external_contract_numbers?: string[];
    pending_change?: { status?: string; reason?: string; changes?: Change["changes"] };
    end_date?: string;
    approval_count?: number;
    customer_manager?: string;
    customer_id?: number;
    customer_no?: string;
    submitted_at?: string;
    submitted_by?: string;
    submit_comment?: string;
    seal_application_id?: number;
    seal_application_no?: string;
    current_approver?: string;
    sync_seal?: boolean;
    /** 合同审批通过时，是否仍需在用印中心补传真实用印文件。 */
    sync_seal_file_required?: boolean;
    contract_guid?: string;
    contractGuid?: string;
  };
};
type Step = {
  id: number;
  step_order: number;
  approver: string;
  approver_display_name?: string;
  status: string;
  comment: string;
  acted_at: string | null;
};
type Change = {
  id: number;
  change_type: string;
  reason: string;
  operator: string;
  created_at: string;
  changes: { field: string; label: string; before: any; after: any }[];
};
type Profile = { username: string; display_name: string; department: string; role: string };
type DirectoryUser = { username: string; display_name: string; department: string; is_active: boolean; role?: string; position?: string; staff_role?: string; job_permissions?: string[]; can_approve_contract?: boolean };
type ApproverSetting = { username: string; display_name: string; display_name_valid?: boolean; department: string; position: string; selected: boolean };
type Attachment = { id: number; original_name: string; category: string; size: number; created_at: string; uploader?: string; uploader_display_name?: string };
type AttachmentPreview = { name: string; kind: "image" | "pdf" | "text" | "docx"; url?: string; text?: string };
type HistoryEvent = { id: number; action: string; from_status: string; to_status: string; operator: string; comment: string; created_at: string };
type ContractEvent = { id: number; contract_record_id: number; content: string; operator: string; created_at: string; contract_guid?: string };
type SealAsset = { id: number; code: string; name: string; seal_type: string; status: string };
type CustomerRef = { id: number; serial_no: string; title: string; owner: string; data: { customer_managers?: string[] } };
type ContractPaymentCandidate = { contract_object_id:number; case_record_id:number; case_no:string; case_title:string; fee_type:string; contract_amount:number; reserved_amount:number; remaining_amount:number; remark:string };
type PaymentTypeOption = { value:string; label:string; payee:string; account:string };
const colors: Record<string, string> = {
  草稿: "default",
  审批中: "orange",
  已通过: "green",
  履行中: "blue",
  已完成: "green",
  已拒绝: "red",
};
const CONTRACT_TYPE_OPTIONS = ["法律顾问合同", "争议解决合同", "框架合作合同", "非诉项目合同", "其他"].map((value) => ({ value, label: value }));
const CONTRACT_FEE_MODE_OPTIONS = ["固定收费", "固定+后期", "免费代理", "法律援助", "计时收费", "全风险代理"].map((value) => ({ value, label: value }));
const CONTRACT_CREATE_STEP_TITLES = ["合同基本信息", "提交审批", "合同审批", "合同用印"];
const CONTRACT_SEAL_READY_STATUSES = ["审批中", "已通过", "履行中", "已完成"];
const WIZARD_STORAGE_KEY = "sunhold-contract-wizard-id";
const CONTRACT_DETAIL_RETURN_VIEW_STORAGE_KEY = "sunhold:contract-detail-return-view";
const CONTRACT_DETAIL_TAB_STORAGE_KEY = "sunhold:contract-detail-active-tab";
const normalizeContractDetailTabKey = (tab?: string | null) =>
  ["objects", "events", "workflow", "attachments", "approvals"].includes(String(tab || ""))
    ? String(tab)
    : "objects";
const consumeContractDetailTabKey = () => {
  try {
    const tab = sessionStorage.getItem(CONTRACT_DETAIL_TAB_STORAGE_KEY);
    sessionStorage.removeItem(CONTRACT_DETAIL_TAB_STORAGE_KEY);
    return tab ? normalizeContractDetailTabKey(tab) : null;
  } catch {
    // Detail pages should still open when session storage is unavailable.
  }
  return null;
};
const consumeContractDetailReturnView = () => {
  try {
    const view = String(sessionStorage.getItem(CONTRACT_DETAIL_RETURN_VIEW_STORAGE_KEY) || "");
    sessionStorage.removeItem(CONTRACT_DETAIL_RETURN_VIEW_STORAGE_KEY);
    return normalizeContractDetailReturnView(view);
  } catch {
    // Detail pages can still close safely when session storage is unavailable.
  }
  return "contract-mine";
};
const readContractQuery = (view: string): Record<string, any> => {
  const parsed = readContractListQuery(sessionStorage, view) as Record<string, any>;
  if (Array.isArray(parsed.signed_at)) parsed.signed_at = parsed.signed_at.map((value: string) => dayjs(value));
  return parsed;
};
const initialProfile = (): Profile => {
  try {
    const stored = JSON.parse(localStorage.getItem("user") || "{}");
    return {
      username: stored.username || "",
      display_name: stored.display_name || "",
      department: stored.department || "",
      role: stored.role || "",
    };
  } catch {
    return { username: "", display_name: "", department: "", role: "" };
  }
};
export default function ContractCenterPage({
  initialView,
  onNavigate,
  detailTarget,
  onDetailTargetHandled,
}: {
  initialView: string;
  onNavigate?: (key: string) => void;
  detailTarget?: ContractDetailNavigationContext | null;
  onDetailTargetHandled?: () => void;
}) {
  const customerContextConsumerRef = useRef(createContractCustomerContextConsumer(sessionStorage));
  const newContractRouteInitializedRef = useRef(false);
  const isContractDetailView = initialView.startsWith("contract-detail-") || initialView.startsWith("contract-preview-");
  const contractDetailRouteMatch = initialView.match(/^contract-detail-(\d+)-(.+)$/);
  const contractPreviewRouteMatch = initialView.match(/^contract-preview-(.+)$/);
  const contractDetailRouteTarget: ContractDetailNavigationContext | null = contractDetailRouteMatch
    ? { id: Number(contractDetailRouteMatch[1]), serial_no: decodeURIComponent(contractDetailRouteMatch[2]), at: Date.now() }
    : contractPreviewRouteMatch
      ? { serial_no: decodeURIComponent(contractPreviewRouteMatch[1]), at: Date.now() }
      : null;
  const [allRows, setAllRows] = useState<Contract[]>([]),
    [loading, setLoading] = useState(false),
    [open, setOpen] = useState(initialView === "contract-new"),
    [editing, setEditing] = useState<Contract | null>(null),
    [wizardDraft, setWizardDraft] = useState<Contract | null>(null),
    [wizardStep, setWizardStep] = useState(0),
    [submitting, setSubmitting] = useState<Contract | null>(null),
    [reviewing, setReviewing] = useState<Contract | null>(null),
    [steps, setSteps] = useState<Step[]>([]),
    [reviewCurrentStep, setReviewCurrentStep] = useState<Step | null>(null),
    [changing, setChanging] = useState<Contract | null>(null),
    [changeHistory, setChangeHistory] = useState<Contract | null>(null),
    [investigating, setInvestigating] = useState<Contract | null>(null),
    [paymentTarget, setPaymentTarget] = useState<Contract | null>(null),
    [invoiceTarget, setInvoiceTarget] = useState<Contract | null>(null),
    [viewing, setViewing] = useState<Contract | null>(null),
    [changes, setChanges] = useState<Change[]>([]),
    [contractEvents, setContractEvents] = useState<ContractEvent[]>([]),
    [contractWorkflowEvents, setContractWorkflowEvents] = useState<ContractEvent[]>([]),
    [contractEventPage, setContractEventPage] = useState(1),
    [contractEventPageSize, setContractEventPageSize] = useState(15),
    [contractEventTotal, setContractEventTotal] = useState(0),
    [contractEventKeyword, setContractEventKeyword] = useState(""),
    [contractEventsLoading, setContractEventsLoading] = useState(false),
    [contractEventsError, setContractEventsError] = useState<string | null>(null),
    [eventTarget, setEventTarget] = useState<Contract | null>(null),
    [eventSaving, setEventSaving] = useState(false);
  const [submitSaving, setSubmitSaving] = useState(false);
  const [paymentSaving, setPaymentSaving] = useState(false);
  const [invoiceSaving, setInvoiceSaving] = useState(false);
  const [directory, setDirectory] = useState<DirectoryUser[]>([]);
  const personName = (value: unknown) => displayChinesePersonName(value, directory);
  const peopleNames = (value: unknown) => displayChinesePersonNames(value, directory);
  const [approverSettingsOpen, setApproverSettingsOpen] = useState(false);
  const [approverSettings, setApproverSettings] = useState<ApproverSetting[]>([]);
  const [selectedApproverUsernames, setSelectedApproverUsernames] = useState<string[]>([]);
  const [approverSettingsTargetUsername, setApproverSettingsTargetUsername] = useState("");
  const [approverSettingsLoading, setApproverSettingsLoading] = useState(false);
  const [approverSettingsSaving, setApproverSettingsSaving] = useState(false);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [viewingAttachments, setViewingAttachments] = useState<Attachment[]>([]);
  const [detailActiveTab, setDetailActiveTab] = useState("objects");
  const [selectedAttachmentKeys, setSelectedAttachmentKeys] = useState<Key[]>([]);
  const [attachmentBatchSaving, setAttachmentBatchSaving] = useState(false);
  const [detailReceipts, setDetailReceipts] = useState<any[]>([]);
  const [detailInvoices, setDetailInvoices] = useState<Contract[]>([]);
  const [detailPayments, setDetailPayments] = useState<Contract[]>([]);
  const [detailApprovals, setDetailApprovals] = useState<Step[]>([]);
  const [detailApprovalsError, setDetailApprovalsError] = useState<string | null>(null);
  type ContractObjectRow = {id:number;case_record_id:number;case_no:string;case_title:string;case_type:string;case_phase:string;fee_type:string;amount:number;customer_manager:string;remark:string;logs:Array<{id:number;action:string;before:Record<string,unknown>;after:Record<string,unknown>;operator:string;created_at:string}>};
  const [contractObjects, setContractObjects] = useState<ContractObjectRow[]>([]);
  const [objectPage, setObjectPage] = useState<number>(1);
  const [objectPageSize, setObjectPageSize] = useState<number>(CONTRACT_OBJECT_DEFAULT_PAGE_SIZE);
  const [paymentCandidates, setPaymentCandidates] = useState<ContractPaymentCandidate[]>([]);
  const [paymentTypes, setPaymentTypes] = useState<PaymentTypeOption[]>([]);
  const [selectedPaymentObjectKeys, setSelectedPaymentObjectKeys] = useState<Key[]>([]);
  const [paymentAmounts, setPaymentAmounts] = useState<Record<number, number>>({});
  const [objectEditing, setObjectEditing] = useState<{id?:number}|null>(null);
  const [objectCases, setObjectCases] = useState<Array<{id:number;serial_no:string;title:string;customer:string}>>([]);
  const [objectLogTarget, setObjectLogTarget] = useState<ContractObjectRow | null>(null);
  const [viewingAttachmentsLoading, setViewingAttachmentsLoading] = useState(false);
  const [viewingAttachmentsError, setViewingAttachmentsError] = useState<string | null>(null);
  const [attachmentPreview, setAttachmentPreview] = useState<AttachmentPreview | null>(null);
  const viewingAttachmentRequest = useRef(0);
  const contractEventRequestTracker = useRef(createContractEventRequestTracker());
  const contractEventSubmitGate = useRef(createContractEventSubmitGate());
  const contractMutationGates = useRef({
    submit: createContractMutationGate(),
    payment: createContractMutationGate(),
    invoice: createContractMutationGate(),
    attachment: createContractMutationGate(),
  });
  const [history, setHistory] = useState<HistoryEvent[]>([]);
  const [sealAssets, setSealAssets] = useState<SealAsset[]>([]);
  const [customers, setCustomers] = useState<CustomerRef[]>([]);
  const [linkedCustomerContext, setLinkedCustomerContext] = useState<LinkedCustomerContext | null>(null);
  const [contractFile, setContractFile] = useState<File | null>(null);
  const [savingContract, setSavingContract] = useState(false);
  const [submittingWizard, setSubmittingWizard] = useState(false);
  const [profile, setProfile] = useState<Profile>(initialProfile);
  const customerRelationQueryRef = useRef<Record<string, any> | null>(null);
  const customerRelationQueryViewRef = useRef<string | null>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([]),
    [query, setQuery] = useState<Record<string, any>>(() => readContractQuery(initialView)),
    [listPagination, setListPagination] = useState(() => readContractListPagination(sessionStorage, initialView));
  const [form] = Form.useForm(),
    [submitForm] = Form.useForm(),
    [reviewForm] = Form.useForm(),
    [sealForm] = Form.useForm(),
    [investigationForm] = Form.useForm(),
    [paymentForm] = Form.useForm(),
    [invoiceForm] = Form.useForm(),
    [changeForm] = Form.useForm(),
    [queryForm] = Form.useForm(),
    [eventForm] = Form.useForm(),
    [objectForm] = Form.useForm();
  const investigationRegion = Form.useWatch("region", investigationForm);
  const listViewConfig = contractListViewConfig(initialView);
  const closeViewing = () => {
    viewingAttachmentRequest.current += 1;
    contractEventRequestTracker.current.next();
    setViewing(null);
    setViewingAttachments([]);
    setSelectedAttachmentKeys([]);
    setAttachmentBatchSaving(false);
    setContractObjects([]);
    setObjectPage(1);
    setObjectPageSize(CONTRACT_OBJECT_DEFAULT_PAGE_SIZE);
    setObjectEditing(null);
    setObjectLogTarget(null);
    setPaymentCandidates([]);
    setPaymentTypes([]);
    setSelectedPaymentObjectKeys([]);
    setPaymentAmounts({});
    setContractEvents([]);
    setContractWorkflowEvents([]);
    setContractEventPage(1);
    setContractEventPageSize(15);
    setContractEventTotal(0);
    setContractEventKeyword("");
    setContractEventsLoading(false);
    setContractEventsError(null);
    setDetailApprovalsError(null);
    setViewingAttachmentsError(null);
    setDetailReceipts([]);
    setDetailInvoices([]);
    setDetailPayments([]);
    setDetailApprovals([]);
    setViewingAttachmentsLoading(false);
    setDetailActiveTab("objects");
  };
  const openViewing = async (contract: Contract, options: { detailTab?: string } = {}) => {
    if (!isContractDetailView) {
      try {
        saveContractListQuery(sessionStorage, initialView, query);
        sessionStorage.setItem(CONTRACT_DETAIL_RETURN_VIEW_STORAGE_KEY, initialView);
        if (options.detailTab) {
          sessionStorage.setItem(CONTRACT_DETAIL_TAB_STORAGE_KEY, normalizeContractDetailTabKey(options.detailTab));
        } else {
          sessionStorage.removeItem(CONTRACT_DETAIL_TAB_STORAGE_KEY);
        }
      } catch {
        // Session storage may be unavailable in embedded/private contexts.
      }
      const route = buildContractDetailRoute(contract);
      if (route) onNavigate?.(route);
      return;
    }
    const pendingDetailTab = options.detailTab ? normalizeContractDetailTabKey(options.detailTab) : consumeContractDetailTabKey();
    if (pendingDetailTab) setDetailActiveTab(pendingDetailTab);
    else if (viewing?.id !== contract.id) setDetailActiveTab("objects");
    const requestId = ++viewingAttachmentRequest.current;
    const eventRequestId = contractEventRequestTracker.current.next();
    setViewing(contract);
    setViewingAttachments([]);
    setSelectedAttachmentKeys([]);
    setViewingAttachmentsLoading(true);
    setViewingAttachmentsError(null);
    setContractEventsLoading(true);
    setContractEventsError(null);
    try {
      const eventRequest = buildContractEventsRequest(contract, { page: 1, pageSize: 15 });
      const [attachmentResult, eventResult, workflowHistoryResult, objectResult, caseResult, receiptResult, invoiceResult, paymentResult, approvalResult] = await Promise.allSettled([
        api.get("/attachments", { params: { record_id: contract.id } }),
        eventRequest.path ? api.get(eventRequest.path, { params: eventRequest.params }) : Promise.resolve({ data: { items: [] } }),
        api.get(`/records/${contract.id}/history`),
        api.get(`/contracts/${contract.id}/objects`),
        api.get(`/contracts/${contract.id}/object-cases`),
        api.get("/finance/incoming-payments"),
        // Invoice records are keyed by contract_record_id/contract_no rather
        // than the generic record serial/title search fields.  Query the
        // finance invoice projection so issued applications reappear in the
        // contract detail instead of falling through to an empty table.
        api.get("/finance/invoices", { params: { scope: "company", customer: contract.customer, page: 1, page_size: 100 } }),
        api.get(`/contracts/${contract.id}/payment-applications`),
        api.get(`/contracts/${contract.id}/approvals`),
      ]);
      if (requestId === viewingAttachmentRequest.current) {
        setViewingAttachments(attachmentResult.status === "fulfilled" ? (attachmentResult.value.data.items || []).map((item: Attachment) => ({ ...item, ...normalizeContractAttachment(item) })) : []);
        setViewingAttachmentsError(attachmentResult.status === "rejected" ? extractContractErrorMessage(attachmentResult.reason, "合同附件加载失败") : null);
        const eventPayload = eventResult.status === "fulfilled" ? normalizeContractEventsResponse(eventResult.value.data) : null;
        const manualEvents = eventPayload?.items.map((event) => ({ ...event, contract_record_id: contract.id })) || [];
        const workflowEvents = workflowHistoryResult.status === "fulfilled"
          ? (workflowHistoryResult.value.data.items || []).map((event: HistoryEvent) => ({
            id: -event.id,
            contract_record_id: contract.id,
            content: [event.action, event.comment].filter(Boolean).join("："),
            operator: event.operator,
            created_at: event.created_at,
          }))
          : [];
        if (contractEventRequestTracker.current.isCurrent(eventRequestId)) {
          setContractEvents(manualEvents);
          setContractWorkflowEvents(workflowEvents);
          setContractEventPage(eventPayload?.page || 1);
          setContractEventPageSize(eventPayload?.pageSize || 15);
          setContractEventTotal(eventPayload?.total || 0);
          setContractEventKeyword("");
          setContractEventsError(eventResult.status === "rejected" ? extractContractErrorMessage(eventResult.reason, "合同事项加载失败") : null);
        }
        setObjectPage(1);
        setObjectPageSize(CONTRACT_OBJECT_DEFAULT_PAGE_SIZE);
        setContractObjects(objectResult.status === "fulfilled"
          ? sortContractObjectRows((objectResult.value.data.items || []).map((item: ContractObjectRow) => ({ ...item, logs: sortContractObjectLogs(item.logs || []) })))
          : []);
        setObjectCases(caseResult.status === "fulfilled" ? (caseResult.value.data.items || []) : []);
        setDetailReceipts(receiptResult.status === "fulfilled"
          ? sortContractRecordRows(filterContractIncomingPayments(receiptResult.value.data.items || [], contract) as any[])
          : []);
        setDetailInvoices(invoiceResult.status === "fulfilled"
          ? sortContractRecordRows(filterContractLinkedRows(invoiceResult.value.data.items || [], contract))
          : []);
        setDetailPayments(paymentResult.status === "fulfilled"
          ? normalizeContractPaymentApplications(paymentResult.value.data, contract).slice().sort((left, right) => left.id - right.id)
          : []);
        const approvalItems = approvalResult.status === "fulfilled" ? approvalResult.value.data.items || [] : [];
        setDetailApprovals(normalizeContractApprovalHistory(approvalItems).map((item, index) => ({ ...item, step_order: Number(approvalItems[index]?.step_order || index + 1) })) as Step[]);
        setDetailApprovalsError(approvalResult.status === "rejected" ? extractContractErrorMessage(approvalResult.reason, "合同审批信息加载失败") : null);
        if (attachmentResult.status === "rejected" || (contractEventRequestTracker.current.isCurrent(eventRequestId) && (eventResult.status === "rejected" || workflowHistoryResult.status === "rejected")) || objectResult.status === "rejected" || approvalResult.status === "rejected") {
          message.warning("合同基础信息已打开，部分附件、事项、合同标的或审批信息暂时加载失败");
        }
      }
    } catch (error: any) {
      if (requestId === viewingAttachmentRequest.current) {
        message.error(error?.response?.data?.detail || "合同附件加载失败，请稍后重试");
      }
    } finally {
      if (requestId === viewingAttachmentRequest.current) {
        setViewingAttachmentsLoading(false);
        if (contractEventRequestTracker.current.isCurrent(eventRequestId)) setContractEventsLoading(false);
      }
    }
  };
  const reloadContractEvents = async (contract: Contract, page = 1, keyword = contractEventKeyword, pageSize = contractEventPageSize) => {
    const eventRequestId = contractEventRequestTracker.current.next();
    const eventRequest = buildContractEventsRequest(contract, { page, pageSize, keyword });
    if (!eventRequest.path) {
      if (contractEventRequestTracker.current.isCurrent(eventRequestId)) {
        setContractEvents([]);
        setContractEventTotal(0);
        setContractEventsError(null);
        setContractEventsLoading(false);
      }
      return;
    }
    setContractEventsLoading(true);
    setContractEventsError(null);
    try {
      const response = await api.get(eventRequest.path, { params: eventRequest.params });
      const payload = normalizeContractEventsResponse(response.data);
      if (contractEventRequestTracker.current.isCurrent(eventRequestId)) {
        setContractEvents(payload.items.map((event) => ({ ...event, contract_record_id: contract.id })));
        setContractEventPage(payload.page);
        setContractEventPageSize(payload.pageSize);
        setContractEventTotal(payload.total);
        setContractEventKeyword(String(keyword || "").trim());
      }
    } catch (error: any) {
      if (contractEventRequestTracker.current.isCurrent(eventRequestId)) setContractEventsError(extractContractErrorMessage(error, "合同事项加载失败"));
    } finally {
      if (contractEventRequestTracker.current.isCurrent(eventRequestId)) setContractEventsLoading(false);
    }
  };
  const reloadViewingAttachments = async (contract: Contract) => {
    setViewingAttachmentsLoading(true);
    setViewingAttachmentsError(null);
    try {
      const response = await api.get("/attachments", { params: { record_id: contract.id } });
      setViewingAttachments((response.data.items || []).map((item: Attachment) => ({ ...item, ...normalizeContractAttachment(item) })));
      setSelectedAttachmentKeys([]);
    } catch (error: any) {
      setViewingAttachmentsError(extractContractErrorMessage(error, "合同附件加载失败"));
    } finally {
      setViewingAttachmentsLoading(false);
    }
  };
  const reloadDetailApprovals = async (contract: Contract) => {
    setDetailApprovalsError(null);
    try {
      const response = await api.get(`/contracts/${contract.id}/approvals`);
      const items = response.data.items || [];
      setDetailApprovals(normalizeContractApprovalHistory(items).map((item: any, index: number) => ({ ...item, step_order: Number(items[index]?.step_order || index + 1) })) as Step[]);
    } catch (error: any) {
      setDetailApprovalsError(extractContractErrorMessage(error, "合同审批信息加载失败"));
    }
  };
  const handleContractDetailTabChange = (key: string) => {
    setDetailActiveTab(key);
    if (!viewing || key === detailActiveTab) return;
    if (key === "attachments") void reloadViewingAttachments(viewing);
    else if (key === "events") void reloadContractEvents(viewing, contractEventPage, contractEventKeyword, contractEventPageSize);
    else if (key === "approvals") void reloadDetailApprovals(viewing);
    else void openViewing(viewing);
  };
  const returnFromDetail = () => {
    closeViewing();
    if (isContractDetailView) onNavigate?.(consumeContractDetailReturnView());
  };
  const saveContractObject = async () => { if (!viewing || !objectEditing) return; try { const values=await objectForm.validateFields(); const request=objectEditing.id?api.patch(`/contracts/${viewing.id}/objects/${objectEditing.id}`,values):api.post(`/contracts/${viewing.id}/objects`,values); const response = await request; const feedback = normalizeContractActionResponse(response, "合同标的保存失败"); if (!feedback.ok) throw new Error(feedback.message); message.success(objectEditing.id?"合同标的已修改":"合同标的已新增"); setObjectEditing(null); objectForm.resetFields(); await openViewing(viewing) } catch(error:any) { if(!error?.errorFields) message.error(extractContractErrorMessage(error, "合同标的保存失败")) } };
  const deleteContractObject = async (objectId:number) => { if(!viewing)return; try { const response = await api.delete(`/contracts/${viewing.id}/objects/${objectId}`); const feedback = normalizeContractActionResponse(response, "合同标的删除失败"); if (!feedback.ok) throw new Error(feedback.message); message.success("合同标的已删除"); await openViewing(viewing) } catch(error:any) { message.error(extractContractErrorMessage(error, "合同标的删除失败")) } };
  const resolveContractDetailTarget = async (target: ContractDetailNavigationContext): Promise<Contract | null> => {
    if (target.id) {
      try {
        const response = await api.get(`/records/${target.id}`);
        if (response.data?.module === "contract") return response.data as Contract;
      } catch {
        // A deleted, out-of-scope, or stale id may still have a usable serial-number fallback below.
      }
    }
    const serialNo = String(target.serial_no || "").trim();
    if (!serialNo) return null;
    try {
      const response = await api.get("/records", {
        params: { module: "contract", keyword: serialNo, page: 1, page_size: 100 },
      });
      return (response.data.items || []).find((item: Contract) => item.serial_no === serialNo) || null;
    } catch {
      return null;
    }
  };
  const load = async (queryOverride?: Record<string, any>) => {
    setLoading(true);
    const target = detailTarget || consumeContractDetailTarget() || contractDetailRouteTarget;
    if (customerRelationQueryViewRef.current && customerRelationQueryViewRef.current !== initialView) {
      customerRelationQueryRef.current = null;
      customerRelationQueryViewRef.current = null;
    }
    const consumedRelationQuery = buildContractCustomerQueryFromRelation(consumeCustomerRelationTarget());
    const relationQuery = consumedRelationQuery || customerRelationQueryRef.current;
    // Relationship navigation carries the immutable customer identity and must
    // replace stale customer filters restored from a previous list visit.
    const baseQuery = queryOverride ?? query;
    const effectiveQuery = relationQuery
      ? { ...baseQuery, customer_id: undefined, customer_no: "", customer: "", ...relationQuery }
      : baseQuery;
    if (relationQuery) {
      customerRelationQueryRef.current = effectiveQuery;
      customerRelationQueryViewRef.current = initialView;
    }
    if (relationQuery) {
      queryForm.setFieldsValue(relationQuery);
      setQuery(effectiveQuery);
    }
    const recordsParams = buildContractListRequestParams(initialView, listPagination, effectiveQuery);
    const recordsRequest = api.get("/records", { params: { ...recordsParams, scope: listViewConfig.scope, page: 1, page_size: 100 } });
    const targetRequest = target ? resolveContractDetailTarget(target) : null;
    const auxiliaryRequests = Promise.allSettled([
      api.get("/auth/me"),
      api.get("/users/directory"),
      api.get("/seals/assets"),
      api.get("/customers", { params: { scope: "mine", customer_type: "客户", page: 1, page_size: 200 } }),
    ]);
    // A dedicated detail route must not wait for the full contract list or
    // unrelated directory/seal/customer data before showing its target.
    if (target) {
      const targetRow = await targetRequest;
      if (targetRow) void openViewing(targetRow);
      else message.warning("未找到关联合同或当前账号无权查看");
      onDetailTargetHandled?.();
    }
    try {
      const recordsRes = await recordsRequest;
      setAllRows(recordsRes.data.items);
    } catch (error: any) {
      message.error(extractContractErrorMessage(error, "合同数据加载失败"));
    } finally {
      setLoading(false);
    }
    const [profileResult, directoryResult, sealResult, customerResult] = await auxiliaryRequests;
    if (profileResult.status === "fulfilled") setProfile(profileResult.value.data);
    if (directoryResult.status === "fulfilled") setDirectory((directoryResult.value.data.items || []).filter((item: DirectoryUser) => item.is_active !== false));
    if (sealResult.status === "fulfilled") setSealAssets((sealResult.value.data.items || []).filter((item: SealAsset) => item.status === "可用"));
    if (customerResult.status === "fulfilled") setCustomers(customerResult.value.data.items || []);
    if ([profileResult, directoryResult, sealResult, customerResult].some((result) => result.status === "rejected")) {
      message.warning("合同基础列表已加载，部分辅助数据暂时不可用");
    }
  };
  useEffect(() => {
    load();
  }, [initialView, detailTarget?.id, detailTarget?.serial_no]);
  useEffect(() => {
    if (isContractDetailView || initialView === "contract-new") return;
    const relationQuery = customerRelationQueryRef.current;
    if (relationQuery) {
      queryForm.resetFields();
      queryForm.setFieldsValue(relationQuery);
      setQuery(relationQuery);
      return;
    }
    const savedQuery = readContractQuery(initialView);
    setQuery(savedQuery);
    queryForm.resetFields();
    queryForm.setFieldsValue(savedQuery);
  }, [initialView]);
  useEffect(() => {
    setListPagination(readContractListPagination(sessionStorage, initialView));
  }, [initialView]);
  useEffect(() => {
    if (initialView !== "contract-new") {
      customerContextConsumerRef.current.reset();
      newContractRouteInitializedRef.current = false;
      setOpen(false);
      return;
    }
    if (newContractRouteInitializedRef.current) return;
    newContractRouteInitializedRef.current = true;
    // A customer-side “新增合同” always starts a new draft for that customer.
    // It must not restore an unfinished draft belonging to a different customer.
    const customerContext = getContractCustomerContext();
    if (customerContext) {
      startCreate(customerContext);
      return;
    }
    // The contract-center entry is always a blank contract. Existing drafts
    // remain available from "我的合同" and must not silently prefill this form.
    startCreate();
  }, [initialView]);
  useEffect(() => {
    if (initialView !== "contract-approver-settings") return;
    if (profile.role !== "admin") return;
    if (approverSettingsOpen || approverSettingsLoading) return;
    const targetUsername = String(new URLSearchParams(window.location.search).get("username") || "").trim();
    setApproverSettingsTargetUsername(targetUsername);
    void openApproverSettings();
  }, [initialView, profile.role, approverSettingsOpen, approverSettingsLoading]);
  const auditViewConfig = contractAuditViewConfig(initialView);
  const rows = useMemo(() => {
    let list = customerRelationQueryRef.current
      ? allRows
      : initialView === "contract-audit-pending"
        ? filterPendingContractApprovals(allRows, profile.username)
        : initialView === "contract-audit-refused"
          ? allRows.filter((x) => auditViewConfig.statuses.includes(x.status))
        : initialView === "contract-audit-approved"
            ? allRows.filter((x) => auditViewConfig.statuses.includes(x.status))
        : initialView === "contract-mine"
          ? allRows.filter((x) =>
              [profile.username, profile.display_name].includes(x.owner),
            )
          : initialView === "contract-dept"
            ? allRows.filter((x) => x.department === profile.department)
            : allRows;
    const text = (v: any) => String(v || "").toLowerCase();
    if (query.title)
      list = list.filter((x) => text(x.title).includes(text(query.title)));
    if (query.serial_no)
      list = list.filter((x) =>
        text(x.serial_no).includes(text(query.serial_no)),
      );
    if (query.type) list = list.filter((x) => x.data.type === query.type);
    if (query.customer_id)
      list = list.filter((x) => Number(x.data.customer_id) === Number(query.customer_id));
    else if (query.customer_no)
      list = list.filter((x) => text(x.data.customer_no) === text(query.customer_no));
    else if (query.customer)
      list = list.filter((x) =>
        text(x.customer).includes(text(query.customer)),
      );
    if (query.exclude_archived)
      list = list.filter((x) => !["已归档", "Archived", "archived"].includes(String(x.status || "").trim()));
    if (query.case_no)
      list = list.filter((x) =>
        text(x.data.case_no).includes(text(query.case_no)),
      );
    if (query.fee_type)
      list = list.filter((x) => x.data.fee_type === query.fee_type);
    if (query.contract_body)
      list = list.filter((x) => x.data.contract_body === query.contract_body);
    if (query.source_person)
      list = list.filter((x) =>
        text(x.data.source_person || x.owner).includes(text(query.source_person)),
      );
    if (query.signed_at?.length === 2)
      list = list.filter(
        (x) =>
          x.data.signed_at &&
          dayjs(x.data.signed_at).isAfter(
            query.signed_at[0].subtract(1, "day"),
          ) &&
          dayjs(x.data.signed_at).isBefore(query.signed_at[1].add(1, "day")),
      );
    return list;
  }, [allRows, initialView, profile, query, auditViewConfig]);
  const getContractCustomerContext = (): LinkedCustomerContext | null => {
    if (sessionStorage.getItem(CONTRACT_CUSTOMER_ROUTE_SOURCE_KEY) !== "customer") {
      clearContractCustomerContext(sessionStorage);
      customerContextConsumerRef.current.reset();
      return null;
    }
    sessionStorage.removeItem(CONTRACT_CUSTOMER_ROUTE_SOURCE_KEY);
    return customerContextConsumerRef.current.consume();
  };
  const resolveCustomerRef = (customerId: number | undefined): CustomerRef | null => {
    return resolveContractCustomerSelection(customerId, customers, linkedCustomerContext, profile) as CustomerRef | null;
  };
  const startCreate = (context: LinkedCustomerContext | null = null) => {
    localStorage.removeItem(WIZARD_STORAGE_KEY);
    setEditing(null);
    setWizardDraft(null);
    setWizardStep(0);
    setContractFile(null);
    setSteps([]);
    setReviewCurrentStep(null);
    setAttachments([]);
    setHistory([]);
    form.resetFields();
    submitForm.resetFields();
    reviewForm.resetFields();
    sealForm.resetFields();
    let linkedCustomerId: number | undefined;
    let linkedContext: LinkedCustomerContext | null = null;
    if (context) {
      linkedContext = context;
      // The customer list loads asynchronously. Keep the linked id immediately;
      // customerOptions supplies the context label until the full list arrives.
      linkedCustomerId = context.id;
    }
    setLinkedCustomerContext(linkedContext);
    const defaults = buildContractDraftDefaults({
      serialNo: createContractNumber(),
      profile,
      customer: linkedContext ? { id: linkedContext.id, title: linkedContext.name } : null,
    });
    form.setFieldsValue({ ...defaults, customer_id: linkedCustomerId, signed_at: dayjs(defaults.signed_at) });
    setOpen(true);
  };
  useEffect(() => {
    const handleRouteReselect = (event: Event) => {
      if ((event as CustomEvent<string>).detail === "contract-new" && initialView === "contract-new") {
        customerContextConsumerRef.current.reset();
        startCreate(getContractCustomerContext());
      }
    };
    window.addEventListener("sunhold:route-reselect", handleRouteReselect);
    return () => window.removeEventListener("sunhold:route-reselect", handleRouteReselect);
  }, [initialView, profile.username, profile.department]);
  const populateDraftForm = (contract: Contract) => {
    setLinkedCustomerContext(null);
    const customerId = Number(contract.data.customer_id)
      || customers.find((customer) => customer.serial_no === contract.data.customer_no)?.id
      || customers.find((customer) => customer.title === contract.customer)?.id;
    form.setFieldsValue({
      ...contract,
      ...contract.data,
      customer_id: customerId || undefined,
      external_contract_numbers: contract.data.external_contract_numbers || (contract.data.external_contract_no ? [contract.data.external_contract_no] : []),
      signed_at: contract.data.signed_at ? dayjs(contract.data.signed_at) : dayjs(),
    });
  };
  const loadWizardContext = async (contractId: number) => {
    const approvalRes = await api.get(`/contracts/${contractId}/approvals`);
    const contract = approvalRes.data.contract as Contract;
    setWizardDraft(contract);
    setSteps(approvalRes.data.items || []);
    submitForm.setFieldsValue({
      approvers: (approvalRes.data.items || [])[0]?.approver,
      comment: contract.data.submit_comment || "",
    });
    populateDraftForm(contract);
    const [attachmentResult, historyResult] = await Promise.allSettled([
      api.get("/attachments", { params: { record_id: contractId } }),
      api.get(`/records/${contractId}/history`),
    ]);
    const attachmentItems = attachmentResult.status === "fulfilled" ? attachmentResult.value.data.items || [] : [];
    setAttachments(attachmentItems.map((item: Attachment) => ({ ...item, ...normalizeContractAttachment(item) })));
    setHistory(historyResult.status === "fulfilled" ? historyResult.value.data.items || [] : []);
    if (attachmentResult.status === "rejected" || historyResult.status === "rejected") {
      message.warning("合同主体已加载，部分附件或历史记录暂时不可用");
    }
    return contract;
  };
  const recoverWizard = async (contractId: number) => {
    try {
      const contract = await loadWizardContext(contractId);
      if (!["草稿", "已拒绝"].includes(contract.status)) {
        localStorage.removeItem(WIZARD_STORAGE_KEY);
        setOpen(false);
        const detailRoute = buildContractDetailRoute(contract);
        if (detailRoute) onNavigate?.(detailRoute);
        return;
      }
      setWizardStep(1);
      setOpen(true);
    } catch {
      localStorage.removeItem(WIZARD_STORAGE_KEY);
      startCreate();
    }
  };
  const startEdit = (r: Contract) => {
    setEditing(r);
    form.setFieldsValue({
      ...r,
      ...r.data,
      customer_id: Number(r.data.customer_id)
        || customers.find((customer) => customer.serial_no === r.data.customer_no)?.id
        || customers.find((customer) => customer.title === r.customer)?.id,
      external_contract_numbers: r.data.external_contract_numbers || (r.data.external_contract_no ? [r.data.external_contract_no] : []),
      signed_at: r.data.signed_at ? dayjs(r.data.signed_at) : undefined,
    });
    setOpen(true);
  };
  const canOpenSubmitWizard = (contract?: Contract | null) => ["草稿", "已拒绝"].includes(contract?.status || "");
  const openSubmitWizardFromList = async (contract: Contract) => {
    if (!canOpenSubmitWizard(contract)) {
      message.warning("仅草稿或已拒绝合同可以提交审批");
      return;
    }
    try {
      setEditing(null);
      setSubmitting(null);
      setChanging(null);
      await loadWizardContext(contract.id);
      localStorage.setItem(WIZARD_STORAGE_KEY, String(contract.id));
      setWizardStep(1);
      setOpen(true);
    } catch (error: any) {
      message.error(extractContractErrorMessage(error, "合同提交审批信息加载失败"));
    }
  };
  const openContractAttachments = (contract: Contract) => {
    void openViewing(contract, { detailTab: "attachments" });
  };
  const openContractApprovalInfo = (contract: Contract) => {
    void openViewing(contract, { detailTab: "approvals" });
  };
  const openContractRelatedCaseFromList = (contract: Contract) => {
    const data = contract.data as Record<string, unknown>;
    void openRelatedCase(data.case_no || data.case_serial_no || data.related_case_no);
  };
  const save = async () => {
    let v: any;
    try {
      v = await form.validateFields();
    } catch {
      message.warning("请先补全红色提示的合同必填信息");
      return;
    }
    const draftErrors = validateContractDraftValues(v);
    if (draftErrors.length) {
      if (draftErrors.includes("customer_id")) form.setFields([{ name: "customer_id", errors: ["请选择客户"] }]);
      if (draftErrors.includes("title")) form.setFields([{ name: "title", errors: ["请输入合同名称"] }]);
      message.warning("请先补全合同必填信息");
      return;
    }
    const selectedCustomer = customers.find((customer) => customer.id === Number(v.customer_id)) || resolveCustomerRef(Number(v.customer_id));
    if (!selectedCustomer) {
      form.setFields([{ name: "customer_id", errors: ["请从客户列表中选择准确客户"] }]);
      message.warning("请输入客户关键字，并从匹配结果中选择客户");
      return;
    }
    const contractFileError = validateContractAttachment(contractFile);
    if (contractFile && contractFileError) {
      message.warning(contractFileError);
      return;
    }
    setSavingContract(true);
    try {
      const target = editing || wizardDraft;
      const sourceData: Contract["data"] = target?.data || { amount: 0, signed_at: "", type: "" };
      const signedAt = dayjs.isDayjs(v.signed_at)
        ? v.signed_at
        : sourceData.signed_at
          ? dayjs(sourceData.signed_at)
          : dayjs();
      const externalNumbers = v.external_contract_numbers || sourceData.external_contract_numbers || [];
      const data = {
        ...sourceData,
        amount: Number(v.amount ?? sourceData.amount ?? 0),
        signed_at: signedAt.format("YYYY-MM-DD"),
        type: v.type || sourceData.type || "法律顾问合同",
        contract_body: v.contract_body || sourceData.contract_body || "律所",
        fee_type: v.fee_type || sourceData.fee_type || "固定收费",
        external_contract_numbers: externalNumbers,
        external_contract_no: externalNumbers[0] || "",
        customer_id: selectedCustomer.id,
        customer_no: selectedCustomer.serial_no,
        customer_manager: (selectedCustomer.data.customer_managers || [selectedCustomer.owner]).join("、"),
      };
      const payload = {
        serial_no: target ? v.serial_no || target.serial_no || createContractNumber() : "",
        title: v.title,
        customer: selectedCustomer.title,
        owner: v.owner || target?.owner || profile.username || "admin",
        department: v.department || target?.department || profile.department || "上海分所",
        description: v.description || "",
        data,
      };
      const response = target
        ? await api.patch(`/contracts/${target.id}`, payload)
        : await api.post("/contracts", payload);
      const feedback = normalizeContractActionResponse(response, "保存失败");
      if (!feedback.ok) throw new Error(feedback.message);
      if (!editing) {
        setWizardDraft(response.data);
        localStorage.setItem(WIZARD_STORAGE_KEY, String(response.data.id));
      }
      if (contractFile) {
        const attachment = new FormData();
        attachment.append("file", contractFile);
        attachment.append("record_id", String(response.data.id));
        attachment.append("category", "合同附件");
        attachment.append("remark", "合同起草时上传");
        const attachmentResponse = await api.post("/attachments", attachment);
        const attachmentFeedback = normalizeContractActionResponse(attachmentResponse, "合同附件上传失败");
        if (!attachmentFeedback.ok) throw new Error(attachmentFeedback.message);
      }
      message.success(editing ? "合同已更新" : "合同草稿已保存，进入提交审批");
      sessionStorage.removeItem("sunhold:contract-customer");
      setContractFile(null);
      if (editing) {
        setOpen(false);
      } else {
        await loadWizardContext(response.data.id);
        setWizardStep(1);
      }
      await load();
    } catch (error: any) {
      message.error(extractContractErrorMessage(error, "保存失败"));
    } finally {
      setSavingContract(false);
    }
  };
  const submitWizard = async () => {
    if (!wizardDraft) return;
    try {
      const values = await submitForm.validateFields();
      const attachmentResponse = await api.get("/attachments", { params: { record_id: wizardDraft.id } });
      const currentAttachments = (attachmentResponse.data.items || []).map((item: Attachment) => ({ ...item, ...normalizeContractAttachment(item) }));
      setAttachments(currentAttachments);
      const submissionErrors = validateContractApprovalSubmission(wizardDraft.status, values.approvers, currentAttachments.length);
      if (submissionErrors.includes("status")) {
        message.warning("仅草稿或已拒绝合同可以提交审批");
        return;
      }
      if (submissionErrors.includes("approver")) {
        message.warning("请选择一名合同审批人");
        return;
      }
      if (submissionErrors.includes("attachment")) {
        message.warning("请先上传至少一份合同附件后再提交审批");
        return;
      }
      setSubmittingWizard(true);
      const response = await api.post(`/contracts/${wizardDraft.id}/submit`, { approvers: values.approvers ? [values.approvers] : [], comment: values.comment || "", sync_seal: Boolean(values.sync_seal) });
      const feedback = normalizeContractActionResponse(response, "提交审批失败");
      if (!feedback.ok) throw new Error(feedback.message);
      const contract = await loadWizardContext(wizardDraft.id);
      const approverName = approvalOptions.find((option) => option.value === values.approvers)?.label || personName(values.approvers);
      message.success(`合同已进入 ${approverName} 的待审批列表`);
      if (values.sync_seal) {
        setWizardStep(3);
        message.info("已同步进入申请用印，请填写用印信息后生成用印申请");
      } else {
        localStorage.removeItem(WIZARD_STORAGE_KEY);
        setOpen(false);
        onNavigate?.(`contract-detail-${contract.id}-${encodeURIComponent(contract.serial_no)}`);
      }
      await load();
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(extractContractErrorMessage(error, "提交审批失败"));
    } finally {
      setSubmittingWizard(false);
    }
  };
  const refreshWizard = async () => {
    if (!wizardDraft) return;
    try {
      const contract = await loadWizardContext(wizardDraft.id);
      if (contract.status === "已拒绝") {
        setWizardStep(1);
        sealForm.resetFields();
        setContractFile(null);
        setSelectedAttachmentKeys([]);
      } else if (CONTRACT_SEAL_READY_STATUSES.includes(contract.status)) {
        setWizardStep(3);
        sealForm.setFieldsValue({
          copies: 1,
          use_date: dayjs().add(1, "day"),
          delivery_method: "现场用印",
          document_names: attachments.map((item) => item.original_name).join("、"),
          purpose: `${contract.title}合同用印`,
          submit: false,
        });
      }
    } catch {
      message.error("审批状态加载失败");
    }
  };
  const approveWizard = async (approved: boolean) => {
    if (!wizardDraft) return;
    const values = await reviewForm.validateFields();
    if (!approved && !String(values.comment || "").trim()) {
      message.warning("拒绝时必须填写审批意见");
      return;
    }
    try {
      const response = await api.post(`/contracts/${wizardDraft.id}/approve`, buildContractApprovalPayload(approved, values.comment));
      const feedback = normalizeContractActionResponse(response, "审批失败");
      if (!feedback.ok) throw new Error(feedback.message);
      reviewForm.resetFields();
      const contract = await loadWizardContext(wizardDraft.id);
      if (!approved || contract.status === "已拒绝") {
        setWizardStep(1);
        sealForm.resetFields();
        setContractFile(null);
        setSelectedAttachmentKeys([]);
      } else if (CONTRACT_SEAL_READY_STATUSES.includes(contract.status)) {
        setWizardStep(3);
        sealForm.setFieldsValue({
          copies: 1,
          use_date: dayjs().add(1, "day"),
          delivery_method: "现场用印",
          document_names: attachments.map((item) => item.original_name).join("、"),
          purpose: `${contract.title}合同用印`,
          submit: false,
        });
      }
      message.success(approved ? "当前审批节点已通过" : "合同审批已拒绝");
      await load();
    } catch (error: any) {
      message.error(extractContractErrorMessage(error, "审批失败"));
    }
  };
  const createSealApplication = async () => {
    if (!wizardDraft) return;
    try {
      const values = await sealForm.validateFields();
      const { submit: enterSealCenter, ...sealValues } = values;
      const { data } = await api.post(`/contracts/${wizardDraft.id}/seal-application`, {
        ...sealValues,
        use_date: formatRequiredDate(values.use_date, "计划用印日期"),
      });
      const contract = await loadWizardContext(wizardDraft.id);
      if (contract.status !== "审批中") localStorage.removeItem(WIZARD_STORAGE_KEY);
      message.success(enterSealCenter
        ? "合同用印申请草稿已创建，正在进入用印中心上传文件并提交审批"
        : "合同用印申请草稿已创建，请到用印中心上传真实用印文件后提交审批");
      setWizardDraft(contract);
      await load();
      if (enterSealCenter) {
        setOpen(false);
        onNavigate?.("seal-my");
      }
      return data;
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "合同用印申请创建失败");
    }
  };
  const downloadAttachment = async (item: Attachment) => {
    try {
      const response = await api.get(`/attachments/${item.id}/download`, { responseType: "blob" });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = item.original_name;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error: any) {
      message.error(extractContractErrorMessage(error, "附件下载失败"));
    }
  };
  const previewAttachment = async (item: Attachment) => {
    try {
      const { data } = await api.get(`/attachments/${item.id}/preview`);
      if (data.kind === "unsupported") {
        message.info(data.detail || "当前文件格式暂不支持在线预览，请下载后查看");
        return;
      }
      if (data.kind === "image" || data.kind === "pdf") {
        const response = await api.get(`/attachments/${item.id}/download`, { responseType: "blob" });
        setAttachmentPreview({ name: item.original_name, kind: data.kind, url: URL.createObjectURL(response.data) });
      } else {
        setAttachmentPreview({ name: item.original_name, kind: data.kind, text: data.text || "" });
      }
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "合同附件预览失败");
    }
  };
  const closeAttachmentPreview = () => {
    if (attachmentPreview?.url) URL.revokeObjectURL(attachmentPreview.url);
    setAttachmentPreview(null);
  };
  const uploadDraftContractAttachment = async () => {
    if (!wizardDraft) return;
    if (!contractFile) {
      message.warning("请先选择合同附件");
      return;
    }
    const attachmentError = validateContractAttachment(contractFile);
    if (attachmentError) {
      message.warning(attachmentError);
      return;
    }
    const attachment = new FormData();
    attachment.append("file", contractFile);
    attachment.append("record_id", String(wizardDraft.id));
    attachment.append("category", "合同附件");
    attachment.append("remark", "合同草稿补传附件");
    try {
      const response = await api.post("/attachments", attachment);
      const feedback = normalizeContractActionResponse(response, "合同附件上传失败");
      if (!feedback.ok) throw new Error(feedback.message);
      setContractFile(null);
      await loadWizardContext(wizardDraft.id);
      message.success("合同附件已上传");
    } catch (error: any) {
      message.error(extractContractErrorMessage(error, "合同附件上传失败"));
    }
  };
  const uploadViewingAttachment = async () => {
    if (!viewing) return;
    if (!contractFile) {
      message.warning("请先选择合同附件");
      return;
    }
    const attachmentPolicy = contractAttachmentActionPolicy(viewing.status);
    if (!attachmentPolicy.canUpload || !canMutateContractAttachments(viewing.status)) {
      message.warning("当前合同状态不允许修改附件");
      return;
    }
    const attachmentError = validateContractAttachment(contractFile);
    if (attachmentError && attachmentError !== "请选择合同附件") {
      message.error(attachmentError);
      return;
    }
    if (contractFile.size > 20 * 1024 * 1024) {
      message.error("单个文件不能超过 20MB");
      return;
    }
    const attachment = new FormData();
    attachment.append("file", contractFile);
    attachment.append("record_id", String(viewing.id));
    attachment.append("category", "合同附件");
    attachment.append("remark", "合同详情补传附件");
    try {
      const response = await api.post("/attachments", attachment);
      const feedback = normalizeContractActionResponse(response, "合同附件上传失败");
      if (!feedback.ok) throw new Error(feedback.message);
      setContractFile(null);
      await openViewing(viewing);
      message.success("合同附件已上传");
    } catch (error: any) {
      message.error(extractContractErrorMessage(error, "合同附件上传失败"));
    }
  };
  const deleteViewingAttachment = async (item: Attachment) => {
    try {
      const response = await api.delete(`/attachments/${item.id}`);
      const feedback = normalizeContractActionResponse(response, "合同附件删除失败");
      if (!feedback.ok) throw new Error(feedback.message);
      await openViewing(viewing!);
      message.success("合同附件已删除");
    } catch (error: any) {
      message.error(extractContractErrorMessage(error, "合同附件删除失败"));
    }
  };
  const batchDeleteViewingAttachments = async () => {
    const target = viewing;
    const deletePlan = buildContractAttachmentDeletePlan(selectedAttachmentKeys);
    if (!target) return;
    if (!deletePlan.length) {
      message.warning("请先选择要删除的合同附件");
      return;
    }
    if (!contractAttachmentActionPolicy(target.status).canDelete) {
      message.warning("当前合同状态不允许删除附件");
      return;
    }
    Modal.confirm({
      title: "确认批量删除合同附件？",
      content: `将删除已选择的 ${deletePlan.length} 个合同附件。若后端返回失败，失败项会保留选中并显示原始失败消息。`,
      okText: "确认删除",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onOk: async () => {
        if (!contractMutationGates.current.attachment.tryEnter()) return;
        setAttachmentBatchSaving(true);
        try {
          const response = await api.post(`/contracts/${target.id}/attachments/delete`, { fileIds: deletePlan });
          const feedback = normalizeContractActionResponse(response, "合同附件删除失败");
          const rawFailed = Array.isArray(response.data?.failed) ? response.data.failed : [];
          const summary: { deleted: number; failed: { id: number; message: string }[] } = {
            deleted: Number(response.data?.deleted || 0),
            failed: rawFailed.map((item: any, index: number) => ({
              id: Number(item.id ?? item.file_id ?? item.fileId ?? deletePlan[index]) || 0,
              message: String(item.message || item.detail || feedback.message),
            })),
          };
          if (!feedback.ok && !summary.failed.length) {
            summary.failed = deletePlan.map((id) => ({ id: Number(id), message: feedback.message }));
          }
          if (summary.failed.length) {
            setSelectedAttachmentKeys(summary.failed.map((item) => item.id).filter(Boolean));
            if (summary.deleted) await reloadViewingAttachments(target);
            message.error(`合同附件批量删除未完成：${summary.failed.map((item) => item.message).join("；")}`);
            return;
          }
          if (summary.deleted) await reloadViewingAttachments(target);
          setSelectedAttachmentKeys([]);
          message.success(`已删除 ${summary.deleted || deletePlan.length} 个合同附件`);
        } finally {
          contractMutationGates.current.attachment.leave();
          setAttachmentBatchSaving(false);
        }
      },
    });
  };
  const submit = async () => {
    if (!submitting || !contractMutationGates.current.submit.tryEnter()) return;
    setSubmitSaving(true);
    try {
      const v = await submitForm.validateFields();
      const response = await api.post(`/contracts/${submitting.id}/submit`, { approvers: v.approvers ? [v.approvers] : [], comment: v.comment || "" });
      const feedback = normalizeContractActionResponse(response, "提交审批失败");
      if (!feedback.ok) throw new Error(feedback.message);
      const approverName = approvalOptions.find((option) => option.value === v.approvers)?.label || personName(v.approvers);
      message.success(`已提交至 ${approverName} 的待审批列表`);
      setSubmitting(null);
      await load();
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(extractContractErrorMessage(error, "提交失败"));
    } finally {
      contractMutationGates.current.submit.leave();
      setSubmitSaving(false);
    }
  };
  const openReview = async (r: Contract) => {
    try {
      const { data } = await api.get(`/contracts/${r.id}/approvals`);
      setReviewing(r);
      setSteps(data.items);
      setReviewCurrentStep(selectContractCurrentApprovalStep<Step>(data));
    } catch {
      message.error("审批节点加载失败");
    }
  };
  const approve = async (approved: boolean) => {
    if (!reviewing) return;
    const v = await reviewForm.validateFields();
    try {
      const response = await api.post(`/contracts/${reviewing.id}/approve`, buildContractApprovalPayload(approved, v.comment));
      const feedback = normalizeContractActionResponse(response, "审批失败");
      if (!feedback.ok) throw new Error(feedback.message);
      message.success(approved ? "当前审批节点已通过" : "合同已拒绝");
      reviewForm.resetFields();
      const { data } = await api.get(`/contracts/${reviewing.id}/approvals`);
      setSteps(data.items);
      setReviewing(data.contract);
      setReviewCurrentStep(selectContractCurrentApprovalStep<Step>(data));
      if (!approved || data.contract?.status === "已拒绝") {
        sealForm.resetFields();
        setContractFile(null);
        setSelectedAttachmentKeys([]);
      }
      if (viewing?.id === data.contract?.id) {
        setViewing(data.contract);
        await reloadViewingAttachments(data.contract);
        await reloadDetailApprovals(data.contract);
      }
      await load();
    } catch (error: any) {
      message.error(extractContractErrorMessage(error, "审批失败"));
    }
  };
  const openChange = (r: Contract) => {
    setChanging(r);
    changeForm.resetFields();
    changeForm.setFieldsValue({
      change_type: "合同补充/修订",
      customer: r.customer,
      contract_body: r.data.contract_body || "律所",
      contract_type: r.data.type || "其他",
      fee_type: r.data.fee_type || "固定收费",
      title: r.title,
      amount: r.data.amount,
      description: (r.data as any).description || "",
      external_contract_numbers: r.data.external_contract_numbers || (r.data.external_contract_no ? [r.data.external_contract_no] : []),
      end_date: r.data.end_date ? dayjs(r.data.end_date) : undefined,
    });
  };
  const saveChange = async () => {
    if (!changing) return;
    const v = await changeForm.validateFields();
    try {
      const response = await api.post(`/contracts/${changing.id}/changes`, {
        ...v,
        end_date: v.end_date?.format("YYYY-MM-DD"),
      });
      const feedback = normalizeContractActionResponse(response, "合同变更失败");
      if (!feedback.ok) throw new Error(feedback.message);
      message.success("合同变更已提交审批");
      setChanging(null);
      load();
    } catch (error: any) {
      message.error(extractContractErrorMessage(error, "合同变更失败"));
    }
  };
  const reviewChange = async (contract: Contract, approved: boolean) => {
    try {
      const response = await api.post(`/contracts/${contract.id}/changes/review`, { approved, comment: approved ? "同意合同变更" : "变更内容需补充后重新提交" });
      const feedback = normalizeContractActionResponse(response, "合同变更审批失败");
      if (!feedback.ok) throw new Error(feedback.message);
      message.success(approved ? "合同变更已审批通过" : "合同变更已驳回");
      setSelectedRowKeys([]);
      await load();
    } catch (error: any) {
      message.error(extractContractErrorMessage(error, "合同变更审批失败"));
    }
  };
  const openChanges = async (r: Contract) => {
    try {
      const { data } = await api.get(`/contracts/${r.id}/changes`);
      setChanges(data.items);
      setChangeHistory(r);
    } catch {
      message.error("变更记录加载失败");
    }
  };
  const openContractEvent = (contract: Contract) => {
    eventForm.resetFields();
    setEventTarget(contract);
  };
  const createContractEvent = async () => {
    if (!eventTarget || !contractEventSubmitGate.current.tryEnter()) return;
    setEventSaving(true);
    try {
      const values = await eventForm.validateFields();
      const eventRequest = buildContractEventsRequest(eventTarget, { page: 1, pageSize: 15 });
      if (!eventRequest.path) throw new Error("合同事项缺少合同标识");
      const response = await api.post(eventRequest.path, { content: values.content });
      const feedback = normalizeContractActionResponse(response, "合同事项记录失败");
      if (!feedback.ok) throw new Error(feedback.message);
      message.success("合同事项已记录");
      setEventTarget(null);
      eventForm.resetFields();
      if (viewing?.id === eventTarget.id) await openViewing(eventTarget);
    } catch (error: any) {
      message.error(extractContractErrorMessage(error, "合同事项记录失败"));
    } finally {
      contractEventSubmitGate.current.leave();
      setEventSaving(false);
    }
  };
  const revokeDraft = (contract: Contract) => {
    Modal.confirm({
      title: "撤销合同草稿",
      content: "将删除该草稿及其附件、事项记录，且无法恢复。仅未提交、未产生后续业务的草稿可以撤销。",
      okText: "确认撤销",
      okButtonProps: { danger: true },
      cancelText: "保留草稿",
      onOk: async () => {
        try {
          const response = await api.delete(`/contracts/${contract.id}/draft`);
          const feedback = normalizeContractActionResponse(response, "合同草稿撤销失败");
          if (!feedback.ok) throw new Error(feedback.message);
          localStorage.removeItem(WIZARD_STORAGE_KEY);
          setContractFile(null);
          setSelectedAttachmentKeys([]);
          setAttachments([]);
          sealForm.resetFields();
          setLinkedCustomerContext(null);
          if (wizardDraft?.id === contract.id) startCreate();
          if (viewing?.id === contract.id) closeViewing();
          setEventTarget((current) => current?.id === contract.id ? null : current);
          message.success("合同草稿已撤销，附件和事项记录已一并清理");
          await load();
        } catch (error: any) {
          message.error(extractContractErrorMessage(error, "合同草稿撤销失败"));
          throw error;
        }
      },
    });
  };
  const deleteRecycledContract = (contract: Contract) => {
    Modal.confirm({
      title: "删除合同",
      content: "仅回收站合同可以物理删除；删除会同时清理合同附件和关联记录，且无法恢复。",
      okText: "确认删除",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onOk: async () => {
        try {
          const response = await api.post("/contracts/delete", { contract_ids: [contract.id] });
          const feedback = normalizeContractActionResponse(response, "合同删除失败");
          if (!feedback.ok) throw new Error(feedback.message);
          if (viewing?.id === contract.id) closeViewing();
          setSelectedAttachmentKeys([]);
          message.success("合同已删除");
          await load();
        } catch (error: any) {
          message.error(extractContractErrorMessage(error, "合同删除失败"));
          throw error;
        }
      },
    });
  };
  const archive = async (r: Contract) => {
    try {
      const response = await api.post(`/contracts/${r.id}/archive`);
      const feedback = normalizeContractActionResponse(response, "合同归档失败");
      if (!feedback.ok) throw new Error(feedback.message);
      message.success("合同已归档");
      setSelectedRowKeys([]);
      load();
    } catch (error: any) {
      message.error(extractContractErrorMessage(error, "合同归档失败"));
    }
  };
  const openInvestigation = async (r: Contract) => {
    investigationForm.resetFields();
    try {
      const { data: supervisor } = await api.get("/investigations/assignment-supervisor");
      investigationForm.setFieldsValue({
        title: `${r.title}调查任务`,
        owner: supervisor.username,
        authorized_from: dayjs(),
        authorized_to: dayjs().add(30, "day"),
        right_type: "商标",
        customer_review: false,
        region: "全国",
        authorization_scope: "",
        description: `来源合同 ${r.serial_no}`,
      });
      setInvestigating(r);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "调查主管配置加载失败");
    }
  };
  const createInvestigation = async () => {
    if (!investigating) return;
    const values = await investigationForm.validateFields();
    try {
      const { data } = await api.post(`/contracts/${investigating.id}/investigation`, {
        ...values,
        authorized_from: formatRequiredDate(values.authorized_from, "授权开始日期"),
        authorized_to: formatRequiredDate(values.authorized_to, "授权结束日期"),
      });
      if (contractFile) {
        const attachment = new FormData();
        attachment.append("file", contractFile);
        attachment.append("record_id", String(data.id));
        attachment.append("category", "调查任务资料");
        await api.post("/attachments", attachment);
        setContractFile(null);
      }
      message.success(`调查任务 ${data.serial_no} 已创建`);
      setInvestigating(null);
      investigationForm.resetFields();
      setSelectedRowKeys([]);
      onNavigate?.("investigation-task-published");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "调查任务创建失败");
    }
  };
  const openContractPayment = async (contract: Contract) => {
    paymentForm.resetFields();
    setPaymentTarget(contract);
    setPaymentCandidates([]);
    setPaymentTypes([]);
    setSelectedPaymentObjectKeys([]);
    setPaymentAmounts({});
    try {
      const { data } = await api.get(`/contracts/${contract.id}/payment-candidates`);
      const types = data.payment_types || [];
      setPaymentCandidates(data.items || []);
      setPaymentTypes(types);
      if (types.length) paymentForm.setFieldsValue({ payment_type: types[0].value, payee: types[0].payee, account: types[0].account, application_date: dayjs(), remark: "" });
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "合同付款候选加载失败");
    }
  };
  const createContractPayment = async () => {
    if (!paymentTarget || !contractMutationGates.current.payment.tryEnter()) return;
    setPaymentSaving(true);
    try {
      const values = await paymentForm.validateFields();
      const lines = selectedPaymentObjectKeys.map((key) => ({ contract_object_id: Number(key), amount: Number(paymentAmounts[Number(key)] || 0) }));
      if (!lines.length) { message.error("请至少选择一条合同标的"); return; }
      if (lines.some((line) => !line.amount || line.amount <= 0)) { message.error("请选择合同标的并填写本次支付金额"); return; }
      const exceeding = lines.find((line) => line.amount > Number(paymentCandidates.find((item) => item.contract_object_id === line.contract_object_id)?.remaining_amount || 0) + 0.0001);
      if (exceeding) { message.error("本次支付金额不能超过待付余额"); return; }
      const response = await api.post(`/contracts/${paymentTarget.id}/payment-applications`, {
        ...values,
        application_date: formatRequiredDate(values.application_date, "申请日期"),
        lines,
      });
      const feedback = normalizeContractActionResponse(response, "合同付款申请创建失败");
      if (!feedback.ok) throw new Error(feedback.message);
      const { data } = response;
      message.success(`合同付款申请 ${data.serial_no} 已提交审批`);
      if (viewing?.id === paymentTarget.id) await openViewing(paymentTarget);
      setPaymentTarget(null);
      paymentForm.resetFields();
      setPaymentCandidates([]);
      setPaymentTypes([]);
      setSelectedPaymentObjectKeys([]);
      setPaymentAmounts({});
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(extractContractErrorMessage(error, "合同付款申请创建失败"));
    } finally {
      contractMutationGates.current.payment.leave();
      setPaymentSaving(false);
    }
  };
  const openContractInvoice = (contract: Contract) => {
    const invoiceDue = Number(contract.data.invoice_should || 0) - Number(contract.data.invoice_opened || 0);
    invoiceForm.resetFields();
    invoiceForm.setFieldsValue({
      amount: invoiceDue > 0 ? invoiceDue : contract.data.amount,
      invoice_title: contract.customer,
      invoice_type: "增值税普通发票",
      invoice_content: "法律服务费",
      delivery_method: "电子发票",
    });
    setInvoiceTarget(contract);
  };
  const createContractInvoice = async () => {
    if (!invoiceTarget || !contractMutationGates.current.invoice.tryEnter()) return;
    setInvoiceSaving(true);
    try {
      const values = await invoiceForm.validateFields();
      const response = await api.post("/finance/invoices", {
        ...values,
        customer: invoiceTarget.customer,
        case_no: invoiceTarget.data.case_no || "",
        contract_record_id: invoiceTarget.id,
        remark: `来源合同 ${invoiceTarget.serial_no}${values.remark ? `；${values.remark}` : ""}`,
      });
      const feedback = normalizeContractActionResponse(response, "合同开票申请创建失败");
      if (!feedback.ok) throw new Error(feedback.message);
      const { data } = response;
      message.success(`发票申请 ${data.serial_no} 已创建并关联合同`);
      if (viewing?.id === invoiceTarget.id) await openViewing(invoiceTarget);
      setInvoiceTarget(null);
      invoiceForm.resetFields();
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(extractContractErrorMessage(error, "合同开票申请创建失败"));
    } finally {
      contractMutationGates.current.invoice.leave();
      setInvoiceSaving(false);
    }
  };
  const startSelectedSeal = async (contract: Contract) => {
    if (!CONTRACT_SEAL_READY_STATUSES.includes(contract.status)) {
      message.warning("当前合同状态不支持申请用印");
      return;
    }
    try {
      const current = await loadWizardContext(contract.id);
      setWizardStep(3);
      sealForm.setFieldsValue({
        copies: 1,
        use_date: dayjs().add(1, "day"),
        delivery_method: "现场用印",
        document_names: "",
        purpose: `${current.title}合同用印`,
        submit: false,
      });
      setOpen(true);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "合同用印上下文加载失败");
    }
  };
  const startCaseFromContract = (contract: Contract) => {
    sessionStorage.setItem("sunhold:case-contract-context", JSON.stringify({
      id: contract.id,
      serial_no: contract.serial_no,
      title: contract.title,
      customer: contract.customer,
      at: Date.now(),
    }));
    onNavigate?.("case-new");
  };
  const exportCsv = async () => {
    try {
      const filters = {
        title: query.title || undefined,
        serial_no: query.serial_no || undefined,
        type: query.type || undefined,
        customer: query.customer || undefined,
        case_no: query.case_no || undefined,
        fee_type: query.fee_type || undefined,
        contract_body: query.contract_body || undefined,
        source_person: query.source_person || undefined,
        signed_at_start: query.signed_at?.[0]?.format("YYYY-MM-DD"),
        signed_at_end: query.signed_at?.[1]?.format("YYYY-MM-DD"),
      };
      const res = await api.get("/records/export", {
        params: { module: "contract", ...filters },
        responseType: "blob",
      });
      const url = URL.createObjectURL(res.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = "合同资料.csv";
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      message.error("导出失败");
    }
  };
  const exportExcel = async () => {
    try {
      const filters = {
        title: query.title || undefined,
        serial_no: query.serial_no || undefined,
        type: query.type || undefined,
        customer: query.customer || undefined,
        case_no: query.case_no || undefined,
        fee_type: query.fee_type || undefined,
        contract_body: query.contract_body || undefined,
        source_person: query.source_person || undefined,
        signed_at_start: query.signed_at?.[0]?.format("YYYY-MM-DD"),
        signed_at_end: query.signed_at?.[1]?.format("YYYY-MM-DD"),
      };
      const res = await api.get("/records/export-excel", {
        params: { module: "contract", ...filters },
        responseType: "blob",
      });
      const url = URL.createObjectURL(res.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = "合同资料.xls";
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      message.error("导出失败");
    }
  };
  const exportContractDetailExcel = async (contract: Contract) => {
    try {
      const res = await api.get("/records/export-excel", {
        params: {
          module: "contract",
          serial_no: contract.serial_no || undefined,
          title: contract.serial_no ? undefined : contract.title,
        },
        responseType: "blob",
      });
      const url = URL.createObjectURL(res.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = (contract.serial_no || contract.title || "合同详情") + ".xls";
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      message.error("导出失败");
    }
  };
  const needSelected = (action: () => void) =>
    selected ? action() : message.warning("请先选择一份合同");
  const selected = rows.find((row) => row.id === Number(selectedRowKeys[0]));
  const selectedActionPolicy = contractListActionPolicy(selected?.status);
  const selectedSecondaryActionPolicy = contractSecondaryActionPolicy(selected?.status);
  const amount = (value?: number) => Number(value || 0).toFixed(2);
  const moneyKeys = [
    "official_paid",
    "official_received",
    "official_unreceived",
    "official_loss",
    "agency_total",
    "agency_received",
    "agency_due",
    "other_total",
    "other_paid",
    "other_due",
    "invoice_opened",
    "invoice_should",
    "invoice_excess",
  ] as const;
  const totals = Object.fromEntries(
    moneyKeys.map((key) => [
      key,
      rows.reduce((sum, row) => sum + Number(row.data[key] || 0), 0),
    ]),
  ) as Record<(typeof moneyKeys)[number], number>;
  const textCell = (value: string) => value;
  const moneyColumn = (title: string, key: (typeof moneyKeys)[number]) => ({
    title: (
      <span>
        {title.split("|")[0]}
        <br />
        {title.split("|")[1] || ""}
      </span>
    ),
    key,
    width: 76,
    align: "right" as const,
    render: (_: unknown, r: Contract) => String(r.data[key] ?? 0),
  });
  const columns = [
    {
      title: "合同号",
      dataIndex: "serial_no",
      width: 160,
      ellipsis: true,
      render: (v: string, r: Contract) => (
          <Button
            type="link"
            className="contract-cell-link"
            title={v}
          onClick={() => void openViewing(r)}
          >
            {v}
          </Button>
        ),
    },
    {
      title: "合同名称",
      dataIndex: "title",
      width: 220,
      ellipsis: true,
      render: (value: string) => <span className="contract-cell-text" title={value}>{value}</span>,
    },
    {
      title: "合同主体",
      key: "body",
      width: 74,
      render: (_: unknown, r: Contract) => r.data.contract_body || "律所",
    },
    { title: "合同状态", dataIndex: "status", width: 74, render: textCell },
    {
      title: "案源人",
      key: "source",
      width: 74,
      render: (_: unknown, r: Contract) => personName((r.data as any).source_person_display_name || r.data.source_person || (r as any).owner_display_name || r.owner),
    },
    moneyColumn("官费|支付金额", "official_paid"),
    moneyColumn("官费|到账金额", "official_received"),
    moneyColumn("官费|未到金额", "official_unreceived"),
    moneyColumn("官费|亏损金额", "official_loss"),
    moneyColumn("代理费|总金额", "agency_total"),
    moneyColumn("代理费|到账金额", "agency_received"),
    moneyColumn("代理费|待收金额", "agency_due"),
    moneyColumn("其他金额", "other_total"),
    moneyColumn("其他金额|已支付", "other_paid"),
    moneyColumn("其他金额|待支付", "other_due"),
    moneyColumn("发票|已开金额", "invoice_opened"),
    moneyColumn("发票|应开金额", "invoice_should"),
    moneyColumn("发票|高开金额", "invoice_excess"),
    {
      title: "操作",
      key: "operations",
      width: 150,
      fixed: "right" as const,
      render: (_: unknown, r: Contract) => (
        <Space size={0}>
          <Button type="link" onClick={() => openContractAttachments(r)}>合同附件</Button>
          <Button type="link" onClick={() => openContractApprovalInfo(r)}>审批信息</Button>
          <Button type="link" onClick={() => openContractRelatedCaseFromList(r)}>关联案件</Button>
          {canOpenSubmitWizard(r) && <Button type="link" onClick={() => void openSubmitWizardFromList(r)}>重新上传</Button>}
          {canOpenSubmitWizard(r) && <Button type="link" onClick={() => void openSubmitWizardFromList(r)}>提交审批</Button>}
        </Space>
      ),
    },
  ];
  const auditColumns = [
    columns[0],
    columns[1],
    { title: "合同状态", dataIndex: "status", width: 88, render: textCell },
    {
      title: "合同总金额",
      key: "amount",
      width: 105,
      align: "right" as const,
      render: (_: unknown, r: Contract) => amount(r.data.amount),
    },
    moneyColumn("回款累计", "agency_received"),
    moneyColumn("应收代理费", "agency_due"),
    moneyColumn("未到账垫付款", "official_unreceived"),
    {
      title: "案源人",
      key: "source",
      width: 90,
      render: (_: unknown, r: Contract) => personName((r.data as any).source_person_display_name || r.data.source_person || (r as any).owner_display_name || r.owner),
    },
    {
      title: "客户管理人",
      key: "customerManager",
      width: 100,
      render: (_: unknown, r: Contract) => peopleNames((r.data as any).customer_manager_display_names || r.data.customer_manager || (r.data as any).customer_managers),
    },
    {
      title: "签订日期",
      key: "signedAt",
      width: 105,
      render: (_: unknown, r: Contract) => r.data.signed_at || "—",
    },
    {
      title: "客户编号",
      key: "customerNo",
      width: 105,
      render: (_: unknown, r: Contract) =>
        r.data.customer_no ? <Button type="link" className="contract-cell-link" onClick={() => openRelatedCustomer(r)}>{r.data.customer_no}</Button> : "—",
    },
    {
      title: "客户名称",
      dataIndex: "customer",
      width: 180,
      ellipsis: true,
      render: (value: string, r: Contract) => value ? <Button type="link" className="contract-cell-link" onClick={() => openRelatedCustomer(r)}>{value}</Button> : "—",
    },
  ];
  const isAuditView = initialView === "contract-audit" || initialView.startsWith("contract-audit-");
  const auditActionPolicy = canAccessContractView(initialView, profile)
    ? contractAuditActionPolicy(initialView)
    : { canReview: false, canReviewChange: false, canExport: false };
  const stepItems = steps.map((s) => ({
    title: `第${s.step_order}级：${personName(s.approver_display_name || s.approver)}`,
    description: (
      <>
        <Tag
          color={
            s.status === "已通过"
              ? "green"
              : s.status === "已拒绝"
                ? "red"
                : s.status === "待审批"
                  ? "orange"
                  : "default"
          }
        >
          {s.status}
        </Tag>
        {s.acted_at && (
          <span>{new Date(s.acted_at).toLocaleString("zh-CN")}</span>
        )}
        {s.comment && <p>{s.comment}</p>}
      </>
    ),
    status: (s.status === "已通过"
      ? "finish"
      : s.status === "待审批"
        ? "process"
        : s.status === "已拒绝"
          ? "error"
          : "wait") as "finish" | "process" | "error" | "wait",
  }));
  const currentApproval = reviewing
    ? (reviewCurrentStep || steps.find((step) => step.status === "待审批"))
    : steps.find((step) => step.status === "待审批");
  const canActOnCurrentApproval = Boolean(currentApproval && canActOnContractApproval("审批中", currentApproval.approver, profile.username, profile.role));
  const contractObjectPolicy = contractObjectActionPolicy(viewing?.status);
  const detailSecondaryActionPolicy = contractSecondaryActionPolicy(viewing?.status);
  const presentedReceipts = detailReceipts.map((row) => {
    const item = normalizeIncomingPaymentForContract(row, viewing || {});
    if (!item) return null;
    return { ...row, receipt_no: item.sequenceNo, received_date: item.receivedDate, bank_reference: item.bankReference, amount: item.amount, official_amount: item.officialAmount, agency_amount: item.agencyAmount, other_amount: item.otherAmount, payment_method: item.paymentMethod, claimant: item.claimant };
  }).filter(Boolean);
  const presentedInvoices = detailInvoices.map((row) => {
    const item = normalizeInvoiceObject(row);
    return { ...row, serial_no: item.applicationNo, status: item.status, description: item.remark, data: { ...row.data, invoice_no: item.invoiceNo, invoice_date: item.invoiceDate, amount: item.amount, official_amount: item.officialAmount, agency_amount: item.agencyAmount, other_amount: item.otherAmount, __lineThrough: item.lineThrough } };
  });
  const presentedPayments = detailPayments.map((row) => {
    const item = normalizePaidObject(row);
    return { ...row, serial_no: item.applicationNo, data: { ...row.data, applicant: item.applicant, pending_amount: item.pendingAmount, payment_date: item.paymentDate, payment_reference: item.packageNo, amount: item.paidAmount, payment_type: item.paymentType, official_amount: item.officialAmount, other_amount: item.otherAmount, __lineThrough: item.lineThrough } };
  });
  const viewingHasEventEndpoint = Boolean(viewing && buildContractEventsRequest(viewing, { page: contractEventPage, pageSize: contractEventPageSize, keyword: contractEventKeyword }).path);
  const objectPageData = paginateContractObjectRows(contractObjects, objectPage, objectPageSize);
  const approvalOptions = buildChinesePersonOptions(directory, (user: DirectoryUser) => Boolean(user.can_approve_contract));
  const openApproverSettings = async () => {
    if (profile.role !== "admin") return;
    setApproverSettingsOpen(true);
    setApproverSettingsLoading(true);
    try {
      const response = await api.get("/contracts/approver-settings");
      const items = (response.data.items || []) as ApproverSetting[];
      setApproverSettings(items);
      const selected = items.filter((item) => item.selected).map((item) => item.username);
      const target = approverSettingsTargetUsername && items.some((item) => item.username === approverSettingsTargetUsername)
        ? [approverSettingsTargetUsername, ...selected.filter((username) => username !== approverSettingsTargetUsername)]
        : selected;
      setSelectedApproverUsernames(target);
    } catch (error: any) {
      setApproverSettingsOpen(false);
      message.error(error?.response?.data?.detail || "合同审批人配置加载失败");
    } finally {
      setApproverSettingsLoading(false);
    }
  };
  const saveApproverSettings = async () => {
    setApproverSettingsSaving(true);
    try {
      const response = await api.put("/contracts/approver-settings", { usernames: selectedApproverUsernames });
      const feedback = normalizeContractActionResponse(response, "合同审批人设置保存失败");
      if (!feedback.ok) throw new Error(feedback.message);
      const directoryResponse = await api.get("/users/directory");
      setDirectory((directoryResponse.data.items || []).filter((item: DirectoryUser) => item.is_active !== false));
      setApproverSettingsOpen(false);
      message.success("合同审批人设置已保存");
    } catch (error: any) {
      message.error(extractContractErrorMessage(error, "合同审批人设置保存失败"));
    } finally {
      setApproverSettingsSaving(false);
    }
  };
  const contractApproverLabel = (
    <Space size={4}>
      <span>合同审批人</span>
    </Space>
  );
  const openRelatedCustomer = async (contract: Contract) => {
    const source = { id: Number(contract.data.customer_id) || undefined, serial_no: contract.data.customer_no, title: contract.customer };
    if (!source.id && !source.serial_no && !source.title) {
      message.warning("当前合同未关联客户");
      return;
    }
    const customer = await resolveCustomerDetailTarget(source);
    if (!customer) {
      message.warning("未找到关联客户或当前账号无权查看");
      return;
    }
    rememberCustomerDetailTarget(customer);
    onNavigate?.("customer-company");
  };
  const openRelatedCase = async (caseNo: unknown) => {
    const serialNo = String(caseNo || "").trim();
    if (!serialNo || serialNo === "—") {
      message.warning("当前合同未关联案件");
      return;
    }
    try {
      const record = await resolveDetailRelation("case", { serial_no: serialNo });
      if (!record) {
        message.warning("未找到关联案件或当前账号无权查看");
        return;
      }
      rememberCaseDetailTarget({ id: record.id, serial_no: record.serial_no });
      onNavigate?.("case-company");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "关联案件加载失败");
    }
  };
  const openRelatedPayment = (payment: Contract) => {
    const target = buildContractPaymentNavigation({
      pathname: window.location.pathname,
      hash: window.location.hash,
      payment,
      contract: viewing || {},
    });
    if (!target.ok) {
      message.warning(target.message);
      return;
    }
    window.history.pushState(null, "", target.url);
    onNavigate?.(target.page);
  };
  const updateListPagination = (current: number, pageSize: number) => {
    setListPagination(saveContractListPagination(sessionStorage, initialView, { current, pageSize }));
  };
  const applyQuery = (values: Record<string, any>) => {
    const normalized = normalizeContractQuery(values);
    customerRelationQueryRef.current = null;
    customerRelationQueryViewRef.current = null;
    saveContractListQuery(sessionStorage, initialView, normalized);
    setQuery(normalized);
    updateListPagination(1, listPagination.pageSize);
    void load(normalized);
  };
  const uniqueCustomers = Array.from(new Map(customers.map((customer) => [customer.title.normalize("NFKC").trim().toLocaleLowerCase(), customer])).values());
  const customerOptions = uniqueCustomers.map((customer) => ({
    value: customer.id,
    label: customer.title,
  }));
  if (linkedCustomerContext && !customerOptions.some((option) => option.value === linkedCustomerContext.id)) {
    customerOptions.unshift({ value: linkedCustomerContext.id, label: linkedCustomerContext.name });
  }
  const historyItems = history.map((event) => ({
    color: event.to_status === "已拒绝" ? "red" : event.action.includes("创建") ? "blue" : "green",
    children: (
      <div className="contract-history-item">
        <b>{event.action}</b>
        {event.from_status && event.from_status !== event.to_status && <Tag>{event.from_status} → {event.to_status}</Tag>}
        <small>{personName(event.operator)} · {dayjs(event.created_at).format("YYYY-MM-DD HH:mm")}</small>
        {event.comment && <p>{event.comment}</p>}
      </div>
    ),
  }));
  return (
    <>
      {initialView !== "contract-new" && !isContractDetailView && <Card className="panel contract-original-panel" title="合同查询">
        <Form
          form={queryForm}
          className="contract-query"
          onFinish={applyQuery}
        >
          <Form.Item label="合同名称" name="title"><Input placeholder="合同名称" /></Form.Item>
          <Form.Item label="合同编号" name="serial_no"><Input placeholder="合同编号" /></Form.Item>
          <Form.Item label="合同类型" name="type"><Select allowClear placeholder="请选择" options={["法律顾问合同","争议解决合同","框架合作合同","非诉项目合同","其他"].map(value=>({value,label:value}))} /></Form.Item>
          <Form.Item label="客户名称" name="customer"><Input placeholder="客户名称" /></Form.Item>
          <Form.Item label={isAuditView ? "案号" : "案件编号"} name="case_no"><Input placeholder="案号" /></Form.Item>
          <Form.Item label="收费类型" name="fee_type"><Select allowClear placeholder="请选择" options={["固定收费","固定+后期","免费代理","法律援助","计时收费","全风险代理"].map(value=>({value,label:value}))} /></Form.Item>
          <Form.Item label="合同日期" name="signed_at"><DatePicker.RangePicker /></Form.Item>
          {initialView === "contract-mine" ? (
            <Form.Item label="案源人"><Input disabled value={personName(profile.display_name || profile.username)} /></Form.Item>
          ) : (
            <Form.Item label="案源人" name="source_person"><Input placeholder="案源人" /></Form.Item>
          )}
          <Form.Item label="合同主体" name="contract_body"><Select allowClear placeholder="请选择" options={["律所","平台"].map(value=>({value,label:value}))} /></Form.Item>
          <Form.Item className="contract-query-submit"><Button type="primary" htmlType="submit">查询</Button></Form.Item>
        </Form>
        <Table
          className="contract-original-table"
          rowKey="id"
          size="small"
          loading={loading}
          columns={isAuditView ? auditColumns : columns}
          dataSource={rows}
          rowSelection={{
            selectedRowKeys,
            onChange: (keys) => {
              setSelectedRowKeys(keys.length ? [keys[keys.length - 1]] : []);
              setChanging(null);
            },
          }}
          tableLayout="fixed"
          scroll={{ x: isAuditView ? 1450 : 1480 }}
          pagination={{current:listPagination.current,pageSize:listPagination.pageSize,showSizeChanger:true,pageSizeOptions:[10,15,20,50,100,200],showQuickJumper:{goButton:<Button size="small">GO</Button>},showTotal:()=>`共有${rows.length}条`,onChange:updateListPagination}}
          summary={isAuditView ? undefined : () => <Table.Summary><Table.Summary.Row className="contract-total-row"><Table.Summary.Cell index={0} colSpan={6}></Table.Summary.Cell>{moneyKeys.map((key,index)=><Table.Summary.Cell key={key} index={index+6} align="right">{amount(totals[key])}</Table.Summary.Cell>)}</Table.Summary.Row></Table.Summary>}
        />
        {!isAuditView && <div className="contract-bottom-actions"><Space size={4} wrap>
          <RecordImportButton module="contract" onImported={load} /><Button onClick={exportExcel}>导出Excel</Button><Button onClick={exportCsv}>导出CSV</Button>
          <Button onClick={()=>needSelected(()=>void openViewing(selected!))}>合同查看</Button>
          <Button danger disabled={!selected || selected.status !== "草稿"} onClick={()=>needSelected(()=>revokeDraft(selected!))}>撤销草稿</Button>
          <Button danger disabled={!selected || selected.status !== "已回收"} onClick={()=>needSelected(()=>deleteRecycledContract(selected!))}>删除合同</Button>
          <Button disabled={!selectedSecondaryActionPolicy.canEdit} onClick={()=>needSelected(()=>openChange(selected!))}>合同变更</Button>
          <Button onClick={()=>needSelected(()=>void startSelectedSeal(selected!))}>合同用印</Button>
          <Button disabled={!selectedActionPolicy.canPayment} onClick={()=>needSelected(()=>void openContractPayment(selected!))}>合同付款</Button>
          <Button disabled={!selectedActionPolicy.canInvoice} onClick={()=>needSelected(()=>openContractInvoice(selected!))}>合同开票</Button>
          <Button disabled={!selectedActionPolicy.canCreateCase} onClick={()=>needSelected(()=>startCaseFromContract(selected!))}>新建案件</Button>
          <Button disabled={!selectedSecondaryActionPolicy.canInvestigation} onClick={()=>needSelected(()=>void openInvestigation(selected!))}>新建调查任务</Button>
          <Button disabled={!selectedSecondaryActionPolicy.canArchive} onClick={()=>needSelected(()=>archive(selected!))}>合同归档</Button>
        </Space></div>}
        {isAuditView && (!["contract-audit-pending", "contract-audit-refused", "contract-audit-approved"].includes(initialView) || rows.length > 0) && <div className="contract-bottom-actions"><Space><Button onClick={exportExcel}>导出Excel</Button><Button onClick={exportCsv}>导出CSV</Button>{auditActionPolicy.canReview && <Button type="primary" onClick={()=>needSelected(()=>{if(selected?.status!=="审批中")return message.warning("所选合同不在待审批状态");void openReview(selected!)})}>合同审批</Button>}{auditActionPolicy.canReviewChange && <><Button onClick={()=>needSelected(()=>{if(selected?.data.pending_change?.status!=="待审批")return message.warning("所选合同没有待审批变更");void reviewChange(selected!,true)})}>通过合同变更</Button><Button danger onClick={()=>needSelected(()=>{if(selected?.data.pending_change?.status!=="待审批")return message.warning("所选合同没有待审批变更");void reviewChange(selected!,false)})}>驳回合同变更</Button></>}</Space></div>}
      </Card>}
      {initialView === "contract-new" && (
        <Card className="panel contract-create-page" title="新建合同">
          <div className="contract-page-steps">
            {CONTRACT_CREATE_STEP_TITLES.map((title, index) => (
              <div key={title} className={wizardStep === index ? "active" : wizardStep > index ? "done" : ""}>{index + 1}. {title}</div>
            ))}
          </div>
          {wizardStep === 0 && (
            <Form form={form} layout="horizontal" className="contract-page-form">
              <Form.Item label="客户" required>
                <Space.Compact style={{ width: "100%" }}>
                  <Form.Item name="customer_id" noStyle rules={[{ required: true, message: "请选择客户" }]}>
                    <Select style={{ flex: 1 }} showSearch optionFilterProp="label" placeholder="输入客户名称关键字后选择" options={customerOptions} notFoundContent="没有匹配客户，请先在客户管理中新建客户" onChange={() => setLinkedCustomerContext(null)} />
                  </Form.Item>
                  <Button onClick={() => openContractCustomerCreation(onNavigate)}>新建客户</Button>
                </Space.Compact>
              </Form.Item>
              <Form.Item label="合同主体" name="contract_body" rules={[{ required: true }]}><Select options={["律所", "平台"].map((v) => ({ value: v, label: v }))} /></Form.Item>
              <Form.Item label="合同类别" name="type" rules={[{ required: true, message: "请选择合同类别" }]}><Select allowClear showSearch optionFilterProp="label" placeholder="请选择合同类别" options={CONTRACT_TYPE_OPTIONS} /></Form.Item>
              <Form.Item label="收费模式" name="fee_type" rules={[{ required: true }]}><Select options={CONTRACT_FEE_MODE_OPTIONS} /></Form.Item>
              <Form.Item label="合同名称" name="title" rules={[{ required: true }]}><Input placeholder="合同名称" /></Form.Item>
              <Form.Item label="外部合同号（可多个）" name="external_contract_numbers">
                <Select mode="tags" tokenSeparators={[",", "，"]} placeholder="输入客户方合同编号后回车" />
              </Form.Item>
              <Form.Item label="备注" name="description" rules={[{ required: true }]}><Input.TextArea rows={4} placeholder="备注" /></Form.Item>
              <Form.Item label="合同附件" extra="起草阶段可跳过；提交审批前须上传至少一份合同附件">
                <input type="file" accept={CONTRACT_ATTACHMENT_ACCEPT} onChange={(event) => setContractFile(event.target.files?.[0] || null)} />
                <div className="contract-upload-tip">附件支持常用图片、压缩包、Office 文档及 PDF 格式</div>
              </Form.Item>
            </Form>
          )}
          {wizardStep === 1 && (
            <div className="contract-wizard-panel contract-page-stage">
              <Descriptions bordered size="small" column={2} items={wizardDraft ? [
                { key: "no", label: "合同编号", children: wizardDraft.serial_no },
                { key: "status", label: "当前状态", children: <Tag>{wizardDraft.status}</Tag> },
                { key: "name", label: "合同名称", children: wizardDraft.title, span: 2 },
                { key: "customer", label: "客户", children: wizardDraft.customer },
                { key: "type", label: "合同类别", children: wizardDraft.data.type },
              ] : []} />
              <Form form={submitForm} layout="vertical" className="contract-submit-form">
                <Form.Item label="是否同步用印" name="sync_seal" initialValue={false}>
                  <Radio.Group disabled={!(["草稿", "已拒绝"].includes(wizardDraft?.status || ""))} options={[{ value: true, label: "是" }, { value: false, label: "否" }]} />
                </Form.Item>
                <Form.Item label={contractApproverLabel} name="approvers" rules={[{required:true,message:"请选择一名合同审批人"}]}>
                  <Select disabled={!("草稿 已拒绝".split(" ").includes(wizardDraft?.status || ""))} showSearch optionFilterProp="label" options={approvalOptions} placeholder="请选择后台已配置的合同审批人" notFoundContent="没有可用审批人，请由管理员在人事中心为在职员工配置合同审批流程资格" />
                </Form.Item>
                <Form.Item label="提交说明" name="comment"><Input.TextArea disabled={!("草稿 已拒绝".split(" ").includes(wizardDraft?.status || ""))} rows={3} /></Form.Item>
              </Form>
              <p className="contract-draft-tip">合同草稿已经持久化保存。关闭页面后，可在“我的合同”中继续编辑或提交。</p>
            </div>
          )}
          {wizardStep === 2 && (
            <div className="contract-wizard-panel contract-page-stage">
              <Descriptions bordered size="small" column={2} items={wizardDraft ? [
                { key: "no", label: "合同编号", children: wizardDraft.serial_no },
                { key: "status", label: "合同状态", children: <Tag color={colors[wizardDraft.status]}>{wizardDraft.status}</Tag> },
                { key: "name", label: "合同名称", children: wizardDraft.title, span: 2 },
              ] : []} />
              <Steps direction="vertical" size="small" className="contract-approval-flow" items={stepItems} />
              {wizardDraft?.status === "审批中" && currentApproval && (canActOnCurrentApproval ? (
                <Form form={reviewForm} layout="vertical" className="contract-review-form">
                  <div className="contract-current-approval">当前节点：第 {currentApproval.step_order} 级 · {personName(currentApproval.approver_display_name || currentApproval.approver)}</div>
                  <Form.Item label="审批意见" name="comment"><Input.TextArea rows={3} placeholder="填写通过意见；拒绝时必须填写原因" /></Form.Item>
                  <Space><Button danger icon={<CloseOutlined />} onClick={() => approveWizard(false)}>拒绝</Button><Button type="primary" icon={<CheckOutlined />} onClick={() => approveWizard(true)}>通过当前节点</Button></Space>
                </Form>
              ) : <Alert type="info" showIcon title={`合同已进入 ${personName(currentApproval.approver_display_name || currentApproval.approver)} 的待审批列表`} description="请等待指定审批人处理。" />)}
              <Divider titlePlacement="start">合同附件</Divider>
              <div className="contract-attachment-list">{attachments.length ? attachments.map((item) => <Button key={item.id} type="link" onClick={() => downloadAttachment(item)}>{item.original_name}</Button>) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无合同附件" />}</div>
              <Divider titlePlacement="start">状态时间线</Divider>
              {historyItems.length ? <Timeline items={historyItems} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无流程记录" />}
            </div>
          )}
          {wizardStep === 3 && (
            <div className="contract-wizard-panel contract-seal-step contract-page-stage">
              {wizardDraft?.status === "审批中" ? <Alert type="info" showIcon title="合同正在审批中" description="可先提交用印申请；合同审批与用印审批将分别流转。" /> : <div className="contract-wizard-finished"><CheckOutlined /><h3>合同审批已通过</h3><p>合同草稿、审批意见、附件和时间线均已保存；请在用印中心上传真实用印文件后提交审批。</p></div>}
              {wizardDraft?.data.seal_application_id ? (
                <Descriptions bordered size="small" column={2} items={[
                  { key: "contract", label: "合同编号", children: wizardDraft.serial_no },
                  { key: "seal", label: "用印申请编号", children: wizardDraft.data.seal_application_no || `#${wizardDraft.data.seal_application_id}` },
                  { key: "status", label: "衔接状态", children: wizardDraft.data.sync_seal_file_required ? <Tag color="orange">待补用印文件</Tag> : <Tag color="green">已生成真实用印申请</Tag>, span: 2 },
                    ]} />
              ) : (
                <Form form={sealForm} layout="vertical" className="contract-seal-form">
                  <div className="form-grid">
                    <Form.Item label="选择印章" name="seal_asset_id" rules={[{ required: true, message: "请选择印章" }]}><Select placeholder="请选择印章类型" notFoundContent="暂无可用印章，请管理员到用印中心维护" options={sealAssets.map((asset) => ({ value: asset.id, label: `${asset.seal_type}｜${asset.name}（${asset.code}）` }))} /></Form.Item>
                    <Form.Item label="用印份数" name="copies" rules={[{ required: true }]}><InputNumber min={1} max={999} style={{ width: "100%" }} /></Form.Item>
                    <Form.Item label="计划用印日期" name="use_date" rules={[{ required: true }]}><DatePicker style={{ width: "100%" }} /></Form.Item>
                    <Form.Item label="办理方式" name="delivery_method"><Select options={["现场用印", "邮寄用印", "外带用印"].map((value) => ({ value, label: value }))} /></Form.Item>
                    <Form.Item className="span-2" label="文件名称" name="document_names"><Input placeholder="多份文件可用顿号分隔" /></Form.Item>
                    <Form.Item className="span-2" label="用印用途" name="purpose" rules={[{ required: true }]}><Input /></Form.Item>
                    <Form.Item className="span-2" label="申请说明" name="description"><Input.TextArea rows={2} /></Form.Item>
                  </div>
                  <Form.Item name="submit" valuePropName="checked" hidden><Checkbox /></Form.Item>
                </Form>
              )}
              <Divider titlePlacement="start">合同附件</Divider>
              <div className="contract-attachment-list">{attachments.length ? attachments.map((item) => <Button key={item.id} type="link" onClick={() => downloadAttachment(item)}>{item.original_name}</Button>) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无合同附件" />}</div>
              <Divider titlePlacement="start">合同状态时间线</Divider>
              {historyItems.length ? <Timeline items={historyItems} /> : null}
            </div>
          )}
          <div className="contract-page-actions"><Space>
            {wizardStep > 0 && wizardStep < CONTRACT_CREATE_STEP_TITLES.length && (wizardStep !== 1 || ["草稿", "已拒绝"].includes(wizardDraft?.status || "")) && <Button onClick={() => setWizardStep((step) => Math.max(0, step - 1))}>上一步</Button>}
            {wizardStep === 0 && <Button type="primary" loading={savingContract} onClick={save}>下一步</Button>}
            {wizardStep === 1 && wizardDraft?.status === "草稿" && <Button danger onClick={() => revokeDraft(wizardDraft)}>撤销草稿</Button>}
            {wizardStep === 1 && ["草稿", "已拒绝"].includes(wizardDraft?.status || "") && <Button type="primary" loading={submittingWizard} onClick={submitWizard}>提交审批</Button>}
            {wizardStep === 1 && wizardDraft?.status === "审批中" && <Button type="primary" onClick={() => { const route = buildContractDetailRoute(wizardDraft); if (route) onNavigate?.(route); }}>查看合同详情</Button>}
            {wizardStep === 2 && <Button type="primary" onClick={refreshWizard}>刷新审批状态</Button>}
            {wizardStep === 3 && !wizardDraft?.data.seal_application_id && <Button onClick={() => { sealForm.setFieldValue("submit", false); void createSealApplication(); }}>保存用印草稿</Button>}
            {wizardStep === 3 && !wizardDraft?.data.seal_application_id && <Button type="primary" onClick={() => { sealForm.setFieldValue("submit", true); void createSealApplication(); }}>生成用印申请并进入用印中心</Button>}
            {wizardStep === 3 && <Button onClick={() => startCreate()}>开始新建合同</Button>}
            {wizardStep === 3 && wizardDraft?.data.seal_application_id && wizardDraft?.status !== "审批中" && <Button onClick={() => startCreate()}>继续新建合同</Button>}
            {wizardStep === 3 && wizardDraft?.data.seal_application_id && wizardDraft?.status !== "审批中" && <Button type="primary" onClick={() => onNavigate?.("seal-my")}>进入用印中心</Button>}
          </Space></div>
        </Card>
      )}
      <Modal
        open={Boolean(paymentTarget)}
        title={`合同付款：${paymentTarget?.serial_no || ""}`}
        width={980}
        okText="提交合同付款申请"
        cancelText="取消"
        confirmLoading={paymentSaving}
        closable={!paymentSaving}
        onOk={createContractPayment}
        cancelButtonProps={{ disabled: paymentSaving }}
        onCancel={() => { if (paymentSaving) return; setPaymentTarget(null); setSelectedPaymentObjectKeys([]); setPaymentAmounts({}); }}
      >
        <Form form={paymentForm} layout="vertical">
          <div className="form-grid">
            <Form.Item label="付款类型" name="payment_type" rules={[{ required: true, message: "请选择付款类型" }]}><Select options={paymentTypes} onChange={(value) => { const current = paymentTypes.find(item => item.value === value); if (current) paymentForm.setFieldsValue({ payee: current.payee, account: current.account }); }} /></Form.Item>
            <Form.Item label="收款单位" name="payee" rules={[{ required: true, message: "请输入收款单位" }]}><Input /></Form.Item>
            <Form.Item label="收款账号" name="account"><Input /></Form.Item>
            <Form.Item label="申请日期" name="application_date" rules={[{ required: true }]}><DatePicker style={{ width: "100%" }} /></Form.Item>
          </div>
          <Form.Item label="申请说明" name="remark"><Input.TextArea rows={2} /></Form.Item>
        </Form>
        <Alert showIcon type="info" message="按合同标的逐项申请" description="勾选需要付款的合同标的并填写本次支付金额；系统将保留已提交、待付款和已付款金额，阻止重复超额申请。" style={{ marginBottom: 12 }} />
        <Table<ContractPaymentCandidate>
          rowKey="contract_object_id"
          size="small"
          pagination={false}
          locale={{ emptyText: "当前合同没有可付款的合同标的" }}
          dataSource={paymentCandidates}
          rowSelection={{ selectedRowKeys: selectedPaymentObjectKeys, onChange: (keys) => { setSelectedPaymentObjectKeys(keys); setPaymentAmounts((previous) => { const next = { ...previous }; keys.forEach((key) => { const id = Number(key); if (next[id] === undefined) next[id] = Number(paymentCandidates.find(item => item.contract_object_id === id)?.remaining_amount || 0); }); return next; }); } }}
          columns={[
            { title: "案号", dataIndex: "case_no", width: 140 },
            { title: "案件名称", dataIndex: "case_title", ellipsis: true },
            { title: "费用类型", dataIndex: "fee_type", width: 120 },
            { title: "合同金额", dataIndex: "contract_amount", width: 105, render: (value) => Number(value).toFixed(2) },
            { title: "已占用", dataIndex: "reserved_amount", width: 100, render: (value) => Number(value).toFixed(2) },
            { title: "待付余额", dataIndex: "remaining_amount", width: 105, render: (value) => Number(value).toFixed(2) },
            { title: "本次支付", width: 130, render: (_, row) => <InputNumber disabled={!selectedPaymentObjectKeys.includes(row.contract_object_id)} min={0.01} max={row.remaining_amount} precision={2} value={paymentAmounts[row.contract_object_id]} style={{ width: "100%" }} onChange={(value) => setPaymentAmounts(previous => ({ ...previous, [row.contract_object_id]: Number(value || 0) }))} /> },
          ]}
        />
      </Modal>
      <Modal
        open={Boolean(invoiceTarget)}
        title={`合同开票：${invoiceTarget?.serial_no || ""}`}
        okText="创建开票申请"
        cancelText="取消"
        confirmLoading={invoiceSaving}
        closable={!invoiceSaving}
        onOk={createContractInvoice}
        cancelButtonProps={{ disabled: invoiceSaving }}
        onCancel={() => { if (invoiceSaving) return; setInvoiceTarget(null); }}
      >
        <Form form={invoiceForm} layout="vertical">
          <div className="form-grid">
            <Form.Item label="开票金额" name="amount" rules={[{ required: true }]}><InputNumber min={0.01} precision={2} style={{ width: "100%" }} /></Form.Item>
            <Form.Item label="发票抬头" name="invoice_title" rules={[{ required: true }]}><Input /></Form.Item>
            <Form.Item label="纳税人识别号" name="taxpayer_id" rules={[{ required: true }]}><Input /></Form.Item>
            <Form.Item label="发票类型" name="invoice_type" rules={[{ required: true }]}><Select options={["增值税普通发票", "增值税专用发票", "电子普通发票", "电子专用发票"].map(value => ({ value, label: value }))} /></Form.Item>
            <Form.Item label="开票内容" name="invoice_content" rules={[{ required: true }]}><Input /></Form.Item>
            <Form.Item label="交付方式" name="delivery_method"><Select options={["电子发票", "邮寄纸质发票", "现场领取"].map(value => ({ value, label: value }))} /></Form.Item>
            <Form.Item label="接收邮箱" name="email"><Input /></Form.Item>
            <Form.Item label="联系电话" name="recipient_phone"><Input /></Form.Item>
          </div>
          <Form.Item label="邮寄地址" name="delivery_address"><Input /></Form.Item>
          <Form.Item label="备注" name="remark"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
      <Modal
        width={720}
        open={Boolean(investigating)}
        title={`新建调查任务：${investigating?.serial_no || ""}`}
        okText="确认创建"
        cancelText="取消"
        onOk={createInvestigation}
        onCancel={() => setInvestigating(null)}
      >
        <Form form={investigationForm} layout="vertical">
          <Form.Item label="调查任务名称" name="title" rules={[{ required: true, min: 2 }]}>
            <Input />
          </Form.Item>
          <div className="form-grid">
            <Form.Item label="调查主管" name="owner" rules={[{ required: true, message: "请选择调查主管" }]}>
              <Select disabled showSearch optionFilterProp="label" options={directory.map(user=>({value:user.username,label:user.display_name || user.username}))} />
            </Form.Item>
            <Form.Item label="权利类型" name="right_type" rules={[{ required: true }]}>
              <Select options={["商标","专利","著作权","不正当竞争"].map(value=>({value,label:value}))} />
            </Form.Item>
            <Form.Item label="授权开始日期" name="authorized_from" rules={[{ required: true }]}>
              <DatePicker style={{width:"100%"}} />
            </Form.Item>
            <Form.Item label="授权结束日期" name="authorized_to" rules={[{ required: true }]}>
              <DatePicker style={{width:"100%"}} />
            </Form.Item>
          </div>
          <Form.Item label="授权范围" name="region" rules={[{ required: true, message: "请选择授权范围" }]}>
            <Select options={["全国", "区域"].map(value=>({value,label:value}))} />
          </Form.Item>
          {investigationRegion === "区域" && <Form.Item label="授权区域" name="authorization_scope" rules={[{ required: true, message: "请输入授权区域" }]}><Input placeholder="省、市或具体授权区域" /></Form.Item>}
          <Form.Item name="customer_review" valuePropName="checked">
            <Checkbox>调查线索需要客户审核</Checkbox>
          </Form.Item>
          <Form.Item label="调查资料"><input type="file" accept={CONTRACT_ATTACHMENT_ACCEPT} onChange={(event) => setContractFile(event.target.files?.[0] || null)} />{contractFile && <span className="contract-upload-name">{contractFile.name}</span>}</Form.Item>
          <Form.Item label="任务说明" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        width={isContractDetailView ? "100%" : 860}
        open={Boolean(viewing)}
        title={isContractDetailView ? "合同查看" : `合同查看：${viewing?.serial_no || ""}`}
        footer={<Space>{viewing?.status === "草稿" && <Button danger onClick={() => revokeDraft(viewing)}>撤销草稿</Button>}{viewing && <Button disabled={!detailSecondaryActionPolicy.canEdit} onClick={() => openChange(viewing)}>合同变更</Button>}<Button onClick={() => viewing && void exportContractDetailExcel(viewing)}>导出Excel</Button><Button onClick={() => viewing && openContractEvent(viewing)}>新增事项</Button><Button onClick={returnFromDetail}>关闭</Button></Space>}
        onCancel={returnFromDetail}
        getContainer={isContractDetailView ? false : undefined}
        mask={!isContractDetailView}
        rootClassName={isContractDetailView ? "contract-detail-static-root" : undefined}
      >
        {isContractDetailView && viewing ? (
          <div className="contract-detail-workbench">
            <section className="contract-detail-summary">
              <div><span>客户编码：</span><Button type="link" onClick={() => openRelatedCustomer(viewing)}>{viewing.data.customer_no || "—"}</Button></div>
              <div><span>签订日期：</span><b>{viewing.data.signed_at || "—"}</b></div>
              <div><span>客户名称：</span><Button type="link" onClick={() => openRelatedCustomer(viewing)}>{viewing.customer || "—"}</Button></div>
              <div><span>合同编号：</span><b>{viewing.serial_no}</b></div>
              <div><span>客户管理人：</span><b>{peopleNames((viewing.data as any).customer_manager_display_names || viewing.data.customer_manager || (viewing.data as any).customer_managers || viewing.owner)}</b></div>
              <div><span>合同名称：</span><b>{viewing.title || "—"}</b></div>
            </section>
            <section className="contract-detail-finance-summary">
              {[
                ["官费支付金额", viewing.data.official_paid],
                ["官费到账金额", viewing.data.official_received],
                ["官费未到金额", viewing.data.official_unreceived],
                ["官费亏损金额", viewing.data.official_loss],
                ["代理费总金额", viewing.data.agency_total],
                ["代理费到账金额", viewing.data.agency_received],
                ["代理费待收金额", viewing.data.agency_due],
                ["其他金额", viewing.data.other_total],
                ["其他金额已支付", viewing.data.other_paid],
                ["其他金额待支付", viewing.data.other_due],
                ["发票已开金额", viewing.data.invoice_opened],
                ["发票应开金额", viewing.data.invoice_should],
                ["发票高开金额", viewing.data.invoice_excess],
              ].map(([label, value]) => <div key={String(label)}><span>{label}：</span><b>{amount(Number(value || 0))}</b></div>)}
            </section>
            <Tabs
              className="contract-detail-tabs"
              activeKey={detailActiveTab}
              onChange={handleContractDetailTabChange}
              items={[
                {
                  key: "objects",
                  label: "合同标的",
                  children: <>
                    <Space style={{ marginBottom: 8 }}>
                      <Button size="small" type="primary" disabled={!viewing || !contractObjectPolicy.canEdit} onClick={() => { objectForm.resetFields(); setObjectEditing({}); }}>新增标的</Button>
                    </Space>
                    <Table size="small" rowKey="id" scroll={{ x: 1120 }} dataSource={objectPageData.items} locale={{ emptyText: "暂无合同标的" }} pagination={{ current: objectPageData.current, pageSize: objectPageData.pageSize, total: objectPageData.total, showSizeChanger: true, pageSizeOptions: [...CONTRACT_OBJECT_PAGE_SIZES], showQuickJumper: { goButton: <Button size="small">GO</Button> }, onChange: (page, pageSize) => { setObjectPage(page); setObjectPageSize(pageSize); } }} columns={[
                    { title: "序号", width: 64, render: (_: unknown, __: ContractObjectRow, index: number) => index + 1 },
                    { title: "案件类型", dataIndex: "case_type", width: 110 },
                    { title: "案号", dataIndex: "case_no", width: 160, render: (value: string) => value ? <Button type="link" className="contract-cell-link" onClick={() => openRelatedCase(value)}>{value}</Button> : "—" },
                    { title: "案件名称", dataIndex: "case_title", width: 180 },
                    { title: "案件阶段", dataIndex: "case_phase", width: 120 },
                    { title: "费用类型", dataIndex: "fee_type", width: 120 },
                    { title: "费用金额", dataIndex: "amount", width: 110, render: (value: number) => amount(value) },
                    { title: "客户管理人", dataIndex: "customer_manager", width: 120, render: (value: string) => peopleNames(value) },
                    { title: "备注", dataIndex: "remark", width: 180 },
                    { title: "操作", width: 176, fixed: "right", render: (_: unknown, row: ContractObjectRow) => <Space size={0}>
                      {contractObjectHasLogs(row.logs) && <Button type="link" onClick={() => setObjectLogTarget(row)}>日志</Button>}
                      <Button type="link" disabled={!viewing || !contractObjectPolicy.canEdit} onClick={() => { objectForm.setFieldsValue({ case_record_id: row.case_record_id, fee_type: row.fee_type, amount: row.amount, remark: row.remark }); setObjectEditing({ id: row.id }); }}>编辑</Button>
                      <Popconfirm title="确认删除该合同标的？" disabled={!viewing || !contractObjectPolicy.canDelete} onConfirm={() => void deleteContractObject(row.id)}><Button type="link" danger disabled={!viewing || !contractObjectPolicy.canDelete}>删除</Button></Popconfirm>
                    </Space> },
                  ]} />
                  </>,
                },
                {
                  key: "events",
                  label: "事项记录",
                  children: <>
                    <Space wrap style={{ marginBottom: 8 }}>
                      <Input.Search allowClear value={contractEventKeyword} loading={contractEventsLoading} placeholder="搜索事项内容" onChange={(event) => setContractEventKeyword(event.target.value)} onSearch={(value) => { setContractEventKeyword(value.trim()); setContractEventPage(1); if (viewing) void reloadContractEvents(viewing, 1, value.trim(), contractEventPageSize); }} />
                      {contractEventsError && <Button type="link" onClick={() => viewing && void reloadContractEvents(viewing, contractEventPage, contractEventKeyword, contractEventPageSize)}>重试</Button>}
                    </Space>
                    {contractEventsError ? <Alert type="error" showIcon message={contractEventsError} /> : contractEvents.length ? <Timeline items={contractEvents.map((event) => ({ children: <div className="contract-history-item"><b>{event.content}</b><small>{personName(event.operator)} · {dayjs(event.created_at).format("YYYY-MM-DD HH:mm")}</small></div> }))} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={viewing ? <span>暂无事项记录，<Button type="link" onClick={() => viewing && void openContractEvent(viewing)}>新建</Button></span> : "暂无事项记录"} />}
                    {viewingHasEventEndpoint && <Pagination size="small" current={contractEventPage} pageSize={contractEventPageSize} total={contractEventTotal} showSizeChanger pageSizeOptions={CONTRACT_EVENT_PAGE_SIZES.map(String)} showQuickJumper={{ goButton: <Button size="small">GO</Button> }} onChange={(page, pageSize) => { setContractEventPage(page); setContractEventPageSize(pageSize); if (viewing) void reloadContractEvents(viewing, page, contractEventKeyword, pageSize); }} />}
                  </>,
                },
                {
                  key: "workflow",
                  label: "流程记录",
                  children: contractWorkflowEvents.length ? <Timeline items={contractWorkflowEvents.map((event) => ({ children: <div className="contract-history-item"><b>{event.content}</b><small>{personName(event.operator)} · {dayjs(event.created_at).format("YYYY-MM-DD HH:mm")}</small></div> }))} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无流程记录" />,
                },
                {
                  key: "attachments",
                  label: "合同附件",
                  children: <>
                    <Space wrap style={{ marginBottom: 8 }}>
                      <input type="file" accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.png,.jpg,.jpeg,.zip,.rar" disabled={!viewing || ["审批中", "已归档"].includes(viewing.status)} onChange={(event) => setContractFile(event.target.files?.[0] || null)} />
                      <Button onClick={() => void uploadViewingAttachment()} disabled={!contractFile || !viewing || ["审批中", "已归档"].includes(viewing.status)}>上传附件</Button>
                      <Button danger loading={attachmentBatchSaving} disabled={!viewing || !contractAttachmentActionPolicy(viewing.status).canDelete || !selectedAttachmentKeys.length} onClick={() => void batchDeleteViewingAttachments()}>批量删除{selectedAttachmentKeys.length ? `（${selectedAttachmentKeys.length}）` : ""}</Button>
                    </Space>
                    {viewingAttachmentsError ? <Alert type="error" showIcon message={viewingAttachmentsError} action={<Button size="small" onClick={() => viewing && void reloadViewingAttachments(viewing)}>重试</Button>} /> : viewingAttachmentsLoading ? <span>正在加载合同附件…</span> : viewingAttachments.length ? <Table size="small" rowKey="id" pagination={false} dataSource={viewingAttachments} rowSelection={{ selectedRowKeys: selectedAttachmentKeys, onChange: setSelectedAttachmentKeys, getCheckboxProps: () => ({ disabled: !viewing || !contractAttachmentActionPolicy(viewing.status).canDelete }) }} columns={[
                    { title: "序号", width: 64, render: (_: unknown, __: Attachment, index: number) => index + 1 },
                    { title: "文件名称", dataIndex: "original_name" },
                    { title: "分类", dataIndex: "category", width: 160 },
                    { title: "上传人", dataIndex: "uploader", width: 120, render: (_value: string, row: Attachment) => personName(row.uploader_display_name || row.uploader) },
                    { title: "上传日期", dataIndex: "created_at", width: 140, render: (value: string) => value ? dayjs(value).format("YYYY-MM-DD") : "—" },
                    { title: "操作", width: 180, render: (_: unknown, item: Attachment) => <Space size={0}><Button type="link" onClick={() => downloadAttachment(item)}>下载</Button><Button type="link" onClick={() => void previewAttachment(item)}>预览</Button><Popconfirm title="确认删除该合同附件？" disabled={!viewing || ["审批中", "已归档"].includes(viewing.status)} onConfirm={() => void deleteViewingAttachment(item)}><Button type="link" danger disabled={!viewing || ["审批中", "已归档"].includes(viewing.status)}>删除</Button></Popconfirm></Space> },
                  ]} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无合同附件" />}
                  </>,
                },
                {
                  key: "approvals",
                  label: "审批信息",
                  children: <>{detailApprovalsError ? <Alert type="error" showIcon message={detailApprovalsError} action={<Button size="small" onClick={() => viewing && void reloadDetailApprovals(viewing)}>重试</Button>} /> : <Table size="small" rowKey="id" pagination={false} dataSource={detailApprovals} locale={{ emptyText: "暂无审批信息" }} columns={[
                    { title: "审批顺序", dataIndex: "step_order", width: 100 },
                    { title: "审批人", dataIndex: "approver", render: (_value: string, row: Step) => personName(row.approver_display_name || row.approver) },
                    { title: "审批日期", dataIndex: "acted_at", width: 140, render: (value: string) => value ? dayjs(value).format("YYYY-MM-DD") : "—" },
                    { title: "状态", dataIndex: "status", width: 120, render: (value: string) => <Tag>{value || "—"}</Tag> },
                    { title: "审批意见", dataIndex: "comment" },
                  ]} />}</>,
                },
              ]}
            />
            <section className="contract-record-section">
              <h3>回款记录</h3>
              <Table size="small" rowKey="id" pagination={false} scroll={{ x: 1180 }} dataSource={presentedReceipts} locale={{ emptyText: "暂无回款记录" }} columns={[
                { title: "序号", width: 64, render: (_: unknown, __: any, index: number) => index + 1 },
                { title: "回款单号", dataIndex: "receipt_no", width: 150 },
                { title: "回款日期", dataIndex: "received_date", width: 120 },
                { title: "银行单据号", dataIndex: "bank_reference", width: 150 },
                { title: "回款金额", dataIndex: "amount", width: 110, render: (value: number) => amount(value) },
                { title: "官费", width: 100, render: (_: unknown, row: any) => amount(row.official_amount || 0) },
                { title: "代理费", width: 100, render: (_: unknown, row: any) => amount(row.agency_amount || 0) },
                { title: "其他费用", width: 100, render: (_: unknown, row: any) => amount(row.other_amount || 0) },
                { title: "回款方式", dataIndex: "payment_method", width: 120 },
                { title: "回款分配人", dataIndex: "claimant", width: 120 },
              ]} />
            </section>
            <section className="contract-record-section">
              <h3>开票记录</h3>
              <Table size="small" rowKey="id" pagination={false} scroll={{ x: 1120 }} dataSource={presentedInvoices} rowClassName={(row: any) => row.data?.__lineThrough ? "contract-line-through" : ""} locale={{ emptyText: "暂无开票记录" }} columns={[
                { title: "序号", width: 64, render: (_: unknown, __: Contract, index: number) => index + 1 },
                { title: "请票单号", dataIndex: "serial_no", width: 150 },
                { title: "发票号码", width: 150, render: (_: unknown, row: Contract) => (row.data as any).invoice_no || "—" },
                { title: "开票日期", width: 120, render: (_: unknown, row: Contract) => (row.data as any).invoice_date || "—" },
                { title: "开票金额", width: 110, render: (_: unknown, row: Contract) => amount((row.data as any).amount || 0) },
                { title: "官费", width: 100, render: (_: unknown, row: Contract) => amount((row.data as any).official_amount || 0) },
                { title: "代理费", width: 100, render: (_: unknown, row: Contract) => amount((row.data as any).agency_amount || 0) },
                { title: "其他费用", width: 100, render: (_: unknown, row: Contract) => amount((row.data as any).other_amount || 0) },
                { title: "状态", dataIndex: "status", width: 110 },
                { title: "备注", dataIndex: "description", width: 180 },
              ]} />
            </section>
            <section className="contract-record-section">
              <h3>付款记录</h3>
              <Table size="small" rowKey="id" pagination={false} scroll={{ x: 1120 }} dataSource={presentedPayments} rowClassName={(row: any) => row.data?.__lineThrough ? "contract-line-through" : ""} locale={{ emptyText: "暂无付款记录" }} columns={[
                { title: "序号", width: 64, render: (_: unknown, __: Contract, index: number) => index + 1 },
                { title: "申请单号", dataIndex: "serial_no", width: 150, render: (value: string, row: Contract) => value ? <Button type="link" className="contract-cell-link" onClick={() => openRelatedPayment(row)}>{value}</Button> : "—" },
                { title: "申请人", width: 120, render: (_: unknown, row: Contract) => personName((row.data as any).applicant_display_name || (row.data as any).applicant || (row as any).owner_display_name || row.owner) },
                { title: "待付金额", width: 110, render: (_: unknown, row: Contract) => amount((row.data as any).pending_amount || 0) },
                { title: "付款日期", width: 120, render: (_: unknown, row: Contract) => (row.data as any).payment_date || "—" },
                { title: "付款单据", width: 140, render: (_: unknown, row: Contract) => (row.data as any).payment_reference || "—" },
                { title: "付款金额", width: 110, render: (_: unknown, row: Contract) => amount((row.data as any).amount || 0) },
                { title: "付款类型", width: 120, render: (_: unknown, row: Contract) => (row.data as any).payment_type || "—" },
                { title: "付款标的", width: 260, dataIndex: "line_summary", render: (value: string) => value || "—" },
                { title: "官费", width: 100, render: (_: unknown, row: Contract) => amount((row.data as any).official_amount || 0) },
                { title: "其他费用", width: 100, render: (_: unknown, row: Contract) => amount((row.data as any).other_amount || 0) },
              ]} />
            </section>
          </div>
        ) : (
          <>
        <Descriptions
          bordered
          size="small"
          column={2}
          items={viewing ? [
            {key:"serial",label:"合同号",children:viewing.serial_no},
            {key:"status",label:"合同状态",children:viewing.status},
            {key:"title",label:"合同名称",children:viewing.title,span:2},
            {key:"customer",label:"客户名称",children:<Button type="link" className="contract-cell-link" onClick={() => openRelatedCustomer(viewing)}>{viewing.customer || "—"}</Button>},
            {key:"case",label:"关联案号",children:viewing.data.case_no ? <Button type="link" className="contract-cell-link" onClick={() => openRelatedCase(viewing.data.case_no)}>{viewing.data.case_no}</Button> : "—"},
            {key:"body",label:"合同主体",children:viewing.data.contract_body||"律所"},
            {key:"type",label:"合同类型",children:viewing.data.type||"—"},
            {key:"fee",label:"收费类型",children:viewing.data.fee_type||"—"},
            {key:"source",label:"案源人",children:personName((viewing.data as any).source_person_display_name || viewing.data.source_person || (viewing as any).owner_display_name || viewing.owner)},
            {key:"date",label:"合同日期",children:viewing.data.signed_at||"—"},
            {key:"official",label:"官费（支付 / 到账 / 未到）",children:`${amount(viewing.data.official_paid)} / ${amount(viewing.data.official_received)} / ${amount(viewing.data.official_unreceived)}`,span:2},
            {key:"agency",label:"代理费（总额 / 到账 / 待收）",children:`${amount(viewing.data.agency_total)} / ${amount(viewing.data.agency_received)} / ${amount(viewing.data.agency_due)}`,span:2},
            {key:"invoice",label:"发票（已开 / 应开 / 高开）",children:`${amount(viewing.data.invoice_opened)} / ${amount(viewing.data.invoice_should)} / ${amount(viewing.data.invoice_excess)}`,span:2},
            {key:"description",label:"合同说明",children:viewing.description||"—",span:2},
          ] : []}
        />
        <Divider>合同附件</Divider>
        {viewingAttachmentsError ? (
          <Alert type="error" showIcon message={viewingAttachmentsError} action={<Button size="small" onClick={() => viewing && void reloadViewingAttachments(viewing)}>重试</Button>} />
        ) : viewingAttachmentsLoading ? (
          <span>正在加载合同附件…</span>
        ) : viewingAttachments.length ? (
          <Space direction="vertical" size={2}>
            {viewingAttachments.map((item) => (
              <Space key={item.id} size={4}>
                <Button type="link" onClick={() => downloadAttachment(item)}>{item.original_name}</Button>
                <Button type="link" onClick={() => void previewAttachment(item)}>预览</Button>
                <small>{personName(item.uploader_display_name || item.uploader)} · {item.created_at ? dayjs(item.created_at).format("YYYY-MM-DD") : "—"}</small>
              </Space>
            ))}
          </Space>
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无合同附件" />
        )}
        <Divider>事项记录</Divider>
        <Space wrap style={{ marginBottom: 8 }}>
          <Input.Search allowClear value={contractEventKeyword} loading={contractEventsLoading} placeholder="搜索事项内容" onChange={(event) => setContractEventKeyword(event.target.value)} onSearch={(value) => { setContractEventKeyword(value.trim()); setContractEventPage(1); if (viewing) void reloadContractEvents(viewing, 1, value.trim(), contractEventPageSize); }} />
          {contractEventsError && <Button type="link" onClick={() => viewing && void reloadContractEvents(viewing, contractEventPage, contractEventKeyword, contractEventPageSize)}>重试</Button>}
        </Space>
        {contractEventsError ? <Alert type="error" showIcon message={contractEventsError} /> : null}
        {viewingHasEventEndpoint && <Pagination size="small" current={contractEventPage} pageSize={contractEventPageSize} total={contractEventTotal} showSizeChanger pageSizeOptions={CONTRACT_EVENT_PAGE_SIZES.map(String)} showQuickJumper={{ goButton: <Button size="small">GO</Button> }} onChange={(page, pageSize) => { setContractEventPage(page); setContractEventPageSize(pageSize); if (viewing) void reloadContractEvents(viewing, page, contractEventKeyword, pageSize); }} />}
        {contractEvents.length ? (
          <Timeline items={contractEvents.map((event) => ({
            children: <div className="contract-history-item"><b>{event.content}</b><small>{personName(event.operator)} · {dayjs(event.created_at).format("YYYY-MM-DD HH:mm")}</small></div>,
          }))} />
        ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={viewing ? <span>暂无事项记录，<Button type="link" onClick={() => viewing && void openContractEvent(viewing)}>新建</Button></span> : "暂无事项记录"} />}
        <Divider>流程记录</Divider>
        {contractWorkflowEvents.length ? <Timeline items={contractWorkflowEvents.map((event) => ({
          children: <div className="contract-history-item"><b>{event.content}</b><small>{personName(event.operator)} · {dayjs(event.created_at).format("YYYY-MM-DD HH:mm")}</small></div>,
        }))} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无流程记录" />}
        <Divider>合同标的 <Button size="small" type="link" disabled={!viewing || !contractObjectPolicy.canEdit} onClick={()=>{objectForm.resetFields();setObjectEditing({})}}>新增标的</Button></Divider>
        {contractObjects.length ? <Table size="small" rowKey="id" scroll={{x:940}} columns={[
          {title:"案件类型",dataIndex:"case_type",width:100},
          {title:"案号",dataIndex:"case_no",width:155,render:(value:string)=><Button type="link" className="contract-cell-link" onClick={()=>openRelatedCase(value)}>{value}</Button>},
          {title:"案件名称",dataIndex:"case_title",width:170,ellipsis:true},
          {title:"案件阶段",dataIndex:"case_phase",width:110},
          {title:"费用类型",dataIndex:"fee_type",width:110},
          {title:"费用金额",dataIndex:"amount",width:110,render:(value:number)=>amount(value)},
          {title:"客户管理人",dataIndex:"customer_manager",width:120,render:(value:string)=>peopleNames(value)},
          {title:"备注",dataIndex:"remark",width:180,ellipsis:true},
          {title:"操作",width:176,fixed:"right",render:(_:unknown,row:ContractObjectRow)=><Space size={0}>{contractObjectHasLogs(row.logs) && <Button type="link" onClick={()=>setObjectLogTarget(row)}>日志</Button>}{!viewing||!contractObjectPolicy.canEdit?null:<><Button type="link" onClick={()=>{objectForm.setFieldsValue({case_record_id:row.case_record_id,fee_type:row.fee_type,amount:row.amount,remark:row.remark});setObjectEditing({id:row.id})}}>编辑</Button><Popconfirm title="确认删除该合同标的？" disabled={!contractObjectPolicy.canDelete} onConfirm={()=>void deleteContractObject(row.id)}><Button type="link" danger disabled={!contractObjectPolicy.canDelete}>删除</Button></Popconfirm></>}</Space>},
        ]} dataSource={objectPageData.items} pagination={{ current: objectPageData.current, pageSize: objectPageData.pageSize, total: objectPageData.total, showSizeChanger: true, pageSizeOptions: [...CONTRACT_OBJECT_PAGE_SIZES], showQuickJumper: { goButton: <Button size="small">GO</Button> }, onChange: (page, pageSize) => { setObjectPage(page); setObjectPageSize(pageSize); } }} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无合同标的" />}
          </>
        )}
      </Modal>
      <Modal open={Boolean(objectEditing)} title={objectEditing?.id?"修改合同标的":"新增合同标的"} okText="保存" cancelText="取消" onCancel={()=>{setObjectEditing(null);objectForm.resetFields()}} onOk={()=>void saveContractObject()}>
        <Form form={objectForm} layout="vertical"><Form.Item name="case_record_id" label="关联案件" rules={[{required:true,message:"请选择合同客户下的案件"}]}><Select showSearch optionFilterProp="label" options={filterContractCaseOptions(objectCases, viewing?.customer || "").map(item=>({value:item.id,label:`${item.serial_no}｜${item.title}`}))}/></Form.Item><Form.Item name="fee_type" label="费用类型" rules={[{required:true}]}><Input/></Form.Item><Form.Item name="amount" label="费用金额" rules={[{required:true}]}><InputNumber min={0} precision={2} style={{width:"100%"}}/></Form.Item><Form.Item name="remark" label="备注"><Input.TextArea rows={3}/></Form.Item></Form>
      </Modal>
      <Modal open={Boolean(objectLogTarget)} title={objectLogTarget ? `合同标的日志：${objectLogTarget.case_no}｜${objectLogTarget.fee_type}` : "合同标的日志"} footer={null} onCancel={()=>setObjectLogTarget(null)}>
        {objectLogTarget?.logs?.length ? <Timeline items={objectLogTarget.logs.map(log=>({children:<div className="contract-history-item"><b>{log.action}</b><small>{personName(log.operator)} · {dayjs(log.created_at).format("YYYY-MM-DD HH:mm")}</small><small>变更前：{Object.keys(log.before || {}).length ? JSON.stringify(log.before) : "-"}</small><small>变更后：{Object.keys(log.after || {}).length ? JSON.stringify(log.after) : "-"}</small></div>}))} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无合同标的日志" />}
      </Modal>
      <Modal open={Boolean(attachmentPreview)} title={`在线查看：${attachmentPreview?.name || ""}`} footer={<Button onClick={closeAttachmentPreview}>关闭</Button>} onCancel={closeAttachmentPreview} width={attachmentPreview?.kind === "pdf" ? 1000 : 760} destroyOnHidden>
        {attachmentPreview?.kind === "image" && <img src={attachmentPreview.url} alt={attachmentPreview.name} style={{ display: "block", maxWidth: "100%", maxHeight: "72vh", margin: "0 auto" }} />}
        {attachmentPreview?.kind === "pdf" && <iframe title={attachmentPreview.name} src={attachmentPreview.url} style={{ width: "100%", height: "72vh", border: 0 }} />}
        {(attachmentPreview?.kind === "text" || attachmentPreview?.kind === "docx") && <pre style={{ maxHeight: "70vh", overflow: "auto", margin: 0, whiteSpace: "pre-wrap", overflowWrap: "anywhere", fontFamily: "inherit", lineHeight: 1.7 }}>{attachmentPreview.text}</pre>}
      </Modal>
      <Modal
        open={Boolean(eventTarget)}
        title={`新增合同事项：${eventTarget?.serial_no || ""}`}
        okText="保存"
        cancelText="取消"
        confirmLoading={eventSaving}
        cancelButtonProps={{ disabled: eventSaving }}
        closable={!eventSaving}
        onOk={() => void createContractEvent()}
        onCancel={() => { if (eventSaving) return; setEventTarget(null); eventForm.resetFields(); }}
        destroyOnHidden
      >
        <Form form={eventForm} layout="vertical">
          <Form.Item label="事项内容" name="content" rules={[{ required: true, whitespace: true, max: 1000, message: "请填写不超过 1000 字的事项内容" }]}>
            <Input.TextArea rows={5} maxLength={1000} showCount placeholder="记录合同履行、沟通或需要跟进的事项" />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        width={820}
        open={open && initialView !== "contract-new"}
        title={editing ? "编辑合同" : "新建合同"}
        footer={
          editing ? [
            <Button key="cancel" onClick={() => setOpen(false)}>取消</Button>,
            <Button key="save" type="primary" loading={savingContract} onClick={save}>保存草稿</Button>,
          ] : [
            wizardStep > 0 && wizardStep < CONTRACT_CREATE_STEP_TITLES.length && (wizardStep !== 1 || ["草稿", "已拒绝"].includes(wizardDraft?.status || "")) ? <Button key="back" onClick={() => setWizardStep((step) => Math.max(0, step - 1))}>上一步</Button> : null,
            <Button key="close" onClick={() => setOpen(false)}>{wizardStep === 0 ? "取消" : "关闭"}</Button>,
            wizardStep === 0 ? <Button key="next" type="primary" loading={savingContract} onClick={save}>下一步</Button> : null,
            wizardStep === 1 && wizardDraft?.status === "草稿" ? <Button key="revoke" danger onClick={() => revokeDraft(wizardDraft)}>撤销草稿</Button> : null,
            wizardStep === 1 && ["草稿", "已拒绝"].includes(wizardDraft?.status || "") ? <Button key="submit" type="primary" loading={submittingWizard} onClick={submitWizard}>提交审批</Button> : null,
            wizardStep === 1 && wizardDraft?.status === "审批中" ? <Button key="detail" type="primary" onClick={() => { const route = buildContractDetailRoute(wizardDraft); if (route) { setOpen(false); onNavigate?.(route); } }}>查看合同详情</Button> : null,
            wizardStep === 2 ? <Button key="refresh" type="primary" onClick={refreshWizard}>刷新审批状态</Button> : null,
            wizardStep === 3 && !wizardDraft?.data.seal_application_id ? <Button key="seal-save" onClick={() => { sealForm.setFieldValue("submit", false); void createSealApplication(); }}>保存用印草稿</Button> : null,
            wizardStep === 3 && !wizardDraft?.data.seal_application_id ? <Button key="seal-submit" type="primary" onClick={() => { sealForm.setFieldValue("submit", true); void createSealApplication(); }}>生成用印申请并进入用印中心</Button> : null,
            wizardStep === 3 && wizardDraft?.data.seal_application_id && wizardDraft?.status !== "审批中" ? <Button key="seal" type="primary" onClick={() => { setOpen(false); onNavigate?.("seal-my"); }}>进入用印中心</Button> : null,
          ]
        }
        onCancel={() => setOpen(false)}
        destroyOnHidden
      >
        {!editing && wizardStep < CONTRACT_CREATE_STEP_TITLES.length && (
          <Steps
            className="contract-create-steps"
            current={Math.min(wizardStep, CONTRACT_CREATE_STEP_TITLES.length - 1)}
            items={CONTRACT_CREATE_STEP_TITLES.map((title) => ({ title }))}
          />
        )}
        {(editing || wizardStep === 0) && (
        <Form form={form} layout="vertical">
          <div className="form-grid">
            <Form.Item hidden={!editing} label="合同编号" name="serial_no" rules={[{ required: true }]}>
              <Input disabled={Boolean(editing)} />
            </Form.Item>
            <Form.Item label="客户" name="customer_id" rules={[{ required: true, message: "请选择客户" }]}>
              <Select showSearch optionFilterProp="label" placeholder="输入客户名称关键字后选择" options={customerOptions} notFoundContent="没有匹配客户，请先在客户管理中新建客户" onChange={() => setLinkedCustomerContext(null)} />
            </Form.Item>
            <Form.Item label="合同主体" name="contract_body" rules={[{ required: true }]}>
              <Select options={["律所", "平台"].map((v) => ({ value: v, label: v }))} />
            </Form.Item>
            <Form.Item label="合同类别" name="type" rules={[{ required: true }]}>
              <Select allowClear showSearch optionFilterProp="label" placeholder="请选择合同类别" options={CONTRACT_TYPE_OPTIONS} />
            </Form.Item>
            <Form.Item label="收费模式" name="fee_type" rules={[{ required: true }]}>
              <Select options={CONTRACT_FEE_MODE_OPTIONS} />
            </Form.Item>
            <Form.Item label="外部合同号（可多个）" name="external_contract_numbers">
              <Select mode="tags" tokenSeparators={[",", "，"]} placeholder="输入客户方合同编号后回车" />
            </Form.Item>
            <Form.Item
              className="span-2"
              label="合同名称"
              name="title"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              label="合同金额"
              name="amount"
              hidden={!editing}
            >
              <InputNumber min={0} precision={2} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item
              label="签订日期"
              name="signed_at"
              hidden={!editing}
            >
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item label="负责人" name="owner" hidden={!editing}>
              <Input />
            </Form.Item>
            <Form.Item label="所属部门" name="department" hidden={!editing}>
              <Input />
            </Form.Item>
            <Form.Item className="span-2" label="备注" name="description" rules={[{ required: !editing }]}>
              <Input.TextArea rows={2} placeholder="备注" />
            </Form.Item>
            <Form.Item className="span-2" label="合同附件">
              <input type="file" onChange={(event) => setContractFile(event.target.files?.[0] || null)} />
            </Form.Item>
          </div>
        </Form>
        )}
        {!editing && wizardStep === 1 && (
          <div className="contract-wizard-panel">
            <Descriptions bordered size="small" column={2} items={wizardDraft ? [
              { key: "no", label: "合同编号", children: wizardDraft.serial_no },
              { key: "status", label: "当前状态", children: <Tag>{wizardDraft.status}</Tag> },
              { key: "name", label: "合同名称", children: wizardDraft.title, span: 2 },
              { key: "customer", label: "客户", children: wizardDraft.customer },
              { key: "type", label: "合同类别", children: wizardDraft.data.type },
            ] : []} />
            <Form.Item label="合同附件" extra="可在草稿阶段补传；未上传时提交审批会被阻断">
              <Space wrap>
                <input type="file" accept={CONTRACT_ATTACHMENT_ACCEPT} onChange={(event) => setContractFile(event.target.files?.[0] || null)} />
                <Button onClick={uploadDraftContractAttachment} disabled={!contractFile}>上传附件</Button>
              </Space>
            </Form.Item>
            <Form form={submitForm} layout="vertical" className="contract-submit-form">
              <Form.Item label="是否同步用印" name="sync_seal" initialValue={false}>
                <Radio.Group disabled={!(["草稿", "已拒绝"].includes(wizardDraft?.status || ""))} options={[{ value: true, label: "是" }, { value: false, label: "否" }]} />
              </Form.Item>
              <Form.Item label={contractApproverLabel} name="approvers" rules={[{required:true,message:"请选择一名合同审批人"}]}>
                <Select disabled={!(["草稿", "已拒绝"].includes(wizardDraft?.status || ""))} showSearch optionFilterProp="label" options={approvalOptions} placeholder="请选择后台已配置的合同审批人" notFoundContent="没有可用审批人，请由管理员设置在职员工的合同审批资格" />
              </Form.Item>
              <Form.Item label="提交说明" name="comment"><Input.TextArea disabled={!(["草稿", "已拒绝"].includes(wizardDraft?.status || ""))} rows={3} /></Form.Item>
            </Form>
            <p className="contract-draft-tip">合同草稿已经持久化保存。关闭向导后，可在“我的合同”中继续编辑或提交。</p>
          </div>
        )}
        {!editing && wizardStep === 2 && (
          <div className="contract-wizard-panel">
            <Descriptions bordered size="small" column={2} items={wizardDraft ? [
              { key: "no", label: "合同编号", children: wizardDraft.serial_no },
              { key: "status", label: "合同状态", children: <Tag color={colors[wizardDraft.status]}>{wizardDraft.status}</Tag> },
              { key: "name", label: "合同名称", children: wizardDraft.title, span: 2 },
            ] : []} />
            <Steps direction="vertical" size="small" className="contract-approval-flow" items={stepItems} />
            {wizardDraft?.status === "审批中" && currentApproval && (canActOnCurrentApproval ? (
              <Form form={reviewForm} layout="vertical" className="contract-review-form">
                <div className="contract-current-approval">当前节点：第 {currentApproval.step_order} 级 · {personName(currentApproval.approver_display_name || currentApproval.approver)}</div>
                <Form.Item label="审批意见" name="comment"><Input.TextArea rows={3} placeholder="填写通过意见；拒绝时必须填写原因" /></Form.Item>
                <Space>
                  <Button danger icon={<CloseOutlined />} onClick={() => approveWizard(false)}>拒绝</Button>
                  <Button type="primary" icon={<CheckOutlined />} onClick={() => approveWizard(true)}>通过当前节点</Button>
                </Space>
              </Form>
            ) : <Alert type="info" showIcon title={`合同已进入 ${personName(currentApproval.approver_display_name || currentApproval.approver)} 的待审批列表`} description="请等待指定审批人处理。" />)}
            <Divider titlePlacement="start">合同附件</Divider>
            <div className="contract-attachment-list">
              {attachments.length ? attachments.map((item) => (
                <Button key={item.id} type="link" onClick={() => downloadAttachment(item)}>{item.original_name}</Button>
              )) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无合同附件" />}
            </div>
            <Divider titlePlacement="start">状态时间线</Divider>
            {historyItems.length ? <Timeline items={historyItems} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无流程记录" />}
          </div>
        )}
        {!editing && wizardStep === 3 && (
          <div className="contract-wizard-panel contract-seal-step">
            {wizardDraft?.status === "审批中" ? <Alert type="info" showIcon title="合同正在审批中" description="可先提交用印申请；合同审批与用印审批将分别流转。" /> : <div className="contract-wizard-finished"><CheckOutlined /><h3>合同审批已通过</h3><p>合同草稿、审批意见、附件和时间线均已保存，可以继续办理合同用印。</p></div>}
            {wizardDraft?.data.seal_application_id ? (
              <Descriptions bordered size="small" column={2} items={[
                { key: "contract", label: "合同编号", children: wizardDraft.serial_no },
                { key: "seal", label: "用印申请编号", children: wizardDraft.data.seal_application_no || `#${wizardDraft.data.seal_application_id}` },
                { key: "status", label: "衔接状态", children: <Tag color="green">已生成真实用印申请</Tag>, span: 2 },
              ]} />
            ) : (
              <Form form={sealForm} layout="vertical" className="contract-seal-form">
                <div className="form-grid">
                  <Form.Item label="选择印章" name="seal_asset_id" rules={[{ required: true, message: "请选择印章" }]}>
                    <Select placeholder="请选择印章类型" notFoundContent="暂无可用印章，请管理员到用印中心维护" options={sealAssets.map((asset) => ({ value: asset.id, label: `${asset.seal_type}｜${asset.name}（${asset.code}）` }))} />
                  </Form.Item>
                  <Form.Item label="用印份数" name="copies" rules={[{ required: true }]}><InputNumber min={1} max={999} style={{ width: "100%" }} /></Form.Item>
                  <Form.Item label="计划用印日期" name="use_date" rules={[{ required: true }]}><DatePicker style={{ width: "100%" }} /></Form.Item>
                  <Form.Item label="办理方式" name="delivery_method"><Select options={["现场用印", "邮寄用印", "外带用印"].map((value) => ({ value, label: value }))} /></Form.Item>
                  <Form.Item className="span-2" label="文件名称" name="document_names"><Input placeholder="多份文件可用顿号分隔" /></Form.Item>
                  <Form.Item className="span-2" label="用印用途" name="purpose" rules={[{ required: true }]}><Input /></Form.Item>
                  <Form.Item className="span-2" label="申请说明" name="description"><Input.TextArea rows={2} /></Form.Item>
                </div>
                <Form.Item name="submit" valuePropName="checked" hidden><Checkbox /></Form.Item>
              </Form>
            )}
            <Divider titlePlacement="start">合同附件</Divider>
            <div className="contract-attachment-list">
              {attachments.length ? attachments.map((item) => (
                <Button key={item.id} type="link" onClick={() => downloadAttachment(item)}>{item.original_name}</Button>
              )) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无合同附件" />}
            </div>
            <Divider titlePlacement="start">合同状态时间线</Divider>
            {historyItems.length ? <Timeline items={historyItems} /> : null}
          </div>
        )}
      </Modal>
      <Modal
        open={Boolean(submitting)}
        title={`配置审批流程：${submitting?.title || ""}`}
        okText="提交审批"
        confirmLoading={submitSaving}
        closable={!submitSaving}
        onOk={submit}
        cancelButtonProps={{ disabled: submitSaving }}
        onCancel={() => { if (submitSaving) return; setSubmitting(null); }}
      >
        <Form form={submitForm} layout="vertical">
          <Form.Item
            label={contractApproverLabel}
            name="approvers"
            rules={[{ required: true }]}
          >
            <Select showSearch optionFilterProp="label" options={approvalOptions} placeholder="请选择后台已配置的合同审批人" notFoundContent="没有可用审批人，请由管理员设置在职员工的合同审批资格" />
          </Form.Item>
          <Form.Item label="提交说明" name="comment">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        width={760}
        open={approverSettingsOpen}
        title="设置合同审批人"
        okText="保存设置"
        cancelText="取消"
        confirmLoading={approverSettingsSaving}
        onOk={saveApproverSettings}
        onCancel={() => setApproverSettingsOpen(false)}
      >
        <Alert
          type="info"
          showIcon
          title="仅管理员可以配置"
          description={<Space direction="vertical" size={4}>这些人员来自人事中心的在职员工。取消勾选只移除合同审批资格，不会删除员工档案；姓名待维护的员工不会进入合同提交下拉。<Button type="link" style={{ padding: 0, height: "auto", alignSelf: "flex-start" }} onClick={() => { setApproverSettingsOpen(false); onNavigate?.("hr-all"); }}>前往人事中心维护姓名</Button></Space>}
          style={{ marginBottom: 16 }}
        />
          <Table
          rowKey="username"
          size="small"
          loading={approverSettingsLoading}
          pagination={false}
          dataSource={approverSettings}
          rowClassName={(row) => (row.username === approverSettingsTargetUsername ? "contract-approver-target-row" : "")}
          rowSelection={{
            selectedRowKeys: selectedApproverUsernames,
            onChange: (keys) => setSelectedApproverUsernames(keys.map(String)),
            getCheckboxProps: (row: ApproverSetting) => ({
              disabled: row.display_name_valid === false && !selectedApproverUsernames.includes(row.username),
            }),
          }}
          columns={[
            { title: "姓名", dataIndex: "display_name", render: (value: string) => personName(value) },
            { title: "登录账号", dataIndex: "username" },
            { title: "部门", dataIndex: "department", render: (value: string) => value || "—" },
            { title: "职务", dataIndex: "position", render: (value: string) => value || "—" },
          ]}
          locale={{ emptyText: "暂无可配置的启用、在职员工" }}
        />
      </Modal>
      <Modal
        width={680}
        open={Boolean(reviewing)}
        title={`合同审批：${reviewing?.title || ""}`}
        footer={
          reviewing?.status === "审批中" && canActOnCurrentApproval ? (
            <Space>
              <Button
                danger
                icon={<CloseOutlined />}
                onClick={() => approve(false)}
              >
                拒绝
              </Button>
              <Button
                type="primary"
                icon={<CheckOutlined />}
                onClick={() => approve(true)}
              >
                通过当前节点
              </Button>
            </Space>
          ) : (
            <Button onClick={() => setReviewing(null)}>关闭</Button>
          )
        }
        onCancel={() => setReviewing(null)}
      >
        <Steps direction="vertical" items={stepItems} />
        {reviewing?.status === "审批中" && canActOnCurrentApproval && (
          <Form form={reviewForm} layout="vertical">
            <Form.Item label="审批意见" name="comment">
              <Input.TextArea rows={3} />
            </Form.Item>
          </Form>
        )}
        {reviewing?.status === "审批中" && currentApproval && profile.role === "admin" && currentApproval.approver !== profile.username && <Alert type="info" showIcon title={`当前节点指定审批人：${personName(currentApproval.approver_display_name || currentApproval.approver)}`} description="管理员可按最高权限代办；审批历史会明确记录管理员代办。" />}
        {reviewing?.status === "审批中" && !canActOnCurrentApproval && currentApproval && <Alert type="info" showIcon title={`当前节点应由 ${personName(currentApproval.approver_display_name || currentApproval.approver)} 审批`} description="当前账号没有该审批节点的办理权限。" />}
      </Modal>
      <Modal
        width={720}
        open={Boolean(changing)}
        title={`合同变更：${changing?.serial_no || ""}`}
        okText="登记变更"
        cancelText="取消"
        onOk={saveChange}
        onCancel={() => setChanging(null)}
      >
        <Form form={changeForm} layout="vertical">
          <Form.Item label="客户" name="customer">
            <Input disabled />
          </Form.Item>
          <Form.Item
            label="变更类型"
            name="change_type"
            rules={[{ required: true }]}
          >
            <Select
              options={[
                "合同补充/修订",
                "金额调整",
                "期限变更",
                "主体信息变更",
                "其他",
              ].map((v) => ({ value: v, label: v }))}
            />
          </Form.Item>
          <Form.Item
            label="变更原因"
            name="reason"
            rules={[{ required: true, min: 2 }]}
          >
            <Input.TextArea rows={3} />
          </Form.Item>
          <div className="form-grid">
            <Form.Item label="合同主体" name="contract_body">
              <Select options={["律所", "平台"].map((value) => ({ value, label: value }))} />
            </Form.Item>
            <Form.Item label="合同类别" name="contract_type">
              <Select options={CONTRACT_TYPE_OPTIONS} />
            </Form.Item>
            <Form.Item label="收费模式" name="fee_type">
              <Select options={CONTRACT_FEE_MODE_OPTIONS} />
            </Form.Item>
            <Form.Item className="span-2" label="合同名称" name="title">
              <Input />
            </Form.Item>
            <Form.Item label="合同金额" name="amount">
              <InputNumber min={0} precision={2} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item label="外部合同号（可多个）" name="external_contract_numbers">
              <Select mode="tags" tokenSeparators={[",", "，"]} placeholder="输入后回车，可关联多个" />
            </Form.Item>
            <Form.Item className="span-2" label="合同截止日期" name="end_date">
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item className="span-2" label="备注" name="description">
              <Input.TextArea rows={3} />
            </Form.Item>
          </div>
        </Form>
      </Modal>
      <Modal
        width={820}
        open={Boolean(changeHistory)}
        title={`合同变更记录：${changeHistory?.serial_no || ""}`}
        footer={<Button onClick={() => setChangeHistory(null)}>关闭</Button>}
        onCancel={() => setChangeHistory(null)}
      >
        <Table
          rowKey="id"
          size="small"
          pagination={false}
          dataSource={changes}
          columns={[
            {
              title: "时间",
              dataIndex: "created_at",
              width: 170,
              render: (v: string) => new Date(v).toLocaleString("zh-CN"),
            },
            { title: "类型", dataIndex: "change_type", width: 130 },
            {
              title: "变更内容",
              key: "detail",
              render: (_: unknown, r: Change) => (
                <>
                  {r.changes.map((x) => (
                    <div key={x.field}>
                      {x.label}：{String(x.before ?? "—")} →{" "}
                      <b>{String(x.after ?? "—")}</b>
                    </div>
                  ))}
                </>
              ),
            },
            { title: "原因", dataIndex: "reason", width: 170 },
            { title: "操作人", dataIndex: "operator", width: 90, render: (value: string) => personName(value) },
          ]}
        />
      </Modal>
    </>
  );
}
