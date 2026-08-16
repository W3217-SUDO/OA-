import { useEffect, useMemo, useState } from "react";
import type { Key } from "react";
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
  message,
  Modal,
  Popconfirm,
  Progress,
  Select,
  Space,
  Statistic,
  Table,
  Tabs,
  Tag,
  Timeline,
  Upload,
} from "antd";
import {
  CheckCircleOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  EyeOutlined,
  FileAddOutlined,
  FolderOutlined,
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
  StopOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import { api } from "./api";
import { rememberCaseDetailTarget } from "./caseDetailNavigation";
import { rememberContractDetailTarget } from "./contractDetailNavigation";
import { rememberCustomerDetailTarget } from "./customerDetailNavigation";
import { resolveDetailRelation } from "./detailRelationResolver";
import { rememberTaskDetailTarget } from "./taskDetailNavigation";
import { rememberInvestigationDetailTarget } from "./investigationDetailNavigation";
import { consumeBusinessRecordDetailTarget, rememberBusinessRecordDetailTarget } from "./businessRecordDetailNavigation";
import { consumeDocumentSearchDetailTarget } from "./documentSearchDetailNavigation";
import { formatRequiredDate } from "./formSafety";
import RecordImportButton from "./RecordImportButton";
import "./document-center.css";

type RecordRow = {
  id: number;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
  owner: string;
  owner_display_name?: string;
  description?: string;
  data: Record<string, any>;
};
type Attachment = {
  id: number;
  record_id: number | null;
  record_no: string;
  record_title: string;
  category: string;
  original_name: string;
  content_type: string;
  size: number;
  uploader: string;
  uploader_display_name?: string;
  remark: string;
  created_at: string;
};
type SealAsset = { id: number; name: string; seal_type: string; status: string };
type Template = {
  id: number;
  name: string;
  category: string;
  version: string;
  description: string;
  fields: string[];
  is_active: boolean;
};
type HistoryEvent = {
  id: number;
  action: string;
  from_status: string;
  to_status: string;
  operator: string;
  operator_display_name?: string;
  comment: string;
  created_at: string;
};
const archiveCategories = ["委托材料", "证据材料", "诉讼文书", "裁判文书"];
const allCategories = [
  ...archiveCategories,
  "收文附件",
  "发文附件",
  "合同附件",
  "财务凭证",
  "普通附件",
];
const fileSize = (n: number) =>
  n >= 1048576
    ? `${(n / 1048576).toFixed(2)} MB`
    : `${Math.max(1, Math.round(n / 1024))} KB`;
const personDisplayName = (value: unknown) =>
  String(value || "").trim() || "姓名待维护";

type ReceiptRow = RecordRow & {
  data: Record<string, any> & {
    case_no?: string;
    plaintiff?: string;
    defendant?: string;
    court_no?: string;
    court_name?: string;
    document_date?: string;
    uploaded_at?: string;
    import_status?: string;
    business_process_status?: string;
    uploader?: string;
    uploader_display_name?: string;
    hearing_lawyer?: string;
    hearing_lawyer_display_name?: string;
    assistant?: string;
    assistant_display_name?: string;
    brand_manager?: string;
    brand_manager_display_name?: string;
    case_manager?: string;
    case_manager_display_name?: string;
    handling_lawyer?: string;
    handling_lawyer_display_name?: string;
    signer_display_name?: string;
  };
};

export default function DocumentCenterPage({
  initialView,
  onNavigate,
}: {
  initialView: string;
  onNavigate?: (route: string) => void;
}) {
  const profile = useMemo(() => {
    try {
      return JSON.parse(localStorage.getItem("user") || "{}");
    } catch {
      return {};
    }
  }, []);
  const first =
    initialView === "documents-template"
      ? "templates"
      : initialView === "documents-archive"
        ? "archive"
        : initialView === "documents-files"
          ? "files"
          : initialView === "documents-official"
            ? "official"
            : initialView === "documents-outgoing"
              ? "outgoing"
            : initialView === "documents-my"
              ? "my-receipts"
              : initialView === "documents-company"
                ? "company-receipts"
                : "documents";
  const [tab, setTab] = useState(first);
  const [documents, setDocuments] = useState<RecordRow[]>([]);
  const [outgoingDocuments, setOutgoingDocuments] = useState<RecordRow[]>([]);
  const [contracts, setContracts] = useState<RecordRow[]>([]);
  const [sealAssets, setSealAssets] = useState<SealAsset[]>([]);
  const [outgoingOpen, setOutgoingOpen] = useState(false);
  const [outgoingSelected, setOutgoingSelected] = useState<Key[]>([]);
  const [outgoingDetail, setOutgoingDetail] = useState<any>(null);
  const [outgoingHistory, setOutgoingHistory] = useState<HistoryEvent[]>([]);
  const [editingOutgoing, setEditingOutgoing] = useState<any>(null);
  const [outgoingReview, setOutgoingReview] = useState<{ row: RecordRow; approved: boolean } | null>(null);
  const [outgoingQuery, setOutgoingQuery] = useState<Record<string, string>>({});
  const [cases, setCases] = useState<RecordRow[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [summary, setSummary] = useState({
    documents: 0,
    pending_receipt: 0,
    received: 0,
    attachments: 0,
    archive_materials: 0,
    templates: 0,
  });
  const [loading, setLoading] = useState(false);
  const [documentOpen, setDocumentOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [templateOpen, setTemplateOpen] = useState(false);
  const [viewing, setViewing] = useState<RecordRow | null>(null);
  const [history, setHistory] = useState<HistoryEvent[]>([]);
  const [actionStatus, setActionStatus] = useState("");
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null);
  const [attachmentDetail, setAttachmentDetail] = useState<Attachment | null>(null);
  const [templateDetail, setTemplateDetail] = useState<Template | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewName, setPreviewName] = useState("");
  const [previewKind, setPreviewKind] = useState<"image" | "pdf" | "text">("text");
  const [previewText, setPreviewText] = useState("");
  const [previewUrl, setPreviewUrl] = useState("");
  const [uploadTarget, setUploadTarget] = useState<RecordRow | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [documentForm] = Form.useForm();
  const [uploadForm] = Form.useForm();
  const [templateForm] = Form.useForm();
  const [actionForm] = Form.useForm();
  const [receiptForm] = Form.useForm();
  const [outgoingForm] = Form.useForm();
  const [outgoingReviewForm] = Form.useForm();
  const [outgoingQueryForm] = Form.useForm();
  const openCaseDetail = async (caseNo: unknown) => {
    const serialNo = String(caseNo || "").trim();
    if (!serialNo || serialNo === "—") {
      message.warning("当前文档未关联案件");
      return;
    }
    try {
      const record = await resolveDetailRelation("case", { serial_no: serialNo });
      if (!record) return message.warning("未找到关联案件或当前账号无权查看");
      rememberCaseDetailTarget({ id: record.id, serial_no: record.serial_no });
      onNavigate?.("case-company");
    } catch (error: any) { message.error(error?.response?.data?.detail || "关联案件加载失败"); }
  };
  const openCustomerDetail = async (customerName: unknown) => {
    const title = String(customerName || "").trim();
    if (!title || title === "—") {
      message.warning("当前文档未关联客户");
      return;
    }
    try {
      const response = await api.get("/records", {
        params: { module: "customer", keyword: title, page_size: 100 },
      });
      const customer = (response.data.items as RecordRow[]).find(
        (item) => item.title === title || item.customer === title,
      );
      if (!customer) {
        message.warning("未找到关联客户档案或当前账号无权查看");
        return;
      }
      rememberCustomerDetailTarget({
        id: customer.id,
        serial_no: customer.serial_no,
        title: customer.title,
      });
      onNavigate?.("customer-company");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "关联客户加载失败");
    }
  };
  const openAttachmentRecord = async (attachment: Attachment) => {
    if (!attachment.record_id) {
      message.warning("该文件未关联业务记录");
      return;
    }
    try {
      const { data: record } = await api.get(`/records/${attachment.record_id}`);
      switch (record.module) {
        case "case":
          rememberCaseDetailTarget({ serial_no: record.serial_no });
          onNavigate?.("case-company");
          return;
        case "contract":
          rememberContractDetailTarget({ serial_no: record.serial_no });
          onNavigate?.("contract-company");
          return;
        case "customer":
          rememberCustomerDetailTarget({ id: record.id, serial_no: record.serial_no, title: record.title });
          onNavigate?.("customer-company");
          return;
        case "task":
          rememberTaskDetailTarget({ id: record.id, serial_no: record.serial_no });
          onNavigate?.("task-my-created");
          return;
        case "clue":
        case "investigation":
        case "notary":
        case "evidence":
          rememberInvestigationDetailTarget({ id: record.id, serial_no: record.serial_no, module: record.module });
          onNavigate?.("clue-my-collect");
          return;
        case "document":
          openDocument(record as RecordRow);
          return;
        case "finance":
        case "invoice":
        case "refund":
        case "finance_package":
        case "finance_settlement":
        case "finance_archive_settlement":
        case "seal":
        case "warehouse":
        case "hr": {
          if (!rememberBusinessRecordDetailTarget({ id: record.id, module: record.module })) {
            message.warning("关联业务不存在或当前账号无权查看");
            return;
          }
          const routes: Record<string, string> = {
            finance: "finance-fee-query",
            invoice: "finance-invoice-mine",
            refund: "finance-refund",
            finance_package: "finance-fee-query",
            finance_settlement: "finance-fee-query",
            finance_archive_settlement: "finance-fee-query",
            seal: "seal-my",
            warehouse: "warehouse",
            hr: "hr-all",
          };
          onNavigate?.(routes[record.module]);
          return;
        }
        default:
          message.info("该关联业务暂不支持详情查看");
      }
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "关联业务不存在或当前账号无权查看");
    }
  };
  const [receiptQuery, setReceiptQuery] = useState<Record<string, any>>({});
  const [selectedReceiptKeys, setSelectedReceiptKeys] = useState<Key[]>([]);
  const [receiptDateOpen, setReceiptDateOpen] = useState(false);
  const [receiptDate, setReceiptDate] = useState<ReturnType<typeof dayjs> | null>(
    null,
  );
  const load = async (outgoingQueryOverride = outgoingQuery) => {
    setLoading(true);
    try {
      const [docRes, outgoingRes, caseRes, contractRes, fileRes, sealAssetsRes, templateRes, summaryRes] =
        await Promise.all([
          api.get("/records", {
            params: { module: "document", page_size: 100 },
          }),
          api.get("/official-outgoing", { params: outgoingQueryOverride }),
          api.get("/records", { params: { module: "case", page_size: 100 } }),
          api.get("/records", { params: { module: "contract", page_size: 100 } }),
          api.get("/attachments"),
          api.get("/seals/assets"),
          api.get("/templates"),
          api.get("/documents/summary"),
        ]);
      setDocuments(docRes.data.items);
      setOutgoingDocuments(outgoingRes.data.items || []);
      setCases(caseRes.data.items);
      setContracts(contractRes.data.items);
      setAttachments(fileRes.data.items);
      setSealAssets(sealAssetsRes.data.items || []);
      setTemplates(templateRes.data.items);
      setSummary(summaryRes.data);
    } catch {
      message.error("收发文数据加载失败");
    } finally {
      setLoading(false);
    }
  };
  const searchOfficialOutgoing = async () => {
    const values = outgoingQueryForm.getFieldsValue();
    const applicationDates = values.application_dates || [];
    const params = Object.fromEntries(Object.entries({
      official_no: String(values.official_no || "").trim(), owner: String(values.owner || "").trim(), customer: String(values.customer || "").trim(),
      case_no: String(values.case_no || "").trim(), contract_no: String(values.contract_no || "").trim(), status_value: String(values.status_value || "").trim(),
      seal_type: String(values.seal_type || "").trim(), file_name: String(values.file_name || "").trim(),
      application_date_from: applicationDates[0] ? applicationDates[0].format("YYYY-MM-DD") : "", application_date_to: applicationDates[1] ? applicationDates[1].format("YYYY-MM-DD") : "",
    }).filter(([, value]) => Boolean(value)) as [string, string][]);
    setOutgoingSelected([]);
    setOutgoingQuery(params);
    await load(params);
  };
  const resetOfficialOutgoingSearch = async () => {
    outgoingQueryForm.resetFields();
    setOutgoingSelected([]);
    setOutgoingQuery({});
    await load({});
  };
  useEffect(() => {
    setTab(first);
    load();
  }, [initialView]);
  const createOfficialOutgoing = async () => {
    const values = await outgoingForm.validateFields();
    const source = (values.source_type === "case" ? cases : contracts).find((item) => item.id === Number(values.source_record_id));
    if (!source) return;
    try {
      await api.post("/official-outgoing", {
        title: values.title,
        source_type: values.source_type,
        source_record_id: source.id,
        source_file_ids: values.source_file_ids || [],
        seal_asset_id: Number(values.seal_asset_id),
        is_electronic_seal: Boolean(values.is_electronic_seal),
        is_offline_print: Boolean(values.is_offline_print),
        print_quantity: Number(values.print_quantity || 1),
        need_audit: values.need_audit !== false,
        content: values.content || "",
        remark: values.remark || "",
      });
      message.success("正式发文已创建" );
      setOutgoingOpen(false);
      outgoingForm.resetFields();
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "正式发文创建失败");
    }
  };
  const openOfficialOutgoingEditor = async (row: RecordRow) => {
    try {
      const detail = await api.get(`/official-outgoing/${row.id}`);
      const item = detail.data;
      setEditingOutgoing(item);
      outgoingForm.setFieldsValue({
        title: item.title,
        source_type: item.source_type,
        source_record_id: item.source_record_id,
        source_file_ids: item.source_file_ids || [],
        seal_asset_id: Number(item.seal_asset_id) || undefined,
        is_electronic_seal: Boolean(item.is_electronic_seal),
        is_offline_print: Boolean(item.is_offline_print),
        print_quantity: Number(item.print_quantity || 1),
        need_audit: item.need_audit !== false,
        content: item.content || "",
        remark: item.description || "",
      });
      setOutgoingOpen(true);
    } catch (error: any) { message.error(error?.response?.data?.detail || "正式发文详情加载失败"); }
  };
  const updateOfficialOutgoing = async () => {
    if (!editingOutgoing) return;
    const values = await outgoingForm.validateFields();
    try {
      await api.patch(`/official-outgoing/${editingOutgoing.id}`, {
        title: values.title,
        seal_asset_id: Number(values.seal_asset_id),
        is_electronic_seal: Boolean(values.is_electronic_seal),
        is_offline_print: Boolean(values.is_offline_print),
        print_quantity: Number(values.print_quantity || 1),
        need_audit: values.need_audit !== false,
        content: values.content || "",
        remark: values.remark || "",
      });
      message.success("正式发文已保存");
      setOutgoingOpen(false);
      setEditingOutgoing(null);
      outgoingForm.resetFields();
      await load();
    } catch (error: any) { message.error(error?.response?.data?.detail || "正式发文保存失败"); }
  };
  const reviewOfficialOutgoing = async (row: RecordRow, approved: boolean, comment: string) => {
    try {
      await api.post(`/official-outgoing/${row.id}/review`, { approved, comment: comment.trim() });
      message.success(approved ? "正式发文已通过" : "正式发文已拒绝");
      setOutgoingReview(null);
      outgoingReviewForm.resetFields();
      await load();
      if (outgoingDetail?.id === row.id) await openOfficialOutgoingDetail(row);
    } catch (error: any) { message.error(error?.response?.data?.detail || "正式发文审批失败"); }
  };
  const rollbackOfficialOutgoing = async (row: RecordRow) => {
    try {
      await api.post(`/official-outgoing/${row.id}/rollback`, { reason: "申请人撤回正式发文" });
      message.success("正式发文已撤回");
      load();
    } catch (error: any) { message.error(error?.response?.data?.detail || "正式发文撤回失败"); }
  };
  const openOfficialOutgoingDetail = async (row: RecordRow) => {
    try {
      const [detail, historyResult] = await Promise.all([
        api.get(`/official-outgoing/${row.id}`),
        api.get(`/records/${row.id}/history`),
      ]);
      setOutgoingDetail(detail.data);
      setOutgoingHistory(historyResult.data.items || []);
    }
    catch (error: any) { message.error(error?.response?.data?.detail || "正式发文详情加载失败"); }
  };
  const openOfficialOutgoingSource = (row: any) => {
    if (row.source_type === "case") {
      void openCaseDetail(row.source_serial_no);
      return;
    }
    if (!row.source_serial_no) {
      message.warning("正式发文未关联可查看的来源合同");
      return;
    }
    rememberContractDetailTarget({ id: Number(row.source_record_id) || undefined, serial_no: row.source_serial_no });
    onNavigate?.("contract-company");
  };
  const submitOfficialOutgoing = async (row: RecordRow) => {
    try { await api.post(`/official-outgoing/${row.id}/submit`, {}); message.success("正式发文已提交"); await load(); await openOfficialOutgoingDetail(row); }
    catch (error: any) { message.error(error?.response?.data?.detail || "正式发文提交失败"); }
  };
  const uploadOfficialOutgoingFile = async (row: any, uploadFile: File, stamped = false) => {
    const data = new FormData(); data.append("file", uploadFile);
    try {
      if (stamped) await api.post(`/official-outgoing/${row.id}/stamp-file`, data);
      else { data.append("record_id", String(row.id)); data.append("category", "正式发文附件"); await api.post("/attachments", data); }
      message.success(stamped ? "盖章文件已上传" : "正式发文附件已上传"); await load(); await openOfficialOutgoingDetail(row);
    } catch (error: any) { message.error(error?.response?.data?.detail || "文件上传失败"); }
    return false;
  };
  const deleteOfficialOutgoingFile = async (row: any, attachment: Attachment) => {
    try {
      await api.delete(`/attachments/${attachment.id}`);
      message.success("正式发文附件已删除");
      await load();
      await openOfficialOutgoingDetail(row);
    } catch (error: any) { message.error(error?.response?.data?.detail || "正式发文附件删除失败"); }
  };
  const downloadOfficialOutgoing = async () => {
    if (!outgoingSelected.length) return message.warning("请先勾选需要打包下载的正式发文");
    try {
      const response = await api.post("/official-outgoing/download", { record_ids: outgoingSelected }, { responseType: "blob" });
      const url = URL.createObjectURL(response.data); const link = document.createElement("a"); link.href = url; link.download = "正式发文附件.zip"; link.click(); URL.revokeObjectURL(url);
    } catch (error: any) { message.error(error?.response?.data?.detail || "正式发文打包下载失败"); }
  };
  const markOfficialOutgoingStamped = async () => {
    if (!outgoingSelected.length) return message.warning("请先勾选审批通过的正式发文");
    const invalid = outgoingDocuments.filter((item) => outgoingSelected.includes(item.id) && item.status !== "已通过");
    if (invalid.length) return message.warning("“标记已盖章”仅支持审批通过的正式发文；已盖章文书可直接打包下载");
    try {
      await api.post("/official-outgoing/mark-stamped", { record_ids: outgoingSelected });
      message.success("所选正式发文已标记为已盖章");
      setOutgoingSelected([]);
      await load();
    } catch (error: any) { message.error(error?.response?.data?.detail || "标记正式发文盖章失败"); }
  };
  useEffect(() => {
    const target = consumeDocumentSearchDetailTarget();
    if (!target) return;
    void (async () => {
      try {
        if (target.kind === "attachment") {
          const { data } = await api.get(`/attachments/${target.id}`);
          setTab("files");
          setAttachmentDetail(data);
        } else {
          const { data } = await api.get(`/templates/${target.id}`);
          setTab("templates");
          setTemplateDetail(data);
        }
      } catch (error: any) {
        message.warning(error?.response?.data?.detail || "关联附件或模板不存在，或当前账号无权查看");
      }
    })();
  }, []);
  const createDocument = async () => {
    const v = await documentForm.validateFields();
    try {
      await api.post("/records", {
        module: "document",
        serial_no: `SW${Date.now()}`,
        title: v.title,
        customer: v.customer || "",
        status: "待登记",
        owner: v.owner || profile.username || "admin",
        department: profile.department || "上海分所",
        description: v.description || "",
        data: {
          direction: v.direction,
          document_date: v.document_date?.format("YYYY-MM-DD") || "",
          case_no: v.case_no || "",
          sender: v.sender || "",
        },
      });
      message.success("收发文草稿已保存，请完成登记");
      setDocumentOpen(false);
      documentForm.resetFields();
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "登记失败");
    }
  };
  const openUpload = (target?: RecordRow, category?: string) => {
    setUploadTarget(target || null);
    setFile(null);
    uploadForm.setFieldsValue({
      record_id: target?.id,
      category: category || "普通附件",
      document_date: dayjs(),
      remark: "",
    });
    setUploadOpen(true);
  };
  const upload = async () => {
    const v = await uploadForm.validateFields();
    if (!file) {
      message.warning("请选择文件");
      return;
    }
    const form = new FormData();
    const officialImport = tab === "official";
    form.append("file", file);
    if (officialImport) {
      form.append("document_date", formatRequiredDate(v.document_date, "收文日期"));
      const linkedCase = cases.find((item) => item.id === Number(v.record_id));
      if (linkedCase) form.append("case_ids", String(linkedCase.id));
    } else if (v.record_id) {
      form.append("record_id", String(v.record_id));
    }
    form.append("category", v.category);
    form.append("remark", v.remark || "");
    try {
      await api.post(officialImport ? "/documents/official/upload" : "/attachments", form);
      message.success(officialImport ? "官文已上传并生成收文记录" : "文件上传成功");
      setUploadOpen(false);
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "上传失败");
    }
  };
  const download = async (row: Attachment) => {
    try {
      const res = await api.get(`/attachments/${row.id}/download`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = row.original_name;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      message.error("下载失败");
    }
  };
  const previewAttachment = async (row: Attachment) => {
    try {
      const { data } = await api.get(`/attachments/${row.id}/preview`);
      if (data.kind === "unsupported") {
        message.info(data.detail || "当前文件格式暂不支持在线预览，请下载后查看");
        return;
      }
      setPreviewName(row.original_name);
      setPreviewKind(data.kind);
      setPreviewText(data.text || "");
      if (data.kind === "image" || data.kind === "pdf") {
        const response = await api.get(`/attachments/${row.id}/download`, { responseType: "blob" });
        setPreviewUrl(URL.createObjectURL(response.data));
      } else {
        setPreviewUrl("");
      }
      setPreviewOpen(true);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "附件预览失败");
    }
  };  const deleteFile = async (id: number) => {
    try {
      await api.delete(`/attachments/${id}`);
      message.success("附件已删除");
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "删除失败");
    }
  };
  const saveTemplate = async () => {
    const v = await templateForm.validateFields();
    try {
      if (editingTemplate)
        await api.patch(`/templates/${editingTemplate.id}`, {
          ...v,
          fields: v.fields || [],
        });
      else await api.post("/templates", { ...v, fields: v.fields || [] });
      message.success(editingTemplate ? "模板已更新" : "模板已创建");
      setTemplateOpen(false);
      setEditingTemplate(null);
      templateForm.resetFields();
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "模板保存失败");
    }
  };
  const editTemplate = (row: Template) => {
    setEditingTemplate(row);
    templateForm.setFieldsValue({
      name: row.name,
      category: row.category,
      version: row.version,
      description: row.description,
      fields: row.fields,
    });
    setTemplateOpen(true);
  };
  const toggleTemplate = async (row: Template) => {
    try {
      await api.patch(`/templates/${row.id}`, { is_active: !row.is_active });
      message.success(row.is_active ? "模板已停用" : "模板已启用");
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "状态修改失败");
    }
  };
  const deleteTemplate = async (id: number) => {
    try {
      await api.delete(`/templates/${id}`);
      message.success("模板已删除");
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "删除失败");
    }
  };
  const openDocument = async (row: RecordRow) => {
    setViewing(row);
    try {
      const { data } = await api.get(`/records/${row.id}/history`);
      setHistory(data.items);
    } catch {
      message.error("流程记录加载失败");
    }
  };
  useEffect(() => {
    const target = consumeBusinessRecordDetailTarget("document");
    if (!target) return;
    void (async () => {
      try {
        const { data } = await api.get(`/records/${target.id}`);
        if (data.module !== "document") throw new Error("关联记录不是收发文");
        await openDocument(data);
      } catch (error: any) {
        message.error(error?.response?.data?.detail || error?.message || "收发文详情加载失败");
      }
    })();
  }, []);
  const startAction = (row: RecordRow, toStatus: string) => {
    setViewing(row);
    setActionStatus(toStatus);
    actionForm.resetFields();
    actionForm.setFieldsValue({ action_date: dayjs(), handler: personDisplayName(profile.display_name) });
  };
  const submitAction = async () => {
    if (!viewing) return;
    const v = await actionForm.validateFields();
    try {
      const { data } = await api.post(`/documents/${viewing.id}/transition`, {
        to_status: actionStatus,
        action_date: formatRequiredDate(v.action_date, "办理日期"),
        handler: v.handler || "",
        archive_no: v.archive_no || "",
        archive_location: v.archive_location || "",
        comment: v.comment || "",
      });
      message.success(
        actionStatus === "待签收"
          ? "登记完成"
          : actionStatus === "已签收"
            ? data.data.direction === "发文"
              ? "已确认送达"
              : "已确认签收"
            : "文档已归档",
      );
      setActionStatus("");
      setViewing(data);
      const result = await api.get(`/records/${data.id}/history`);
      setHistory(result.data.items);
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "办理失败");
    }
  };
  const documentAction = (r: RecordRow) =>
    r.status === "待登记" ? (
      <Button type="link" onClick={() => startAction(r, "待签收")}>
        完成登记
      </Button>
    ) : r.status === "待签收" ? (
      <Button
        type="link"
        icon={<CheckCircleOutlined />}
        onClick={() => startAction(r, "已签收")}
      >
        {r.data.direction === "发文" ? "确认送达" : "确认签收"}
      </Button>
    ) : r.status === "已签收" ? (
      <Button
        type="link"
        icon={<FolderOutlined />}
        onClick={() => startAction(r, "已归档")}
      >
        归档
      </Button>
    ) : null;
  const documentColumns = [
    {
      title: "文号",
      dataIndex: "serial_no",
      width: 160,
      render: (v: string, r: RecordRow) => (
        <a onClick={() => openDocument(r)}>{v}</a>
      ),
    },
    { title: "文件名称", dataIndex: "title", width: 240, ellipsis: true },
    {
      title: "收发类型",
      key: "direction",
      width: 90,
      render: (_: unknown, r: RecordRow) => (
        <Tag color={r.data.direction === "发文" ? "blue" : "green"}>
          {r.data.direction || "收文"}
        </Tag>
      ),
    },
    {
      title: "客户",
      dataIndex: "customer",
      width: 170,
      render: (value: string) => value ? <Button type="link" onClick={() => void openCustomerDetail(value)}>{value}</Button> : "—",
    },
    {
      title: "关联案号",
      key: "case",
      width: 145,
      render: (_: unknown, r: RecordRow) => r.data.case_no ? <Button type="link" onClick={() => openCaseDetail(r.data.case_no)}>{r.data.case_no}</Button> : "—",
    },
    {
      title: "来文/送达单位",
      key: "sender",
      width: 160,
      render: (_: unknown, r: RecordRow) => r.data.sender || "—",
    },
    { title: "负责人", dataIndex: "owner_display_name", width: 90, render: personDisplayName },
    {
      title: "状态",
      dataIndex: "status",
      width: 90,
      render: (v: string) => (
        <Tag
          color={v === "已归档" ? "green" : v === "已签收" ? "blue" : "orange"}
        >
          {v}
        </Tag>
      ),
    },
    {
      title: "附件",
      key: "files",
      width: 65,
      render: (_: unknown, r: RecordRow) =>
        attachments.filter((a) => a.record_id === r.id).length,
    },
    {
      title: "操作",
      key: "actions",
      fixed: "right" as const,
      width: 260,
      render: (_: unknown, r: RecordRow) => (
        <Space size={0}>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => openDocument(r)}
          >
            详情
          </Button>
          <Button
            type="link"
            icon={<UploadOutlined />}
            onClick={() =>
              openUpload(
                r,
                r.data.direction === "发文" ? "发文附件" : "收文附件",
              )
            }
          >
            附件
          </Button>
          {documentAction(r)}
        </Space>
      ),
    },
  ];
  const fileColumns = [
    { title: "文件名", dataIndex: "original_name", width: 260 },
    {
      title: "分类",
      dataIndex: "category",
      width: 110,
      render: (v: string) => (
        <Tag color={archiveCategories.includes(v) ? "green" : "blue"}>{v}</Tag>
      ),
    },
    {
      title: "关联编号",
      dataIndex: "record_no",
      width: 160,
      render: (v: string, r: Attachment) =>
        r.record_id ? <Button type="link" onClick={() => openAttachmentRecord(r)}>{v || "查看关联业务"}</Button> : "公共文件",
    },
    {
      title: "关联业务",
      dataIndex: "record_title",
      width: 220,
      ellipsis: true,
      render: (v: string, r: Attachment) =>
        r.record_id ? <Button type="link" onClick={() => openAttachmentRecord(r)}>{v || r.record_no || "查看关联业务"}</Button> : "—",
    },
    { title: "大小", dataIndex: "size", width: 90, render: fileSize },
    { title: "上传人", dataIndex: "uploader_display_name", width: 90, render: personDisplayName },
    {
      title: "上传时间",
      dataIndex: "created_at",
      width: 165,
      render: (v: string) => new Date(v).toLocaleString(),
    },
    { title: "备注", dataIndex: "remark", width: 160 },
    {
      title: "操作",
      key: "actions",
      fixed: "right" as const,
      width: 130,
      render: (_: unknown, r: Attachment) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => void previewAttachment(r)}
          >
            查看
          </Button>
          <Button
            type="link"
            icon={<DownloadOutlined />}
            onClick={() => download(r)}
          >
            下载
          </Button>
          <Popconfirm
            title="确定删除此附件？"
            onConfirm={() => deleteFile(r.id)}
          >
            <Button danger type="link" icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];
  const templateColumns = [
    { title: "模板名称", dataIndex: "name", width: 220, render: (value: string, row: Template) => <Button type="link" onClick={() => setTemplateDetail(row)}>{value}</Button> },
    {
      title: "分类",
      dataIndex: "category",
      width: 110,
      render: (v: string) => <Tag color="green">{v}</Tag>,
    },
    { title: "版本", dataIndex: "version", width: 90 },
    {
      title: "模板字段",
      dataIndex: "fields",
      width: 360,
      render: (v: string[]) => (
        <Space wrap>
          {v.map((x) => (
            <Tag key={x}>{x}</Tag>
          ))}
        </Space>
      ),
    },
    { title: "说明", dataIndex: "description" },
    {
      title: "状态",
      dataIndex: "is_active",
      width: 80,
      render: (v: boolean) => (
        <Tag color={v ? "green" : "default"}>{v ? "启用" : "停用"}</Tag>
      ),
    },
    {
      title: "操作",
      key: "actions",
      fixed: "right" as const,
      width: 190,
      render: (_: unknown, r: Template) => (
        <Space size={0}>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => editTemplate(r)}
          >
            编辑
          </Button>
          <Popconfirm
            title={`确定${r.is_active ? "停用" : "启用"}此模板？`}
            onConfirm={() => toggleTemplate(r)}
          >
            <Button type="link" icon={<StopOutlined />}>
              {r.is_active ? "停用" : "启用"}
            </Button>
          </Popconfirm>
          <Popconfirm
            title="确定删除此模板？"
            onConfirm={() => deleteTemplate(r.id)}
          >
            <Button danger type="link" icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];
  const archiveRows = useMemo(
    () =>
      cases.map((c) => {
        const categories = new Set(
          attachments
            .filter((a) => a.record_id === c.id)
            .map((a) => a.category),
        );
        const done = archiveCategories.filter((x) => categories.has(x)).length;
        return {
          ...c,
          categories,
          done,
          percent: (done / archiveCategories.length) * 100,
        };
      }),
    [cases, attachments],
  );
  const archiveColumns = [
    { title: "案号", dataIndex: "serial_no", width: 155, render: (value: string, r: RecordRow) => value ? <Button type="link" onClick={() => openCaseDetail(value)}>{value}</Button> : "—" },
    { title: "案件名称", dataIndex: "title", width: 250 },
    { title: "客户", dataIndex: "customer", width: 190, render: (value: string) => value ? <Button type="link" onClick={() => void openCustomerDetail(value)}>{value}</Button> : "—" },
    {
      title: "归档材料",
      key: "materials",
      width: 400,
      render: (_: unknown, r: any) => (
        <Space wrap>
          {archiveCategories.map((c) => (
            <Tag key={c} color={r.categories.has(c) ? "green" : "default"}>
              {r.categories.has(c) ? "✓ " : "○ "}
              {c}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: "完整度",
      key: "progress",
      width: 170,
      render: (_: unknown, r: any) => (
        <Progress
          percent={r.percent}
          size="small"
          status={r.percent === 100 ? "success" : "active"}
        />
      ),
    },
    {
      title: "操作",
      key: "action",
      width: 95,
      render: (_: unknown, r: RecordRow) => (
        <Button
          type="link"
          icon={<UploadOutlined />}
          onClick={() => openUpload(r, "委托材料")}
        >
          上传材料
        </Button>
      ),
    },
  ];
  const receiptRows = useMemo<ReceiptRow[]>(() => {
    const live = documents
      .filter((d) => (d.data.direction || "收文") === "收文")
      .map(
        (d) =>
          ({
            ...d,
            data: {
              ...d.data,
              case_no: d.data.case_no || d.serial_no,
              plaintiff: d.data.plaintiff || d.customer,
              defendant: d.data.defendant || d.data.sender || "—",
              court_no: d.data.court_no || "—",
              court_name: d.data.court_name || d.data.sender || "—",
              document_date: d.data.document_date || d.data.received_at || "",
              uploaded_at: d.data.uploaded_at || d.data.registered_at || "",
              uploader: d.data.uploader || d.owner,
              import_status: d.data.import_status || "已导入",
              business_process_status: d.data.business_process_status || "未处理",
              hearing_lawyer: d.data.hearing_lawyer || d.owner,
              assistant: d.data.assistant || "—",
              brand_manager: d.data.brand_manager || "—",
              case_manager: d.data.case_manager || "—",
              handling_lawyer: d.data.handling_lawyer || d.owner,
            },
          }) as ReceiptRow,
      );
    return live;
  }, [documents]);
  const searchedReceipts = useMemo(
    () =>
      receiptRows.filter((r) => {
        const q = receiptQuery,
          d = r.data;
        const names = [profile.username, profile.display_name].filter(Boolean);
        if (tab === "my-receipts" && !names.includes(d.uploader || r.owner))
          return false;
        const contains = (value: unknown, key: string) =>
          !q[key] ||
          String(value || "")
            .toLowerCase()
            .includes(String(q[key]).trim().toLowerCase());
        const ur = q.upload_range,
          rr = q.receipt_range,
          ud = d.uploaded_at || "",
          rd = d.document_date || "";
        return (
          contains(d.case_no, "case_no") &&
          contains(r.title, "file_name") &&
          contains(d.court_no, "court_no") &&
          contains(d.court_name, "court_name") &&
          contains(d.plaintiff, "plaintiff") &&
          contains(d.defendant, "defendant") &&
          contains(d.hearing_lawyer, "hearing_lawyer") &&
          contains(d.case_manager, "case_manager") &&
          contains(d.handling_lawyer, "handling_lawyer") &&
          contains(d.assistant, "assistant") &&
          contains(r.title, "document_name") &&
          (!q.import_status || d.import_status === q.import_status) &&
          (!q.business_process_status ||
            (d.business_process_status || "未处理") === q.business_process_status) &&
          (!ur ||
            (ud >= ur[0].format("YYYY-MM-DD") &&
              ud <= ur[1].format("YYYY-MM-DD"))) &&
          (!rr ||
            (rd >= rr[0].format("YYYY-MM-DD") &&
              rd <= rr[1].format("YYYY-MM-DD")))
        );
      }),
    [receiptRows, receiptQuery, profile, tab],
  );
  const showReceipt = (r: ReceiptRow) => openDocument(r);
  const receiptAttachment = (r: ReceiptRow) =>
    attachments.find((a) => a.record_id === r.id);
  const previewReceiptFile = (r: ReceiptRow) => {
    const file = receiptAttachment(r);
    if (!file) return showReceipt(r);
    void previewAttachment(file);
  };
  const officialColumns = [
    {
      title: "案号",
      key: "case_no",
      width: 145,
      render: (_: unknown, r: ReceiptRow) => r.data.case_no ? (
        <Button type="link" onClick={() => openCaseDetail(r.data.case_no)}>{r.data.case_no}</Button>
      ) : "—",
    },
    {
      title: "原告",
      key: "plaintiff",
      width: 210,
      render: (_: unknown, r: ReceiptRow) => r.data.plaintiff || "—",
    },
    {
      title: "被告",
      key: "defendant",
      width: 245,
      ellipsis: true,
      render: (_: unknown, r: ReceiptRow) => r.data.defendant || "—",
    },
    {
      title: "文件名称",
      dataIndex: "title",
      width: 430,
      ellipsis: true,
      render: (v: string, r: ReceiptRow) => (
        <Space size={0}>
          <a onClick={() => showReceipt(r)}>{v}</a>
          {receiptAttachment(r) && (
            <Button
              type="link"
              icon={<EyeOutlined />}
              onClick={() => previewReceiptFile(r)}
            >
              查看
            </Button>
          )}
        </Space>
      ),
    },
    {
      title: "文件日期",
      key: "document_date",
      width: 105,
      render: (_: unknown, r: ReceiptRow) => r.data.document_date || "—",
    },
    {
      title: "上传日期",
      key: "uploaded_at",
      width: 105,
      render: (_: unknown, r: ReceiptRow) => r.data.uploaded_at || "—",
    },
    {
      title: "上传人",
      key: "uploader",
      width: 90,
      render: (_: unknown, r: ReceiptRow) => personDisplayName(r.data.uploader_display_name || r.owner_display_name),
    },
    {
      title: "状态",
      key: "import_status",
      width: 80,
      render: (_: unknown, r: ReceiptRow) => (
        <span className="receipt-imported">
          {r.data.import_status || "已导入"}
        </span>
      ),
    },
    {
      title: "业务处理",
      key: "business_process_status",
      width: 96,
      render: (_: unknown, r: ReceiptRow) => {
        const processed = (r.data.business_process_status || "未处理") === "已处理";
        return <Tag color={processed ? "green" : "orange"}>{processed ? "已处理" : "未处理"}</Tag>;
      },
    },
  ];
  const receivedColumns = [
    {
      title: "收文日",
      key: "document_date",
      width: 100,
      render: (_: unknown, r: ReceiptRow) => r.data.document_date || "—",
    },
    {
      title: "案号",
      key: "case_no",
      width: 145,
      render: (_: unknown, r: ReceiptRow) => r.data.case_no ? (
        <Button type="link" onClick={() => openCaseDetail(r.data.case_no)}>{r.data.case_no}</Button>
      ) : "—",
    },
    {
      title: "法院案号",
      key: "court_no",
      width: 180,
      ellipsis: true,
      render: (_: unknown, r: ReceiptRow) => r.data.court_no || "—",
    },
    {
      title: "原告",
      key: "plaintiff",
      width: 200,
      ellipsis: true,
      render: (_: unknown, r: ReceiptRow) => r.data.plaintiff || "—",
    },
    {
      title: "被告",
      key: "defendant",
      width: 220,
      ellipsis: true,
      render: (_: unknown, r: ReceiptRow) => r.data.defendant || "—",
    },
    {
      title: "文件名称",
      dataIndex: "title",
      width: 350,
      ellipsis: true,
      render: (v: string, r: ReceiptRow) => (
        <Space size={0}>
          <a onClick={() => showReceipt(r)}>{v}</a>
          {receiptAttachment(r) && (
            <Button
              type="link"
              icon={<EyeOutlined />}
              onClick={() => previewReceiptFile(r)}
            >
              查看
            </Button>
          )}
        </Space>
      ),
    },
    {
      title: "上传日期",
      key: "uploaded_at",
      width: 100,
      render: (_: unknown, r: ReceiptRow) => r.data.uploaded_at || "—",
    },
    {
      title: "开庭律师",
      key: "hearing_lawyer",
      width: 90,
      render: (_: unknown, r: ReceiptRow) => personDisplayName(r.data.hearing_lawyer_display_name),
    },
    {
      title: "律师助理",
      key: "assistant",
      width: 90,
      render: (_: unknown, r: ReceiptRow) => personDisplayName(r.data.assistant_display_name),
    },
    {
      title: "品牌管理人",
      key: "brand_manager",
      width: 100,
      render: (_: unknown, r: ReceiptRow) => personDisplayName(r.data.brand_manager_display_name),
    },
  ];
  const isReceiptView = [
    "official",
    "my-receipts",
    "company-receipts",
  ].includes(tab);
  const receiptSearch = () => setReceiptQuery(receiptForm.getFieldsValue());
  const clearReceiptSearch = () => {
    receiptForm.resetFields();
    setReceiptQuery({});
  };
  const selectedFormalReceipts = receiptRows.filter(
    (row) => row.id > 0 && selectedReceiptKeys.includes(row.id),
  );
  const deleteSelectedReceipts = async () => {
    if (!selectedFormalReceipts.length) {
      message.warning("请选择需要删除的正式收文记录");
      return;
    }
    try {
      const { data } = await api.post("/documents/official/delete", {
        record_ids: selectedFormalReceipts.map((row) => row.id),
      });
      if (data.deleted !== selectedFormalReceipts.length) {
        throw new Error("Official receipt removal was incomplete");
      }
      message.success(`已删除 ${selectedFormalReceipts.length} 条正式收文记录`);
      setSelectedReceiptKeys([]);
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "删除收文记录失败");
    }
  };
  const exportOfficialReceipts = async () => {
    const source = selectedFormalReceipts.length
      ? selectedFormalReceipts
      : searchedReceipts;
    try {
      const response = await api.get("/documents/official/export", {
        params: { ids: source.map((row) => row.id).join(",") },
        responseType: "blob",
      });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = "官文收文.csv";
      link.click();
      URL.revokeObjectURL(url);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "官文导出失败");
    }
  };
  const openReceiptDateEditor = () => {
    if (!selectedFormalReceipts.length) {
      message.warning("请选择至少一条正式收文记录修改收文日期");
      return;
    }
    const current = selectedFormalReceipts[0].data.document_date;
    setReceiptDate(current ? dayjs(current) : dayjs());
    setReceiptDateOpen(true);
  };
  const saveReceiptDate = async () => {
    if (!selectedFormalReceipts.length || !receiptDate) {
      message.warning("请选择收文日期");
      return;
    }
    const date = receiptDate.format("YYYY-MM-DD");
    try {
      const { data } = await api.post("/documents/official/receipt-date", {
        record_ids: selectedFormalReceipts.map((row) => row.id),
        document_date: date,
      });
      message.success(`已修改 ${data.updated} 条收文日期`);
      setReceiptDateOpen(false);
      setSelectedReceiptKeys([]);
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "修改收文日期失败");
    }
  };
  const updateOfficialProcessStatus = async (processed: boolean) => {
    if (!selectedFormalReceipts.length) {
      message.warning("请选择需要标记的官文收文记录");
      return;
    }
    try {
      const { data } = await api.post("/documents/official/process", {
        record_ids: selectedFormalReceipts.map((row) => row.id),
        processed,
      });
      message.success(`已标记 ${data.processed} 条官文为${processed ? "已处理" : "未处理"}`);
      setSelectedReceiptKeys([]);
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "更新官文业务处理状态失败");
    }
  };
  const receiptMoreActionItems = [
    { key: "upload-case-files", label: "上传案件文档" },
    {
      key: "case-fees",
      label: "新增案件费用",
      children: [
        { key: "case-fee-office", label: "新增官费" },
        { key: "case-fee-agent", label: "新增代理费" },
        { key: "case-fee-other", label: "新增其他费用" },
      ],
    },
    { key: "internal-fee", label: "新增内部费用" },
    {
      key: "batch-update",
      label: "批量修改",
      children: [
        { key: "hearing-lawyer", label: "修改开庭律师" },
        { key: "handling-lawyer", label: "修改经办律师" },
        { key: "assistant", label: "修改律师助理" },
        { key: "case-phase", label: "修改案件阶段" },
      ],
    },
    { key: "authorization-letter", label: "生成授权委托书" },
    { key: "law-firm-letter", label: "生成律所函" },
    { key: "identity-certificate", label: "生成身份证明" },
    { key: "settlement-list", label: "生成结算提成表" },
    { key: "case-tasks", label: "案件任务" },
    { key: "case-logs", label: "案件日志" },
  ];
  const openSelectedReceiptCase = () => {
    const row = receiptRows.find((item) => selectedReceiptKeys.includes(item.id));
    if (!row) {
      message.warning("请选择需要操作的收文记录");
      return;
    }
    if (!row.data.case_no || row.data.case_no === "—") {
      message.warning("当前收文未关联案件，无法进入案件操作");
      return;
    }
    void openCaseDetail(row.data.case_no);
  };
  const handleReceiptMoreAction = (key: string) => {
    if (["authorization-letter", "law-firm-letter", "identity-certificate", "settlement-list"].includes(key)) {
      onNavigate?.("documents-agent");
      return;
    }
    openSelectedReceiptCase();
  };  const receiptPanel = isReceiptView ? (
    <Card
      className="panel receipt-original-panel"
      title={
        tab === "official"
          ? "官文收文"
          : tab === "my-receipts"
            ? "我的收文"
            : "公司收文"
      }
    >
      <Form
        form={receiptForm}
        className="receipt-query-form"
        onFinish={receiptSearch}
      >
        {tab === "official" ? (
          <div className="receipt-filter-grid official">
            <Form.Item label="案件编号" name="case_no">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="文件名称" name="file_name">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="导入状态" name="import_status">
              <Select
                allowClear
                placeholder="请选择"
                options={["未导入", "已导入"].map((value) => ({
                  value,
                  label: value,
                }))}
              />
            </Form.Item>
            <Form.Item label="业务处理状态" name="business_process_status">
              <Select
                allowClear
                placeholder="请选择"
                options={["未处理", "已处理"].map((value) => ({
                  value,
                  label: value,
                }))}
              />
            </Form.Item>
            <Form.Item label="上传日期" name="upload_range">
              <DatePicker.RangePicker />
            </Form.Item>
          </div>
        ) : (
          <div className="receipt-filter-grid">
            <Form.Item label="案件编号" name="case_no">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="法院案号" name="court_no">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="法院名称" name="court_name">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="收文日期" name="receipt_range">
              <DatePicker.RangePicker />
            </Form.Item>
            <Form.Item label="原告" name="plaintiff">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="被告" name="defendant">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="开庭律师" name="hearing_lawyer">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="上传日期" name="upload_range">
              <DatePicker.RangePicker />
            </Form.Item>
            <Form.Item label="客户管理人" name="case_manager">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="经办律师" name="handling_lawyer">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="律师助理" name="assistant">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="文件名称" name="document_name">
              <Input allowClear />
            </Form.Item>
          </div>
        )}
        <div className="receipt-query-actions">
          <Button type="primary" htmlType="submit" icon={<SearchOutlined />}>
            查询
          </Button>
          {tab === "official" && (
            <Button icon={<UploadOutlined />} onClick={() => openUpload(undefined, "收文附件")}>
              上传
            </Button>
          )}
        </div>
      </Form>
      <Table
        rowKey="id"
        loading={loading}
        size="small"
        className="receipt-table"
        rowSelection={{
          selectedRowKeys: selectedReceiptKeys,
          onChange: (keys) => setSelectedReceiptKeys(keys),
        }}
        columns={tab === "official" ? officialColumns : receivedColumns}
        dataSource={searchedReceipts}
        scroll={{ x: tab === "official" ? 1450 : 1800 }}
        pagination={{
          pageSize: 15,
          showTotal: (total) => `共 ${total} 条记录`,
          showSizeChanger: false,
        }}
      />
      <div className="receipt-footer-actions">
        {tab === "official" ? (
          <>
            <Popconfirm
              title="确定删除选中的收文记录？"
              description={
                selectedFormalReceipts.length
                  ? `将永久删除 ${selectedFormalReceipts.length} 条正式记录及其附件。`
                  : "请先选择需要删除的正式收文记录。"
              }
              onConfirm={deleteSelectedReceipts}
            >
              <Button
                danger
                size="small"
                icon={<DeleteOutlined />}
                disabled={!selectedReceiptKeys.length}
              >
                删除
              </Button>
            </Popconfirm>
            <Button
              size="small"
              icon={<EditOutlined />}
              disabled={!selectedReceiptKeys.length}
              onClick={openReceiptDateEditor}
            >
              修改收文日期
            </Button>
            <Button
              size="small"
              disabled={!selectedFormalReceipts.length}
              onClick={() => void updateOfficialProcessStatus(true)}
            >
              标记已处理
            </Button>
            <Button
              size="small"
              disabled={!selectedFormalReceipts.length}
              onClick={() => void updateOfficialProcessStatus(false)}
            >
              标记未处理
            </Button>
            <Button
              size="small"
              icon={<DownloadOutlined />}
              disabled={!searchedReceipts.length}
              onClick={exportOfficialReceipts}
            >
              {selectedFormalReceipts.length ? "导出选中" : "导出查询结果"}
            </Button>
          </>
        ) : (<>
          <Button size="small" icon={<EditOutlined />} disabled={!selectedReceiptKeys.length} onClick={openReceiptDateEditor}>修改收文日期</Button>
          <Dropdown menu={{ items: receiptMoreActionItems, onClick: ({ key }) => handleReceiptMoreAction(key) }}><Button size="small" disabled={selectedReceiptKeys.length !== 1}>更多操作</Button></Dropdown>
        </>)}
      </div>
    </Card>
  ) : null;
  return (
    <>
      {isReceiptView ? (
        receiptPanel
      ) : (
        <>
          <div className="document-stats">
            <Card>
              <Statistic title="收发文" value={summary.documents} />
            </Card>
            <Card>
              <Statistic
                title="待签收"
                value={summary.pending_receipt}
                styles={{ content: { color: "#f39c12" } }}
              />
            </Card>
            <Card>
              <Statistic
                title="已签收"
                value={summary.received}
                styles={{ content: { color: "#3c8dbc" } }}
              />
            </Card>
            <Card>
              <Statistic title="文件附件" value={summary.attachments} />
            </Card>
            <Card>
              <Statistic
                title="归档材料"
                value={summary.archive_materials}
                styles={{ content: { color: "#00a65a" } }}
              />
            </Card>
            <Card>
              <Statistic title="文书模板" value={summary.templates} />
            </Card>
          </div>
          <Card
            className="panel"
            title="收发文台"
            extra={
              <Space>
                {tab === "documents" && (
                  <RecordImportButton module="document" onImported={load} />
                )}
                <Button icon={<ReloadOutlined />} onClick={() => void load()}>
                  刷新
                </Button>
                {tab === "outgoing" && (
                  <><Popconfirm title="确认将所选审批通过的正式发文标记为已盖章？" onConfirm={markOfficialOutgoingStamped}><Button disabled={!outgoingSelected.length}>标记已盖章</Button></Popconfirm><Button onClick={downloadOfficialOutgoing}>打包下载</Button><Button type="primary" icon={<PlusOutlined />} onClick={() => { outgoingForm.resetFields(); outgoingForm.setFieldsValue({ source_type: "contract", need_audit: true, is_offline_print: true, print_quantity: 1 }); setOutgoingOpen(true); }}>新建正式发文</Button></>
                )}
                {tab === "documents" && (
                  <Button
                    type="primary"
                    icon={<FileAddOutlined />}
                    onClick={() => {
                      documentForm.setFieldsValue({
                        direction: "收文",
                        owner: profile.username || "admin",
                        document_date: dayjs(),
                      });
                      setDocumentOpen(true);
                    }}
                  >
                    登记收发文
                  </Button>
                )}
                {tab === "files" && (
                  <Button
                    type="primary"
                    icon={<UploadOutlined />}
                    onClick={() => openUpload()}
                  >
                    上传文件
                  </Button>
                )}
                {tab === "templates" && (
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={() => {
                      setEditingTemplate(null);
                      templateForm.resetFields();
                      templateForm.setFieldsValue({
                        version: "1.0",
                        category: "诉讼文书",
                      });
                      setTemplateOpen(true);
                    }}
                  >
                    新增模板
                  </Button>
                )}
              </Space>
            }
          >
            <Tabs
              activeKey={tab}
              onChange={setTab}
              items={[
                { key: "documents", label: "收发文登记" },
                { key: "outgoing", label: "正式发文" },
                { key: "files", label: "文件附件" },
                { key: "templates", label: "文书模板" },
                { key: "archive", label: "案件归档材料" },
              ]}
            />
            {tab === "outgoing" && <Form form={outgoingQueryForm} layout="inline" onFinish={searchOfficialOutgoing} style={{ padding: "0 0 12px", rowGap: 8 }}>
              <Form.Item label="申请编号" name="official_no"><Input allowClear placeholder="正式发文编号" style={{ width: 176 }} /></Form.Item>
              <Form.Item label="申请人" name="owner"><Input allowClear placeholder="申请人" style={{ width: 120 }} /></Form.Item>
              <Form.Item label="申请日期" name="application_dates"><DatePicker.RangePicker allowClear style={{ width: 230 }} /></Form.Item>
              <Form.Item label="案件编号" name="case_no"><Input allowClear placeholder="案件编号" style={{ width: 160 }} /></Form.Item>
              <Form.Item label="合同编号" name="contract_no"><Input allowClear placeholder="合同编号" style={{ width: 160 }} /></Form.Item>
              <Form.Item label="客户名称" name="customer"><Input allowClear placeholder="客户名称" style={{ width: 150 }} /></Form.Item>
              <Form.Item label="用印状态" name="status_value"><Select allowClear placeholder="全部" style={{ width: 120 }} options={["草稿", "待审批", "已通过", "已拒绝", "已撤回", "已盖章"].map((value) => ({ value, label: value }))} /></Form.Item>
              <Form.Item label="印章类型" name="seal_type"><Input allowClear placeholder="印章类型" style={{ width: 140 }} /></Form.Item>
              <Form.Item label="文件名称" name="file_name"><Input allowClear placeholder="文件名称" style={{ width: 160 }} /></Form.Item>
              <Form.Item><Space><Button type="primary" htmlType="submit" icon={<SearchOutlined />}>查询</Button><Button onClick={() => void resetOfficialOutgoingSearch()}>重置</Button></Space></Form.Item>
            </Form>}
            {tab === "documents" ? (
              <Table
                rowKey="id"
                loading={loading}
                size="small"
                columns={documentColumns}
                dataSource={documents}
                scroll={{ x: 1700 }}
                pagination={{
                  pageSize: 15,
                  showTotal: (total) => `共 ${total} 条记录`,
                  showSizeChanger: true,
                }}
              />
            ) : tab === "outgoing" ? (
              <Table
                rowKey="id"
                loading={loading}
                size="small"
                rowSelection={{ selectedRowKeys: outgoingSelected, onChange: setOutgoingSelected, getCheckboxProps: (row: RecordRow) => ({ disabled: !["已通过", "已盖章"].includes(row.status) }) }}
                locale={{ emptyText: "暂无正式发文；请从合同或案件发起" }}
                columns={[
                  { title: "正式发文编号", dataIndex: "official_no", width: 190, render: (_: unknown, row: RecordRow) => <Button type="link" className="case-cell-link" onClick={() => openOfficialOutgoingDetail(row)}>{(row as any).official_no || row.serial_no}</Button> },
                  { title: "文书名称", dataIndex: "title", width: 240, ellipsis: true },
                  { title: "来源", width: 180, render: (_, row: any) => row.source_serial_no ? <Button type="link" className="case-cell-link" onClick={() => openOfficialOutgoingSource(row)}>{`${row.source_type === "contract" ? "合同" : "案件"}：${row.source_serial_no}`}</Button> : "—" },
                  { title: "客户", dataIndex: "customer", width: 180, ellipsis: true, render: (value: string) => value ? <Button type="link" className="case-cell-link" onClick={() => void openCustomerDetail(value)}>{value}</Button> : "—" },
                  { title: "印章类型", dataIndex: "seal_type", width: 130, render: (value: string) => value || "—" },
                  { title: "用印类型", key: "official_document_type", width: 90, render: (_, row: any) => row.source_type === "case" ? "案件" : row.source_type === "contract" ? "合同" : "—" },
                  { title: "文件数", key: "file_count", width: 80, render: (_: unknown, row: RecordRow) => <Button type="link" className="case-cell-link" onClick={() => openOfficialOutgoingDetail(row)}>{(row as any).attachments?.length || 0}</Button> },
                  { title: "状态", dataIndex: "status", width: 110, render: (value: string) => <Tag color={value === "已通过" ? "green" : value === "已拒绝" ? "red" : value === "待审批" ? "orange" : "default"}>{value}</Tag> },
                  { title: "申请人", dataIndex: "owner_display_name", width: 120, render: personDisplayName },
                  { title: "申请时间", dataIndex: "created_at", width: 175, sorter: (a: any, b: any) => String(a.created_at || "").localeCompare(String(b.created_at || "")), render: (value: string) => value ? dayjs(value).format("YYYY-MM-DD HH:mm") : "—" },
                  { title: "审核人", dataIndex: "auditor_display_name", width: 120, render: personDisplayName },
                  { title: "审核时间", dataIndex: "audit_time", width: 175, sorter: (a: any, b: any) => String(a.audit_time || "").localeCompare(String(b.audit_time || "")), render: (value: string) => value ? dayjs(value).format("YYYY-MM-DD HH:mm") : "—" },
                  { title: "审核意见", dataIndex: "audit_remark", width: 220, ellipsis: true, render: (value: string) => value || "—" },
                  { title: "操作", fixed: "right", width: 290, render: (_, row: RecordRow) => <Space size={2}><Button type="link" size="small" onClick={() => openOfficialOutgoingDetail(row)}>详情</Button>{["草稿", "已拒绝", "已撤回"].includes(row.status) && <Button type="link" size="small" onClick={() => openOfficialOutgoingEditor(row)}>编辑</Button>}{["草稿", "已拒绝", "已撤回"].includes(row.status) && <Button type="link" size="small" onClick={() => submitOfficialOutgoing(row)}>提交</Button>}{row.status === "待审批" && <><Button type="link" size="small" onClick={() => { outgoingReviewForm.setFieldsValue({ comment: "" }); setOutgoingReview({ row, approved: true }); }}>通过</Button><Button danger type="link" size="small" onClick={() => { outgoingReviewForm.setFieldsValue({ comment: "" }); setOutgoingReview({ row, approved: false }); }}>拒绝</Button></>}{["待审批", "已拒绝"].includes(row.status) && <Popconfirm title="确认撤回正式发文？" onConfirm={() => rollbackOfficialOutgoing(row)}><Button type="link" size="small">撤回</Button></Popconfirm>}</Space> },
                ]}
                dataSource={outgoingDocuments}
                pagination={{
                  pageSize: 15,
                  showTotal: (total) => `共 ${total} 条记录`,
                  showSizeChanger: true,
                }}
                scroll={{ x: 1920 }}
              />
            ) : tab === "files" ? (
              <Table
                rowKey="id"
                loading={loading}
                size="small"
                columns={fileColumns}
                dataSource={attachments}
                pagination={{
                  pageSize: 15,
                  showTotal: (total) => `共 ${total} 条记录`,
                  showSizeChanger: true,
                }}
                scroll={{ x: 1450 }}
              />
            ) : tab === "templates" ? (
              <Table
                rowKey="id"
                loading={loading}
                size="small"
                columns={templateColumns}
                dataSource={templates}
                pagination={{
                  pageSize: 15,
                  showTotal: (total) => `共 ${total} 条记录`,
                  showSizeChanger: true,
                }}
                scroll={{ x: 1200 }}
              />
            ) : (
              <Table
                rowKey="id"
                loading={loading}
                size="small"
                columns={archiveColumns}
                dataSource={archiveRows}
                pagination={{
                  pageSize: 15,
                  showTotal: (total) => `共 ${total} 条记录`,
                  showSizeChanger: true,
                }}
                scroll={{ x: 1300 }}
              />
            )}
          </Card>
        </>
      )}
      <Drawer open={!!outgoingDetail} title={outgoingDetail ? `\u6b63\u5f0f\u53d1\u6587\u8be6\u60c5\uff1a${outgoingDetail.official_no || outgoingDetail.serial_no}` : "\u6b63\u5f0f\u53d1\u6587\u8be6\u60c5"} width={760} onClose={() => setOutgoingDetail(null)}>
        {outgoingDetail && <><Descriptions bordered size="small" column={2} items={[
          { key: "title", label: "\u6587\u4e66\u540d\u79f0", children: outgoingDetail.title }, { key: "status", label: "\u72b6\u6001", children: outgoingDetail.status },
          { key: "source", label: "\u6765\u6e90\u4e1a\u52a1", children: outgoingDetail.source_serial_no ? <Button type="link" className="case-cell-link" onClick={() => openOfficialOutgoingSource(outgoingDetail)}>{`${outgoingDetail.source_type === "contract" ? "\u5408\u540c" : "\u6848\u4ef6"}\uff5c${outgoingDetail.source_serial_no}`}</Button> : "\u2014" }, { key: "seal", label: "\u5370\u7ae0\u7c7b\u578b", children: outgoingDetail.seal_type || "\u2014" },
          { key: "copies", label: "\u76d6\u7ae0\u4efd\u6570", children: outgoingDetail.print_quantity || 1 }, { key: "electronic", label: "\u7535\u5b50\u5370\u7ae0", children: outgoingDetail.is_electronic_seal ? "\u662f" : "\u5426" }, { key: "offline", label: "\u6253\u5370\u76d6\u7ae0", children: outgoingDetail.is_offline_print ? "\u9700\u8981" : "\u4e0d\u9700\u8981" }, { key: "customer", label: "\u5ba2\u6237\u540d\u79f0", children: outgoingDetail.customer || "\u2014" }, { key: "applied", label: "\u7533\u8bf7\u65f6\u95f4", children: outgoingDetail.created_at ? dayjs(outgoingDetail.created_at).format("YYYY-MM-DD HH:mm") : "\u2014" },
          { key: "content", label: "\u6587\u4e66\u5185\u5bb9", children: outgoingDetail.content || "\u2014", span: 2 }, { key: "remark", label: "\u5907\u6ce8", children: outgoingDetail.description || "\u2014", span: 2 },
        ]} />
        <Card size="small" title={"\u6b63\u5f0f\u53d1\u6587\u9644\u4ef6"} style={{ marginTop: 16 }} extra={["\u8349\u7a3f", "\u5df2\u62d2\u7edd", "\u5df2\u64a4\u56de"].includes(outgoingDetail.status) ? <Upload key="upload" showUploadList={false} beforeUpload={(item) => { void uploadOfficialOutgoingFile(outgoingDetail, item as unknown as File); return false; }}><Button icon={<UploadOutlined />}>{"\u4e0a\u4f20\u9644\u4ef6"}</Button></Upload> : null}>
          <Table size="small" rowKey="id" pagination={false} dataSource={outgoingDetail.attachments || []} columns={[
            { title: "\u6587\u4ef6\u540d\u79f0", dataIndex: "original_name", ellipsis: true }, { title: "\u7c7b\u522b", dataIndex: "category", width: 150 }, { title: "\u5927\u5c0f", dataIndex: "size", width: 100, render: (value: number) => fileSize(value) },
            { title: "\u4e0a\u4f20\u4eba", dataIndex: "uploader_display_name", width: 90, render: personDisplayName }, { title: "\u4e0a\u4f20\u65f6\u95f4", dataIndex: "created_at", width: 150, render: (value: string) => value ? new Date(value).toLocaleString() : "\u2014" }, { title: "\u64cd\u4f5c", width: 180, render: (_, item: Attachment) => <Space size={2}><Button type="link" size="small" onClick={() => void previewAttachment(item)}>{"\u67e5\u770b"}</Button><Button type="link" size="small" onClick={() => window.open(`/api/v1/attachments/${item.id}/download`, "_blank")}>{"\u4e0b\u8f7d"}</Button>{["\u8349\u7a3f", "\u5df2\u62d2\u7edd", "\u5df2\u64a4\u56de"].includes(outgoingDetail.status) && item.category === "正式发文附件" && <Popconfirm title="确认删除该正式发文附件？" onConfirm={() => deleteOfficialOutgoingFile(outgoingDetail, item)}><Button danger type="link" size="small">删除</Button></Popconfirm>}</Space> },
          ]} />
        </Card>
        {outgoingDetail.status === "\u5df2\u901a\u8fc7" && <Card size="small" title={"\u76d6\u7ae0\u6587\u4ef6"} style={{ marginTop: 16 }}><Upload showUploadList={false} beforeUpload={(item) => { void uploadOfficialOutgoingFile(outgoingDetail, item as unknown as File, true); return false; }}><Button type="primary" icon={<UploadOutlined />}>{"\u4e0a\u4f20\u76d6\u7ae0\u6587\u4ef6\u5e76\u6807\u8bb0\u5df2\u76d6\u7ae0"}</Button></Upload></Card>}
        {["\u8349\u7a3f", "\u5df2\u62d2\u7edd", "\u5df2\u64a4\u56de"].includes(outgoingDetail.status) && <Button style={{ marginTop: 16 }} type="primary" onClick={() => submitOfficialOutgoing(outgoingDetail)}>{"\u63d0\u4ea4\u5ba1\u6279"}</Button>}
        <Card size="small" title="审批与办理记录" style={{ marginTop: 16 }}>
          <Timeline items={outgoingHistory.map((item) => ({ color: item.to_status === "已通过" || item.to_status === "已盖章" ? "green" : item.to_status === "已拒绝" ? "red" : "blue", children: <div><b>{item.action}</b>{item.from_status && <span>　{item.from_status} → {item.to_status}</span>}<div style={{ color: "#999", fontSize: 12 }}>{personDisplayName(item.operator_display_name)} · {new Date(item.created_at).toLocaleString("zh-CN")}</div>{item.comment && <div>{item.comment}</div>}</div> }))} />
        </Card>
        </>}
      </Drawer>
      <Modal
        open={!!outgoingReview}
        title={outgoingReview?.approved ? "通过正式发文" : "拒绝正式发文"}
        okText={outgoingReview?.approved ? "确认通过" : "确认拒绝"}
        okButtonProps={{ danger: !outgoingReview?.approved }}
        cancelText="取消"
        onOk={async () => {
          const values = await outgoingReviewForm.validateFields();
          if (outgoingReview) await reviewOfficialOutgoing(outgoingReview.row, outgoingReview.approved, values.comment || "");
        }}
        onCancel={() => { setOutgoingReview(null); outgoingReviewForm.resetFields(); }}
        destroyOnHidden
      >
        {outgoingReview && <>
          <Alert
            type={outgoingReview.approved ? "info" : "warning"}
            showIcon
            message={`${(outgoingReview.row as any).official_no || outgoingReview.row.serial_no}｜${outgoingReview.row.title}`}
            description={outgoingReview.approved ? "请填写本次审核意见；该意见将同步写入正式发文审批记录。" : "请填写具体驳回原因；申请人可在修改后再次提交。"}
            style={{ marginBottom: 16 }}
          />
          <Form form={outgoingReviewForm} layout="vertical">
            <Form.Item label="审核意见" name="comment" rules={outgoingReview.approved ? [{ max: 1000 }] : [{ required: true, whitespace: true, message: "请填写驳回原因" }, { max: 1000 }]}>
              <Input.TextArea rows={4} maxLength={1000} showCount placeholder={outgoingReview.approved ? "例如：材料齐全，同意正式发文" : "请说明需补正或修改的具体事项"} />
            </Form.Item>
          </Form>
        </>}
      </Modal>
      <Modal open={outgoingOpen} title={editingOutgoing ? "编辑正式发文" : "新建正式发文"} okText={editingOutgoing ? "保存修改" : "创建草稿"} cancelText="取消" onOk={editingOutgoing ? updateOfficialOutgoing : createOfficialOutgoing} onCancel={() => { setOutgoingOpen(false); setEditingOutgoing(null); outgoingForm.resetFields(); }} destroyOnHidden>
        <Form form={outgoingForm} layout="vertical">
          <Form.Item label="文书名称" name="title" rules={[{ required: true, message: "请输入文书名称" }]}><Input /></Form.Item>
          <Form.Item label="来源类型" name="source_type" rules={[{ required: true }]}><Select disabled={!!editingOutgoing} options={[{ value: "contract", label: "合同" }, { value: "case", label: "案件" }]} onChange={() => outgoingForm.setFieldsValue({ source_record_id: undefined, source_file_ids: [] })} /></Form.Item>
          <Form.Item noStyle shouldUpdate={(previous, current) => previous.source_type !== current.source_type}>{() => <Form.Item label="来源业务" name="source_record_id" rules={[{ required: true, message: "请选择来源合同或案件" }]}><Select disabled={!!editingOutgoing} showSearch optionFilterProp="label" options={(outgoingForm.getFieldValue("source_type") === "case" ? cases : contracts).map((item) => ({ value: item.id, label: `${item.serial_no}｜${item.title}` }))} onChange={() => outgoingForm.setFieldValue("source_file_ids", [])} /></Form.Item>}</Form.Item>
          <Form.Item noStyle shouldUpdate={(previous, current) => previous.source_record_id !== current.source_record_id || previous.source_type !== current.source_type}>{() => {
            const sourceId = Number(outgoingForm.getFieldValue("source_record_id") || 0);
            const sourceFiles = attachments.filter((item) => item.record_id === sourceId);
            return <Form.Item label="随文附件" name="source_file_ids" extra={editingOutgoing ? "编辑不改变既有来源和已复制附件；请在详情中维护正式发文附件。" : outgoingForm.getFieldValue("source_type") === "contract" ? "未选择时将按旧系统规则带入该合同全部附件。" : "案件发文仅带入本处选中的附件。"}><Select mode="multiple" allowClear placeholder={sourceId ? "选择需要带入正式发文的附件" : "请先选择来源业务"} disabled={!!editingOutgoing || !sourceId} options={sourceFiles.map((item) => ({ value: item.id, label: `${item.original_name}（${fileSize(item.size)}）` }))} notFoundContent={sourceId ? "该来源暂无可带入附件" : undefined} /></Form.Item>;
          }}</Form.Item>
          <Form.Item label="印章类型" name="seal_asset_id" rules={[{ required: true, message: "请选择可用印章类型" }]}><Select placeholder="请选择可用印章" options={sealAssets.filter((item) => item.status === "可用").map((item) => ({ value: item.id, label: `${item.seal_type}｜${item.name}` }))} onChange={(value) => outgoingForm.setFieldsValue({ seal_asset_id: value })} onSelect={(value) => outgoingForm.setFieldsValue({ seal_asset_id: value })} /></Form.Item>
          <Form.Item label="盖章份数" name="print_quantity" rules={[{ required: true }]}><InputNumber min={1} max={9999} precision={0} style={{ width: "100%" }} /></Form.Item>
          <Form.Item name="is_electronic_seal" valuePropName="checked"><Checkbox>使用电子印章</Checkbox></Form.Item>
          <Form.Item name="is_offline_print" valuePropName="checked"><Checkbox>需要打印盖章</Checkbox></Form.Item>
          <Form.Item name="need_audit" valuePropName="checked"><Checkbox>提交后进入正式发文审批</Checkbox></Form.Item>
          <Form.Item label="文书内容" name="content"><Input.TextArea rows={4} /></Form.Item>
          <Form.Item label="备注" name="remark"><Input.TextArea rows={2} /></Form.Item>
        </Form>
        <Alert type="info" showIcon message="先创建草稿；可上传/删除正式发文附件后再提交审批。来源合同或案件、附件和印章均由服务端校验。" />
      </Modal>
      <Modal
        open={receiptDateOpen}
        title={`修改收文日期（已选 ${selectedFormalReceipts.length} 条）`}
        okText="保存"
        cancelText="取消"
        onOk={saveReceiptDate}
        onCancel={() => setReceiptDateOpen(false)}
        destroyOnHidden
      >
        <Alert
          type="info"
          showIcon
          title="修改后会同步更新正式收文记录，并写入操作日志。"
          style={{ marginBottom: 16 }}
        />
        <DatePicker
          value={receiptDate}
          onChange={setReceiptDate}
          format="YYYY-MM-DD"
          style={{ width: "100%" }}
        />
      </Modal>
      <Modal
        open={documentOpen}
        title="登记收发文"
        okText="保存草稿"
        cancelText="取消"
        onOk={createDocument}
        onCancel={() => setDocumentOpen(false)}
      >
        <Form form={documentForm} layout="vertical">
          <Alert
            type="info"
            showIcon
            title="保存后先进入待登记；核对资料并上传附件后点击“完成登记”。"
            style={{ marginBottom: 16 }}
          />
          <Form.Item label="文件名称" name="title" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <div className="form-grid">
            <Form.Item
              label="收发类型"
              name="direction"
              rules={[{ required: true }]}
            >
              <Select
                options={["收文", "发文"].map((v) => ({ value: v, label: v }))}
              />
            </Form.Item>
            <Form.Item
              label="文件日期"
              name="document_date"
              rules={[{ required: true }]}
            >
              <DatePicker style={{ width: "100%" }} format="YYYY-MM-DD" />
            </Form.Item>
            <Form.Item label="负责人" name="owner">
              <Input />
            </Form.Item>
            <Form.Item label="客户" name="customer">
              <Input />
            </Form.Item>
            <Form.Item label="关联案号" name="case_no">
              <Select
                allowClear
                showSearch
                options={cases.map((c) => ({
                  value: c.serial_no,
                  label: `${c.serial_no}｜${c.title}`,
                }))}
              />
            </Form.Item>
            <Form.Item label="来文/送达单位" name="sender">
              <Input />
            </Form.Item>
          </div>
          <Form.Item label="备注" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={uploadOpen}
        title={`上传文件${uploadTarget ? `：${uploadTarget.serial_no}` : ""}`}
        okText="开始上传"
        cancelText="取消"
        onOk={upload}
        onCancel={() => setUploadOpen(false)}
      >
        <Form form={uploadForm} layout="vertical">
          <Form.Item label={tab === "official" ? "关联案件" : "关联业务"} name="record_id">
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              options={(tab === "official" ? cases : [...cases, ...documents]).map((r) => ({
                value: r.id,
                label: `${r.serial_no}｜${r.title}`,
              }))}
            />
          </Form.Item>
          {tab === "official" && (
            <Form.Item
              label="文件日期"
              name="document_date"
              rules={[{ required: true, message: "请选择文件日期" }]}
            >
              <DatePicker style={{ width: "100%" }} format="YYYY-MM-DD" />
            </Form.Item>
          )}
          <Form.Item
            label="材料分类"
            name="category"
            rules={[{ required: true }]}
          >
            <Select
              options={allCategories.map((v) => ({ value: v, label: v }))}
            />
          </Form.Item>
          <Form.Item label="选择文件" required>
            <Upload
              beforeUpload={(f) => {
                setFile(f);
                return false;
              }}
              maxCount={1}
              onRemove={() => setFile(null)}
            >
              <Button icon={<UploadOutlined />}>选择文件（最大 20MB）</Button>
            </Upload>
          </Form.Item>
          <Form.Item label="备注" name="remark">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={templateOpen}
        title={editingTemplate ? "编辑文书模板" : "新增文书模板"}
        okText="保存模板"
        cancelText="取消"
        onOk={saveTemplate}
        onCancel={() => {
          setTemplateOpen(false);
          setEditingTemplate(null);
        }}
      >
        <Form form={templateForm} layout="vertical">
          <Form.Item label="模板名称" name="name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <div className="form-grid">
            <Form.Item
              label="模板分类"
              name="category"
              rules={[{ required: true }]}
            >
              <Select
                options={[
                  "诉讼文书",
                  "非诉文书",
                  "合同文书",
                  "归档文书",
                  "内部表单",
                ].map((v) => ({ value: v, label: v }))}
              />
            </Form.Item>
            <Form.Item label="版本" name="version">
              <Input />
            </Form.Item>
          </div>
          <Form.Item label="模板字段" name="fields">
            <Select
              mode="tags"
              tokenSeparators={[",", "，"]}
              placeholder="输入字段名后回车"
            />
          </Form.Item>
          <Form.Item label="模板说明" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(actionStatus)}
        title={
          actionStatus === "待签收"
            ? "完成收发文登记"
            : actionStatus === "已签收"
              ? viewing?.data.direction === "发文"
                ? "确认文件送达"
                : "确认文件签收"
              : "文档归档"
        }
        okText="确认提交"
        cancelText="取消"
        onOk={submitAction}
        onCancel={() => setActionStatus("")}
        destroyOnHidden
      >
        <Form form={actionForm} layout="vertical">
          <Alert
            type="info"
            showIcon
            title={
              actionStatus === "待签收"
                ? "登记完成后进入待签收，后续不能直接修改流程状态。"
                : actionStatus === "已签收"
                  ? "请登记实际签收/送达人和日期，完成后可进入归档。"
                  : "归档编号用于纸质及电子档案定位，归档后流程办结。"
            }
            style={{ marginBottom: 16 }}
          />
          <Form.Item
            label="办理日期"
            name="action_date"
            rules={[{ required: true }]}
          >
            <DatePicker style={{ width: "100%" }} format="YYYY-MM-DD" />
          </Form.Item>
          {actionStatus === "已签收" && (
            <Form.Item
              label={
                viewing?.data.direction === "发文" ? "送达确认人" : "签收人"
              }
              name="handler"
              rules={[{ required: true, message: "请填写人员" }]}
            >
              <Input />
            </Form.Item>
          )}
          {actionStatus === "已归档" && (
            <>
              <Form.Item
                label="归档编号"
                name="archive_no"
                rules={[{ required: true, message: "请填写归档编号" }]}
              >
                <Input />
              </Form.Item>
              <Form.Item label="存放位置" name="archive_location">
                <Input placeholder="例如：上海档案室 A-03-12" />
              </Form.Item>
            </>
          )}
          <Form.Item label="办理说明" name="comment">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Drawer
        size={720}
        open={Boolean(viewing) && !actionStatus}
        title={`收发文详情：${viewing?.serial_no || ""}`}
        onClose={() => setViewing(null)}
        extra={viewing && documentAction(viewing)}
      >
        {viewing && (
          <>
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="文件名称" span={2}>
                {viewing.title}
              </Descriptions.Item>
              <Descriptions.Item label="收发类型">
                <Tag
                  color={viewing.data.direction === "发文" ? "blue" : "green"}
                >
                  {viewing.data.direction}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={viewing.status === "已归档" ? "green" : "blue"}>
                  {viewing.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="客户/主体" span={2}>
                {viewing.customer ? <Button type="link" onClick={() => void openCustomerDetail(viewing.customer)}>{viewing.customer}</Button> : "—"}
              </Descriptions.Item>
              <Descriptions.Item label="关联案号">
                {viewing.data.case_no ? <Button type="link" onClick={() => openCaseDetail(viewing.data.case_no)}>{viewing.data.case_no}</Button> : "—"}
              </Descriptions.Item>
              <Descriptions.Item label="来文/送达单位">
                {viewing.data.sender || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="负责人">
                {personDisplayName(viewing.owner_display_name)}
              </Descriptions.Item>
              <Descriptions.Item label="登记日期">
                {viewing.data.registered_at || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="签收/送达日期">
                {viewing.data.signed_at || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="签收/确认人">
                {personDisplayName(viewing.data.signer_display_name)}
              </Descriptions.Item>
              <Descriptions.Item label="归档编号">
                {viewing.data.archive_no || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="存放位置">
                {viewing.data.archive_location || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="备注" span={2}>
                {viewing.description || "—"}
              </Descriptions.Item>
            </Descriptions>
            <Card
              size="small"
              title={`关联附件（${attachments.filter((a) => a.record_id === viewing.id).length}）`}
              style={{ marginTop: 16 }}
              extra={
                <Button
                  type="link"
                  icon={<UploadOutlined />}
                  onClick={() =>
                    openUpload(
                      viewing,
                      viewing.data.direction === "发文"
                        ? "发文附件"
                        : "收文附件",
                    )
                  }
                >
                  上传附件
                </Button>
              }
            >
              <Table
                rowKey="id"
                size="small"
                pagination={false}
                dataSource={attachments.filter(
                  (a) => a.record_id === viewing.id,
                )}
                columns={[
                  {
                    title: "文件名",
                    dataIndex: "original_name",
                    ellipsis: true,
                  },
                  { title: "分类", dataIndex: "category", width: 100 },
                  { title: "上传人", dataIndex: "uploader_display_name", width: 80, render: personDisplayName },
                  {
                    title: "操作",
                    width: 100,
                    render: (_: unknown, r: Attachment) => (
                      <Space size={0}>
                        <Button type="link" onClick={() => void previewAttachment(r)}>
                          查看
                        </Button>
                        <Button type="link" onClick={() => download(r)}>
                          下载
                        </Button>
                      </Space>
                    ),
                  },
                ]}
              />
            </Card>
            <Card size="small" title="办理记录" style={{ marginTop: 16 }}>
              <Timeline
                items={history.map((x) => ({
                  color: x.to_status === "已归档" ? "green" : "blue",
                  children: (
                    <div>
                      <b>{x.action}</b>
                      {x.from_status && (
                        <span>
                          　{x.from_status} → {x.to_status}
                        </span>
                      )}
                      <div style={{ color: "#999", fontSize: 12 }}>
                        {personDisplayName(x.operator_display_name)} ·{" "}
                        {new Date(x.created_at).toLocaleString("zh-CN")}
                      </div>
                      {x.comment && <div>{x.comment}</div>}
                    </div>
                  ),
                }))}
              />
            </Card>
          </>
        )}
      </Drawer>
      <Drawer
        size={560}
        open={Boolean(attachmentDetail)}
        title={`附件详情：${attachmentDetail?.original_name || ""}`}
        onClose={() => setAttachmentDetail(null)}
        extra={attachmentDetail && <Button type="primary" icon={<DownloadOutlined />} onClick={() => download(attachmentDetail)}>下载附件</Button>}
      >
        {attachmentDetail && <Descriptions bordered size="small" column={1}>
          <Descriptions.Item label="文件名称">{attachmentDetail.original_name}</Descriptions.Item>
          <Descriptions.Item label="分类">{attachmentDetail.category || "—"}</Descriptions.Item>
          <Descriptions.Item label="关联编号">{attachmentDetail.record_no || "公共文件"}</Descriptions.Item>
          <Descriptions.Item label="关联业务">{attachmentDetail.record_id ? <Button type="link" onClick={() => void openAttachmentRecord(attachmentDetail)}>{attachmentDetail.record_title || attachmentDetail.record_no || "查看关联业务"}</Button> : "公共文件"}</Descriptions.Item>
          <Descriptions.Item label="大小">{fileSize(attachmentDetail.size)}</Descriptions.Item>
          <Descriptions.Item label="上传人">{personDisplayName(attachmentDetail.uploader_display_name)}</Descriptions.Item>
          <Descriptions.Item label="上传时间">{attachmentDetail.created_at ? new Date(attachmentDetail.created_at).toLocaleString() : "—"}</Descriptions.Item>
          <Descriptions.Item label="备注">{attachmentDetail.remark || "—"}</Descriptions.Item>
        </Descriptions>}
      </Drawer>
      <Drawer
        size={560}
        open={Boolean(templateDetail)}
        title={`模板详情：${templateDetail?.name || ""}`}
        onClose={() => setTemplateDetail(null)}
      >
        {templateDetail && <Descriptions bordered size="small" column={1}>
          <Descriptions.Item label="模板名称">{templateDetail.name}</Descriptions.Item>
          <Descriptions.Item label="分类">{templateDetail.category || "—"}</Descriptions.Item>
          <Descriptions.Item label="版本">{templateDetail.version || "—"}</Descriptions.Item>
          <Descriptions.Item label="状态"><Tag color={templateDetail.is_active ? "green" : "default"}>{templateDetail.is_active ? "启用" : "停用"}</Tag></Descriptions.Item>
          <Descriptions.Item label="模板字段"><Space wrap>{(templateDetail.fields || []).map((field) => <Tag key={field}>{field}</Tag>) || "—"}</Space></Descriptions.Item>
          <Descriptions.Item label="说明">{templateDetail.description || "—"}</Descriptions.Item>
        </Descriptions>}
      </Drawer>
      <Modal
        open={previewOpen}
        title={`文件预览：${previewName}`}
        footer={null}
        width={760}
        onCancel={() => {
          setPreviewOpen(false);
          setPreviewUrl("");
        }}
        destroyOnHidden
      >
        {previewKind === "image" ? (
          <img src={previewUrl} alt={previewName} style={{ maxWidth: "100%" }} />
        ) : previewKind === "pdf" ? (
          <iframe
            src={previewUrl}
            title={previewName}
            style={{ width: "100%", height: 520 }}
          />
        ) : (
          <pre style={{ whiteSpace: "pre-wrap", maxHeight: 520, overflow: "auto" }}>
            {previewText}
          </pre>
        )}
      </Modal>
    </>
  );
}
