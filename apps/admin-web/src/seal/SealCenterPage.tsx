import { useEffect, useMemo, useRef, useState } from "react";
import {
  Button,
  Card,
  DatePicker,
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
} from "antd";
import {
  DeleteOutlined,
  PlusOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import { api } from "../api";
import { openAttachmentOnlinePreview } from "../attachmentOnlinePreview.mjs";
import { rememberCaseDetailTarget } from "../caseDetailNavigation";
import { rememberContractDetailTarget } from "../contractDetailNavigation";
import { rememberCustomerDetailTarget } from "../customerDetailNavigation";
import { resolveDetailRelation } from "../detailRelationResolver";
import { consumeBusinessRecordDetailTarget } from "../businessRecordDetailNavigation";
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
  legacySealApplicationDefaults,
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
  sealAttachmentTotal,
  sealRouteStatuses,
  toSealAuditRows,
} from "../sealWorkflowPolicy";
import type { SealAssetAuditRow, SealAuditRow } from "../sealWorkflowPolicy";
import { formatRequiredDate } from "../formSafety";
import RecordImportButton from "../RecordImportButton";
import "../seal-center.css";

import type {
  AssetAuditFilters,
  AttachmentRow,
  EventRow,
  RelationRow,
  SealActionState,
  SealAsset,
  SealPreviewMode,
  SealRow,
  Summary,
} from "./types";
import {
  SEAL_APPLICATION_FILE_CATEGORY,
  SEAL_STAMPED_FILE_CATEGORY,
  assetColors,
  displayStatus,
  getSealPreviewMode,
  listSealRowFileNames,
  personDisplayName,
  sealActionFailureMessage,
  sealAttachmentDeleteFailureMessage,
  sealAttachmentDownloadFailureMessage,
  sealAttachmentLabel,
  sealAttachmentListLabel,
  sealAttachmentPreviewFailureMessage,
  sealPackageDownloadFailureMessage,
  sealStatusOptions,
  sealTypes,
  sealUploadExtensions,
  statusColors,
  validateSealUploadFile,
} from "./constants";
import { SealActionModal } from "./SealActionModal";
import { SealAssetAuditModal } from "./SealAssetAuditModal";
import { SealAssetModal } from "./SealAssetModal";
import { SealAuditListModal } from "./SealAuditListModal";
import { SealBatchStampModal } from "./SealBatchStampModal";
import { SealCreateModal } from "./SealCreateModal";
import { SealDetailDrawer } from "./SealDetailDrawer";
import { SealFileListModal } from "./SealFileListModal";
import { SealPreviewModal } from "./SealPreviewModal";

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
  const statusFromView = (v: string): string[] => sealRouteStatuses(v);
  const usesLegacyApplicationPagination = [
    "seal-my-pending",
    "seal-audit-pending",
    "seal-audit-stamping",
    "seal-audit-refused",
    "seal-admin-pending",
    "seal-admin-used",
    "seal-admin-query",
  ].includes(initialView);
  const [tab, setTab] = useState(tabFromView(initialView));
  const [rows, setRows] = useState<SealRow[]>([]);
  const [assets, setAssets] = useState<SealAsset[]>([]);
  const [assetCapabilities, setAssetCapabilities] = useState<{ manage_assets?: boolean; action_keys?: string[] }>({});
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
  const [applicationPage, setApplicationPage] = useState(1);
  const [applicationPageSize, setApplicationPageSize] = useState(
    usesLegacyApplicationPagination ? 15 : 20,
  );
  const [applicationGoPage, setApplicationGoPage] = useState(1);
  const [editingApplication, setEditingApplication] = useState<SealRow | null>(
    null,
  );
  const [createOpen, setCreateOpen] = useState(false);
  const createSubmitModeRef = useRef(false);
  const [pendingCreateFiles, setPendingCreateFiles] = useState<File[]>([]);
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
  const [stampAttachmentIds, setStampAttachmentIds] = useState<number[]>([]);
  const [stampAttachmentLoading, setStampAttachmentLoading] = useState(false);
  const [stampAttachmentPage, setStampAttachmentPage] = useState(1);
  const [stampAttachmentPageSize, setStampAttachmentPageSize] = useState(sealFilePagination.defaultPageSize);
  const [stampAttachmentTotal, setStampAttachmentTotal] = useState(0);
  const [stampAttachmentUploading, setStampAttachmentUploading] = useState(false);
  const [stampAttachmentUploadFailed, setStampAttachmentUploadFailed] = useState(false);
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
  const [detailAuditForm] = Form.useForm();
  const [batchStampForm] = Form.useForm();
  const [queryForm] = Form.useForm();
  const [actionSubmitting, setActionSubmitting] = useState(false);
  const actionGate = useMemo(() => createSealActionGate(), []);
  const assetAuditRequestTracker = useMemo(() => createSealAssetAuditRequestTracker(), []);
  const canReadAssetAudit = canViewSealAssetAudit(assetCapabilities);
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
  const selectAllSourceAttachments = async () => {
    if (!selectedSourceRecord || sourceAttachmentLoading) return;
    setSourceAttachmentLoading(true);
    try {
      const allItems: AttachmentRow[] = [];
      let nextPage = 1;
      let total = 0;
      let pageSize = sourceAttachmentPageSize || sealFilePagination.defaultPageSize;
      while (allItems.length < total || nextPage === 1) {
        const { data } = await api.get("/attachments", {
          params: {
            record_id: selectedSourceRecord.id,
            page: nextPage,
            page_size: pageSize,
          },
        });
        const items = Array.isArray(data.items) ? data.items : [];
        const seen = new Set(allItems.map((item) => Number(item.id)));
        allItems.push(
          ...items.filter(
            (item: AttachmentRow) => !seen.has(Number(item.id)),
          ),
        );
        total = Number(data.total) || allItems.length;
        pageSize = Number(data.page_size) || pageSize;
        const resolvedPage = Number(data.page) || nextPage;
        if (!items.length || allItems.length >= total) break;
        nextPage = resolvedPage + 1;
      }
      setSourceAttachments(allItems);
      setSourceAttachmentPage(Math.max(1, nextPage));
      setSourceAttachmentPageSize(pageSize);
      setSourceAttachmentTotal(total || allItems.length);
      createForm.setFieldValue(
        "source_attachment_ids",
        allItems.map((item) => item.id),
      );
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
      const items = Array.isArray(apps.data.items) ? apps.data.items : [];
      setRows(items);
      setSummary(apps.data.summary);
      setAssets(inventory.data.items);
      setAssetCapabilities({
        ...(inventory.data.capabilities || {}),
        action_keys: Array.isArray(inventory.data.action_keys) ? inventory.data.action_keys : [],
      });
      setCases(caseResult.data.items);
      setContracts(contractResult.data.items);
      setCustomers(customerResult.data.items);
      return items as SealRow[];
    } catch (error: any) {
      message.error(
        error?.response?.data?.detail ||
          sealQueryFailureMessage(error?.response?.status),
      );
      return undefined;
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
    queryForm.resetFields();
    setQuery({});
    setApplicationPage(1);
    setApplicationGoPage(1);
    setApplicationPageSize(
      [
        "seal-my-pending",
        "seal-audit-pending",
        "seal-audit-stamping",
        "seal-audit-refused",
        "seal-admin-pending",
        "seal-admin-used",
        "seal-admin-query",
      ].includes(initialView)
        ? 15
        : 20,
    );
  }, [initialView, queryForm]);
  useEffect(() => {
    setSelectedKeys([]);
    setApplicationPage(1);
    setApplicationGoPage(1);
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
  const applicationPageCount = Math.max(
    1,
    Math.ceil(visibleRows.length / applicationPageSize),
  );
  const goToApplicationPage = () => {
    const page = Math.min(
      applicationPageCount,
      Math.max(1, Math.floor(Number(applicationGoPage) || 1)),
    );
    setApplicationPage(page);
    setApplicationGoPage(page);
  };
  const applicationPagination = usesLegacyApplicationPagination
    ? {
        current: applicationPage,
        pageSize: applicationPageSize,
        defaultPageSize: 15,
        showSizeChanger: true,
        showQuickJumper:
          initialView === "seal-my-pending" ? { goButton: "GO" } : true,
        pageSizeOptions: [10, 15, 20, 50, 100, 200],
        showTotal: (n: number) => `共 ${n} 条记录`,
        onChange: (page: number, pageSize: number) => {
          setApplicationPage(page);
          setApplicationGoPage(page);
          setApplicationPageSize(pageSize);
        },
      }
    : {
        current: applicationPage,
        pageSize: applicationPageSize,
        showTotal: (n: number) => `共 ${n} 条记录`,
        onChange: (page: number, pageSize: number) => {
          setApplicationPage(page);
          setApplicationGoPage(page);
          setApplicationPageSize(pageSize);
        },
      };
  useEffect(() => {
    if (applicationPage > applicationPageCount) {
      setApplicationPage(applicationPageCount);
      setApplicationGoPage(applicationPageCount);
    }
  }, [applicationPage, applicationPageCount]);
  const auditRows = useMemo(() => toSealAuditRows(history), [history]);
  const queueCreateFiles = (files: File[]) => {
    const validFiles = files.filter(Boolean);
    for (const file of validFiles) {
      const validationError = validateSealUploadFile(file);
      if (validationError) {
        message.error(validationError);
        return;
      }
    }
    setPendingCreateFiles((current) => [...current, ...validFiles]);
  };
  const createApplication = async () => {
    const submitAfterSave = createSubmitModeRef.current;
    createSubmitModeRef.current = false;
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
      const savedApplication = response.data as SealRow;
      const queuedFilesUploaded = pendingCreateFiles.length
        ? await uploadSealFiles(pendingCreateFiles, savedApplication)
        : true;
      if (submitAfterSave && !queuedFilesUploaded) {
        throw new Error("附件上传失败，未提交审批");
      }
      if (submitAfterSave) {
        await postSeal(`/seals/applications/${savedApplication.id}/submit`, {
          comment: "申请人在编辑弹窗内确认材料无误并提交审批",
        });
      }
      message.success(
        submitAfterSave
          ? "用印申请已保存并提交审批"
          : editingApplication
            ? "用印申请已修改"
            : "用印申请已保存为草稿",
      );
      if (queuedFilesUploaded) setPendingCreateFiles([]);
      setCreateOpen(false);
      setEditingApplication(null);
      createForm.resetFields();
      load();
      if (pendingCreateFiles.length) await openDetail(savedApplication);
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
    setPendingCreateFiles([]);
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
            ...legacySealApplicationDefaults(assets),
          },
    );
    setCreateOpen(true);
  };
  const editSelectedApplication = () => {
    const selected = selectedSealRows(visibleRows, selectedKeys);
    if (!selected.length) {
      message.info("请选择用印申请");
      return;
    }
    if (selected.length > 1) {
      message.info("只能选择一个用印申请进行修改");
      return;
    }
    const row = selected[0];
    if (row.status !== "草稿") {
      message.info("仅草稿用印申请可以修改");
      return;
    }
    openApplication(row);
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
    Modal.confirm({
      title: "撤回用印申请",
      content: `确定撤回选中的 ${selected.length} 条用印申请？撤回后相关申请将停止审批。`,
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
      },
    });
  };
  const withdrawSelectedApplications = () => {
    const selected = selectedSealRows(visibleRows, selectedKeys);
    if (!selected.length) {
      message.info("请选择需要撤回的用印申请");
      return;
    }
    if (!canBatchWithdrawSealRows(selected)) {
      message.info("仅待审批或待用印用印申请可以撤回");
      return;
    }
    if (selected.length > 1) {
      void batchWithdraw(selected);
      return;
    }
    void withdraw(selected[0]);
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
    setStampAttachmentIds([]);
    setStampAttachmentLoading(false);
    setStampAttachmentPage(1);
    setStampAttachmentPageSize(sealFilePagination.defaultPageSize);
    setStampAttachmentTotal(0);
    setStampAttachmentUploadFailed(false);
    actionForm.setFieldValue("stamp_attachment_ids", []);
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
          category: SEAL_STAMPED_FILE_CATEGORY,
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
      stamp_attachment_ids: [],
    });
    const { items, total } = await loadStampAttachments(row);
    if (items.length && items.length === total) {
      const ids = items.map((item: AttachmentRow) => item.id);
      setStampAttachmentIds(ids);
      actionForm.setFieldValue("stamp_attachment_ids", ids);
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
  const uploadStampAttachments = async (files: File[], row: SealRow): Promise<number[]> => {
    const validationError = files.map(validateSealUploadFile).find(Boolean);
    if (validationError) {
      setStampAttachmentUploadFailed(true);
      message.error(validationError);
      return [];
    }
    const body = new FormData();
    files.forEach((file) => body.append("files", file));
    setStampAttachmentUploading(true);
    setStampAttachmentUploadFailed(false);
    try {
      const response = await postSeal(`/seals/applications/${row.id}/files`, body);
      const uploadedItems = Array.isArray(response?.data?.items) ? response.data.items : [];
      const uploadedIds = uploadedItems.map((item: AttachmentRow) => Number(item.id)).filter(Boolean);
      if (!uploadedIds.length) {
        setStampAttachmentUploadFailed(true);
        message.error("盖章文件上传失败：未返回附件标识");
        return [];
      }
      const { items } = await loadStampAttachments(row, 1, Math.max(sealFilePagination.defaultPageSize, uploadedItems.length));
      const selectedIds = items.map((item: AttachmentRow) => Number(item.id)).filter(Boolean);
      setStampAttachmentIds(selectedIds);
      actionForm.setFieldValue("stamp_attachment_ids", selectedIds);
      message.success(`已上传盖章文件：${files.length} 份`);
      return uploadedIds;
    } catch (error: any) {
      setStampAttachmentUploadFailed(true);
      message.error(error?.response?.data?.detail || "盖章文件上传失败");
      return [];
    } finally {
      setStampAttachmentUploading(false);
    }
  };
  const runAction = async () => {
    if (!action) return;
    const v = await actionForm.validateFields();
    let stampAttachmentsForSubmit: number[] = [];
    if (action.type === "stamp") {
      if (stampAttachmentUploading) {
        message.info("盖章附件正在上传，请稍后确认");
        return;
      }
      if (stampAttachmentUploadFailed) {
        message.error("盖章附件上传失败，请重新上传后再登记实际用印");
        return;
      }
      stampAttachmentsForSubmit = (v.stamp_attachment_ids || stampAttachmentIds)
        .map(Number)
        .filter((value: number) => Number.isFinite(value) && value > 0);
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
          stamp_attachment_id: stampAttachmentsForSubmit[0],
          stamp_attachment_ids: stampAttachmentsForSubmit,
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
  const openDetail = async (row: SealRow, preserveAuditInput = false) => {
    const requestId = detailRequestTracker.next();
    if (!preserveAuditInput) detailAuditForm.resetFields();
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
  const refreshDetail = async () => {
    if (!detail) return;
    const latestRows = await load();
    const latestRow =
      latestRows?.find((item: SealRow) => item.id === detail.id) || detail;
    await openDetail(latestRow, true);
  };
  const openSealNumber = (row: SealRow) => {
    void openDetail(row);
  };
  const closeDetail = () => {
    detailRequestTracker.invalidate();
    setDetail(null);
    setHistory([]);
    setAttachments([]);
    setAttachmentPage(1);
    setAttachmentPageSize(sealFilePagination.defaultPageSize);
    setAttachmentTotal(0);
    setAttachmentSelectedKeys([]);
    detailAuditForm.resetFields();
  };
  const runDetailApproval = async (approved: boolean) => {
    if (!detail) return;
    const comment = String(detailAuditForm.getFieldValue("comment") || "").trim();
    if (!approved && !comment) {
      detailAuditForm.setFields([
        { name: "comment", errors: ["拒绝时必须填写原因"] },
      ]);
      return;
    }
    if (!actionGate.tryEnter()) {
      message.info("操作正在提交，请勿重复点击");
      return;
    }
    setActionSubmitting(true);
    try {
      await postSeal(`/seals/applications/${detail.id}/approve`, {
        approved,
        comment,
      });
      message.success(approved ? "审批已通过" : "申请已拒绝");
      closeDetail();
      await load();
    } catch (error: any) {
      message.error(
        error?.response?.data?.detail ||
          sealActionFailureMessage(approved ? "approve" : "reject"),
      );
    } finally {
      actionGate.leave();
      setActionSubmitting(false);
    }
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
    try {
      await openAttachmentOnlinePreview(api, item);
    } catch (error: any) {
      message.error(
        sealErrorMessage(error, error?.message || sealAttachmentPreviewFailureMessage(error?.response?.status)),
      );
    }
  };
  const previewListAttachmentByName = async (row: SealRow, fileName?: string) => {
    try {
      let page = 1;
      let total = 0;
      do {
        const { data } = await api.get("/attachments", {
          params: {
            record_id: row.id,
            page,
            page_size: sealFilePagination.defaultPageSize,
          },
        });
        const items = Array.isArray(data.items) ? data.items : [];
        const target = items.find(
          (item: AttachmentRow) => item.original_name === fileName,
        );
        if (target) {
          await previewAttachment(target);
          return;
        }
        total = Number(data.total ?? items.length);
        if (!items.length) break;
        page += 1;
      } while ((page - 1) * sealFilePagination.defaultPageSize < total);
      if (fileName) {
        message.warning(`未找到文件：${fileName}`);
      }
      await openFileList(row);
    } catch {
      await openFileList(row);
    }
  };
  const uploadSealFiles = async (files: File[], target: SealRow | null = detail): Promise<boolean> => {
    if (!target) return false;
    const validFiles = files.filter(Boolean);
    if (!validFiles.length) return false;
    for (const file of validFiles) {
      const validationError = validateSealUploadFile(file);
      if (validationError) {
        message.error(validationError);
        return false;
      }
    }
    const body = new FormData();
    validFiles.forEach((file) => body.append("files", file));
    try {
      const uploadPath =
        target === detail && detail
          ? `/seals/applications/${detail.id}/files`
          : `/seals/applications/${target.id}/files`;
      await postSeal(uploadPath, body);
      message.success(`已上传用印文件：${validFiles.length} 个`);
      await loadDetailFiles(target, 1, attachmentPageSize);
      load();
      return true;
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "用印文件上传失败");
      return false;
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
        "/seals/applications/batch-download",
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
  const stampSelectedApplications = () => {
    const selected = selectedSealRows(visibleRows, selectedKeys);
    if (!selected.length) {
      message.info("请选择用印文件");
      return;
    }
    if (!canBatchStampSealRows(selected)) {
      message.info("仅待用印用印申请可以标记用印");
      return;
    }
    const selectedRow = selected.length === 1 ? selected[0] : null;
    if (selectedRow) {
      setAction({ type: "stamp", row: selectedRow });
      void openStampAction(selectedRow);
      return;
    }
    batchStampForm.setFieldsValue({
      actual_copies: Math.min(
        ...selected.map((row) => Number(row.data.copies) || 0),
      ),
      operator: "admin",
    });
    setBatchStampOpen(true);
  };
  const downloadSelectedSealFiles = () => {
    const selected = selectedSealRows(visibleRows, selectedKeys);
    if (!selected.length) {
      message.warning("请选择用印文件");
      return;
    }
    void packageDownload(selected);
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
    { title: "申请人", dataIndex: "owner_display_name", width: 90, render: personDisplayName },
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
      render: (_value: number, r: SealRow) => {
        const names = listSealRowFileNames(r);
        const total = sealAttachmentTotal(r);
        const hasFiles = total > 0 || names.length > 0;
        return (
          <Space size={4} wrap>
            <Button type="link" onClick={() => void openFileList(r)}>
              {total}
            </Button>
            {hasFiles && (
              <Popover
                trigger="click"
                title={sealAttachmentListLabel}
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
                      全部{sealAttachmentListLabel}
                    </Button>
                  </Space>
                }
              >
                <Button type="link" size="small">
                  {sealAttachmentListLabel}
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
      render: (_: unknown, r: SealRow) => personDisplayName(r.data.approver_display_name),
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
          {tab === "audit" && (canSealAction("approve", r) || canSealAction("reject", r)) && (
            <>
              {canSealAction("approve", r) && (
                <Button
                  type="link"
                  onClick={() => {
                    setAction({ type: "approve", row: r });
                    actionForm.resetFields();
                  }}
                >
                  通过
                </Button>
              )}
              {canSealAction("reject", r) && (
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
              )}
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
          {canReadAssetAudit && (
            <>
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
            </>
          )}
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

  // === Modal handlers ===

  const closeCreateModal = () => {
    setCreateOpen(false);
    setEditingApplication(null);
    setPendingCreateFiles([]);
    setSourceAttachments([]);
    setSourceAttachmentPage(1);
    setSourceAttachmentPageSize(sealFilePagination.defaultPageSize);
    setSourceAttachmentTotal(0);
    createForm.setFieldValue("source_attachment_ids", []);
  };

  const handleCreateSave = () => {
    void createApplication();
  };

  const handleCreateSubmit = () => {
    createSubmitModeRef.current = true;
    void createApplication();
  };

  const handleCreateFileRemove = (file: { uid: string }) => {
    setPendingCreateFiles((current) =>
      current.filter((item, index) =>
        `${item.name}-${item.lastModified}-${index}` !== file.uid,
      ),
    );
  };

  const handleOpenDetailFromEdit = () => {
    setCreateOpen(false);
    if (editingApplication) void openDetail(editingApplication);
  };

  const handleLoadMoreSourceAttachments = () => {
    void loadMoreSourceAttachments();
  };

  const handleSelectAllSourceAttachments = () => {
    void selectAllSourceAttachments();
  };

  const closePreviewModal = () => {
    previewRequestTracker.invalidate();
    setPreviewOpen(false);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl("");
    setPreviewText("");
    setPreviewDetail("");
    setPreviewName("");
  };

  const closeAuditListModal = () => {
    setAuditListOpen(false);
  };

  const closeBatchStampModal = () => {
    setBatchStampOpen(false);
    batchStampForm.resetFields();
  };

  const handleBatchStampOk = () => {
    void runBatchStamp();
  };

  const closeAssetModal = () => {
    setAssetOpen(false);
  };

  const handleSaveAsset = () => {
    void saveAsset();
  };

  const closeFileListModal = () => {
    fileListRequestTracker.invalidate();
    setFileListOpen(false);
    setFileListRow(null);
    setFileListAttachments([]);
    setFileListPage(1);
    setFileListPageSize(sealFilePagination.defaultPageSize);
    setFileListTotal(0);
    setAttachmentSelectedKeys([]);
  };

  const handleFileListPageChange = (page: number, pageSize: number) => {
    if (fileListRow) void loadFileList(fileListRow, page, pageSize);
  };

  const handleFileListPreview = (item: AttachmentRow) => {
    void previewAttachment(item);
  };

  const handleFileListDownload = (item: AttachmentRow) => {
    void downloadAttachment(item);
  };

  const handleAssetAuditClose = () => {
    clearAssetAudit();
  };

  const handleAssetAuditQuery = () => {
    setAssetAuditPage(1);
    if (assetAuditAsset) void loadAssetAudit(assetAuditAsset.id, 1, assetAuditPageSize, assetAuditFilters);
  };

  const handleAssetAuditReset = () => {
    const filters = { action: "", operator: "", keyword: "", date_from: "", date_to: "" };
    setAssetAuditFilters(filters);
    setAssetAuditPage(1);
    if (assetAuditAsset) void loadAssetAudit(assetAuditAsset.id, 1, assetAuditPageSize, filters);
  };

  const handleAssetAuditPageChange = (page: number, pageSize: number) => {
    setAssetAuditPage(page);
    setAssetAuditPageSize(pageSize);
    if (assetAuditAsset) void loadAssetAudit(assetAuditAsset.id, page, pageSize);
  };

  const handleActionOk = () => {
    void runAction();
  };

  const handleActionCancel = () => {
    setAction(null);
    resetStampAttachmentState();
  };

  const handleActionOpenDetail = () => {
    if (!action) return;
    setAction(null);
    void openDetail(action.row);
  };

  const handleStampAttachmentChange = (values: number[]) => {
    setStampAttachmentIds(values.map(Number).filter(Boolean));
    setStampAttachmentUploadFailed(false);
  };

  const handleLoadMoreStampAttachments = () => {
    void loadMoreStampAttachments();
  };

  const handleUploadStampAttachments = (files: File[]) => {
    const row = action?.type === "stamp" ? action.row : null;
    if (!row) return;
    void uploadStampAttachments(files, row);
  };

  const handleDetailClose = () => {
    closeDetail();
  };

  const handleDetailRefresh = () => {
    void refreshDetail();
  };

  const handleDetailApproval = (approved: boolean) => {
    void runDetailApproval(approved);
  };

  const handleDetailAttachmentPageChange = (page: number, pageSize: number) => {
    if (detail) void loadDetailFiles(detail, page, pageSize);
  };

  const handleDetailUploadFiles = (files: File[]) => {
    void uploadSealFiles(files);
  };

  const handleDetailRemoveFiles = () => {
    void removeSealFiles();
  };

  const handleDetailRemoveFile = (item: AttachmentRow) => {
    void removeSealFile(item);
  };

  const handleDetailPreviewAttachment = (item: AttachmentRow) => {
    void previewAttachment(item);
  };

  const handleDetailDownloadAttachment = (item: AttachmentRow) => {
    void downloadAttachment(item);
  };

  const handleDetailOpenAuditList = () => {
    setAuditListOpen(true);
  };

  const handleDetailOpenCustomerDetail = (customer: unknown, customerNo?: unknown) => {
    void openCustomerDetail(customer, customerNo);
  };

  const handleDetailOpenCaseDetail = (caseNo: unknown) => {
    void openCaseDetail(caseNo);
  };

  const handleDetailOpenContractDetail = (contractNo: unknown) => {
    void openContractDetail(contractNo);
  };

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
                {canReadAssetAudit && (
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={() => openAsset()}
                  >
                    新增印章
                  </Button>
                )}
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
            pagination={applicationPagination}
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
                      {initialView === "seal-my-pending" && (
                        <Space size={4} aria-label="分页跳转">
                          <InputNumber
                            aria-label="跳转页码"
                            min={1}
                            max={applicationPageCount}
                            value={applicationGoPage}
                            controls={false}
                            size="small"
                            style={{ width: 52 }}
                            onChange={(page) =>
                              setApplicationGoPage(Number(page) || 1)
                            }
                          />
                          <Button size="small" onClick={goToApplicationPage}>
                            GO
                          </Button>
                        </Space>
                      )}
                      {initialView === "seal-my-pending" && (
                        <>
                          <Button onClick={() => openApplication()}>
                            申请用印
                          </Button>
                          <Button onClick={() => editSelectedApplication()}>
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
                            onClick={() => withdrawSelectedApplications()}
                          >
                            撤回
                          </Button>
                        </>
                      )}
                      {initialView === "seal-my-stamping" && (
                        <Button
                          onClick={() => withdrawSelectedApplications()}
                        >
                          撤回
                        </Button>
                      )}
                      {initialView === "seal-admin-pending" && (
                        <>
                          <Button
                            onClick={() => stampSelectedApplications()}
                          >
                            标记用印
                          </Button>
                          <Button
                            disabled={!selectedRows.length}
                            onClick={() => downloadSelectedSealFiles()}
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
      <SealCreateModal
        open={createOpen}
        editingApplication={editingApplication}
        form={createForm}
        submitting={actionSubmitting}
        isContractSeal={isContractSeal}
        isCaseSeal={isCaseSeal}
        showSourceRelationFields={showSourceRelationFields}
        customers={customers}
        cases={cases}
        contracts={contracts}
        availableAssets={availableAssets}
        sourceAttachments={sourceAttachments}
        sourceAttachmentLoading={sourceAttachmentLoading}
        sourceAttachmentTotal={sourceAttachmentTotal}
        pendingCreateFiles={pendingCreateFiles}
        selectedSourceRecord={selectedSourceRecord}
        onCancel={closeCreateModal}
        onSave={handleCreateSave}
        onSubmit={handleCreateSubmit}
        onUseTypeChange={handleUseTypeChange}
        onQueueCreateFiles={queueCreateFiles}
        onRemoveCreateFile={handleCreateFileRemove}
        onOpenDetailFromEdit={handleOpenDetailFromEdit}
        onLoadMoreSourceAttachments={handleLoadMoreSourceAttachments}
        onSelectAllSourceAttachments={handleSelectAllSourceAttachments}
      />
      <SealAssetModal
        open={assetOpen}
        editAsset={editAsset}
        form={assetForm}
        submitting={actionSubmitting}
        onOk={handleSaveAsset}
        onCancel={closeAssetModal}
      />
      <SealAssetAuditModal
        open={assetAuditOpen && canReadAssetAudit}
        asset={assetAuditAsset}
        rows={assetAuditRows}
        total={assetAuditTotal}
        page={assetAuditPage}
        pageSize={assetAuditPageSize}
        loading={assetAuditLoading}
        filters={assetAuditFilters}
        onClose={handleAssetAuditClose}
        onFiltersChange={setAssetAuditFilters}
        onPageChange={handleAssetAuditPageChange}
        onQuery={handleAssetAuditQuery}
        onReset={handleAssetAuditReset}
      />
      <SealActionModal
        action={action}
        form={actionForm}
        submitting={actionSubmitting}
        stampAttachments={stampAttachments}
        stampAttachmentLoading={stampAttachmentLoading}
        stampAttachmentUploading={stampAttachmentUploading}
        stampAttachmentUploadFailed={stampAttachmentUploadFailed}
        stampAttachmentTotal={stampAttachmentTotal}
        onOk={handleActionOk}
        onCancel={handleActionCancel}
        onOpenDetail={handleActionOpenDetail}
        onStampAttachmentChange={handleStampAttachmentChange}
        onLoadMoreStampAttachments={handleLoadMoreStampAttachments}
        onUploadStampAttachments={handleUploadStampAttachments}
      />
      <SealBatchStampModal
        open={batchStampOpen}
        form={batchStampForm}
        submitting={actionSubmitting}
        onOk={handleBatchStampOk}
        onCancel={closeBatchStampModal}
      />
      <SealDetailDrawer
        open={Boolean(detail)}
        detail={detail}
        tab={tab}
        history={history}
        attachments={attachments}
        attachmentPage={attachmentPage}
        attachmentPageSize={attachmentPageSize}
        attachmentTotal={attachmentTotal}
        attachmentSelectedKeys={attachmentSelectedKeys}
        detailAuditForm={detailAuditForm}
        actionSubmitting={actionSubmitting}
        onClose={handleDetailClose}
        onRefresh={handleDetailRefresh}
        onDetailApproval={handleDetailApproval}
        onAttachmentPageChange={handleDetailAttachmentPageChange}
        onAttachmentSelectionChange={setAttachmentSelectedKeys}
        onUploadFiles={handleDetailUploadFiles}
        onRemoveFiles={handleDetailRemoveFiles}
        onRemoveFile={handleDetailRemoveFile}
        onPreviewAttachment={handleDetailPreviewAttachment}
        onDownloadAttachment={handleDetailDownloadAttachment}
        onOpenAuditList={handleDetailOpenAuditList}
        onOpenCustomerDetail={handleDetailOpenCustomerDetail}
        onOpenCaseDetail={handleDetailOpenCaseDetail}
        onOpenContractDetail={handleDetailOpenContractDetail}
      />
      <SealAuditListModal
        open={auditListOpen}
        rows={auditRows}
        onClose={closeAuditListModal}
      />
      <SealFileListModal
        open={fileListOpen}
        row={fileListRow}
        attachments={fileListAttachments}
        page={fileListPage}
        pageSize={fileListPageSize}
        total={fileListTotal}
        onClose={closeFileListModal}
        onPageChange={handleFileListPageChange}
        onPreview={handleFileListPreview}
        onDownload={handleFileListDownload}
      />
      <SealPreviewModal
        open={previewOpen}
        name={previewName}
        mode={previewMode}
        url={previewUrl}
        text={previewText}
        detail={previewDetail}
        onClose={closePreviewModal}
      />
    </>
  );
}
