import { useEffect, useMemo, useState } from "react";
import type { Key } from "react";
import {
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
  Tag,
  Timeline,
} from "antd";
import { CheckOutlined, CloseOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { api } from "./api";
import { formatRequiredDate } from "./formSafety";
import "./contract-center.css";
type Contract = {
  id: number;
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
  };
};
type Step = {
  id: number;
  step_order: number;
  approver: string;
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
type DirectoryUser = { username: string; display_name: string; department: string; is_active: boolean; role?: string; position?: string; staff_role?: string };
type Attachment = { id: number; original_name: string; category: string; size: number; created_at: string };
type HistoryEvent = { id: number; action: string; from_status: string; to_status: string; operator: string; comment: string; created_at: string };
type SealAsset = { id: number; code: string; name: string; seal_type: string; status: string };
type CustomerRef = { id: number; serial_no: string; title: string; owner: string; data: { customer_managers?: string[] } };
const colors: Record<string, string> = {
  草稿: "default",
  审批中: "orange",
  已通过: "green",
  履行中: "blue",
  已完成: "green",
  已拒绝: "red",
};
const contractNo = () => `HT${dayjs().format("YYYYMMDDHHmmss")}`;
const WIZARD_STORAGE_KEY = "sunhold-contract-wizard-id";
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
}: {
  initialView: string;
  onNavigate?: (key: string) => void;
}) {
  const [allRows, setAllRows] = useState<Contract[]>([]),
    [loading, setLoading] = useState(false),
    [open, setOpen] = useState(initialView === "contract-new"),
    [editing, setEditing] = useState<Contract | null>(null),
    [wizardDraft, setWizardDraft] = useState<Contract | null>(null),
    [wizardStep, setWizardStep] = useState(0),
    [submitting, setSubmitting] = useState<Contract | null>(null),
    [reviewing, setReviewing] = useState<Contract | null>(null),
    [steps, setSteps] = useState<Step[]>([]),
    [changing, setChanging] = useState<Contract | null>(null),
    [changeHistory, setChangeHistory] = useState<Contract | null>(null),
    [investigating, setInvestigating] = useState<Contract | null>(null),
    [paymentTarget, setPaymentTarget] = useState<Contract | null>(null),
    [invoiceTarget, setInvoiceTarget] = useState<Contract | null>(null),
    [viewing, setViewing] = useState<Contract | null>(null),
    [changes, setChanges] = useState<Change[]>([]);
  const [directory, setDirectory] = useState<DirectoryUser[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [history, setHistory] = useState<HistoryEvent[]>([]);
  const [sealAssets, setSealAssets] = useState<SealAsset[]>([]);
  const [customers, setCustomers] = useState<CustomerRef[]>([]);
  const [contractFile, setContractFile] = useState<File | null>(null);
  const [savingContract, setSavingContract] = useState(false);
  const [submittingWizard, setSubmittingWizard] = useState(false);
  const [approvalCreatorOpen, setApprovalCreatorOpen] = useState(false);
  const [creatingApprovalUser, setCreatingApprovalUser] = useState(false);
  const [profile, setProfile] = useState<Profile>(initialProfile);
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([]),
    [query, setQuery] = useState<Record<string, any>>({});
  const [form] = Form.useForm(),
    [submitForm] = Form.useForm(),
    [reviewForm] = Form.useForm(),
    [sealForm] = Form.useForm(),
    [investigationForm] = Form.useForm(),
    [paymentForm] = Form.useForm(),
    [invoiceForm] = Form.useForm(),
    [changeForm] = Form.useForm(),
    [queryForm] = Form.useForm(),
    [approvalUserForm] = Form.useForm();
  const load = async () => {
    setLoading(true);
    try {
      const [recordsRes, profileRes, directoryRes, sealRes, customerRes] = await Promise.all([
        api.get("/records", { params: { module: "contract", page_size: 100 } }),
        api.get("/auth/me"),
        api.get("/users/directory"),
        api.get("/seals/assets"),
        api.get("/customers", { params: { scope: "mine", customer_type: "客户", page: 1, page_size: 200 } }),
      ]);
      setAllRows(recordsRes.data.items);
      setProfile(profileRes.data);
      setDirectory((directoryRes.data.items || []).filter((item: DirectoryUser) => item.is_active !== false));
      setSealAssets((sealRes.data.items || []).filter((item: SealAsset) => item.status === "可用"));
      setCustomers(customerRes.data.items || []);
    } catch {
      message.error("合同数据加载失败");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    load();
  }, [initialView]);
  useEffect(() => {
    if (initialView !== "contract-new") {
      setOpen(false);
      return;
    }
    const savedId = Number(localStorage.getItem(WIZARD_STORAGE_KEY) || 0);
    if (savedId) void recoverWizard(savedId);
    else startCreate();
  }, [initialView]);
  const rows = useMemo(() => {
    let list =
      initialView === "contract-audit-pending"
        ? allRows.filter((x) => x.status === "审批中")
        : initialView === "contract-audit-refused"
          ? allRows.filter((x) => ["已拒绝", "已驳回"].includes(x.status))
          : initialView === "contract-audit-approved"
            ? allRows.filter((x) =>
                ["已通过", "履行中", "已完成", "已归档"].includes(x.status),
              )
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
    if (query.customer)
      list = list.filter((x) =>
        text(x.customer).includes(text(query.customer)),
      );
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
  }, [allRows, initialView, profile, query]);
  const startCreate = () => {
    localStorage.removeItem(WIZARD_STORAGE_KEY);
    setEditing(null);
    setWizardDraft(null);
    setWizardStep(0);
    setContractFile(null);
    setSteps([]);
    setAttachments([]);
    setHistory([]);
    form.resetFields();
    submitForm.resetFields();
    reviewForm.resetFields();
    sealForm.resetFields();
    let linkedCustomerId: number | undefined;
    try {
      const context = JSON.parse(sessionStorage.getItem("sunhold:contract-customer") || "null");
      if (context?.id && Date.now() - Number(context.at || 0) < 60 * 60 * 1000) linkedCustomerId = Number(context.id);
    } catch { /* ignore invalid navigation context */ }
    form.setFieldsValue({
      serial_no: contractNo(),
      status: "草稿",
      owner: profile.username || "admin",
      department: profile.department || "上海分所",
      type: "法律顾问合同",
      contract_body: "律所",
      fee_type: "固定收费",
      amount: 0,
      signed_at: dayjs(),
      customer_id: linkedCustomerId,
    });
    setOpen(true);
  };
  useEffect(() => {
    const handleRouteReselect = (event: Event) => {
      if ((event as CustomEvent<string>).detail === "contract-new" && initialView === "contract-new") startCreate();
    };
    window.addEventListener("sunhold:route-reselect", handleRouteReselect);
    return () => window.removeEventListener("sunhold:route-reselect", handleRouteReselect);
  }, [initialView, profile.username, profile.department]);
  const populateDraftForm = (contract: Contract) => {
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
    const [approvalRes, attachmentRes, historyRes] = await Promise.all([
      api.get(`/contracts/${contractId}/approvals`),
      api.get("/attachments", { params: { record_id: contractId } }),
      api.get(`/records/${contractId}/history`),
    ]);
    const contract = approvalRes.data.contract as Contract;
    setWizardDraft(contract);
    setSteps(approvalRes.data.items || []);
    setAttachments(attachmentRes.data.items || []);
    setHistory(historyRes.data.items || []);
    submitForm.setFieldsValue({
      approvers: (approvalRes.data.items || [])[0]?.approver,
      comment: contract.data.submit_comment || "",
    });
    populateDraftForm(contract);
    return contract;
  };
  const recoverWizard = async (contractId: number) => {
    try {
      const contract = await loadWizardContext(contractId);
      if (contract.data.seal_application_id) {
        localStorage.removeItem(WIZARD_STORAGE_KEY);
        startCreate();
        return;
      }
      const step = contract.data.seal_application_id || ["已通过", "履行中", "已完成"].includes(contract.status)
        ? 3
        : contract.status === "审批中"
          ? 2
          : 1;
      setWizardStep(step);
      setOpen(true);
      if (step === 3 && !contract.data.seal_application_id) {
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
  const save = async () => {
    let v: any;
    try {
      v = await form.validateFields();
    } catch {
      message.warning("请先补全红色提示的合同必填信息");
      return;
    }
    const selectedCustomer = customers.find((customer) => customer.id === Number(v.customer_id));
    if (!selectedCustomer) {
      form.setFields([{ name: "customer_id", errors: ["请从客户列表中选择准确客户"] }]);
      message.warning("请输入客户关键字，并从匹配结果中选择客户");
      return;
    }
    if (!editing && !wizardDraft && !contractFile) {
      message.warning("请上传合同附件");
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
        serial_no: v.serial_no || target?.serial_no || contractNo(),
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
        await api.post("/attachments", attachment);
      }
      message.success(editing ? "合同已更新" : "合同草稿已保存，进入提交审核");
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
      message.error(error?.response?.data?.detail || "保存失败");
    } finally {
      setSavingContract(false);
    }
  };
  const submitWizard = async () => {
    if (!wizardDraft) return;
    try {
      const values = await submitForm.validateFields();
      setSubmittingWizard(true);
      await api.post(`/contracts/${wizardDraft.id}/submit`, { approvers: values.approvers ? [values.approvers] : [], comment: values.comment || "" });
      await loadWizardContext(wizardDraft.id);
      setWizardStep(2);
      message.success("合同已提交审核");
      await load();
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(error?.response?.data?.detail || error?.message || "提交审核失败");
    } finally {
      setSubmittingWizard(false);
    }
  };
  const openApprovalCreator = () => {
    approvalUserForm.resetFields();
    approvalUserForm.setFieldsValue({ department: profile.department || "上海分所", position: "诉讼部部长" });
    setApprovalCreatorOpen(true);
  };
  const createApprovalUser = async () => {
    if (profile.role !== "admin") {
      message.error("仅系统管理员可以创建审批账号");
      return;
    }
    try {
      const values = await approvalUserForm.validateFields();
      setCreatingApprovalUser(true);
      const { data } = await api.post("/system/users", {
        username: values.username,
        display_name: values.display_name,
        department: values.department,
        password: values.password,
        role: "manager",
        is_active: true,
        must_change_password: true,
        profile: { position: values.position, staff_role: values.position },
      });
      const created: DirectoryUser = {
        username: data.username,
        display_name: data.display_name,
        department: data.department,
        is_active: true,
        role: data.role,
        position: values.position,
        staff_role: values.position,
      };
      setDirectory((items) => [...items.filter((item) => item.username !== created.username), created]);
      submitForm.setFieldValue("approvers", created.username);
      setApprovalCreatorOpen(false);
      message.success("部长审批账号已创建并选中；首次登录必须修改初始密码");
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(error?.response?.data?.detail || error?.message || "审批账号创建失败");
    } finally {
      setCreatingApprovalUser(false);
    }
  };
  const refreshWizard = async () => {
    if (!wizardDraft) return;
    try {
      const contract = await loadWizardContext(wizardDraft.id);
      if (["已通过", "履行中", "已完成"].includes(contract.status)) {
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
      await api.post(`/contracts/${wizardDraft.id}/approve`, {
        approved,
        comment: values.comment || "",
      });
      reviewForm.resetFields();
      const contract = await loadWizardContext(wizardDraft.id);
      if (contract.status === "已通过") {
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
      message.error(error?.response?.data?.detail || "审批失败");
    }
  };
  const createSealApplication = async () => {
    if (!wizardDraft) return;
    try {
      const values = await sealForm.validateFields();
      const { data } = await api.post(`/contracts/${wizardDraft.id}/seal-application`, {
        ...values,
        use_date: formatRequiredDate(values.use_date, "计划用印日期"),
      });
      const contract = await loadWizardContext(wizardDraft.id);
      localStorage.removeItem(WIZARD_STORAGE_KEY);
      message.success(values.submit ? "合同用印申请已创建并提交审批" : "合同用印申请草稿已创建");
      setWizardDraft(contract);
      await load();
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
    } catch {
      message.error("附件下载失败");
    }
  };
  const submit = async () => {
    if (!submitting) return;
    const v = await submitForm.validateFields();
    try {
      await api.post(`/contracts/${submitting.id}/submit`, { approvers: v.approvers ? [v.approvers] : [], comment: v.comment || "" });
      message.success("已提交部长审批");
      setSubmitting(null);
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "提交失败");
    }
  };
  const openReview = async (r: Contract) => {
    try {
      const { data } = await api.get(`/contracts/${r.id}/approvals`);
      setReviewing(r);
      setSteps(data.items);
    } catch {
      message.error("审批节点加载失败");
    }
  };
  const approve = async (approved: boolean) => {
    if (!reviewing) return;
    const v = await reviewForm.validateFields();
    try {
      await api.post(`/contracts/${reviewing.id}/approve`, {
        approved,
        comment: v.comment || "",
      });
      message.success(approved ? "当前审批节点已通过" : "合同已拒绝");
      reviewForm.resetFields();
      const { data } = await api.get(`/contracts/${reviewing.id}/approvals`);
      setSteps(data.items);
      setReviewing(data.contract);
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "审批失败");
    }
  };
  const openChange = (r: Contract) => {
    setChanging(r);
    changeForm.resetFields();
    changeForm.setFieldsValue({
      change_type: "合同补充/修订",
      title: r.title,
      amount: r.data.amount,
      external_contract_numbers: r.data.external_contract_numbers || (r.data.external_contract_no ? [r.data.external_contract_no] : []),
      end_date: r.data.end_date ? dayjs(r.data.end_date) : undefined,
    });
  };
  const saveChange = async () => {
    if (!changing) return;
    const v = await changeForm.validateFields();
    try {
      await api.post(`/contracts/${changing.id}/changes`, {
        ...v,
        end_date: v.end_date?.format("YYYY-MM-DD"),
      });
      message.success("合同变更已提交审批");
      setChanging(null);
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "合同变更失败");
    }
  };
  const reviewChange = async (contract: Contract, approved: boolean) => {
    try {
      await api.post(`/contracts/${contract.id}/changes/review`, { approved, comment: approved ? "同意合同变更" : "变更内容需补充后重新提交" });
      message.success(approved ? "合同变更已审批通过" : "合同变更已驳回");
      setSelectedRowKeys([]);
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "合同变更审批失败");
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
  const archive = async (r: Contract) => {
    try {
      await api.post(`/contracts/${r.id}/archive`);
      message.success("合同已归档");
      setSelectedRowKeys([]);
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "合同归档失败");
    }
  };
  const openInvestigation = (r: Contract) => {
    investigationForm.resetFields();
    investigationForm.setFieldsValue({
      title: `${r.title}调查任务`,
      owner: profile.username,
      authorized_from: dayjs(),
      authorized_to: dayjs().add(30, "day"),
      right_type: "商标",
      customer_review: false,
      region: "",
      description: `来源合同 ${r.serial_no}`,
    });
    setInvestigating(r);
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
      message.success(`调查任务 ${data.serial_no} 已创建`);
      setInvestigating(null);
      investigationForm.resetFields();
      setSelectedRowKeys([]);
      onNavigate?.("investigation-task-published");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "调查任务创建失败");
    }
  };
  const openContractPayment = (contract: Contract) => {
    const outstanding = Number(contract.data.official_unreceived || 0) + Number(contract.data.agency_due || 0) + Number(contract.data.other_due || 0);
    paymentForm.resetFields();
    paymentForm.setFieldsValue({
      title: `${contract.title}合同付款`,
      amount: outstanding > 0 ? outstanding : contract.data.amount,
      fee_type: "结算费用",
      handler: profile.username,
      payee: contract.customer,
      description: `来源合同 ${contract.serial_no}`,
    });
    setPaymentTarget(contract);
  };
  const createContractPayment = async () => {
    if (!paymentTarget) return;
    const values = await paymentForm.validateFields();
    try {
      const { data } = await api.post("/finance/fees", {
        ...values,
        customer: paymentTarget.customer,
        case_no: paymentTarget.data.case_no || "",
        contract_record_id: paymentTarget.id,
      });
      message.success(`请款单 ${data.serial_no} 已创建并关联合同`);
      setPaymentTarget(null);
      paymentForm.resetFields();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "合同付款申请创建失败");
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
    if (!invoiceTarget) return;
    const values = await invoiceForm.validateFields();
    try {
      const { data } = await api.post("/finance/invoices", {
        ...values,
        customer: invoiceTarget.customer,
        case_no: invoiceTarget.data.case_no || "",
        contract_record_id: invoiceTarget.id,
        remark: `来源合同 ${invoiceTarget.serial_no}${values.remark ? `；${values.remark}` : ""}`,
      });
      message.success(`发票申请 ${data.serial_no} 已创建并关联合同`);
      setInvoiceTarget(null);
      invoiceForm.resetFields();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "合同开票申请创建失败");
    }
  };
  const startSelectedSeal = async (contract: Contract) => {
    if (!["已通过", "履行中", "已完成"].includes(contract.status)) {
      message.warning("合同审批通过后才能申请用印");
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
    }));
    onNavigate?.("case-new");
  };
  const exportCsv = async () => {
    try {
      const res = await api.get("/records/export", {
        params: { module: "contract" },
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
  const needSelected = (action: () => void) =>
    selected ? action() : message.warning("请先选择一份合同");
  const selected = rows.find((row) => selectedRowKeys.includes(row.id));
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
  const totalRow: Contract = {
    id: -1,
    serial_no: "",
    title: "",
    customer: "",
    status: "",
    owner: "",
    department: "",
    description: "",
    data: { amount: 0, signed_at: "", type: "", ...totals },
  };
  const textCell = (value: string, r: Contract) => (r.id < 0 ? "" : value);
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
    render: (_: unknown, r: Contract) =>
      r.id < 0 ? amount(totals[key]) : String(r.data[key] ?? 0),
  });
  const columns = [
    {
      title: "合同号",
      dataIndex: "serial_no",
      width: 105,
      render: (v: string, r: Contract) =>
        r.id < 0 ? (
          ""
        ) : (
          <Button
            type="link"
            className="contract-cell-link"
          onClick={() => setViewing(r)}
          >
            {v}
          </Button>
        ),
    },
    {
      title: "合同名称",
      dataIndex: "title",
      width: 135,
      ellipsis: true,
      render: textCell,
    },
    {
      title: "合同主体",
      key: "body",
      width: 74,
      render: (_: unknown, r: Contract) =>
        r.id < 0 ? "" : r.data.contract_body || "律所",
    },
    { title: "合同状态", dataIndex: "status", width: 74, render: textCell },
    {
      title: "案源人",
      key: "source",
      width: 74,
      render: (_: unknown, r: Contract) =>
        r.id < 0 ? "" : r.data.source_person || r.owner,
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
      render: (_: unknown, r: Contract) => r.data.source_person || r.owner,
    },
    {
      title: "客户管理人",
      key: "customerManager",
      width: 100,
      render: (_: unknown, r: Contract) => r.data.customer_manager || "—",
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
        String((r.data as Record<string, any>).customer_no || "—"),
    },
    { title: "客户名称", dataIndex: "customer", width: 180, ellipsis: true },
  ];
  const isAuditView = initialView.startsWith("contract-audit-");
  const stepItems = steps.map((s) => ({
    title: `第${s.step_order}级：${s.approver}`,
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
  const currentApproval = steps.find((step) => step.status === "待审批");
  const approvalOptions = directory.filter((user) => `${user.position || ""}${user.staff_role || ""}`.includes("部长")).map((user) => ({
    value: user.username,
    label: `${user.display_name || user.username}（${user.position || user.staff_role}｜${user.department || "未分部门"}）`,
  }));
  const uniqueCustomers = Array.from(new Map(customers.map((customer) => [customer.title.normalize("NFKC").trim().toLocaleLowerCase(), customer])).values());
  const customerOptions = uniqueCustomers.map((customer) => ({
    value: customer.id,
    label: customer.title,
  }));
  const historyItems = history.map((event) => ({
    color: event.to_status === "已拒绝" ? "red" : event.action.includes("创建") ? "blue" : "green",
    children: (
      <div className="contract-history-item">
        <b>{event.action}</b>
        {event.from_status && event.from_status !== event.to_status && <Tag>{event.from_status} → {event.to_status}</Tag>}
        <small>{event.operator} · {dayjs(event.created_at).format("YYYY-MM-DD HH:mm")}</small>
        {event.comment && <p>{event.comment}</p>}
      </div>
    ),
  }));
  return (
    <>
      {initialView !== "contract-new" && <Card className="panel contract-original-panel" title="合同查询">
        <Form
          form={queryForm}
          className="contract-query"
          onFinish={(values) => setQuery(values)}
        >
          <Form.Item label="合同名称" name="title"><Input placeholder="合同名称" /></Form.Item>
          <Form.Item label="合同编号" name="serial_no"><Input placeholder="合同编号" /></Form.Item>
          <Form.Item label="合同类型" name="type"><Select allowClear placeholder="请选择" options={["法律顾问合同","争议解决合同","框架合作合同","非诉项目合同","其他"].map(value=>({value,label:value}))} /></Form.Item>
          <Form.Item label="客户名称" name="customer"><Input placeholder="客户名称" /></Form.Item>
          <Form.Item label={isAuditView ? "案号" : "案件编号"} name="case_no"><Input placeholder="案号" /></Form.Item>
          <Form.Item label="收费类型" name="fee_type"><Select allowClear placeholder="请选择" options={["固定收费","固定+后期","免费代理","法律援助","计时收费","全风险代理"].map(value=>({value,label:value}))} /></Form.Item>
          <Form.Item label="合同日期" name="signed_at"><DatePicker.RangePicker /></Form.Item>
          {initialView === "contract-mine" ? (
            <Form.Item label="案源人"><Input disabled value={profile.display_name || profile.username || "管理者"} /></Form.Item>
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
          dataSource={isAuditView ? rows : [totalRow, ...rows]}
          rowClassName={(record) => record.id < 0 ? "contract-total-row" : ""}
          rowSelection={{
            selectedRowKeys,
            onChange: (keys) => setSelectedRowKeys(keys.filter((key) => Number(key) > 0)),
            getCheckboxProps: (record) => ({ disabled: record.id < 0 }),
          }}
          scroll={{ x: isAuditView ? 1450 : 1480 }}
          pagination={{pageSize:15,showSizeChanger:true,pageSizeOptions:[10,15,20,50,100,200],showTotal:()=>`共有${rows.length}条`}}
          summary={isAuditView ? undefined : () => <Table.Summary><Table.Summary.Row className="contract-total-row"><Table.Summary.Cell index={0} colSpan={6}></Table.Summary.Cell>{moneyKeys.map((key,index)=><Table.Summary.Cell key={key} index={index+6} align="right">{amount(totals[key])}</Table.Summary.Cell>)}</Table.Summary.Row></Table.Summary>}
        />
        {!isAuditView && <div className="contract-bottom-actions"><Space size={4} wrap>
          <Button onClick={exportCsv}>导出CSV</Button>
          <Button onClick={()=>needSelected(()=>setViewing(selected!))}>合同查看</Button>
          <Button onClick={()=>needSelected(()=>openChange(selected!))}>合同变更</Button>
          <Button onClick={()=>needSelected(()=>void startSelectedSeal(selected!))}>合同用印</Button>
          <Button onClick={()=>needSelected(()=>openContractPayment(selected!))}>合同付款</Button>
          <Button onClick={()=>needSelected(()=>openContractInvoice(selected!))}>合同开票</Button>
          <Button onClick={()=>needSelected(()=>startCaseFromContract(selected!))}>新建案件</Button>
          <Button onClick={()=>needSelected(()=>openInvestigation(selected!))}>新建调查任务</Button>
          <Button onClick={()=>needSelected(()=>archive(selected!))}>合同归档</Button>
        </Space></div>}
        {isAuditView && <div className="contract-bottom-actions"><Space><Button onClick={exportCsv}>导出CSV</Button><Button onClick={()=>needSelected(()=>{if(selected?.data.pending_change?.status!=="待审批")return message.warning("所选合同没有待审批变更");void reviewChange(selected!,true)})}>通过合同变更</Button><Button danger onClick={()=>needSelected(()=>{if(selected?.data.pending_change?.status!=="待审批")return message.warning("所选合同没有待审批变更");void reviewChange(selected!,false)})}>驳回合同变更</Button></Space></div>}
      </Card>}
      {initialView === "contract-new" && (
        <Card className="panel contract-create-page" title="新建合同">
          <div className="contract-page-steps">
            {["合同基本信息", "提交审核", "合同审批", "合同用印"].map((title, index) => (
              <div key={title} className={wizardStep === index ? "active" : wizardStep > index ? "done" : ""}>{["①", "②", "③", "④"][index]} {title}</div>
            ))}
          </div>
          {wizardStep === 0 && (
            <Form form={form} layout="horizontal" className="contract-page-form">
              <Form.Item label="客户" name="customer_id" rules={[{ required: true, message: "请选择客户" }]}><Select showSearch optionFilterProp="label" placeholder="输入客户名称关键字后选择" options={customerOptions} notFoundContent="没有匹配客户，请先在客户管理中新建客户" /></Form.Item>
              <Form.Item label="合同主体" name="contract_body" rules={[{ required: true }]}><Select options={["律所", "平台"].map((v) => ({ value: v, label: v }))} /></Form.Item>
              <Form.Item label="合同类别" name="type" rules={[{ required: true }]}><Select options={["法律顾问合同", "争议解决合同", "框架合作合同", "非诉项目合同", "其他"].map((v) => ({ value: v, label: v }))} /></Form.Item>
              <Form.Item label="收费模式" name="fee_type" rules={[{ required: true }]}><Select options={["固定收费", "固定+后期", "免费代理", "法律援助", "计时收费", "全风险代理"].map((v) => ({ value: v, label: v }))} /></Form.Item>
              <Form.Item label="合同名称" name="title" rules={[{ required: true }]}><Input placeholder="合同名称" /></Form.Item>
              <Form.Item label="外部合同号（可多个）" name="external_contract_numbers"><Select mode="tags" tokenSeparators={[",", "，"]} placeholder="输入客户方合同编号后回车" /></Form.Item>
              <Form.Item label="备注" name="description" rules={[{ required: true }]}><Input.TextArea rows={4} placeholder="备注" /></Form.Item>
              <Form.Item label="合同附件" required>
                <input type="file" onChange={(event) => setContractFile(event.target.files?.[0] || null)} />
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
                <Form.Item label={<span>审批部长{profile.role === "admin" && <Button type="link" size="small" onClick={openApprovalCreator}>新增部长审批人</Button>}</span>} name="approvers" rules={[{required:true,message:"请选择一名部长审批"}]}>
                  <Select disabled={!("草稿 已拒绝".split(" ").includes(wizardDraft?.status || ""))} showSearch optionFilterProp="label" options={approvalOptions} placeholder="请选择一名部长" notFoundContent="没有可用部长，请由管理员创建部长审批账号" />
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
              {wizardDraft?.status === "审批中" && currentApproval && (
                <Form form={reviewForm} layout="vertical" className="contract-review-form">
                  <div className="contract-current-approval">当前节点：第 {currentApproval.step_order} 级 · {currentApproval.approver}</div>
                  <Form.Item label="审批意见" name="comment"><Input.TextArea rows={3} placeholder="填写通过意见；拒绝时必须填写原因" /></Form.Item>
                  <Space><Button danger icon={<CloseOutlined />} onClick={() => approveWizard(false)}>拒绝</Button><Button type="primary" icon={<CheckOutlined />} onClick={() => approveWizard(true)}>通过当前节点</Button></Space>
                </Form>
              )}
              <Divider titlePlacement="start">合同附件</Divider>
              <div className="contract-attachment-list">{attachments.length ? attachments.map((item) => <Button key={item.id} type="link" onClick={() => downloadAttachment(item)}>{item.original_name}</Button>) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无合同附件" />}</div>
              <Divider titlePlacement="start">状态时间线</Divider>
              {historyItems.length ? <Timeline items={historyItems} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无流程记录" />}
            </div>
          )}
          {wizardStep === 3 && (
            <div className="contract-wizard-panel contract-seal-step contract-page-stage">
              <div className="contract-wizard-finished"><CheckOutlined /><h3>合同审批已通过</h3><p>合同草稿、审批意见、附件和时间线均已保存，可以继续办理合同用印。</p></div>
              {wizardDraft?.data.seal_application_id ? (
                <Descriptions bordered size="small" column={2} items={[
                  { key: "contract", label: "合同编号", children: wizardDraft.serial_no },
                  { key: "seal", label: "用印申请编号", children: wizardDraft.data.seal_application_no || `#${wizardDraft.data.seal_application_id}` },
                  { key: "status", label: "衔接状态", children: <Tag color="green">已生成真实用印申请</Tag>, span: 2 },
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
            {wizardStep > 0 && wizardStep < 3 && (wizardStep !== 1 || ["草稿", "已拒绝"].includes(wizardDraft?.status || "")) && <Button onClick={() => setWizardStep((step) => Math.max(0, step - 1))}>上一步</Button>}
            {wizardStep === 0 && <Button type="primary" loading={savingContract} onClick={save}>下一步</Button>}
            {wizardStep === 1 && ["草稿", "已拒绝"].includes(wizardDraft?.status || "") && <Button type="primary" loading={submittingWizard} onClick={submitWizard}>提交审核</Button>}
            {wizardStep === 1 && wizardDraft?.status === "审批中" && <Button type="primary" onClick={() => setWizardStep(2)}>返回审批进度</Button>}
            {wizardStep === 2 && <Button type="primary" onClick={refreshWizard}>刷新审批状态</Button>}
            {wizardStep === 3 && !wizardDraft?.data.seal_application_id && <Button onClick={() => { sealForm.setFieldValue("submit", false); void createSealApplication(); }}>保存用印草稿</Button>}
            {wizardStep === 3 && !wizardDraft?.data.seal_application_id && <Button type="primary" onClick={() => { sealForm.setFieldValue("submit", true); void createSealApplication(); }}>保存并提交用印</Button>}
            {wizardStep === 3 && wizardDraft?.data.seal_application_id && <Button onClick={startCreate}>继续新建合同</Button>}
            {wizardStep === 3 && wizardDraft?.data.seal_application_id && <Button type="primary" onClick={() => onNavigate?.("seal-my")}>进入用印中心</Button>}
          </Space></div>
        </Card>
      )}
      <Modal
        open={approvalCreatorOpen}
        title="管理员新增部长审批人"
        okText="创建并选中"
        cancelText="取消"
        confirmLoading={creatingApprovalUser}
        onOk={() => void createApprovalUser()}
        onCancel={() => setApprovalCreatorOpen(false)}
        destroyOnHidden
      >
        <Form form={approvalUserForm} layout="vertical">
          <Form.Item label="登录账号" name="username" rules={[{ required: true, min: 3, message: "请输入至少 3 位登录账号" }, { pattern: /^[A-Za-z0-9._-]+$/, message: "账号只能包含字母、数字、点、下划线或短横线" }]}><Input autoComplete="off" /></Form.Item>
          <Form.Item label="姓名" name="display_name" rules={[{ required: true, message: "请输入审批人姓名" }]}><Input /></Form.Item>
          <Form.Item label="所属部门" name="department" rules={[{ required: true, message: "请输入所属部门" }]}><Input /></Form.Item>
          <Form.Item label="部长岗位" name="position" rules={[{ required: true, message: "请选择部长岗位" }]}><Select options={[{ value: "诉讼部部长", label: "诉讼部部长" }, { value: "调查部部长", label: "调查部部长" }]} /></Form.Item>
          <Form.Item label="初始密码" name="password" rules={[{ required: true, min: 8, message: "初始密码至少 8 位" }]}><Input.Password autoComplete="new-password" /></Form.Item>
          <p className="contract-draft-tip">只有部长账号会出现在合同审批人下拉中；账号首次登录必须修改初始密码。</p>
        </Form>
      </Modal>
      <Modal
        open={Boolean(paymentTarget)}
        title={`合同付款：${paymentTarget?.serial_no || ""}`}
        okText="创建请款单"
        cancelText="取消"
        onOk={createContractPayment}
        onCancel={() => setPaymentTarget(null)}
      >
        <Form form={paymentForm} layout="vertical">
          <Form.Item label="费用名称" name="title" rules={[{ required: true }]}><Input /></Form.Item>
          <div className="form-grid">
            <Form.Item label="金额" name="amount" rules={[{ required: true }]}><InputNumber min={0.01} precision={2} style={{ width: "100%" }} /></Form.Item>
            <Form.Item label="费用类型" name="fee_type" rules={[{ required: true }]}><Select options={["结算费用", "官方费用", "内部费用", "预损费用", "归档费用"].map(value => ({ value, label: value }))} /></Form.Item>
            <Form.Item label="经办人" name="handler" rules={[{ required: true }]}><Input /></Form.Item>
            <Form.Item label="收款单位" name="payee"><Input /></Form.Item>
          </div>
          <Form.Item label="说明" name="description"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(invoiceTarget)}
        title={`合同开票：${invoiceTarget?.serial_no || ""}`}
        okText="创建开票申请"
        cancelText="取消"
        onOk={createContractInvoice}
        onCancel={() => setInvoiceTarget(null)}
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
            <Form.Item label="调查负责人" name="owner">
              <Select allowClear showSearch optionFilterProp="label" options={directory.map(user=>({value:user.username,label:`${user.display_name}（${user.username}）`}))} />
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
          <Form.Item label="调查区域" name="region">
            <Input placeholder="省、市或具体授权区域" />
          </Form.Item>
          <Form.Item name="customer_review" valuePropName="checked">
            <Checkbox>调查线索需要客户审核</Checkbox>
          </Form.Item>
          <Form.Item label="任务说明" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        width={860}
        open={Boolean(viewing)}
        title={`合同查看：${viewing?.serial_no || ""}`}
        footer={<Button onClick={() => setViewing(null)}>关闭</Button>}
        onCancel={() => setViewing(null)}
      >
        <Descriptions
          bordered
          size="small"
          column={2}
          items={viewing ? [
            {key:"serial",label:"合同号",children:viewing.serial_no},
            {key:"status",label:"合同状态",children:viewing.status},
            {key:"title",label:"合同名称",children:viewing.title,span:2},
            {key:"customer",label:"客户名称",children:viewing.customer},
            {key:"body",label:"合同主体",children:viewing.data.contract_body||"律所"},
            {key:"type",label:"合同类型",children:viewing.data.type||"—"},
            {key:"fee",label:"收费类型",children:viewing.data.fee_type||"—"},
            {key:"source",label:"案源人",children:viewing.data.source_person||viewing.owner},
            {key:"date",label:"合同日期",children:viewing.data.signed_at||"—"},
            {key:"official",label:"官费（支付 / 到账 / 未到）",children:`${amount(viewing.data.official_paid)} / ${amount(viewing.data.official_received)} / ${amount(viewing.data.official_unreceived)}`,span:2},
            {key:"agency",label:"代理费（总额 / 到账 / 待收）",children:`${amount(viewing.data.agency_total)} / ${amount(viewing.data.agency_received)} / ${amount(viewing.data.agency_due)}`,span:2},
            {key:"invoice",label:"发票（已开 / 应开 / 高开）",children:`${amount(viewing.data.invoice_opened)} / ${amount(viewing.data.invoice_should)} / ${amount(viewing.data.invoice_excess)}`,span:2},
            {key:"description",label:"合同说明",children:viewing.description||"—",span:2},
          ] : []}
        />
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
            wizardStep > 0 && wizardStep < 3 && (wizardStep !== 1 || ["草稿", "已拒绝"].includes(wizardDraft?.status || "")) ? <Button key="back" onClick={() => setWizardStep((step) => Math.max(0, step - 1))}>上一步</Button> : null,
            <Button key="close" onClick={() => setOpen(false)}>{wizardStep === 0 ? "取消" : "关闭"}</Button>,
            wizardStep === 0 ? <Button key="next" type="primary" loading={savingContract} onClick={save}>下一步</Button> : null,
            wizardStep === 1 && ["草稿", "已拒绝"].includes(wizardDraft?.status || "") ? <Button key="submit" type="primary" loading={submittingWizard} onClick={submitWizard}>提交审核</Button> : null,
            wizardStep === 1 && wizardDraft?.status === "审批中" ? <Button key="approval" type="primary" onClick={() => setWizardStep(2)}>返回审批进度</Button> : null,
            wizardStep === 2 ? <Button key="refresh" type="primary" onClick={refreshWizard}>刷新审批状态</Button> : null,
            wizardStep === 3 && !wizardDraft?.data.seal_application_id ? <Button key="seal-save" onClick={() => { sealForm.setFieldValue("submit", false); void createSealApplication(); }}>保存用印草稿</Button> : null,
            wizardStep === 3 && !wizardDraft?.data.seal_application_id ? <Button key="seal-submit" type="primary" onClick={() => { sealForm.setFieldValue("submit", true); void createSealApplication(); }}>保存并提交用印</Button> : null,
            wizardStep === 3 && wizardDraft?.data.seal_application_id ? <Button key="seal" type="primary" onClick={() => { setOpen(false); onNavigate?.("seal-my"); }}>进入用印中心</Button> : null,
          ]
        }
        onCancel={() => setOpen(false)}
        destroyOnHidden
      >
        {!editing && (
          <Steps
            className="contract-create-steps"
            current={wizardStep}
            items={["合同基本信息", "提交审核", "合同审批", "合同用印"].map((title) => ({ title }))}
          />
        )}
        {(editing || wizardStep === 0) && (
        <Form form={form} layout="vertical">
          <div className="form-grid">
            <Form.Item hidden={!editing} label="合同编号" name="serial_no" rules={[{ required: true }]}>
              <Input disabled={Boolean(editing)} />
            </Form.Item>
            <Form.Item label="客户" name="customer_id" rules={[{ required: true, message: "请选择客户" }]}>
              <Select showSearch optionFilterProp="label" placeholder="输入客户名称关键字后选择" options={customerOptions} notFoundContent="没有匹配客户，请先在客户管理中新建客户" />
            </Form.Item>
            <Form.Item label="合同主体" name="contract_body" rules={[{ required: true }]}>
              <Select options={["律所", "平台"].map((v) => ({ value: v, label: v }))} />
            </Form.Item>
            <Form.Item label="合同类别" name="type" rules={[{ required: true }]}>
              <Select options={["法律顾问合同", "争议解决合同", "框架合作合同", "非诉项目合同", "其他"].map((v) => ({ value: v, label: v }))} />
            </Form.Item>
            <Form.Item label="收费模式" name="fee_type" rules={[{ required: true }]}>
              <Select options={["固定收费", "固定+后期", "免费代理", "法律援助", "计时收费", "全风险代理"].map((v) => ({ value: v, label: v }))} />
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
            <Form.Item className="span-2" label="合同附件" required={!editing}>
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
            <Form form={submitForm} layout="vertical" className="contract-submit-form">
              <Form.Item label="审批部长" name="approvers" rules={[{required:true,message:"请选择一名部长审批"}]}>
                <Select disabled={!(["草稿", "已拒绝"].includes(wizardDraft?.status || ""))} showSearch optionFilterProp="label" options={approvalOptions} placeholder="请选择一名部长" notFoundContent="没有可用部长，请由管理员创建部长审批账号" />
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
            {wizardDraft?.status === "审批中" && currentApproval && (
              <Form form={reviewForm} layout="vertical" className="contract-review-form">
                <div className="contract-current-approval">当前节点：第 {currentApproval.step_order} 级 · {currentApproval.approver}</div>
                <Form.Item label="审批意见" name="comment"><Input.TextArea rows={3} placeholder="填写通过意见；拒绝时必须填写原因" /></Form.Item>
                <Space>
                  <Button danger icon={<CloseOutlined />} onClick={() => approveWizard(false)}>拒绝</Button>
                  <Button type="primary" icon={<CheckOutlined />} onClick={() => approveWizard(true)}>通过当前节点</Button>
                </Space>
              </Form>
            )}
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
            <div className="contract-wizard-finished">
              <CheckOutlined />
              <h3>合同审批已通过</h3>
              <p>合同草稿、审批意见、附件和时间线均已保存，可以继续办理合同用印。</p>
            </div>
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
        onOk={submit}
        onCancel={() => setSubmitting(null)}
      >
        <Form form={submitForm} layout="vertical">
          <Form.Item
            label="审批部长"
            name="approvers"
            rules={[{ required: true }]}
          >
            <Select showSearch optionFilterProp="label" options={approvalOptions} placeholder="请选择一名部长" notFoundContent="没有可用部长，请由管理员创建部长审批账号" />
          </Form.Item>
          <Form.Item label="提交说明" name="comment">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        width={680}
        open={Boolean(reviewing)}
        title={`合同审批：${reviewing?.title || ""}`}
        footer={
          reviewing?.status === "审批中" ? (
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
        {reviewing?.status === "审批中" && (
          <Form form={reviewForm} layout="vertical">
            <Form.Item label="审批意见" name="comment">
              <Input.TextArea rows={3} />
            </Form.Item>
          </Form>
        )}
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
            { title: "操作人", dataIndex: "operator", width: 90 },
          ]}
        />
      </Modal>
    </>
  );
}
