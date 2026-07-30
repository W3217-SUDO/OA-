import { useEffect, useMemo, useRef, useState } from "react";
import type { Key } from "react";
import {
  Alert,
  Button,
  Card,
  Checkbox,
  DatePicker,
  Dropdown,
  Drawer,
  Form,
  Input,
  InputNumber,
  message,
  Modal,
  Select,
  Space,
  Steps,
  Statistic,
  Table,
  Tabs,
  Tag,
  TimePicker,
} from "antd";
import {
  CalendarOutlined,
  CheckSquareOutlined,
  EditOutlined,
  FileTextOutlined,
  ReloadOutlined,
  TeamOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import { api } from "./api";
import { consumeCaseDetailTarget, rememberCaseDetailTarget } from "./caseDetailNavigation";
import { rememberContractDetailTarget } from "./contractDetailNavigation";
import { rememberCustomerDetailTarget, resolveCustomerDetailTarget } from "./customerDetailNavigation";
import { consumeCustomerRelationTarget } from "./customerRelationNavigation";
import { rememberInvestigationDetailTarget } from "./investigationDetailNavigation";
import { rememberTaskDetailTarget } from "./taskDetailNavigation";
import { rememberBusinessRecordDetailTarget } from "./businessRecordDetailNavigation";
import { formatRequiredDate } from "./formSafety";
import "./case-center.css";

type CaseRow = {
  id: number;
  module?: string;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
  owner: string;
  department: string;
  description: string;
  data: Record<string, any>;
};
const caseDocumentTypes = [
  ["authorization-letter", "授权委托书"], ["archive-letter", "归档函"], ["gd-authorization-letter", "广东版授权委托书"], ["compensation-letter", "赔偿函"],
  ["law-firm-letter", "律师事务所函"], ["identity-certificate", "主体身份证明"], ["settlement-list", "结算提成表"],
  ["first-instance-appellant-lawyer-letter", "一审上诉人律师函"], ["first-instance-appellee-lawyer-letter", "一审被上诉人律师函"],
  ["second-instance-appellant-lawyer-letter", "二审上诉人律师函"], ["second-instance-appellee-lawyer-letter", "二审被上诉人律师函"], ["execution-lawyer-letter", "执行律师函"],
  ["gd-first-instance-appellant-lawyer-letter", "广东版一审上诉人律师函"], ["gd-first-instance-appellee-lawyer-letter", "广东版一审被上诉人律师函"],
  ["gd-second-instance-appellant-lawyer-letter", "广东版二审上诉人律师函"], ["gd-second-instance-appellee-lawyer-letter", "广东版二审被上诉人律师函"], ["gd-execution-lawyer-letter", "广东版执行律师函"],
] as const;
type ContractRow = {
  id: number;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
  owner: string;
  department: string;
  data: Record<string, any>;
};
type Profile = {
  username: string;
  display_name: string;
  department: string;
  role?: string;
};
type Hearing = {
  id: number;
  case_record_id: number;
  case_no: string;
  case_title: string;
  customer: string;
  weekday: string;
  hearing_date: string;
  hearing_time: string;
  court: string;
  courtroom: string;
  hearing_type: string;
  hearing_lawyer: string;
  status: string;
};
type TaskRow = {
  id: number;
  serial_no: string;
  title: string;
  status: string;
  owner: string;
  initiator: string;
  deadline: string;
  priority: string;
  source: string;
  case_no: string;
  days_remaining?: number | null;
  collaborators?: string[];
};
type AttachmentRow = {id:number;record_id:number|null;original_name:string;category:string;uploader:string;created_at:string;size:number;remark?:string};
type AttachmentPreview = {name:string;kind:"image"|"pdf"|"text"|"docx";url?:string;text?:string};
type CaseReminderRow = {id:number;description:string;owner:string;data:{reminder_date:string;deadline:string;case_id:number}};
type CaseLogRow = {id:number;content:string;operator:string;created_at:string};
type CaseDetailCapabilities = {
  can_write: boolean;
  can_upload_attachment: boolean;
  can_delete_attachment: boolean;
  can_create_reminder: boolean;
  can_delete_reminder: boolean;
  can_create_log: boolean;
  can_update_progress: boolean;
  can_manage_hearing: boolean;
  can_create_case_task: boolean;
  can_duplicate_case: boolean;
  can_merge_case: boolean;
  can_assign_team: boolean;
  can_edit_basic: boolean;
  can_close_case: boolean;
  can_archive: boolean;
  can_create_finance: boolean;
  team_role: "manager" | "handling_lawyer" | "assistant" | "none";
  reason: string;
};
const noCaseDetailWriteCapability: CaseDetailCapabilities = {
  can_write: false, can_upload_attachment: false, can_delete_attachment: false,
  can_create_reminder: false, can_delete_reminder: false, can_create_log: false,
  can_update_progress: false, can_manage_hearing: false, can_create_case_task: false, can_duplicate_case: false, can_merge_case: false, can_assign_team: false,
  can_edit_basic: false, can_close_case: false, can_archive: false,
  can_create_finance: false, team_role: "none",
  reason: "当前账号没有案件详情办理权限",
};
// 普通附件是普通案件上传接口始终接受的兜底分类。主数据尚未配置时，
// 页面不能再提交一个接口无法识别的静态分类。
const DEFAULT_CASE_ATTACHMENT_CATEGORY = "普通附件";
const caseStatuses = [
  "等待公证书",
  "等待审核公证书",
  "待立案审批",
  "新案待分配",
  "文书准备",
  "一审立案受理",
  "一审准备开庭",
  "待上诉",
  "二审",
  "执行",
];
const statusColors: Record<string, string> = {
  等待公证书: "gold",
  等待审核公证书: "purple",
  待立案审批: "gold",
  新案待分配: "orange",
  文书准备: "blue",
  一审立案受理: "cyan",
  一审准备开庭: "purple",
  待上诉: "red",
  二审: "geekblue",
  执行: "volcano",
  待归档审核: "gold",
  已归档: "green",
};
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
  const [contractPrefill] = useState<{ id: number; title: string; customer: string } | null>(() => {
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
  const [tab, setTab] = useState(first);
  const [cases, setCases] = useState<CaseRow[]>([]);
  const [counselCases, setCounselCases] = useState<CaseRow[]>([]);
  const [counselTotal, setCounselTotal] = useState(0);
  const [counselPage, setCounselPage] = useState(1);
  const [counselPageSize, setCounselPageSize] = useState(10);
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
  const [archiveChecks, setArchiveChecks] = useState<Record<string, boolean>>({});
  const [reviewing, setReviewing] = useState<{
    row: CaseRow;
    approved: boolean;
  } | null>(null);
  const [progressEditing, setProgressEditing] = useState<CaseRow | null>(null);
  const [taskCase, setTaskCase] = useState<CaseRow | null>(null);
  const [viewingCounselCase, setViewingCounselCase] = useState<CaseRow | null>(null);
  const [mergingCase, setMergingCase] = useState<CaseRow | null>(null);
  const [notaryInfoCase, setNotaryInfoCase] = useState<CaseRow | null>(null);
  const [settlementAmountCase, setSettlementAmountCase] = useState<CaseRow | null>(null);
  const [counselDetailHistory, setCounselDetailHistory] = useState<any[]>([]);
  const [counselDetailTasks, setCounselDetailTasks] = useState<TaskRow[]>([]);
  const [counselDetailAttachments, setCounselDetailAttachments] = useState<AttachmentRow[]>([]);
  const [attachmentPreview, setAttachmentPreview] = useState<AttachmentPreview | null>(null);
  const [renamingCounselAttachment, setRenamingCounselAttachment] = useState<AttachmentRow | null>(null);
  const [sealingCounselAttachment, setSealingCounselAttachment] = useState<AttachmentRow | null>(null);
  const [caseSealAssets, setCaseSealAssets] = useState<{ id: number; status: string; seal_type: string; name: string }[]>([]);
  const [counselReminders, setCounselReminders] = useState<CaseReminderRow[]>([]);
  const [counselLogs, setCounselLogs] = useState<CaseLogRow[]>([]);
  const [counselDetailCapabilities, setCounselDetailCapabilities] = useState<CaseDetailCapabilities>(noCaseDetailWriteCapability);
  const [caseActionCapabilities, setCaseActionCapabilities] = useState<Record<number, CaseDetailCapabilities>>({});
  const [selectedCounselAttachmentKeys, setSelectedCounselAttachmentKeys] = useState<Key[]>([]);
  const [activeCounselDocCategory, setActiveCounselDocCategory] = useState("");
  const [counselUploadCategory, setCounselUploadCategory] = useState(DEFAULT_CASE_ATTACHMENT_CATEGORY);
  const [reminderOpen, setReminderOpen] = useState(false);
  const [caseLogOpen, setCaseLogOpen] = useState(false);
  const [batchUpdateOpen, setBatchUpdateOpen] = useState(false);
  const [batchFeeOpen, setBatchFeeOpen] = useState(false);
  const [editingCounselCase, setEditingCounselCase] = useState<CaseRow | null>(null);
  const [editingNormalCase, setEditingNormalCase] = useState<CaseRow | null>(null);
  const [editingArbitrationCase, setEditingArbitrationCase] = useState<CaseRow | null>(null);
  const [criminalMaintenance, setCriminalMaintenance] = useState<{row:CaseRow;kind:"litigants"|"public-security"|"procuratorates"|"courts"}|null>(null);
  const [feeCase, setFeeCase] = useState<CaseRow | null>(null);
  const [caseTaskCreateCase, setCaseTaskCreateCase] = useState<CaseRow | null>(null);
  const [refundCompleting, setRefundCompleting] = useState<CaseRow | null>(null);
  const [caseTasks, setCaseTasks] = useState<TaskRow[]>([]);
  const [selectedCaseKeys, setSelectedCaseKeys] = useState<Key[]>([]);
  const [caseQuery, setCaseQuery] = useState<Record<string, any>>({});
  const [caseUploadCategory, setCaseUploadCategory] = useState(DEFAULT_CASE_ATTACHMENT_CATEGORY);
  const [caseFileTypeOptions, setCaseFileTypeOptions] = useState<{value:string;label:string}[]>([{value:DEFAULT_CASE_ATTACHMENT_CATEGORY,label:DEFAULT_CASE_ATTACHMENT_CATEGORY}]);
  const [courtOptions, setCourtOptions] = useState<{value:string;label:string;code?:string}[]>([]);
  const [courtOfficerOptions, setCourtOfficerOptions] = useState<{value:string;label:string;court_code?:string;role?:string;phone?:string}[]>([]);
  const caseUploadRef = useRef<HTMLInputElement>(null);
  const counselDetailUploadRef = useRef<HTMLInputElement>(null);
  const [createForm] = Form.useForm();
  const createCustomer = Form.useWatch("customer", createForm);
  const createContractId = Form.useWatch("contract_record_id", createForm);
  const selectedCreateContract = useMemo(() => contracts.find((row) => row.id === createContractId), [contracts, createContractId]);
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
  const [progressForm] = Form.useForm();
  const [counselEditForm] = Form.useForm();
  const [normalCaseEditForm] = Form.useForm();
  const [arbitrationBasicForm] = Form.useForm();
  const [criminalMaintenanceForm] = Form.useForm();
  const [caseQueryForm] = Form.useForm();
  const [refundCompleteForm] = Form.useForm();
  const [reminderForm] = Form.useForm();
  const [caseLogForm] = Form.useForm();
  const [attachmentRenameForm] = Form.useForm();
  const [caseFileSealForm] = Form.useForm();
  const [batchUpdateForm] = Form.useForm();
  const [batchFeeForm] = Form.useForm();
  const [mergeCaseForm] = Form.useForm();
  const [notaryInfoForm] = Form.useForm();
  const [settlementAmountForm] = Form.useForm();
  const batchExpenseScope = Form.useWatch("expense_scope", batchFeeForm);
  const feeExpenseScope = Form.useWatch("expense_scope", feeForm);
  const getCaseCapability = (row?: CaseRow | null) => row ? caseActionCapabilities[row.id] || noCaseDetailWriteCapability : noCaseDetailWriteCapability;
  const loadCaseCapabilities = async (rows: CaseRow[]) => {
    const uniqueRows = Array.from(new Map(rows.map((row) => [row.id, row])).values());
    const results = await Promise.all(uniqueRows.map(async (row) => {
      try {
        const { data } = await api.get(`/cases/${row.id}/action-capabilities`);
        return [row.id, data as CaseDetailCapabilities] as const;
      } catch {
        return [row.id, noCaseDetailWriteCapability] as const;
      }
    }));
    setCaseActionCapabilities((previous) => ({ ...previous, ...Object.fromEntries(results) }));
  };
  const load = async () => {
    setLoading(true);
    try {
      // 关联详情不能依赖合同、排期、附件等旁路数据全部成功；否则案号跳转会
      // 只进入案件列表而没有打开目标详情。
      const caseRes = await api.get("/records", { params: { module: "case", page_size: 100 } });
      setCases(caseRes.data.items);
      void loadCaseCapabilities(caseRes.data.items as CaseRow[]);
      const detailTarget = consumeCaseDetailTarget();
      if (detailTarget && !isCreateView) {
        let linkedCase = (caseRes.data.items as CaseRow[]).find((row) =>
          (detailTarget.id && row.id === detailTarget.id) ||
          (detailTarget.serial_no && row.serial_no === detailTarget.serial_no),
        );
        if (!linkedCase && detailTarget.serial_no) {
          const { data } = await api.get("/records", {
            params: { module: "case", keyword: detailTarget.serial_no, page_size: 100 },
          });
          linkedCase = (data.items as CaseRow[]).find((row) => row.serial_no === detailTarget.serial_no);
        }
        if (linkedCase) void openCounselDetail(linkedCase);
        else message.warning("未找到关联案件或当前账号无权查看");
      } else if (isCaseDetailView && detailRouteId > 0) {
        let linkedCase = (caseRes.data.items as CaseRow[]).find((row) => row.id === detailRouteId);
        if (!linkedCase) {
          try {
            const { data } = await api.get(`/records/${detailRouteId}`);
            if (data.module === "case") linkedCase = data as CaseRow;
          } catch {
            // The common detail loader below provides the user-facing error.
          }
        }
        if (linkedCase) void openCounselDetail(linkedCase);
        else message.warning("未找到关联案件或当前账号无权查看");
      }
      const [contractRes, hearingRes, summaryRes, profileRes,financeRes,refundRes,attachmentRes,referenceRes,customerRes,clueRes] =
        await Promise.all([
          api.get("/cases/eligible-contracts"),
          api.get("/hearings"),
          api.get("/cases/summary"),
          api.get("/auth/me"),
          api.get("/records",{params:{module:"finance",page_size:100}}),
          api.get("/records",{params:{module:"refund",page_size:100}}),
          api.get("/attachments"),
          api.get("/cases/reference-options"),
          api.get("/records", { params: { module: "customer", page_size: 100 } }),
          api.get("/records", { params: { module: "clue", page_size: 100 } }),
        ]);
      setContracts(contractRes.data.items);
      setHearings(hearingRes.data.items);
      setSummary(summaryRes.data);
      setProfile(profileRes.data);
      setFinanceRows([...financeRes.data.items,...refundRes.data.items]);
      setAttachments(attachmentRes.data.items);
      setCaseTypeOptions(referenceRes.data.case_types || []);
      setCauseOptions(referenceRes.data.causes || []);
      if ((referenceRes.data.case_file_types || []).length) {
        const nextFileTypes = referenceRes.data.case_file_types;
        setCaseFileTypeOptions(nextFileTypes);
        setCaseUploadCategory((current) => nextFileTypes.some((item:{value:string}) => item.value === current) ? current : nextFileTypes[0].value);
        setCounselUploadCategory((current) => nextFileTypes.some((item:{value:string}) => item.value === current) ? current : nextFileTypes[0].value);
      }
      setCourtOptions(referenceRes.data.courts || []);
      setCourtOfficerOptions(referenceRes.data.court_officers || []);
      setCaseLawyerOptions(referenceRes.data.case_lawyers || []);
      setCaseAssistantOptions(referenceRes.data.case_assistants || []);
      setRightTypeOptions((referenceRes.data.right_types || []).map((value:string)=>({value,label:value})));
      setCaseCustomers(customerRes.data.items || []);
      setCaseClues(clueRes.data.items || []);
      if (isCreateView && contractPrefill?.id) {
        const selected = contractRes.data.items.find((row:ContractRow) => row.id === contractPrefill.id);
        if (selected) createForm.setFieldsValue({customer:selected.customer,source_person:selected.data?.source_person||selected.owner});
      }
    } catch {
      message.error("案件中心数据加载失败");
    } finally {
      setLoading(false);
    }
  };
  const counselScope = initialView.startsWith("case-mine") ? "mine" : initialView.startsWith("case-dept") ? "department" : "company";
  const counselSearchPayload = (values:Record<string,any>, page:number, pageSize:number, extra:Record<string,any>={}) => ({
    scope: counselScope,
    customer: values.customer || "",
    serial_no: values.serial_no || "",
    keyword: values.keyword || "",
    counsel_start: values.counsel_range?.[0]?.format("YYYY-MM-DD") || null,
    counsel_end: values.counsel_range?.[1]?.format("YYYY-MM-DD") || null,
    counsel_type: values.counsel_type || "",
    case_status: values.status || "",
    handling_lawyer: values.handling_lawyer || "",
    assistant: values.assistant || "",
    document_name: values.document_name || "",
    sort_order: values.sort_order || "updated_desc",
    page,
    page_size: pageSize,
    ...extra,
  });
  const loadCounselCases = async (values:Record<string,any>=caseQuery, page=1, pageSize=counselPageSize) => {
    setLoading(true);
    try {
      const { data } = await api.post("/cases/counsel/search", counselSearchPayload(values,page,pageSize));
      setCounselCases(data.items || []);
      void loadCaseCapabilities(data.items || []);
      setCounselTotal(data.total || 0);
      setCounselPage(data.page || page);
      setCounselPageSize(data.page_size || pageSize);
      setSelectedCaseKeys([]);
    } catch (error:any) {
      message.error(error?.response?.data?.detail || "法律顾问案件加载失败");
    } finally {
      setLoading(false);
    }
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
      handling_lawyers: [],
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
    const relationTarget = consumeCustomerRelationTarget();
    const relationQuery = relationTarget?.target === "civil-cases" ? { customer: relationTarget.title || relationTarget.serial_no || "" } : {};
    if (relationQuery.customer) {
      caseQueryForm.setFieldsValue(relationQuery);
      setCaseQuery(relationQuery);
    }
    load();
    if (!isCreateView && initialView.includes("counsel")) void loadCounselCases(relationQuery,1,10);
  }, [initialView]);
  const advanceCreateStep = async () => {
    if (createStep === 0) {
      const values = createForm.getFieldsValue(true);
      const warning = !values.customer
        ? "请选择客户."
        : !values.contract_record_id
          ? "请选择合同."
          : isCounselCreate && !String(values.counsel_type || "").trim()
            ? "请输入顾问类型."
            : isCounselCreate && (!values.counsel_range?.[0] || !values.counsel_range?.[1])
              ? "请选择顾问期限."
              : !isCounselCreate && !String(values.cause_or_charge || "").trim()
            ? "请输入案由."
            : !String(values.title || "").trim()
              ? "请输入案件名称."
              : !(values.handling_lawyers || []).length
                ? "请按顺序录入经办律师."
                : "";
      if (warning) {
        Modal.info({ title: "提示", content: warning, okText: "确定" });
        return;
      }
      setCreateSubmitting(true);
      try {
        const response = await api.post("/cases", {
          contract_record_id: values.contract_record_id,
          title: String(values.title || "").trim(),
          status: "新案待分配",
          owner: values.owner || profile.username || "admin",
          case_type: values.case_type || createRouteType,
          client_position: isCounselCreate ? "" : values.client_position || "",
          cause_or_charge: isCounselCreate ? "" : String(values.cause_or_charge || "").trim(),
          right_type: isCounselCreate ? "" : String(values.right_type || "").trim(),
          source_person: String(values.source_person || "").trim(),
          counsel_type: isCounselCreate ? String(values.counsel_type || "").trim() : "",
          counsel_start: isCounselCreate ? values.counsel_range[0].format("YYYY-MM-DD") : null,
          counsel_end: isCounselCreate ? values.counsel_range[1].format("YYYY-MM-DD") : null,
          handling_lawyers: values.handling_lawyers || [],
          assistant: values.assistant || "",
        });
        const newCaseId = Number(response.data?.id);
        if (!Number.isInteger(newCaseId) || newCaseId <= 0) {
          throw new Error("案件创建接口没有返回有效案件 ID");
        }
        setCreatedCaseId(newCaseId);
        const customer = String(values.customer || "").trim();
        const customerIsDefendant = ["被告人/犯罪嫌疑人", "被告/被申请人"].includes(values.client_position);
        const customerIsThirdParty = values.client_position === "第三人";
        createForm.setFieldsValue({
          plaintiffs: !isCounselCreate && customer && !customerIsDefendant && !customerIsThirdParty ? [customer] : [],
          plaintiff_agents: [],
          defendants: customer && customerIsDefendant ? [customer] : [],
          defendant_agents: [],
          third_parties: customer && customerIsThirdParty ? [customer] : [],
          third_party_agents: [],
          litigant_comment: "",
        });
        setCreateStep(1);
      } catch (error: any) {
        message.error(error?.response?.data?.detail || error?.message || "案件创建失败");
      } finally {
        setCreateSubmitting(false);
      }
      return;
    }
    if (!createdCaseId) {
      message.error("案件尚未创建，请重新进入新建案件页面");
      return;
    }
    await saveLitigants(false);
  };
  const redirectAfterCreate = () => {
    const params = new URLSearchParams(window.location.search);
    params.set("page", createRedirectPage);
    window.location.search = params.toString();
  };
  const saveLitigants = async (complete: boolean) => {
    if (!createdCaseId) {
      message.error("案件尚未创建，请重新进入新建案件页面");
      return;
    }
    const values = createForm.getFieldsValue(true);
    setCreateSubmitting(true);
    try {
      await api.put(`/cases/${createdCaseId}/litigants`, {
        plaintiffs: values.plaintiffs || [],
        plaintiff_agents: values.plaintiff_agents || [],
        defendants: values.defendants || [],
        defendant_agents: values.defendant_agents || [],
        third_parties: values.third_parties || [],
        third_party_agents: values.third_party_agents || [],
        comment: values.litigant_comment || "",
      });
      if (complete) {
        if (isCounselCreate) {
          await api.put(`/cases/${createdCaseId}/complete-creation`, { comment: values.litigant_comment || "" });
        } else {
          await api.put(`/cases/${createdCaseId}/judicial`, {});
        }
        message.success("案件信息已完成");
        redirectAfterCreate();
      } else {
        setCreateStep(2);
      }
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "当事人信息保存失败");
    } finally {
      setCreateSubmitting(false);
    }
  };
  const finishCreateFlow = async () => {
    if (!createdCaseId) {
      message.error("案件尚未创建，请重新进入新建案件页面");
      return;
    }
    const values = createForm.getFieldsValue(true);
    setCreateSubmitting(true);
    try {
      await api.put(`/cases/${createdCaseId}/judicial`, {
        court: values.court || "",
        court_case_no: values.court_case_no || "",
        judge: values.judge || "",
        judge_phone: values.judge_phone || "",
        filing_date: values.filing_date?.format("YYYY-MM-DD") || null,
        hearing_date: values.hearing_date?.format("YYYY-MM-DD") || null,
        hearing_time: values.hearing_time?.format("HH:mm") || "",
        courtroom: values.courtroom || "",
        judicial_remark: values.judicial_remark || "",
        description: values.description || "",
        public_security_name: values.public_security_name || "",
        public_security_case_no: values.public_security_case_no || "",
        public_security_address: values.public_security_address || "",
        public_security_phone: values.public_security_phone || "",
        public_security_operator: values.public_security_operator || "",
        first_procuratorate_name: values.first_procuratorate_name || "",
        first_procuratorate_case_no: values.first_procuratorate_case_no || "",
        first_procuratorate_address: values.first_procuratorate_address || "",
        first_procuratorate_phone: values.first_procuratorate_phone || "",
        first_procuratorate_operator: values.first_procuratorate_operator || "",
        second_procuratorate_name: values.second_procuratorate_name || "",
        second_procuratorate_case_no: values.second_procuratorate_case_no || "",
        second_procuratorate_address: values.second_procuratorate_address || "",
        second_procuratorate_phone: values.second_procuratorate_phone || "",
        second_procuratorate_operator: values.second_procuratorate_operator || "",
        retrial_procuratorate_name: values.retrial_procuratorate_name || "",
        retrial_procuratorate_case_no: values.retrial_procuratorate_case_no || "",
        retrial_procuratorate_address: values.retrial_procuratorate_address || "",
        retrial_procuratorate_phone: values.retrial_procuratorate_phone || "",
        retrial_procuratorate_operator: values.retrial_procuratorate_operator || "",
        first_court_enabled: Boolean(values.first_court_enabled),
        first_court_name: values.first_court_name || "",
        first_court_case_no: values.first_court_case_no || "",
        first_court_courtroom: values.first_court_courtroom || "",
        first_court_judge: values.first_court_judge || "",
        first_court_clerk: values.first_court_clerk || "",
        first_court_filing_date: values.first_court_filing_date?.format("YYYY-MM-DD") || null,
        first_court_hearing_date: values.first_court_hearing_date?.format("YYYY-MM-DD") || null,
        second_court_enabled: Boolean(values.second_court_enabled),
        second_court_name: values.second_court_name || "",
        second_court_case_no: values.second_court_case_no || "",
        second_court_courtroom: values.second_court_courtroom || "",
        second_court_judge: values.second_court_judge || "",
        second_court_clerk: values.second_court_clerk || "",
        second_court_filing_date: values.second_court_filing_date?.format("YYYY-MM-DD") || null,
        second_court_hearing_date: values.second_court_hearing_date?.format("YYYY-MM-DD") || null,
        retrial_court_enabled: Boolean(values.retrial_court_enabled),
        retrial_court_name: values.retrial_court_name || "",
        retrial_court_case_no: values.retrial_court_case_no || "",
        retrial_court_courtroom: values.retrial_court_courtroom || "",
        retrial_court_judge: values.retrial_court_judge || "",
        retrial_court_clerk: values.retrial_court_clerk || "",
        retrial_court_filing_date: values.retrial_court_filing_date?.format("YYYY-MM-DD") || null,
        retrial_court_hearing_date: values.retrial_court_hearing_date?.format("YYYY-MM-DD") || null,
      });
      message.success("案件信息已完成");
      redirectAfterCreate();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "司法机关信息保存失败");
    } finally {
      setCreateSubmitting(false);
    }
  };
  const assign = async () => {
    if (!assigning) return;
    const v = await assignForm.validateFields();
    try {
      await api.post(`/cases/${assigning.id}/assign`, v);
      message.success("案件人员分配成功");
      setAssigning(null);
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "分配失败");
    }
  };
  const createHearing = async () => {
    const v = await hearingForm.validateFields();
    try {
      await api.post("/hearings", {
        ...v,
        hearing_date: formatRequiredDate(v.hearing_date, "开庭日期"),
        hearing_time: formatRequiredDate(v.hearing_time, "开庭时间", "HH:mm"),
      });
      message.success("开庭排期已创建");
      setHearingOpen(false);
      hearingForm.resetFields();
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "排期失败");
    }
  };
  const openArchive = async (row: CaseRow) => {
    if (!getCaseCapability(row).can_archive) return message.warning("当前账号没有案件归档权限");
    try {
      const { data } = await api.get(`/cases/${row.id}/archive-readiness`);
      archiveForm.setFieldsValue({
        ...data.checks,
        archive_no: data.archive_no,
        paper_archive_location: data.paper_archive_location,
        paper_volume_count: data.paper_volume_count || 1,
        comment: "",
      });
      setArchiveChecks(data.checks || {});
      setArchiving(row);
    } catch {
      message.error("归档检查加载失败");
    }
  };
  const closeCase = async () => {
    if (!archiving) return;
    try {
      await api.post(`/cases/${archiving.id}/close`, { comment: "归档前确认案件已经办结" });
      message.success("案件办结已由系统记录");
      await openArchive(archiving);
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "案件办结失败");
    }
  };
  const archive = async (submit: boolean) => {
    if (!archiving) return;
    const v = await archiveForm.validateFields();
    try {
      await api.post(`/cases/${archiving.id}/archive`, { ...v, submit });
      message.success(submit ? "已提交归档审核" : "归档检查已保存");
      setArchiving(null);
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "归档操作失败");
    }
  };
  const reviewArchive = async () => {
    if (!reviewing) return;
    const v = await reviewForm.validateFields();
    try {
      await api.post(`/cases/${reviewing.row.id}/archive/review`, {
        approved: reviewing.approved,
        comment: v.comment,
      });
      message.success(reviewing.approved ? "归档审核已通过" : "归档审核已驳回");
      setReviewing(null);
      reviewForm.resetFields();
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "归档审核失败");
    }
  };
  const reviewCaseCreation = async (row: CaseRow, approved: boolean) => {
    try {
      await api.post(`/cases/${row.id}/creation/review`, { approved, comment: approved ? "案件资料完整，同意立案" : "案件资料不完整，请补充后重新提交" });
      message.success(approved ? "立案审批已通过，固定任务已生成" : "立案审批已驳回");
      setSelectedCaseKeys([]);
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "立案审批失败");
    }
  };
  const requestUnarchive = (row: CaseRow) => {
    let reason = "";
    Modal.confirm({
      title: `申请解档：${row.serial_no}`,
      content: <Input.TextArea rows={4} placeholder="请填写必须解档修改的具体原因" onChange={(event) => { reason = event.target.value; }} />,
      okText: "提交审批",
      cancelText: "取消",
      onOk: async () => {
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
  const reviewUnarchive = async (row: CaseRow, approved: boolean) => {
    try {
      await api.post(`/cases/${row.id}/unarchive/review`, { approved, comment: approved ? "同意解档并恢复办理" : "不同意解档" });
      message.success(approved ? "解档审批已通过" : "解档审批已驳回");
      setSelectedCaseKeys([]);
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "解档审批失败");
    }
  };
  const openAssign = (row: CaseRow) => {
    if (!getCaseCapability(row).can_assign_team) return message.warning("当前账号没有案件人员分配权限");
    setAssigning(row);
    assignForm.setFieldsValue({
      customer_manager: row.data.customer_manager || "",
      hearing_lawyer: row.data.hearing_lawyer || "",
      handling_lawyers: row.data.handling_lawyers || [],
      assistant: row.data.assistant || "",
    });
  };
  const openCaseTasks = async (row: CaseRow) => {
    try {
      const { data } = await api.get(`/cases/${row.id}/tasks`);
      setCaseTasks(data.items);
      taskForm.resetFields();
      taskForm.setFieldsValue({
        owner: profile.username || row.owner,
        deadline: undefined,
        priority: "普通",
        collaborators: [],
      });
      setTaskCase(row);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "案件任务加载失败");
    }
  };
  const openCounselDetail = async (row: CaseRow) => {
    if (!isCaseDetailView) {
      const serialNo = String(row.serial_no || `案件-${row.id}`).trim();
      rememberCaseDetailTarget({ id: row.id, serial_no: serialNo });
      onNavigate?.(`case-detail-${row.id}-${encodeURIComponent(serialNo)}`);
      return;
    }
    try {
      // 基础案件详情必须先打开；历史、附件、提醒等附加面板不能因为单点失败
      // 阻断案号关联、搜索或通知进入详情。
      const recordRes = await api.get(`/records/${row.id}`);
      setViewingCounselCase(recordRes.data);
      document.querySelector<HTMLElement>(".content")?.scrollTo({top:0,left:0});
      setSelectedCounselAttachmentKeys([]);
      setActiveCounselDocCategory("");
      const [historyRes, taskRes, attachmentRes, reminderRes, logRes, capabilityRes] = await Promise.allSettled([
        api.get(`/records/${row.id}/history`),
        api.get(`/cases/${row.id}/tasks`),
        api.get("/attachments", { params: { record_id: row.id } }),
        api.get(`/cases/${row.id}/reminders`),
        api.get(`/cases/${row.id}/logs`),
        api.get(`/cases/${row.id}/action-capabilities`),
      ]);
      setCounselDetailHistory(historyRes.status === "fulfilled" ? historyRes.value.data.items || [] : []);
      setCounselDetailTasks(taskRes.status === "fulfilled" ? taskRes.value.data.items || [] : []);
      setCounselDetailAttachments(attachmentRes.status === "fulfilled" ? attachmentRes.value.data.items || [] : []);
      setCounselReminders(reminderRes.status === "fulfilled" ? reminderRes.value.data.items || [] : []);
      setCounselLogs(logRes.status === "fulfilled" ? logRes.value.data.items || [] : []);
      setCounselDetailCapabilities(capabilityRes.status === "fulfilled" ? capabilityRes.value.data || noCaseDetailWriteCapability : noCaseDetailWriteCapability);
      if ([historyRes, taskRes, attachmentRes, reminderRes, logRes, capabilityRes].some((result) => result.status === "rejected")) {
        message.warning("部分案件附加信息加载失败，已打开基础详情");
      }
    } catch (error: any) {
      setCounselDetailCapabilities(noCaseDetailWriteCapability);
      message.error(error?.response?.data?.detail || "案件详情加载失败");
    }
  };
  const duplicateCase = async (row: CaseRow) => {
    try {
      const { data } = await api.post(`/cases/${row.id}/duplicate`);
      message.success(`已复制为新案件：${data.serial_no}`);
      await openCounselDetail(data);
      void load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "案件复制失败");
    }
  };
  const submitCaseMerge = async () => {
    if (!mergingCase) return;
    try {
      const values = await mergeCaseForm.validateFields();
      const { data } = await api.post(`/cases/${mergingCase.id}/merge`, values);
      message.success(`已合并案件 ${data.source.serial_no}：迁移费用 ${data.moved_fees} 条、案件文件 ${data.moved_attachments} 个`);
      setMergingCase(null);
      mergeCaseForm.resetFields();
      await openCounselDetail(data.target);
      void load();
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(error?.response?.data?.detail || "案件合并失败");
    }
  };
  const submitNotaryInfo = async () => {
    if (!notaryInfoCase) return;
    try {
      const values = await notaryInfoForm.validateFields();
      const { data } = await api.put(`/cases/${notaryInfoCase.id}/notary-info`, values);
      message.success("公证信息已更新");
      setNotaryInfoCase(null); notaryInfoForm.resetFields(); await openCounselDetail(data); void load();
    } catch (error: any) { if (!error?.errorFields) message.error(error?.response?.data?.detail || "公证信息更新失败"); }
  };
  const submitSettlementAmount = async () => {
    if (!settlementAmountCase) return;
    try {
      const values = await settlementAmountForm.validateFields();
      const { data } = await api.put(`/cases/${settlementAmountCase.id}/settlement-amount`, values);
      message.success("诉讼或判决金额已更新");
      setSettlementAmountCase(null); settlementAmountForm.resetFields(); await openCounselDetail(data); void load();
    } catch (error: any) { if (!error?.errorFields) message.error(error?.response?.data?.detail || "金额更新失败"); }
  };
  const openRelatedCustomer = async (target: { id?: number; serial_no?: string; title?: string; customer?: string }) => {
    const title = String(target.title || target.customer || "").trim();
    if (!title && !target.id && !target.serial_no) {
      message.warning("当前记录未关联客户");
      return;
    }
    const customer = await resolveCustomerDetailTarget({ id: target.id, serial_no: target.serial_no, title });
    if (!customer) {
      message.warning("未找到关联客户或当前账号无权查看");
      return;
    }
    rememberCustomerDetailTarget(customer);
    onNavigate?.("customer-company");
  };
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
    if (!rememberTaskDetailTarget({ id: task.id, serial_no: task.serial_no })) {
      message.warning("当前案件任务未生成可查看编号");
      return;
    }
    const route = task.initiator === profile.username
      ? "task-my-created"
      : task.owner === profile.username
        ? "task-my-accepted"
        : task.collaborators?.includes(profile.username)
          ? "task-my-collaborating"
          : profile.role === "admin"
            ? "task-company-accepted"
            : "task-my-accepted";
    onNavigate?.(route);
  };
  const openRelatedFee = async (fee: CaseRow) => {
    if (!fee.id) {
      message.warning("当前费用记录不存在或无权查看");
      return;
    }
    try {
      const { data } = await api.get(`/records/${fee.id}`);
      if (data.module !== "finance") throw new Error("关联记录不是费用申请");
      if (!rememberBusinessRecordDetailTarget({ id: data.id, module: "finance" })) {
        message.warning("当前费用记录不存在或无权查看");
        return;
      }
      onNavigate?.("finance-fee-query");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || error?.message || "费用记录不存在或无权查看");
    }
  };
  const openRelatedClue = (target: { id?: number; serial_no?: unknown }) => {
    const id = Number(target.id || 0) || undefined;
    const serialNo = String(target.serial_no || "").trim();
    if (!rememberInvestigationDetailTarget({ id, serial_no: serialNo || undefined, module: "clue" })) {
      message.warning("当前案件未关联调查线索");
      return;
    }
    onNavigate?.("clue-company-draft");
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
  const resolveVisibleCase = async (row: { case?: CaseRow; case_record_id?: number; serial_no?: string; case_no?: string }) => {
    if (row.case?.id) return row.case;
    const caseRecordId = Number(row.case_record_id || 0);
    try {
      if (caseRecordId > 0) {
        const { data } = await api.get(`/records/${caseRecordId}`);
        if (data.module !== "case") throw new Error("关联记录不是案件");
        return data as CaseRow;
      }
      const caseNo = String(row.case_no || row.serial_no || "").trim();
      if (!caseNo) return null;
      const cached = cases.find((item) => item.serial_no === caseNo);
      if (cached) return cached;
      const { data } = await api.get("/records", { params: { module: "case", keyword: caseNo, page_size: 100 } });
      return (data.items as CaseRow[]).find((item) => item.serial_no === caseNo) || null;
    } catch (error: any) {
      const detail = error?.response?.data?.detail;
      message.warning(detail || "关联案件不存在或当前账号无权查看");
      return null;
    }
  };
  const openSpecialCaseDetail = async (row: { case?: CaseRow; case_record_id?: number; serial_no?: string; case_no?: string }) => {
    const target = await resolveVisibleCase(row);
    if (!target) {
      if (!row.case_record_id && !row.case_no && !row.serial_no) message.warning("当前记录未关联案件");
      return;
    }
    await openCounselDetail(target);
  };
  const openSpecialCaseTasks = async (row: { case?: CaseRow; case_record_id?: number; serial_no?: string; case_no?: string }) => {
    const target = await resolveVisibleCase(row);
    if (!target) return;
    await openCaseTasks(target);
  };
  const createCounselReminder = async () => {
    if (!viewingCounselCase) return;
    const values = await reminderForm.validateFields();
    try {
      await api.post(`/cases/${viewingCounselCase.id}/reminders`, {
        reminder_date: formatRequiredDate(values.reminder_date, "提醒日期"),
        deadline: formatRequiredDate(values.deadline, "截止日期"),
        content: values.content.trim(),
      });
      message.success("案件提醒已创建");
      setReminderOpen(false);
      reminderForm.resetFields();
      await openCounselDetail(viewingCounselCase);
    } catch (error:any) { message.error(error?.response?.data?.detail || "案件提醒创建失败"); }
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
  const createCounselLog = async () => {
    if (!viewingCounselCase) return;
    const values = await caseLogForm.validateFields();
    try {
      await api.post(`/cases/${viewingCounselCase.id}/logs`,{content:values.content.trim()});
      message.success("案件日志已保存");
      setCaseLogOpen(false);
      caseLogForm.resetFields();
      await openCounselDetail(viewingCounselCase);
    } catch(error:any){message.error(error?.response?.data?.detail||"案件日志保存失败");}
  };
  const submitCounselBatchUpdate = async () => {
    const values=await batchUpdateForm.validateFields();
    const caseIds=selectedCaseKeys.map(Number);
    if(!caseIds.length)return message.warning("请选择需要修改的法律顾问案件");
    const payload:any={case_ids:caseIds,comment:values.comment||""};
    if(values.handling_lawyers!==undefined)payload.handling_lawyers=values.handling_lawyers;
    if(values.assistant!==undefined)payload.assistant=values.assistant;
    if(values.case_stage!==undefined)payload.case_stage=values.case_stage;
    if(payload.handling_lawyers===undefined&&payload.assistant===undefined&&payload.case_stage===undefined)return message.warning("请至少填写一个需要修改的字段");
    try{
      const {data}=await api.post("/cases/batch-update",payload);
      message.success(`已修改 ${data.updated} 个案件`);setBatchUpdateOpen(false);batchUpdateForm.resetFields();
      await loadCounselCases(caseQuery,counselPage,counselPageSize);
    }catch(error:any){message.error(error?.response?.data?.detail||"批量修改失败");}
  };
  const submitCounselBatchFee = async () => {
    const values=await batchFeeForm.validateFields();
    const caseIds=selectedCaseKeys.map(Number);
    if(!caseIds.length)return message.warning("请选择需要新增费用的法律顾问案件");
    try{
      const {data}=await api.post("/cases/batch-fees",{case_ids:caseIds,amount:values.amount,expense_scope:values.expense_scope,expense_subtype:values.expense_subtype,handler:values.handler||profile.username,description:values.description||""});
      message.success(`已为 ${data.created} 个案件创建费用草稿`);setBatchFeeOpen(false);batchFeeForm.resetFields();await load();
    }catch(error:any){message.error(error?.response?.data?.detail||"批量新增费用失败");}
  };
  const downloadCounselAttachments = async () => {
    if(!selectedCounselAttachmentKeys.length)return message.warning("请选择需要下载的案件文件");
    try{
      const response=await api.post("/cases/attachments/download",{attachment_ids:selectedCounselAttachmentKeys.map(Number)},{responseType:"blob"});
      const url=URL.createObjectURL(response.data),link=document.createElement("a");link.href=url;link.download="案件文件.zip";link.click();URL.revokeObjectURL(url);
    }catch(error:any){message.error(error?.response?.data?.detail||"案件文件下载失败");}
  };
  const generateCaseDocument = async (documentType: string) => {
    if (!viewingCounselCase) return;
    try {
      const { data } = await api.post(`/cases/${viewingCounselCase.id}/documents/${documentType}`);
      message.success("案件文书已生成并归入案件附件");
      setAttachments((current) => [data, ...current.filter((item) => item.id !== data.id)]);
      await openCounselDetail(viewingCounselCase);
    } catch (error: any) { message.error(error?.response?.data?.detail || "案件文书生成失败"); }
  };
  const openCounselAttachmentSeal = async (item: AttachmentRow) => {
    if (!viewingCounselCase) return;
    try {
      const { data } = await api.get("/seals/assets");
      const available = (data.items || []).filter((asset: { status: string }) => asset.status === "可用");
      setCaseSealAssets(available);
      caseFileSealForm.setFieldsValue({ seal_asset_id: undefined, print_quantity: 2, is_electronic_seal: false, is_offline_print: true, need_audit: true, remark: "" });
      setSealingCounselAttachment(item);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "可用印章加载失败");
    }
  };
  const submitCounselAttachmentSeal = async () => {
    if (!viewingCounselCase || !sealingCounselAttachment) return;
    try {
      const values = await caseFileSealForm.validateFields();
      await api.post("/official-outgoing", {
        title: sealingCounselAttachment.original_name,
        source_type: "case",
        source_record_id: viewingCounselCase.id,
        source_file_ids: [sealingCounselAttachment.id],
        seal_asset_id: values.seal_asset_id,
        print_quantity: values.print_quantity,
        is_electronic_seal: Boolean(values.is_electronic_seal),
        is_offline_print: Boolean(values.is_offline_print),
        need_audit: Boolean(values.need_audit),
        remark: String(values.remark || "").trim(),
      });
      message.success("已创建正式发文草稿，可在正式发文继续提交审批");
      setSealingCounselAttachment(null);
      caseFileSealForm.resetFields();
      await openCounselDetail(viewingCounselCase);
    } catch (error: any) {
      if (!error?.errorFields) message.error(error?.response?.data?.detail || "提交用印失败");
    }
  };
  const uploadCounselDetailAttachment = async (file?: File) => {
    if (!file || !viewingCounselCase) return message.warning("请先打开案件详情再上传文件");
    const data = new FormData();
    data.append("file", file);
    data.append("record_id", String(viewingCounselCase.id));
    data.append("category", counselUploadCategory || DEFAULT_CASE_ATTACHMENT_CATEGORY);
    data.append("remark", `案件详情文档：${counselUploadCategory || DEFAULT_CASE_ATTACHMENT_CATEGORY}`);
    try {
      await api.post("/attachments", data);
      message.success("案件文件已上传");
      await openCounselDetail(viewingCounselCase);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "案件文件上传失败");
    } finally {
      if (counselDetailUploadRef.current) counselDetailUploadRef.current.value = "";
    }
  };
  const downloadCounselDetailAttachment = async (item: AttachmentRow) => {
    try {
      const response = await api.get(`/attachments/${item.id}/download`, { responseType: "blob" });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = item.original_name;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "案件文件下载失败");
    }
  };
  const previewCounselDetailAttachment = async (item: AttachmentRow) => {
    try {
      const { data } = await api.get(`/attachments/${item.id}/preview`);
      if (data.kind === "unsupported") {
        message.info(data.detail || "当前文件格式暂不支持在线预览，请下载后查看");
        return;
      }
      if (data.kind === "pdf" || data.kind === "image") {
        const response = await api.get(`/attachments/${item.id}/download`, { responseType: "blob" });
        setAttachmentPreview({ name: item.original_name, kind: data.kind, url: URL.createObjectURL(response.data) });
        return;
      }
      setAttachmentPreview({ name: item.original_name, kind: data.kind, text: data.text || "" });
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "案件文件预览失败");
    }
  };
  const closeAttachmentPreview = () => {
    if (attachmentPreview?.url) URL.revokeObjectURL(attachmentPreview.url);
    setAttachmentPreview(null);
  };
  const deleteCounselAttachments = () => {
    if(!viewingCounselCase||!selectedCounselAttachmentKeys.length)return message.warning("请选择需要删除的案件文件");
    Modal.confirm({title:"批量删除案件文件",content:`确认删除选中的 ${selectedCounselAttachmentKeys.length} 个文件吗？该操作会记录审计日志。`,okText:"删除",okButtonProps:{danger:true},onOk:async()=>{
      try{
        const {data}=await api.post("/cases/attachments/delete",{attachment_ids:selectedCounselAttachmentKeys.map(Number)});message.success(`已删除 ${data.deleted} 个文件`);await openCounselDetail(viewingCounselCase);
      }catch(error:any){message.error(error?.response?.data?.detail||"案件文件删除失败");}
    }});
  };
  const openCounselAttachmentRename = (item: AttachmentRow) => {
    attachmentRenameForm.setFieldsValue({ original_name: item.original_name });
    setRenamingCounselAttachment(item);
  };
  const renameCounselAttachment = async () => {
    if (!renamingCounselAttachment || !viewingCounselCase) return;
    const values = await attachmentRenameForm.validateFields();
    try {
      await api.put(`/cases/attachments/${renamingCounselAttachment.id}/rename`, { original_name: values.original_name.trim() });
      message.success("案件文件已重命名");
      setRenamingCounselAttachment(null);
      attachmentRenameForm.resetFields();
      await openCounselDetail(viewingCounselCase);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "案件文件重命名失败");
    }
  };
  const selectCounselDocCategory = (category: string) => {
    setActiveCounselDocCategory(category);
    setCounselUploadCategory(caseFileTypeOptions.some((item) => item.value === category) ? category : DEFAULT_CASE_ATTACHMENT_CATEGORY);
    setSelectedCounselAttachmentKeys([]);
  };
  const openCounselEdit = (row: CaseRow) => {
    if (!getCaseCapability(row).can_edit_basic) return message.warning("当前账号没有修改案件基本信息权限");
    counselEditForm.setFieldsValue({
      title: row.title,
      customer: row.customer,
      counsel_type: row.data.counsel_type || "",
      counsel_range: row.data.counsel_start && row.data.counsel_end ? [dayjs(row.data.counsel_start), dayjs(row.data.counsel_end)] : undefined,
      handling_lawyers: row.data.handling_lawyers || [],
      assistant: row.data.assistant || "",
      comment: "",
    });
    setEditingCounselCase(row);
  };
  const saveCounselBasic = async () => {
    if (!editingCounselCase) return;
    const values = await counselEditForm.validateFields();
    try {
      const { data } = await api.put(`/cases/${editingCounselCase.id}/counsel-basic`, {
        title: values.title.trim(),
        counsel_type: values.counsel_type.trim(),
        counsel_start: values.counsel_range[0].format("YYYY-MM-DD"),
        counsel_end: values.counsel_range[1].format("YYYY-MM-DD"),
        handling_lawyers: values.handling_lawyers || [],
        assistant: values.assistant || "",
        comment: values.comment || "",
      });
      message.success("法律顾问案件基本信息已保存");
      setEditingCounselCase(null);
      setViewingCounselCase(data);
      await load();
      await loadCounselCases(caseQuery,counselPage,counselPageSize);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "法律顾问案件基本信息保存失败");
    }
  };
  const isNormalEditableCase = (row: CaseRow) => ["民事案件", "刑事案件", "行政案件及国家赔偿"].includes(String(row.data.case_type || ""));
  const openNormalCaseEdit = (row: CaseRow) => {
    if (!getCaseCapability(row).can_edit_basic) return message.warning("当前账号没有修改案件基本信息权限");
    if (!isNormalEditableCase(row)) return message.warning("当前案件类型没有普通案件基本信息修改入口");
    const clueIds = Array.isArray(row.data.investigation_clue_ids) ? row.data.investigation_clue_ids.map(Number).filter(Boolean) : (Number(row.data.investigation_clue_id || row.data.clue_record_id) ? [Number(row.data.investigation_clue_id || row.data.clue_record_id)] : []);
    normalCaseEditForm.setFieldsValue({
      customer_record_id: Number(row.data.customer_record_id || row.data.customer_id) || caseCustomers.find((item) => item.title === row.customer)?.id,
      title: row.title,
      case_phase: row.status,
      cause_or_charge: row.data.cause_or_charge || "",
      handling_lawyers: row.data.handling_lawyers || [],
      assistant: row.data.assistant || "",
      business_owner: row.data.business_owner || row.data.source_person || "",
      investigator: row.data.investigator || "",
      investigation_clue_ids: clueIds,
      right_type: row.data.right_type || "",
      comment: "",
    });
    setEditingNormalCase(row);
  };
  const saveNormalCaseBasic = async () => {
    if (!editingNormalCase) return;
    const values = await normalCaseEditForm.validateFields();
    try {
      const { data } = await api.put(`/cases/${editingNormalCase.id}/normal-basic`, {
        ...values,
        title: values.title.trim(),
        case_phase: values.case_phase.trim(),
        cause_or_charge: values.cause_or_charge.trim(),
        handling_lawyers: values.handling_lawyers || [],
        assistant: values.assistant || "",
        business_owner: values.business_owner || "",
        investigator: values.investigator || "",
        investigation_clue_ids: values.investigation_clue_ids || [],
        right_type: values.right_type || "",
        comment: values.comment || "",
      });
      message.success("案件基本信息已保存");
      setEditingNormalCase(null);
      setViewingCounselCase(data);
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "案件基本信息保存失败");
    }
  };
  const openArbitrationBasicEdit = (row: CaseRow) => {
    if (!getCaseCapability(row).can_edit_basic) return message.warning("当前账号没有修改案件基本信息权限");
    if (row.data.case_type !== "仲裁") return message.warning("当前案件不是仲裁案件");
    arbitrationBasicForm.setFieldsValue({
      customer_record_id: Number(row.data.customer_record_id || row.data.customer_id) || caseCustomers.find(item=>item.title===row.customer)?.id,
      title: row.title, case_phase: row.status, cause_or_charge: row.data.cause_or_charge || "",
      handling_lawyers: row.data.handling_lawyers || [], assistant: row.data.assistant || "", investigator: row.data.investigator || "",
      investigation_clue_ids: Array.isArray(row.data.investigation_clue_ids) ? row.data.investigation_clue_ids : [], comment: "",
    });
    setEditingArbitrationCase(row);
  };
  const saveArbitrationBasic = async () => {
    if (!editingArbitrationCase) return;
    const values = await arbitrationBasicForm.validateFields();
    try {
      const {data} = await api.put(`/cases/${editingArbitrationCase.id}/arbitration-basic`, {...values, title:values.title.trim(),case_phase:values.case_phase.trim(),cause_or_charge:values.cause_or_charge.trim(),handling_lawyers:values.handling_lawyers||[],assistant:values.assistant||"",investigator:values.investigator||"",investigation_clue_ids:values.investigation_clue_ids||[],comment:values.comment||""});
      message.success("仲裁案件基本信息已保存"); setEditingArbitrationCase(null); setViewingCounselCase(data); await load();
    } catch(error:any) { message.error(error?.response?.data?.detail||"仲裁案件基本信息保存失败"); }
  };
  const openCriminalMaintenance = (row:CaseRow, kind:"litigants"|"public-security"|"procuratorates"|"courts") => {
    if (!getCaseCapability(row).can_edit_basic) return message.warning("当前账号没有维护刑事案件资料权限");
    const dateFields=["first_court_filing_date","first_court_hearing_date","second_court_filing_date","second_court_hearing_date","retrial_court_filing_date","retrial_court_hearing_date"];
    criminalMaintenanceForm.setFieldsValue({...row.data,...Object.fromEntries(dateFields.map(key=>[key,row.data[key]?dayjs(row.data[key]):undefined])),comment:""}); setCriminalMaintenance({row,kind});
  };
  const saveCriminalMaintenance = async () => {
    if (!criminalMaintenance) return; const values=await criminalMaintenanceForm.validateFields();
    const dateFields=["first_court_filing_date","first_court_hearing_date","second_court_filing_date","second_court_hearing_date","retrial_court_filing_date","retrial_court_hearing_date"];
    const payload={...values,...Object.fromEntries(dateFields.map(key=>[key,values[key]?.format?.("YYYY-MM-DD")||null]))};
    try { const {data}=await api.put(`/cases/${criminalMaintenance.row.id}/criminal/${criminalMaintenance.kind}`,payload); message.success("刑事案件资料已保存"); setCriminalMaintenance(null);setViewingCounselCase(data);await load(); } catch(error:any){message.error(error?.response?.data?.detail||"刑事案件资料保存失败");}
  };
  const openCaseTaskCreator = (row: CaseRow) => {
    if (!getCaseCapability(row).can_create_case_task) return message.warning("当前账号没有创建该案件任务的权限");
    taskForm.resetFields();
    taskForm.setFieldsValue({ owner: profile.username || row.owner, deadline: undefined, priority: "普通", collaborators: [] });
    setCaseTaskCreateCase(row);
  };
  const createCaseTask = async () => {
    const targetCase = taskCase || caseTaskCreateCase;
    if (!targetCase) return;
    if (!getCaseCapability(targetCase).can_create_case_task) return message.warning("当前账号没有创建该案件任务的权限");
    const v = await taskForm.validateFields();
    try {
      await api.post("/tasks", {
        title: v.title,
        customer: targetCase.customer,
        owner: v.owner,
        collaborators: v.collaborators || [],
        case_no: targetCase.serial_no,
        deadline: formatRequiredDate(v.deadline, "截止日期"),
        priority: v.priority || "普通",
        source: "案件任务",
        description: v.description || "",
      });
      message.success("案件任务已创建");
      setCaseTaskCreateCase(null);
      taskForm.resetFields();
      if (taskCase) await openCaseTasks(targetCase);
      else if (viewingCounselCase) await openCounselDetail(targetCase);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "案件任务创建失败");
    }
  };
  const openCaseFee = (row: CaseRow, expenseScope: "律所" | "平台" | "内部" = "律所") => {
    if (!getCaseCapability(row).can_create_finance) return message.warning("当前账号没有新增案件费用权限");
    feeForm.resetFields();
    feeForm.setFieldsValue({
      title: `${row.title}案件费用`,
      amount: row.data.amount || undefined,
      expense_scope: expenseScope,
      expense_subtype: expenseScope === "内部" ? "内部费用" : "官费",
      fee_type: expenseScope === "内部" ? "内部费用" : "官方费用",
      handler: profile.username || row.owner,
      court: row.data.court || "",
      payee: row.data.court || "",
      description: `来源案件 ${row.serial_no}`,
    });
    setFeeCase(row);
  };
  const createCaseFee = async () => {
    if (!feeCase) return;
    const values = await feeForm.validateFields();
    try {
      const { data } = await api.post("/finance/fees", {
        ...values,
        customer: feeCase.customer,
        case_no: feeCase.serial_no,
        case_record_id: feeCase.id,
      });
      message.success(`案件费用 ${data.serial_no} 已创建并关联当前案件`);
      setFeeCase(null);
      feeForm.resetFields();
      await load();
      if (viewingCounselCase) await openCounselDetail(feeCase);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "案件费用创建失败");
    }
  };
  const openProgress = (row: CaseRow) => {
    if (!getCaseCapability(row).can_update_progress) return message.warning("当前账号没有案件进展维护权限");
    progressForm.resetFields();
    progressForm.setFieldsValue({
      ...row.data,
      judgment_date: row.data.judgment_date
        ? dayjs(row.data.judgment_date)
        : undefined,
    });
    setProgressEditing(row);
  };
  const openHearing = (row: CaseRow) => {
    if (!getCaseCapability(row).can_manage_hearing) return message.warning("当前账号没有开庭排期权限");
    setHearingOpen(true);
    hearingForm.setFieldsValue({ case_record_id: row.id, court: row.data.court || "", hearing_lawyer: row.data.hearing_lawyer || "" });
  };
  const saveProgress = async () => {
    if (!progressEditing) return;
    const v = await progressForm.validateFields();
    try {
      await api.post(`/cases/${progressEditing.id}/progress`, {
        ...v,
        judgment_date: v.judgment_date?.format("YYYY-MM-DD"),
      });
      message.success("案件进展已保存，阶段已按要素自动更新");
      setProgressEditing(null);
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "案件进展保存失败");
    }
  };
  const caseColumns = useMemo(
    () => [
      {
        title: "案号",
        dataIndex: "serial_no",
        width: 150,
        render: (value: string, row: CaseRow) => (
          <Button type="link" className="case-cell-link" onClick={() => void openCounselDetail(row)}>
            {value}
          </Button>
        ),
      },
      { title: "案件名称", dataIndex: "title", width: 220, ellipsis: true },
      {
        title: "关联合同",
        key: "contract",
        width: 165,
        ellipsis: true,
        render: (_: unknown, r: CaseRow) =>
          r.data.contract_no ? <Button type="link" className="case-cell-link" onClick={() => openRelatedContract({ id: Number(r.data.contract_record_id) || undefined, serial_no: r.data.contract_no })}>{r.data.contract_no}</Button> : <Tag color="warning">系统转案待补</Tag>,
      },
      { title: "客户", dataIndex: "customer", width: 180, ellipsis: true, render: (value: string, r: CaseRow) => value ? <Button type="link" className="case-cell-link" onClick={() => openRelatedCustomer({ id: Number(r.data.customer_id) || undefined, serial_no: r.data.customer_no, title: value })}>{value}</Button> : "—" },
      {
        title: "案件类型",
        key: "type",
        width: 100,
        render: (_: unknown, r: CaseRow) => r.data.case_type || "-",
      },
      {
        title: "阶段",
        dataIndex: "status",
        width: 115,
        render: (v: string) => <Tag color={statusColors[v] || "blue"}>{v}</Tag>,
      },
      {
        title: "法院",
        key: "court",
        width: 190,
        ellipsis: true,
        render: (_: unknown, r: CaseRow) => r.data.court || "-",
      },
      {
        title: "开庭律师",
        key: "hearing_lawyer",
        width: 90,
        render: (_: unknown, r: CaseRow) => r.data.hearing_lawyer || "-",
      },
      {
        title: "经办律师",
        key: "handlers",
        width: 130,
        render: (_: unknown, r: CaseRow) =>
          (r.data.handling_lawyers || []).join("、") || "-",
      },
      {
        title: "律师助理",
        key: "assistant",
        width: 90,
        render: (_: unknown, r: CaseRow) => r.data.assistant || "-",
      },
      {
        title: "操作",
        key: "actions",
        fixed: "right" as const,
        width: 400,
        render: (_: unknown, r: CaseRow) => {
          const capability = getCaseCapability(r);
          return (
          <Space size={0}>
            {capability.can_assign_team && <Button
              type="link"
              icon={<TeamOutlined />}
              disabled={["待归档审核", "已归档"].includes(r.status)}
              onClick={() => openAssign(r)}
            >
              分配
            </Button>}
            {capability.can_update_progress && <Button
              type="link"
              icon={<EditOutlined />}
              disabled={[
                "等待公证书",
                "等待审核公证书",
                "待归档审核",
                "已归档",
              ].includes(r.status)}
              onClick={() => openProgress(r)}
            >
              进展
            </Button>}
            <Button
              type="link"
              icon={<FileTextOutlined />}
              onClick={() => openCaseTasks(r)}
            >
              任务
            </Button>
            {capability.can_create_finance && <Button type="link" onClick={() => openCaseFee(r)}>费用</Button>}
            {capability.can_manage_hearing && <Button
              type="link"
              icon={<CalendarOutlined />}
              disabled={["待归档审核", "已归档"].includes(r.status)}
              onClick={() => openHearing(r)}
            >
              排期
            </Button>}
            {capability.can_archive && <Button
              type="link"
              icon={<CheckSquareOutlined />}
              disabled={["待归档审核", "已归档"].includes(r.status)}
              onClick={() => openArchive(r)}
            >
              归档
            </Button>}
          </Space>
          );
        },
      },
    ],
    [caseActionCapabilities, cases],
  );
  const hearingColumns = [
    { title: "星期", dataIndex: "weekday", width: 75 },
    { title: "日期", dataIndex: "hearing_date", width: 105 },
    { title: "时间", dataIndex: "hearing_time", width: 75 },
    { title: "开庭法院", dataIndex: "court", width: 220 },
    { title: "法庭", dataIndex: "courtroom", width: 100 },
    {
      title: "案号",
      dataIndex: "case_no",
      width: 145,
      render: (value: string, row: Hearing) => {
        return value ? (
          <Button type="link" className="case-cell-link" onClick={() => void openSpecialCaseDetail({ case_record_id: row.case_record_id, case_no: value })}>
            {value}
          </Button>
        ) : "—";
      },
    },
    { title: "客户", dataIndex: "customer", width: 190, render: (value: string) => value ? <Button type="link" className="case-cell-link" onClick={() => openRelatedCustomer({ title: value })}>{value}</Button> : "—" },
    { title: "开庭类型", dataIndex: "hearing_type", width: 100 },
    { title: "开庭律师", dataIndex: "hearing_lawyer", width: 90 },
    {
      title: "状态",
      dataIndex: "status",
      width: 90,
      render: (v: string) => <Tag color="green">{v}</Tag>,
    },
  ];
  const canReview = ["admin", "manager"].includes(profile.role || "");
  const archiveColumns = [
    ...caseColumns.slice(0, 5),
    {
      title: "归档状态",
      dataIndex: "status",
      width: 105,
      render: (v: string) => <Tag color={statusColors[v] || "blue"}>{v}</Tag>,
    },
    {
      title: "归档号",
      key: "archive_no",
      width: 135,
      render: (_: unknown, r: CaseRow) => r.data.archive_no || "—",
    },
    {
      title: "纸质卷宗",
      key: "paper",
      width: 170,
      render: (_: unknown, r: CaseRow) =>
        r.data.paper_archive_location
          ? `${r.data.paper_archive_location}（${r.data.paper_volume_count || 1}卷）`
          : "—",
    },
    {
      title: "四项检查",
      key: "checks",
      width: 95,
      render: (_: unknown, r: CaseRow) =>
        [
          "case_closed",
          "fees_settled",
          "documents_complete",
          "finance_complete",
        ].every((k) => r.data[k]) ? (
          <Tag color="green">已通过</Tag>
        ) : (
          <Tag color="orange">待完善</Tag>
        ),
    },
    {
      title: "驳回原因",
      key: "reject",
      width: 160,
      ellipsis: true,
      render: (_: unknown, r: CaseRow) => r.data.archive_reject_reason || "—",
    },
    {
      title: "操作",
      key: "archive",
      fixed: "right" as const,
      width: 190,
      render: (_: unknown, r: CaseRow) =>
        r.status === "待归档审核" && canReview ? (
          <Space>
            <Button
              type="link"
              onClick={() => {
                reviewForm.resetFields();
                setReviewing({ row: r, approved: true });
              }}
            >
              通过
            </Button>
            <Button
              type="link"
              danger
              onClick={() => {
                reviewForm.resetFields();
                setReviewing({ row: r, approved: false });
              }}
            >
              驳回
            </Button>
          </Space>
        ) : r.status === "已归档" ? (
          <Tag color="green">已归档</Tag>
        ) : getCaseCapability(r).can_archive ? (
          <Button type="link" onClick={() => openArchive(r)}>
            归档检查
          </Button>
        ) : null,
    },
  ];
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
  const originalCases = useMemo(() => {
    const routeCaseType = initialView.includes("civil") ? "民事案件"
      : initialView.includes("criminal") ? "刑事案件"
        : initialView.includes("administrative") ? "行政案件及国家赔偿"
          : initialView.includes("counsel") ? "法律顾问"
            : initialView.includes("arbitration") ? "仲裁" : "";
    let list = scopedCases.filter((row) => !routeCaseType || (row.data.case_type || "民事案件") === routeCaseType);
    const includes = (value: unknown, queryValue: string) =>
      String(value || "").toLowerCase().includes(queryValue.toLowerCase());
    const mappings: [string, (row: CaseRow) => unknown][] = [
      ["plaintiff", (row) => row.data.plaintiff || row.customer],
      ["customer", (row) => row.customer],
      ["counsel_type", (row) => row.data.counsel_type],
      ["serial_no", (row) => row.serial_no],
      ["evidence_org", (row) => row.data.evidence_org],
      ["keyword", (row) => `${row.serial_no}${row.title}${row.customer}${row.data.opponent}`],
      ["defendant", (row) => row.data.opponent],
      ["handling_lawyer", (row) => (row.data.handling_lawyers || []).join(",")],
      ["notary_no", (row) => row.data.notary_no],
      ["status", (row) => row.status],
      ["hearing_lawyer", (row) => row.data.hearing_lawyer],
      ["assistant", (row) => row.data.assistant],
      ["investigator", (row) => row.data.investigator],
      ["court", (row) => row.data.court],
      ["channel", (row) => row.data.channel],
      ["warehouse", (row) => row.data.warehouse],
      ["document_name", (row) => attachments.filter((item) => item.record_id === row.id).map((item) => item.original_name).join(",")],
      ["area", (row) => row.data.area],
      ["location", (row) => row.data.location],
      ["log_content", (row) => row.data.log_content || row.description],
    ];
    for (const [key, getter] of mappings) {
      if (caseQuery[key]) list = list.filter((row) => includes(getter(row), String(caseQuery[key])));
    }
    const withinRange = (value: unknown, range: any) => {
      if (!range?.[0] || !range?.[1]) return true;
      const date = dayjs(String(value || ""));
      return date.isValid() && !date.isBefore(range[0], "day") && !date.isAfter(range[1], "day");
    };
    if (caseQuery.source_range) list = list.filter((row) => withinRange(row.data.source_date || row.data.source_at || row.data.created_at, caseQuery.source_range));
    if (caseQuery.hearing_range) list = list.filter((row) => withinRange(row.data.hearing_date, caseQuery.hearing_range));
    if (caseQuery.counsel_range) list = list.filter((row) => {
      if (!caseQuery.counsel_range?.[0] || !caseQuery.counsel_range?.[1]) return true;
      const start = dayjs(String(row.data.counsel_start || ""));
      const end = dayjs(String(row.data.counsel_end || ""));
      return start.isValid() && end.isValid() && !end.isBefore(caseQuery.counsel_range[0], "day") && !start.isAfter(caseQuery.counsel_range[1], "day");
    });
    return list;
  }, [scopedCases, initialView, caseQuery, attachments]);
  const selectedCase = (counselListMode?counselCases:originalCases).find((row) => selectedCaseKeys.includes(row.id));
  const selectedCaseCapability = getCaseCapability(selectedCase);
  const selectedCases = (counselListMode ? counselCases : originalCases).filter((row) => selectedCaseKeys.includes(row.id));
  const canCreateSelectedCaseFees = selectedCases.length > 0 && selectedCases.every((row) => getCaseCapability(row).can_create_finance);
  const isArchiveManager = ["admin", "manager"].includes(profile.role || "");
  const exportCases = async () => {
    try {
      const res = await api.get("/records/export", {params:{module:"case"},responseType:"blob"});
      const url = URL.createObjectURL(res.data), link = document.createElement("a");
      link.href=url; link.download="案件资料.csv"; link.click(); URL.revokeObjectURL(url);
    } catch { message.error("案件导出失败"); }
  };
  const downloadCaseExport = async (path: string, filename: string, ids: Key[], emptyMessage: string) => {
    const selectedIds = ids.map(Number).filter((id) => Number.isInteger(id) && id > 0);
    if (!selectedIds.length) return message.warning(emptyMessage);
    try {
      const response = await api.get(path, { params: { ids: selectedIds.join(",") }, responseType: "blob" });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "案件文件导出失败");
    }
  };
  const exportSelectedCasesExcel = (selectedOnly: boolean) => void downloadCaseExport(
    "/cases/export/excel",
    selectedOnly ? "普通案件-选中.xls" : "普通案件-当前查询.xls",
    selectedOnly ? selectedCaseKeys : originalCases.map((row) => row.id),
    selectedOnly ? "请选择需要导出的案件" : "当前查询没有可导出的案件",
  );
  const exportArchiveManifest = () => void downloadCaseExport(
    "/cases/export/archive-manifest", "案件归档清单.xls", selectedCaseKeys, "请选择需要导出归档清单的案件",
  );
  const exportCaseQrWord = () => void downloadCaseExport(
    "/cases/export/qr-word", "案件二维码清单.docx", selectedCaseKeys, "请选择需要生成二维码清单的案件",
  );
  const exportCounselCases = async (selectedOnly:boolean) => {
    if(selectedOnly&&!selectedCaseKeys.length)return message.warning("请选择需要导出的法律顾问案件");
    try {
      const response=await api.post("/cases/counsel/export",counselSearchPayload(caseQuery,1,200,{selected_only:selectedOnly,selected_ids:selectedOnly?selectedCaseKeys.map(Number):[]}),{responseType:"blob"});
      const url=URL.createObjectURL(response.data),link=document.createElement("a");
      link.href=url;link.download=selectedOnly?"法律顾问案件-选中.csv":"法律顾问案件-全部.csv";link.click();URL.revokeObjectURL(url);
    } catch(error:any){message.error(error?.response?.data?.detail||"法律顾问案件导出失败");}
  };
  const exportSpecialRecords = async (module:string,filename:string) => {
    try {
      const res=await api.get("/records/export",{params:{module},responseType:"blob"});
      const url=URL.createObjectURL(res.data),link=document.createElement("a");link.href=url;link.download=filename;link.click();URL.revokeObjectURL(url);
    } catch { message.error("数据导出失败"); }
  };
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
  const uploadCaseFile = async (file?: File) => {
    if (!file || !selectedCase) return message.warning("请先选择案件再上传文件");
    const category = initialView === "case-files-receipt" ? "案件票据文件" : caseUploadCategory;
    const data = new FormData(); data.append("file",file); data.append("record_id",String(selectedCase.id)); data.append("category",category); data.append("remark",initialView==="case-files-receipt"?"案件票据批量上传":`案件列表上传：${category}`);
    try { await api.post("/attachments",data); message.success("案件文件已上传"); } catch(error:any){message.error(error?.response?.data?.detail||"上传失败");}
    finally { if(caseUploadRef.current) caseUploadRef.current.value=""; }
  };
  const uploadCaseInvoiceFile = async (file?: File) => {
    if (!file) return;
    const data = new FormData();
    data.append("file", file);
    data.append("category", "案件发票文件");
    data.append("remark", "案件发票文件导入");
    try {
      await api.post("/attachments", data);
      message.success("发票文件已上传，请点击开始导入完成案件匹配");
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "发票文件上传失败");
    } finally {
      if (caseUploadRef.current) caseUploadRef.current.value = "";
    }
  };
  const startCaseInvoiceImport = async () => {
    if (!invoiceRows.length) return message.warning("请先上传发票文件");
    try {
      const { data } = await api.post("/cases/invoice-files/import");
      if (data.unmatched) message.warning(`已处理 ${data.processed} 个文件，匹配案件 ${data.matched} 个，${data.unmatched} 个文件名未识别案件编号`);
      else message.success(`已完成 ${data.processed} 个发票文件导入并匹配案件`);
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "发票文件导入失败");
    }
  };
  const originalCaseColumns = [
    {title:"基本信息",key:"base",width:185,render:(_:unknown,row:CaseRow)=><><p><Button type="link" className="case-cell-link" onClick={()=>void openCounselDetail(row)}>案件编号:{row.serial_no}</Button></p><p>案件名称:{row.title}</p></>},
    {title:"当事人信息",key:"parties",width:250,render:(_:unknown,row:CaseRow)=><><p>原告:{row.data.plaintiff||row.customer}</p><p>被告:{row.data.opponent||""}</p></>},
    {title:"阶段信息",key:"phase",width:175,render:(_:unknown,row:CaseRow)=><><p>案件阶段:{row.status}</p><p>变更时间:{row.data.phase_changed_at||""}</p></>},
    {title:"法院信息",key:"court",width:205,render:(_:unknown,row:CaseRow)=><><p>法院:{row.data.court||""}</p><p>法院案号:{row.data.court_case_no||""}</p></>},
    {title:"法官信息",key:"judge",width:170,render:(_:unknown,row:CaseRow)=><><p>法官:{row.data.judge||""}</p><p>联系方式:{row.data.judge_phone||""}</p></>},
    {title:"委托律师",key:"lawyer",width:180,render:(_:unknown,row:CaseRow)=><><p>经办:{(row.data.handling_lawyers||[]).join(",")}</p><p>开庭:{row.data.hearing_lawyer||""}　助理:{row.data.assistant||""}</p></>},
    {title:"判决信息",key:"judgment",width:190,render:(_:unknown,row:CaseRow)=><><p>判决日期:{row.data.judgment_date||""}</p><p>判决结果:{row.data.judgment_result||""}</p></>},
    {title:"调查信息",key:"investigation",width:190,render:(_:unknown,row:CaseRow)=><><p>调查员:{row.data.investigator||""}</p><p>取证机构:{row.data.evidence_org||""}</p></>},
    {title:"阶段信息",key:"phase-detail",width:190,render:(_:unknown,row:CaseRow)=><><p>当前阶段:{row.status}</p><p>执行进度:{row.data.execution_progress||""}</p></>},
    {title:"任务信息",key:"task",width:255,render:(_:unknown,row:CaseRow)=><><p>名称:<Button type="link" className="case-cell-link" onClick={()=>openCaseTasks(row)}>{row.data.task_name||""}</Button></p><p>内容:{row.data.task_content||""}</p></>},
    {title:"主体信息",key:"entity",width:190,render:(_:unknown,row:CaseRow)=><><p>主体:{row.customer?<Button type="link" className="case-cell-link" onClick={()=>openRelatedCustomer({id:Number(row.data.customer_id)||undefined,serial_no:row.data.customer_no,title:row.customer})}>{row.data.subject_name||row.customer}</Button>:row.data.subject_name||""}</p><p>披露状态:{row.data.subject_status||""}</p></>},
    {title:"归档信息",key:"archive",width:190,render:(_:unknown,row:CaseRow)=><><p>归档状态:{row.data.archive_status||row.status}</p><p>归档日期:{row.data.archived_at||""} <Button type="link" className="case-cell-link" onClick={()=>openCaseTasks(row)}>查看</Button></p></>},
  ];
  const counselCaseColumns = [
    {title:"案件编号",dataIndex:"serial_no",width:170,sorter:true,render:(value:string,row:CaseRow)=><Button type="link" className="case-cell-link" onClick={()=>void openCounselDetail(row)}>{value}</Button>},
    {title:"顾问类型",key:"counsel_type",width:150,render:(_:unknown,row:CaseRow)=>row.data.counsel_type||"—"},
    {title:"客户",dataIndex:"customer",width:230,ellipsis:true,render:(value:string,row:CaseRow)=>value?<Button type="link" className="case-cell-link" onClick={()=>openRelatedCustomer({id:Number(row.data.customer_id)||undefined,serial_no:row.data.customer_no,title:value})}>{value}</Button>:"—"},
    {title:"顾问期限",key:"counsel_range",width:225,render:(_:unknown,row:CaseRow)=>row.data.counsel_start&&row.data.counsel_end?`${row.data.counsel_start} 至 ${row.data.counsel_end}`:"—"},
    {title:"经办律师",key:"handling_lawyers",width:150,render:(_:unknown,row:CaseRow)=>(row.data.handling_lawyers||[]).join("、")||"—"},
    {title:"律师助理",key:"assistant",width:120,render:(_:unknown,row:CaseRow)=>row.data.assistant||"—"},
    {title:"案源人",key:"source_person",width:120,render:(_:unknown,row:CaseRow)=>row.data.source_person||row.owner||"—"},
    {title:"剩余时间",key:"remaining_days",width:105,render:(_:unknown,row:CaseRow)=>{const end=dayjs(String(row.data.counsel_end||""));const days=end.isValid()?Math.max(0,end.startOf("day").diff(dayjs().startOf("day"),"day")):0;return <span style={{color:days<10?"red":"green"}}>{days} 天</span>;}},
    {title:"操作",key:"actions",fixed:"right" as const,width:150,render:(_:unknown,row:CaseRow)=><Space size={0}><Button type="link" onClick={()=>void openCounselDetail(row)}>查看</Button>{getCaseCapability(row).can_edit_basic&&<Button type="link" disabled={["待归档审核","已归档"].includes(row.status)} onClick={()=>openCounselEdit(row)}>编辑</Button>}</Space>},
  ];
  const phaseLabels=["等待公证书","审核公证书","待主体披露","新案待分配","文书准备","客户盖章","等待立案","补充取证","提交立案","一审阶段","二审阶段","再审阶段","执行阶段","归档阶段"];
  const phaseItems=phaseLabels.map(label=>[label,scopedCases.filter(row=>row.status===label).length] as const);
  const originalArchiveMode=initialView.startsWith("case-archive-");
  const archiveDone=initialView.includes("done"), archiveRefused=initialView.includes("refused");
  const originalArchiveRows=cases.filter(row=>archiveDone?row.status==="已归档":archiveRefused?Boolean(row.data.archive_reject_reason):row.status==="待归档审核").filter(row=>{
    const match=(value:unknown,key:string)=>!caseQuery[key]||String(value||"").toLowerCase().includes(String(caseQuery[key]).toLowerCase());
    return match(row.data.plaintiff||row.customer,"plaintiff")&&match(row.serial_no,"serial_no")&&match(row.data.assistant,"assistant")&&match(row.data.court,"court")&&match(row.data.opponent,"defendant")&&match(row.data.notary_no,"notary_no")&&match(row.data.hearing_lawyer,"hearing_lawyer")&&match((row.data.handling_lawyers||[]).join(","),"handling_lawyer")&&match(row.data.archive_submitter||row.owner,"submitter");
  });
  const originalArchiveColumns:any[]=[
    {title:"提交人",key:"submitter",width:105,render:(_:unknown,row:CaseRow)=>row.data.archive_submitter||row.owner},
    {title:"提交日期",key:"submitted",width:150,render:(_:unknown,row:CaseRow)=>row.data.archive_submitted_at||""},
    ...(archiveDone||archiveRefused?[{title:"审核人",key:"reviewer",width:105,render:(_:unknown,row:CaseRow)=>row.data.archive_reviewer||""},{title:"审核日期",key:"reviewed",width:150,render:(_:unknown,row:CaseRow)=>row.data.archive_reviewed_at||row.data.archived_at||""}]:[{title:"提交人备注",key:"comment",width:160,render:(_:unknown,row:CaseRow)=>row.data.archive_submit_comment||row.description||""}]),
    {title:"案件编号",width:145,render:(_:unknown,row:CaseRow)=><Button type="link" className="case-cell-link" onClick={()=>void openCounselDetail(row)}>{row.serial_no}</Button>},{title:"案件阶段",dataIndex:"status",width:110},
    {title:"法院名称",key:"court",width:190,render:(_:unknown,row:CaseRow)=>row.data.court||""},
    {title:"原告",key:"plaintiff",width:180,render:(_:unknown,row:CaseRow)=>row.data.plaintiff||row.customer},
    {title:"被告",key:"defendant",width:180,render:(_:unknown,row:CaseRow)=>row.data.opponent||""},
    {title:"开庭律师",key:"hearing",width:105,render:(_:unknown,row:CaseRow)=>row.data.hearing_lawyer||""},
    {title:"经办律师",key:"handlers",width:130,render:(_:unknown,row:CaseRow)=>(row.data.handling_lawyers||[]).join(",")},
    {title:"律师助理",key:"assistant",width:105,render:(_:unknown,row:CaseRow)=>row.data.assistant||""},
  ];
  // All data columns below declare their widths. Keep the selection column inside
  // the horizontal viewport so the fixed right action column never overlays data.
  const originalCaseTableScrollX=2420;
  const counselCaseTableScrollX=1460;
  const archiveCaseTableScrollX=archiveDone||archiveRefused?1700:1600;
  const specialMode=initialView.endsWith("-schedule")?"schedule":initialView.endsWith("-execution")?"execution":initialView.endsWith("-unclaimed")?"unclaimed":initialView.endsWith("-stage")?"stage":initialView.endsWith("-no-refund")?"refund":initialView==="case-files-receipt"?"receipt":initialView==="case-files-invoice"?"invoice":"";
  const specialTitle:Record<string,string>={schedule:"案件列表",execution:"案件列表",unclaimed:"内部提成-待结算",stage:"案件阶段统计",refund:"退费查询",receipt:"票据上传",invoice:"发票文件导入"};
  const specialFilters:Record<string,[string,string,string?][]>= {
    schedule:[["plaintiff","原告/申请人/公诉机关"],["serial_no","案号"],["handling_lawyer","经办律师"],["keyword","关键字"],["defendant","被告/被申请人"],["notary_no","公证书号"],["hearing_lawyer","开庭律师"],["court","法院/机构"],["third_party","第三人/受害人"],["investigator","调查员"],["assistant","律师助理"],["document_name","文档名称"],["source_range","案源时间","date"],["hearing_range","开庭时间","date"],["case_type","案件类型","select"],["log_content","日志内容"]],
    execution:[["plaintiff","原告"],["serial_no","案件编号"],["evidence_org","取证机构"],["keyword","关键字"],["defendant","被告"],["handling_lawyer","经办律师"],["notary_no","公证书号"],["execution_progress","执行进度"],["hearing_lawyer","开庭律师"],["assistant","律师助理"],["investigator","调查员"],["court","法院名称"],["source_range","案源时间","date"],["channel","侵权渠道"],["warehouse","仓库"],["document_name","文档名称"],["hearing_range","开庭时间","date"],["area","侵权区域"],["location","库位"],["log_content","日志内容"]],
    unclaimed:[["customer","客户名称"],["serial_no","案件编号"],["court_case_no","法院案号"],["notary_no","公证书号"],["hearing_lawyer","开庭律师"],["assistant","律师助理"],["status","案件阶段"],["investigator","调查员"],["source_person","案源人"]],
    refund:[["serial_no","案件编号"],["court_case_no","法院案号"],["court","法院名称"],["payment_range","付款时间","date"],["customer","客户名称"],["payee","收款单位"],["refund_status","退费状态"],["refund_amount","退费金额"],["hearing_lawyer","开庭律师"],["assistant","律师助理"],["status","案件阶段"],["fee_type","费用类型"]],
    receipt:[["serial_no","案件编号"],["customer","客户名称"],["contract_no","合同编号"],["fee_group","费用大类"],["case_type","案件类型"],["status","案件阶段"],["fee_type","费用类型"],["receipt_status","票据状态"],["notary_no","公证书号"],["package_no","打包号"]],
  };
  const caseMatches=(row:CaseRow)=>Object.entries(caseQuery).every(([key,value])=>{if(!value||Array.isArray(value))return true;const map:Record<string,unknown>={serial_no:row.serial_no,customer:row.customer,status:row.status,plaintiff:row.data.plaintiff||row.customer,defendant:row.data.opponent,keyword:`${row.serial_no}${row.title}${row.customer}${row.data.opponent||""}`,handling_lawyer:(row.data.handling_lawyers||[]).join(","),...row.data};return String(map[key]||"").toLowerCase().includes(String(value).toLowerCase())});
  const specialCases=scopedCases.filter(caseMatches);
  const phaseRows:any[]=Object.values(specialCases.reduce((acc:Record<string,any>,row)=>{const name=row.owner||"未分配";if(!acc[name])acc[name]={id:name,name,date:dayjs().format("YYYY-MM-DD"),filing:0,refund:0,execution:0,clue:0};if(String(row.status).includes("立案"))acc[name].filing++;if(String(row.status).includes("退费"))acc[name].refund++;if(String(row.status).includes("执行"))acc[name].execution++;if(row.data.investigation_clue)acc[name].clue++;return acc},{}));
  const relatedCase=(id:number)=>cases.find(row=>row.id===id);
  const relatedFinance=(id:number)=>financeRows.find(row=>row.id===id);
  const invoiceCase=(row:AttachmentRow)=>{const finance=relatedFinance(row.record_id||0);return relatedCase(row.record_id||0)||cases.find(item=>item.serial_no===finance?.data?.case_no)};
  const scheduleRows=hearings.filter(row=>{const c=relatedCase(row.case_record_id);return c?caseMatches(c):true}).map(row=>({...row,case:relatedCase(row.case_record_id)}));
  const receiptRows=specialCases;
  const invoiceRows=attachments.filter(row=>row.category.includes("发票")||row.category.includes("票据"));
  const specialRows:any[]=specialMode==="schedule"?scheduleRows:specialMode==="execution"?specialCases.filter(row=>row.status==="执行"):specialMode==="unclaimed"?specialCases.filter(row=>!row.data.commission_applied):specialMode==="stage"?phaseRows:specialMode==="refund"?financeRows.filter(row=>String(row.data.fee_type||row.title).includes("退费")&&caseMatches(row)):specialMode==="receipt"?receiptRows:specialMode==="invoice"?invoiceRows:[];
  const selectedSpecialRow:any=specialRows.find(row=>selectedCaseKeys.includes(row.id));
  const openSelectedScheduleHearing = async () => {
    if (!selectedSpecialRow) return message.warning("请先选择案件");
    const target = await resolveVisibleCase({ case: selectedSpecialRow.case, case_record_id: selectedSpecialRow.case_record_id, case_no: selectedSpecialRow.case_no });
    if (target) openHearing(target);
  };
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
  const completeRefund=async()=>{
    if(!refundCompleting)return;
    const values=await refundCompleteForm.validateFields();
    await api.post(`/finance/refunds/${refundCompleting.id}/complete`,{
      actual_date:formatRequiredDate(values.actual_date,"实际退款日期"),
      voucher_no:values.voucher_no,
      comment:values.comment||"",
    });
    message.success("退款到账登记完成");
    setRefundCompleting(null);
    refundCompleteForm.resetFields();
    await load();
  };
  const specialColumns:Record<string,any[]>={
    schedule:[
      {title:"星期",dataIndex:"weekday"},
      {title:"开庭日期",dataIndex:"hearing_date"},
      {title:"时间",dataIndex:"hearing_time"},
      {
        title:"案件编号",
        render:(_:unknown,row:any)=>(
          <Button type="link" className="case-cell-link" onClick={()=>openSpecialCaseDetail(row)}>
            {row.case_no || row.case?.serial_no || ""}
          </Button>
        ),
      },
      {title:"案件阶段",render:(_:unknown,row:any)=>row.case?.status||""},
      {title:"法院名称",dataIndex:"court"},
      {title:"法庭",dataIndex:"courtroom"},
      {title:"原告",render:(_:unknown,row:any)=>row.case?.data.plaintiff||row.customer},
      {title:"被告",render:(_:unknown,row:any)=>row.case?.data.opponent||""},
      {title:"开庭律师",dataIndex:"hearing_lawyer"},
      {title:"经办律师",render:(_:unknown,row:any)=>(row.case?.data.handling_lawyers||[]).join(",")},
      {title:"律师助理",render:(_:unknown,row:any)=>row.case?.data.assistant||""},
    ],
    execution:[{title:"基本信息",render:(_:unknown,row:CaseRow)=><><p><Button type="link" className="case-cell-link" onClick={()=>openSpecialCaseDetail(row)}>{row.serial_no}</Button></p><p>阶段:{row.status}</p></>},{title:"当事人信息",render:(_:unknown,row:CaseRow)=><><p>原告:{row.data.plaintiff||row.customer}</p><p>被告:{row.data.opponent||""}</p></>},{title:"法院信息",render:(_:unknown,row:CaseRow)=><><p>法院:{row.data.court||""}</p><p>案号:{row.data.court_case_no||""}</p></>},{title:"法官信息",render:(_:unknown,row:CaseRow)=>row.data.judge||""},{title:"委托律师",render:(_:unknown,row:CaseRow)=>(row.data.handling_lawyers||[]).join(",")},{title:"判决信息",render:(_:unknown,row:CaseRow)=>row.data.judgment_result||""},{title:"进度时长",render:(_:unknown,row:CaseRow)=>row.data.execution_days??0},{title:"操作",render:(_:unknown,row:CaseRow)=>getCaseCapability(row).can_update_progress?<Button type="link" onClick={()=>openProgress(row)}>修改进度</Button>:null}],
    unclaimed:["案号","原告","被告","金额","回款单位","到账金额","到账时间","结算状态","案件阶段","案源人","开庭律师","律师助理","调查员","品管"].map((title,i)=>({title,key:String(i),render:(_:unknown,row:CaseRow)=>i===0?<Button type="link" className="case-cell-link" onClick={()=>openSpecialCaseDetail(row)}>{row.serial_no}</Button>:[row.data.plaintiff||row.customer,row.data.opponent,row.data.amount,row.data.payer,row.data.received_amount,row.data.received_at,row.data.settlement_status,row.status,row.data.source_person,row.data.hearing_lawyer,row.data.assistant,row.data.investigator,row.data.quality_manager][i-1]||""})),
    stage:[{title:"姓名",dataIndex:"name"},{title:"日期",dataIndex:"date"},{title:"立案进度",dataIndex:"filing"},{title:"退费进度",dataIndex:"refund"},{title:"执行进度",dataIndex:"execution"},{title:"线索进度",dataIndex:"clue"}],
    refund:["案号","原告","被告","案件阶段","律师助理","开庭律师","费用类型","金额","退费金额","新建时间","法院名称","退费进度","进度时长","操作"].map((title,i)=>({title,key:String(i),render:(_:unknown,row:CaseRow)=>i===0?<Button type="link" className="case-cell-link" onClick={()=>openSpecialCaseDetail({case_no:row.data.case_no||row.serial_no})}>{row.data.case_no||row.serial_no}</Button>:[row.data.plaintiff||row.customer,row.data.opponent,row.data.case_stage||row.status,row.data.assistant,row.data.hearing_lawyer,row.data.fee_type,row.data.amount,row.data.refund_amount,row.data.created_at||"",row.data.court,row.data.refund_status,row.data.progress_days,"查看"][i-1]||""})),
    receipt:["案号","案件名称","客户","费用类型","金额","申请人","通知日期","已收","已付","已开票"].map((title,i)=>({title,key:String(i),render:(_:unknown,row:CaseRow)=>i===0?<Button type="link" className="case-cell-link" onClick={()=>openSpecialCaseDetail(row)}>{row.serial_no}</Button>:i===2&&row.customer?<Button type="link" className="case-cell-link" onClick={()=>openRelatedCustomer({id:Number(row.data.customer_id)||undefined,serial_no:row.data.customer_no,title:row.customer})}>{row.customer}</Button>:[row.title,row.customer,row.data.fee_type,row.data.amount,row.owner,row.data.notice_date,row.data.received_amount,row.data.paid_amount,row.data.invoiced_amount][i-1]||""})),
    invoice:[{title:"文件名",dataIndex:"original_name"},{title:"案件编号",render:(_:unknown,row:AttachmentRow)=>{const target=invoiceCase(row);const caseNo=target?.serial_no||relatedFinance(row.record_id||0)?.data?.case_no||"";return caseNo?<Button type="link" className="case-cell-link" onClick={()=>openSpecialCaseDetail(target||{case_no:caseNo})}>{caseNo}</Button>:""}},{title:"案件类型",render:(_:unknown,row:AttachmentRow)=>invoiceCase(row)?.data.case_type||""},{title:"发票申请人",dataIndex:"uploader"},{title:"费用类型",render:(_:unknown,row:AttachmentRow)=>relatedFinance(row.record_id||0)?.data?.fee_type||row.category},{title:"费用金额",render:(_:unknown,row:AttachmentRow)=>relatedFinance(row.record_id||0)?.data?.amount??""},{title:"票据编号",render:(_:unknown,row:AttachmentRow)=>relatedFinance(row.record_id||0)?.data?.invoice_no||row.remark||""},{title:"票据金额",render:(_:unknown,row:AttachmentRow)=>relatedFinance(row.record_id||0)?.data?.invoice_amount??relatedFinance(row.record_id||0)?.data?.amount??""},{title:"票据日期",render:(_:unknown,row:AttachmentRow)=>relatedFinance(row.record_id||0)?.data?.invoice_date||row.created_at}],
  };
  const counselDocTree=[
    {label:"客户文档",category:"客户文档",type:"folder"},
    {label:"合同文档",category:"合同文档",type:"folder"},
    {label:"调查文档",category:"调查文档",type:"folder-open"},
    {label:"鉴别资料",category:"鉴别资料",type:"child"},
    {label:"调查文档",category:"调查文档",type:"child"},
    {label:"取证文档",category:"取证文档",type:"child"},
    {label:"案件文档",category:"案件文件",type:"folder-open"},
    {label:"主体及委托资料",category:"主体及委托资料",type:"child"},
    {label:"起诉材料及证据",category:"起诉材料及证据",type:"child"},
    {label:"答辩材料及证据",category:"答辩材料及证据",type:"child"},
    {label:"法院诉讼文书",category:"法院诉讼文书",type:"child"},
    {label:"庭审及庭后文件",category:"庭审及庭后文件",type:"child"},
  ];
  const filteredCounselDetailAttachments=activeCounselDocCategory
    ? counselDetailAttachments.filter(row=>String(row.category||"").includes(activeCounselDocCategory))
    : counselDetailAttachments;
  return (
    <div className={`case-center-page ${isCaseDetailView ? "case-detail-route" : ""}`}>
      {isCaseDetailView && !viewingCounselCase && <div className="case-detail-route-loading">正在加载案件详情...</div>}
      {isCreateView && (
        <div className="case-create-route-page" data-flow-token={createFlowToken}>
          <Steps
            className="case-create-steps"
            current={createStep}
            items={isCounselCreate
              ? [{ title: "基本信息" }, { title: "当事人信息" }]
              : [{ title: "基本信息" }, { title: "当事人信息" }, { title: "司法机关信息" }]}
          />
          <Form
            form={createForm}
            className="case-create-wizard-form"
            labelCol={{ span: 5 }}
            wrapperCol={{ span: 17 }}
          >
            {createStep === 0 && (
              <div className="case-create-step">
                <div className="case-create-section-title">基本信息</div>
                <div className="case-create-fields">
                  <Form.Item label="案件类型" name="case_type" rules={[{ required: true, message: "请选择案件类型" }]}>
                    <Select
                      options={caseTypeOptions}
                      disabled={initialView !== "case-new"}
                      onChange={(value:string)=>{
                        setSelectedCreateType(value);
                        createForm.setFieldsValue({client_position:value==="刑事案件"?"被告人/犯罪嫌疑人":value==="法律顾问"?"":"原告/申请人",cause_or_charge:undefined,right_type:undefined,counsel_type:undefined,counsel_range:value==="法律顾问"?[dayjs(),dayjs().add(1,"year")]:undefined});
                      }}
                    />
                  </Form.Item>
                  <Form.Item label="客户" name="customer" rules={[{ required: true, message: "请选择客户" }]}>
                    <Select disabled={Boolean(createContractId)} showSearch optionFilterProp="label" placeholder="先选择合同后自动锁定客户" options={[...new Set(contracts.map((row) => row.customer))].map((value) => ({ value, label: value }))} />
                  </Form.Item>
                  {!isCounselCreate && <Form.Item label="客户诉讼地位" name="client_position" rules={[{ required: true }]}>
                    <Select options={clientPositionOptions.map((value) => ({ value, label: value }))} />
                  </Form.Item>}
                  <Form.Item label="合同号" name="contract_record_id" rules={[{ required: true, message: "请选择已审批合同" }]}>
                    <Select showSearch allowClear optionFilterProp="label" placeholder="请选择合同" onChange={(value:number|undefined)=>{const selected=contracts.find(row=>row.id===value);createForm.setFieldsValue({customer:selected?.customer,source_person:selected?.data?.source_person||selected?.owner||"",title:selected?`${selected.title}案件`:undefined})}}>
                      {contracts.map((row) => <Select.Option key={row.id} value={row.id} label={`${row.serial_no}｜${row.customer}｜${row.title}`}>{row.serial_no}｜{row.customer}｜{row.title}</Select.Option>)}
                    </Select>
                  </Form.Item>
                  <Form.Item label="案源人" name="source_person"><Input placeholder="由关联合同自动带入，可按本案实际情况修改" maxLength={128} /></Form.Item>
                  {!isCounselCreate && <Form.Item label={isCriminalCreate ? "罪名" : "案由"} name="cause_or_charge" rules={[{ required: true }]}>{isCriminalCreate?<Input placeholder="请输入罪名" />:<Select showSearch optionFilterProp="label" placeholder="输入关键词选择案由" options={causeOptions}/>}</Form.Item>}
                  {isCounselCreate && <><Form.Item label="顾问类型" name="counsel_type" rules={[{ required: true }]}><Input placeholder="请输入顾问类型" /></Form.Item><Form.Item label="顾问期限" name="counsel_range" rules={[{ required: true }]}><DatePicker.RangePicker style={{ width: "100%" }} /></Form.Item></>}
                  <Form.Item label="案件名称" name="title" rules={[{ required: true }]}><Input placeholder="请输入案件名称" /></Form.Item>
                  {!isCounselCreate && <Form.Item label="案件阶段" name="status"><Select disabled options={caseStatuses.map((value) => ({ value, label: value === "新案待分配" ? "待分配" : value }))} /></Form.Item>}
                  <Form.Item label="经办律师" name="handling_lawyers" rules={[{ required: true, message: "请选择系统已创建的在职律师" }]}><Select mode="multiple" showSearch optionFilterProp="label" options={caseLawyerOptions} placeholder="请选择系统已创建的在职律师" notFoundContent="暂无在职律师；请先在人事中心创建并启用律师账号" /></Form.Item>
                  <Form.Item label="律师助理" name="assistant"><Select allowClear showSearch optionFilterProp="label" options={caseAssistantOptions} placeholder="请选择系统已创建的在职人员" /></Form.Item>
                  {!isCriminalCreate && !isCounselCreate && <Form.Item label="权利类型" name="right_type"><Select allowClear showSearch optionFilterProp="label" placeholder="请选择权利类型" options={rightTypeOptions} /></Form.Item>}
                </div>
              </div>
            )}
            {createStep === 1 && (
              <div className="case-create-step"><div className="case-create-section-title">当事人信息</div><div className="case-create-fields">
                <Form.Item label={litigantLabels.plaintiff} name="plaintiffs"><Select mode="tags" tokenSeparators={[",", "，"]} placeholder="输入名称后回车，可添加多人" /></Form.Item>
                <Form.Item label={litigantLabels.plaintiffAgent} name="plaintiff_agents"><Select mode="tags" tokenSeparators={[",", "，"]} placeholder="输入名称后回车，可添加多人" /></Form.Item>
                <Form.Item label={litigantLabels.defendant} name="defendants"><Select mode="tags" tokenSeparators={[",", "，"]} placeholder="输入名称后回车，可添加多人" /></Form.Item>
                <Form.Item label={litigantLabels.defendantAgent} name="defendant_agents"><Select mode="tags" tokenSeparators={[",", "，"]} placeholder="输入名称后回车，可添加多人" /></Form.Item>
                <Form.Item label={litigantLabels.third} name="third_parties"><Select mode="tags" tokenSeparators={[",", "，"]} placeholder="输入名称后回车，可添加多人" /></Form.Item>
                <Form.Item label={litigantLabels.thirdAgent} name="third_party_agents"><Select mode="tags" tokenSeparators={[",", "，"]} placeholder="输入名称后回车，可添加多人" /></Form.Item>
                <Form.Item label="备注" name="litigant_comment"><Input.TextArea rows={3} /></Form.Item>
              </div></div>
            )}
            {createStep === 2 && !isCounselCreate && (
              <div className="case-create-step"><div className="case-create-section-title">司法机关信息</div><div className="case-create-fields">
                {isCriminalCreate && <><div className="case-create-section-title">公安机关</div>
                <Form.Item label="公安机关" name="public_security_name"><Input /></Form.Item><Form.Item label="案件编号" name="public_security_case_no"><Input /></Form.Item><Form.Item label="地址" name="public_security_address"><Input /></Form.Item><Form.Item label="联系电话" name="public_security_phone"><Input /></Form.Item><Form.Item label="承办人" name="public_security_operator"><Input /></Form.Item>
                <div className="case-create-section-title">一审检察院</div>
                <Form.Item label="检察院" name="first_procuratorate_name"><Input /></Form.Item><Form.Item label="案件编号" name="first_procuratorate_case_no"><Input /></Form.Item><Form.Item label="地址" name="first_procuratorate_address"><Input /></Form.Item><Form.Item label="联系电话" name="first_procuratorate_phone"><Input /></Form.Item><Form.Item label="承办人" name="first_procuratorate_operator"><Input /></Form.Item>
                <div className="case-create-section-title">二审检察院</div>
                <Form.Item label="检察院" name="second_procuratorate_name"><Input /></Form.Item><Form.Item label="案件编号" name="second_procuratorate_case_no"><Input /></Form.Item><Form.Item label="地址" name="second_procuratorate_address"><Input /></Form.Item><Form.Item label="联系电话" name="second_procuratorate_phone"><Input /></Form.Item><Form.Item label="承办人" name="second_procuratorate_operator"><Input /></Form.Item>
                <div className="case-create-section-title">再审检察院</div>
                <Form.Item label="检察院" name="retrial_procuratorate_name"><Input /></Form.Item><Form.Item label="案件编号" name="retrial_procuratorate_case_no"><Input /></Form.Item><Form.Item label="地址" name="retrial_procuratorate_address"><Input /></Form.Item><Form.Item label="联系电话" name="retrial_procuratorate_phone"><Input /></Form.Item><Form.Item label="承办人" name="retrial_procuratorate_operator"><Input /></Form.Item></>}
                <Form.Item name="first_court_enabled" valuePropName="checked" wrapperCol={{ offset: 5, span: 17 }}><Checkbox>一审法院信息</Checkbox></Form.Item>
                {firstCourtEnabled && <><Form.Item label="法院" name="first_court_name"><Select showSearch optionFilterProp="label" options={courtOptions}/></Form.Item><Form.Item label="法庭" name="first_court_courtroom"><Input /></Form.Item><Form.Item label="法官" name="first_court_judge"><Select allowClear showSearch optionFilterProp="label" options={officersForCourt(firstCourtName, "法官")} placeholder="请先选择法院" /></Form.Item><Form.Item label="书记员" name="first_court_clerk"><Select allowClear showSearch optionFilterProp="label" options={officersForCourt(firstCourtName, "书记员")} placeholder="请先选择法院" /></Form.Item><Form.Item label="案号" name="first_court_case_no"><Input /></Form.Item><Form.Item label="立案日期" name="first_court_filing_date"><DatePicker style={{ width: "100%" }} /></Form.Item><Form.Item label="开庭日期" name="first_court_hearing_date"><DatePicker style={{ width: "100%" }} /></Form.Item></>}
                <Form.Item name="second_court_enabled" valuePropName="checked" wrapperCol={{ offset: 5, span: 17 }}><Checkbox>二审法院信息</Checkbox></Form.Item>
                {secondCourtEnabled && <><Form.Item label="法院" name="second_court_name"><Select showSearch optionFilterProp="label" options={courtOptions}/></Form.Item><Form.Item label="法庭" name="second_court_courtroom"><Input /></Form.Item><Form.Item label="法官" name="second_court_judge"><Select allowClear showSearch optionFilterProp="label" options={officersForCourt(secondCourtName, "法官")} placeholder="请先选择法院" /></Form.Item><Form.Item label="书记员" name="second_court_clerk"><Select allowClear showSearch optionFilterProp="label" options={officersForCourt(secondCourtName, "书记员")} placeholder="请先选择法院" /></Form.Item><Form.Item label="案号" name="second_court_case_no"><Input /></Form.Item><Form.Item label="立案日期" name="second_court_filing_date"><DatePicker style={{ width: "100%" }} /></Form.Item><Form.Item label="开庭日期" name="second_court_hearing_date"><DatePicker style={{ width: "100%" }} /></Form.Item></>}
                <Form.Item name="retrial_court_enabled" valuePropName="checked" wrapperCol={{ offset: 5, span: 17 }}><Checkbox>再审法院信息</Checkbox></Form.Item>
                {retrialCourtEnabled && <><Form.Item label="法院" name="retrial_court_name"><Select showSearch optionFilterProp="label" options={courtOptions}/></Form.Item><Form.Item label="法庭" name="retrial_court_courtroom"><Input /></Form.Item><Form.Item label="法官" name="retrial_court_judge"><Select allowClear showSearch optionFilterProp="label" options={officersForCourt(retrialCourtName, "法官")} placeholder="请先选择法院" /></Form.Item><Form.Item label="书记员" name="retrial_court_clerk"><Select allowClear showSearch optionFilterProp="label" options={officersForCourt(retrialCourtName, "书记员")} placeholder="请先选择法院" /></Form.Item><Form.Item label="案号" name="retrial_court_case_no"><Input /></Form.Item><Form.Item label="立案日期" name="retrial_court_filing_date"><DatePicker style={{ width: "100%" }} /></Form.Item><Form.Item label="开庭日期" name="retrial_court_hearing_date"><DatePicker style={{ width: "100%" }} /></Form.Item></>}
                <Form.Item label="司法机关备注" name="judicial_remark"><Input.TextArea rows={2} /></Form.Item><Form.Item label="案情说明" name="description"><Input.TextArea rows={3} /></Form.Item>
              </div></div>
            )}
            <div className="case-create-actions">
              <Space>
                {createStep === 0 && <Button type="primary" loading={createSubmitting} onClick={advanceCreateStep}>下一步</Button>}
                {createStep === 1 && (isCounselCreate
                  ? <Button type="primary" loading={createSubmitting} onClick={() => void saveLitigants(true)}>完成</Button>
                  : <><Button type="primary" loading={createSubmitting} onClick={advanceCreateStep}>下一步</Button>{!isAdministrativeCreate && <Button loading={createSubmitting} onClick={() => void saveLitigants(true)}>完成</Button>}</>)}
                {createStep === 2 && <Button type="primary" loading={createSubmitting} onClick={finishCreateFlow}>完成</Button>}
              </Space>
            </div>
            <Form.Item name="owner" hidden><Input /></Form.Item><Form.Item name="case_type" hidden><Input /></Form.Item>
          </Form>
        </div>
      )}
      {specialMode ? <Card className="panel case-original-panel case-special-panel" title={specialTitle[specialMode]} extra={specialMode==="execution"?<Space><Button type="link" onClick={()=>document.querySelector('.case-special-query')?.classList.remove('case-query-hidden')}>高级搜索</Button><Button type="link" onClick={()=>document.querySelector('.case-special-query')?.classList.add('case-query-hidden')}>普通搜索</Button></Space>:null}>
        {specialMode==="invoice"&&<div className="case-invoice-import"><input ref={caseUploadRef} hidden type="file" accept=".xlsx,.xls,.csv,.pdf,.zip" onChange={event=>uploadCaseInvoiceFile(event.target.files?.[0])}/><Space><Button onClick={()=>caseUploadRef.current?.click()}>上传文件</Button><Button type="primary" onClick={startCaseInvoiceImport}>开始导入</Button></Space></div>}
        {specialMode!=="invoice"&&specialMode!=="stage"&&<Form form={caseQueryForm} className="case-special-query" onFinish={values=>setCaseQuery(values)}>
          {(specialFilters[specialMode]||[]).map(([key,label,type])=><Form.Item key={key} name={key} label={label}>{type==="date"?<DatePicker.RangePicker/>:type==="select"?<Select allowClear options={["民事争议","刑事案件","行政案件及国家赔偿","法律顾问","仲裁"].map(value=>({value,label:value}))}/>:<Input/>}</Form.Item>)}
          <Form.Item className="case-special-query-actions"><Space><Button type="primary" htmlType="submit">查询</Button><Button onClick={()=>{caseQueryForm.resetFields();setCaseQuery({})}}>{["unclaimed","refund","receipt"].includes(specialMode)?"清空":"重置"}</Button></Space></Form.Item>
        </Form>}
        {specialMode==="stage"&&<div className="case-stage-query"><DatePicker picker="month" defaultValue={dayjs()}/><Button type="primary" onClick={()=>void load()}>查询</Button><Button onClick={exportStageStatistics}>导出统计</Button></div>}
        {specialMode!=="invoice"&&<input ref={caseUploadRef} hidden type="file" onChange={event=>uploadCaseFile(event.target.files?.[0])}/>} 
        <Table className="case-original-table" rowKey="id" size="small" loading={loading} columns={specialColumns[specialMode]} dataSource={specialRows} rowSelection={specialMode==="invoice"||specialMode==="stage"?undefined:{selectedRowKeys:selectedCaseKeys,onChange:setSelectedCaseKeys}} scroll={{x:specialMode==="stage"?800:1500}} pagination={{pageSize:20,showTotal:total=>`共有${total}条`}} />
        {specialMode!=="invoice"&&specialMode!=="stage"&&<div className="case-bottom-actions"><Space>
          {(specialMode==="schedule"||specialMode==="execution"||specialMode==="unclaimed")&&<Button onClick={exportCases}>导出{specialMode==="schedule"?"案件":""}</Button>}
          {specialMode==="refund"&&<Button onClick={()=>void exportSpecialRecords("refund","退费查询.csv")}>导出</Button>}
          {specialMode==="refund"&&<Dropdown menu={{items:[{key:"view",label:"案件任务"},{key:"export",label:"导出案件打印表"}],onClick:({key})=>{if(key==="export")void exportCases();else if(selectedSpecialRow)void openSpecialCaseTasks({case_record_id:selectedSpecialRow.data.case_record_id||selectedSpecialRow.data.case_id,case_no:selectedSpecialRow.data.case_no||selectedSpecialRow.serial_no});else message.warning("请先选择退费记录")}}}><Button>更多操作</Button></Dropdown>}
          {specialMode==="refund"&&<Button onClick={operateRefund}>退费操作</Button>}
          {specialMode==="receipt"&&<Button onClick={()=>selectedCase?caseUploadRef.current?.click():message.warning("请先选择案件")}>批量上传</Button>}
          {specialMode==="unclaimed"&&<Button onClick={markCommissionPaid}>标识提成已发</Button>}
          {specialMode==="schedule"&&<Button onClick={()=>void openSelectedScheduleHearing()}>更多操作</Button>}
          {specialMode==="execution"&&<Button onClick={()=>selectedCase?openProgress(selectedCase):message.warning("请先选择案件")}>更多操作</Button>}
          {specialMode==="unclaimed"&&<Button onClick={()=>selectedCase?openCaseTasks(selectedCase):message.warning("请先选择案件")}>更多操作</Button>}
        </Space></div>}
      </Card> : originalArchiveMode ? <Card className="panel case-original-panel" title={archiveDone?"已审核":archiveRefused?"已拒绝":"待审核"}>
        <Form form={caseQueryForm} className="case-archive-query" layout="inline" onFinish={values=>setCaseQuery(values)}>
          <Form.Item label="原告/申请人/公诉机关" name="plaintiff"><Input /></Form.Item><Form.Item label="案号" name="serial_no"><Input /></Form.Item><Form.Item label="律师助理" name="assistant"><Input /></Form.Item><Form.Item label="法院/机构" name="court"><Input /></Form.Item>
          <Form.Item label="被告/被申请人" name="defendant"><Input /></Form.Item><Form.Item label="公证书号" name="notary_no"><Input /></Form.Item><Form.Item label="开庭律师" name="hearing_lawyer"><Input /></Form.Item><Form.Item label={archiveDone||archiveRefused?"审核时间":"开庭时间"} name="review_range"><DatePicker.RangePicker /></Form.Item>
          <Form.Item label="第三人/受害人" name="third_party"><Input /></Form.Item><Form.Item label="经办律师" name="handling_lawyer"><Input /></Form.Item><Form.Item label="提交人" name="submitter"><Input /></Form.Item><Form.Item label="提交时间" name="submit_range"><DatePicker.RangePicker /></Form.Item>
          <Form.Item className="case-archive-query-actions"><Space><Button type="primary" htmlType="submit">查询</Button><Button onClick={()=>{caseQueryForm.resetFields();setCaseQuery({})}}>重置</Button></Space></Form.Item>
        </Form>
        <Table className="case-original-table" rowKey="id" size="small" loading={loading} columns={originalArchiveColumns} dataSource={originalArchiveRows} rowSelection={{selectedRowKeys:selectedCaseKeys,onChange:setSelectedCaseKeys}} scroll={{x:archiveCaseTableScrollX}} pagination={{pageSize:20,showTotal:total=>`共有${total}条`}} />
        <div className="case-bottom-actions"><Space wrap>
          <Button onClick={exportCases}>导出全部（CSV）</Button>
          <Button onClick={exportArchiveManifest}>导出选中归档清单（Excel）</Button>
          <Dropdown
            menu={{
              items: selectedCase ? [
                { key: "tasks", label: "案件任务" },
                ...(selectedCaseCapability.can_archive ? [{ key: "archive", label: "归档检查" }] : []),
                ...(!archiveDone && !archiveRefused && isArchiveManager ? [{ key: "approve", label: "通过归档审核" }, { key: "reject", label: "驳回归档审核" }] : []),
                ...(archiveDone && selectedCaseCapability.can_edit_basic ? [{ key: "unarchive-request", label: "申请解档" }] : []),
                ...(archiveDone && isArchiveManager ? [{ key: "unarchive-approve", label: "通过解档审批" }, { key: "unarchive-reject", label: "驳回解档审批" }] : []),
              ] : [{ key: "select", label: "请先选择一条案件", disabled: true }],
              onClick: ({ key }) => {
                if (!selectedCase) return message.warning("请先选择一条案件");
                if (key === "tasks") openCaseTasks(selectedCase);
                if (key === "archive") void openArchive(selectedCase);
                if (key === "approve" || key === "reject") {
                  if (!isArchiveManager) return message.warning("当前账号没有归档审核权限");
                  if (selectedCase.status !== "待归档审核") return message.warning("只有待归档审核案件可执行审核");
                  reviewForm.resetFields();
                  setReviewing({ row: selectedCase, approved: key === "approve" });
                }
                if (key === "unarchive-request") void requestUnarchive(selectedCase);
                if (key === "unarchive-approve" || key === "unarchive-reject") {
                  if (!isArchiveManager) return message.warning("当前账号没有解档审批权限");
                  if (selectedCase.data.unarchive_request?.status !== "待审批") return message.warning("该案件没有待审批的解档申请");
                  void reviewUnarchive(selectedCase, key === "unarchive-approve");
                }
              },
            }}
          ><Button>更多操作</Button></Dropdown>
          {!archiveDone && !archiveRefused && isArchiveManager && <Button onClick={() => {
            if (!selectedCase) return message.warning("请先选择一条案件");
            reviewForm.resetFields();
            setReviewing({ row: selectedCase, approved: true });
          }}>归档审核</Button>}
          {archiveDone && selectedCaseCapability.can_edit_basic && <Button onClick={() => selectedCase ? void requestUnarchive(selectedCase) : message.warning("请先选择一条案件")}>申请解档</Button>}
          {archiveDone && isArchiveManager && <Button onClick={() => {
            if (!selectedCase) return message.warning("请先选择一条案件");
            if (selectedCase.data.unarchive_request?.status !== "待审批") return message.warning("该案件没有待审批的解档申请");
            void reviewUnarchive(selectedCase, true);
          }}>解档审批</Button>}
        </Space></div>
      </Card> : originalListMode && <div className="case-original-layout">
        <aside className="case-phase-panel"><div className="case-phase-title">案件阶段</div>{phaseItems.map(([label,count])=><button key={label} type="button" onClick={()=>{caseQueryForm.setFieldValue("status",label);setCaseQuery({...caseQuery,status:String(label)})}}>📁 {label}【{count}】</button>)}</aside>
        <Card className="panel case-original-panel" title="案件列表" extra={<Button type="link" onClick={()=>document.querySelector('.case-advanced-query')?.classList.toggle('case-query-expanded')}>高级搜索</Button>}>
          <Form form={caseQueryForm} className="case-advanced-query case-query-expanded" onFinish={(values)=>{setCaseQuery(values);if(counselListMode)void loadCounselCases(values,1,counselPageSize);}}>
            {counselListMode ? <>
              <Form.Item label="客户" name="customer"><Input placeholder="客户"/></Form.Item><Form.Item label="案号" name="serial_no"><Input placeholder="案号"/></Form.Item><Form.Item label="关键字" name="keyword"><Input placeholder="案号、案件名称、客户名称"/></Form.Item><Form.Item label="顾问期间" name="counsel_range"><DatePicker.RangePicker /></Form.Item>
              <Form.Item label="顾问类型" name="counsel_type"><Input placeholder="顾问类型"/></Form.Item><Form.Item label="案件阶段" name="status"><Input placeholder="案件阶段"/></Form.Item><Form.Item label="经办律师" name="handling_lawyer"><Input placeholder="经办律师"/></Form.Item><Form.Item label="律师助理" name="assistant"><Input placeholder="律师助理"/></Form.Item><Form.Item label="文档名称" name="document_name"><Input placeholder="文档名称"/></Form.Item>
            </> : <>
              <Form.Item label="原告" name="plaintiff"><Input placeholder="原告"/></Form.Item><Form.Item label="案件编号" name="serial_no"><Input placeholder="案件编号"/></Form.Item><Form.Item label="取证机构" name="evidence_org"><Input placeholder="取证机构"/></Form.Item><Form.Item label="关键字" name="keyword"><Input placeholder="案号、法院号、案件名、客户名"/></Form.Item>
              <Form.Item label="被告" name="defendant"><Input placeholder="被告"/></Form.Item><Form.Item label="经办律师" name="handling_lawyer"><Input placeholder="经办律师"/></Form.Item><Form.Item label="公证书号" name="notary_no"><Input placeholder="公证书号"/></Form.Item><Form.Item label="案件阶段" name="status"><Input placeholder="案件阶段"/></Form.Item>
              <Form.Item label="开庭律师" name="hearing_lawyer"><Input placeholder="开庭律师"/></Form.Item><Form.Item label="律师助理" name="assistant"><Input placeholder="律师助理"/></Form.Item><Form.Item label="调查员" name="investigator"><Input placeholder="调查员"/></Form.Item><Form.Item label="法院名称" name="court"><Input placeholder="法院名称"/></Form.Item>
              <Form.Item label="案源时间" name="source_range"><DatePicker.RangePicker /></Form.Item><Form.Item label="侵权渠道" name="channel"><Input placeholder="侵权渠道"/></Form.Item><Form.Item label="仓库" name="warehouse"><Input placeholder="仓库"/></Form.Item><Form.Item label="文档名称" name="document_name"><Input placeholder="文档名称"/></Form.Item>
              <Form.Item label="开庭时间" name="hearing_range"><DatePicker.RangePicker /></Form.Item><Form.Item label="侵权区域" name="area"><Input placeholder="侵权区域"/></Form.Item><Form.Item label="库位" name="location"><Input placeholder="库位"/></Form.Item><Form.Item label="日志内容" name="log_content"><Input placeholder="日志内容"/></Form.Item>
            </>}
            <Form.Item className="case-query-buttons"><Space><Button type="primary" htmlType="submit">查询</Button><Button onClick={()=>{caseQueryForm.resetFields();setCaseQuery({});if(counselListMode)void loadCounselCases({},1,counselPageSize);}}>重置</Button></Space></Form.Item>
          </Form>
          <input ref={caseUploadRef} hidden type="file" onChange={event=>uploadCaseFile(event.target.files?.[0])}/>
          <Table className="case-original-table" rowKey="id" size="small" loading={loading} columns={counselListMode?counselCaseColumns:originalCaseColumns} dataSource={counselListMode?counselCases:originalCases} rowSelection={{selectedRowKeys:selectedCaseKeys,onChange:setSelectedCaseKeys}} scroll={{x:counselListMode?counselCaseTableScrollX:originalCaseTableScrollX}} pagination={counselListMode?{current:counselPage,pageSize:counselPageSize,total:counselTotal,showSizeChanger:true,pageSizeOptions:[10,15,20,50,100,200],showTotal:total=>`共有${total}条`}:{pageSize:10,showSizeChanger:true,pageSizeOptions:[10,15,20,50,100,200],showTotal:total=>`共有${total}条`}} onChange={(pagination,_filters,sorter:any)=>{if(!counselListMode)return;const nextQuery={...caseQuery,sort_order:sorter?.order==="ascend"?"case_no_asc":sorter?.order==="descend"?"case_no_desc":"updated_desc"};setCaseQuery(nextQuery);void loadCounselCases(nextQuery,pagination.current||1,pagination.pageSize||counselPageSize);}}/>
          <div className="case-bottom-actions"><Space size={5} wrap>
            {counselListMode?<><Button onClick={()=>void exportCounselCases(true)}>导出选中（CSV）</Button><Button onClick={()=>void exportCounselCases(false)}>导出全部（CSV）</Button></>:<><Button onClick={()=>exportSelectedCasesExcel(true)}>导出选中（Excel）</Button><Button onClick={()=>exportSelectedCasesExcel(false)}>导出当前查询（Excel）</Button><Button onClick={exportCaseQrWord}>导出选中二维码（Word）</Button><Button onClick={exportCases}>导出全部（CSV）</Button></>}
            {selectedCaseCapability.can_upload_attachment && <Select
              aria-label="上传材料分类"
              value={caseUploadCategory}
              onChange={setCaseUploadCategory}
              style={{ width: 150 }}
              options={caseFileTypeOptions}
            />}
            {selectedCaseCapability.can_upload_attachment && <Button onClick={()=>caseUploadRef.current?.click()}>上传文件</Button>}
            {["admin","manager"].includes(profile.role||"")&&<Button onClick={()=>{if(!selectedCase)return message.warning("请先选择案件");if(selectedCase.status!=="待立案审批")return message.warning("只有待立案审批案件可以审核");void reviewCaseCreation(selectedCase,true)}}>立案审批通过</Button>}
            {["admin","manager"].includes(profile.role||"")&&<Button danger onClick={()=>{if(!selectedCase)return message.warning("请先选择案件");if(selectedCase.status!=="待立案审批")return message.warning("只有待立案审批案件可以审核");void reviewCaseCreation(selectedCase,false)}}>立案审批驳回</Button>}
            {counselListMode&&<>
              <Button onClick={()=>selectedCase?void openCounselDetail(selectedCase):message.warning("请先选择案件")}>查看详情</Button>
              {(["admin","manager"].includes(profile.role||""))&&<Button onClick={()=>{if(!selectedCaseKeys.length)return message.warning("请选择需要修改的案件");batchUpdateForm.resetFields();setBatchUpdateOpen(true);}}>批量修改</Button>}
              {canCreateSelectedCaseFees&&<Button onClick={()=>{batchFeeForm.resetFields();batchFeeForm.setFieldsValue({expense_scope:"律所",expense_subtype:"官费",handler:profile.username});setBatchFeeOpen(true);}}>批量新增费用</Button>}
            </>}
            <Dropdown
              trigger={["click"]}
              menu={{
                items: selectedCase ? [
                  ...(counselListMode && selectedCaseCapability.can_edit_basic ? [{ key: "edit", label: "修改基本信息" }] : []),
                  { key: "view", label: "案件任务" },
                  ...(selectedCaseCapability.can_create_finance ? [{ key: "fee", label: "新增案件费用" }] : []),
                  ...(selectedCaseCapability.can_assign_team ? [{ key: "assign", label: "人员分配" }] : []),
                  ...(!counselListMode && selectedCaseCapability.can_update_progress ? [{ key: "progress", label: "登记进展" }] : []),
                  ...(!counselListMode && selectedCaseCapability.can_manage_hearing ? [{ key: "hearing", label: "开庭排期" }] : []),
                  ...(selectedCaseCapability.can_archive ? [{ key: "archive", label: "案件归档" }] : []),
                ] : [{ key: "select", label: "请先选择案件", disabled: true }],
                onClick: ({ key }) => {
                  if (!selectedCase) return message.warning("请先选择案件");
                  if (key === "edit") openCounselEdit(selectedCase);
                  if (key === "view") openCaseTasks(selectedCase);
                  if (key === "fee") openCaseFee(selectedCase);
                  if (key === "assign") openAssign(selectedCase);
                  if (key === "progress") openProgress(selectedCase);
                  if (key === "hearing") openHearing(selectedCase);
                  if (key === "archive") void openArchive(selectedCase);
                },
              }}
            ><Button>更多操作 ▾</Button></Dropdown>
          </Space></div>
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
            dataSource={cases}
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
          <Form.Item label="存放位置" name="deposit_address"><Input /></Form.Item>
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
        open={Boolean(feeCase)}
        title={`新增案件费用：${feeCase?.serial_no || ""}`}
        okText="创建费用草稿"
        cancelText="取消"
        onOk={createCaseFee}
        onCancel={() => setFeeCase(null)}
      >
        <Form form={feeForm} layout="vertical">
          <Form.Item label="费用名称" name="title" rules={[{ required: true }]}><Input /></Form.Item>
          <div className="form-grid">
            <Form.Item label="费用归属" name="expense_scope" rules={[{ required: true }]}><Select options={["律所", "平台", "内部"].map(value => ({ value, label: value }))} onChange={(value) => feeForm.setFieldsValue({ expense_subtype: value === "内部" ? "内部费用" : "官费", fee_type: value === "内部" ? "内部费用" : "官方费用" })} /></Form.Item>
            <Form.Item label="费用类别" name="expense_subtype" rules={[{ required: true }]}><Select options={(feeExpenseScope === "内部" ? ["内部费用"] : ["官费", "第三方费用", "代理费", "其他费用"]).map(value => ({ value, label: value }))} onChange={(value) => feeForm.setFieldValue("fee_type", ({ "官费": "官方费用", "第三方费用": "其他费用", "代理费": "代理费", "其他费用": "其他费用", "内部费用": "内部费用" } as Record<string, string>)[value])} /></Form.Item>
            <Form.Item label="金额" name="amount" rules={[{ required: true }]}><InputNumber min={0.01} precision={2} style={{ width: "100%" }} /></Form.Item>
            <Form.Item name="fee_type" hidden><Input /></Form.Item>
            <Form.Item label="经办人员" name="handler" rules={[{ required: true }]}><Input /></Form.Item>
            <Form.Item label="收款单位" name="payee"><Input /></Form.Item>
            <Form.Item label="缴费法院/机构" name="court"><Input /></Form.Item>
            <Form.Item label="缴费通知文号" name="document_no"><Input /></Form.Item>
          </div>
          <Form.Item label="说明" name="description"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
      <Modal open={Boolean(caseTaskCreateCase)} title={`发布案件任务：${caseTaskCreateCase?.serial_no || ""}`} okText="发布任务" cancelText="取消" onOk={createCaseTask} onCancel={() => { setCaseTaskCreateCase(null); taskForm.resetFields(); }} destroyOnHidden>
        <Alert type="info" showIcon title="任务创建后会自动关联当前案件并即时回填到“案件任务”页签。" style={{ marginBottom: 16 }} />
        <Form form={taskForm} layout="vertical">
          <Form.Item label="任务名称" name="title" rules={[{ required: true, message: "请输入任务名称" }]}><Input /></Form.Item>
          <div className="form-grid">
            <Form.Item label="负责人" name="owner" rules={[{ required: true, message: "请输入负责人账号" }]}><Input /></Form.Item>
            <Form.Item label="截止日期" name="deadline" rules={[{ required: true, message: "请选择截止日期" }]}><DatePicker style={{ width: "100%" }} /></Form.Item>
            <Form.Item label="优先级" name="priority"><Select options={["普通", "紧急", "特急"].map(value => ({ value, label: value }))} /></Form.Item>
            <Form.Item label="协作人" name="collaborators"><Select mode="tags" tokenSeparators={[",", "，"]} placeholder="输入账号后回车" /></Form.Item>
          </div>
          <Form.Item label="任务说明" name="description"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>
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
      <Drawer
        width="100%"
        rootClassName={isCaseDetailView ? "case-detail-static-root" : undefined}
        className="case-detail-drawer"
        getContainer={false}
        mask={false}
        rootStyle={{position:"absolute",inset:0,height:"calc(100vh - 88px)"}}
        open={Boolean(viewingCounselCase)}
        title={`${viewingCounselCase?.data.case_type || "案件"}详情：${viewingCounselCase?.serial_no || ""}`}
        onClose={() => isCaseDetailView ? onNavigate?.("case-mine-civil") : setViewingCounselCase(null)}
        extra={viewingCounselCase&&<Space wrap>
          {counselDetailCapabilities.can_update_progress && <Button disabled={["待归档审核","已归档"].includes(viewingCounselCase.status)} onClick={()=>openProgress(viewingCounselCase)}>登记进展</Button>}
          {counselDetailCapabilities.can_manage_hearing && <Button disabled={["待归档审核","已归档"].includes(viewingCounselCase.status)} onClick={()=>openHearing(viewingCounselCase)}>开庭排期</Button>}
          {counselDetailCapabilities.can_assign_team && <Button disabled={["待归档审核","已归档"].includes(viewingCounselCase.status)} onClick={()=>openAssign(viewingCounselCase)}>人员分配</Button>}
          {counselDetailCapabilities.can_edit_basic && viewingCounselCase.data.case_type === "法律顾问" && <Button disabled={["待归档审核","已归档"].includes(viewingCounselCase.status)} onClick={()=>openCounselEdit(viewingCounselCase)}>修改基本信息</Button>}
          {counselDetailCapabilities.can_edit_basic && isNormalEditableCase(viewingCounselCase) && <Button disabled={["待归档审核","已归档"].includes(viewingCounselCase.status)} onClick={()=>openNormalCaseEdit(viewingCounselCase)}>修改基本信息</Button>}
          {counselDetailCapabilities.can_edit_basic && viewingCounselCase.data.case_type === "仲裁" && <Button disabled={["待归档审核","已归档"].includes(viewingCounselCase.status)} onClick={()=>openArbitrationBasicEdit(viewingCounselCase)}>修改基本信息</Button>}
          {counselDetailCapabilities.can_edit_basic && viewingCounselCase.data.case_type === "刑事案件" && <Dropdown menu={{items:[{key:"litigants",label:"修改当事人"},{key:"public-security",label:"修改公安机关"},{key:"procuratorates",label:"修改检察院"},{key:"courts",label:"修改审级法院"}],onClick:({key})=>openCriminalMaintenance(viewingCounselCase,key as "litigants"|"public-security"|"procuratorates"|"courts")}}><Button disabled={["待归档审核","已归档"].includes(viewingCounselCase.status)}>维护刑事资料</Button></Dropdown>}
          {counselDetailCapabilities.can_write && !["待归档审核","已归档","已合并"].includes(viewingCounselCase.status) && <Dropdown menu={{ items: caseDocumentTypes.map(([key, label]) => ({ key, label })), onClick: ({ key }) => void generateCaseDocument(String(key)) }}><Button icon={<FileTextOutlined />}>生成案件文书</Button></Dropdown>}
          {counselDetailCapabilities.can_duplicate_case && <Button onClick={()=>Modal.confirm({title:`复制案件：${viewingCounselCase.serial_no}`,content:"将只复制案件基础信息并生成新案号；任务、附件、费用、提醒、排期和历史记录不会复制。",okText:"确认复制",cancelText:"取消",onOk:()=>duplicateCase(viewingCounselCase)})}>复制案件</Button>}
          {counselDetailCapabilities.can_merge_case && !["待归档审核","已归档","已合并"].includes(viewingCounselCase.status) && <Button onClick={() => { mergeCaseForm.resetFields(); setMergingCase(viewingCounselCase); }}>合并案件</Button>}
          {counselDetailCapabilities.can_edit_basic && viewingCounselCase.data.case_type === "民事案件" && !["待归档审核","已归档","已合并"].includes(viewingCounselCase.status) && <Button onClick={() => { notaryInfoForm.setFieldsValue({ notary_nos: viewingCounselCase.data.notary_nos || viewingCounselCase.data.notary_no || "", deposit_address: viewingCounselCase.data.deposit_address || "", comment: "" }); setNotaryInfoCase(viewingCounselCase); }}>修改公证信息</Button>}
          {counselDetailCapabilities.can_edit_basic && ["民事案件","刑事案件","行政案件及国家赔偿","仲裁"].includes(viewingCounselCase.data.case_type) && !["待归档审核","已归档","已合并"].includes(viewingCounselCase.status) && <Button onClick={() => { settlementAmountForm.setFieldsValue({ litigation_amount: viewingCounselCase.data.litigation_amount ?? 0, settlement_amount: viewingCounselCase.data.settlement_amount ?? 0, comment: "" }); setSettlementAmountCase(viewingCounselCase); }}>修改诉讼/判决金额</Button>}
        </Space>}
      >
        {viewingCounselCase&&<div className="case-detail-workbench">
          <Card size="small" title="基本信息" className="case-counsel-detail-card">
            <div className="form-grid">
              <p><strong>案件编号：</strong>{viewingCounselCase.serial_no}</p>
              <p><strong>案件类型：</strong>{viewingCounselCase.data.case_type||"—"}</p>
              <p><strong>案件阶段：</strong>{viewingCounselCase.status||"—"}</p>
              <p><strong>案件名称：</strong>{viewingCounselCase.title}</p>
              <p><strong>案源人：</strong>{viewingCounselCase.data.business_owner||viewingCounselCase.data.source_person||viewingCounselCase.owner||"—"}</p>
              <p><strong>客户：</strong><Button type="link" className="case-cell-link" onClick={() => openRelatedCustomer({ id: Number(viewingCounselCase.data.customer_id) || undefined, serial_no: viewingCounselCase.data.customer_no, title: viewingCounselCase.customer })}>{viewingCounselCase.customer || "—"}</Button></p>
              <p><strong>经办律师：</strong>{(viewingCounselCase.data.handling_lawyers||[]).join("、")||"—"}</p>
              <p><strong>合同号：</strong>{viewingCounselCase.data.contract_no ? <Button type="link" className="case-cell-link" onClick={() => openRelatedContract({ id: Number(viewingCounselCase.data.contract_record_id) || undefined, serial_no: viewingCounselCase.data.contract_no })}>{viewingCounselCase.data.contract_no}</Button> : "—"}</p>
              <p><strong>律师助理：</strong>{viewingCounselCase.data.assistant||"—"}</p>
              {String(viewingCounselCase.data.clue_no || viewingCounselCase.data.investigation_clue || viewingCounselCase.data.source_clue_no || "").trim() && <p><strong>关联线索：</strong><Button type="link" className="case-cell-link" onClick={() => openRelatedClue({ id: Number(viewingCounselCase.data.clue_record_id || viewingCounselCase.data.investigation_clue_id) || undefined, serial_no: viewingCounselCase.data.clue_no || viewingCounselCase.data.investigation_clue || viewingCounselCase.data.source_clue_no })}>{viewingCounselCase.data.investigation_clue_nos?.join("、") || viewingCounselCase.data.clue_no || viewingCounselCase.data.investigation_clue || viewingCounselCase.data.source_clue_no}</Button></p>}
              {String(viewingCounselCase.data.original_case_no || viewingCounselCase.data.origin_case_no || viewingCounselCase.data.source_case_no || "").trim() && <p><strong>原案件号：</strong><Button type="link" className="case-cell-link" onClick={() => openRelatedOriginalCase({ id: Number(viewingCounselCase.data.original_case_record_id || viewingCounselCase.data.origin_case_record_id || viewingCounselCase.data.source_case_record_id) || undefined, serial_no: viewingCounselCase.data.original_case_no || viewingCounselCase.data.origin_case_no || viewingCounselCase.data.source_case_no })}>{viewingCounselCase.data.original_case_no || viewingCounselCase.data.origin_case_no || viewingCounselCase.data.source_case_no}</Button></p>}
              {viewingCounselCase.data.case_type === "法律顾问" ? <><p><strong>顾问类型：</strong>{viewingCounselCase.data.counsel_type||"—"}</p><p><strong>顾问期限：</strong>{viewingCounselCase.data.counsel_start||"—"} 至 {viewingCounselCase.data.counsel_end||"—"}</p></> : <><p><strong>原告/申请人：</strong>{viewingCounselCase.data.plaintiff||viewingCounselCase.customer||"—"}</p><p><strong>被告/被申请人：</strong>{viewingCounselCase.data.opponent||"—"}</p><p><strong>法院/机构：</strong>{viewingCounselCase.data.court||viewingCounselCase.data.first_court_name||"—"}</p><p><strong>案由/罪名：</strong>{viewingCounselCase.data.cause_or_charge||"—"}</p><p><strong>调查员：</strong>{viewingCounselCase.data.investigator||"—"}</p>{viewingCounselCase.data.case_type === "行政案件及国家赔偿" && <p><strong>权利类型：</strong>{viewingCounselCase.data.right_type||"—"}</p>}</>}
            </div>
          </Card>
          <div className="case-detail-body-grid">
            <aside className="case-detail-doc-tree">
              <button className={`case-doc-all ${!activeCounselDocCategory?"case-doc-active":""}`} onClick={()=>selectCounselDocCategory("")}>全部文档</button>
              {counselDocTree.map((item,index)=>(
                <button
                  key={`${item.category}-${item.type}-${index}`}
                  className={`${item.type==="child"?"case-doc-child":"case-doc-folder"} ${item.type==="folder-open"?"case-doc-folder-open":""} ${activeCounselDocCategory===item.category?"case-doc-active":""}`}
                  onClick={()=>selectCounselDocCategory(item.category)}
                  title={`查看${item.label}`}
                >
                  {item.label}
                </button>
              ))}
            </aside>
            <div className="case-detail-tab-area">
          <Tabs
            items={[
              {key:"documents",label:"文档信息",children:<>
                <input ref={counselDetailUploadRef} hidden type="file" onChange={event=>void uploadCounselDetailAttachment(event.target.files?.[0])}/>
                <Space wrap style={{marginBottom:10}}>
                  <Select value={counselUploadCategory} style={{width:180}} onChange={setCounselUploadCategory} options={caseFileTypeOptions}/>
                  {counselDetailCapabilities.can_upload_attachment && <Button type="primary" onClick={()=>counselDetailUploadRef.current?.click()}>上传文件</Button>}
                  <Button onClick={()=>void downloadCounselAttachments()}>下载选中（ZIP）</Button>
                  {counselDetailCapabilities.can_delete_attachment && <Button danger onClick={deleteCounselAttachments}>删除选中</Button>}
                  {activeCounselDocCategory&&<Tag color="green">当前目录：{activeCounselDocCategory}</Tag>}
                </Space>
                <Table rowKey="id" size="small" pagination={false} scroll={{x:940}} dataSource={filteredCounselDetailAttachments} rowSelection={{selectedRowKeys:selectedCounselAttachmentKeys,onChange:setSelectedCounselAttachmentKeys}} columns={[
                  {title:"文件名称",dataIndex:"original_name",width:280,ellipsis:true},
                  {title:"分类",dataIndex:"category",width:150,ellipsis:true},
                  {title:"上传人",dataIndex:"uploader",width:110},
                  {title:"上传时间",dataIndex:"created_at",width:170},
                  {title:"操作",key:"actions",width:280,render:(_:unknown,row:AttachmentRow)=><Space size={0}><Button type="link" onClick={()=>void previewCounselDetailAttachment(row)}>查看</Button><Button type="link" onClick={()=>void downloadCounselDetailAttachment(row)}>下载</Button>{counselDetailCapabilities.can_write&&<Button type="link" onClick={()=>openCounselAttachmentRename(row)}>重命名</Button>}{counselDetailCapabilities.can_write&&/\.docx?$/i.test(row.original_name)&&<Button type="link" onClick={()=>void openCounselAttachmentSeal(row)}>提交用印</Button>}</Space>},
                ]}/>
              </>},
              {key:"firm-fees",label:"律所费用",children:<><Space style={{marginBottom:10}}>{counselDetailCapabilities.can_create_finance&&<Button type="primary" onClick={()=>openCaseFee(viewingCounselCase,"律所")}>新增律所费用</Button>}</Space><Table rowKey="id" size="small" pagination={false} dataSource={financeRows.filter(row=>row.module==="finance"&&row.data.case_no===viewingCounselCase.serial_no&&row.data.expense_scope!=="平台"&&row.data.expense_scope!=="内部"&&!String(row.data.fee_type||"").includes("内部"))} columns={[{title:"费用编号",dataIndex:"serial_no",render:(value:string,row:CaseRow)=><Button type="link" className="case-cell-link" onClick={()=>void openRelatedFee(row)}>{value||"—"}</Button>},{title:"费用名称",dataIndex:"title"},{title:"类型",render:(_:unknown,row:CaseRow)=>row.data.fee_type||""},{title:"金额",render:(_:unknown,row:CaseRow)=>row.data.amount??""},{title:"状态",dataIndex:"status"}]}/></>},
              {key:"platform-fees",label:"平台费用",children:<><Space style={{marginBottom:10}}>{counselDetailCapabilities.can_create_finance&&<Button type="primary" onClick={()=>openCaseFee(viewingCounselCase,"平台")}>新增平台费用</Button>}</Space><Table rowKey="id" size="small" pagination={false} dataSource={financeRows.filter(row=>row.module==="finance"&&row.data.case_no===viewingCounselCase.serial_no&&row.data.expense_scope==="平台")} columns={[{title:"费用编号",dataIndex:"serial_no",render:(value:string,row:CaseRow)=><Button type="link" className="case-cell-link" onClick={()=>void openRelatedFee(row)}>{value||"—"}</Button>},{title:"费用名称",dataIndex:"title"},{title:"金额",render:(_:unknown,row:CaseRow)=>row.data.amount??""},{title:"状态",dataIndex:"status"}]}/></>},
              {key:"internal-fees",label:"内部结算",children:<><Space style={{marginBottom:10}}>{counselDetailCapabilities.can_create_finance&&<Button type="primary" onClick={()=>openCaseFee(viewingCounselCase,"内部")}>新增内部结算</Button>}</Space><Table rowKey="id" size="small" pagination={false} dataSource={financeRows.filter(row=>row.module==="finance"&&row.data.case_no===viewingCounselCase.serial_no&&(row.data.expense_scope==="内部"||String(row.data.fee_type||"").includes("内部")))} columns={[{title:"费用编号",dataIndex:"serial_no",render:(value:string,row:CaseRow)=><Button type="link" className="case-cell-link" onClick={()=>void openRelatedFee(row)}>{value||"—"}</Button>},{title:"费用名称",dataIndex:"title"},{title:"金额",render:(_:unknown,row:CaseRow)=>row.data.amount??""},{title:"状态",dataIndex:"status"}]}/></>},
              {key:"reminders",label:"案件提醒",children:<>{counselDetailCapabilities.can_create_reminder && <Button type="primary" style={{marginBottom:10}} onClick={()=>{reminderForm.resetFields();setReminderOpen(true);}}>新增提醒</Button>}<Table rowKey="id" size="small" pagination={false} dataSource={counselReminders} columns={[{title:"提醒日期",render:(_:unknown,row:CaseReminderRow)=>row.data.reminder_date,width:120},{title:"截止日期",render:(_:unknown,row:CaseReminderRow)=>row.data.deadline,width:120},{title:"提醒内容",dataIndex:"description"},{title:"创建人",dataIndex:"owner",width:110},{title:"操作",width:80,render:(_:unknown,row:CaseReminderRow)=>counselDetailCapabilities.can_delete_reminder?<Button type="link" danger onClick={()=>deleteCounselReminder(row)}>删除</Button>:null}]}/></>},
              {key:"case-logs",label:"案件日志",children:<>{counselDetailCapabilities.can_create_log && <Button type="primary" style={{marginBottom:10}} onClick={()=>{caseLogForm.resetFields();setCaseLogOpen(true);}}>新增日志</Button>}<Table rowKey="id" size="small" pagination={false} dataSource={counselLogs} columns={[{title:"时间",dataIndex:"created_at",width:170},{title:"日志内容",dataIndex:"content"},{title:"记录人",dataIndex:"operator",width:110}]}/></>},
              {key:"logs",label:"系统日志",children:<Table rowKey="id" size="small" pagination={false} dataSource={counselDetailHistory} columns={[{title:"时间",dataIndex:"created_at",width:170},{title:"操作",dataIndex:"action",width:210},{title:"操作人",dataIndex:"operator",width:110},{title:"说明",dataIndex:"comment"}]}/>},
              {key:"tasks",label:"案件任务",children:<><Space style={{marginBottom:10}}>{counselDetailCapabilities.can_create_case_task&&<Button type="primary" onClick={()=>openCaseTaskCreator(viewingCounselCase)}>发布案件任务</Button>}</Space><Table rowKey="id" size="small" pagination={false} tableLayout="fixed" scroll={{x:1130}} dataSource={counselDetailTasks.filter(row=>row.source!=="客户任务")} columns={[{title:"任务编号",dataIndex:"serial_no",width:175,ellipsis:true,render:(value:string,row:TaskRow)=><Button type="link" className="case-cell-link" onClick={()=>openRelatedTask(row)}>{value||"—"}</Button>},{title:"类型",dataIndex:"source",width:100,ellipsis:true},{title:"任务名称",dataIndex:"title",width:230,ellipsis:true,render:(value:string,row:TaskRow)=><Button type="link" className="case-cell-link" onClick={()=>openRelatedTask(row)}>{value||"—"}</Button>},{title:"截止日",dataIndex:"deadline",width:120,ellipsis:true},{title:"剩余时间",width:100,render:(_:unknown,row:TaskRow)=>row.days_remaining===null||row.days_remaining===undefined?"—":`${row.days_remaining} 天`},{title:"发起人",dataIndex:"initiator",width:110,ellipsis:true},{title:"负责人",dataIndex:"owner",width:110,ellipsis:true},{title:"状态",dataIndex:"status",width:100,ellipsis:true}]}/></>},
              {key:"customer-tasks",label:"客户任务",children:<Table rowKey="id" size="small" pagination={false} tableLayout="fixed" scroll={{x:1130}} dataSource={counselDetailTasks.filter(row=>row.source==="客户任务")} columns={[{title:"任务编号",dataIndex:"serial_no",width:175,ellipsis:true,render:(value:string,row:TaskRow)=><Button type="link" className="case-cell-link" onClick={()=>openRelatedTask(row)}>{value||"—"}</Button>},{title:"类型",dataIndex:"source",width:100,ellipsis:true},{title:"任务名称",dataIndex:"title",width:230,ellipsis:true,render:(value:string,row:TaskRow)=><Button type="link" className="case-cell-link" onClick={()=>openRelatedTask(row)}>{value||"—"}</Button>},{title:"截止日",dataIndex:"deadline",width:120,ellipsis:true},{title:"剩余时间",width:100,render:(_:unknown,row:TaskRow)=>row.days_remaining===null||row.days_remaining===undefined?"—":`${row.days_remaining} 天`},{title:"发起人",dataIndex:"initiator",width:110,ellipsis:true},{title:"负责人",dataIndex:"owner",width:110,ellipsis:true},{title:"状态",dataIndex:"status",width:100,ellipsis:true}]}/>},
            ]}
          />
            </div>
            <aside className="case-detail-side-panel">
              <section>
                <div className="case-detail-side-title"><span>案件提醒</span>{counselDetailCapabilities.can_create_reminder && <Button type="link" size="small" onClick={()=>{reminderForm.resetFields();setReminderOpen(true);}}>新增</Button>}</div>
                {counselReminders.length?counselReminders.slice(0,5).map((item)=><p key={item.id}>{item.data.reminder_date || item.data.deadline}　{item.description}</p>):<p className="case-detail-empty">暂无提醒</p>}
              </section>
              <section>
                <div className="case-detail-side-title"><span>案件日志</span>{counselDetailCapabilities.can_create_log && <Button type="link" size="small" onClick={()=>{caseLogForm.resetFields();setCaseLogOpen(true);}}>新增日志</Button>}</div>
                {counselLogs.length?counselLogs.slice(0,5).map((item)=><p key={item.id}>{item.created_at}　{item.content}</p>):<p className="case-detail-empty">暂无日志</p>}
              </section>
            </aside>
          </div>
        </div>}
      </Drawer>
      <Modal
        open={Boolean(attachmentPreview)}
        title={`在线查看：${attachmentPreview?.name || ""}`}
        footer={<Button onClick={closeAttachmentPreview}>关闭</Button>}
        onCancel={closeAttachmentPreview}
        width={attachmentPreview?.kind === "pdf" ? 1000 : 760}
        destroyOnHidden
      >
        {attachmentPreview?.kind === "image" && <img src={attachmentPreview.url} alt={attachmentPreview.name} style={{ display: "block", maxWidth: "100%", maxHeight: "72vh", margin: "0 auto" }} />}
        {attachmentPreview?.kind === "pdf" && <iframe title={attachmentPreview.name} src={attachmentPreview.url} style={{ width: "100%", height: "72vh", border: 0 }} />}
        {(attachmentPreview?.kind === "text" || attachmentPreview?.kind === "docx") && <pre style={{ maxHeight: "70vh", overflow: "auto", margin: 0, whiteSpace: "pre-wrap", overflowWrap: "anywhere", fontFamily: "inherit", lineHeight: 1.7 }}>{attachmentPreview.text}</pre>}
      </Modal>
      <Modal open={Boolean(renamingCounselAttachment)} title={`重命名案件文件：${renamingCounselAttachment?.original_name || ""}`} okText="保存" cancelText="取消" onOk={renameCounselAttachment} onCancel={()=>{setRenamingCounselAttachment(null);attachmentRenameForm.resetFields();}}>
        <Form form={attachmentRenameForm} layout="vertical">
          <Form.Item label="文件名称" name="original_name" rules={[{required:true,message:"请输入文件名称"},{max:255,message:"文件名称不能超过 255 个字符"},{validator:async(_rule,value)=>{const name=String(value||"").trim();if(!name||/[\\\\/]/.test(name))throw new Error("文件名不能为空且不能包含路径");const currentSuffix=renamingCounselAttachment?.original_name.slice(renamingCounselAttachment.original_name.lastIndexOf("."))||"";const nextSuffix=name.slice(name.lastIndexOf("."));if(currentSuffix.toLowerCase()!==nextSuffix.toLowerCase())throw new Error("不能修改文件扩展名");}}]}><Input autoFocus /></Form.Item>
          <Alert type="info" showIcon title="仅修改展示和下载文件名，不会移动或改写原文件内容；保存后会写入案件审计日志。"/>
        </Form>
      </Modal>
      <Modal open={Boolean(sealingCounselAttachment)} title={`案件文件提交用印：${sealingCounselAttachment?.original_name || ""}`} okText="创建正式发文草稿" cancelText="取消" onOk={submitCounselAttachmentSeal} onCancel={()=>{setSealingCounselAttachment(null);caseFileSealForm.resetFields();}} destroyOnHidden>
        <Alert type="info" showIcon message="将复制当前 Word 文件为正式发文附件" description="请明确选择可用印章。创建后仍需在“正式发文”中提交审批，原案件文件不会被修改或移动。" style={{ marginBottom: 12 }} />
        <Form form={caseFileSealForm} layout="vertical">
          <Form.Item label="印章类型" name="seal_asset_id" rules={[{ required: true, message: "请选择可用印章" }]}><Select placeholder="请选择可用印章" options={caseSealAssets.map((asset) => ({ value: asset.id, label: `${asset.seal_type}｜${asset.name}` }))} /></Form.Item>
          <Form.Item label="盖章份数" name="print_quantity" rules={[{ required: true }]}><InputNumber min={1} max={9999} style={{ width: "100%" }} /></Form.Item>
          <Form.Item name="is_electronic_seal" valuePropName="checked"><Checkbox>电子盖章</Checkbox></Form.Item>
          <Form.Item name="is_offline_print" valuePropName="checked"><Checkbox>线下打印盖章</Checkbox></Form.Item>
          <Form.Item name="need_audit" valuePropName="checked"><Checkbox>创建后进入正式发文审批</Checkbox></Form.Item>
          <Form.Item label="备注" name="remark" rules={[{ max: 2000 }]}><Input.TextArea rows={3} maxLength={2000} showCount /></Form.Item>
        </Form>
      </Modal>
      <Modal open={reminderOpen} title={`新增案件提醒：${viewingCounselCase?.serial_no||""}`} okText="确定" cancelText="取消" onOk={createCounselReminder} onCancel={()=>setReminderOpen(false)}>
        <Form form={reminderForm} layout="vertical">
          <div className="form-grid"><Form.Item label="提醒日期" name="reminder_date" rules={[{required:true,message:"请选择提醒日期"}]}><DatePicker style={{width:"100%"}}/></Form.Item><Form.Item label="截止日期" name="deadline" rules={[{required:true,message:"请选择截止日期"}]}><DatePicker style={{width:"100%"}}/></Form.Item></div>
          <Form.Item label="提醒内容" name="content" rules={[{required:true,message:"请输入提醒内容"},{max:1000}]}><Input.TextArea rows={4}/></Form.Item>
          <Alert type="info" showIcon title="提醒日期不能晚于截止日期；保存和删除都会写入案件审计记录。"/>
        </Form>
      </Modal>
      <Modal open={caseLogOpen} title={`新增案件日志：${viewingCounselCase?.serial_no||""}`} okText="确定" cancelText="取消" onOk={createCounselLog} onCancel={()=>setCaseLogOpen(false)}>
        <Form form={caseLogForm} layout="vertical"><Form.Item label="日志内容" name="content" rules={[{required:true,message:"请输入日志内容"},{max:1000}]}><Input.TextArea rows={5}/></Form.Item></Form>
      </Modal>
      <Modal width={680} open={batchUpdateOpen} title={`批量修改法律顾问案件（已选 ${selectedCaseKeys.length} 个）`} okText="确定" cancelText="取消" onOk={submitCounselBatchUpdate} onCancel={()=>setBatchUpdateOpen(false)}>
        <Alert type="warning" showIcon title="只填写需要统一修改的字段；未填写字段保持原值。已进入归档流程的案件会被整体阻断。" style={{marginBottom:12}}/>
        <Form form={batchUpdateForm} layout="vertical">
          <Form.Item label="经办律师" name="handling_lawyers"><Select mode="multiple" showSearch optionFilterProp="label" options={caseLawyerOptions} placeholder="不修改则留空"/></Form.Item>
          <div className="form-grid"><Form.Item label="律师助理" name="assistant"><Select allowClear showSearch optionFilterProp="label" options={caseAssistantOptions} placeholder="不修改则留空"/></Form.Item><Form.Item label="案件阶段" name="case_stage"><Input placeholder="不修改则留空"/></Form.Item></div>
          <Form.Item label="修改说明" name="comment"><Input.TextArea rows={3}/></Form.Item>
        </Form>
      </Modal>
      <Modal width={680} open={batchFeeOpen} title={`批量新增案件费用（已选 ${selectedCaseKeys.length} 个）`} okText="创建费用草稿" cancelText="取消" onOk={submitCounselBatchFee} onCancel={()=>setBatchFeeOpen(false)}>
        <Alert type="info" showIcon title="系统会为每个案件分别创建一条费用草稿，并分别写入案件与费用审计记录。" style={{marginBottom:12}}/>
        <Form form={batchFeeForm} layout="vertical">
          <div className="form-grid">
            <Form.Item label="费用归属" name="expense_scope" rules={[{required:true}]}><Select options={["律所","平台","内部"].map(value=>({value,label:value}))} onChange={(value)=>batchFeeForm.setFieldValue("expense_subtype",value==="内部"?"内部费用":"官费")}/></Form.Item>
            <Form.Item label="费用类型" name="expense_subtype" rules={[{required:true}]}><Select options={(batchExpenseScope==="内部"?["内部费用"]:["官费","第三方费用","代理费","其他费用"]).map(value=>({value,label:value}))}/></Form.Item>
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
          <div className="form-grid">
            <Form.Item label="客户" name="customer_record_id" rules={[{required:true,message:"请选择可见且有效的客户"}]}><Select showSearch optionFilterProp="label" options={caseCustomers.filter(item=>!["公海","已回收"].includes(item.status)).map(item=>({value:item.id,label:`${item.serial_no}｜${item.title}`}))}/></Form.Item>
            <Form.Item label="案件阶段" name="case_phase" rules={[{required:true,message:"请选择案件阶段"}]}><Select options={caseStatuses.map(value=>({value,label:value}))}/></Form.Item>
          </div>
          <Form.Item label={editingNormalCase?.data.case_type === "刑事案件" ? "罪名/案由" : "案由"} name="cause_or_charge" rules={[{required:true,message:"请输入案由或罪名"}]}><Input/></Form.Item>
          <Form.Item label="案件名称" name="title" rules={[{required:true,message:"请输入案件名称"}]}><Input/></Form.Item>
          <div className="form-grid">
            <Form.Item label="经办律师" name="handling_lawyers" rules={[{required:true,message:"请选择系统已创建的在职律师"}]}><Select mode="multiple" showSearch optionFilterProp="label" options={caseLawyerOptions}/></Form.Item>
            <Form.Item label="律师助理" name="assistant"><Select allowClear showSearch optionFilterProp="label" options={caseAssistantOptions}/></Form.Item>
            <Form.Item label="调查员" name="investigator"><Input/></Form.Item>
            {editingNormalCase?.data.case_type === "民事案件" && <Form.Item label="案源人" name="business_owner"><Input/></Form.Item>}
            {editingNormalCase?.data.case_type === "行政案件及国家赔偿" && <Form.Item label="权利类型" name="right_type"><Select allowClear options={rightTypeOptions}/></Form.Item>}
          </div>
          <Form.Item label="关联调查线索" name="investigation_clue_ids"><Select mode="multiple" showSearch optionFilterProp="label" options={caseClues.map(item=>({value:item.id,label:`${item.serial_no}｜${item.title}`}))}/></Form.Item>
          <Form.Item label="修改说明" name="comment"><Input.TextArea rows={3}/></Form.Item>
        </Form>
      </Modal>
      <Modal width={720} open={Boolean(editingArbitrationCase)} title={`修改仲裁案件基本信息：${editingArbitrationCase?.serial_no||""}`} okText="确定" cancelText="取消" onOk={saveArbitrationBasic} onCancel={()=>setEditingArbitrationCase(null)} destroyOnHidden>
        <Alert type="info" showIcon title="仲裁案件使用独立基本信息流程，不复用民事、刑事、行政或法律顾问案件接口。" style={{marginBottom:12}}/>
        <Form form={arbitrationBasicForm} layout="vertical">
          <div className="form-grid"><Form.Item label="客户" name="customer_record_id" rules={[{required:true,message:"请选择可见且有效的客户"}]}><Select showSearch optionFilterProp="label" options={caseCustomers.filter(item=>!["公海","已回收"].includes(item.status)).map(item=>({value:item.id,label:`${item.serial_no}｜${item.title}`}))}/></Form.Item><Form.Item label="案件阶段" name="case_phase" rules={[{required:true,message:"请选择案件阶段"}]}><Select options={caseStatuses.map(value=>({value,label:value}))}/></Form.Item></div>
          <Form.Item label="案由" name="cause_or_charge" rules={[{required:true,message:"请输入案由"}]}><Input/></Form.Item><Form.Item label="案件名称" name="title" rules={[{required:true,message:"请输入案件名称"}]}><Input/></Form.Item>
          <div className="form-grid"><Form.Item label="经办律师" name="handling_lawyers" rules={[{required:true,message:"请选择系统已创建的在职律师"}]}><Select mode="multiple" showSearch optionFilterProp="label" options={caseLawyerOptions}/></Form.Item><Form.Item label="律师助理" name="assistant"><Select allowClear showSearch optionFilterProp="label" options={caseAssistantOptions}/></Form.Item><Form.Item label="调查员" name="investigator"><Input/></Form.Item></div>
          <Form.Item label="关联调查线索" name="investigation_clue_ids"><Select mode="multiple" showSearch optionFilterProp="label" options={caseClues.map(item=>({value:item.id,label:`${item.serial_no}｜${item.title}`}))}/></Form.Item><Form.Item label="修改说明" name="comment"><Input.TextArea rows={3}/></Form.Item>
        </Form>
      </Modal>
      <Modal width={760} open={Boolean(criminalMaintenance)} title={`维护刑事案件资料：${criminalMaintenance?.row.serial_no||""}`} okText="确定" cancelText="取消" onOk={saveCriminalMaintenance} onCancel={()=>setCriminalMaintenance(null)} destroyOnHidden>
        <Form form={criminalMaintenanceForm} layout="vertical">
          {criminalMaintenance?.kind==="litigants"&&<div className="form-grid">{[["plaintiffs","受害人"],["plaintiff_agents","受害人代理人"],["defendants","被告/犯罪嫌疑人"],["defendant_agents","被告代理人"],["third_parties","第三人"],["third_party_agents","第三人代理人"]].map(([name,label])=><Form.Item key={name} label={label} name={name}><Select mode="tags" tokenSeparators={[",","，"]}/></Form.Item>)}</div>}
          {criminalMaintenance?.kind==="public-security"&&<div className="form-grid">{[["public_security_name","公安机关"],["public_security_case_no","公安案件号"],["public_security_address","地址"],["public_security_phone","联系电话"],["public_security_operator","承办人"]].map(([name,label])=><Form.Item key={name} label={label} name={name}><Input/></Form.Item>)}</div>}
          {criminalMaintenance?.kind==="procuratorates"&&["first","second","retrial"].map(level=><div className="form-grid" key={level}>{[[`${level}_procuratorate_name`,`${level==="first"?"一审":level==="second"?"二审":"再审"}检察院`],[`${level}_procuratorate_case_no`,`案件号`],[`${level}_procuratorate_address`,`地址`],[`${level}_procuratorate_phone`,`联系电话`],[`${level}_procuratorate_operator`,`承办人`]].map(([name,label])=><Form.Item key={name} label={label} name={name}><Input/></Form.Item>)}</div>)}
          {criminalMaintenance?.kind==="courts"&&["first","second","retrial"].map(level=><div key={level}><Form.Item name={`${level}_court_enabled`} valuePropName="checked"><Checkbox>{`${level==="first"?"一审":level==="second"?"二审":"再审"}法院信息`}</Checkbox></Form.Item><div className="form-grid">{[[`${level}_court_name`,`${level==="first"?"一审":level==="second"?"二审":"再审"}法院`],[`${level}_court_case_no`,`案号`],[`${level}_court_courtroom`,`法庭`],[`${level}_court_judge`,`法官`],[`${level}_court_clerk`,`书记员`]].map(([name,label])=><Form.Item key={name} label={label} name={name}><Input/></Form.Item>)}<Form.Item label="立案日期" name={`${level}_court_filing_date`}><DatePicker style={{width:"100%"}}/></Form.Item><Form.Item label="开庭日期" name={`${level}_court_hearing_date`}><DatePicker style={{width:"100%"}}/></Form.Item></div></div>)}
          <Form.Item label="修改说明" name="comment"><Input.TextArea rows={3}/></Form.Item>
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
        onClose={() => setTaskCase(null)}
      >
        <Alert
          type="info"
          showIcon
          title="分配包含公证材料的案件时，系统会自动生成公证书及公证费发票原件交接任务。扫描文员提交完成后，文书人员 5 日内可退回重启。"
          style={{ marginBottom: 16 }}
        />
        <Table
          rowKey="id"
          size="small"
          pagination={false}
          tableLayout="fixed"
          scroll={{ x: 890 }}
          dataSource={caseTasks}
          columns={[
            { title: "任务编号", dataIndex: "serial_no", width: 175, render: (value: string, row: TaskRow) => <Button type="link" className="case-cell-link" onClick={() => openRelatedTask(row)}>{value || "—"}</Button> },
            { title: "任务名称", dataIndex: "title", width: 230, ellipsis: true, render: (value: string, row: TaskRow) => <Button type="link" className="case-cell-link" onClick={() => openRelatedTask(row)}>{value || "—"}</Button> },
            {
              title: "来源",
              dataIndex: "source",
              width: 90,
              render: (v: string) => (
                <Tag color={v === "自动任务" ? "purple" : "blue"}>{v}</Tag>
              ),
            },
            { title: "发起/验收人", dataIndex: "initiator", width: 105 },
            { title: "负责人", dataIndex: "owner", width: 90 },
            { title: "截止日", dataIndex: "deadline", width: 110 },
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
                <Input />
              </Form.Item>
              <Form.Item
                label="截止日期"
                name="deadline"
                rules={[{ required: true }]}
              >
                <DatePicker style={{ width: "100%" }} />
              </Form.Item>
              <Form.Item label="优先级" name="priority">
                <Select
                  options={["普通", "紧急", "特急"].map((v) => ({
                    value: v,
                    label: v,
                  }))}
                />
              </Form.Item>
              <Form.Item label="协作人" name="collaborators">
                <Select
                  mode="tags"
                  tokenSeparators={[",", "，"]}
                  placeholder="输入账号后回车"
                />
              </Form.Item>
            </div>
            <Form.Item label="任务说明" name="description">
              <Input.TextArea rows={3} />
            </Form.Item>
            <Button type="primary" onClick={createCaseTask}>
              创建案件任务
            </Button>
          </Form>
        </Card>}
      </Drawer>
      <Modal
        width={620}
        open={Boolean(archiving)}
        title={`归档检查：${archiving?.serial_no || ""}`}
        okText="提交归档审核"
        cancelText="取消"
        onOk={() => archive(true)}
        onCancel={() => setArchiving(null)}
        footer={() => (
          <>
            <Button onClick={() => archive(false)}>保存检查</Button>
            <Button onClick={() => setArchiving(null)}>取消</Button>
            <Button type="primary" onClick={() => archive(true)}>提交归档审核</Button>
          </>
        )}
      >
        <Alert
          type="warning"
          showIcon
          title="四项条件由系统根据办结记录、费用、归档附件和财务状态自动核验；审核通过才会正式归档。"
        />
        {!archiveChecks.case_closed && <Button style={{marginTop:12}} onClick={closeCase}>确认案件办结</Button>}
        <Form
          form={archiveForm}
          layout="vertical"
          className="archive-check-form"
        >
          <Form.Item name="case_closed" valuePropName="checked">
            <Checkbox disabled>案件已经办结或终止（系统核验）</Checkbox>
          </Form.Item>
          <Form.Item name="fees_settled" valuePropName="checked">
            <Checkbox disabled>官方费用、内部费用及结算费用已结清（系统核验）</Checkbox>
          </Form.Item>
          <Form.Item name="documents_complete" valuePropName="checked">
            <Checkbox disabled>委托材料、证据材料、诉讼文书和裁判文书齐全（系统核验）</Checkbox>
          </Form.Item>
          <Form.Item name="finance_complete" valuePropName="checked">
            <Checkbox disabled>回款、开票、退费及财务流程已完成（系统核验）</Checkbox>
          </Form.Item>
          <div className="form-grid">
            <Form.Item
              label="案件归档号"
              name="archive_no"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              label="纸质卷宗卷数"
              name="paper_volume_count"
              rules={[{ required: true }]}
            >
              <Input type="number" min={1} />
            </Form.Item>
          </div>
          <Form.Item
            label="纸质卷宗存放位置"
            name="paper_archive_location"
            rules={[{ required: true }]}
          >
            <Input placeholder="例如：上海档案室 A-03-12" />
          </Form.Item>
          <Form.Item label="归档意见" name="comment">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(reviewing)}
        title={`${reviewing?.approved ? "通过" : "驳回"}归档审核：${reviewing?.row.serial_no || ""}`}
        okText={reviewing?.approved ? "确认通过" : "确认驳回"}
        okButtonProps={{ danger: reviewing?.approved === false }}
        cancelText="取消"
        onOk={reviewArchive}
        onCancel={() => setReviewing(null)}
      >
        <Alert
          type={reviewing?.approved ? "success" : "warning"}
          showIcon
          title={
            reviewing?.approved
              ? "审核通过后案件进入已归档，归档资料只读保留。"
              : "驳回后案件恢复提交前阶段，经办人修改后可重新提交。"
          }
          style={{ marginBottom: 16 }}
        />
        <Form form={reviewForm} layout="vertical">
          <Form.Item
            label={reviewing?.approved ? "审核意见" : "驳回原因"}
            name="comment"
            rules={[
              {
                required: true,
                message: reviewing?.approved
                  ? "请输入审核意见"
                  : "请输入明确的驳回原因",
              },
            ]}
          >
            <Input.TextArea rows={4} />
          </Form.Item>
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
