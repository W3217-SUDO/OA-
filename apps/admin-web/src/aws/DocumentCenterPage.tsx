import { useEffect, useMemo, useState } from "react";
import type { Key } from "react";
import { Button, Card, Popconfirm, Space, Statistic, Tabs, message } from "antd";
import {
  CheckCircleOutlined,
  FileAddOutlined,
  FolderOutlined,
  PlusOutlined,
  ReloadOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import { api } from "../api";
import { openAttachmentOnlinePreview } from "../attachmentOnlinePreview.mjs";
import { rememberCaseDetailTarget } from "../caseDetailNavigation";
import { rememberContractDetailTarget } from "../contractDetailNavigation";
import { rememberCustomerDetailTarget } from "../customerDetailNavigation";
import { resolveDetailRelation } from "../detailRelationResolver";
import { rememberTaskDetailTarget } from "../taskDetailNavigation";
import { rememberInvestigationDetailTarget } from "../investigationDetailNavigation";
import {
  consumeBusinessRecordDetailTarget,
  rememberBusinessRecordDetailTarget,
} from "../businessRecordDetailNavigation";
import { consumeDocumentSearchDetailTarget } from "../documentSearchDetailNavigation";
import { formatRequiredDate } from "../formSafety";
import RecordImportButton from "../RecordImportButton";
import "../document-center.css";
import type {
  Attachment,
  DocumentSummary,
  HistoryEvent,
  ReceiptRow,
  RecordRow,
  SealAsset,
  Template,
  LegacyHistoricalAttachment,
} from "./types";
import { archiveCategories, personDisplayName } from "./constants";
import {
  ArchiveList,
  DocumentList,
  FileList,
  LegacyHistoryList,
  OutgoingList,
  OutgoingSearchForm,
  TemplateList,
} from "./DocumentTabContent";
import { DocumentDetail } from "./DocumentDetail";
import { OfficialOutgoingDetail } from "./OfficialOutgoingDetail";
import { DocumentReceiptPanel } from "./DocumentReceiptPanel";
import {
  ActionModal,
  CaseLinkModal,
  DocumentCreateModal,
  OutgoingModal,
  OutgoingReviewModal,
  PreviewModal,
  ReceiptDateModal,
  TemplateModal,
  UploadModal,
} from "./DocumentModals";
import { Form } from "antd";
import { AttachmentDetailDrawer, TemplateDetailDrawer } from "./DocumentDrawers";

export default function DocumentCenterPage({
  initialView,
  onNavigate,
}: {
  initialView: string;
  onNavigate?: (route: string) => void;
}) {
  // ===== Profile =====
  const profile = useMemo(() => {
    try {
      return JSON.parse(localStorage.getItem("user") || "{}");
    } catch {
      return {};
    }
  }, []);

  // ===== Tab state =====
  const first =
    initialView === "documents-template"
      ? "templates"
      : initialView === "documents-archive"
        ? "archive"
        : initialView === "documents-files"
          ? "files"
          : initialView === "documents-legacy-history"
            ? "legacy-history"
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

  // ===== Data states =====
  const [documents, setDocuments] = useState<RecordRow[]>([]);
  const [outgoingDocuments, setOutgoingDocuments] = useState<RecordRow[]>([]);
  const [contracts, setContracts] = useState<RecordRow[]>([]);
  const [sealAssets, setSealAssets] = useState<SealAsset[]>([]);
  const [cases, setCases] = useState<RecordRow[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [legacyHistoricalAttachments, setLegacyHistoricalAttachments] = useState<
    LegacyHistoricalAttachment[]
  >([]);
  const [legacyHistoricalAttachmentLoading, setLegacyHistoricalAttachmentLoading] =
    useState(false);
  const [legacyHistoricalAttachmentError, setLegacyHistoricalAttachmentError] = useState<
    string | null
  >(null);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [summary, setSummary] = useState<DocumentSummary>({
    documents: 0,
    pending_receipt: 0,
    received: 0,
    attachments: 0,
    archive_materials: 0,
    templates: 0,
  });
  const [loading, setLoading] = useState(false);

  // ===== UI states: drawers and modals =====
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

  // ===== Outgoing states =====
  const [outgoingOpen, setOutgoingOpen] = useState(false);
  const [outgoingSelected, setOutgoingSelected] = useState<Key[]>([]);
  const [outgoingDetail, setOutgoingDetail] = useState<any>(null);
  const [outgoingHistory, setOutgoingHistory] = useState<HistoryEvent[]>([]);
  const [editingOutgoing, setEditingOutgoing] = useState<any>(null);
  const [outgoingReview, setOutgoingReview] =
    useState<{ row: RecordRow; approved: boolean } | null>(null);
  const [outgoingQuery, setOutgoingQuery] = useState<Record<string, string>>({});

  // ===== Receipt states =====
  const [receiptQuery, setReceiptQuery] = useState<Record<string, any>>({});
  const [selectedReceiptKeys, setSelectedReceiptKeys] = useState<Key[]>([]);
  const [receiptDateOpen, setReceiptDateOpen] = useState(false);
  const [receiptDate, setReceiptDate] = useState<ReturnType<typeof dayjs> | null>(null);
  const [caseLinkOpen, setCaseLinkOpen] = useState(false);
  const [linkingCases, setLinkingCases] = useState(false);

  // ===== Forms =====
  const [documentForm] = Form.useForm();
  const [uploadForm] = Form.useForm();
  const [templateForm] = Form.useForm();
  const [actionForm] = Form.useForm();
  const [receiptForm] = Form.useForm();
  const [outgoingForm] = Form.useForm();
  const [outgoingReviewForm] = Form.useForm();
  const [outgoingQueryForm] = Form.useForm();
  const [caseLinkForm] = Form.useForm<{ case_ids: number[] }>();

  // ===== Navigation helpers =====
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
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "关联案件加载失败");
    }
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
          rememberCustomerDetailTarget({
            id: record.id,
            serial_no: record.serial_no,
            title: record.title,
          });
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
          rememberInvestigationDetailTarget({
            id: record.id,
            serial_no: record.serial_no,
            module: record.module,
          });
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
          if (
            !rememberBusinessRecordDetailTarget({ id: record.id, module: record.module })
          ) {
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

  // ===== Data loading =====
  const load = async (outgoingQueryOverride = outgoingQuery) => {
    setLoading(true);
    try {
      const [
        docRes,
        outgoingRes,
        caseRes,
        contractRes,
        fileRes,
        sealAssetsRes,
        templateRes,
        summaryRes,
      ] = await Promise.all([
        api.get("/records", { params: { module: "document", page_size: 100 } }),
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

  const loadLegacyHistoricalAttachments = async () => {
    setLegacyHistoricalAttachmentLoading(true);
    setLegacyHistoricalAttachmentError(null);
    try {
      const { data } = await api.get("/legacy-history/attachments", {
        params: { page_size: 200, include_inactive: true },
      });
      setLegacyHistoricalAttachments(data.items || []);
    } catch (error: any) {
      setLegacyHistoricalAttachments([]);
      setLegacyHistoricalAttachmentError(
        error?.response?.data?.detail || "历史附件元数据加载失败",
      );
    } finally {
      setLegacyHistoricalAttachmentLoading(false);
    }
  };

  useEffect(() => {
    if (tab === "legacy-history") void loadLegacyHistoricalAttachments();
  }, [tab]);

  // ===== Official outgoing =====
  const searchOfficialOutgoing = async () => {
    const values = outgoingQueryForm.getFieldsValue();
    const applicationDates = values.application_dates || [];
    const params = Object.fromEntries(
      Object.entries({
        official_no: String(values.official_no || "").trim(),
        owner: String(values.owner || "").trim(),
        customer: String(values.customer || "").trim(),
        case_no: String(values.case_no || "").trim(),
        contract_no: String(values.contract_no || "").trim(),
        status_value: String(values.status_value || "").trim(),
        seal_type: String(values.seal_type || "").trim(),
        file_name: String(values.file_name || "").trim(),
        application_date_from: applicationDates[0]
          ? applicationDates[0].format("YYYY-MM-DD")
          : "",
        application_date_to: applicationDates[1]
          ? applicationDates[1].format("YYYY-MM-DD")
          : "",
      }).filter(([, value]) => Boolean(value)) as [string, string][],
    );
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
    const source = (values.source_type === "case" ? cases : contracts).find(
      (item) => item.id === Number(values.source_record_id),
    );
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
      message.success("正式发文已创建");
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
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "正式发文详情加载失败");
    }
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
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "正式发文保存失败");
    }
  };

  const reviewOfficialOutgoing = async (
    row: RecordRow,
    approved: boolean,
    comment: string,
  ) => {
    try {
      await api.post(`/official-outgoing/${row.id}/review`, {
        approved,
        comment: comment.trim(),
      });
      message.success(approved ? "正式发文已通过" : "正式发文已拒绝");
      setOutgoingReview(null);
      outgoingReviewForm.resetFields();
      await load();
      if (outgoingDetail?.id === row.id) await openOfficialOutgoingDetail(row);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "正式发文审批失败");
    }
  };

  const rollbackOfficialOutgoing = async (row: RecordRow) => {
    try {
      await api.post(`/official-outgoing/${row.id}/rollback`, {
        reason: "申请人撤回正式发文",
      });
      message.success("正式发文已撤回");
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "正式发文撤回失败");
    }
  };

  const openOfficialOutgoingDetail = async (row: RecordRow) => {
    try {
      const [detail, historyResult] = await Promise.all([
        api.get(`/official-outgoing/${row.id}`),
        api.get(`/records/${row.id}/history`),
      ]);
      setOutgoingDetail(detail.data);
      setOutgoingHistory(historyResult.data.items || []);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "正式发文详情加载失败");
    }
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
    rememberContractDetailTarget({
      id: Number(row.source_record_id) || undefined,
      serial_no: row.source_serial_no,
    });
    onNavigate?.("contract-company");
  };

  const submitOfficialOutgoing = async (row: RecordRow) => {
    try {
      await api.post(`/official-outgoing/${row.id}/submit`, {});
      message.success("正式发文已提交");
      await load();
      await openOfficialOutgoingDetail(row);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "正式发文提交失败");
    }
  };

  const uploadOfficialOutgoingFile = async (
    row: any,
    uploadFile: File,
    stamped = false,
  ) => {
    const data = new FormData();
    data.append("file", uploadFile);
    try {
      if (stamped) await api.post(`/official-outgoing/${row.id}/stamp-file`, data);
      else {
        data.append("record_id", String(row.id));
        data.append("category", "正式发文附件");
        await api.post("/attachments", data);
      }
      message.success(stamped ? "盖章文件已上传" : "正式发文附件已上传");
      await load();
      await openOfficialOutgoingDetail(row);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "文件上传失败");
    }
    return false;
  };

  const deleteOfficialOutgoingFile = async (row: any, attachment: Attachment) => {
    try {
      await api.delete(`/attachments/${attachment.id}`);
      message.success("正式发文附件已删除");
      await load();
      await openOfficialOutgoingDetail(row);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "正式发文附件删除失败");
    }
  };

  const downloadOfficialOutgoing = async () => {
    if (!outgoingSelected.length)
      return message.warning("请先勾选需要打包下载的正式发文");
    try {
      const response = await api.post(
        "/official-outgoing/download",
        { record_ids: outgoingSelected },
        { responseType: "blob" },
      );
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = "正式发文附件.zip";
      link.click();
      URL.revokeObjectURL(url);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "正式发文打包下载失败");
    }
  };

  const markOfficialOutgoingStamped = async () => {
    if (!outgoingSelected.length)
      return message.warning("请先勾选审批通过的正式发文");
    const invalid = outgoingDocuments.filter(
      (item) => outgoingSelected.includes(item.id) && item.status !== "已通过",
    );
    if (invalid.length)
      return message.warning(
        "“标记已盖章”仅支持审批通过的正式发文；已盖章文书可直接打包下载",
      );
    try {
      await api.post("/official-outgoing/mark-stamped", {
        record_ids: outgoingSelected,
      });
      message.success("所选正式发文已标记为已盖章");
      setOutgoingSelected([]);
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "标记正式发文盖章失败");
    }
  };

  // ===== Document search navigation =====
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
        message.warning(
          error?.response?.data?.detail || "关联附件或模板不存在，或当前账号无权查看",
        );
      }
    })();
  }, []);

  // ===== Document CRUD =====
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
      await openAttachmentOnlinePreview(api, row);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || error?.message || "附件预览失败");
    }
  };

  const deleteFile = async (id: number) => {
    try {
      await api.delete(`/attachments/${id}`);
      message.success("附件已删除");
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "删除失败");
    }
  };

  // ===== Template CRUD =====
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

  // ===== Document detail & workflow =====
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
        message.error(
          error?.response?.data?.detail || error?.message || "收发文详情加载失败",
        );
      }
    })();
  }, []);

  const startAction = (row: RecordRow, toStatus: string) => {
    setViewing(row);
    setActionStatus(toStatus);
    actionForm.resetFields();
    actionForm.setFieldsValue({
      action_date: dayjs(),
      handler: personDisplayName(profile.display_name),
    });
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

  const documentActionButton = (r: RecordRow) =>
    r.status === "待登记" ? (
      <Button type="link" onClick={() => startAction(r, "待签收")}>
        完成登记
      </Button>
    ) : r.status === "待签收" ? (
      <Button type="link" icon={<CheckCircleOutlined />} onClick={() => startAction(r, "已签收")}>
        {r.data.direction === "发文" ? "确认送达" : "确认签收"}
      </Button>
    ) : r.status === "已签收" ? (
      <Button type="link" icon={<FolderOutlined />} onClick={() => startAction(r, "已归档")}>
        归档
      </Button>
    ) : null;

  // ===== Receipt (官文/我的/公司收文) =====
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
    const found = receiptAttachment(r);
    if (!found) return showReceipt(r);
    void previewAttachment(found);
  };

  const isReceiptView = ["official", "my-receipts", "company-receipts"].includes(tab);
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
      message.success(
        `已标记 ${data.processed} 条官文为${processed ? "已处理" : "未处理"}`,
      );
      setSelectedReceiptKeys([]);
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "更新官文业务处理状态失败");
    }
  };

  const openOfficialCaseLinker = () => {
    if (!selectedFormalReceipts.length) {
      message.warning("请选择至少一条官文收文记录");
      return;
    }
    const existingCaseIds = Array.from(
      new Set(
        selectedFormalReceipts.flatMap((row) => {
          const linked = Array.isArray(row.data.case_ids)
            ? row.data.case_ids
            : [row.data.case_id];
          return linked.map(Number).filter((id) => id > 0);
        }),
      ),
    );
    caseLinkForm.setFieldsValue({ case_ids: existingCaseIds });
    setCaseLinkOpen(true);
  };

  const linkSelectedOfficialReceiptsToCases = async () => {
    if (!selectedFormalReceipts.length) {
      message.warning("请选择至少一条官文收文记录");
      return;
    }
    try {
      const values = await caseLinkForm.validateFields();
      const caseIds = Array.from(
        new Set((values.case_ids || []).map(Number).filter((id) => id > 0)),
      );
      if (!caseIds.length) {
        message.warning("请选择至少一个案件");
        return;
      }
      setLinkingCases(true);
      const { data } = await api.post("/documents/official/batch-case-ids", {
        record_ids: selectedFormalReceipts.map((row) => row.id),
        case_ids: caseIds,
      });
      message.success(
        data.updated
          ? `已关联 ${data.updated} 条官文收文至 ${caseIds.length} 个案件`
          : "所选官文收文已关联至所选案件",
      );
      setCaseLinkOpen(false);
      caseLinkForm.resetFields();
      setSelectedReceiptKeys([]);
      await load();
    } catch (error: any) {
      if (!error?.errorFields)
        message.error(error?.response?.data?.detail || "批量关联案件失败");
    } finally {
      setLinkingCases(false);
    }
  };

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
    if (
      [
        "authorization-letter",
        "law-firm-letter",
        "identity-certificate",
        "settlement-list",
      ].includes(key)
    ) {
      onNavigate?.("documents-agent");
      return;
    }
    openSelectedReceiptCase();
  };

  // ===== Archive rows (computed) =====
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


  // ===== Receipt panel =====
  const receiptPanel = isReceiptView ? (
    <DocumentReceiptPanel
      tab={tab}
      loading={loading}
      receiptForm={receiptForm}
      searchedReceipts={searchedReceipts}
      selectedReceiptKeys={selectedReceiptKeys}
      selectedFormalReceipts={selectedFormalReceipts}
      receiptAttachment={receiptAttachment}
      onSelectionChange={setSelectedReceiptKeys}
      onSearch={receiptSearch}
      onClearSearch={clearReceiptSearch}
      onShowReceipt={showReceipt}
      onPreviewReceiptFile={previewReceiptFile}
      onOpenCaseDetail={openCaseDetail}
      onOpenUpload={openUpload}
      onDeleteSelected={deleteSelectedReceipts}
      onOpenReceiptDateEditor={openReceiptDateEditor}
      onOpenCaseLinker={openOfficialCaseLinker}
      onUpdateProcessStatus={updateOfficialProcessStatus}
      onExport={exportOfficialReceipts}
      onMoreAction={handleReceiptMoreAction}
    />
  ) : null;

  // ===== Render =====
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
                  <>
                    <Popconfirm
                      title="确认将所选审批通过的正式发文标记为已盖章？"
                      onConfirm={markOfficialOutgoingStamped}
                    >
                      <Button disabled={!outgoingSelected.length}>标记已盖章</Button>
                    </Popconfirm>
                    <Button onClick={downloadOfficialOutgoing}>打包下载</Button>
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={() => {
                        outgoingForm.resetFields();
                        outgoingForm.setFieldsValue({
                          source_type: "contract",
                          need_audit: true,
                          is_offline_print: true,
                          print_quantity: 1,
                        });
                        setOutgoingOpen(true);
                      }}
                    >
                      新建正式发文
                    </Button>
                  </>
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
                  <Button type="primary" icon={<UploadOutlined />} onClick={() => openUpload()}>
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
                { key: "legacy-history", label: "历史附件元数据" },
                { key: "templates", label: "文书模板" },
                { key: "archive", label: "案件归档材料" },
              ]}
            />
            {tab === "outgoing" && (
              <OutgoingSearchForm
                form={outgoingQueryForm}
                onSearch={searchOfficialOutgoing}
                onReset={resetOfficialOutgoingSearch}
              />
            )}
            {tab === "documents" ? (
              <DocumentList
                documents={documents}
                attachments={attachments}
                loading={loading}
                onOpenDetail={openDocument}
                onOpenUpload={openUpload}
                onOpenCustomerDetail={openCustomerDetail}
                onOpenCaseDetail={openCaseDetail}
                onStartAction={startAction}
              />
            ) : tab === "outgoing" ? (
              <OutgoingList
                outgoingDocuments={outgoingDocuments}
                loading={loading}
                selectedKeys={outgoingSelected}
                onSelectionChange={setOutgoingSelected}
                onOpenDetail={openOfficialOutgoingDetail}
                onOpenEditor={openOfficialOutgoingEditor}
                onSubmit={submitOfficialOutgoing}
                onOpenSource={openOfficialOutgoingSource}
                onOpenCustomerDetail={openCustomerDetail}
                onApprove={(row) => {
                  outgoingReviewForm.setFieldsValue({ comment: "" });
                  setOutgoingReview({ row, approved: true });
                }}
                onReject={(row) => {
                  outgoingReviewForm.setFieldsValue({ comment: "" });
                  setOutgoingReview({ row, approved: false });
                }}
                onRollback={rollbackOfficialOutgoing}
              />
            ) : tab === "files" ? (
              <FileList
                attachments={attachments}
                loading={loading}
                onPreview={previewAttachment}
                onDownload={download}
                onDelete={deleteFile}
                onOpenRecord={openAttachmentRecord}
              />
            ) : tab === "legacy-history" ? (
              <LegacyHistoryList
                attachments={legacyHistoricalAttachments}
                loading={legacyHistoricalAttachmentLoading}
                error={legacyHistoricalAttachmentError}
              />
            ) : tab === "templates" ? (
              <TemplateList
                templates={templates}
                loading={loading}
                onViewDetail={setTemplateDetail}
                onEdit={editTemplate}
                onToggle={toggleTemplate}
                onDelete={deleteTemplate}
              />
            ) : (
              <ArchiveList
                archiveRows={archiveRows}
                loading={loading}
                onOpenCaseDetail={openCaseDetail}
                onOpenCustomerDetail={openCustomerDetail}
                onOpenUpload={openUpload}
              />
            )}
          </Card>
        </>
      )}

      {/* ===== Drawers ===== */}
      <OfficialOutgoingDetail
        open={!!outgoingDetail}
        detail={outgoingDetail}
        history={outgoingHistory}
        onClose={() => setOutgoingDetail(null)}
        onOpenSource={openOfficialOutgoingSource}
        onPreviewAttachment={previewAttachment}
        onUploadFile={uploadOfficialOutgoingFile}
        onDeleteFile={deleteOfficialOutgoingFile}
        onSubmit={submitOfficialOutgoing}
      />

      <DocumentDetail
        open={Boolean(viewing) && !actionStatus}
        viewing={viewing}
        attachments={attachments}
        history={history}
        actionButton={viewing && documentActionButton(viewing)}
        onClose={() => setViewing(null)}
        onOpenCustomerDetail={openCustomerDetail}
        onOpenCaseDetail={openCaseDetail}
        onPreviewAttachment={previewAttachment}
        onDownload={download}
        onOpenUpload={openUpload}
      />

      <AttachmentDetailDrawer
        open={Boolean(attachmentDetail)}
        attachmentDetail={attachmentDetail}
        onClose={() => setAttachmentDetail(null)}
        onDownload={download}
        onOpenRecord={openAttachmentRecord}
      />

      <TemplateDetailDrawer
        open={Boolean(templateDetail)}
        templateDetail={templateDetail}
        onClose={() => setTemplateDetail(null)}
      />

      {/* ===== Modals ===== */}
      <OutgoingReviewModal
        open={!!outgoingReview}
        outgoingReviewForm={outgoingReviewForm}
        reviewData={outgoingReview}
        onOk={async () => {
          const values = await outgoingReviewForm.validateFields();
          if (outgoingReview)
            await reviewOfficialOutgoing(
              outgoingReview.row,
              outgoingReview.approved,
              values.comment || "",
            );
        }}
        onCancel={() => {
          setOutgoingReview(null);
          outgoingReviewForm.resetFields();
        }}
      />

      <OutgoingModal
        open={outgoingOpen}
        outgoingForm={outgoingForm}
        editingOutgoing={editingOutgoing}
        cases={cases}
        contracts={contracts}
        sealAssets={sealAssets}
        attachments={attachments}
        onCreate={createOfficialOutgoing}
        onUpdate={updateOfficialOutgoing}
        onCancel={() => {
          setOutgoingOpen(false);
          setEditingOutgoing(null);
          outgoingForm.resetFields();
        }}
      />

      <ReceiptDateModal
        open={receiptDateOpen}
        receiptDate={receiptDate}
        selectedCount={selectedFormalReceipts.length}
        onDateChange={setReceiptDate}
        onOk={saveReceiptDate}
        onCancel={() => setReceiptDateOpen(false)}
      />

      <CaseLinkModal
        open={caseLinkOpen}
        caseLinkForm={caseLinkForm}
        cases={cases}
        linkingCases={linkingCases}
        selectedCount={selectedFormalReceipts.length}
        onOk={() => void linkSelectedOfficialReceiptsToCases()}
        onCancel={() => {
          setCaseLinkOpen(false);
          caseLinkForm.resetFields();
        }}
      />

      <DocumentCreateModal
        open={documentOpen}
        documentForm={documentForm}
        cases={cases}
        onCreate={createDocument}
        onCancel={() => setDocumentOpen(false)}
      />

      <UploadModal
        open={uploadOpen}
        uploadForm={uploadForm}
        uploadTarget={uploadTarget}
        tab={tab}
        cases={cases}
        documents={documents}
        file={file}
        onFileChange={setFile}
        onOk={upload}
        onCancel={() => setUploadOpen(false)}
      />

      <TemplateModal
        open={templateOpen}
        templateForm={templateForm}
        editingTemplate={editingTemplate}
        onSave={saveTemplate}
        onCancel={() => {
          setTemplateOpen(false);
          setEditingTemplate(null);
        }}
      />

      <ActionModal
        open={Boolean(actionStatus)}
        actionForm={actionForm}
        actionStatus={actionStatus}
        direction={viewing?.data?.direction}
        onSubmit={submitAction}
        onCancel={() => setActionStatus("")}
      />

      <PreviewModal
        open={previewOpen}
        previewName={previewName}
        previewKind={previewKind}
        previewUrl={previewUrl}
        previewText={previewText}
        onCancel={() => {
          setPreviewOpen(false);
          setPreviewUrl("");
        }}
      />
    </>
  );
}
