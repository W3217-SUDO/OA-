import { useEffect, useMemo, useState } from "react";
import { sealViewSpec } from "./sealViewMapping";
import {
  Alert,
  Button,
  Card,
  DatePicker,
  Descriptions,
  Drawer,
  Form,
  Input,
  InputNumber,
  message,
  Modal,
  Popconfirm,
  Popover,
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
  DeleteOutlined,
  DownloadOutlined,
  FileDoneOutlined,
  PlusOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  ToolOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import { api } from "./api";
import { rememberCaseDetailTarget } from "./caseDetailNavigation";
import { rememberContractDetailTarget } from "./contractDetailNavigation";
import { rememberCustomerDetailTarget } from "./customerDetailNavigation";
import { resolveDetailRelation } from "./detailRelationResolver";
import { consumeBusinessRecordDetailTarget } from "./businessRecordDetailNavigation";
import {
  canBatchDeleteSealFiles,
  canBatchStampSealRows,
  canBatchWithdrawSealRows,
  canSealAction,
  canViewSealAssetAudit,
  createSealActionGate,
  createSealAssetAuditRequestTracker,
  createSealDetailRequestTracker,
  createSealFileListRequestTracker,
  createSealPreviewRequestTracker,
  mergeSealAssetSnapshot,
  formatSealAttachmentSize,
  getSealAttachmentExtension,
  sealAssetAuditFailureMessage,
  sealAssetAuditPagination,
  sealFilePagination,
  sealAttachmentListFailureMessage,
  sealQueryFailureMessage,
  compareSealDateValues,
  selectedSealRows,
  shouldCloseSealAssetAuditAfterDelete,
  sealErrorMessage,
  sealResponseIsFailure,
  toSealAuditRows,
} from "./sealWorkflowPolicy";
import type { SealAssetAuditRow } from "./sealWorkflowPolicy";
import { formatRequiredDate } from "./formSafety";
import RecordImportButton from "./RecordImportButton";
import "./seal-center.css";

type SealAsset = {
  id: number;
  code: string;
  name: string;
  seal_type: string;
  custodian: string;
  location: string;
  status: string;
  usage_count: number;
  last_used_at?: string;
  remark: string;
};
type SealRow = {
  id: number;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
  owner: string;
  description: string;
  data: Record<string, any>;
  seal_asset?: SealAsset;
  created_at: string;
  updated_at: string;
  file_count: number;
};
type Summary = {
  total: number;
  pending: number;
  waiting_stamp: number;
  completed: number;
};
type EventRow = {
  id: number;
  action: string;
  from_status: string;
  to_status: string;
  operator: string;
  comment: string;
  created_at: string;
  audit_status?: string;
  audit_date?: string;
  audit_content?: string;
  audit_round?: number;
};
type AttachmentRow = {
  id: number;
  original_name: string;
  category: string;
  size: number;
  uploader: string;
  created_at: string;
};
type SealPreviewMode = "binary" | "text" | "unsupported";
function getSealPreviewMode(payload: { kind?: string }): SealPreviewMode {
  if (payload.kind === "image" || payload.kind === "pdf") return "binary";
  if (payload.kind === "docx" || payload.kind === "text") return "text";
  return "unsupported";
}
const sealUploadExtensions = new Set([
  ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
  ".txt", ".png", ".jpg", ".jpeg", ".zip", ".rar",
]);
function validateSealUploadFile(file: File | undefined): string | null {
  if (!file || !file.name || file.size <= 0) return "请选择上传文件.";
  const suffix = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  if (!sealUploadExtensions.has(suffix)) return "不支持的文件格式";
  if (file.size > 20 * 1024 * 1024) return "单个文件不能超过 20MB";
  return null;
}
function sealUploadedAttachmentId(response: { data?: any } | undefined): number | null {
  const direct = Number(response?.data?.id);
  if (Number.isFinite(direct) && direct > 0) return direct;
  const nested = Number(response?.data?.attachment?.id);
  if (Number.isFinite(nested) && nested > 0) return nested;
  return null;
}
function sealActionFailureMessage(type: "approve" | "reject" | "stamp" | "archive"): string {
  return {
    approve: "审批失败",
    reject: "审批失败",
    stamp: "登记实际用印失败",
    archive: "归档失败",
  }[type];
}
function sealAttachmentDeleteFailureMessage(status?: number): string {
  if (status === 403) return "当前账号无权删除该用印文件";
  if (status === 409) return "仅草稿用印申请可以删除文件";
  return "用印文件删除失败";
}
function sealPackageDownloadFailureMessage(status?: number): string {
  if (status === 403) return "当前账号无权下载所选用印附件";
  if (status === 404) return "所选用印申请暂无可下载附件";
  return "打包下载失败";
}
function sealAttachmentDownloadFailureMessage(status?: number): string {
  if (status === 403) return "当前账号无权下载该用印文件";
  if (status === 404) return "附件不存在或文件实体不存在";
  if (status === 409) return "当前状态不允许下载该用印文件";
  return "用印文件下载失败";
}
function sealAttachmentPreviewFailureMessage(status?: number): string {
  if (status === 403) return "当前账号无权预览该用印文件";
  if (status === 404) return "附件不存在或文件实体不存在";
  if (status === 409) return "当前状态不允许预览该用印文件";
  return "文件预览失败";
}
function ensureSealSuccess<T extends { data?: unknown }>(response: T, fallback: string): T {
  if (sealResponseIsFailure(response.data)) {
    const failure = new Error(sealErrorMessage(response.data, fallback)) as Error & {
      response?: { data?: unknown };
    };
    failure.response = { data: { detail: failure.message } };
    throw failure;
  }
  return response;
}
async function postSeal(url: string, data?: unknown) {
  return ensureSealSuccess(await api.post(url, data), "鐢ㄥ嵃鎿嶄綔澶辫触");
}
async function patchSeal(url: string, data?: unknown) {
  return ensureSealSuccess(await api.patch(url, data), "鐢ㄥ嵃淇濆瓨澶辫触");
}
async function deleteSeal(url: string) {
  return ensureSealSuccess(await api.delete(url), "鐢ㄥ嵃鍒犻櫎澶辫触");
}
async function postSealBlob(url: string, data: unknown, config: any) {
  const response = await api.post(url, data, config);
  if (typeof Blob !== "undefined" && response.data instanceof Blob && response.data.type.includes("json")) {
    let payload: unknown;
    try {
      payload = JSON.parse(await response.data.text());
    } catch {
      payload = undefined;
    }
    if (sealResponseIsFailure(payload)) {
      const failure = new Error(sealErrorMessage(payload, "鎵撳寘涓嬭浇澶辫触")) as Error & {
        response?: { data?: unknown };
      };
      failure.response = { data: { detail: failure.message } };
      throw failure;
    }
  }
  return ensureSealSuccess(response, "鎵撳寘涓嬭浇澶辫触");
}
type RelationRow = {
  id: number;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
  data: Record<string, any>;
};
const statusColors: Record<string, string> = {
  草稿: "default",
  待审批: "orange",
  待用印: "blue",
  已用印: "green",
  已归档: "cyan",
  已拒绝: "red",
  已撤回: "default",
};
const sealStatusOptions = [
  { value: "待审批", label: "待审核" },
  { value: "待用印", label: "已审待用印" },
  { value: "已拒绝", label: "审核拒绝" },
  { value: "已撤回", label: "已撤回" },
  { value: "已用印", label: "已用印" },
  { value: "已归档", label: "已归档" },
];
const assetColors: Record<string, string> = {
  可用: "green",
  停用: "default",
  维修: "orange",
  遗失: "red",
};
const sealTypes = [
  "合同章",
  "公章",
  "所函专用章",
  "法人章",
  "发票章",
  "财务专用章",
  "财务三排章",
];

const listSealRowFileNames = (row: SealRow): string[] => {
  const names: string[] = [];
  const append = (value: unknown) => {
    if (!value) return;
    if (Array.isArray(value)) {
      value.forEach(append);
      return;
    }
    if (typeof value === "object") {
      const item = value as Record<string, unknown>;
      append(item.original_name || item.file_name || item.FileName || item.name);
      return;
    }
    String(value)
      .split(/[\n\r,;；、|]+/)
      .map((name) => name.trim())
      .filter(Boolean)
      .forEach((name) => names.push(name));
  };

  append(row.data.document_names);
  append(row.data.documentNames);
  append(row.data.file_names);
  append(row.data.fileNames);
  append(row.data.attachments);
  append(row.data.files);

  return Array.from(new Set(names)).slice(0, 5);
};

export default function SealCenterPage({
  initialView,
  onNavigate,
}: {
  initialView: string;
  onNavigate?: (route: string) => void;
}) {
  const tabFromView = (v: string) =>
    v.startsWith("seal-audit")
      ? "audit"
      : v.startsWith("seal-admin-")
        ? "admin"
        : v === "seal-admin"
          ? "assets"
          : "my";
  const statusFromView = (v: string): string[] => sealViewSpec(v).statuses;
  const [tab, setTab] = useState(tabFromView(initialView));
  const [rows, setRows] = useState<SealRow[]>([]);
  const [assets, setAssets] = useState<SealAsset[]>([]);
  const [assetAuditOpen, setAssetAuditOpen] = useState(false);
  const [assetAuditAsset, setAssetAuditAsset] = useState<SealAsset | null>(null);
  const [assetAuditRows, setAssetAuditRows] = useState<SealAssetAuditRow[]>([]);
  const [assetAuditTotal, setAssetAuditTotal] = useState(0);
  const [assetAuditPage, setAssetAuditPage] = useState(1);
  const [assetAuditPageSize, setAssetAuditPageSize] = useState(sealAssetAuditPagination.defaultPageSize);
  const [assetAuditLoading, setAssetAuditLoading] = useState(false);
  const [assetAuditFilters, setAssetAuditFilters] = useState({
    action: "",
    operator: "",
    keyword: "",
    date_from: "",
    date_to: "",
  });
  const [cases, setCases] = useState<RelationRow[]>([]);
  const [contracts, setContracts] = useState<RelationRow[]>([]);
  const [customers, setCustomers] = useState<RelationRow[]>([]);
  const [summary, setSummary] = useState<Summary>({
    total: 0,
    pending: 0,
    waiting_stamp: 0,
    completed: 0,
  });
  const [loading, setLoading] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [query, setQuery] = useState<Record<string, any>>({});
  const [selectedKeys, setSelectedKeys] = useState<(string | number)[]>([]);
  const [editingApplication, setEditingApplication] = useState<SealRow | null>(
    null,
  );
  const [createOpen, setCreateOpen] = useState(false);
  const [assetOpen, setAssetOpen] = useState(false);
  const [editAsset, setEditAsset] = useState<SealAsset | null>(null);
  const [detail, setDetail] = useState<SealRow | null>(null);
  const [history, setHistory] = useState<EventRow[]>([]);
  const [auditListOpen, setAuditListOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewUrl, setPreviewUrl] = useState("");
  const [previewText, setPreviewText] = useState("");
  const [previewMode, setPreviewMode] = useState<"binary" | "text" | "unsupported">("binary");
  const [previewDetail, setPreviewDetail] = useState("");
  const [previewName, setPreviewName] = useState("");
  const [attachments, setAttachments] = useState<AttachmentRow[]>([]);
  const [attachmentPage, setAttachmentPage] = useState(1);
  const [attachmentPageSize, setAttachmentPageSize] = useState(sealFilePagination.defaultPageSize);
  const [attachmentTotal, setAttachmentTotal] = useState(0);
  const [attachmentSelectedKeys, setAttachmentSelectedKeys] = useState<number[]>([]);
  const detailRequestTracker = useMemo(() => createSealDetailRequestTracker(), []);
  const fileListRequestTracker = useMemo(() => createSealFileListRequestTracker(), []);
  const previewRequestTracker = useMemo(() => createSealPreviewRequestTracker(), []);
  const [fileListOpen, setFileListOpen] = useState(false);
  const [fileListRow, setFileListRow] = useState<SealRow | null>(null);
  const [fileListAttachments, setFileListAttachments] = useState<AttachmentRow[]>([]);
  const [fileListPage, setFileListPage] = useState(1);
  const [fileListPageSize, setFileListPageSize] = useState(sealFilePagination.defaultPageSize);
  const [fileListTotal, setFileListTotal] = useState(0);
  const [stampAttachments, setStampAttachments] = useState<AttachmentRow[]>([]);
  const [stampAttachmentId, setStampAttachmentId] = useState<number | null>(null);
  const [stampAttachmentLoading, setStampAttachmentLoading] = useState(false);
  const [stampAttachmentPage, setStampAttachmentPage] = useState(1);
  const [stampAttachmentPageSize, setStampAttachmentPageSize] = useState(sealFilePagination.defaultPageSize);
  const [stampAttachmentTotal, setStampAttachmentTotal] = useState(0);
  const [stampAttachmentUploading, setStampAttachmentUploading] = useState(false);
  const [sourceAttachments, setSourceAttachments] = useState<AttachmentRow[]>([]);
  const [sourceAttachmentLoading, setSourceAttachmentLoading] = useState(false);
  const [sourceAttachmentPage, setSourceAttachmentPage] = useState(1);
  const [sourceAttachmentPageSize, setSourceAttachmentPageSize] = useState(sealFilePagination.defaultPageSize);
  const [sourceAttachmentTotal, setSourceAttachmentTotal] = useState(0);
  const [action, setAction] = useState<{
    type: "approve" | "reject" | "stamp" | "archive";
    row: SealRow;
  } | null>(null);
  const [batchStampOpen, setBatchStampOpen] = useState(false);
  const [createForm] = Form.useForm();
  const [assetForm] = Form.useForm();
  const [actionForm] = Form.useForm();
  const [batchStampForm] = Form.useForm();
  const [queryForm] = Form.useForm();
  const [actionSubmitting, setActionSubmitting] = useState(false);
  const actionGate = useMemo(() => createSealActionGate(), []);
  const assetAuditRequestTracker = useMemo(() => createSealAssetAuditRequestTracker(), []);
  const sessionRole = useMemo(() => {
    try {
      return String((JSON.parse(localStorage.getItem("user") || "{}") as { role?: string }).role || "");
    } catch {
      return "";
    }
  }, []);
  const canReadAssetAudit = canViewSealAssetAudit(sessionRole);
  const selectedUseType = Form.useWatch("use_type", createForm);
  const selectedCaseNo = Form.useWatch("case_no", createForm);
  const selectedContractNo = Form.useWatch("contract_no", createForm);
  const isContractSeal = selectedUseType === "合同用印";
  const isCaseSeal = selectedUseType === "案件用印";
  const showSourceRelationFields = isContractSeal || isCaseSeal;
  const selectedSourceRecord = useMemo(() => {
    if (isContractSeal && selectedContractNo) {
      return contracts.find((item) => item.serial_no === selectedContractNo) || null;
    }
    if (isCaseSeal && selectedCaseNo) {
      return cases.find((item) => item.serial_no === selectedCaseNo) || null;
    }
    return null;
  }, [cases, contracts, isCaseSeal, isContractSeal, selectedCaseNo, selectedContractNo]);
  useEffect(() => {
    if (!createOpen) return;
    if (!selectedSourceRecord) {
      setSourceAttachments([]);
      setSourceAttachmentPage(1);
      setSourceAttachmentPageSize(sealFilePagination.defaultPageSize);
      setSourceAttachmentTotal(0);
      createForm.setFieldValue("source_attachment_ids", []);
      return;
    }
    let active = true;
    const nextPageSize = sealFilePagination.defaultPageSize;
    setSourceAttachmentLoading(true);
    setSourceAttachmentPage(1);
    setSourceAttachmentPageSize(nextPageSize);
    setSourceAttachmentTotal(0);
    api
      .get("/attachments", {
        params: {
          record_id: selectedSourceRecord.id,
          page: 1,
          page_size: nextPageSize,
        },
      })
      .then(({ data }) => {
        if (!active) return;
        const items = Array.isArray(data.items) ? data.items : [];
        setSourceAttachments(items);
        setSourceAttachmentPage(Number(data.page) || 1);
        setSourceAttachmentPageSize(Number(data.page_size) || nextPageSize);
        setSourceAttachmentTotal(Number(data.total) || items.length);
        const availableIds = new Set(items.map((item: AttachmentRow) => Number(item.id)));
        const selectedIds = createForm.getFieldValue("source_attachment_ids");
        if (Array.isArray(selectedIds)) {
          const nextIds = selectedIds
            .map((id) => Number(id))
            .filter((id) => Number.isFinite(id) && availableIds.has(id));
          if (nextIds.length !== selectedIds.length) {
            createForm.setFieldValue("source_attachment_ids", nextIds);
          }
        }
      })
      .catch((error: any) => {
        if (!active) return;
        setSourceAttachments([]);
        message.error(
          error?.response?.data?.detail ||
            sealAttachmentListFailureMessage(error?.response?.status),
        );
      })
      .finally(() => {
        if (active) setSourceAttachmentLoading(false);
      });
    return () => {
      active = false;
    };
  }, [createForm, createOpen, selectedSourceRecord?.id]);
  const loadMoreSourceAttachments = async () => {
    if (!selectedSourceRecord || sourceAttachmentLoading) return;
    if (sourceAttachmentTotal > 0 && sourceAttachments.length >= sourceAttachmentTotal) return;
    const nextPage = sourceAttachmentPage + 1;
    setSourceAttachmentLoading(true);
    try {
      const { data } = await api.get("/attachments", {
        params: {
          record_id: selectedSourceRecord.id,
          page: nextPage,
          page_size: sourceAttachmentPageSize,
        },
      });
      const items = Array.isArray(data.items) ? data.items : [];
      setSourceAttachments((current) => {
        const seen = new Set(current.map((item) => Number(item.id)));
        return [
          ...current,
          ...items.filter((item: AttachmentRow) => !seen.has(Number(item.id))),
        ];
      });
      setSourceAttachmentPage(Number(data.page) || nextPage);
      setSourceAttachmentPageSize(Number(data.page_size) || sourceAttachmentPageSize);
      setSourceAttachmentTotal(Number(data.total) || sourceAttachmentTotal);
    } catch (error: any) {
      message.error(
        error?.response?.data?.detail ||
          sealAttachmentListFailureMessage(error?.response?.status),
      );
    } finally {
      setSourceAttachmentLoading(false);
    }
  };
  const handleUseTypeChange = (nextUseType: string) => {
    const nextIsContractSeal = nextUseType === "合同用印";
    const nextIsCaseSeal = nextUseType === "案件用印";
    const nextShowSourceRelationFields = nextIsContractSeal || nextIsCaseSeal;
    setSourceAttachments([]);
    setSourceAttachmentPage(1);
    setSourceAttachmentPageSize(sealFilePagination.defaultPageSize);
    setSourceAttachmentTotal(0);
    if (!nextShowSourceRelationFields) {
      createForm.setFieldsValue({
        customer: undefined,
        case_no: undefined,
        contract_no: undefined,
        source_attachment_ids: [],
      });
      return;
    }
    createForm.setFieldsValue({
      case_no: nextIsCaseSeal ? createForm.getFieldValue("case_no") : undefined,
      contract_no: nextIsContractSeal
        ? createForm.getFieldValue("contract_no")
        : undefined,
      source_attachment_ids: [],
    });
  };
  const clearQuery = () => {
    queryForm.resetFields();
    setQuery({});
  };
  const load = async () => {
    setLoading(true);
    try {
      const view = ["admin", "assets"].includes(tab) ? "all" : tab;
      const routeStatuses = statusFromView(initialView);
      const [apps, inventory, caseResult, contractResult, customerResult] =
        await Promise.all([
          api.get("/seals/applications", {
            params: {
              view,
              keyword,
              page_size: 100,
              serial_no: query.serial_no,
              applicant: query.applicant,
              record_status:
                routeStatuses.length === 1
                  ? routeStatuses[0]
                  : query.record_status,
              date_from: query.application_date?.[0]?.format("YYYY-MM-DD"),
              date_to: query.application_date?.[1]?.format("YYYY-MM-DD"),
              case_no: query.case_no,
              contract_no: query.contract_no,
              customer: query.customer,
              use_type: query.use_type,
              file_name: query.file_name,
            },
          }),
          api.get("/seals/assets", {
            params: { keyword: tab === "assets" ? keyword : "" },
          }),
          api.get("/records", { params: { module: "case", page_size: 100 } }),
          api.get("/records", {
            params: { module: "contract", page_size: 100 },
          }),
          api.get("/records", {
            params: { module: "customer", page_size: 100 },
          }),
        ]);
      setRows(apps.data.items);
      setSummary(apps.data.summary);
      setAssets(inventory.data.items);
      setCases(caseResult.data.items);
      setContracts(contractResult.data.items);
      setCustomers(customerResult.data.items);
    } catch (error: any) {
      message.error(
        error?.response?.data?.detail ||
          sealQueryFailureMessage(error?.response?.status),
      );
    } finally {
      setLoading(false);
    }
  };
  const clearAssetAudit = () => {
    assetAuditRequestTracker.invalidate();
    setAssetAuditLoading(false);
    setAssetAuditOpen(false);
    setAssetAuditAsset(null);
    setAssetAuditRows([]);
    setAssetAuditTotal(0);
    setAssetAuditPage(1);
  };
  const loadAssetAudit = async (
    assetId: number,
    nextPage = assetAuditPage,
    nextPageSize = assetAuditPageSize,
    filters = assetAuditFilters,
  ) => {
    if (!canReadAssetAudit) return;
    const requestId = assetAuditRequestTracker.next();
    setAssetAuditLoading(true);
    try {
      const { data } = await api.get(`/seals/assets/${assetId}/audit`, {
        params: {
          page: nextPage,
          page_size: nextPageSize,
          action: filters.action || undefined,
          operator: filters.operator || undefined,
          keyword: filters.keyword || undefined,
          date_from: filters.date_from || undefined,
          date_to: filters.date_to || undefined,
        },
      });
      if (!assetAuditRequestTracker.isCurrent(requestId)) return;
      setAssetAuditRows(Array.isArray(data.items) ? data.items : []);
      setAssetAuditTotal(Number(data.total) || 0);
      setAssetAuditPage(Number(data.page) || nextPage);
      setAssetAuditPageSize(Number(data.page_size) || nextPageSize);
    } catch (error: any) {
      if (!assetAuditRequestTracker.isCurrent(requestId)) return;
      message.error(
        sealErrorMessage(error, sealAssetAuditFailureMessage(error?.response?.status)),
      );
    } finally {
      if (assetAuditRequestTracker.isCurrent(requestId)) setAssetAuditLoading(false);
    }
  };
  const refreshAssetAudit = async () => {
    if (!assetAuditOpen || !assetAuditAsset || !canReadAssetAudit) return;
    const target = assetAuditAsset;
    const requestId = assetAuditRequestTracker.next();
    setAssetAuditLoading(true);
    try {
      const [inventoryResult, auditResult] = await Promise.all([
        api.get("/seals/assets", { params: { keyword: target.code } }),
        api.get(`/seals/assets/${target.id}/audit`, {
          params: {
            page: assetAuditPage,
            page_size: assetAuditPageSize,
            action: assetAuditFilters.action || undefined,
            operator: assetAuditFilters.operator || undefined,
            keyword: assetAuditFilters.keyword || undefined,
            date_from: assetAuditFilters.date_from || undefined,
            date_to: assetAuditFilters.date_to || undefined,
          },
        }),
      ]);
      if (!assetAuditRequestTracker.isCurrent(requestId)) return;
      const latest = (inventoryResult.data.items || []).find((item: SealAsset) => item.id === target.id);
      if (!latest) {
        clearAssetAudit();
        return;
      }
      setAssets((currentAssets) => mergeSealAssetSnapshot(currentAssets, latest));
      setAssetAuditAsset(latest);
      setAssetAuditRows(Array.isArray(auditResult.data.items) ? auditResult.data.items : []);
      setAssetAuditTotal(Number(auditResult.data.total) || 0);
      setAssetAuditPage(Number(auditResult.data.page) || assetAuditPage);
      setAssetAuditPageSize(Number(auditResult.data.page_size) || assetAuditPageSize);
    } catch (error: any) {
      if (!assetAuditRequestTracker.isCurrent(requestId)) return;
      message.error(
        sealErrorMessage(error, sealAssetAuditFailureMessage(error?.response?.status)),
      );
    } finally {
      if (assetAuditRequestTracker.isCurrent(requestId)) setAssetAuditLoading(false);
    }
  };
  const openAssetAudit = (asset: SealAsset) => {
    if (!canReadAssetAudit) return;
    assetAuditRequestTracker.invalidate();
    const filters = { action: "", operator: "", keyword: "", date_from: "", date_to: "" };
    const pageSize = sealAssetAuditPagination.defaultPageSize;
    setAssetAuditAsset(asset);
    setAssetAuditFilters(filters);
    setAssetAuditPage(1);
    setAssetAuditPageSize(pageSize);
    setAssetAuditOpen(true);
    void loadAssetAudit(asset.id, 1, pageSize, filters);
  };
  const openCaseDetail = async (caseNo: unknown) => {
    const serialNo = String(caseNo || "").trim();
    if (!serialNo || serialNo === "—") {
      message.warning("当前用印申请未关联案件");
      return;
    }
    try {
      const record = await resolveDetailRelation("case", { serial_no: serialNo });
      if (!record) return message.warning("未找到关联案件或当前账号无权查看");
      rememberCaseDetailTarget({ id: record.id, serial_no: record.serial_no });
      onNavigate?.("case-company");
    } catch (error: any) { message.error(error?.response?.data?.detail || "关联案件加载失败"); }
  };
  const openContractDetail = async (contractNo: unknown) => {
    const serialNo = String(contractNo || "").trim();
    if (!serialNo || serialNo === "—") {
      message.warning("当前用印申请未关联合同");
      return;
    }
    try {
      const record = await resolveDetailRelation("contract", { serial_no: serialNo });
      if (!record) return message.warning("未找到关联合同或当前账号无权查看");
      rememberContractDetailTarget({ id: record.id, serial_no: record.serial_no });
      onNavigate?.("contract-company");
    } catch (error: any) { message.error(error?.response?.data?.detail || "关联合同加载失败"); }
  };
  const openCustomerDetail = async (customer: unknown, customerNo?: unknown) => {
    const title = String(customer || "").trim();
    const serialNo = String(customerNo || "").trim();
    if (!title && !serialNo) return message.warning("当前申请未关联客户");
    try {
      const record = await resolveDetailRelation("customer", { title, serial_no: serialNo });
      if (!record) return message.warning("未找到关联客户或当前账号无权查看");
      rememberCustomerDetailTarget({ id: record.id, title: record.title, serial_no: record.serial_no });
      onNavigate?.("customer-company");
    } catch (error: any) { message.error(error?.response?.data?.detail || "关联客户加载失败"); }
  };
  useEffect(() => {
    setTab(tabFromView(initialView));
  }, [initialView]);
  useEffect(() => {
    setSelectedKeys([]);
  }, [initialView, tab, query]);
  useEffect(() => {
    load();
  }, [tab, initialView, query]);
  const availableAssets = useMemo(
    () => assets.filter((x) => x.status === "可用"),
    [assets],
  );
  const visibleRows = useMemo(() => {
    const statuses = statusFromView(initialView);
    let result = statuses.length
      ? rows.filter((row) => statuses.includes(row.status))
      : rows;
    const contains = (v: unknown, k: string) =>
      !query[k] || String(v || "").includes(String(query[k]).trim());
    const dates = query.application_date;
    return result.filter(
      (r) =>
        contains(r.serial_no, "serial_no") &&
        contains(r.owner, "applicant") &&
        contains(r.data.case_no, "case_no") &&
        contains(r.data.contract_no, "contract_no") &&
        contains(r.customer, "customer") &&
        contains(r.data.document_names, "file_name") &&
        (!query.use_type || String(r.data.use_type || "") === query.use_type) &&
        (!dates ||
          (r.created_at.slice(0, 10) >= dates[0].format("YYYY-MM-DD") &&
            r.created_at.slice(0, 10) <= dates[1].format("YYYY-MM-DD"))),
    );
  }, [rows, initialView, query]);
  const auditRows = useMemo(() => toSealAuditRows(history), [history]);
  const createApplication = async () => {
    let v: Record<string, any>;
    try {
      v = await createForm.validateFields();
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(
        error?.response?.data?.detail || error?.message || "申请保存失败",
      );
      return;
    }
    if (!actionGate.tryEnter()) {
      message.info("操作正在提交，请勿重复点击");
      return;
    }
    setActionSubmitting(true);
    try {
      const sourceAttachmentIds = Array.isArray(v.source_attachment_ids)
        ? v.source_attachment_ids
            .map((id) => Number(id))
            .filter((id) => Number.isFinite(id) && id > 0)
        : [];
      const data = {
        ...(editingApplication?.data || {}),
        ...v,
        customer: showSourceRelationFields ? v.customer : "",
        case_no: isCaseSeal ? v.case_no : "",
        contract_no: isContractSeal ? v.contract_no : "",
        source_attachment_ids: showSourceRelationFields ? sourceAttachmentIds : [],
        use_date: formatRequiredDate(v.use_date, "计划用印日期"),
      };
      const response = editingApplication
        ? await patchSeal(`/seals/applications/${editingApplication.id}`, data)
        : await postSeal("/seals/applications", data);
      ensureSealSuccess(response, "鐢宠淇濆瓨澶辫触");
      message.success(
        editingApplication ? "用印申请已修改" : "用印申请已保存为草稿",
      );
      setCreateOpen(false);
      setEditingApplication(null);
      createForm.resetFields();
      load();
    } catch (error: any) {
      message.error(
        error?.response?.data?.detail || error?.message || "申请保存失败",
      );
    } finally {
      actionGate.leave();
      setActionSubmitting(false);
    }
  };
  const openApplication = (row?: SealRow) => {
    setEditingApplication(row || null);
    setSourceAttachments([]);
    setSourceAttachmentLoading(false);
    setSourceAttachmentPage(1);
    setSourceAttachmentPageSize(sealFilePagination.defaultPageSize);
    setSourceAttachmentTotal(0);
    createForm.resetFields();
    createForm.setFieldsValue(
      row
        ? {
            ...row.data,
            title: row.title,
            customer: row.customer,
            description: row.description,
            use_date: dayjs(row.data.use_date),
          }
        : {
            use_date: dayjs().add(1, "day"),
            copies: 1,
            source_attachment_ids: [],
            delivery_method: "现场用印",
            is_electronic_seal: false,
            is_offline_print: false,
          },
    );
    setCreateOpen(true);
  };
  const submit = async (row: SealRow) => {
    if (!actionGate.tryEnter()) {
      message.info("操作正在提交，请勿重复点击");
      return;
    }
    setActionSubmitting(true);
    try {
      const response = await postSeal(`/seals/applications/${row.id}/submit`, {
        comment: "申请人确认材料无误并提交",
      });
      message.success("已提交用印审批");
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "提交失败");
    } finally {
      actionGate.leave();
      setActionSubmitting(false);
    }
  };
  const withdraw = async (row: SealRow) => {
    Modal.confirm({
      title: "撤回用印申请",
      content: `确认撤回 ${row.serial_no}？撤回后该申请将停止审批。`,
      okText: "确认撤回",
      cancelText: "取消",
      okButtonProps: { danger: true },
      async onOk() {
        if (!actionGate.tryEnter()) {
          message.info("操作正在提交，请勿重复点击");
          return;
        }
        setActionSubmitting(true);
        try {
          await postSeal(`/seals/applications/${row.id}/withdraw`, {
            comment: "申请人撤回待审批用印申请",
          });
          message.success("用印申请已撤回");
          load();
        } catch (error: any) {
          message.error(error?.response?.data?.detail || "撤回失败");
        } finally {
          actionGate.leave();
          setActionSubmitting(false);
        }
      },
    });
  };
  const batchWithdraw = async (selected: SealRow[]) => {
    if (!canBatchWithdrawSealRows(selected)) return;
    if (!actionGate.tryEnter()) {
      message.info("操作正在提交，请勿重复点击");
      return;
    }
    setActionSubmitting(true);
    try {
      await postSeal("/seals/applications/batch/withdraw", {
        application_ids: selected.map((row) => row.id),
        comment: "申请人批量撤回待审批用印申请",
      });
      message.success(`已撤回 ${selected.length} 条用印申请`);
      setSelectedKeys([]);
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "批量撤回失败");
    } finally {
      actionGate.leave();
      setActionSubmitting(false);
    }
  };
  const removeDraft = async (row: SealRow) => {
    Modal.confirm({
      title: "删除用印草稿",
      content: `确认删除草稿 ${row.serial_no}？仅无附件的草稿可删除。`,
      okText: "确认删除",
      cancelText: "取消",
      okButtonProps: { danger: true },
      async onOk() {
        try {
          await deleteSeal(`/seals/applications/${row.id}`);
          message.success("用印草稿已删除");
          setSelectedKeys((keys) => keys.filter((key) => key !== row.id));
          load();
        } catch (error: any) {
          message.error(error?.response?.data?.detail || "删除失败");
        }
      },
    });
  };
  const resetStampAttachmentState = () => {
    setStampAttachments([]);
    setStampAttachmentId(null);
    setStampAttachmentLoading(false);
    setStampAttachmentPage(1);
    setStampAttachmentPageSize(sealFilePagination.defaultPageSize);
    setStampAttachmentTotal(0);
    actionForm.setFieldValue("stamp_attachment_id", undefined);
  };
  const loadStampAttachments = async (
    row: SealRow,
    nextPage = 1,
    nextPageSize = sealFilePagination.defaultPageSize,
    append = false,
  ) => {
    setStampAttachmentLoading(true);
    try {
      const { data } = await api.get("/attachments", {
        params: {
          record_id: row.id,
          category: "用印文件",
          page: nextPage,
          page_size: nextPageSize,
        },
      });
      const items = Array.isArray(data.items) ? data.items : [];
      const total = Number(data.total ?? items.length);
      setStampAttachmentPage(Number(data.page) || nextPage);
      setStampAttachmentPageSize(Number(data.page_size) || nextPageSize);
      setStampAttachmentTotal(total);
      setStampAttachments((current) => {
        if (!append) return items;
        const seen = new Set(current.map((item) => Number(item.id)));
        return [
          ...current,
          ...items.filter((item: AttachmentRow) => !seen.has(Number(item.id))),
        ];
      });
      return { items, total };
    } catch (error: any) {
      setStampAttachments([]);
      setStampAttachmentTotal(0);
      message.error(
        sealErrorMessage(error, sealAttachmentListFailureMessage(error?.response?.status)),
      );
      return { items: [], total: 0 };
    } finally {
      setStampAttachmentLoading(false);
    }
  };
  const openStampAction = async (row: SealRow) => {
    setAction({ type: "stamp", row });
    resetStampAttachmentState();
    actionForm.setFieldsValue({
      actual_copies: row.data.copies,
      operator: "admin",
      stamp_attachment_id: undefined,
    });
    const { items, total } = await loadStampAttachments(row);
    if (items.length === 1 && total === 1) {
      setStampAttachmentId(items[0].id);
      actionForm.setFieldValue("stamp_attachment_id", items[0].id);
    }
  };
  const loadMoreStampAttachments = async () => {
    if (!action || action.type !== "stamp" || stampAttachmentLoading) return;
    if (stampAttachmentTotal > 0 && stampAttachments.length >= stampAttachmentTotal) return;
    await loadStampAttachments(
      action.row,
      stampAttachmentPage + 1,
      stampAttachmentPageSize,
      true,
    );
  };
  const uploadStampAttachment = async (file: File, row: SealRow): Promise<number | null> => {
    const validationError = validateSealUploadFile(file);
    if (validationError) {
      message.error(validationError);
      return null;
    }
    const body = new FormData();
    body.append("file", file);
    body.append("record_id", String(row.id));
    body.append("category", "用印文件");
    setStampAttachmentUploading(true);
    try {
      const response = await postSeal("/attachments", body);
      const uploadedStampAttachmentId = sealUploadedAttachmentId(response);
      if (!uploadedStampAttachmentId) {
        message.error("盖章附件上传失败：未返回附件标识");
        return null;
      }
      setStampAttachmentId(uploadedStampAttachmentId);
      actionForm.setFieldValue("stamp_attachment_id", uploadedStampAttachmentId);
      message.success("已上传盖章附件：" + file.name);
      await loadStampAttachments(row);
      return uploadedStampAttachmentId;
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "盖章附件上传失败");
      return null;
    } finally {
      setStampAttachmentUploading(false);
    }
  };
  const runAction = async () => {
    if (!action) return;
    const v = await actionForm.validateFields();
    let stampAttachmentForSubmit: number | null = null;
    if (action.type === "stamp") {
      if (stampAttachmentUploading) {
        message.info("盖章附件正在上传，请稍后确认");
        return;
      }
      stampAttachmentForSubmit = Number(v.stamp_attachment_id ?? stampAttachmentId);
      if (!Number.isFinite(stampAttachmentForSubmit) || stampAttachmentForSubmit <= 0) {
        message.error("请先选择或上传盖章附件");
        return;
      }
    }
    if (!actionGate.tryEnter()) {
      message.info("操作正在提交，请勿重复点击");
      return;
    }
    setActionSubmitting(true);
    try {
      if (action.type === "approve" || action.type === "reject")
        await postSeal(`/seals/applications/${action.row.id}/approve`, {
          approved: action.type === "approve",
          comment: v.comment || "",
        });
      else if (action.type === "stamp")
        await postSeal(`/seals/applications/${action.row.id}/stamp`, {
          ...v,
          stamp_attachment_id: stampAttachmentForSubmit,
        });
      else
        await postSeal(`/seals/applications/${action.row.id}/archive`, {
          comment: v.comment || "",
        });
      message.success(
        {
          approve: "审批已通过",
          reject: "申请已拒绝",
          stamp: "实际用印已登记",
          archive: "材料已归档",
        }[action.type],
      );
      setAction(null);
      resetStampAttachmentState();
      actionForm.resetFields();
      load();
      if (action.type === "stamp") void refreshAssetAudit();
    } catch (error: any) {
      message.error(
        error?.response?.data?.detail || sealActionFailureMessage(action.type),
      );
    } finally {
      actionGate.leave();
      setActionSubmitting(false);
    }
  };
  const runBatchStamp = async () => {
    const selected = selectedSealRows(visibleRows, selectedKeys);
    if (!canBatchStampSealRows(selected)) return;
    const values = await batchStampForm.validateFields();
    if (!actionGate.tryEnter()) {
      message.info("操作正在提交，请勿重复点击");
      return;
    }
    setActionSubmitting(true);
    try {
      await postSeal("/seals/applications/batch-stamp", {
        application_ids: selected.map((row) => row.id),
        ...values,
      });
      message.success(`已完成 ${selected.length} 条实际用印登记`);
      setBatchStampOpen(false);
      setSelectedKeys([]);
      batchStampForm.resetFields();
      load();
      void refreshAssetAudit();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "批量登记实际用印失败");
    } finally {
      actionGate.leave();
      setActionSubmitting(false);
    }
  };
  const loadDetailFiles = async (
    row: SealRow,
    nextPage = attachmentPage,
    nextPageSize = attachmentPageSize,
  ) => {
    const requestId = detailRequestTracker.next();
    try {
      const { data } = await api.get("/attachments", {
        params: {
          record_id: row.id,
          category: "用印文件",
          page: nextPage,
          page_size: nextPageSize,
        },
      });
      if (!detailRequestTracker.isCurrent(requestId)) return;
      const items = Array.isArray(data.items) ? data.items : [];
      setAttachmentPage(nextPage);
      setAttachmentPageSize(nextPageSize);
      setAttachmentTotal(Number(data.total ?? items.length));
      setAttachments(items);
      setAttachmentSelectedKeys([]);
    } catch (error: any) {
      if (!detailRequestTracker.isCurrent(requestId)) return;
      setAttachments([]);
      setAttachmentTotal(0);
      setAttachmentSelectedKeys([]);
      message.error(
        error?.response?.data?.detail ||
          sealAttachmentListFailureMessage(error?.response?.status),
      );
    }
  };
  const openDetail = async (row: SealRow) => {
    const requestId = detailRequestTracker.next();
    setDetail(row);
    setHistory([]);
    setAttachments([]);
    setAttachmentPage(1);
    setAttachmentPageSize(sealFilePagination.defaultPageSize);
    setAttachmentTotal(0);
    setAttachmentSelectedKeys([]);
    const [historyResult, filesResult] = await Promise.allSettled([
      api.get(`/records/${row.id}/history`),
      api.get("/attachments", {
        params: {
          record_id: row.id,
          category: "用印文件",
          page: 1,
          page_size: sealFilePagination.defaultPageSize,
        },
      }),
    ]);
    if (!detailRequestTracker.isCurrent(requestId)) return;
    if (historyResult.status === "fulfilled") {
      setHistory(historyResult.value.data.items || []);
    } else {
      setHistory([]);
      message.error(
        historyResult.reason?.response?.data?.detail ||
          sealQueryFailureMessage(historyResult.reason?.response?.status),
      );
    }
    if (filesResult.status === "fulfilled") {
      const items = Array.isArray(filesResult.value.data.items)
        ? filesResult.value.data.items
        : [];
      setAttachmentTotal(Number(filesResult.value.data.total ?? items.length));
      setAttachments(items);
    } else {
      setAttachments([]);
      setAttachmentTotal(0);
      message.error(
        filesResult.reason?.response?.data?.detail ||
          sealAttachmentListFailureMessage(filesResult.reason?.response?.status),
      );
    }
  };
  const openSealNumber = (row: SealRow) => {
    if (tab === "audit" && canSealAction("approve", row)) {
      setAction({ type: "approve", row });
      actionForm.resetFields();
      return;
    }
    void openDetail(row);
  };
  const openAuditList = async (row: SealRow) => {
    await openDetail(row);
    setAuditListOpen(true);
  };
  const downloadAttachment = async (item: AttachmentRow) => {
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
    } catch (error: any) {
      message.error(
        sealErrorMessage(error, sealAttachmentDownloadFailureMessage(error?.response?.status)),
      );
    }
  };
  const loadFileList = async (
    row: SealRow,
    nextPage = fileListPage,
    nextPageSize = fileListPageSize,
  ) => {
    const requestId = fileListRequestTracker.next();
    try {
      const { data } = await api.get("/attachments", {
        params: {
          record_id: row.id,
          category: "用印文件",
          page: nextPage,
          page_size: nextPageSize,
        },
      });
      if (!fileListRequestTracker.isCurrent(requestId)) return;
      setFileListRow(row);
      setFileListPage(nextPage);
      setFileListPageSize(nextPageSize);
      setFileListTotal(Number(data.total ?? (Array.isArray(data.items) ? data.items.length : 0)));
      setFileListAttachments(Array.isArray(data.items) ? data.items : []);
      setFileListOpen(true);
    } catch (error: any) {
      if (!fileListRequestTracker.isCurrent(requestId)) return;
      setFileListRow(null);
      setFileListAttachments([]);
      setFileListTotal(0);
      setFileListOpen(false);
      message.error(
        sealErrorMessage(error, sealAttachmentListFailureMessage(error?.response?.status)),
      );
    }
  };
  const openFileList = async (row: SealRow) => {
    setFileListRow(null);
    setFileListAttachments([]);
    setFileListPage(1);
    setFileListPageSize(sealFilePagination.defaultPageSize);
    setFileListTotal(0);
    setFileListOpen(false);
    await loadFileList(row, 1, sealFilePagination.defaultPageSize);
  };
  const previewAttachment = async (item: AttachmentRow) => {
    const requestId = previewRequestTracker.next();
    setPreviewOpen(false);
    setPreviewName("");
    setPreviewText("");
    setPreviewDetail("");
    setPreviewMode("unsupported");
    setPreviewUrl((previous) => {
      if (previous) URL.revokeObjectURL(previous);
      return "";
    });
    try {
      const { data } = await api.get(`/attachments/${item.id}/preview`);
      if (!previewRequestTracker.isCurrent(requestId)) return;
      const mode = getSealPreviewMode(data);
      setPreviewMode(mode);
      setPreviewText(data.text || "");
      setPreviewDetail(data.detail || "");
      setPreviewUrl((previous) => {
        if (previous) URL.revokeObjectURL(previous);
        return "";
      });
      if (mode === "binary") {
        const response = await api.get(`/attachments/${item.id}/download`, {
          responseType: "blob",
        });
        const url = URL.createObjectURL(response.data);
        if (!previewRequestTracker.isCurrent(requestId)) {
          URL.revokeObjectURL(url);
          return;
        }
        setPreviewUrl(url);
      }
      if (!previewRequestTracker.isCurrent(requestId)) return;
      setPreviewName(item.original_name);
      setPreviewOpen(true);
    } catch (error: any) {
      if (!previewRequestTracker.isCurrent(requestId)) return;
      message.error(
        sealErrorMessage(error, sealAttachmentPreviewFailureMessage(error?.response?.status)),
      );
    }
  };
  const previewListAttachmentByName = async (row: SealRow, fileName?: string) => {
    try {
      const { data } = await api.get("/attachments", {
        params: {
          record_id: row.id,
          category: "用印文件",
          page: 1,
          page_size: sealFilePagination.defaultPageSize,
        },
      });
      const items = Array.isArray(data.items) ? data.items : [];
      const target =
        items.find((item: AttachmentRow) => item.original_name === fileName) ||
        items.find((item: AttachmentRow) =>
          fileName
            ? item.original_name.includes(fileName) ||
              fileName.includes(item.original_name)
            : false,
        ) ||
        items[0];
      if (target) {
        await previewAttachment(target);
        return;
      }
      await openFileList(row);
    } catch {
      await openFileList(row);
    }
  };
  const uploadSealFiles = async (files: File[]) => {
    if (!detail) return;
    const validFiles = files.filter(Boolean);
    if (!validFiles.length) return;
    for (const file of validFiles) {
      const validationError = validateSealUploadFile(file);
      if (validationError) {
        message.error(validationError);
        return;
      }
    }
    const body = new FormData();
    validFiles.forEach((file) => body.append("files", file));
    try {
      await postSeal(`/seals/applications/${detail.id}/files`, body);
      message.success(`已上传用印文件：${validFiles.length} 个`);
      await loadDetailFiles(detail, 1, attachmentPageSize);
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "用印文件上传失败");
    }
  };
  const uploadSealFile = async (file: File) => {
    await uploadSealFiles([file]);
  };
  const removeSealFile = async (item: AttachmentRow) => {
    if (!actionGate.tryEnter()) {
      message.info("操作正在提交，请勿重复点击");
      return;
    }
    setActionSubmitting(true);
    try {
      await deleteSeal(`/attachments/${item.id}`);
      message.success("用印文件已删除");
      if (detail) await loadDetailFiles(detail, attachmentPage, attachmentPageSize);
      load();
    } catch (error: any) {
      message.error(
        error?.response?.data?.detail ||
          sealAttachmentDeleteFailureMessage(error?.response?.status),
      );
    } finally {
      actionGate.leave();
      setActionSubmitting(false);
    }
  };
  const removeSealFiles = async () => {
    if (!detail || !attachmentSelectedKeys.length) return;
    try {
      await postSeal("/seals/applications/batch/files/delete", {
        attachment_ids: attachmentSelectedKeys,
      });
      message.success(`已删除 ${attachmentSelectedKeys.length} 个用印文件`);
      setAttachmentSelectedKeys([]);
      await loadDetailFiles(detail, attachmentPage, attachmentPageSize);
      load();
    } catch (error: any) {
      message.error(
        error?.response?.data?.detail ||
          sealAttachmentDeleteFailureMessage(error?.response?.status),
      );
    }
  };
  useEffect(() => {
    const target = consumeBusinessRecordDetailTarget("seal");
    if (!target) return;
    void (async () => {
      try {
        const { data } = await api.get(`/records/${target.id}`);
        if (data.module !== "seal") throw new Error("关联记录不是用印申请");
        await openDetail(data);
      } catch (error: any) {
        message.error(
          error?.response?.data?.detail || error?.message || "用印详情加载失败",
        );
      }
    })();
  }, []);
  const packageDownload = async (selected: SealRow[]) => {
    if (!selected.length) {
      message.warning("请选择用印文件");
      return;
    }
    try {
      const res = await postSealBlob(
        "/seals/applications/package-download",
        { application_ids: selected.map((row) => row.id) },
        { responseType: "blob" },
      );
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `用印文件-${dayjs().format("YYYYMMDD")}.zip`;
      a.click();
      URL.revokeObjectURL(url);
      message.success(`已将 ${selected.length} 条用印申请的附件打包为 ZIP`);
    } catch (error: any) {
      if (error?.response?.data instanceof Blob) {
        try {
          const detail = JSON.parse(await error.response.data.text()).detail;
          message.error(detail || sealPackageDownloadFailureMessage(error?.response?.status));
          return;
        } catch {}
      }
      message.error(
        error?.response?.data?.detail ||
          sealPackageDownloadFailureMessage(error?.response?.status),
      );
    }
  };
  const saveAsset = async () => {
    let v: Record<string, any>;
    try {
      v = await assetForm.validateFields();
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(error?.message || "印章保存失败");
      return;
    }
    if (!actionGate.tryEnter()) {
      message.info("操作正在提交，请勿重复点击");
      return;
    }
    setActionSubmitting(true);
    try {
      if (editAsset) await patchSeal(`/seals/assets/${editAsset.id}`, v);
      else await postSeal("/seals/assets", v);
      message.success(editAsset ? "印章资料已更新" : "印章已入库");
      setAssetOpen(false);
      setEditAsset(null);
      assetForm.resetFields();
      load();
      void refreshAssetAudit();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "印章保存失败");
    } finally {
      actionGate.leave();
      setActionSubmitting(false);
    }
  };
  const removeAsset = async (item: SealAsset) => {
    if (!actionGate.tryEnter()) {
      message.info("操作正在提交，请勿重复点击");
      return;
    }
    setActionSubmitting(true);
    try {
      await deleteSeal(`/seals/assets/${item.id}`);
      message.success("印章资产已删除");
      void load();
      if (shouldCloseSealAssetAuditAfterDelete(item.id, assetAuditAsset?.id ?? null)) {
        clearAssetAudit();
      } else {
        void refreshAssetAudit();
      }
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "印章资产删除失败");
    } finally {
      actionGate.leave();
      setActionSubmitting(false);
    }
  };
  const openAsset = (item?: SealAsset) => {
    setEditAsset(item || null);
    assetForm.setFieldsValue(
      item || { seal_type: "公章", custodian: "admin", status: "可用" },
    );
    setAssetOpen(true);
  };
  const displayStatus = (v: string) =>
    sealStatusOptions.find((option) => option.value === v)?.label || v;
  const appColumns = [
    {
      title: "编号",
      dataIndex: "serial_no",
      width: 175,
      render: (v: string, r: SealRow) => (
        <Button type="link" onClick={() => openSealNumber(r)}>
          {v}
        </Button>
      ),
    },
    { title: "申请人", dataIndex: "owner", width: 90 },
    {
      title: "申请时间",
      dataIndex: "created_at",
      width: 110,
      sorter: (a: SealRow, b: SealRow) => compareSealDateValues(a.created_at, b.created_at),
      render: (v: string) => dayjs(v).format("YYYY-M-D"),
    },
    {
      title: "用印状态",
      dataIndex: "status",
      width: 105,
      render: (v: string) => (
        <Tag color={statusColors[v] || "blue"}>{displayStatus(v)}</Tag>
      ),
    },
    {
      title: "用印类型",
      width: 95,
      render: (_: unknown, r: SealRow) =>
        r.data.use_type ||
        (r.data.case_no
          ? "案件用印"
          : r.data.contract_no
            ? "合同用印"
            : "行政用印"),
    },
    {
      title: "印章类型",
      width: 130,
      render: (_: unknown, r: SealRow) =>
        r.seal_asset?.seal_type || r.data.seal_name || "—",
    },
    {
      title: "文件数",
      width: 145,
      dataIndex: "file_count",
      render: (value: number, r: SealRow) => {
        const names = listSealRowFileNames(r);
        const hasFiles = Number(value || 0) > 0 || names.length > 0;
        return (
          <Space size={4} wrap>
            <Button type="link" onClick={() => void openFileList(r)}>
              {value || 0}
            </Button>
            {hasFiles && (
              <Popover
                trigger="click"
                title="用印文件"
                content={
                  <Space direction="vertical" size={0}>
                    {names.length ? (
                      names.map((name) => (
                        <Button
                          key={name}
                          type="link"
                          size="small"
                          onClick={() => void previewListAttachmentByName(r, name)}
                        >
                          {name}
                        </Button>
                      ))
                    ) : (
                      <Button
                        type="link"
                        size="small"
                        onClick={() => void openFileList(r)}
                      >
                        打开文件列表
                      </Button>
                    )}
                    <Button
                      type="link"
                      size="small"
                      onClick={() => void openFileList(r)}
                    >
                      全部用印文件
                    </Button>
                  </Space>
                }
              >
                <Button type="link" size="small">
                  用印文件
                </Button>
              </Popover>
            )}
          </Space>
        );
      },
    },
    {
      title: "案号",
      width: 145,
      render: (_: unknown, r: SealRow) =>
        r.data.case_no ? (
          <Button type="link" onClick={() => openCaseDetail(r.data.case_no)}>
            {r.data.case_no}
          </Button>
        ) : (
          "—"
        ),
    },
    {
      title: "合同号",
      width: 145,
      render: (_: unknown, r: SealRow) =>
        r.data.contract_no ? (
          <Button
            type="link"
            onClick={() => openContractDetail(r.data.contract_no)}
          >
            {r.data.contract_no}
          </Button>
        ) : (
          "—"
        ),
    },
    { title: "客户", dataIndex: "customer", width: 190, ellipsis: true, render: (value: string, r: SealRow) => value ? <Button type="link" onClick={() => openCustomerDetail(value, r.data.customer_no)}>{value}</Button> : "—" },
    {
      title: "审核人",
      width: 90,
      render: (_: unknown, r: SealRow) => r.data.approver || "—",
    },
    {
      title: "审核时间",
      width: 110,
      sorter: (a: SealRow, b: SealRow) => compareSealDateValues(a.data.approved_at, b.data.approved_at),
      render: (_: unknown, r: SealRow) => r.data.approved_at || "—",
    },
    {
      title: "审核意见",
      width: 180,
      render: (_: unknown, r: SealRow) => r.data.approval_comment || "—",
    },
    {
      title: "",
      key: "actions",
      width: 260,
      render: (_: unknown, r: SealRow) => (
        <Space size={0}>
          <Button type="link" onClick={() => openDetail(r)}>
            查看
          </Button>
          <Button type="link" onClick={() => void openAuditList(r)}>
            审批流程
          </Button>
          {tab === "my" && r.status === "草稿" && (
            <>
              <Button type="link" onClick={() => submit(r)}>
                提交
              </Button>
              <Button danger type="link" onClick={() => void removeDraft(r)}>
                删除
              </Button>
            </>
          )}
          {tab === "audit" && canSealAction("approve", r) && (
            <>
              <Button
                type="link"
                onClick={() => {
                  setAction({ type: "approve", row: r });
                  actionForm.resetFields();
                }}
              >
                通过
              </Button>
              <Button
                danger
                type="link"
                onClick={() => {
                  setAction({ type: "reject", row: r });
                  actionForm.resetFields();
                }}
              >
                拒绝
              </Button>
            </>
          )}
          {tab === "admin" && canSealAction("archive", r) && (
            <Button
              type="link"
              onClick={() => {
                setAction({ type: "archive", row: r });
                actionForm.resetFields();
              }}
            >
              归档
            </Button>
          )}
        </Space>
      ),
    },
  ];
  const assetColumns = [
    { title: "印章编号", dataIndex: "code", width: 130 },
    { title: "印章名称", dataIndex: "name", width: 240 },
    {
      title: "类别",
      dataIndex: "seal_type",
      width: 160,
      render: (value: string) => value || "—",
    },
    { title: "保管人", dataIndex: "custodian", width: 100 },
    { title: "存放位置", dataIndex: "location", width: 190 },
    {
      title: "累计用印",
      dataIndex: "usage_count",
      width: 95,
      render: (v: number) => `${v} 份`,
    },
    {
      title: "最近使用",
      dataIndex: "last_used_at",
      width: 160,
      render: (v: string) => (v ? dayjs(v).format("YYYY-MM-DD HH:mm") : "—"),
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 85,
      render: (v: string) => <Tag color={assetColors[v] || "blue"}>{v}</Tag>,
    },
    {
      title: "操作",
      width: 150,
      fixed: "right" as const,
      render: (_: unknown, r: SealAsset) => (
        <Space size={0}>
          {canReadAssetAudit && (
            <Button type="link" onClick={() => openAssetAudit(r)}>
              审计
            </Button>
          )}
          <Button type="link" onClick={() => openAsset(r)}>
            维护
          </Button>
          <Popconfirm
            title="确认删除这枚未被用印申请引用的印章？"
            description="已被任何用印申请引用的印章将被系统阻断删除。"
            okText="确认删除"
            cancelText="取消"
            onConfirm={() => void removeAsset(r)}
          >
            <Button danger type="link" icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];
  const selectedRows = selectedSealRows(visibleRows, selectedKeys);
  const selectedRow = selectedRows.length === 1 ? selectedRows[0] : null;
  const routeStatuses = statusFromView(initialView);
  const routeStatus =
    initialView === "seal-my-withdrawn"
      ? ""
      : routeStatuses.length === 1
        ? routeStatuses[0]
        : initialView === "seal-my-pending"
          ? "待审批"
          : initialView === "seal-my-used"
          ? "已用印"
          : "";
  const statusLocked = initialView !== "seal-admin-query";
  const tabItems = [
    { key: "my", label: "我的申请" },
    { key: "audit", label: `用印审批（${summary.pending}）` },
    { key: "admin", label: `行政用印（${summary.waiting_stamp}）` },
    { key: "assets", label: "印章管理" },
  ];
  return (
    <>
      <div className="seal-stats">
        <Card>
          <Statistic title="全部申请" value={summary.total} />
        </Card>
        <Card>
          <Statistic
            title="待审批"
            value={summary.pending}
            styles={{ content: { color: "#f39c12" } }}
          />
        </Card>
        <Card>
          <Statistic
            title="待用印"
            value={summary.waiting_stamp}
            styles={{ content: { color: "#3c8dbc" } }}
          />
        </Card>
        <Card>
          <Statistic
            title="已完成"
            value={summary.completed}
            styles={{ content: { color: "#00a65a" } }}
          />
        </Card>
      </div>
      <Card
        className="panel seal-original-panel"
        title={tab === "assets" ? "印章资产管理" : "用印申请列表"}
      >
        {tab !== "assets" && (
          <Form form={queryForm} className="seal-query" onFinish={setQuery}>
            <Form.Item label="申请编号" name="serial_no">
              <Input />
            </Form.Item>
            <Form.Item label="申请人" name="applicant">
              <Input />
            </Form.Item>
            <Form.Item label="申请日期" name="application_date">
              <DatePicker.RangePicker />
            </Form.Item>
            <Form.Item label="案件编号" name="case_no">
              <Input />
            </Form.Item>
            <Form.Item label="合同编号" name="contract_no">
              <Input />
            </Form.Item>
            <Form.Item label="客户名称" name="customer">
              <Input />
            </Form.Item>
            <Form.Item
              label="用印状态"
              name={statusLocked ? undefined : "record_status"}
            >
              <Select
                allowClear={!statusLocked}
                disabled={statusLocked}
                value={statusLocked ? routeStatus || undefined : undefined}
                placeholder="请选择"
                options={sealStatusOptions}
              />
            </Form.Item>
            <Form.Item label="用印类型" name="use_type">
              <Select
                allowClear
                placeholder="请选择"
                options={["合同用印", "案件用印", "行政用印"].map((value) => ({
                  value,
                  label: value,
                }))}
              />
            </Form.Item>
            <Form.Item label="文件名称" name="file_name">
              <Input />
            </Form.Item>
            <div className="seal-query-actions">
              <Button type="primary" htmlType="submit">
                查询
              </Button>
              <Button onClick={clearQuery}>清空</Button>
            </div>
          </Form>
        )}
        <Tabs
          className="seal-original-tabs"
          activeKey={tab}
          onChange={setTab}
          items={tabItems}
        />
        {tab === "assets" ? (
          <>
            <div className="seal-asset-toolbar">
              <span>印章资产台账</span>
              <Space>
                <Input
                  allowClear
                  value={keyword}
                  onChange={(event) => setKeyword(event.target.value)}
                  onPressEnter={load}
                  placeholder="编号、名称、类别或保管人"
                />
                <Button icon={<ReloadOutlined />} onClick={load}>
                  刷新
                </Button>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => openAsset()}
                >
                  新增印章
                </Button>
              </Space>
            </div>
            <Table
              rowKey="id"
              loading={loading}
              size="small"
              columns={assetColumns.map((column: any) =>
                column.title === "操作"
                  ? { ...column, fixed: undefined }
                  : column,
              )}
              dataSource={assets}
              scroll={{ x: 1240 }}
              pagination={{ pageSize: 20, showTotal: (n) => `共 ${n} 枚印章` }}
              locale={{ emptyText: "暂无印章资产，请由管理员新增入库" }}
            />
          </>
        ) : (
          <Table
            rowKey="id"
            loading={loading}
            size="small"
            rowSelection={{
              selectedRowKeys: selectedKeys,
              onChange: (keys) => setSelectedKeys(keys as (string | number)[]),
            }}
            columns={appColumns}
            dataSource={visibleRows}
            scroll={{ x: 1850 }}
            pagination={
              [
                "seal-my-pending",
                "seal-audit-pending",
                "seal-audit-stamping",
                "seal-audit-refused",
                "seal-admin-pending",
                "seal-admin-used",
                "seal-admin-query",
              ].includes(
                initialView,
              )
                ? {
                    defaultPageSize: 15,
                    showSizeChanger: true,
                    showQuickJumper:
                      initialView === "seal-my-pending"
                        ? { goButton: "GO" }
                        : true,
                    pageSizeOptions: [10, 15, 20, 50, 100, 200],
                    showTotal: (n) => `共 ${n} 条记录`,
                  }
                : { pageSize: 20, showTotal: (n) => `共 ${n} 条记录` }
            }
            locale={{
              emptyText:
                initialView === "seal-my-pending" ? (
                  <span>
                    没有查询到符合条件的记录，可以去{" "}
                    <Button
                      className="seal-empty-link"
                      type="link"
                      onClick={() => openApplication()}
                    >
                      申请用印
                    </Button>
                    。
                  </span>
                ) : (
                  "没有查询到符合条件的记录。"
                ),
            }}
            footer={
              visibleRows.length &&
              [
                "seal-my-pending",
                "seal-my-stamping",
                "seal-admin-pending",
              ].includes(initialView)
                ? () => (
                    <div className="seal-table-actions">
                      {initialView === "seal-my-pending" &&
                        visibleRows.length <= 15 && (
                          <Space size={4} aria-label="分页跳转">
                            <InputNumber
                              aria-label="跳转页码"
                              min={1}
                              max={1}
                              defaultValue={1}
                              controls={false}
                              size="small"
                              style={{ width: 52 }}
                            />
                            <Button size="small">GO</Button>
                          </Space>
                        )}
                      {initialView === "seal-my-pending" && (
                        <>
                          <Button onClick={() => openApplication()}>
                            申请用印
                          </Button>
                          <Button
                            disabled={
                              !selectedRow || selectedRow.status !== "草稿"
                            }
                            onClick={() =>
                              selectedRow && openApplication(selectedRow)
                            }
                          >
                            修改
                          </Button>
                          <Button
                            disabled={
                              !selectedRow || selectedRow.status !== "草稿"
                            }
                            onClick={() => selectedRow && submit(selectedRow)}
                          >
                            提交
                          </Button>
                          <Button
                            disabled={!canBatchWithdrawSealRows(selectedRows)}
                            onClick={() =>
                              selectedRows.length > 1
                                ? void batchWithdraw(selectedRows)
                                : selectedRow && void withdraw(selectedRow)
                            }
                          >
                            撤回
                          </Button>
                        </>
                      )}
                      {initialView === "seal-my-stamping" && (
                        <Button
                          disabled={!canBatchWithdrawSealRows(selectedRows)}
                          onClick={() =>
                            selectedRows.length > 1
                              ? void batchWithdraw(selectedRows)
                              : selectedRow && void withdraw(selectedRow)
                          }
                        >
                          撤回
                        </Button>
                      )}
                      {initialView === "seal-admin-pending" && (
                        <>
                          <Button
                            disabled={!canBatchStampSealRows(selectedRows)}
                            onClick={() => {
                              if (selectedRows.length === 1 && selectedRow) {
                                setAction({ type: "stamp", row: selectedRow });
                                void openStampAction(selectedRow);
                              } else if (selectedRows.length > 1) {
                                batchStampForm.setFieldsValue({
                                  actual_copies: Math.min(
                                    ...selectedRows.map((row) => Number(row.data.copies) || 0),
                                  ),
                                  operator: "admin",
                                });
                                setBatchStampOpen(true);
                              }
                            }}
                          >
                            标记用印
                          </Button>
                          <Button
                            disabled={!selectedRows.length}
                            onClick={() => packageDownload(selectedRows)}
                          >
                            打包下载
                          </Button>
                        </>
                      )}
                    </div>
                  )
                : undefined
            }
          />
        )}
      </Card>
      <Modal
        open={createOpen}
        title={editingApplication ? "修改用印申请" : "申请用印"}
        width={760}
        okText="保存草稿"
        cancelText="取消"
        confirmLoading={actionSubmitting}
        onOk={createApplication}
        onCancel={() => {
          setCreateOpen(false);
          setEditingApplication(null);
          setSourceAttachments([]);
          setSourceAttachmentPage(1);
          setSourceAttachmentPageSize(sealFilePagination.defaultPageSize);
          setSourceAttachmentTotal(0);
          createForm.setFieldValue("source_attachment_ids", []);
        }}
      >
        <Form form={createForm} layout="vertical">
          <div className="seal-form-grid">
            <Form.Item
              label="申请标题"
              name="title"
              rules={[{ required: true }]}
            >
              <Input placeholder="例如：民事起诉状用印" />
            </Form.Item>
            <Form.Item
              label="用印类型"
              name="use_type"
              rules={[{ required: true }]}
            >
              <Select
                onChange={handleUseTypeChange}
                options={["合同用印", "案件用印", "行政用印"].map((x) => ({
                  value: x,
                  label: x,
                }))}
              />
            </Form.Item>
            {showSourceRelationFields && (
              <Form.Item label="客户/单位" name="customer" preserve={false}>
                <Select
                  showSearch
                  allowClear
                  optionFilterProp="label"
                  options={customers.map((x) => ({
                    value: x.title || x.customer,
                    label: `${x.title || x.customer}｜${x.serial_no}`,
                  }))}
                />
              </Form.Item>
            )}
            {isCaseSeal && (
              <Form.Item
                label="关联案号"
                name="case_no"
                preserve={false}
                rules={[{ required: true, message: "案件用印必须选择关联案件" }]}
              >
                <Select
                  showSearch
                  allowClear
                  optionFilterProp="label"
                  options={cases.map((x) => ({
                    value: x.serial_no,
                    label: `${x.serial_no}｜${x.title}`,
                  }))}
                />
              </Form.Item>
            )}
            {isContractSeal && (
              <Form.Item
                label="关联合同号"
                name="contract_no"
                preserve={false}
                rules={[{ required: true, message: "合同用印必须选择关联合同" }]}
              >
                <Select
                  showSearch
                  allowClear
                  optionFilterProp="label"
                  options={contracts.map((x) => ({
                    value: x.serial_no,
                    label: `${x.serial_no}｜${x.customer}｜${x.title}`,
                  }))}
                />
              </Form.Item>
            )}
            {showSourceRelationFields && (
              <Form.Item
                label="来源附件"
                name="source_attachment_ids"
                preserve={false}
              >
                <Select
                  mode="multiple"
                  allowClear
                  loading={sourceAttachmentLoading}
                  placeholder={
                    selectedSourceRecord
                      ? "选择合同/案件来源附件"
                      : "请先选择关联合同或案件"
                  }
                  options={sourceAttachments.map((file) => ({
                    value: file.id,
                    label: `${file.original_name}｜${formatSealAttachmentSize(file.size)}`,
                  }))}
                  dropdownRender={(menu) => (
                    <>
                      {menu}
                      {selectedSourceRecord &&
                        sourceAttachmentTotal > sourceAttachments.length && (
                          <div style={{ padding: 8, textAlign: "center" }}>
                            <Button
                              type="link"
                              size="small"
                              loading={sourceAttachmentLoading}
                              onMouseDown={(event) => event.preventDefault()}
                              onClick={() => void loadMoreSourceAttachments()}
                            >
                              加载更多来源附件（{sourceAttachments.length}/{sourceAttachmentTotal}）
                            </Button>
                          </div>
                        )}
                    </>
                  )}
                />
              </Form.Item>
            )}
            <Form.Item
              label="选择印章"
              name="seal_asset_id"
              rules={[{ required: true }]}
            >
              <Select
                options={availableAssets.map((x) => ({
                  value: x.id,
                  label: `${x.name}（${x.code}）`,
                }))}
              />
            </Form.Item>
            <Form.Item
              label="计划用印日期"
              name="use_date"
              rules={[{ required: true }]}
            >
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item
              label="用印份数"
              name="copies"
              rules={[{ required: true }]}
            >
              <InputNumber min={1} max={999} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item label="办理方式" name="delivery_method">
              <Select
                options={["现场用印", "邮寄用印", "外带用印"].map((x) => ({
                  value: x,
                  label: x,
                }))}
              />
            </Form.Item>
            <Form.Item label="是否电子印章" name="is_electronic_seal">
              <Select
                options={[
                  { value: true, label: "是" },
                  { value: false, label: "否" },
                ]}
              />
            </Form.Item>
            <Form.Item label="是否打印盖章" name="is_offline_print">
              <Select
                options={[
                  { value: true, label: "需要" },
                  { value: false, label: "不需要" },
                ]}
              />
            </Form.Item>
          </div>
          <Alert
            type="info"
            showIcon
            title="请先保存草稿，再在用印详情中上传真实用印文件；未上传文件不能提交审批。"
            style={{ marginBottom: 12 }}
          />
          <Form.Item
            label="用印用途"
            name="purpose"
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label="申请说明" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={assetOpen}
        title={editAsset ? "维护印章资料" : "新增印章入库"}
        okText="保存"
        cancelText="取消"
        confirmLoading={actionSubmitting}
        onOk={saveAsset}
        onCancel={() => setAssetOpen(false)}
      >
        <Form form={assetForm} layout="vertical">
          <Form.Item label="印章编号" name="code" rules={[{ required: true }]}>
            <Input disabled={Boolean(editAsset)} />
          </Form.Item>
          <Form.Item label="印章名称" name="name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <div className="seal-form-grid">
            <Form.Item
              label="印章类别"
              name="seal_type"
              rules={[{ required: true }]}
            >
              <Select
                options={sealTypes.map((x) => ({ value: x, label: x }))}
              />
            </Form.Item>
            <Form.Item
              label="保管人"
              name="custodian"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <Form.Item label="存放位置" name="location">
              <Input />
            </Form.Item>
            {editAsset && (
              <Form.Item label="状态" name="status">
                <Select
                  options={["可用", "停用", "维修", "遗失"].map((x) => ({
                    value: x,
                    label: x,
                  }))}
                />
              </Form.Item>
            )}
          </div>
          <Form.Item label="备注" name="remark">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={assetAuditOpen && canReadAssetAudit}
        width={920}
        title={assetAuditAsset ? `印章详情与审计：${assetAuditAsset.name}（${assetAuditAsset.code}）` : "印章详情与审计"}
        footer={<Button onClick={clearAssetAudit}>关闭</Button>}
        onCancel={clearAssetAudit}
      >
        {assetAuditAsset && (
          <>
            <Descriptions
              bordered
              size="small"
              column={3}
              items={[
                { key: "code", label: "印章编号", children: assetAuditAsset.code },
                { key: "name", label: "印章名称", children: assetAuditAsset.name },
                { key: "type", label: "印章类别", children: assetAuditAsset.seal_type },
                { key: "custodian", label: "保管人", children: assetAuditAsset.custodian },
                { key: "location", label: "存放位置", children: assetAuditAsset.location || "—" },
                { key: "status", label: "状态", children: <Tag color={assetColors[assetAuditAsset.status] || "blue"}>{assetAuditAsset.status}</Tag> },
                { key: "usage", label: "累计用印", children: `${assetAuditAsset.usage_count} 份` },
                { key: "last_used", label: "最近使用", children: assetAuditAsset.last_used_at ? dayjs(assetAuditAsset.last_used_at).format("YYYY-MM-DD HH:mm") : "—" },
                { key: "remark", label: "备注", children: assetAuditAsset.remark || "—", span: 3 },
              ]}
            />
            <Space wrap style={{ margin: "12px 0" }}>
              <Input
                placeholder="动作"
                value={assetAuditFilters.action}
                onChange={(event) => setAssetAuditFilters((current) => ({ ...current, action: event.target.value }))}
                style={{ width: 150 }}
              />
              <Input
                placeholder="操作人"
                value={assetAuditFilters.operator}
                onChange={(event) => setAssetAuditFilters((current) => ({ ...current, operator: event.target.value }))}
                style={{ width: 130 }}
              />
              <Input
                placeholder="关键词（动作/操作人/备注）"
                value={assetAuditFilters.keyword}
                onChange={(event) => setAssetAuditFilters((current) => ({ ...current, keyword: event.target.value }))}
                style={{ width: 220 }}
              />
              <DatePicker.RangePicker
                value={assetAuditFilters.date_from && assetAuditFilters.date_to ? [dayjs(assetAuditFilters.date_from), dayjs(assetAuditFilters.date_to)] : null}
                onChange={(values) => setAssetAuditFilters((current) => ({ ...current, date_from: values?.[0]?.format("YYYY-MM-DD") || "", date_to: values?.[1]?.format("YYYY-MM-DD") || "" }))}
              />
              <Button type="primary" onClick={() => { setAssetAuditPage(1); if (assetAuditAsset) void loadAssetAudit(assetAuditAsset.id, 1, assetAuditPageSize, assetAuditFilters); }}>查询</Button>
              <Button onClick={() => { const filters = { action: "", operator: "", keyword: "", date_from: "", date_to: "" }; setAssetAuditFilters(filters); setAssetAuditPage(1); if (assetAuditAsset) void loadAssetAudit(assetAuditAsset.id, 1, assetAuditPageSize, filters); }}>清空</Button>
            </Space>
            <Table
              rowKey="id"
              size="small"
              loading={assetAuditLoading}
              dataSource={assetAuditRows}
              locale={{ emptyText: "暂无审计记录" }}
              columns={[
                { title: "动作", dataIndex: "action", width: 150 },
                { title: "操作人", dataIndex: "operator", width: 110 },
                { title: "备注", dataIndex: "comment", ellipsis: true },
                { title: "时间", dataIndex: "created_at", width: 170, render: (value: string) => dayjs(value).format("YYYY-MM-DD HH:mm:ss") },
              ]}
              pagination={{
                current: assetAuditPage,
                pageSize: assetAuditPageSize,
                total: assetAuditTotal,
                showSizeChanger: sealAssetAuditPagination.showSizeChanger,
                pageSizeOptions: sealAssetAuditPagination.pageSizeOptions.map(String),
                showQuickJumper: sealAssetAuditPagination.showQuickJumper,
                showTotal: sealAssetAuditPagination.showTotal,
                onChange: (page, pageSize) => {
                  setAssetAuditPage(page);
                  setAssetAuditPageSize(pageSize);
                  if (assetAuditAsset) void loadAssetAudit(assetAuditAsset.id, page, pageSize);
                },
              }}
            />
          </>
        )}
      </Modal>
      <Modal
        open={Boolean(action)}
        title={
          {
            approve: "审批通过",
            reject: "审批拒绝",
            stamp: "登记实际用印",
            archive: "归档用印材料",
          }[action?.type || "approve"]
        }
        okText="确认"
        cancelText="取消"
        confirmLoading={actionSubmitting}
        onOk={runAction}
        onCancel={() => {
          setAction(null);
          resetStampAttachmentState();
        }}
      >
        <Form form={actionForm} layout="vertical">
          {action?.type === "stamp" && (
            <>
              <Form.Item
                label="实际用印份数"
                name="actual_copies"
                rules={[{ required: true }]}
              >
                <InputNumber
                  min={1}
                  max={action.row.data.copies}
                  style={{ width: "100%" }}
                />
              </Form.Item>
              <Form.Item
                label="用印操作人"
                name="operator"
                rules={[{ required: true }]}
              >
                <Input />
              </Form.Item>
              <Form.Item
                label="归档号"
                name="archive_no"
                rules={[{ required: true }]}
              >
                <Input placeholder="例如：YY-2026-0042" />
              </Form.Item>
              <Form.Item
                label="盖章附件"
                name="stamp_attachment_id"
                rules={[{ required: true, message: "请先选择或上传盖章附件" }]}
              >
                <Select
                  allowClear
                  loading={stampAttachmentLoading || stampAttachmentUploading}
                  placeholder="选择已上传盖章附件"
                  options={stampAttachments.map((file) => ({
                    value: file.id,
                    label: file.original_name + "｜" + file.uploader,
                  }))}
                  onChange={(value) => setStampAttachmentId(Number(value) || null)}
                  dropdownRender={(menu) => (
                    <>
                      {menu}
                      {stampAttachmentTotal > stampAttachments.length && (
                        <div style={{ padding: 8, textAlign: "center" }}>
                          <Button
                            type="link"
                            size="small"
                            loading={stampAttachmentLoading}
                            onMouseDown={(event) => event.preventDefault()}
                            onClick={() => void loadMoreStampAttachments()}
                          >
                            加载更多盖章附件（{stampAttachments.length}/{stampAttachmentTotal}）
                          </Button>
                        </div>
                      )}
                    </>
                  )}
                />
              </Form.Item>
              <Upload
                showUploadList={false}
                beforeUpload={(file) => {
                  const row = action?.type === "stamp" ? action.row : null;
                  if (!row) return Upload.LIST_IGNORE;
                  void uploadStampAttachment(file as File, row);
                  return Upload.LIST_IGNORE;
                }}
              >
                <Button icon={<UploadOutlined />} loading={stampAttachmentUploading}>
                  上传盖章附件
                </Button>
              </Upload>
            </>
          )}
          <Form.Item
            label="审批/操作意见"
            name="comment"
            rules={
              action?.type === "reject"
                ? [{ required: true, message: "拒绝时必须填写原因" }]
                : []
            }
          >
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={batchStampOpen}
        title="批量登记实际用印"
        okText="确认"
        cancelText="取消"
        confirmLoading={actionSubmitting}
        onOk={runBatchStamp}
        onCancel={() => {
          setBatchStampOpen(false);
          batchStampForm.resetFields();
        }}
      >
        <Form form={batchStampForm} layout="vertical">
          <Form.Item
            label="实际用印份数"
            name="actual_copies"
            rules={[{ required: true }]}
          >
            <InputNumber min={1} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item
            label="用印操作人"
            name="operator"
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="归档号"
            name="archive_no"
            rules={[{ required: true }]}
          >
            <Input placeholder="例如：YY-2026-0042" />
          </Form.Item>
          <Form.Item label="审批/操作意见" name="comment">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Drawer
        open={Boolean(detail)}
        size={640}
        title={`用印详情：${detail?.serial_no || ""}`}
        onClose={() => {
          detailRequestTracker.invalidate();
          setDetail(null);
          setHistory([]);
          setAttachments([]);
          setAttachmentPage(1);
          setAttachmentPageSize(sealFilePagination.defaultPageSize);
          setAttachmentTotal(0);
          setAttachmentSelectedKeys([]);
        }}
      >
        {detail && (
          <>
            <Descriptions
              bordered
              size="small"
              column={2}
              items={[
                {
                  key: "title",
                  label: "申请标题",
                  children: detail.title,
                  span: 2,
                },
                {
                  key: "customer",
                  label: "客户",
                  children: detail.customer ? <Button type="link" onClick={() => openCustomerDetail(detail.customer, detail.data.customer_no)}>{detail.customer}</Button> : "—",
                },
                {
                  key: "customer_no",
                  label: "\u5ba2\u6237\u7f16\u53f7",
                  children: detail.data.customer_no || "—",
                },
                {
                  key: "use_type",
                  label: "\u7528\u5370\u7c7b\u578b",
                  children: detail.data.use_type || "—",
                },
                {
                  key: "case",
                  label: "关联案号",
                  children: detail.data.case_no ? (
                    <Button
                      type="link"
                      onClick={() => openCaseDetail(detail.data.case_no)}
                    >
                      {detail.data.case_no}
                    </Button>
                  ) : (
                    "—"
                  ),
                },
                {
                  key: "contract",
                  label: "关联合同号",
                  children: detail.data.contract_no ? (
                    <Button
                      type="link"
                      onClick={() =>
                        openContractDetail(detail.data.contract_no)
                      }
                    >
                      {detail.data.contract_no}
                    </Button>
                  ) : (
                    "—"
                  ),
                },
                {
                  key: "seal",
                  label: "印章",
                  children: detail.seal_asset?.name || detail.data.seal_name,
                },
                {
                  key: "copies",
                  label: "申请份数",
                  children: detail.data.copies,
                },
                {
                  key: "print_quantity",
                  label: "\u76d6\u7ae0\u4efd\u6570",
                  children: detail.data.print_quantity ?? detail.data.copies ?? "—",
                },
                {
                  key: "electronic",
                  label: "电子印章",
                  children: detail.data.is_electronic_seal ? "是" : "否",
                },
                {
                  key: "print",
                  label: "打印盖章",
                  children: detail.data.is_offline_print ? "需要" : "不需要",
                },
                {
                  key: "purpose",
                  label: "用途",
                  children: detail.data.purpose,
                  span: 2,
                },
                {
                  key: "remark",
                  label: "\u7528\u5370\u5907\u6ce8",
                  children: detail.data.remark || detail.description || "—",
                  span: 2,
                },
                {
                  key: "method",
                  label: "办理方式",
                  children: detail.data.delivery_method,
                },
                {
                  key: "date",
                  label: "计划日期",
                  children: detail.data.use_date,
                },
                {
                  key: "actual",
                  label: "实际份数",
                  children: detail.data.actual_copies || "—",
                },
                {
                  key: "archive",
                  label: "归档号",
                  children: detail.data.archive_no || "—",
                },
                {
                  key: "status",
                  label: "当前状态",
                  children: (
                    <Tag color={statusColors[detail.status]}>
                      {detail.status}
                    </Tag>
                  ),
                },
                { key: "owner", label: "申请人", children: detail.owner },
              ]}
            />
            <h3 className="seal-history-title">
              <FileDoneOutlined /> 用印文件
            </h3>
            {detail.status === "草稿" && (
              <Space>
                <Upload
                  multiple
                  showUploadList={false}
                  beforeUpload={(file, fileList) => {
                    const firstFile = fileList[0] as File & { uid?: string };
                    const currentFile = file as File & { uid?: string };
                    if (!firstFile || firstFile.uid === currentFile.uid || firstFile === currentFile) {
                      void uploadSealFiles(fileList as File[]);
                    }
                    return Upload.LIST_IGNORE;
                  }}
                >
                  <Button icon={<UploadOutlined />}>上传用印文件</Button>
                </Upload>
                <Button
                  danger
                  disabled={
                    !canBatchDeleteSealFiles(
                      detail.status,
                      attachmentSelectedKeys,
                    )
                  }
                  onClick={() => void removeSealFiles()}
                >
                  批量删除
                </Button>
              </Space>
            )}
            <Table
              size="small"
              rowKey="id"
              style={{ marginTop: 10 }}
              rowSelection={
                detail.status === "草稿"
                  ? {
                      selectedRowKeys: attachmentSelectedKeys,
                      onChange: (keys) =>
                        setAttachmentSelectedKeys(keys as number[]),
                    }
                  : undefined
              }
              pagination={{
                current: attachmentPage,
                pageSize: attachmentPageSize,
                total: attachmentTotal,
                showSizeChanger: sealFilePagination.showSizeChanger,
                pageSizeOptions: sealFilePagination.pageSizeOptions.map(String),
                showQuickJumper: sealFilePagination.showQuickJumper,
                showTotal: sealFilePagination.showTotal,
                onChange: (page, pageSize) => {
                  if (detail) void loadDetailFiles(detail, page, pageSize);
                },
              }}
              locale={{
                emptyText: "暂无用印文件；提交审批前请上传至少一个文件",
              }}
              dataSource={attachments}
              columns={[
                {
                  title: "文件名称",
                  dataIndex: "original_name",
                  ellipsis: true,
                },
                {
                  title: "类型",
                  width: 70,
                  render: (_: unknown, item: AttachmentRow) =>
                    getSealAttachmentExtension(item.original_name) || "—",
                },
                {
                  title: "大小",
                  width: 90,
                  dataIndex: "size",
                  render: (value: number) => formatSealAttachmentSize(value),
                },
                { title: "上传人", dataIndex: "uploader", width: 90 },
                {
                  title: "上传时间",
                  dataIndex: "created_at",
                  width: 145,
                  render: (value: string) =>
                    dayjs(value).format("YYYY-MM-DD HH:mm"),
                },
                {
                  title: "操作",
                  width: 130,
                  render: (_: unknown, item: AttachmentRow) => (
                    <Space size={0}>
                      <Button
                        type="link"
                        onClick={() => void previewAttachment(item)}
                      >
                        预览
                      </Button>
                      <Button
                        type="link"
                        icon={<DownloadOutlined />}
                        onClick={() => void downloadAttachment(item)}
                      >
                        下载
                      </Button>
                      {detail.status === "草稿" && (
                        <Button
                          type="link"
                          danger
                          onClick={() => void removeSealFile(item)}
                        >
                          删除
                        </Button>
                      )}
                    </Space>
                  ),
                },
              ]}
            />
            <h3 className="seal-history-title">
              <FileDoneOutlined /> 流程记录
            </h3>
            <Button type="link" onClick={() => setAuditListOpen(true)}>
              审核记录
            </Button>
            <Timeline
              items={history.map((x) => ({
                color: x.to_status === "已拒绝" ? "red" : "green",
                children: (
                  <div>
                    <b>{x.action}</b>{" "}
                    <Tag>
                      {x.from_status || "创建"} → {x.to_status}
                    </Tag>
                    <div>
                      {x.operator} ·{" "}
                      {dayjs(x.created_at).format("YYYY-MM-DD HH:mm")}
                    </div>
                    {x.comment && <small>{x.comment}</small>}
                  </div>
                ),
              }))}
            />
          </>
        )}
      </Drawer>
      <Modal
        open={auditListOpen}
        title="审批流程"
        footer={<Button onClick={() => setAuditListOpen(false)}>关闭</Button>}
        onCancel={() => setAuditListOpen(false)}
      >
        <Table
          size="small"
          rowKey="id"
          pagination={false}
          locale={{ emptyText: "" }}
          dataSource={auditRows}
          columns={[
            { title: "审批人", dataIndex: "auditor" },
            { title: "审核状态", dataIndex: "audit_status" },
            {
              title: "审核日期",
              dataIndex: "audit_date",
              render: (value: string) => dayjs(value).format("YYYY-MM-DD"),
            },
            { title: "审批意见", dataIndex: "audit_content" },
            {
              title: "审批轮次",
                  dataIndex: "audit_round",
                },
                { title: "当前步骤", dataIndex: "current_step" },
          ]}
        />
      </Modal>
      <Modal
        open={fileListOpen}
        title="文件列表"
        onCancel={() => {
          fileListRequestTracker.invalidate();
          setFileListOpen(false);
          setFileListRow(null);
          setFileListAttachments([]);
          setFileListPage(1);
          setFileListPageSize(sealFilePagination.defaultPageSize);
          setFileListTotal(0);
          setAttachmentSelectedKeys([]);
        }}
        footer={<Button onClick={() => {
          fileListRequestTracker.invalidate();
          setFileListOpen(false);
          setFileListRow(null);
          setFileListAttachments([]);
          setFileListPage(1);
          setFileListPageSize(sealFilePagination.defaultPageSize);
          setFileListTotal(0);
          setAttachmentSelectedKeys([]);
        }}>关闭</Button>}
      >
        <Table
          size="small"
          rowKey="id"
          pagination={{
            current: fileListPage,
            pageSize: fileListPageSize,
            total: fileListTotal,
            showSizeChanger: sealFilePagination.showSizeChanger,
            pageSizeOptions: sealFilePagination.pageSizeOptions.map(String),
            showQuickJumper: sealFilePagination.showQuickJumper,
            showTotal: sealFilePagination.showTotal,
            onChange: (page, pageSize) => {
              if (fileListRow) void loadFileList(fileListRow, page, pageSize);
            },
          }}
          locale={{ emptyText: "" }}
          dataSource={fileListAttachments}
          columns={[
            { title: "上传人", dataIndex: "uploader" },
            { title: "文件名称", dataIndex: "original_name" },
            {
              title: "类型",
              width: 70,
              render: (_: unknown, item: AttachmentRow) =>
                getSealAttachmentExtension(item.original_name) || "—",
            },
            {
              title: "大小",
              width: 90,
              dataIndex: "size",
              render: (value: number) => formatSealAttachmentSize(value),
            },
            {
              title: "文件日期",
              dataIndex: "created_at",
              render: (value: string) => dayjs(value).format("YYYY-MM-DD"),
            },
            {
              title: "操作",
              render: (_: unknown, item: AttachmentRow) => (
                <Space size={0}>
                  <Button type="link" onClick={() => void previewAttachment(item)}>查看</Button>
                  <Button type="link" onClick={() => void downloadAttachment(item)}>下载</Button>
                </Space>
              ),
            },
          ]}
        />
        {!fileListRow && <span>暂无文件</span>}
      </Modal>
      <Modal
        open={previewOpen}
        title={`文件预览：${previewName}`}
        width={900}
        footer={<Button onClick={() => {
          previewRequestTracker.invalidate();
          setPreviewOpen(false);
          if (previewUrl) URL.revokeObjectURL(previewUrl);
          setPreviewUrl("");
          setPreviewText("");
          setPreviewDetail("");
          setPreviewName("");
        }}>关闭</Button>}
        onCancel={() => {
          previewRequestTracker.invalidate();
          setPreviewOpen(false);
          if (previewUrl) URL.revokeObjectURL(previewUrl);
          setPreviewUrl("");
          setPreviewText("");
          setPreviewDetail("");
          setPreviewName("");
        }}
      >
        {previewMode === "binary" && previewUrl && (
          <iframe
            title={previewName}
            src={previewUrl}
            style={{ width: "100%", height: 620, border: 0 }}
          />
        )}
        {previewMode === "text" && (
          <pre style={{ maxHeight: 620, overflow: "auto", whiteSpace: "pre-wrap" }}>
            {previewText}
          </pre>
        )}
        {previewMode === "unsupported" && <Alert type="info" message={previewDetail || "当前文件格式暂不支持在线预览，请下载后查看"} />}
      </Modal>
    </>
  );
}
