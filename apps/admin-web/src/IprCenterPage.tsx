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
  Tag,
  message,
} from "antd";
import type { TableColumnsType } from "antd";
import dayjs from "dayjs";
import { api } from "./api";
import { formatRequiredDate } from "./formSafety";
import {
  buildIprCaseActionPayload,
  getIprCaseActionValidationError,
} from "./iprCaseWorkflowParity.mjs";
import {
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
  status: string;
  description: string;
  data: Record<string, any>;
  updated_at: string;
};
type Customer = { id: number; title: string; serial_no: string };
type Attachment = {
  id: number;
  original_name: string;
  size: number;
  uploader: string;
  category?: string;
  document_date?: string | null;
  requires_transmission?: boolean;
  is_transmitted?: boolean;
  transmitted_by?: string;
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
  response_date: string | null;
  response_user: string;
  remark: string;
  receipt: Attachment | null;
};
type IprReminder = {
  id: number;
  event_type_id: number;
  event_type: string;
  reminder_date: string;
  deadline: string;
  content: string;
  creator: string;
};
type ReminderEventType = { id: number; name: string; suppressed: boolean };
type IprLawFirm = { id: number; law_firm_id: number; code: string; name: string; phone: string; email: string };
type IprLawFirmCandidate = { id: number; code: string; name: string; phone: string; email: string; selected: boolean };
type IprCaseCustomer = { id: number | null; customer_id: number; customer_no: string; name: string; status: string; is_primary: boolean };
type IprCaseCustomerCandidate = { id: number; customer_no: string; name: string; status: string; selected: boolean };
type CustomerContact = { id: string; name: string; phone?: string; email?: string; position?: string; is_valid?: boolean };
type IprCaseContact = CustomerContact & { customer_id: number; customer_name: string; contact_id: string; contact_role: "document" | "technology" };
type IprBusinessLog = { id: number; content: string; created_by: string; created_at: string };
type IprOperationLog = { id: number; action: string; operator: string; comment: string; from_status?: string; to_status?: string; created_at: string };
type IprHistoryItem = { id: number; action: string; operator: string; comment?: string; from_status?: string; to_status?: string; created_at: string };
type IprDetailPageState = { page: number; pageSize: number; total: number; pages: number };
type IprDetailPagePayload<T> = { items?: T[]; total?: number; page?: number; page_size?: number; pages?: number };
const IPR_DETAIL_DEFAULT_PAGE = 1;
const IPR_DETAIL_DEFAULT_PAGE_SIZE = 15;
const statusColor: Record<string, string> = {
  草稿: "default",
  待立案审核: "gold",
  在办: "blue",
  已驳回: "red",
  已结案: "green",
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
  const [items, setItems] = useState<IprRecord[]>([]),
    [total, setTotal] = useState(0),
    [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);
  const [pages, setPages] = useState(0);
  const [keyword, setKeyword] = useState(""),
    [annualFeeMonitoringFilter, setAnnualFeeMonitoringFilter] = useState<"" | "true" | "false">(""),
    [form] = Form.useForm(),
    [createOpen, setCreateOpen] = useState(false),
    [detail, setDetail] = useState<IprRecord | null>(null),
    [editing, setEditing] = useState<IprRecord | null>(null),
    [attachments, setAttachments] = useState<Attachment[]>([]);
  const [iprSectionErrors, setIprSectionErrors] = useState({
    files: "",
    logs: "",
    reminders: "",
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
  const [assistedFeesPageState, setAssistedFeesPageState] = useState<IprDetailPageState>({
    page: IPR_DETAIL_DEFAULT_PAGE,
    pageSize: IPR_DETAIL_DEFAULT_PAGE_SIZE,
    total: 0,
    pages: 0,
  });
  const [customers, setCustomers] = useState<Customer[]>([]),
    [profile, setProfile] = useState<{ role?: string; username?: string }>({}),
    [maintenanceTarget, setMaintenanceTarget] = useState<IprRecord | null>(
      null,
    ),
    [maintenanceForm] = Form.useForm(),
    [assistedFees, setAssistedFees] = useState<AssistedFee[]>([]),
    [assistedOpen, setAssistedOpen] = useState(false),
    [assistedForm] = Form.useForm(),
    [transactTarget, setTransactTarget] = useState<AssistedFee | null>(null),
    [transactForm] = Form.useForm(),
    [receiptFile, setReceiptFile] = useState<File | null>(null),
    [reminders, setReminders] = useState<IprReminder[]>([]),
    [reminderOpen, setReminderOpen] = useState(false),
    [reminderForm] = Form.useForm(),
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
    [iprLogForm] = Form.useForm();
  const [deadlineOffsetOpen, setDeadlineOffsetOpen] = useState(false);
  const [deadlineOffsetForm] = Form.useForm();
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
      [section]: getIprSectionLoadError(section, error),
    }));
  };
  const handledDetailTarget = useRef("");
  const reviewView = initialView === "ipr-review";
  const load = async (nextPage = page, nextPageSize = pageSize) => {
    setLoading(true);
    try {
      const { data } = await api.get("/ipr/cases", {
        params: {
          case_kind: kind,
          record_status: reviewView ? "待立案审核" : "",
          keyword,
          annual_fee_monitoring: annualFeeMonitoringFilter || undefined,
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
  useEffect(() => {
    void load(1, pageSize);
    void api
      .get<{ items: Customer[] }>("/customers", { params: { page_size: 100 } })
      .then(({ data }) => setCustomers(data.items || []))
      .catch(() => setCustomers([]));
    void api
      .get<{ role?: string; username?: string }>("/auth/me")
      .then(({ data }) => setProfile(data))
      .catch(() => setProfile({}));
  }, [initialView, annualFeeMonitoringFilter]);
  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ case_kind: kind || "专利", rate: 0 });
    setCreateOpen(true);
  };
  const openEdit = (record: IprRecord) => {
    setEditing(record);
    form.resetFields();
    form.setFieldsValue({
      case_kind: record.data.case_kind,
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
      rate: record.data.rate ?? 0,
      description: record.description,
    });
    setCreateOpen(true);
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
  const loadReminders = async (
    caseId: number,
    nextPage = remindersPageState.page,
    nextPageSize = remindersPageState.pageSize,
  ) => {
    try {
      const { data } = await api.get<IprDetailPagePayload<IprReminder>>(
        `/ipr/cases/${caseId}/reminders`,
        { params: { page: nextPage, page_size: nextPageSize } },
      );
      setReminders(data.items || []);
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
    setAttachments([]);
    setIprBusinessLogs([]);
    setIprOperationLogs([]);
    setAssistedFees([]);
    setReminders([]);
    setFilesPageState({ page: IPR_DETAIL_DEFAULT_PAGE, pageSize: IPR_DETAIL_DEFAULT_PAGE_SIZE, total: 0, pages: 0 });
    setRemindersPageState({ page: IPR_DETAIL_DEFAULT_PAGE, pageSize: IPR_DETAIL_DEFAULT_PAGE_SIZE, total: 0, pages: 0 });
    setAssistedFeesPageState({ page: IPR_DETAIL_DEFAULT_PAGE, pageSize: IPR_DETAIL_DEFAULT_PAGE_SIZE, total: 0, pages: 0 });
    setIprSectionErrors({ files: "", logs: "", reminders: "", assistedFees: "" });
    try {
      await Promise.all([
        loadIprFiles(record.id, IPR_DETAIL_DEFAULT_PAGE, IPR_DETAIL_DEFAULT_PAGE_SIZE),
        loadCaseLawFirms(record.id),
        loadCaseCustomers(record.id),
        loadCaseContacts(record.id),
        loadIprLogs(record.id),
        loadIprHistory(record.id),
        loadAssistedFees(record.id, IPR_DETAIL_DEFAULT_PAGE, IPR_DETAIL_DEFAULT_PAGE_SIZE),
        loadReminders(record.id, IPR_DETAIL_DEFAULT_PAGE, IPR_DETAIL_DEFAULT_PAGE_SIZE),
        loadReminderSuppressions(record.id),
      ]);
    } catch (error) {
      message.error(getIprApiErrorMessage(error, "案件详情加载失败"));
    }
  };
  useEffect(() => {
    const targetId = Number(
      new URLSearchParams(window.location.search).get("record_id") || 0,
    );
    const targetKey = `${initialView}:${targetId}`;
    if (!targetId || handledDetailTarget.current === targetKey) return;
    handledDetailTarget.current = targetKey;
    const listed = items.find((item) => item.id === targetId);
    if (listed) {
      void openDetail(listed);
      return;
    }
    void api
      .get(`/ipr/cases/${targetId}`)
      .then(({ data }) => {
        if (kind && data?.data?.case_kind !== kind) {
          message.warning("关联案件类型与当前页面不一致");
          return;
        }
        void openDetail(data);
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
      await api.post(`/ipr/cases/${detail.id}/files`, payload);
      message.success("案件文档已上传");
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
      const { data } = await api.post("/ipr/cases/files/batch-upload", payload);
      message.success(`已向 ${data.created} 个案件上传文档`); setIprBatchOpen(false); setIprBatchFile(null); iprBatchForm.resetFields();
    } catch (e: any) { if (!e?.errorFields) message.error(e?.response?.data?.detail || "批量上传案件文档失败"); }
  };
  const markIprFileTransmitted = async (row: Attachment) => {
    if (!detail) return;
    try {
      await api.post(
        `/ipr/cases/${detail.id}/files/${row.id}/mark-transmitted`,
        { comment: "" },
      );
      message.success("已标记为已转");
      await loadIprFiles(detail.id);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "标记已转失败");
    }
  };
  const markSelectedIprFilesTransmitted = async () => {
    if (!detail || !selectedIprFileIds.length) return;
    try {
      const { data } = await api.post(`/ipr/cases/${detail.id}/files/mark-transmitted`, { attachment_ids: selectedIprFileIds, comment: "" });
      message.success(`已标记 ${data.updated} 份文档为已转`);
      setSelectedIprFileIds([]);
      await loadIprFiles(detail.id);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "批量标记已转失败");
    }
  };
  const deleteIprFile = async (row: Attachment) => {
    if (!detail) return;
    try {
      await api.delete(`/ipr/cases/${detail.id}/files/${row.id}`);
      message.success("案件文档已删除");
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
      message.success("资助费用已提交，等待办理");
      setAssistedOpen(false);
      assistedForm.resetFields();
      await loadAssistedFees(detail.id);
    } catch (e: any) {
      if (!e?.errorFields)
        message.error(e?.response?.data?.detail || "新建资助费用失败");
    }
  };
  const transactAssistedFee = async () => {
    if (!detail || !transactTarget) return;
    try {
      const values = await transactForm.validateFields();
      if (!receiptFile) {
        message.warning("请上传资助回执文件");
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
      message.success("资助费用已办理并保存回执");
      setTransactTarget(null);
      setReceiptFile(null);
      transactForm.resetFields();
      await loadAssistedFees(detail.id);
    } catch (e: any) {
      if (!e?.errorFields)
        message.error(e?.response?.data?.detail || "办理资助费用失败");
    }
  };
  const deleteAssistedFee = async (row: AssistedFee) => {
    if (!detail) return;
    try {
      await api.delete(`/ipr/cases/${detail.id}/assisted-fees/${row.id}`);
      message.success("资助费用已删除");
      await loadAssistedFees(detail.id);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "删除资助费用失败");
    }
  };
  const createReminder = async () => {
    if (!detail) return;
    try {
      const values = await reminderForm.validateFields();
      await api.post(`/ipr/cases/${detail.id}/reminders`, {
        ...values,
        reminder_date: formatRequiredDate(values.reminder_date, "提醒日期"),
        deadline: formatRequiredDate(values.deadline, "截止日期"),
      });
      message.success("案件提醒已保存");
      setReminderOpen(false);
      reminderForm.resetFields();
      await loadReminders(detail.id);
    } catch (e: any) {
      if (!e?.errorFields)
        message.error(e?.response?.data?.detail || "新增案件提醒失败");
    }
  };
  const deleteReminder = async (row: IprReminder) => {
    if (!detail) return;
    try {
      await api.delete(`/ipr/cases/${detail.id}/reminders/${row.id}`);
      message.success("案件提醒已删除");
      await loadReminders(detail.id);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "删除案件提醒失败");
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
          keyword,
          annual_fee_monitoring: annualFeeMonitoringFilter || undefined,
        },
        responseType: "blob",
      });
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${kind || "知识产权"}案件清单.xls`;
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
      await api.post(
        `/ipr/cases/${record.id}/${name}`,
        payload,
      );
      message.success("操作成功");
      setDetail(null);
      void load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "操作失败");
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
      { title: "客户", dataIndex: "customer", width: 160, ellipsis: true },
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
    [profile.role, reviewView],
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
      if (detail) void loadReminders(detail.id, nextPage, nextPageSize);
    },
  };
  return (
    <div className="page-shell">
      <Card
        title={reviewView ? "知识产权立案审核" : `${kind || "全部"}案件台账`}
        extra={
          !reviewView && (
            <Space>
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
                value={annualFeeMonitoringFilter}
                onChange={setAnnualFeeMonitoringFilter}
                style={{ width: 112 }}
                options={[{ value: "", label: "全部年费" }, { value: "true", label: "监控中" }, { value: "false", label: "未监控" }]}
              />
              <Button onClick={() => void exportExcel()}>导出Excel</Button>
              <Button onClick={() => { iprBatchForm.resetFields(); iprBatchForm.setFieldsValue({ document_date: dayjs() }); void loadIprFileTypes(""); setIprBatchFile(null); setIprBatchOpen(true); }}>批量上传文档</Button>
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
            showTotal: (t) => "共 " + t + " 条" + (pages ? " / " + pages + " 页" : ""),
            onChange: (nextPage, nextPageSize) => void load(nextPage, nextPageSize),
          }}
        />
      </Card>
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
        onClose={() => setDetail(null)}
      >
        {detail && (
          <>
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
                  { title: "内容", dataIndex: "content", ellipsis: true },
                  { title: "创建人", dataIndex: "created_by", width: 110 },
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
                  { title: "操作", dataIndex: "action", width: 180 },
                  { title: "说明", dataIndex: "comment", ellipsis: true, render: (value) => value || "—" },
                  { title: "操作人", dataIndex: "operator", width: 110 },
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
                  { title: "事项", dataIndex: "action", width: 160 },
                  { title: "状态变化", width: 180, render: (_, row: IprHistoryItem) => row.from_status || row.to_status ? `${row.from_status || "—"} → ${row.to_status || "—"}` : "—" },
                  { title: "说明", dataIndex: "comment", ellipsis: true },
                  { title: "操作人", dataIndex: "operator", width: 110 },
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
                  { title: "客户编号", dataIndex: "customer_no", width: 150 },
                  { title: "客户名称", dataIndex: "name", render: (value, row) => <Space>{value}{row.is_primary ? <Tag color="blue">主客户</Tag> : null}</Space> },
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
          <Card size="small" title="案件文书与附件" style={{ marginTop: 16 }}>
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
                      <Button
                        key={item.id}
                        type="link"
                        onClick={() => void downloadAttachment(item)}
                      >
                        {item.original_name}
                      </Button>
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
                  render: (_, row: Attachment) => <Button type="link" onClick={() => void downloadAttachment(row)}>{row.original_name}</Button>,
                },
                { title: "上传人", dataIndex: "uploader", width: 95 },
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
          <Card
            size="small"
            title="资助明细"
              style={{ marginTop: 16 }}
              extra={
                detail.status === "在办" ? (
                  <Button
                    type="primary"
                    size="small"
                    onClick={() => {
                      assistedForm.resetFields();
                      setAssistedOpen(true);
                    }}
                  >
                    新建资助费用
                  </Button>
                ) : null
              }
            >
              {iprSectionErrors.assistedFees ? <Alert type="error" showIcon message={iprSectionErrors.assistedFees} style={{ marginBottom: 12 }} /> : null}
              <Table
                rowKey="id"
                size="small"
                pagination={assistedFeesPagination}
                dataSource={assistedFees}
                scroll={{ x: 780 }}
                columns={[
                  { title: "资助类别", dataIndex: "assisted_type", width: 150 },
                  {
                    title: "提交",
                    width: 145,
                    render: (_, row: AssistedFee) =>
                      `${row.request_date || "—"} / ${row.request_user || "—"}`,
                  },
                  {
                    title: "办理",
                    width: 145,
                    render: (_, row: AssistedFee) =>
                      row.response_date
                        ? `${row.response_date} / ${row.response_user || "—"}`
                        : "待办理",
                  },
                  {
                    title: "回执文件",
                    width: 180,
                    render: (_, row: AssistedFee) =>
                      row.receipt ? (
                        <Button
                          type="link"
                          onClick={() => void downloadAttachment(row.receipt!)}
                        >
                          {row.receipt.original_name}
                        </Button>
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
                    width: 145,
                    render: (_, row: AssistedFee) => (
                      <Space size={0}>
                        {row.status === "待办理" &&
                          detail.status === "在办" && (
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
                        {row.status === "待办理" && (
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
            <Card
              size="small"
              title="案件提醒"
              style={{ marginTop: 16 }}
              extra={
                <Space>
                  {detail.status === "在办" && (
                    <Button
                      size="small"
                      onClick={() => {
                        reminderForm.resetFields();
                        reminderForm.setFieldsValue({
                          reminder_date: dayjs(),
                          deadline: detail.data.deadline
                            ? dayjs(detail.data.deadline)
                            : undefined,
                        });
                        setReminderOpen(true);
                      }}
                    >
                      新增提醒
                    </Button>
                  )}
                  {detail.status === "在办" && (
                    <Button
                      size="small"
                      onClick={() => setSuppressionOpen(true)}
                    >
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
                dataSource={reminders}
                scroll={{ x: 700 }}
                columns={[
                  { title: "提醒日期", dataIndex: "reminder_date", width: 110 },
                  { title: "截止日期", dataIndex: "deadline", width: 110 },
                  { title: "提醒内容", dataIndex: "content", ellipsis: true },
                  { title: "创建人", dataIndex: "creator", width: 100 },
                  {
                    title: "操作",
                    width: 80,
                    render: (_, row: IprReminder) =>
                      detail.status === "在办" ? (
                        <Button
                          type="link"
                          danger
                          onClick={() => confirmIprDeletion("reminder", row.content, () => deleteReminder(row))}
                        >
                          删除
                        </Button>
                      ) : (
                        "—"
                      ),
                  },
                ]}
              />
              <div style={{ marginTop: 8, color: "#777" }}>
                不监控类型：
                {reminderEventTypes
                  .filter((item) => suppressedIds.includes(item.id))
                  .map((item) => item.name)
                  .join("、") || "未设置"}
              </div>
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
        open={reminderOpen}
        title="新增知识产权案件提醒"
        onCancel={() => setReminderOpen(false)}
        onOk={() => void createReminder()}
        okText="保存提醒"
      >
        <Form form={reminderForm} layout="vertical">
          <Form.Item
            name="reminder_date"
            label="提醒日期"
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
            label="提醒内容"
            rules={[{ required: true, message: "请输入提醒内容" }]}
          >
            <Input.TextArea rows={3} maxLength={1000} />
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
        title="新建知识产权资助费用"
        onCancel={() => setAssistedOpen(false)}
        onOk={() => void createAssistedFee()}
        okText="提交"
      >
        <Form form={assistedForm} layout="vertical">
          <Form.Item
            name="assisted_type"
            label="资助类别"
            rules={[{ required: true, message: "请选择或填写资助类别" }]}
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
            ? `办理资助费用：${transactTarget.assisted_type}`
            : "办理资助费用"
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
