import { useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  AutoComplete,
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
  Popover,
  Select,
  Space,
  Steps,
  Statistic,
  Table,
  Tabs,
  Tag,
  TreeSelect,
} from "antd";
import {
  AuditOutlined,
  ArrowUpOutlined,
  BookOutlined,
  CheckCircleOutlined,
  DeleteOutlined,
  DollarOutlined,
  DownloadOutlined,
  MinusCircleOutlined,
  PaperClipOutlined,
  PlusCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
  RollbackOutlined,
  ShareAltOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import { api } from "./api";
import { rememberCaseDetailTarget } from "./caseDetailNavigation";
import { rememberContractDetailTarget } from "./contractDetailNavigation";
import { rememberCustomerDetailTarget } from "./customerDetailNavigation";
import { consumeBusinessRecordDetailTarget } from "./businessRecordDetailNavigation";
import { resolveIncomingPaymentDetailTarget } from "./incomingPaymentDetailNavigation";
import { formatRequiredDate } from "./formSafety";
import { createFinanceActionGate } from "./financeActionGate.mjs";
import { buildInvoiceApplicationPayload } from "./financeInvoiceHelpers.mjs";
import { internalFeeExportRequestParams } from "./financeInternalFeeHelpers.mjs";
import {
  consumeDashboardFeeQuery,
  preserveDashboardFeeQueryContext,
} from "./dashboardFeeNavigation.mjs";
import {
  normalizeRefundResponse,
  caseFeeRefundStatusLabel,
  createLatestRequestGuard,
  refreshRefundListWithFallback,
  refundAmountUpdateRequest,
  refundBatchStatusRequest,
  refundExportRequestParams,
  refundListRequest,
  refundLoadFailure,
  refundPageSizeOptions,
  refundSelectedExportRequestParams,
  refundStatusForRoute,
  refundStatusOptions,
} from "./financeRefundHelpers.mjs";
import RecordImportButton from "./RecordImportButton";
import { ReceiptCreatePage } from "./PlatformFinancePage";
import "./finance-center.css";

type Fee = {
  id: number;
  module?: string;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
  owner: string;
  description?: string;
  data: Record<string, any>;
  created_at?: string;
  updated_at?: string;
};
type FinanceFlow = Fee;

type LegacyFinanceRecord = {
  id: number;
  source_table: string;
  legacy_id: string;
  record_kind: "ap_payment" | "ar_payment" | "invoice" | "ap_packing" | "case_fee";
  status_code: string;
  status_label: string;
  is_active: boolean;
  currency?: string;
  legacy_contract_no?: string;
  legacy_case_no?: string;
  legacy_customer_no?: string;
  contract_record_id?: number | null;
  case_record_id?: number | null;
  customer_record_id?: number | null;
  mapping_status?: string;
  allocation_count: number;
  file_count: number;
  audit_count: number;
  primary_amount: number | null;
  imported_at?: string;
  updated_at?: string;
  source_payload?: Record<string, unknown>;
  allocations?: Array<Record<string, any>>;
  files?: Array<Record<string, any>>;
  audits?: Array<Record<string, any>>;
  legacy_statuses?: Record<string, unknown>;
  legacy_amounts?: Record<string, unknown>;
  read_only?: boolean;
};

type LegacyFinanceSummary = {
  records: Array<{
    record_kind: LegacyFinanceRecord["record_kind"];
    is_active: boolean;
    count: number;
    primary_amount: number | null;
  }>;
  allocations: Array<Record<string, any>>;
  audits: Array<Record<string, any>>;
  orphan_allocations: Array<Record<string, any>>;
  orphan_files: Array<Record<string, any>>;
  orphan_audits: Array<Record<string, any>>;
  amount_visible: boolean;
  read_only: boolean;
};

type InvoiceCustomerDefaults = {
  customer: string;
  customer_no: string;
  invoice_title: string;
  taxpayer_id: string;
  invoice_phone: string;
  bank_account: string;
  bank_name: string;
  invoice_address: string;
};

type InvoiceSourceFields = {
  case_no?: string;
  case_record_id?: number | string;
  contract_record_id?: number | string;
  contract_no?: string;
  external_contract_no?: string;
  customer?: string;
  customer_no?: string;
  invoice_title?: string;
  taxpayer_id?: string;
  invoice_phone?: string;
  bank_account?: string;
  bank_name?: string;
  invoice_address?: string;
  amount?: number;
};

const invoiceText = (value: unknown) => String(value ?? "").trim();

const legacyInvoiceUpdateFailureMessage = (response: { data?: unknown }) => {
  const payload = response?.data;
  if (!payload || typeof payload !== "object") return "";
  const result = payload as Record<string, unknown>;
  if (result.IsSuccess !== false && result.success !== false) return "";
  return invoiceText(result.message || result.Message || result.detail) || "发票申请更新失败";
};

const findInvoiceContract = (fee: Fee, contracts: Fee[]) => {
  const data = fee.data || {};
  const contractId = Number(data.contract_id ?? data.contract_record_id);
  const contractNo = invoiceText(data.contract_no);
  return contracts.find((contract) =>
    (Number.isFinite(contractId) && contractId > 0 && contract.id === contractId) ||
    (contractNo && contract.serial_no === contractNo),
  );
};

const findInvoiceCustomer = (
  customerRows: Fee[],
  customerName: unknown,
  customerNo: unknown,
  customerId: unknown,
) => {
  const name = invoiceText(customerName);
  const serialNo = invoiceText(customerNo);
  const id = Number(customerId);
  return customerRows.find((customer) =>
    (Number.isFinite(id) && id > 0 && customer.id === id) ||
    (serialNo && customer.serial_no === serialNo) ||
    (name && (customer.title === name || customer.customer === name)),
  );
};

const buildInvoiceCustomerDefaults = (
  customerRows: Fee[],
  customerName: unknown,
  customerNo: unknown,
  customerId: unknown,
): InvoiceCustomerDefaults => {
  const customer = findInvoiceCustomer(customerRows, customerName, customerNo, customerId);
  const data = customer?.data || {};
  const name = invoiceText(customer?.title || customer?.customer || customerName);
  return {
    customer: name,
    customer_no: invoiceText(customer?.serial_no || customerNo),
    invoice_title: invoiceText(data.invoice_title || name),
    taxpayer_id: invoiceText(
      data.taxpayer_id || data.credit_code || data.unified_social_credit_code,
    ),
    invoice_phone: invoiceText(data.invoice_phone || data.phone || data.office_phone),
    bank_account: invoiceText(data.bank_account),
    bank_name: invoiceText(data.bank_name),
    invoice_address: invoiceText(data.invoice_address || data.registered_address),
  };
};

const invoiceFeeAvailableAmount = (fee: Fee) =>
  Number(fee.data?.remaining_invoice_amount ?? fee.data?.amount ?? 0);

const invoiceFeeIssuedAmount = (fee: Fee) => {
  const data = fee.data || {};
  if (data.invoiced_amount != null) return Number(data.invoiced_amount || 0);
  return Math.max(0, Number(data.amount || 0) - invoiceFeeAvailableAmount(fee));
};

const buildInvoiceSourceFields = (
  selectedFees: Fee[],
  contracts: Fee[],
  customerRows: Fee[],
): InvoiceSourceFields => {
  const first = selectedFees[0];
  if (!first) return {};
  const data = first.data || {};
  const contract = findInvoiceContract(first, contracts);
  const contractData = contract?.data || {};
  const customerDefaults = buildInvoiceCustomerDefaults(
    customerRows,
    first.customer || data.customer || contract?.customer,
    data.customer_no || contractData.customer_no,
    data.customer_id || data.customer_record_id || contractData.customer_id,
  );
  return {
    case_no: invoiceText(data.case_no),
    case_record_id: data.case_id || data.case_record_id || undefined,
    contract_record_id:
      data.contract_id || data.contract_record_id || contract?.id || undefined,
    contract_no: invoiceText(data.contract_no || contract?.serial_no),
    external_contract_no: invoiceText(
      data.external_contract_no || contractData.external_contract_no,
    ),
    ...customerDefaults,
    amount: Number(
      selectedFees.reduce((total, fee) => total + invoiceFeeAvailableAmount(fee), 0).toFixed(2),
    ),
  };
};
type FinancePersonOption = { value: string; label: string; username: string };
type Attachment = {
  id: number;
  original_name: string;
  category: string;
  size: number;
  uploader: string;
  created_at: string;
};
type Transaction = {
  id: number;
  finance_record_id: number | null;
  finance_no: string;
  finance_title: string;
  transaction_type: string;
  amount: number | null;
  transaction_date: string;
  voucher_no: string;
  counterparty: string;
  operator: string;
  remark: string;
  voucher_count: number;
  voucher_categories: string[];
  vouchers: Attachment[];
};
type PaymentPackagePreview = {
  package_no: string;
  print_date: string;
  payee: string;
  total_amount: number;
  items: Array<{
    fee_id: number;
    request_no: string;
    case_no: string;
    case_name: string;
    amount: number;
    commission_type: string;
    payee: string;
    remark: string;
  }>;
  submitted?: boolean;
};
type Reconciliation = {
  id: number;
  period_type: string;
  date_from: string;
  date_to: string;
  transaction_count: number;
  total_amount: number;
  discrepancy_amount: number;
  status: string;
  operator: string;
  remark: string;
};
type IncomingPayment = {
  id: number;
  receipt_no: string;
  received_date: string;
  amount: number | null;
  payer_name: string;
  bank_reference: string;
  status: string;
  claimed_customer: string;
  claimant: string;
  allocated_amount: number | null;
  remaining_amount: number | null;
  contract_no: string;
  bank_source: string;
  customer_name?: string;
  payment_method?: string;
  assigned_official_fee?: number | null;
  assigned_agency_fee?: number | null;
  assigned_other_fee?: number | null;
  claimant_display_name?: string;
  allocation_details?: Array<{
    detail_id?: string;
    case_id?: number;
    case_type?: string;
    case_name?: string;
    case_no?: string;
    contract_no?: string;
    fee_type?: string;
    fee_total_amount?: number | null;
    fee_allocated_amount?: number | null;
    current_amount?: number | null;
  }>;
  allocations: any[];
  operator: string;
  remark: string;
};
type Receivable = {
  id: number;
  contract_record_id: number;
  contract_no: string;
  contract_title: string;
  customer: string;
  phase: string;
  due_date: string;
  amount: number;
  received_amount: number;
  remaining_amount: number;
  status: string;
};
type AllocationCandidate = {
  key: string;
  receivable_plan_id: number | null;
  fee_record_id?: number | null;
  contract_id: number;
  contract_no: string;
  case_id: number | null;
  case_no: string;
  case_title: string;
  plaintiff: string;
  defendant: string;
  case_stage: string;
  submission_date: string;
  fee_type: string;
  total_amount: number;
  received_amount: number;
  remaining_amount: number;
};
const feeTypes = [
  "官方费用",
  "代理费",
  "其他费用",
  "内部费用",
  "结算费用",
  "预损费用",
  "归档费用",
];
const internalApprovalRoutes = [
  "finance-payment-audit",
  "finance-internal-archive",
  "finance-internal-audit",
  "finance-internal-fee-audit",
  "finance-internal-refund-audit",
];
const statusColors: Record<string, string> = {
  草稿: "default",
  待审批: "orange",
  已审批: "blue",
  部分付款: "cyan",
  已付款: "green",
  已退回: "red",
  已驳回: "red",
  待开票: "cyan",
  已开票: "green",
  已作废: "default",
  退款办理中: "blue",
  已退款: "green",
};
const money = (v: number) =>
  `¥ ${Number(v || 0).toLocaleString("zh-CN", { minimumFractionDigits: 2 })}`;
const voucherCategory: Record<string, string> = {
  付款: "付款凭证",
  开票: "发票扫描件",
  回款: "回款凭证",
  退费: "退费凭证",
};
const attachmentRecordModule = (row: FinanceFlow, category: string) =>
  row.module ||
  (category === "发票扫描件"
    ? "invoice"
    : category === "退费凭证"
      ? "refund"
      : "finance");
const initialSessionUser = () => {
  try {
    return JSON.parse(localStorage.getItem("user") || "{}");
  } catch {
    return {};
  }
};

const CONTRACT_PAYMENT_SOURCE_KEYS = [
  ["payment_no", "请款单号"],
  ["contract_no", "合同号"],
  ["customer", "客户名称"],
  ["amount", "金额"],
  ["source_id", "来源ID"],
  ["source_module", "来源模块"],
  ["return_page", "返回路径"],
] as const;

type ContractPaymentSourceSuccess = {
  active: true;
  ok: true;
  paymentNo: string;
  contractNo: string;
  customer: string;
  amount: number;
  sourceId: number;
  sourceModule: "contract_payment";
  returnPage: string;
};

type ContractPaymentSourceState =
  | { active: false }
  | { active: true; ok: false; error: string }
  | ContractPaymentSourceSuccess;

const parseContractPaymentSource = (
  initialView: string,
  search: string,
): ContractPaymentSourceState => {
  if (initialView !== "finance-payment-mine") return { active: false };
  const params = new URLSearchParams(search);
  if (!CONTRACT_PAYMENT_SOURCE_KEYS.some(([key]) => params.has(key))) {
    return { active: false };
  }
  const duplicates = CONTRACT_PAYMENT_SOURCE_KEYS.filter(
    ([key]) => params.getAll(key).length > 1,
  ).map(([, label]) => label);
  if (duplicates.length) {
    return {
      active: true,
      ok: false,
      error: `合同付款来源参数重复：${duplicates.join("、")}`,
    };
  }
  const values = Object.fromEntries(
    CONTRACT_PAYMENT_SOURCE_KEYS.map(([key]) => [
      key,
      String(params.get(key) || "").trim(),
    ]),
  );
  const missing = CONTRACT_PAYMENT_SOURCE_KEYS.filter(
    ([key]) => !values[key],
  ).map(([, label]) => label);
  if (missing.length) {
    return {
      active: true,
      ok: false,
      error: `合同付款来源缺少参数：${missing.join("、")}`,
    };
  }
  if (values.source_module !== "contract_payment") {
    return { active: true, ok: false, error: "合同付款来源模块无效" };
  }
  const sourceId = Number(values.source_id);
  if (!Number.isInteger(sourceId) || sourceId <= 0) {
    return { active: true, ok: false, error: "合同付款来源ID无效" };
  }
  const amount = Number(values.amount);
  if (!Number.isFinite(amount) || amount <= 0) {
    return { active: true, ok: false, error: "合同付款来源金额无效" };
  }
  const returnMatch = values.return_page.match(/^contract-detail-(\d+)-(.+)$/);
  let returnContractNo = "";
  try {
    returnContractNo = returnMatch ? decodeURIComponent(returnMatch[2]) : "";
  } catch {
    returnContractNo = "";
  }
  if (
    !returnMatch ||
    Number(returnMatch[1]) <= 0 ||
    returnContractNo !== values.contract_no
  ) {
    return { active: true, ok: false, error: "合同付款返回路径无效" };
  }
  return {
    active: true,
    ok: true,
    paymentNo: values.payment_no,
    contractNo: values.contract_no,
    customer: values.customer,
    amount,
    sourceId,
    sourceModule: "contract_payment",
    returnPage: values.return_page,
  };
};

const matchesContractPaymentSource = (
  item: Fee,
  source: ContractPaymentSourceSuccess,
) =>
  item.data?._source_module === source.sourceModule &&
  Number(item.id) === source.sourceId &&
  String(item.serial_no || "").trim() === source.paymentNo &&
  String(item.data?.contract_no || "").trim() === source.contractNo &&
  String(item.customer || "").trim() === source.customer &&
  Number(item.data?.amount) === source.amount;

const paymentPackageEmptySelectionMessage = (initialView: string) =>
  initialView === "finance-payment-print"
    ? "请选择需要导出的请款单."
    : "请选择提成.";

const paymentPrintStatusField = (initialView: string) =>
  initialView === "finance-payment-print"
    ? {
        options: [
          "请选择",
          "创建待提交",
          "待审批",
          "待付款",
          "待核销",
          "已付款",
          "已驳回",
          "已作废",
        ],
        defaultValue: "请选择",
      }
    : undefined;

const paymentWriteoffClearQuery = (initialView: string) =>
  initialView === "finance-payment-writeoff" ? { status: "待核销" } : {};

const paymentPackagePageSizeOptions = [10, 15, 20, 50, 100, 200];

const paymentPackageRequestParams = (
  initialView: string,
  query: Record<string, any>,
  page: number,
  pageSize: number,
) => {
  const pageId = initialView === "finance-internal-writeoff" ? "5001003006" : "";
  const status = String(
    initialView === "finance-internal-writeoff"
      ? "待核销"
      : query.status || query.routeField3 || "",
  ).trim();
  return {
    page,
    page_size: pageSize,
    ...(pageId ? { page_id: pageId } : {}),
    ...(status ? { status } : {}),
  };
};

const normalizePaymentPackageResponse = (
  data: Record<string, any> | undefined,
  fallbackPage = 1,
  fallbackPageSize = 15,
) => ({
  items: Array.isArray(data?.items) ? data.items : [],
  total: Number(data?.total || 0),
  page: Number(data?.page || fallbackPage),
  pageSize: Number(data?.page_size || fallbackPageSize),
});
const paymentPackageWordExportPath = (packageNo: string) =>
  "/finance/payment-packages/{package_no}/print-word".replace(
    "{package_no}",
    encodeURIComponent(packageNo),
  );

const paymentPackageWriteoffPayload = (
  values: Record<string, any>,
  formatDate: (value: any) => any = (value) => value,
) => ({
  amount: values.amount,
  paid_date: formatDate(values.paid_date),
  payment_method: values.payment_method,
  invoice_no: values.invoice_no,
  remark: values.remark || "",
});

const paymentQueryQuickJumper = (initialView: string) =>
  [
    "finance-payment-query",
    "finance-payment-mine",
    "finance-internal-mine",
  ].includes(initialView)
    ? { goButton: "GO" }
    : undefined;

// Legacy AP/PaymentList accepts the complete payment status vocabulary and
// treats an omitted status as "all statuses". Keep this matrix explicit so
// query requests do not silently collapse to the local workflow subset.
const paymentQueryLegacyStatusMatrix = [
  "创建待提交",
  "待审批",
  "待付款",
  "待核销",
  "已付款",
  "已驳回",
  "已作废",
];

const paymentQueryLegacyErrorMessage = "查询出错.";

const paymentQueryRequestParams = (
  query: Record<string, any>,
  page: number,
  pageSize: number,
) => ({
  module: "finance",
  page,
  page_size: pageSize,
  keyword: String(query.paymentNo || "").trim(),
  record_status: String(query.status || "").trim(),
});

const contractPaymentQueryRequestParams = (
  query: Record<string, any>,
  page: number,
  pageSize: number,
) => ({
  module: "contract_payment",
  page,
  page_size: pageSize,
  keyword: String(query.paymentNo || "").trim(),
  record_status: String(query.status || "").trim(),
});

const paymentQueryShowsSinglePageGo = (
  initialView: string,
  total: number,
  pageSize: number,
) =>
  initialView === "finance-payment-query" &&
  total > 0 &&
  total <= pageSize;

const paymentQueryQuickPageResult = (value: string, totalPages: number) => {
  if (value === "") {
    return { ok: false, page: null, message: "请输入页码数" };
  }
  if (!/^[0-9]*[1-9][0-9]*$/.test(value)) {
    return { ok: false, page: null, message: "请输入正确的页码!" };
  }
  const page = Number(value);
  if (page > totalPages) {
    return { ok: false, page: null, message: "请输入有效范围的页码!" };
  }
  return { ok: true, page, message: "" };
};

const paymentQueryPageSizeOptions = (initialView: string) =>
  initialView === "finance-payment-query"
    ? [10, 15, 20, 50, 100, 200]
    : undefined;

const paymentQueryDefaultPageSize = (initialView: string) =>
  initialView === "finance-payment-query" ? 15 : undefined;

// Legacy FAS/FAM invoice controllers initialize every invoice list with
// PageSize=20 (audit/process/application lists alike).
const invoiceLegacyDefaultPageSize = (initialView: string) =>
  initialView.startsWith("finance-invoice") ? 20 : 15;
const invoiceLegacyErrorMessage = "查询出错.";
const settlementLegacyErrorMessage = "查询出错.";

const paymentQueryControlledPageSize = (
  initialView: string,
  selectedPageSize: number,
) =>
  initialView === "finance-payment-query" ? selectedPageSize : undefined;

const paymentQueryServerPagePlan = (page: number, pageSize: number) => {
  const safePage = Math.max(1, page);
  const safePageSize = Math.max(1, pageSize);
  if (safePageSize <= 100) {
    return [{ page: safePage, pageSize: safePageSize }];
  }
  const apiPageCount = Math.ceil(safePageSize / 100);
  const firstApiPage = (safePage - 1) * apiPageCount + 1;
  return Array.from({ length: apiPageCount }, (_value, index) => ({
    page: firstApiPage + index,
    pageSize: 100,
  }));
};

const paymentQueryPageTotal = (
  rows: ReadonlyArray<{
    data?: Record<string, any>;
    amount?: number | string;
  }>,
) =>
  rows
    .reduce(
      (sum, row) => sum + Number(row.data?.amount ?? row.amount ?? 0),
      0,
    )
    .toFixed(2);

const paymentQueryFeeTypeControl = (initialView: string): "feeType" | undefined =>
  initialView === "finance-payment-query" ? undefined : "feeType";

const settlementContextPageSize = 100;

const settlementContextTasksRequest = (caseId: number, page: number) => ({
  url: "/cases/" + caseId + "/tasks",
  params: { page, page_size: settlementContextPageSize },
});

const normalizeSettlementContextRows = (data: any) =>
  Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : [];

const effectivePaymentQuery = (
  initialView: string,
  query: Record<string, any>,
  knownFeeTypes: string[],
) => {
  const feeType = String(query.feeType || "").trim();
  if (
    initialView !== "finance-payment-query" ||
    !feeType ||
    knownFeeTypes.includes(feeType)
  ) {
    return query;
  }
  const next = { ...query };
  delete next.feeType;
  return next;
};

type PaymentPrintDocumentData = {
  documentTitle: string;
  packageNo: string;
  serialNo: string;
  paymentDate: string;
  feeTitle: string;
  attribute: string;
  feeType: string;
  customer: string;
  caseNo: string;
  contractNo: string;
  contractTitle: string;
  applicant: string;
  applicantDisplayName: string;
  payer: string;
  payerDisplayName: string;
  payee: string;
  amount: string;
  voucherNo: string;
  operator: string;
  operatorDisplayName: string;
  remark: string;
  creator: string;
  printTime: string;
};

const createPaymentPrintPreview = (
  row: Fee,
  transactions: Transaction[],
  creator: string,
  printTime: string,
): PaymentPrintDocumentData | null => {
  const payment = transactions
    .filter(
      (item) =>
        item.finance_record_id === row.id && item.transaction_type === "付款",
    )
    .sort((a, b) =>
      String(b.transaction_date).localeCompare(String(a.transaction_date)),
    )[0];
  if (!payment) return null;
  return {
    documentTitle: `${row.serial_no}付款单`,
    packageNo:
      row.data.payment_package_no || row.data.package_no || "",
    serialNo: row.serial_no,
    paymentDate: payment.transaction_date,
    feeTitle: row.title,
    attribute:
      row.data.attribute || row.data.property || row.data.expense_subtype || "",
    feeType:
      row.data.fee_type_name ||
      row.data.commission_type ||
      row.data.fee_type ||
      row.title,
    customer: row.customer,
    caseNo: row.data.case_no,
    contractNo: row.data.contract_no,
    contractTitle: row.data.contract_title || "",
    applicant: row.data.applicant || row.owner || "",
    applicantDisplayName:
      row.data.applicant_display_name || row.data.owner_display_name || "",
    payer: row.data.payer || row.data.payer_name || row.customer || "",
    payerDisplayName:
      row.data.payer_display_name || row.data.payer_name_display_name || "",
    payee: payment.counterparty || row.data.payee,
    amount: money(payment.amount || 0),
    voucherNo: payment.voucher_no,
    operator: payment.operator,
    operatorDisplayName: (payment as any).operator_display_name || "",
    remark: payment.remark || row.data.description || row.data.remark,
    creator,
    printTime,
  };
};

export default function FinanceCenterPage({
  initialView,
  platformMode = false,
  onNavigate,
}: {
  initialView: string;
  platformMode?: boolean;
  onNavigate?: (route: string) => void;
}) {
  const sessionUser = useMemo(initialSessionUser, []);
  const financeActionGates = useMemo(
    () => ({
      archiveSettlement: createFinanceActionGate(),
      generalSettlement: createFinanceActionGate(),
      paymentPackage: createFinanceActionGate(),
    }),
    [],
  );
  const refundRequestGuard = useMemo(() => createLatestRequestGuard(), []);
  const invoiceDetailRequestGuard = useMemo(() => createLatestRequestGuard(), []);
  const refundDetailRequestGuard = useMemo(() => createLatestRequestGuard(), []);
  const contractPaymentSourceSearch =
    initialView === "finance-payment-mine" && typeof window !== "undefined"
      ? window.location.search
      : "";
  const contractPaymentSource = useMemo(
    () =>
      parseContractPaymentSource(initialView, contractPaymentSourceSearch),
    [initialView, contractPaymentSourceSearch],
  );
  const first = initialView.startsWith("finance-audit")
    ? "audit"
    : initialView.startsWith("finance-receipts")
      ? "receipts"
      : initialView.startsWith("finance-invoice")
        ? "invoices"
        : initialView.startsWith("finance-refund")
          ? "refunds"
          : initialView.startsWith("finance-transactions")
            ? "transactions"
            : initialView.startsWith("finance-reconcile")
              ? "reconcile"
              : "fees";
  const [tab, setTab] = useState(first);
  const [fees, setFees] = useState<Fee[]>([]);
  const [financeFeeListMeta, setFinanceFeeListMeta] = useState({
    page: 1,
    pageSize: 100,
    total: 0,
  });
  const [contractPayments, setContractPayments] = useState<Fee[]>([]);
  const [contracts, setContracts] = useState<Fee[]>([]);
  const [invoiceCandidateFees, setInvoiceCandidateFees] = useState<Fee[]>([]);
  const [invoices, setInvoices] = useState<FinanceFlow[]>([]);
  const [refunds, setRefunds] = useState<FinanceFlow[]>([]);
  const [refundMeta, setRefundMeta] = useState({
    total: 0,
    page: 1,
    pageSize: 15,
  });
  const [selectedRefundRows, setSelectedRefundRows] = useState<number[]>([]);
  const [refundStatusFilter, setRefundStatusFilter] = useState("全部");
  const [refundGroupFilter, setRefundGroupFilter] = useState("");
  const [cases, setCases] = useState<Fee[]>([]);
  const financeFeeRefreshGuard = useMemo(() => createLatestRequestGuard(), []);
  const openCaseDetail = async (caseNo: unknown) => {
    const serialNo = String(caseNo || "").trim();
    if (!serialNo || serialNo === "—") {
      message.warning("当前记录未关联案件");
      return;
    }
    try {
      const { data } = await api.get("/records", { params: { module: "case", keyword: serialNo, page_size: 100 } });
      const record = (data.items as Fee[]).find((item) => item.serial_no === serialNo);
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
  const openContractDetail = async (contractNo: unknown) => {
    const serialNo = String(contractNo || "").trim();
    if (!serialNo || serialNo === "—") {
      message.warning("当前记录未关联合同");
      return;
    }
    try {
      const { data } = await api.get("/records", { params: { module: "contract", keyword: serialNo, page_size: 100 } });
      const record = (data.items as Fee[]).find((item) => item.serial_no === serialNo);
      if (!record) {
        message.warning("未找到关联合同或当前账号无权查看");
        return;
      }
      rememberContractDetailTarget({ id: record.id, serial_no: record.serial_no });
      onNavigate?.("contract-company");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "关联合同加载失败");
    }
  };
  const openCustomerDetail = async (customer: unknown, customerNo?: unknown) => {
    const title = String(customer || "").trim();
    const serialNo = String(customerNo || "").trim();
    if (!title && !serialNo) {
      message.warning("当前记录未关联客户");
      return;
    }
    try {
      const { data } = await api.get("/records", { params: { module: "customer", keyword: serialNo || title, page_size: 100 } });
      const record = (data.items as Fee[]).find((item) =>
        (serialNo && item.serial_no === serialNo) || (title && (item.title === title || item.customer === title)),
      );
      if (!record) {
        message.warning("未找到关联客户或当前账号无权查看");
        return;
      }
      rememberCustomerDetailTarget({ id: record.id, title: record.title, serial_no: record.serial_no });
      onNavigate?.("customer-company");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "关联客户加载失败");
    }
  };
  const openCaseTaskCreate = (source: any) => {
    const caseNo = String(source?.case_no || source?.data?.case_no || "").trim();
    if (!caseNo) {
      message.warning("当前费用未关联案件，无法新建案件任务");
      return;
    }
    window.sessionStorage.setItem("sunhold:task-create-context", JSON.stringify({
      case_no: caseNo,
      customer: String(source?.customer || source?.data?.customer || "").trim(),
      title: `案件费用跟进—${caseNo}`,
    }));
    onNavigate?.("task-my-created");
  };
  const [customers, setCustomers] = useState<Fee[]>([]);
  const [receivables, setReceivables] = useState<Receivable[]>([]);
  const [incoming, setIncoming] = useState<IncomingPayment[]>([]);
  const [selectedIncomingRows, setSelectedIncomingRows] = useState<number[]>([]);
  const [pendingSettlements, setPendingSettlements] = useState<Fee[]>([]);
  const [generalSettlementRows, setGeneralSettlementRows] = useState<Fee[]>([]);
  const [generalSettlementMeta, setGeneralSettlementMeta] = useState({
    total: 0,
    page: 1,
    pageSize: 10,
    totals: {} as Record<string, number>,
  });
  const [generalSettlementDetails, setGeneralSettlementDetails] = useState<
    (string | number)[]
  >([]);
  const [generalSettlementBusy, setGeneralSettlementBusy] = useState(false);
  const [generalSettlementReviewTargets, setGeneralSettlementReviewTargets] =
    useState<Fee[]>([]);
  const [generalSettlementReviewApproved, setGeneralSettlementReviewApproved] =
    useState(true);
  const [generalSettlementReviewComment, setGeneralSettlementReviewComment] =
    useState("");
  const [generalSettlementApplyTargets, setGeneralSettlementApplyTargets] =
    useState<(string | number)[]>([]);
  const [generalSettlementApplyComment, setGeneralSettlementApplyComment] =
    useState("");
  const [generalSettlementPaymentTargets, setGeneralSettlementPaymentTargets] =
    useState<Fee[]>([]);
  const [generalSettlementPaymentAction, setGeneralSettlementPaymentAction] =
    useState<"paid" | "rollback">("paid");
  const [generalSettlementPaymentComment, setGeneralSettlementPaymentComment] =
    useState("");
  const [generalSettlementReapplyTargets, setGeneralSettlementReapplyTargets] =
    useState<Fee[]>([]);
  const [generalSettlementReapplyComment, setGeneralSettlementReapplyComment] =
    useState("");
  const [archiveSettlementRows, setArchiveSettlementRows] = useState<any[]>([]);
  const [archiveSettlementMeta, setArchiveSettlementMeta] = useState({
    total: 0,
    page: 1,
    pageSize: 10,
    totals: {} as Record<string, number>,
  });
  const [archiveSettlementBusy, setArchiveSettlementBusy] = useState(false);
  const [archiveSettlementReviewTargets, setArchiveSettlementReviewTargets] =
    useState<any[]>([]);
  const [archiveSettlementReviewApproved, setArchiveSettlementReviewApproved] =
    useState(true);
  const [archiveSettlementReviewComment, setArchiveSettlementReviewComment] =
    useState("");
  const [archiveSettlementRollbackTargets, setArchiveSettlementRollbackTargets] =
    useState<any[]>([]);
  const [archiveSettlementRollbackComment, setArchiveSettlementRollbackComment] =
    useState("");
  const [archiveSettlementReapplyTargets, setArchiveSettlementReapplyTargets] =
    useState<any[]>([]);
  const [archiveSettlementReapplyComment, setArchiveSettlementReapplyComment] =
    useState("");
  const [refundReviewFees, setRefundReviewFees] = useState<Fee[]>([]);
  const [paymentPackages, setPaymentPackages] = useState<Fee[]>([]);
  const [paymentPackageMeta, setPaymentPackageMeta] = useState({
    total: 0,
    page: 1,
    pageSize: 15,
  });
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [reconciliations, setReconciliations] = useState<Reconciliation[]>([]);
  const [summary, setSummary] = useState<any>({
    fees: 0,
    pending: 0,
    approved: 0,
    paid: 0,
    total_fee_amount: 0,
    paid_amount: 0,
    invoice_amount: 0,
    refund_amount: 0,
  });
  const [legacyFinanceRows, setLegacyFinanceRows] = useState<LegacyFinanceRecord[]>([]);
  const [legacyFinanceMeta, setLegacyFinanceMeta] = useState({ total: 0, page: 1, pageSize: 30 });
  const [legacyFinanceSummary, setLegacyFinanceSummary] = useState<LegacyFinanceSummary>({
    records: [], allocations: [], audits: [], orphan_allocations: [], orphan_files: [], orphan_audits: [], amount_visible: false, read_only: true,
  });
  const [legacyFinanceLoading, setLegacyFinanceLoading] = useState(false);
  const [legacyFinanceKind, setLegacyFinanceKind] = useState("");
  const [legacyFinanceKeyword, setLegacyFinanceKeyword] = useState("");
  const [legacyFinanceStatusCode, setLegacyFinanceStatusCode] = useState("");
  const [legacyFinanceIncludeInactive, setLegacyFinanceIncludeInactive] = useState(false);
  const [legacyFinanceDetail, setLegacyFinanceDetail] = useState<LegacyFinanceRecord | null>(null);
  const [legacyFinanceDetailLoading, setLegacyFinanceDetailLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [financeDataReady, setFinanceDataReady] = useState(false);
  const [role, setRole] = useState(sessionUser.role || "user");
  const [currentUser, setCurrentUser] = useState({
    username: sessionUser.username || "",
    displayName: sessionUser.display_name || "",
  });
  const [financePeople, setFinancePeople] = useState<FinancePersonOption[]>([]);
  const financePersonNameMap = useMemo(() => {
    const names = new Map<string, string>();
    financePeople.forEach((person) => {
      const displayName = String(person.label || person.value || "").trim();
      if (!displayName) return;
      [person.username, person.value, person.label].forEach((identity) => {
        const key = String(identity || "").trim();
        if (key) names.set(key, displayName);
      });
    });
    if (currentUser.username && currentUser.displayName) {
      names.set(currentUser.username, currentUser.displayName);
    }
    return names;
  }, [financePeople, currentUser]);
  const financePersonDisplayName = (identity: unknown, displayName?: unknown) => {
    const explicitName = String(displayName || "").trim();
    if (explicitName) return explicitName;
    const key = String(identity || "").trim();
    if (!key) return "—";
    return financePersonNameMap.get(key) || (/[㐀-鿿]/.test(key) ? key : "—");
  };
  const financePersonDisplayNames = (identities: unknown, displayNames?: unknown) => {
    const values = Array.isArray(identities) ? identities : [identities];
    const names = Array.isArray(displayNames) ? displayNames : [];
    const rendered = values.filter(Boolean).map((value, index) => financePersonDisplayName(value, names[index]));
    return rendered.length ? rendered.join("、") : "—";
  };
  const dashboardFeeQuerySeed = useMemo(
    () => consumeDashboardFeeQuery(initialView),
    [initialView],
  );
  const [originalQueryDraft, setOriginalQueryDraft] = useState<
    Record<string, any>
  >(dashboardFeeQuerySeed);
  const [originalQuery, setOriginalQuery] = useState<Record<string, any>>(
    dashboardFeeQuerySeed,
  );
  const [paymentAuditPageSize, setPaymentAuditPageSize] = useState(15);
  const [paymentQueryQuickPage, setPaymentQueryQuickPage] = useState("1");
  const [paymentQueryPageSize, setPaymentQueryPageSize] = useState(
    paymentQueryDefaultPageSize(initialView) ?? 15,
  );
  const [paymentQueryMeta, setPaymentQueryMeta] = useState({
    total: 0,
    page: 1,
    pageSize: paymentQueryDefaultPageSize(initialView) ?? 15,
  });
  const [internalDetailRows, setInternalDetailRows] = useState<Fee[]>([]);
  const [internalDetailMeta, setInternalDetailMeta] = useState({
    total: 0,
    totalAmount: 0,
    page: 1,
    pageSize: 15,
  });
  const [invoiceMineRows, setInvoiceMineRows] = useState<FinanceFlow[]>([]);
  const [invoiceMineMeta, setInvoiceMineMeta] = useState({
    total: 0,
    totalAmount: 0,
    totalExtraAmount: 0,
    page: 1,
    pageSize: invoiceLegacyDefaultPageSize(initialView),
  });
  const [invoicePendingRows, setInvoicePendingRows] = useState<FinanceFlow[]>([]);
  const [invoicePendingMeta, setInvoicePendingMeta] = useState({
    total: 0,
    totalAmount: 0,
    totalExtraAmount: 0,
    page: 1,
    pageSize: invoiceLegacyDefaultPageSize(initialView),
  });
  const [invoiceCompanyRows, setInvoiceCompanyRows] = useState<FinanceFlow[]>([]);
  const [invoiceCompanyMeta, setInvoiceCompanyMeta] = useState({
    total: 0,
    totalAmount: 0,
    totalExtraAmount: 0,
    page: 1,
    pageSize: invoiceLegacyDefaultPageSize(initialView),
  });
  const [invoiceUnissuedRows, setInvoiceUnissuedRows] = useState<FinanceFlow[]>([]);
  const [invoiceUnissuedMeta, setInvoiceUnissuedMeta] = useState({
    total: 0,
    totalAmount: 0,
    totalInvoiceAmount: 0,
    totalCashedAmount: 0,
    totalPaidAmount: 0,
    page: 1,
    pageSize: invoiceLegacyDefaultPageSize(initialView),
  });
  const [feeQueryRows, setFeeQueryRows] = useState<Fee[]>([]);
  const [feeQueryMeta, setFeeQueryMeta] = useState({
    total: 0,
    page: 1,
    pageSize: 15,
    totals: {} as Record<string, number | null>,
  });
  const [feeQueryExportLoading, setFeeQueryExportLoading] = useState(false);
  const [refundCaseFeeStatusOpen, setRefundCaseFeeStatusOpen] = useState(false);
  const [refundCaseFeeStatus, setRefundCaseFeeStatus] = useState("R10");
  const [refundCaseFeeLogKind, setRefundCaseFeeLogKind] = useState<
    "court" | "received" | "other" | null
  >(null);
  const [refundCaseFeeLogContent, setRefundCaseFeeLogContent] = useState("");
  const [refundCaseFeeMutationLoading, setRefundCaseFeeMutationLoading] =
    useState(false);
  const [invoiceExportLoading, setInvoiceExportLoading] = useState(false);
  const [invoiceDetail, setInvoiceDetail] = useState<FinanceFlow | null>(null);
  const [refundDetail, setRefundDetail] = useState<FinanceFlow | null>(null);
  const [refundAmountTarget, setRefundAmountTarget] =
    useState<FinanceFlow | null>(null);
  const [refundBatchStatusOpen, setRefundBatchStatusOpen] = useState(false);
  const [refundBatchStatus, setRefundBatchStatus] = useState("待审批");
  const [refundMutationLoading, setRefundMutationLoading] = useState(false);
  const [invoiceProcess, setInvoiceProcess] = useState<FinanceFlow | null>(null);
  const [invoiceCancel, setInvoiceCancel] = useState<FinanceFlow | null>(null);
  const [invoiceCancelReason, setInvoiceCancelReason] = useState("");
  const [invoiceNumberTarget, setInvoiceNumberTarget] = useState<FinanceFlow | null>(null);
  const [invoiceDateTarget, setInvoiceDateTarget] = useState<FinanceFlow | null>(null);
  const [invoiceMutationLoading, setInvoiceMutationLoading] = useState(false);
  const [multiPickerOpen, setMultiPickerOpen] = useState<string | null>(null);
  const [multiPickerDraft, setMultiPickerDraft] = useState<
    Record<string, string[]>
  >({});
  const [internalDetailExportLoading, setInternalDetailExportLoading] =
    useState(false);
  const [selectedOriginalRows, setSelectedOriginalRows] = useState<
    (string | number)[]
  >([]);
  const [paymentPrintPreview, setPaymentPrintPreview] =
    useState<PaymentPrintDocumentData | null>(null);
  const [paymentWordExportLoading, setPaymentWordExportLoading] = useState(false);
  const [paymentPackagePreview, setPaymentPackagePreview] =
    useState<PaymentPackagePreview | null>(null);
  const [paymentPackageLoading, setPaymentPackageLoading] = useState(false);
  const [paymentPackageDetail, setPaymentPackageDetail] = useState<Fee | null>(
    null,
  );
  const [paymentPackageWriteoffTarget, setPaymentPackageWriteoffTarget] =
    useState<Fee | null>(null);
  const [feeReviewTargets, setFeeReviewTargets] = useState<Fee[]>([]);
  const [feeReviewComment, setFeeReviewComment] = useState("");
  const [feeReviewLoading, setFeeReviewLoading] = useState(false);
  const [paymentCancelTarget, setPaymentCancelTarget] = useState<Fee | null>(
    null,
  );
  const [paymentCancelReason, setPaymentCancelReason] = useState("");
  const [paymentRollbackTarget, setPaymentRollbackTarget] =
    useState<Fee | null>(null);
  const [paymentRollbackComment, setPaymentRollbackComment] = useState("");
  const [settlementBatchOpen, setSettlementBatchOpen] = useState(false);
  const [settlementContext, setSettlementContext] = useState<{
    mode: "tasks" | "logs" | "log-create" | "task-create";
    caseRecords: Fee[];
  } | null>(null);
  const [settlementLogContent, setSettlementLogContent] = useState("");
  const [settlementTaskForm, setSettlementTaskForm] = useState({
    title: "",
    owner: "",
    deadline: null as any,
    priority: "普通",
  });
  const [settlementContextRows, setSettlementContextRows] = useState<any[]>([]);
  const [settlementActionLoading, setSettlementActionLoading] = useState(false);
  const [refundBatchFeeOpen, setRefundBatchFeeOpen] = useState(false);
  const [refundBatchFeeStep, setRefundBatchFeeStep] = useState(0);
  const [refundBatchFeeLoading, setRefundBatchFeeLoading] = useState(false);
  const [refundBatchFeeKind, setRefundBatchFeeKind] = useState<"ordinary" | "internal">("ordinary");
  const [refundBatchFeeBaseType, setRefundBatchFeeBaseType] = useState<string>("官方费用");
  const [refundBatchFeeSubTypes, setRefundBatchFeeSubTypes] = useState<any[]>([]);
  const [refundBatchPaymentTypes, setRefundBatchPaymentTypes] = useState<any[]>([]);
  const [feeOpen, setFeeOpen] = useState(false);
  const [feeEditTarget, setFeeEditTarget] = useState<Fee | null>(null);
  const [feeDetail, setFeeDetail] = useState<Fee | null>(null);
  // Legacy PaymentView resolves the complete payment plus its contract,
  // customer and package before rendering. Fetch the canonical record for
  // payment-list detail actions instead of reusing a possibly truncated row.
  const openPaymentDetail = async (row: Fee) => {
    try {
      const { data } = await api.get(`/records/${row.id}`);
      if (!data || !["finance", "contract_payment"].includes(data.module)) {
        throw new Error("请款单详情记录无效");
      }
      const packageNo = String(
        data.data?.payment_package_no || data.data?.package_no || "",
      ).trim();
      let detail = data;
      if (packageNo) {
        try {
          const packageResponse = await api.get("/records", {
            params: { module: "finance_package", keyword: packageNo },
          });
          const paymentPackage = (packageResponse.data?.items || []).find(
            (item: Fee) =>
              item.module === "finance_package" &&
              (String(item.serial_no || "").trim() === packageNo ||
                String(item.data?.package_no || "").trim() === packageNo ||
                String(item.data?.payment_package_no || "").trim() === packageNo),
          );
          if (paymentPackage) {
            detail = {
              ...data,
              data: {
                ...data.data,
                package_no: data.data?.package_no || packageNo,
                payment_package_no:
                  data.data?.payment_package_no || packageNo,
                payment_package_context: paymentPackage,
              },
            };
          }
        } catch {
          detail = {
            ...data,
            data: {
              ...data.data,
              package_no: data.data?.package_no || packageNo,
              payment_package_no: data.data?.payment_package_no || packageNo,
            },
          };
        }
      }
      setFeeDetail(detail);
    } catch (error: any) {
      message.error(
        error?.response?.data?.detail ||
          error?.message ||
          "请款单详情加载失败",
      );
    }
  };
  const openInvoiceDetail = async (row: FinanceFlow) => {
    const token = invoiceDetailRequestGuard.begin();
    try {
      const { data } = await api.get(`/records/${row.id}`);
      if (!invoiceDetailRequestGuard.isLatest(token)) return;
      if (!data || data.module !== "invoice") {
        throw new Error("发票详情记录无效");
      }
      if (String(data.id) !== String(row.id)) {
        throw new Error("发票详情记录不匹配");
      }
      setInvoiceDetail(data);
    } catch (error: any) {
      if (invoiceDetailRequestGuard.isLatest(token)) {
        message.error(
          error?.response?.data?.detail || error?.message || "发票详情加载失败",
        );
      }
    }
  };
  const openRefundDetail = async (row: FinanceFlow) => {
    const token = refundDetailRequestGuard.begin();
    try {
      const { data } = await api.get(`/records/${row.id}`);
      if (!refundDetailRequestGuard.isLatest(token)) return;
      if (!data || data.module !== "refund") {
        throw new Error("退款详情记录无效");
      }
      if (String(data.id) !== String(row.id)) {
        throw new Error("退款详情记录不匹配");
      }
      setRefundDetail(data);
    } catch (error: any) {
      if (refundDetailRequestGuard.isLatest(token)) {
        message.error(
          error?.response?.data?.detail || error?.message || "退款详情加载失败",
        );
      }
    }
  };
  const [invoiceOpen, setInvoiceOpen] = useState(false);
  const [invoiceEditTarget, setInvoiceEditTarget] =
    useState<FinanceFlow | null>(null);
  const [invoiceSelectedFeeIds, setInvoiceSelectedFeeIds] = useState<number[]>([]);
  const [invoiceFeeAmounts, setInvoiceFeeAmounts] = useState<Record<number, number>>({});
  const [invoiceSourceFeeId, setInvoiceSourceFeeId] = useState<number | null>(null);
  const [refundOpen, setRefundOpen] = useState(false);
  const [invoiceForm] = Form.useForm();
  const [refundForm] = Form.useForm();
  useEffect(() => {
    const target = consumeBusinessRecordDetailTarget(["finance", "invoice", "refund", "finance_package", "finance_settlement", "finance_archive_settlement"]);
    if (!target) return;
    void (async () => {
      try {
        const { data } = await api.get(`/records/${target.id}`);
        if (data.module === "finance" && target.action === "create_invoice") {
          const [contractResponse, customerResponse, feeResponse] = await Promise.all([
            api.get("/records", { params: { module: "contract", page_size: 100 } }),
            api.get("/records", { params: { module: "customer", page_size: 100 } }),
            api.get("/finance/case-fees/invoice-status", { params: { scope: "company", invoice_status: "未开票", page: 1, page_size: 100, fee_types: "" } }),
          ]);
          const contractRows = Array.isArray(contractResponse.data?.items) ? contractResponse.data.items : [];
          const customerRows = Array.isArray(customerResponse.data?.items) ? customerResponse.data.items : [];
          const candidateRows = Array.isArray(feeResponse.data?.items) ? feeResponse.data.items : [];
          const sourceFee = candidateRows.find((fee: Fee) => Number(fee.id) === Number(data.id));
          setContracts(contractRows);
          setCustomers(customerRows);
          setInvoiceCandidateFees(candidateRows);
          setTab("invoices");
          if (!sourceFee) {
            message.warning("该费用当前不可申请开票（已申请、已开票或不在可开票范围内），未打开开票申请。");
            return;
          }
          invoiceForm.resetFields();
          invoiceForm.setFieldsValue({
            ...buildInvoiceSourceFields([sourceFee], contractRows, customerRows),
            case_fee_ids: [sourceFee.id],
            extra_amount: 0,
            invoice_type: "增值税普通发票",
            invoice_content: "法律服务费",
            delivery_method: "电子发票",
          });
          setInvoiceSelectedFeeIds([sourceFee.id]);
          setInvoiceFeeAmounts({ [sourceFee.id]: invoiceFeeAvailableAmount(sourceFee) });
          setInvoiceSourceFeeId(sourceFee.id);
          setInvoiceOpen(true);
          return;
        }
        if (data.module === "finance" && target.action === "create_refund") {
          const profile = await api.get("/auth/me");
          refundForm.resetFields();
          refundForm.setFieldsValue({
            fee_record_id: data.id,
            case_no: data.data?.case_no || "",
            customer: data.customer || "",
            court: data.data?.court || data.data?.payee || "",
            original_payment_no: data.data?.document_no || "",
            amount: Math.abs(Number(data.data?.amount || 0)) || undefined,
            applicant: profile.data?.display_name || data.owner_display_name || "姓名待维护",
            reason: "诉讼费退费",
          });
          setTab("refunds");
          setRefundOpen(true);
          return;
        }
        if (["finance", "finance_package", "finance_settlement", "finance_archive_settlement"].includes(data.module)) {
          setFeeDetail(data);
        } else if (data.module === "invoice") {
          setInvoiceDetail(data);
        } else if (data.module === "refund") {
          setRefundDetail(data);
        } else {
          throw new Error("关联记录不是可查看的财务业务");
        }
      } catch (error: any) {
        message.error(error?.response?.data?.detail || error?.message || "费用详情加载失败");
      }
    })();
  }, []);
  const [transactionOpen, setTransactionOpen] = useState(false);
  const [reconcileOpen, setReconcileOpen] = useState(false);
  const [incomingOpen, setIncomingOpen] = useState(false);
  const [claimTarget, setClaimTarget] = useState<IncomingPayment | null>(null);
  const [claimCustomers, setClaimCustomers] = useState<
    { id: number; title: string; serial_no: string }[]
  >([]);
  const [claimCustomersLoading, setClaimCustomersLoading] = useState(false);
  const claimCustomerSearchRequest = useRef(0);
  const [allocateTarget, setAllocateTarget] = useState<IncomingPayment | null>(
    null,
  );
  const [allocationCandidates, setAllocationCandidates] = useState<AllocationCandidate[]>([]);
  const [allocationLoading, setAllocationLoading] = useState(false);
  const [selectedAllocationKeys, setSelectedAllocationKeys] = useState<(string | number)[]>([]);
  const [allocationAmounts, setAllocationAmounts] = useState<Record<string, number>>({});
  const [allocationKeyword, setAllocationKeyword] = useState("");
  const [allocationStage, setAllocationStage] = useState("");
  const [allocationFeeType, setAllocationFeeType] = useState("");
  const [allocationComment, setAllocationComment] = useState("");
  const [allocationValidationError, setAllocationValidationError] = useState("");
  const [incomingAllocationTarget, setIncomingAllocationTarget] =
    useState<IncomingPayment | null>(null);
  const [incomingDetailTarget, setIncomingDetailTarget] =
    useState<IncomingPayment | null>(null);
  useEffect(() => {
    const paymentId = resolveIncomingPaymentDetailTarget(initialView);
    if (!paymentId) return;
    void api.get(`/finance/incoming-payments/${paymentId}`)
      .then(({ data }) => setIncomingDetailTarget(data))
      .catch((error: any) => message.error(error?.response?.data?.detail || "回款详情加载失败"));
  }, [initialView]);
  const [issueTarget, setIssueTarget] = useState<FinanceFlow | null>(null);
  const [voidTarget, setVoidTarget] = useState<FinanceFlow | null>(null);
  const [refundCompleteTarget, setRefundCompleteTarget] =
    useState<FinanceFlow | null>(null);
  const [recordFileTarget, setRecordFileTarget] = useState<FinanceFlow | null>(
    null,
  );
  const [recordFileTargets, setRecordFileTargets] = useState<FinanceFlow[]>([]);
  const [recordFiles, setRecordFiles] = useState<Attachment[]>([]);
  const [recordFile, setRecordFile] = useState<File | null>(null);
  const [recordUploadFiles, setRecordUploadFiles] = useState<File[]>([]);
  const [recordFileTypeTree, setRecordFileTypeTree] = useState<any[]>([]);
  const [voucherOpen, setVoucherOpen] = useState(false);
  const [voucherTarget, setVoucherTarget] = useState<Transaction | null>(null);
  const [voucherFile, setVoucherFile] = useState<File | null>(null);
  const [writeoffTarget, setWriteoffTarget] = useState<Fee | null>(null);
  const bankUploadRef = useRef<HTMLInputElement>(null);
  const [feeForm] = Form.useForm();
  const [issueForm] = Form.useForm();
  const [voidForm] = Form.useForm();
  const [invoiceNumberForm] = Form.useForm();
  const [invoiceDateForm] = Form.useForm();
  const [refundCompleteForm] = Form.useForm();
  const [refundAmountForm] = Form.useForm();
  const [transactionForm] = Form.useForm();
  const [reconcileForm] = Form.useForm();
  const [voucherForm] = Form.useForm();
  const [writeoffForm] = Form.useForm();
  const [paymentPackageWriteoffForm] = Form.useForm();
  const [recordFileForm] = Form.useForm();
  const [incomingForm] = Form.useForm();
  const [claimForm] = Form.useForm();
  const [settlementBatchForm] = Form.useForm();
  const [refundBatchFeeForm] = Form.useForm();
  const watchedFeeType = Form.useWatch("fee_type", feeForm);
  const [feeTypeOverride, setFeeTypeOverride] = useState("");
  const selectedFeeType = watchedFeeType || feeTypeOverride;
  const feeCommissionDetails = Form.useWatch("commission_details", feeForm) || [];
  const invoiceFeeOptions = useMemo(() => {
    if (!invoiceEditTarget) return invoiceCandidateFees;
    return Array.from(
      new Map([...invoiceCandidateFees, ...fees].map((fee) => [fee.id, fee])).values(),
    );
  }, [invoiceEditTarget, invoiceCandidateFees, fees]);
  const isInternalApprovalRoute = internalApprovalRoutes.includes(initialView);
  const isInternalDetailRoute = [
    "finance-internal-detail",
    "finance-internal-company",
  ].includes(initialView);
  const isInvoiceMineRoute = initialView === "finance-invoice-mine";
  const isInvoicePendingRoute = initialView === "finance-invoice-pending";
  const isInvoiceCompanyRoute = initialView === "finance-invoice-company";
  const isInvoiceUnissuedRoute = [
    "finance-invoice-unissued",
    "finance-invoice-company-unissued",
  ].includes(initialView);
  const isGeneralSettlementPendingRoute =
    initialView === "finance-settlement-pending";
  const isGeneralSettlementAuditRoute =
    initialView === "finance-settlement-audit";
  const isGeneralSettlementPaymentRoute =
    initialView === "finance-settlement-payment";
  const isGeneralSettlementPaidRoute =
    initialView === "finance-settlement-paid";
  const isGeneralSettlementRejectedRoute =
    initialView === "finance-settlement-refused";
  const isGeneralSettlementRoute =
    isGeneralSettlementPendingRoute ||
    isGeneralSettlementAuditRoute ||
    isGeneralSettlementPaymentRoute ||
    isGeneralSettlementPaidRoute ||
    isGeneralSettlementRejectedRoute;
  const isArchiveSettlementPendingRoute =
    initialView === "finance-archive-fee-pending";
  const isArchiveSettlementPaymentRoute =
    initialView === "finance-archive-fee-payment";
  const isArchiveSettlementPaidRoute =
    initialView === "finance-archive-fee-paid";
  const isArchiveSettlementRejectedRoute =
    initialView === "finance-archive-fee-refused";
  const isArchiveSettlementActiveRoute =
    isArchiveSettlementPendingRoute ||
    isArchiveSettlementPaymentRoute ||
    isArchiveSettlementPaidRoute ||
    isArchiveSettlementRejectedRoute;
  const isRefundCaseFeeRoute = initialView === "finance-refund";
  const isFeeQueryRoute = ["finance-fee-query", "finance-refund"].includes(initialView);
  const isRefundNotRequiredRoute = initialView === "finance-refund-not-required";
  const activeRefundStatus = refundStatusForRoute(initialView, refundStatusFilter);
  const generalSettlementParams = (
    query: Record<string, any>,
    page = 1,
    pageSize = 10,
  ) => {
    if (!isGeneralSettlementPendingRoute) {
      const receivedRange = query.routeField3;
      const appliedRange = query.routeField7;
      const reviewedRange = query.routeField11;
      const paidRange = query.routeField13;
      return {
        customer: query.routeField0 || "",
        case_no: query.routeField1 || "",
        customer_manager: query.routeField2 || "",
        received_from: receivedRange?.[0]?.format?.("YYYY-MM-DD") || undefined,
        received_to: receivedRange?.[1]?.format?.("YYYY-MM-DD") || undefined,
        payer: query.routeField4 || "",
        payment_method: query.routeField5 || "",
        applied_by: query.routeField6 || "",
        applied_from: appliedRange?.[0]?.format?.("YYYY-MM-DD") || undefined,
        applied_to: appliedRange?.[1]?.format?.("YYYY-MM-DD") || undefined,
        hearing_lawyer: query.routeField8 || "",
        assistant: query.routeField9 || "",
        reviewer: query.routeField10 || "",
        reviewed_from: reviewedRange?.[0]?.format?.("YYYY-MM-DD") || undefined,
        reviewed_to: reviewedRange?.[1]?.format?.("YYYY-MM-DD") || undefined,
        source_person: query.routeField12 || "",
        paid_from: paidRange?.[0]?.format?.("YYYY-MM-DD") || undefined,
        paid_to: paidRange?.[1]?.format?.("YYYY-MM-DD") || undefined,
        status: isGeneralSettlementPaidRoute
          ? "已付款"
          : isGeneralSettlementRejectedRoute
            ? "已拒绝,已退回,已驳回"
          : isGeneralSettlementPaymentRoute
            ? "待付款"
            : "待审批",
        page,
        page_size: pageSize,
      };
    }
    const receivedRange = query.routeField2;
    return {
      customer: query.routeField0 || "",
      case_no: query.routeField1 || "",
      received_from: receivedRange?.[0]?.format?.("YYYY-MM-DD") || undefined,
      received_to: receivedRange?.[1]?.format?.("YYYY-MM-DD") || undefined,
      payer: query.routeField3 || "",
      payment_method: query.routeField4 || "",
      case_customer: query.customerSecond || "",
      hearing_lawyer: query.routeField6 || "",
      assistant: query.routeField7 || "",
      customer_manager: query.routeField8 || "",
      source_person: query.routeField9 || "",
      page,
      page_size: pageSize,
    };
  };
  const loadGeneralSettlements = async (
    query: Record<string, any>,
    page = 1,
    pageSize = generalSettlementMeta.pageSize,
  ) => {
    const response = await api.get(
      isGeneralSettlementPendingRoute
        ? "/finance/general-settlements/pending"
        : "/finance/general-settlements/applications",
      {
      params: generalSettlementParams(query, page, pageSize),
      },
    );
    setGeneralSettlementRows(response.data.items || []);
    setGeneralSettlementMeta({
      total: response.data.total || 0,
      page: response.data.page || page,
      pageSize: response.data.page_size || pageSize,
      totals: response.data.totals || {},
    });
  };
  const archiveSettlementParams = (
    query: Record<string, any>,
    page = 1,
    pageSize = 10,
  ) => {
    const receivedRange = query.routeField3;
    const settledRange = query.routeField7;
    const archiveRange = query.routeField11;
    const archivePaymentRange = query.routeField12;
    return {
      case_type:
        query.routeField0 && query.routeField0 !== "请选择"
          ? query.routeField0
          : "",
      case_stage: query.routeField1 || "",
      payer: query.routeField2 || "",
      received_from: receivedRange?.[0]?.format?.("YYYY-MM-DD") || undefined,
      received_to: receivedRange?.[1]?.format?.("YYYY-MM-DD") || undefined,
      hearing_lawyer: query.routeField4 || "",
      assistant: query.routeField5 || "",
      submitted_by: query.routeField6 || "",
      ...(isArchiveSettlementRejectedRoute
        ? {
            submitted_from:
              settledRange?.[0]?.format?.("YYYY-MM-DD") || undefined,
            submitted_to:
              settledRange?.[1]?.format?.("YYYY-MM-DD") || undefined,
          }
        : {
            settled_from:
              settledRange?.[0]?.format?.("YYYY-MM-DD") || undefined,
            settled_to:
              settledRange?.[1]?.format?.("YYYY-MM-DD") || undefined,
          }),
      case_no: query.routeField8 || "",
      customer: query.routeField9 || "",
      reviewer: query.routeField10 || "",
      reviewed_from: isArchiveSettlementRejectedRoute
        ? archiveRange?.[0]?.format?.("YYYY-MM-DD") || undefined
        : undefined,
      reviewed_to: isArchiveSettlementRejectedRoute
        ? archiveRange?.[1]?.format?.("YYYY-MM-DD") || undefined
        : undefined,
      archive_from: archiveRange?.[0]?.format?.("YYYY-MM-DD") || undefined,
      archive_to: archiveRange?.[1]?.format?.("YYYY-MM-DD") || undefined,
      payment_from:
        archivePaymentRange?.[0]?.format?.("YYYY-MM-DD") || undefined,
      payment_to:
        archivePaymentRange?.[1]?.format?.("YYYY-MM-DD") || undefined,
      page,
      page_size: pageSize,
    };
  };
  const loadArchiveSettlements = async (
    query: Record<string, any>,
    page = 1,
    pageSize = archiveSettlementMeta.pageSize,
  ) => {
    const response = await api.get(
      isArchiveSettlementPaymentRoute
        ? "/finance/archive-settlements/payment"
        : isArchiveSettlementPaidRoute
          ? "/finance/archive-settlements/paid"
          : isArchiveSettlementRejectedRoute
            ? "/finance/archive-settlements/rejected"
            : "/finance/archive-settlements/pending",
      {
      params: archiveSettlementParams(query, page, pageSize),
      },
    );
    setArchiveSettlementRows(response.data.items || []);
    setArchiveSettlementMeta({
      total: response.data.total || 0,
      page: response.data.page || page,
      pageSize: response.data.page_size || pageSize,
      totals: response.data.totals || {},
    });
  };
  const feeQueryParams = (
    query: Record<string, any>,
    page = 1,
    pageSize = feeQueryMeta.pageSize,
  ) => {
    const refundRange = isRefundCaseFeeRoute ? query.routeField7 : query.routeField3;
    const paidRange = isRefundCaseFeeRoute ? query.routeField3 : query.routeField7;
    const listValue = (value: unknown) =>
      Array.isArray(value) ? value.join(",") : String(value || "");
    if (isRefundCaseFeeRoute) return {
      case_no: query.routeField0 || "",
      court_case_no: query.routeField1 || "",
      court_name: query.routeField2 || "",
      paid_from: paidRange?.[0]?.format?.("YYYY-MM-DD") || undefined,
      paid_to: paidRange?.[1]?.format?.("YYYY-MM-DD") || undefined,
      customer: query.routeField4 || "",
      paid_organization: query.routeField5 || "",
      refund_status: query.routeField6 || "",
      refund_amount_from: refundRange?.[0] ?? undefined,
      refund_amount_to: refundRange?.[1] ?? undefined,
      hearing_lawyer: query.routeField8 || "",
      assistant: query.routeField9 || "",
      case_stages: listValue(query.routeField10),
      fee_types: listValue(query.routeField11),
      page,
      page_size: pageSize,
    };
    return {
      scope: query.dashboardScope || "company",
      unpaid_official: query.dashboardUnpaidOfficial || undefined,
      case_no: query.routeField0 || "",
      court_case_no: query.routeField1 || "",
      notary_no: query.routeField2 || "",
      refund_amount_from: refundRange?.[0] ?? undefined,
      refund_amount_to: refundRange?.[1] ?? undefined,
      customer: query.routeField4 || "",
      paid_organization: query.routeField5 || "",
      payment_status: query.routeField6 || "",
      paid_from: paidRange?.[0]?.format?.("YYYY-MM-DD") || undefined,
      paid_to: paidRange?.[1]?.format?.("YYYY-MM-DD") || undefined,
      hearing_lawyer: query.routeField8 || "",
      assistant: query.routeField9 || "",
      case_stages: listValue(query.routeField10),
      fee_types: listValue(query.routeField11),
      page,
      page_size: pageSize,
    };
  };
  const loadFeeQuery = async (
    query: Record<string, any>,
    page = 1,
    pageSize = feeQueryMeta.pageSize,
  ) => {
    const response = await api.get(
      isRefundCaseFeeRoute
        ? "/finance/case-fees/refunds"
        : "/finance/fees/query", {
      params: feeQueryParams(query, page, pageSize),
      },
    );
    setFeeQueryRows(response.data.items || []);
    setFeeQueryMeta({
      total: response.data.total || 0,
      page: response.data.page || page,
      pageSize: response.data.page_size || pageSize,
      totals: response.data.totals || {},
    });
  };
  const internalDetailParams = (
    query: Record<string, any>,
    page = 1,
    pageSize = 15,
  ) => {
    const paidRange = query.routeField8;
    const listValue = (value: unknown) =>
      Array.isArray(value) ? value.join(",") : String(value || "");
    return {
      scope: initialView === "finance-internal-detail" ? "mine" : "company",
      case_no: query.routeField0 || "",
      handling_lawyer: query.routeField1 || "",
      assistant: query.routeField2 || "",
      source_person: query.routeField3 || "",
      customer: query.routeField4 || "",
      customer_manager: query.routeField5 || "",
      investigator: query.routeField6 || "",
      payment_status:
        query.routeField7 && query.routeField7 !== "全部"
          ? query.routeField7
          : "",
      paid_from: paidRange?.[0]?.format?.("YYYY-MM-DD") || undefined,
      paid_to: paidRange?.[1]?.format?.("YYYY-MM-DD") || undefined,
      payee:
        query.routeField9 ||
        (initialView === "finance-internal-detail"
          ? currentUser.displayName || "姓名待维护"
          : ""),
      case_stages: listValue(query.routeField10),
      fee_types: listValue(query.routeField11),
      page,
      page_size: pageSize,
    };
  };
  const loadInternalDetails = async (
    query: Record<string, any>,
    page = 1,
    pageSize = internalDetailMeta.pageSize,
  ) => {
    const response = await api.get("/finance/internal-fees", {
      params: internalDetailParams(query, page, pageSize),
    });
    setInternalDetailRows(response.data.items || []);
    setInternalDetailMeta({
      total: response.data.total || 0,
      totalAmount: Number(response.data.total_amount || 0),
      page: response.data.page || page,
      pageSize: response.data.page_size || pageSize,
    });
  };
  const invoiceMineParams = (
    query: Record<string, any>,
    page = 1,
    pageSize = invoiceLegacyDefaultPageSize(initialView),
  ) => {
    const invoiceRange = query.routeField6;
    return {
      scope: "mine",
      customer: query.routeField0 || "",
      application_no: query.routeField1 || "",
      invoice_type: query.routeField2 || "",
      invoice_title: query.routeField3 || "",
      invoice_no: query.routeField4 || "",
      invoice_status: query.routeField5 || "",
      invoiced_from: invoiceRange?.[0]?.format?.("YYYY-MM-DD") || undefined,
      invoiced_to: invoiceRange?.[1]?.format?.("YYYY-MM-DD") || undefined,
      case_no: query.routeField7 || "",
      page,
      page_size: pageSize,
    };
  };
  const loadInvoiceMine = async (
    query: Record<string, any>,
    page = 1,
    pageSize = invoiceMineMeta.pageSize,
  ) => {
    const response = await api.get("/finance/invoices", {
      params: invoiceMineParams(query, page, pageSize),
    });
    setInvoiceMineRows(response.data.items || []);
    setInvoiceMineMeta({
      total: response.data.total || 0,
      totalAmount: Number(response.data.total_amount || 0),
      totalExtraAmount: Number(response.data.total_extra_amount || 0),
      page: response.data.page || page,
      pageSize: response.data.page_size || pageSize,
    });
  };
  const invoicePendingParams = (
    query: Record<string, any>,
    page = 1,
    pageSize = invoiceLegacyDefaultPageSize(initialView),
  ) => {
    const invoiceRange = query.routeField6;
    return {
      scope: "pending",
      customer: query.routeField0 || "",
      application_no: query.routeField1 || "",
      invoice_type: query.routeField2 || "",
      invoice_title: query.routeField3 || "",
      invoice_no: query.routeField4 || "",
      invoice_status: query.routeField5 || "",
      invoiced_from: invoiceRange?.[0]?.format?.("YYYY-MM-DD") || undefined,
      invoiced_to: invoiceRange?.[1]?.format?.("YYYY-MM-DD") || undefined,
      applicant: query.routeField7 || "",
      case_no: query.routeField8 || "",
      page,
      page_size: pageSize,
    };
  };
  const invoiceCompanyParams = (
    query: Record<string, any>,
    page = 1,
    pageSize = invoiceLegacyDefaultPageSize(initialView),
  ) => {
    const invoiceRange = query.routeField6;
    return {
      scope: "company",
      customer: query.routeField0 || "",
      application_no: query.routeField1 || "",
      invoice_type: query.routeField2 || "",
      invoice_title: query.routeField3 || "",
      invoice_no: query.routeField4 || "",
      invoice_status: query.routeField5 || "",
      invoiced_from: invoiceRange?.[0]?.format?.("YYYY-MM-DD") || undefined,
      invoiced_to: invoiceRange?.[1]?.format?.("YYYY-MM-DD") || undefined,
      applicant: query.routeField7 || "",
      case_no: query.routeField8 || "",
      page,
      page_size: pageSize,
    };
  };
  const loadInvoiceCompany = async (
    query: Record<string, any>,
    page = 1,
    pageSize = invoiceCompanyMeta.pageSize,
  ) => {
    const response = await api.get("/finance/invoices", {
      params: invoiceCompanyParams(query, page, pageSize),
    });
    setInvoiceCompanyRows(response.data.items || []);
    setInvoiceCompanyMeta({
      total: response.data.total || 0,
      totalAmount: Number(response.data.total_amount || 0),
      totalExtraAmount: Number(response.data.total_extra_amount || 0),
      page: response.data.page || page,
      pageSize: response.data.page_size || pageSize,
    });
  };
  const invoiceUnissuedParams = (
    query: Record<string, any>,
    page = 1,
    pageSize = invoiceLegacyDefaultPageSize(initialView),
  ) => {
    const invoiceAmount = query.routeField3;
    const invoiceRange = query.routeField7;
    const paidRange = query.routeField11;
    const cashedRange = query.routeField14;
    const listValue = (value: unknown) =>
      Array.isArray(value) ? value.join(",") : String(value || "");
    return {
      scope:
        initialView === "finance-invoice-company-unissued"
          ? "company"
          : "mine",
      case_no: query.routeField0 || "",
      court_case_no: query.routeField1 || "",
      notary_no: query.routeField2 || "",
      invoice_amount_from: invoiceAmount?.[0] ?? undefined,
      invoice_amount_to: invoiceAmount?.[1] ?? undefined,
      customer: query.routeField4 || "",
      paid_organization: query.routeField5 || "",
      invoice_status: query.routeField6 || "未开票",
      invoice_from: invoiceRange?.[0]?.format?.("YYYY-MM-DD") || undefined,
      invoice_to: invoiceRange?.[1]?.format?.("YYYY-MM-DD") || undefined,
      hearing_lawyer: query.routeField8 || "",
      assistant: query.routeField9 || "",
      case_stages: listValue(query.routeField10),
      paid_from: paidRange?.[0]?.format?.("YYYY-MM-DD") || undefined,
      paid_to: paidRange?.[1]?.format?.("YYYY-MM-DD") || undefined,
      fee_types: listValue(query.routeField12) || "律师代理费",
      payer_name: query.routeField13 || "",
      cashed_from: cashedRange?.[0]?.format?.("YYYY-MM-DD") || undefined,
      cashed_to: cashedRange?.[1]?.format?.("YYYY-MM-DD") || undefined,
      page,
      page_size: pageSize,
    };
  };
  const loadInvoiceUnissued = async (
    query: Record<string, any>,
    page = 1,
    pageSize = invoiceUnissuedMeta.pageSize,
  ) => {
    const response = await api.get("/finance/case-fees/invoice-status", {
      params: invoiceUnissuedParams(query, page, pageSize),
    });
    setInvoiceUnissuedRows(response.data.items || []);
    setInvoiceUnissuedMeta({
      total: response.data.total || 0,
      totalAmount: Number(response.data.totals?.amount || 0),
      totalInvoiceAmount: Number(response.data.totals?.invoice_amount || 0),
      totalCashedAmount: Number(response.data.totals?.cashed_amount || 0),
      totalPaidAmount: Number(response.data.totals?.paid_amount || 0),
      page: response.data.page || page,
      pageSize: response.data.page_size || pageSize,
    });
  };
  const loadInvoicePending = async (
    query: Record<string, any>,
    page = 1,
    pageSize = invoicePendingMeta.pageSize,
  ) => {
    const response = await api.get("/finance/invoices", {
      params: invoicePendingParams(query, page, pageSize),
    });
    setInvoicePendingRows(response.data.items || []);
    setInvoicePendingMeta({
      total: response.data.total || 0,
      totalAmount: Number(response.data.total_amount || 0),
      totalExtraAmount: Number(response.data.total_extra_amount || 0),
      page: response.data.page || page,
      pageSize: response.data.page_size || pageSize,
    });
  };
  const loadPaymentQueryPage = async (
    query: Record<string, any>,
    page = 1,
    pageSize = paymentQueryPageSize,
  ) => {
    const requests = paymentQueryServerPagePlan(page, pageSize);
    const responses = await Promise.all(
      requests.flatMap((request) => [
        api.get("/records", {
          params: paymentQueryRequestParams(query, request.page, request.pageSize),
        }),
        api.get("/records", {
          params: contractPaymentQueryRequestParams(
            query,
            request.page,
            request.pageSize,
          ),
        }),
      ]),
    );
    const seen = new Set<string>();
    const mergedItems = responses
      .flatMap((response) => response.data?.items || [])
      .filter((item: Fee) => {
        const key = String(item.module || item.data?._source_module || "finance") + ":" + String(item.id);
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });
    return {
      data: {
        items: mergedItems.slice(0, pageSize),
        total: responses.reduce(
          (sum, response) => sum + Number(response.data?.total || 0),
          0,
        ),
        page,
        page_size: pageSize,
      },
    };
  };
  const loadPaymentPackages = async (
    query: Record<string, any>,
    page = 1,
    pageSize = paymentPackageMeta.pageSize,
  ) => {
    const response = await api.get("/finance/payment-packages", {
      params: paymentPackageRequestParams(initialView, query, page, pageSize),
    });
    const normalized = normalizePaymentPackageResponse(response.data, page, pageSize);
    setPaymentPackages(normalized.items);
    setPaymentPackageMeta(normalized);
    return response;
  };
  const loadRefunds = async (
    page = 1,
    pageSize = refundMeta.pageSize,
    status = refundStatusForRoute(initialView, refundStatusFilter),
    preserveOnError = false,
    group = refundGroupFilter,
  ) => {
    const requestToken = refundRequestGuard.begin();
    try {
      const request = refundListRequest(page, pageSize, status, group);
      const response = await api.get(request.url, { params: request.params });
      if (!refundRequestGuard.isLatest(requestToken)) {
        return { applied: false, response: null };
      }
      const normalized = normalizeRefundResponse(response.data, page, pageSize);
      setRefunds(normalized.items);
      setRefundMeta(normalized);
      setSelectedRefundRows([]);
      return { applied: true, response };
    } catch (error: any) {
      if (!refundRequestGuard.isLatest(requestToken)) {
        return { applied: false, response: null };
      }
      const failure = refundLoadFailure(
        {
          items: refunds,
          total: refundMeta.total,
          page: refundMeta.page,
          pageSize: refundMeta.pageSize,
        },
        error,
      );
      message.error(failure.message);
      if (!preserveOnError) throw error;
      return { applied: false, response: null };
    }
  };
  const refreshRefundList = async (page = refundMeta.page) => {
    return refreshRefundListWithFallback({
      load: loadRefunds,
      page,
      pageSize: refundMeta.pageSize,
      status: activeRefundStatus,
      group: refundGroupFilter,
    });
  };
  const load = async () => {
    setLoading(true);
    setFinanceDataReady(false);
    try {
      const [
        feeRes,
        contractPaymentRes,
        invoiceRes,
        refundRes,
        caseRes,
        customerRes,
        receivableRes,
        incomingRes,
        txRes,
        recRes,
        sumRes,
        profileRes,
        settlementRes,
        refundReviewRes,
        paymentPackageRes,
        internalDetailRes,
        invoiceMineRes,
        invoicePendingRes,
        invoiceCompanyRes,
        invoiceUnissuedRes,
        generalSettlementRes,
        archiveSettlementRes,
        feeQueryRes,
        peopleRes,
      ] = await Promise.all([
        initialView === "finance-payment-query"
          ? loadPaymentQueryPage({}, 1, paymentQueryPageSize)
          : api.get("/records", { params: { module: "finance", page_size: 100 } }),
        initialView === "finance-payment-query"
          ? Promise.resolve({
              data: {
                items: [],
                total: 0,
                page: 1,
                page_size: paymentQueryPageSize,
              },
            })
          : contractPaymentSource.active && contractPaymentSource.ok
            ? api.get(`/finance/payment-source/${contractPaymentSource.sourceId}`, {
                params: {
                  payment_no: contractPaymentSource.paymentNo,
                  contract_no: contractPaymentSource.contractNo,
                  customer: contractPaymentSource.customer,
                  amount: contractPaymentSource.amount,
                },
              })
          : api.get("/records", { params: { module: "contract_payment", page_size: 100 } }),
        api.get("/records", { params: { module: "invoice", page_size: 100 } }),
        loadRefunds(
          1,
          refundMeta.pageSize,
          activeRefundStatus,
          isRefundNotRequiredRoute,
        ),
        api.get("/records", { params: { module: "case", page_size: 100 } }),
        api.get("/records", { params: { module: "customer", page_size: 100 } }),
        api.get("/receivables"),
        api.get("/finance/incoming-payments"),
        api.get("/finance/transactions"),
        api.get("/finance/reconciliations"),
        api.get("/finance/summary"),
        api.get("/auth/me"),
        api.get("/finance/settlements/pending"),
        api.get("/finance/fees/refund-review-candidates"),
        api.get("/finance/payment-packages", {
          params: paymentPackageRequestParams(
            initialView,
            initialView === "finance-internal-writeoff"
              ? { status: "待核销" }
              : {},
            1,
            paymentPackageMeta.pageSize,
          ),
        }),
        isInternalDetailRoute
          ? api.get("/finance/internal-fees", {
              params: internalDetailParams(
                initialView === "finance-internal-detail"
                  ? {
                      routeField7: "全部",
                      routeField9:
                        currentUser.displayName || "姓名待维护",
                    }
                  : { routeField7: "全部" },
                1,
                15,
              ),
            })
          : Promise.resolve({
              data: {
                items: [],
                total: 0,
                total_amount: 0,
                page: 1,
                page_size: 15,
              },
            }),
        isInvoiceMineRoute
          ? api.get("/finance/invoices", {
              params: invoiceMineParams({}, 1, invoiceLegacyDefaultPageSize(initialView)),
            })
          : Promise.resolve({
              data: {
                items: [],
                total: 0,
                total_amount: 0,
                total_extra_amount: 0,
                page: 1,
                page_size: invoiceLegacyDefaultPageSize(initialView),
              },
            }),
        isInvoicePendingRoute
          ? api.get("/finance/invoices", {
              params: invoicePendingParams({}, 1, invoiceLegacyDefaultPageSize(initialView)),
            })
          : Promise.resolve({
              data: {
                items: [],
                total: 0,
                total_amount: 0,
                total_extra_amount: 0,
                page: 1,
                page_size: invoiceLegacyDefaultPageSize(initialView),
              },
            }),
        isInvoiceCompanyRoute
          ? api.get("/finance/invoices", {
              params: invoiceCompanyParams({}, 1, invoiceLegacyDefaultPageSize(initialView)),
            })
          : Promise.resolve({
              data: {
                items: [],
                total: 0,
                total_amount: 0,
                total_extra_amount: 0,
                page: 1,
                page_size: invoiceLegacyDefaultPageSize(initialView),
              },
            }),
        isInvoiceUnissuedRoute
          ? api.get("/finance/case-fees/invoice-status", {
              params: invoiceUnissuedParams(
                {
                  routeField6: "未开票",
                  routeField12: ["律师代理费"],
                },
                1,
                invoiceLegacyDefaultPageSize(initialView),
              ),
            })
          : Promise.resolve({
              data: {
                items: [],
                total: 0,
                totals: {},
                page: 1,
                page_size: invoiceLegacyDefaultPageSize(initialView),
              },
            }),
        isGeneralSettlementRoute
          ? api.get(
              isGeneralSettlementPendingRoute
                ? "/finance/general-settlements/pending"
                : "/finance/general-settlements/applications",
              { params: generalSettlementParams({}, 1, 10) },
            )
          : Promise.resolve({
              data: { items: [], total: 0, totals: {}, page: 1, page_size: 10 },
            }),
        isArchiveSettlementActiveRoute
          ? api.get(
              isArchiveSettlementPaymentRoute
                ? "/finance/archive-settlements/payment"
                : isArchiveSettlementPaidRoute
                  ? "/finance/archive-settlements/paid"
                  : isArchiveSettlementRejectedRoute
                    ? "/finance/archive-settlements/rejected"
                    : "/finance/archive-settlements/pending",
              {
              params: archiveSettlementParams({}, 1, 10),
              },
            )
          : Promise.resolve({
              data: { items: [], total: 0, totals: {}, page: 1, page_size: 10 },
            }),
        isFeeQueryRoute
          ? api.get(isRefundCaseFeeRoute ? "/finance/case-fees/refunds" : "/finance/fees/query", {
              params: feeQueryParams(dashboardFeeQuerySeed, 1, 15),
            })
          : Promise.resolve({
              data: { items: [], total: 0, totals: {}, page: 1, page_size: 15 },
            }),
        api.get("/people/options").catch(() => ({ data: { items: [] } })),
      ]);
      setFees(feeRes.data.items);
      setFinanceFeeListMeta({
        page: Number(feeRes.data.page || 1),
        pageSize: Number(feeRes.data.page_size || 100),
        total: Number(feeRes.data.total || feeRes.data.items?.length || 0),
      });
      if (initialView === "finance-payment-query") {
        setPaymentQueryMeta({
          total: Number(feeRes.data.total || 0),
          page: Number(feeRes.data.page || 1),
          pageSize: Number(feeRes.data.page_size || paymentQueryPageSize),
        });
      }
      const contractPaymentItems = contractPaymentSource.active && contractPaymentSource.ok
        ? [contractPaymentRes.data]
        : contractPaymentRes.data.items || [];
      setContractPayments(
        contractPaymentItems.map((item: Fee) => ({
          ...item,
          data: {
            ...(item.data || {}),
            _source_module: "contract_payment",
            fee_type: item.data?.lines?.[0]?.fee_type || item.data?.payment_type,
            case_no: item.data?.lines?.[0]?.case_no,
            amount: item.data?.amount,
          },
        })),
      );
      setInvoices(invoiceRes.data.items);
      if (refundRes?.applied && refundRes.response) {
        const normalizedRefunds = normalizeRefundResponse(
          refundRes.response.data,
          1,
          refundMeta.pageSize,
        );
        setRefunds(normalizedRefunds.items);
        setRefundMeta(normalizedRefunds);
        setSelectedRefundRows([]);
      }
      setCases(caseRes.data.items);
      setCustomers(customerRes.data.items);
      setReceivables(receivableRes.data.items);
      setIncoming(incomingRes.data.items);
      setSelectedIncomingRows([]);
      setTransactions(txRes.data.items);
      setReconciliations(recRes.data.items);
      setSummary(sumRes.data);
      setRole(profileRes.data.role);
      setCurrentUser({
        username: profileRes.data.username || "",
        displayName: profileRes.data.display_name || "",
      });
      setFinancePeople(peopleRes.data.items || []);
      setPendingSettlements(settlementRes.data.items);
      setRefundReviewFees(refundReviewRes.data.items);
      const normalizedPaymentPackages = normalizePaymentPackageResponse(
        paymentPackageRes.data,
        1,
        paymentPackageMeta.pageSize,
      );
      setPaymentPackages(normalizedPaymentPackages.items);
      setPaymentPackageMeta(normalizedPaymentPackages);
      if (isInternalDetailRoute) {
        setInternalDetailRows(internalDetailRes.data.items || []);
        setInternalDetailMeta({
          total: internalDetailRes.data.total || 0,
          totalAmount: Number(internalDetailRes.data.total_amount || 0),
          page: internalDetailRes.data.page || 1,
          pageSize: internalDetailRes.data.page_size || 15,
        });
      }
      if (isInvoiceMineRoute) {
        setInvoiceMineRows(invoiceMineRes.data.items || []);
        setInvoiceMineMeta({
          total: invoiceMineRes.data.total || 0,
          totalAmount: Number(invoiceMineRes.data.total_amount || 0),
          totalExtraAmount: Number(
            invoiceMineRes.data.total_extra_amount || 0,
          ),
          page: invoiceMineRes.data.page || 1,
          pageSize: invoiceMineRes.data.page_size || 15,
        });
      }
      if (isInvoicePendingRoute) {
        setInvoicePendingRows(invoicePendingRes.data.items || []);
        setInvoicePendingMeta({
          total: invoicePendingRes.data.total || 0,
          totalAmount: Number(invoicePendingRes.data.total_amount || 0),
          totalExtraAmount: Number(
            invoicePendingRes.data.total_extra_amount || 0,
          ),
          page: invoicePendingRes.data.page || 1,
          pageSize: invoicePendingRes.data.page_size || 15,
        });
      }
      if (isInvoiceCompanyRoute) {
        setInvoiceCompanyRows(invoiceCompanyRes.data.items || []);
        setInvoiceCompanyMeta({
          total: invoiceCompanyRes.data.total || 0,
          totalAmount: Number(invoiceCompanyRes.data.total_amount || 0),
          totalExtraAmount: Number(
            invoiceCompanyRes.data.total_extra_amount || 0,
          ),
          page: invoiceCompanyRes.data.page || 1,
          pageSize: invoiceCompanyRes.data.page_size || 15,
        });
      }
      if (isInvoiceUnissuedRoute) {
        setInvoiceUnissuedRows(invoiceUnissuedRes.data.items || []);
        setInvoiceUnissuedMeta({
          total: invoiceUnissuedRes.data.total || 0,
          totalAmount: Number(invoiceUnissuedRes.data.totals?.amount || 0),
          totalInvoiceAmount: Number(
            invoiceUnissuedRes.data.totals?.invoice_amount || 0,
          ),
          totalCashedAmount: Number(
            invoiceUnissuedRes.data.totals?.cashed_amount || 0,
          ),
          totalPaidAmount: Number(
            invoiceUnissuedRes.data.totals?.paid_amount || 0,
          ),
          page: invoiceUnissuedRes.data.page || 1,
          pageSize: invoiceUnissuedRes.data.page_size || 15,
        });
      }
      if (isGeneralSettlementRoute) {
        setGeneralSettlementRows(generalSettlementRes.data.items || []);
        setGeneralSettlementMeta({
          total: generalSettlementRes.data.total || 0,
          page: generalSettlementRes.data.page || 1,
          pageSize: generalSettlementRes.data.page_size || 10,
          totals: generalSettlementRes.data.totals || {},
        });
      }
      if (isArchiveSettlementActiveRoute) {
        setArchiveSettlementRows(archiveSettlementRes.data.items || []);
        setArchiveSettlementMeta({
          total: archiveSettlementRes.data.total || 0,
          page: archiveSettlementRes.data.page || 1,
          pageSize: archiveSettlementRes.data.page_size || 10,
          totals: archiveSettlementRes.data.totals || {},
        });
      }
      if (isFeeQueryRoute) {
        setFeeQueryRows(feeQueryRes.data.items || []);
        setFeeQueryMeta({
          total: feeQueryRes.data.total || 0,
          page: feeQueryRes.data.page || 1,
          pageSize: feeQueryRes.data.page_size || 15,
          totals: feeQueryRes.data.totals || {},
        });
      }
    } catch {
      message.error("财务中心数据加载失败");
    } finally {
      setLoading(false);
      setFinanceDataReady(true);
    }
  };
  const loadLegacyFinanceHistory = async (
    page = legacyFinanceMeta.page,
    pageSize = legacyFinanceMeta.pageSize,
  ) => {
    setLegacyFinanceLoading(true);
    try {
      const [listRes, summaryRes] = await Promise.all([
        api.get("/finance/legacy-history", {
          params: {
            record_kind: legacyFinanceKind,
            status_code: legacyFinanceStatusCode.trim(),
            keyword: legacyFinanceKeyword.trim(),
            include_inactive: legacyFinanceIncludeInactive,
            page,
            page_size: pageSize,
          },
        }),
        api.get("/finance/legacy-history/summary"),
      ]);
      setLegacyFinanceRows(listRes.data.items || []);
      setLegacyFinanceMeta({
        total: Number(listRes.data.total || 0),
        page: Number(listRes.data.page || page),
        pageSize: Number(listRes.data.page_size || pageSize),
      });
      setLegacyFinanceSummary(summaryRes.data);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "历史财务账本加载失败");
    } finally {
      setLegacyFinanceLoading(false);
    }
  };
  const openLegacyFinanceDetail = async (recordId: number) => {
    setLegacyFinanceDetailLoading(true);
    setLegacyFinanceDetail(null);
    try {
      const { data } = await api.get(`/finance/legacy-history/${recordId}`);
      setLegacyFinanceDetail(data);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "历史财务明细加载失败");
    } finally {
      setLegacyFinanceDetailLoading(false);
    }
  };
  useEffect(() => {
    setTab(first);
    const defaults =
      contractPaymentSource.active && contractPaymentSource.ok
        ? {
            paymentNo: contractPaymentSource.paymentNo,
            contractNo: contractPaymentSource.contractNo,
            customer: contractPaymentSource.customer,
          }
      : initialView === "finance-payment-audit"
        ? { status: "待审批" }
        : initialView === "finance-payment-waiting"
          ? { status: "待付款" }
          : initialView === "finance-payment-print"
            ? { status: "已付款" }
      : initialView === "finance-payment-writeoff"
              ? { status: "待核销" }
              : initialView === "finance-internal-archive"
                ? { routeField1: "待归档" }
              : initialView === "finance-internal-refund-audit"
                ? { routeField1: "待审批" }
                : initialView === "finance-internal-detail"
                  ? {
                      routeField7: "全部",
                      routeField9:
                        currentUser.displayName || "姓名待维护",
                    }
                  : initialView === "finance-internal-company"
                    ? { routeField7: "全部" }
                    : isInvoiceUnissuedRoute
                      ? {
                          routeField6: "未开票",
                          routeField12: ["律师代理费"],
                        }
                    : isArchiveSettlementActiveRoute
                      ? { routeField0: "请选择" }
                      : isFeeQueryRoute
                        ? dashboardFeeQuerySeed
                        : {};
    setOriginalQueryDraft(defaults);
    setOriginalQuery(defaults);
    setSelectedOriginalRows([]);
    setPaymentPrintPreview(null);
    setPaymentPackagePreview(null);
    setPaymentPackageDetail(null);
    setPaymentPackageWriteoffTarget(null);
    setPaymentPackageMeta({ total: 0, page: 1, pageSize: 15 });
    setGeneralSettlementDetails([]);
    load();
  }, [initialView, contractPaymentSourceSearch]);
  const createIncoming = async () => {
    const v = await incomingForm.validateFields();
    try {
      await api.post("/finance/incoming-payments", {
        ...v,
        received_date: formatRequiredDate(v.received_date, "到账日期"),
      });
      message.success("银行到账已登记，等待客户认领");
      setIncomingOpen(false);
      incomingForm.resetFields();
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "银行到账登记失败");
    }
  };
  const importBankStatement = async (file?: File) => {
    if (!file) return;
    const body = new FormData();
    body.append("file", file);
    try {
      const { data } = await api.post(
        "/finance/incoming-payments/import",
        body,
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      if (data.errors?.length) {
        message.warning(
          `成功导入 ${data.created} 条，${data.errors.length} 条未导入`,
        );
      } else {
        message.success(`成功导入 ${data.created} 条银行到账`);
      }
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "银行流水导入失败");
    } finally {
      if (bankUploadRef.current) bankUploadRef.current.value = "";
    }
  };
  const claimIncoming = async () => {
    if (!claimTarget) return;
    const v = await claimForm.validateFields();
    try {
      await api.post(`/finance/incoming-payments/${claimTarget.id}/claim`, v);
      message.success("到账已认领到客户，等待分配");
      setClaimTarget(null);
      claimForm.resetFields();
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "到账认领失败");
    }
  };
  const searchClaimCustomers = async (keyword = "") => {
    const requestId = ++claimCustomerSearchRequest.current;
    setClaimCustomersLoading(true);
    try {
      const { data } = await api.get("/finance/customer-options", {
        params: { keyword },
      });
      if (requestId === claimCustomerSearchRequest.current) {
        setClaimCustomers(data.items || []);
      }
    } catch {
      if (requestId === claimCustomerSearchRequest.current) {
        setClaimCustomers([]);
      }
    } finally {
      if (requestId === claimCustomerSearchRequest.current) {
        setClaimCustomersLoading(false);
      }
    }
  };
  const openIncomingAllocation = async (payment: IncomingPayment) => {
    setAllocateTarget(payment);
    setAllocationLoading(true);
    setSelectedAllocationKeys([]);
    setAllocationAmounts({});
    setAllocationKeyword("");
    setAllocationStage("");
    setAllocationFeeType("");
    setAllocationComment("");
    setAllocationValidationError("");
    try {
      const response = await api.get(
        `/finance/incoming-payments/${payment.id}/allocation-candidates`,
      );
      const rows = Array.isArray(response.data?.items) ? response.data.items : [];
      setAllocationCandidates(rows);
      setAllocationAmounts(
        Object.fromEntries(
          rows.map((row: AllocationCandidate) => [row.key, row.remaining_amount]),
        ),
      );
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "可分配案件费用加载失败");
      setAllocationCandidates([]);
    } finally {
      setAllocationLoading(false);
    }
  };
  const filteredAllocationCandidates = allocationCandidates.filter((row) => {
    const needle = allocationKeyword.trim().toLocaleLowerCase();
    const keywordMatched = !needle || [
      row.case_no,
      row.case_title,
      row.plaintiff,
      row.defendant,
      row.contract_no,
    ].some((value) => String(value || "").toLocaleLowerCase().includes(needle));
    return keywordMatched
      && (!allocationStage || row.case_stage === allocationStage)
      && (!allocationFeeType || row.fee_type === allocationFeeType);
  });
  const allocateIncoming = async () => {
    if (!allocateTarget) return;
    const selected = allocationCandidates.filter((row) => selectedAllocationKeys.includes(row.key));
    if (!selected.length) {
      const detail = "请至少选择一笔待回款案件费用";
      setAllocationValidationError(detail);
      message.warning(detail);
      return;
    }
    const allocations = selected.map((row) => ({
      receivable_plan_id: row.receivable_plan_id,
      fee_record_id: row.fee_record_id || undefined,
      amount: Number(allocationAmounts[row.key] || 0),
      case_no: row.case_no || "",
      settlement_items: [{
        fee_record_id: row.fee_record_id || undefined,
        fee_type: row.fee_type || "代理费",
        amount: Number(allocationAmounts[row.key] || 0),
        settlement_amount: Number(allocationAmounts[row.key] || 0),
        archive_fee: 0,
      }],
    }));
    if (allocations.some((entry) => entry.amount <= 0)) {
      const detail = "所选费用的本次回款金额必须大于 0";
      setAllocationValidationError(detail);
      message.warning(detail);
      return;
    }
    const total = allocations.reduce((sum, entry) => sum + entry.amount, 0);
    if (allocateTarget.remaining_amount != null && total > allocateTarget.remaining_amount + 0.001) {
      const detail = `本次分配合计不能超过未分配余额 ${money(allocateTarget.remaining_amount)}`;
      setAllocationValidationError(detail);
      message.warning(detail);
      return;
    }
    try {
      setAllocationValidationError("");
      await api.post(
        `/finance/incoming-payments/${allocateTarget.id}/allocate`,
        {
          allocations,
          comment: allocationComment,
        },
      );
      message.success("回款已分配并同步更新合同应收");
      setAllocateTarget(null);
      setAllocationCandidates([]);
      setSelectedAllocationKeys([]);
      setAllocationValidationError("");
      load();
    } catch (error: any) {
      const detail = error?.response?.data?.detail || "回款分配失败";
      setAllocationValidationError(detail);
      message.error(detail);
    }
  };
  const deleteIncoming = async (row: IncomingPayment) => {
    try {
      await api.delete(`/finance/incoming-payments/${row.id}`);
      message.success("到账记录及其分配已撤销");
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "删除失败");
    }
  };
  const closeFeeModal = () => {
    setFeeOpen(false);
    setFeeEditTarget(null);
    setFeeTypeOverride("");
    feeForm.resetFields();
  };
  const openFeeEdit = (row: Fee) => {
    const data = row.data || {};
    feeForm.setFieldsValue({
      title: row.title,
      customer: row.customer,
      amount: data.amount,
      fee_type: data.fee_type,
      expense_scope: data.expense_scope,
      expense_subtype: data.expense_subtype,
      handler: data.handler || row.owner,
      court: data.court,
      document_no: data.document_no,
      payee: data.payee,
      description: row.description || "",
      case_no: data.case_no || "",
      case_record_id: data.case_record_id || data.case_id || undefined,
      contract_record_id: data.contract_record_id || data.contract_id || undefined,
      commission_details: Array.isArray(data.commission_details)
        ? data.commission_details.map((detail: Record<string, any>) => ({
            employee_username: detail.employee_username || detail.username || "",
            commission_type: detail.commission_type || "员工提成",
            amount: detail.amount ?? detail.actual_commission,
            remark: detail.remark || "",
          }))
        : [],
    });
    setFeeTypeOverride(data.fee_type || "");
    setFeeEditTarget(row);
    setFeeOpen(true);
  };
  const createFee = async () => {
    const v = await feeForm.validateFields();
    try {
      feeEditTarget
        ? await api.put(`/finance/fees/${feeEditTarget.id}`, v)
        : await api.post("/finance/fees", v);
      message.success(feeEditTarget ? "费用已更新" : "费用已创建");
      closeFeeModal();
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "创建失败");
    }
  };
  const feeAction = async (row: Fee, type: "submit" | "approve") => {
    try {
      if (type === "submit" && row.data.fee_type === "官方费用") {
        const { data } = await api.get(`/finance/fees/${row.id}/readiness`);
        if (!data.ready) {
          Modal.warning({
            title: "案件付款三要素不完整",
            content: (
              <div>
                {data.missing.map((item: string) => (
                  <div key={item}>• {item}</div>
                ))}
              </div>
            ),
          });
          return;
        }
      }
      await api.post(`/finance/fees/${row.id}/${type}`, {
        comment: type === "submit" ? "提交财务审批" : "审批通过",
      });
      message.success(type === "submit" ? "已提交审批" : "费用已审批");
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "操作失败");
    }
  };
  const openPaymentCancel = (row: Fee) => {
    setPaymentCancelReason("");
    setPaymentCancelTarget(row);
  };
  const refreshCurrentFinanceFeeList = async ({
    page,
    pageSize,
    status,
    query,
  }: {
    page: number;
    pageSize: number;
    status: string;
    query: Record<string, any>;
  }) => {
    const token = financeFeeRefreshGuard.begin();
    try {
      const response = await api.get("/records", {
        params: {
          module: "finance",
          page: Math.max(1, page),
          page_size: Math.min(100, Math.max(1, pageSize)),
          keyword: String(query?.keyword || query?.paymentNo || "").trim(),
          record_status:
            status && status !== "全部" ? status : undefined,
        },
      });
      if (!financeFeeRefreshGuard.isLatest(token)) return false;
      setFees(Array.isArray(response.data?.items) ? response.data.items : []);
      setFinanceFeeListMeta({
        page: Number(response.data?.page || page),
        pageSize: Number(response.data?.page_size || pageSize),
        total: Number(response.data?.total || 0),
      });
      return true;
    } catch (error: any) {
      if (financeFeeRefreshGuard.isLatest(token)) {
        message.error(error?.response?.data?.detail || "财务费用刷新失败");
      }
      return false;
    }
  };
  const submitPaymentCancel = async () => {
    if (!paymentCancelTarget) return;
    const reason = paymentCancelReason.trim();
    if (!reason) {
      message.warning("请输入撤回原因.");
      return;
    }
    try {
      await api.post(`/finance/fees/${paymentCancelTarget.id}/cancel`, {
        reason,
      });
      message.success("撤销成功！");
      setPaymentCancelTarget(null);
      setPaymentCancelReason("");
      await refreshCurrentFinanceFeeList({
        page: financeFeeListMeta.page,
        pageSize: financeFeeListMeta.pageSize,
        status: paymentCancelTarget.status,
        query: originalQuery,
      });
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "撤销失败！");
    }
  };
  const openPaymentRollback = (row: Fee) => {
    setPaymentRollbackComment("");
    setPaymentRollbackTarget(row);
  };
  const submitPaymentRollback = async () => {
    if (!paymentRollbackTarget) return;
    try {
      await api.post(`/finance/fees/${paymentRollbackTarget.id}/rollback`, {
        comment: paymentRollbackComment.trim(),
      });
      message.success("回滚成功！");
      setPaymentRollbackTarget(null);
      setPaymentRollbackComment("");
      await refreshCurrentFinanceFeeList({
        page: financeFeeListMeta.page,
        pageSize: financeFeeListMeta.pageSize,
        status: paymentRollbackTarget.status,
        query: originalQuery,
      });
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "回滚失败！");
    }
  };
  const voidRejectedInternalFee = (row: Fee) => {
    Modal.confirm({
      title: "请款单作废",
      content: `确认作废请款单 ${row.serial_no}？`,
      okText: "作废",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onOk: async () => {
        try {
          await api.post(`/finance/fees/${row.id}/void`, {
            comment: "已拒绝请款单作废",
          });
          message.success("请款单已作废");
          await load();
        } catch (error: any) {
          message.error(error?.response?.data?.detail || "请款单作废失败");
          throw error;
        }
      },
    });
  };
  const writeoffFee = async () => {
    if (!writeoffTarget) return;
    const values = await writeoffForm.validateFields();
    const target = writeoffTarget;
    try {
      const contractPayment = contractPayments.find((item) => item.id === target.id);
      if (contractPayment) {
        await api.post(`/contract-payment-applications/${contractPayment.id}/writeoff`, {
          writeoff_date: formatRequiredDate(values.writeoff_date || dayjs(), "核销日期"),
          voucher_no: values.voucher_no,
          comment: values.comment || "",
        });
        message.success("合同付款已核销");
        setWriteoffTarget(null);
        writeoffForm.resetFields();
        await refreshCurrentFinanceFeeList({
          page: financeFeeListMeta.page,
          pageSize: financeFeeListMeta.pageSize,
          status: paymentStatus(target),
          query: originalQuery,
        });
        if (feeDetail?.id === target.id) {
          await openPaymentDetail(target);
        }
        return;
      }
      await api.post(`/finance/fees/${writeoffTarget.id}/writeoff`, values);
      message.success("付款已核销并留痕");
      setWriteoffTarget(null);
      writeoffForm.resetFields();
      await refreshCurrentFinanceFeeList({
        page: financeFeeListMeta.page,
        pageSize: financeFeeListMeta.pageSize,
        status: paymentStatus(target),
        query: originalQuery,
      });
      if (feeDetail?.id === target.id) {
        await openPaymentDetail(target);
      }
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "付款核销失败");
    }
  };
  const writeoffPaymentPackage = async () => {
    if (!paymentPackageWriteoffTarget) return;
    const values = await paymentPackageWriteoffForm.validateFields();
    if (!financeActionGates.paymentPackage.tryEnter()) {
      message.info("操作正在提交，请勿重复点击");
      return;
    }
    setPaymentPackageLoading(true);
    try {
      await api.post(
        `/finance/payment-packages/${paymentPackageWriteoffTarget.id}/writeoff`,
        paymentPackageWriteoffPayload(values, (value) =>
          formatRequiredDate(value, "付款日期"),
        ),
      );
      message.success("核销成功.");
      setPaymentPackageWriteoffTarget(null);
      paymentPackageWriteoffForm.resetFields();
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "付款包核销失败");
    } finally {
      financeActionGates.paymentPackage.leave();
      setPaymentPackageLoading(false);
    }
  };
  const downloadPaymentPrintWord = async (packageNoOverride?: string) => {
    if (!paymentPrintPreview && !packageNoOverride) return;
    const packageNo = String(packageNoOverride || paymentPrintPreview?.packageNo || "").trim();
    if (!packageNo) {
      message.warning("付款包号不能为空，不能导出 Word");
      return;
    }
    setPaymentWordExportLoading(true);
    try {
      const response = await api.get(
        paymentPackageWordExportPath(packageNo),
        { params: { scope: "internal_fee" }, responseType: "blob" },
      );
      const disposition =
        response.headers?.["content-disposition"] ||
        response.headers?.["Content-Disposition"] ||
        "";
      const filenameMatch =
        /filename\*=UTF-8''([^;]+)/i.exec(disposition) ||
        /filename="?([^";]+)"?/i.exec(disposition);
      let filename = packageNo + "-付款申请单.docx";
      if (filenameMatch?.[1]) {
        try {
          filename = decodeURIComponent(filenameMatch[1]);
        } catch {
          filename = filenameMatch[1];
        }
      }
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      URL.revokeObjectURL(url);
      message.success("付款单 Word 已下载");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "付款单 Word 下载失败");
    } finally {
      setPaymentWordExportLoading(false);
    }
  };
  const printPayment = async (row: Fee) => {
    let printRow = row;
    const packageNo = String(
      row.data.payment_package_no || row.data.package_no || "",
    ).trim();
    if (packageNo) {
      try {
        const { data } = await api.get("/records", {
          params: { module: "finance_package", keyword: packageNo },
        });
        const paymentPackage = (data?.items || []).find(
          (item: Fee) =>
            item.module === "finance_package" &&
            (String(item.serial_no || "").trim() === packageNo ||
              String(item.data?.package_no || "").trim() === packageNo ||
              String(item.data?.payment_package_no || "").trim() === packageNo),
        );
        if (!paymentPackage) {
          message.warning("未找到付款包或当前账号无权查看");
          return;
        }
        printRow = {
          ...row,
          data: {
            ...row.data,
            package_no: row.data.package_no || packageNo,
            payment_package_no: row.data.payment_package_no || packageNo,
            payment_package_context: paymentPackage,
          },
        };
      } catch (error: any) {
        message.error(error?.response?.data?.detail || "付款包详情加载失败");
        return;
      }
    }
    const preview = createPaymentPrintPreview(
      printRow,
      transactions,
      currentUser.displayName || "姓名待维护",
      dayjs().format("YYYY-MM-DD HH:mm"),
    );
    if (!preview) {
      message.warning("该请款单尚无付款流水，不能打印付款单");
      return;
    }
    setPaymentPrintPreview(preview);
  };
  const loadInvoiceReferenceData = async () => {
    try {
      const [contractResponse, customerResponse, feeResponse] = await Promise.all([
        api.get("/records", { params: { module: "contract", page_size: 100 } }),
        api.get("/records", { params: { module: "customer", page_size: 100 } }),
        api.get("/finance/case-fees/invoice-status", {
          params: { scope: "company", invoice_status: "未开票", page: 1, page_size: 100, fee_types: "" },
        }),
      ]);
      const contractRows = Array.isArray(contractResponse.data?.items) ? contractResponse.data.items : [];
      const customerRows = Array.isArray(customerResponse.data?.items) ? customerResponse.data.items : [];
      const candidateRows = Array.isArray(feeResponse.data?.items) ? feeResponse.data.items : [];
      setContracts(contractRows);
      setCustomers(customerRows);
      setInvoiceCandidateFees(candidateRows);
      return { contractRows, customerRows, candidateRows };
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "合同关联数据加载失败");
      throw error;
    }
  };
  const applyInvoiceFeeSelection = (nextIds: number[], candidateRows = invoiceFeeOptions) => {
    const selectedFees = candidateRows.filter((fee) => nextIds.includes(fee.id));
    if (!selectedFees.length) {
      setInvoiceSelectedFeeIds([]);
      setInvoiceFeeAmounts({});
      invoiceForm.setFieldsValue({
        case_no: undefined,
        case_record_id: undefined,
        contract_record_id: undefined,
        contract_no: undefined,
        external_contract_no: undefined,
        customer: undefined,
        customer_no: undefined,
        amount: undefined,
      });
      return;
    }
    const first = buildInvoiceSourceFields([selectedFees[0]], contracts, customers);
    const mismatched = selectedFees.some((fee) => {
      const source = buildInvoiceSourceFields([fee], contracts, customers);
      return source.case_no !== first.case_no ||
        Number(source.contract_record_id || 0) !== Number(first.contract_record_id || 0) ||
        source.customer !== first.customer;
    });
    if (mismatched) {
      message.warning("一次申请开票只能选择同一案件、合同和客户下的费用。");
      return;
    }
    setInvoiceSelectedFeeIds(nextIds);
    setInvoiceFeeAmounts(
      Object.fromEntries(
        selectedFees.map((fee) => [fee.id, invoiceFeeAvailableAmount(fee)]),
      ),
    );
    invoiceForm.setFieldsValue({
      ...buildInvoiceSourceFields(selectedFees, contracts, customers),
      case_fee_ids: nextIds,
    });
  };
  const createInvoice = async () => {
    const v = await invoiceForm.validateFields();
    const linked = buildInvoiceApplicationPayload({
      values: v,
      cases,
      contracts,
      caseFees: invoiceCandidateFees.length ? invoiceCandidateFees : fees,
      requireSource: !invoiceEditTarget,
    });
    if (linked.ok === false) {
      message.error(linked.error);
      return;
    }
    if (!invoiceEditTarget) {
      const selectedFeeIds = new Set((linked.payload.case_fee_ids || []).map(Number));
      const duplicateInvoice = invoices.find((invoice) =>
        !["已撤回", "已作废"].includes(invoice.status) &&
        (invoice.data?.case_fee_ids || []).some((feeId: number) => selectedFeeIds.has(Number(feeId))),
      );
      if (duplicateInvoice) {
        message.error("所选案件费用已经申请开票，不能重复申请");
        return;
      }
    }
    try {
      if (invoiceEditTarget) {
        const response = await api.patch(
          `/finance/invoices/${invoiceEditTarget.id}`,
          linked.payload,
        );
        const legacyFailure = legacyInvoiceUpdateFailureMessage(response);
        if (legacyFailure) throw { legacyInvoiceUpdateFailure: legacyFailure };
        message.success("发票申请草稿已更新");
      } else {
        await api.post("/finance/invoices", linked.payload);
        message.success("发票申请草稿已创建");
      }
      setInvoiceOpen(false);
      setInvoiceEditTarget(null);
      invoiceForm.resetFields();
      await loadInvoiceReferenceData();
      await load();
    } catch (error: any) {
      message.error(
        error?.response?.data?.detail ||
          error?.legacyInvoiceUpdateFailure ||
          (invoiceEditTarget
            ? "发票申请更新失败，请确认后端已提供 PATCH /finance/invoices/{id}"
            : "发票申请创建失败"),
      );
    }
  };
  const openInvoiceEdit = (row: FinanceFlow) => {
    setInvoiceEditTarget(row);
    setInvoiceSourceFeeId(null);
    const selectedFeeIds = Array.isArray(row.data?.case_fee_ids)
        ? row.data.case_fee_ids.map(Number)
        : row.data?.case_fee_id
          ? [Number(row.data.case_fee_id)]
          : [];
    setInvoiceSelectedFeeIds(selectedFeeIds);
    setInvoiceFeeAmounts(
      Object.fromEntries(
        invoiceFeeOptions
          .filter((fee) => selectedFeeIds.includes(fee.id))
          .map((fee) => [fee.id, invoiceFeeAvailableAmount(fee)]),
      ),
    );
    invoiceForm.setFieldsValue({
      ...row.data,
      customer: row.customer || row.data?.customer,
      amount: Number(row.data?.amount || 0),
      extra_amount: Number(row.data?.extra_amount || 0),
      case_fee_ids: Array.isArray(row.data?.case_fee_ids)
        ? row.data.case_fee_ids
        : row.data?.case_fee_id
          ? [Number(row.data.case_fee_id)]
          : [],
    });
    setInvoiceOpen(true);
  };
  const createRefund = async () => {
    const v = await refundForm.validateFields();
    try {
      await api.post("/finance/refunds", {
        ...v,
        expected_date: v.expected_date?.format("YYYY-MM-DD") || null,
      });
      message.success("诉讼费退款草稿已创建");
      setRefundOpen(false);
      refundForm.resetFields();
      await refreshRefundList(1);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "退款申请创建失败");
    }
  };
  const updateRefundAmount = async () => {
    if (!refundAmountTarget) return;
    const mutationStatus = refundStatusForRoute(initialView, refundStatusFilter);
    const values = await refundAmountForm.validateFields();
    const request = refundAmountUpdateRequest(
      refundAmountTarget.id,
      Number(values.amount),
      String(values.comment || ""),
    );
    setRefundMutationLoading(true);
    try {
      await api.patch(request.url, request.body);
      message.success("退款金额已修改");
      setRefundAmountTarget(null);
      refundAmountForm.resetFields();
      await loadRefunds(
        refundMeta.page,
        refundMeta.pageSize,
        mutationStatus,
        true,
        refundGroupFilter,
      );
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "退款金额修改失败");
    } finally {
      setRefundMutationLoading(false);
    }
  };
  const updateRefundBatchStatus = async () => {
    const mutationStatus = refundStatusForRoute(initialView, refundStatusFilter);
    const request = refundBatchStatusRequest(
      selectedRefundRows,
      refundBatchStatus,
      "批量修改退费进度",
    );
    setRefundMutationLoading(true);
    try {
      await api.post(request.url, request.body);
      message.success("退费进度已批量修改");
      setRefundBatchStatusOpen(false);
      await loadRefunds(
        refundMeta.page,
        refundMeta.pageSize,
        mutationStatus,
        true,
        refundGroupFilter,
      );
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "退费进度修改失败");
    } finally {
      setRefundMutationLoading(false);
    }
  };
  const submitFlow = async (kind: "invoices" | "refunds", row: FinanceFlow) => {
    try {
      await api.post(`/finance/${kind}/${row.id}/submit`, {
        comment: "提交财务审批",
      });
      message.success("已提交审批");
      if (kind === "refunds") {
        await refreshRefundList();
      } else {
        await load();
      }
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "提交失败");
    }
  };
  const reviewFlow = (
    kind: "invoices" | "refunds",
    row: FinanceFlow,
    approved: boolean,
  ) =>
    Modal.confirm({
      title: `${approved ? "通过" : "驳回"}${kind === "invoices" ? "发票" : "退款"}申请`,
      content: approved
        ? "确认资料及金额无误并通过审批？"
        : "确认驳回并退回申请人修改？",
      okText: approved ? "通过" : "驳回",
      okButtonProps: { danger: !approved },
      onOk: async () => {
        try {
          await api.post(`/finance/${kind}/${row.id}/review`, {
            approved,
            comment: approved ? "财务审核通过" : "资料不完整，退回修改",
          });
          message.success(approved ? "审批已通过" : "申请已驳回");
          if (kind === "refunds") {
            await refreshRefundList();
          } else {
            await load();
          }
        } catch (error: any) {
          message.error(error?.response?.data?.detail || "审核失败");
          throw error;
        }
      },
    });
  const issueInvoice = async () => {
    const target = issueTarget || invoiceProcess;
    if (!target) return;
    if (invoiceProcess && !String(issueForm.getFieldValue("invoice_no") || "").trim()) {
      Modal.info({ title: "提示", content: "请输入发票号码.", okText: "确定" });
      return;
    }
    const v = await issueForm.validateFields();
    try {
      await api.post(`/finance/invoices/${target.id}/issue`, {
        ...v,
        invoice_date: formatRequiredDate(v.invoice_date, "开票日期"),
      });
      message.success("开票信息已登记");
      setIssueTarget(null);
      setInvoiceProcess(null);
      issueForm.resetFields();
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "开票登记失败");
    }
  };
  const rejectInvoiceIssue = async () => {
    if (!invoiceProcess) return;
    const reason = String(issueForm.getFieldValue("comment") || "").trim();
    if (!reason) {
      Modal.info({ title: "提示", content: "请输入驳回原因.", okText: "确定" });
      return;
    }
    try {
      await api.post(`/finance/invoices/${invoiceProcess.id}/reject-issue`, {
        comment: reason,
      });
      message.success("发票申请已驳回");
      setInvoiceProcess(null);
      issueForm.resetFields();
      await loadInvoicePending(originalQuery, 1, invoicePendingMeta.pageSize);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "开票驳回失败");
    }
  };
  const voidInvoice = async () => {
    if (!voidTarget) return;
    const v = await voidForm.validateFields();
    try {
      await api.post(`/finance/invoices/${voidTarget.id}/void`, v);
      message.success("发票已作废并生成冲销流水");
      setVoidTarget(null);
      voidForm.resetFields();
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "发票作废失败");
    }
  };
  const completeRefund = async () => {
    if (!refundCompleteTarget) return;
    const v = await refundCompleteForm.validateFields();
    try {
      await api.post(`/finance/refunds/${refundCompleteTarget.id}/complete`, {
        ...v,
        actual_date: formatRequiredDate(v.actual_date, "实际退款日期"),
      });
      message.success("退款到账已登记");
      setRefundCompleteTarget(null);
      refundCompleteForm.resetFields();
      await refreshRefundList();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "退款到账登记失败");
    }
  };
  const openRecordFiles = async (row: FinanceFlow, category: string, targets: FinanceFlow[] = [row]) => {
    try {
      const recordModule = attachmentRecordModule(row, category);
      const { data } = await api.get("/attachments", {
        params: { record_id: row.id, category, module: row.module || recordModule },
      });
      setRecordFiles(data.items);
      setRecordFileTarget(row);
      setRecordFileTargets(targets);
      setRecordFile(null);
      setRecordUploadFiles([]);
      recordFileForm.setFieldsValue({ category, remark: "", document_date: dayjs() });
      if (targets.length > 1 && !recordFileTypeTree.length) {
        api.get("/system/parameters/options", { params: { category: "case_file_type" } })
          .then(({ data }) => setRecordFileTypeTree(data.items || []))
          .catch(() => setRecordFileTypeTree([]));
      }
    } catch (error: any) {
      setRecordFiles([]);
      setRecordFileTarget(null);
      setRecordFileTargets([]);
      setRecordFile(null);
      setRecordUploadFiles([]);
      message.error(error?.response?.data?.detail || "业务凭证加载失败");
    }
  };
  const uploadRecordFile = async () => {
    if (!recordFileTarget || (!recordFile && !recordUploadFiles.length)) return message.warning("请选择文件");
    const v = await recordFileForm.validateFields();
    try {
      const filesToUpload = recordUploadFiles.length ? recordUploadFiles : [recordFile!];
      for (const target of recordFileTargets.length ? recordFileTargets : [recordFileTarget]) {
        for (const sourceFile of filesToUpload) {
        const form = new FormData();
        form.append("file", sourceFile);
        form.append("record_id", String(target.id));
        form.append("category", v.category);
        form.append("module", attachmentRecordModule(target, v.category));
        form.append("remark", v.remark || "");
        if (v.document_date) form.append("document_date", formatRequiredDate(v.document_date, "参考日期"));
        await api.post("/attachments", form);
        }
      }
      message.success(`${filesToUpload.length} 个文件已上传到 ${recordFileTargets.length || 1} 个案件`);
      await openRecordFiles(recordFileTarget, v.category, recordFileTargets);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "上传失败");
    }
  };
  const deleteRecordFile = async (row: Attachment) => {
    try {
      await api.delete(`/attachments/${row.id}`);
      setRecordFiles((files) => files.filter((x) => x.id !== row.id));
      message.success("凭证已删除");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "删除失败");
    }
  };
  const openVouchers = (row: Transaction) => {
    setVoucherTarget(row);
    setVoucherFile(null);
    voucherForm.setFieldsValue({
      category: voucherCategory[row.transaction_type],
      remark: "",
    });
    setVoucherOpen(true);
  };
  const createTransaction = async () => {
    const v = await transactionForm.validateFields();
    try {
      const contractPayment = contractPayments.find(
        (item) => item.id === Number(v.finance_record_id),
      );
      if (contractPayment) {
        await api.post(`/contract-payment-applications/${contractPayment.id}/pay`, {
          paid_date: formatRequiredDate(v.transaction_date, "交易日期"),
          voucher_no: v.voucher_no || "",
          comment: v.remark || "",
        });
        message.success("合同付款已登记");
        setTransactionOpen(false);
        transactionForm.resetFields();
        await load();
        return;
      }
      const { data } = await api.post("/finance/transactions", {
        ...v,
        transaction_date: formatRequiredDate(v.transaction_date, "交易日期"),
      });
      message.success("财务流水已登记，请上传对应凭证");
      setTransactionOpen(false);
      transactionForm.resetFields();
      openVouchers({
        ...data,
        voucher_count: 0,
        voucher_categories: [],
        vouchers: [],
      });
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "登记失败");
    }
  };
  const uploadVoucher = async () => {
    if (!voucherTarget) return;
    const v = await voucherForm.validateFields();
    if (!voucherFile) {
      message.warning("请选择凭证文件");
      return;
    }
    const form = new FormData();
    form.append("file", voucherFile);
    form.append("finance_transaction_id", String(voucherTarget.id));
    form.append("category", v.category);
    form.append("remark", v.remark || "");
    try {
      const { data } = await api.post("/attachments", form);
      const vouchers = [...(voucherTarget.vouchers || []), data];
      setVoucherTarget({
        ...voucherTarget,
        vouchers,
        voucher_count: vouchers.length,
        voucher_categories: [...new Set(vouchers.map((x) => x.category))],
      });
      setVoucherFile(null);
      voucherForm.setFieldValue("remark", "");
      message.success("凭证上传成功");
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "凭证上传失败");
    }
  };
  const downloadVoucher = async (row: Attachment) => {
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
      message.error("凭证下载失败");
    }
  };
  const deleteVoucher = async (row: Attachment) => {
    try {
      await api.delete(`/attachments/${row.id}`);
      if (voucherTarget) {
        const vouchers = voucherTarget.vouchers.filter((x) => x.id !== row.id);
        setVoucherTarget({
          ...voucherTarget,
          vouchers,
          voucher_count: vouchers.length,
          voucher_categories: [...new Set(vouchers.map((x) => x.category))],
        });
      }
      message.success("凭证已删除");
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "删除失败");
    }
  };
  const rollbackFinanceTransaction = (row: Transaction) => {
    Modal.confirm({
      title: "回退财务流水",
      content:
        row.transaction_type === "付款"
          ? "回退后会删除本笔付款流水及其凭证，并按剩余付款金额恢复关联请款单状态。确定继续吗？"
          : "回退后会删除本笔财务流水及其凭证。确定继续吗？",
      okText: "确认回退",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onOk: async () => {
        try {
          await api.delete(`/finance/transactions/${row.id}`);
          if (voucherTarget?.id === row.id) {
            setVoucherOpen(false);
            setVoucherTarget(null);
          }
          message.success("财务流水已回退");
          load();
        } catch (error: any) {
          message.error(error?.response?.data?.detail || "财务流水回退失败");
        }
      },
    });
  };
  const createReconciliation = async () => {
    const v = await reconcileForm.validateFields();
    const { period, ...fields } = v;
    try {
      await api.post("/finance/reconciliations", {
        ...fields,
        date_from: period[0].format("YYYY-MM-DD"),
        date_to: period[1].format("YYYY-MM-DD"),
      });
      message.success("对账单已生成");
      setReconcileOpen(false);
      reconcileForm.resetFields();
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "生成失败");
    }
  };
  const confirmReconciliation = async (row: Reconciliation) => {
    try {
      await api.post(`/finance/reconciliations/${row.id}/confirm`, {
        comment: "财务核对无误",
      });
      message.success("对账单已确认");
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "确认失败");
    }
  };
  const canApprove = ["admin", "manager", "auditor"].includes(role);
  const canManage = ["admin", "manager"].includes(role);
  const canWithdrawFinanceFee = (row: Fee) =>
    row.module === "finance" &&
    ["草稿", "待审批", "已审批", "待付款"].includes(row.status) &&
    (canManage || row.owner === currentUser.username);
  const originalIncomingOperation = (_: unknown, r: IncomingPayment) => (
    <Space size={0}>
      <Button type="link" onClick={() => setIncomingDetailTarget(r)}>
        查看
      </Button>
      {r.status === "待认领" && (
        <Button
          type="link"
          onClick={() => {
            claimForm.resetFields();
            void searchClaimCustomers();
            setClaimTarget(r);
          }}
        >
          认领
        </Button>
      )}
      {["待分配", "部分分配"].includes(r.status) &&
        r.remaining_amount !== null &&
        r.remaining_amount > 0 && (
          <Button
            type="link"
            onClick={() => openIncomingAllocation(r)}
          >
            分配
          </Button>
        )}
      {r.allocations?.length > 0 && (
        <Button
          type="link"
          onClick={() => setIncomingAllocationTarget(r)}
        >
          分配记录
        </Button>
      )}
      {role === "admin" && (
        <Button type="link" danger onClick={() => deleteIncoming(r)}>
          删除
        </Button>
      )}
    </Space>
  );
  const incomingColumns = [
    { title: "到账编号", dataIndex: "receipt_no", width: 180 },
    { title: "到账日期", dataIndex: "received_date", width: 110 },
    { title: "付款单位/户名", dataIndex: "payer_name", width: 210 },
    { title: "银行流水号", dataIndex: "bank_reference", width: 165 },
    {
      title: "到账金额",
      dataIndex: "amount",
      width: 130,
      render: (v: number | null) => (v == null ? "无权限" : money(v)),
    },
    {
      title: "已分配",
      dataIndex: "allocated_amount",
      width: 120,
      render: (v: number | null) => (v == null ? "无权限" : money(v)),
    },
    {
      title: "认领客户",
      dataIndex: "claimed_customer",
      width: 190,
      render: (v: string) => v || "—",
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 100,
      render: (v: string) => (
        <Tag
          color={v === "已分配" ? "green" : v === "待认领" ? "orange" : "blue"}
        >
          {v}
        </Tag>
      ),
    },
    {
      title: "认领人",
      dataIndex: "claimant",
      width: 90,
      render: (v: string, row: IncomingPayment) => financePersonDisplayName(v, (row as any).claimant_display_name),
    },
    { title: "备注", dataIndex: "remark", ellipsis: true },
    {
      title: "操作",
      key: "action",
      fixed: "right" as const,
      width: 205,
      render: originalIncomingOperation,
    },
  ];
  const feeColumns = [
    { title: "费用编号", dataIndex: "serial_no", width: 175 },
    { title: "费用名称", dataIndex: "title", width: 240 },
    {
      title: "费用类型",
      key: "type",
      width: 100,
      render: (_: unknown, r: Fee) => (
        <Tag color="blue">{r.data.fee_type || "官方费用"}</Tag>
      ),
    },
    {
      title: "金额",
      key: "amount",
      width: 120,
      render: (_: unknown, r: Fee) => (
        <b>{r.data.amount == null ? "无权限" : money(r.data.amount)}</b>
      ),
    },
    { title: "客户", dataIndex: "customer", width: 180, render: (value: string, r: Fee) => value ? <Button type="link" onClick={() => openCustomerDetail(value, r.data.customer_no)}>{value}</Button> : "—" },
    {
      title: "案号",
      key: "case",
      width: 145,
      render: (_: unknown, r: Fee) => r.data.case_no ? <Button type="link" onClick={() => openCaseDetail(r.data.case_no)}>{r.data.case_no}</Button> : "—",
    },
    {
      title: "法院/机构",
      key: "court",
      width: 180,
      render: (_: unknown, r: Fee) => r.data.court || "—",
    },
    { title: "经办人", dataIndex: "owner", width: 90 },
    {
      title: "状态",
      dataIndex: "status",
      width: 90,
      render: (v: string) => (
        <Tag color={statusColors[v] || "default"}>{v}</Tag>
      ),
    },
    {
      title: "操作",
      key: "action",
      fixed: "right" as const,
      width: 145,
      render: (_: unknown, r: Fee) => (
        <Space>
          {["草稿", "已退回"].includes(r.status) && (
            <Button
              type="link"
              icon={<AuditOutlined />}
              onClick={() => feeAction(r, "submit")}
            >
              提交
            </Button>
          )}
          {canApprove && r.status === "待审批" && (
            <Button
              type="link"
              icon={<CheckCircleOutlined />}
              onClick={() => feeAction(r, "approve")}
            >
              通过
            </Button>
          )}
          {r.data.amount != null &&
            ["已审批", "部分付款"].includes(r.status) && (
              <Button
                type="link"
                icon={<DollarOutlined />}
                onClick={() => {
                  transactionForm.setFieldsValue({
                    finance_record_id: r.id,
                    transaction_type: "付款",
                    transaction_date: dayjs(),
                    counterparty: r.data.payee || r.customer,
                  });
                  setTransactionOpen(true);
                }}
              >
                付款
              </Button>
            )}
        </Space>
      ),
    },
  ];
  const invoiceColumns = [
    { title: "申请编号", dataIndex: "serial_no", width: 180 },
    { title: "客户", dataIndex: "customer", width: 190, render: (value: string, r: FinanceFlow) => value ? <Button type="link" onClick={() => openCustomerDetail(value, r.data.customer_no)}>{value}</Button> : "—" },
    {
      title: "案号",
      key: "case_no",
      width: 150,
      render: (_: unknown, r: FinanceFlow) => r.data.case_no ? <Button type="link" onClick={() => openCaseDetail(r.data.case_no)}>{r.data.case_no}</Button> : "—",
    },
    {
      title: "发票抬头",
      key: "title",
      width: 210,
      render: (_: unknown, r: FinanceFlow) => r.data.invoice_title || "—",
    },
    {
      title: "发票类型",
      key: "type",
      width: 130,
      render: (_: unknown, r: FinanceFlow) => r.data.invoice_type,
    },
    {
      title: "金额",
      key: "amount",
      width: 125,
      render: (_: unknown, r: FinanceFlow) =>
        r.data.amount == null ? "无权限" : money(r.data.amount),
    },
    {
      title: "交付",
      key: "delivery",
      width: 100,
      render: (_: unknown, r: FinanceFlow) => r.data.delivery_method,
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 95,
      render: (v: string) => (
        <Tag color={statusColors[v] || "default"}>{v}</Tag>
      ),
    },
    {
      title: "发票号码",
      key: "invoice_no",
      width: 150,
      render: (_: unknown, r: FinanceFlow) => r.data.invoice_no || "—",
    },
    {
      title: "扫描件",
      key: "files",
      width: 95,
      render: (_: unknown, r: FinanceFlow) => (
        <Button
          type="link"
          icon={<PaperClipOutlined />}
          onClick={() => openRecordFiles(r, "发票扫描件")}
        >
          凭证
        </Button>
      ),
    },
    {
      title: "操作",
      key: "action",
      fixed: "right" as const,
      width: 205,
      render: (_: unknown, r: FinanceFlow) => (
        <Space wrap>
          <Button type="link" onClick={() => void openInvoiceDetail(r)}>
            详情
          </Button>
          {["草稿", "已驳回"].includes(r.status) && (
            <Button type="link" onClick={() => submitFlow("invoices", r)}>
              提交
            </Button>
          )}
          {canApprove && r.status === "待审批" && (
            <>
              <Button
                type="link"
                onClick={() => reviewFlow("invoices", r, true)}
              >
                通过
              </Button>
              <Button
                type="link"
                danger
                onClick={() => reviewFlow("invoices", r, false)}
              >
                驳回
              </Button>
            </>
          )}
          {canManage && r.status === "待开票" && (
            <Button
              type="link"
              onClick={() => {
                issueForm.setFieldsValue({ invoice_date: dayjs() });
                setIssueTarget(r);
              }}
            >
              登记开票
            </Button>
          )}
          {canManage && r.status === "已开票" && (
            <Button type="link" danger onClick={() => setVoidTarget(r)}>
              作废
            </Button>
          )}
        </Space>
      ),
    },
  ];
  const refundColumns = [
    { title: "申请编号", dataIndex: "serial_no", width: 180 },
    {
      title: "案号",
      key: "case_no",
      width: 150,
      render: (_: unknown, r: FinanceFlow) => r.data.case_no ? <Button type="link" onClick={() => openCaseDetail(r.data.case_no)}>{r.data.case_no}</Button> : "—",
    },
    { title: "客户", dataIndex: "customer", width: 180, render: (value: string, r: FinanceFlow) => value ? <Button type="link" onClick={() => openCustomerDetail(value, r.data.customer_no)}>{value}</Button> : "—" },
    {
      title: "法院",
      key: "court",
      width: 190,
      render: (_: unknown, r: FinanceFlow) => r.data.court,
    },
    {
      title: "原缴费票号",
      key: "payment_no",
      width: 150,
      render: (_: unknown, r: FinanceFlow) => r.data.original_payment_no,
    },
    {
      title: "退款金额",
      key: "amount",
      width: 125,
      render: (_: unknown, r: FinanceFlow) =>
        r.data.amount == null ? "无权限" : money(r.data.amount),
    },
    {
      title: "退款账户",
      key: "account",
      width: 180,
      render: (_: unknown, r: FinanceFlow) => r.data.refund_account_name || "—",
    },
    {
      title: "预计到账",
      key: "expected",
      width: 110,
      render: (_: unknown, r: FinanceFlow) => r.data.expected_date || "—",
    },
    {
      title: "实际到账",
      key: "actual",
      width: 110,
      render: (_: unknown, r: FinanceFlow) => r.data.actual_date || "—",
    },
    {
      title: "退款凭证号",
      key: "voucher",
      width: 135,
      render: (_: unknown, r: FinanceFlow) =>
        r.data.refund_voucher_no || r.data.voucher_no || "—",
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 105,
      render: (v: string) => (
        <Tag color={statusColors[v] || "default"}>{v}</Tag>
      ),
    },
    {
      title: "到账凭证",
      key: "files",
      width: 105,
      render: (_: unknown, r: FinanceFlow) => (
        <Button
          type="link"
          icon={<PaperClipOutlined />}
          onClick={() => openRecordFiles(r, "退费凭证")}
        >
          凭证
        </Button>
      ),
    },
    {
      title: "操作",
      key: "action",
      fixed: "right" as const,
      width: 205,
      render: (_: unknown, r: FinanceFlow) => (
        <Space wrap>
          <Button type="link" onClick={() => void openRefundDetail(r)}>
            详情
          </Button>
          {['草稿', '已驳回'].includes(r.status) && (
            <Button
              type="link"
              onClick={() => {
                refundAmountForm.setFieldsValue({
                  amount: r.data.amount,
                  comment: "",
                });
                setRefundAmountTarget(r);
              }}
            >
              修改金额
            </Button>
          )}
          {["草稿", "已驳回"].includes(r.status) && (
            <Button type="link" onClick={() => submitFlow("refunds", r)}>
              提交
            </Button>
          )}
          {canApprove && r.status === "待审批" && (
            <>
              <Button
                type="link"
                onClick={() => reviewFlow("refunds", r, true)}
              >
                通过
              </Button>
              <Button
                type="link"
                danger
                onClick={() => reviewFlow("refunds", r, false)}
              >
                驳回
              </Button>
            </>
          )}
          {canManage && r.status === "退款办理中" && (
            <Button
              type="link"
              onClick={() => {
                refundCompleteForm.setFieldsValue({ actual_date: dayjs() });
                setRefundCompleteTarget(r);
              }}
            >
              登记到账
            </Button>
          )}
        </Space>
      ),
    },
  ];
  const transactionColumns = [
    { title: "日期", dataIndex: "transaction_date", width: 105 },
    {
      title: "类型",
      dataIndex: "transaction_type",
      width: 80,
      render: (v: string) => (
        <Tag color={v === "付款" ? "green" : v === "退费" ? "red" : "blue"}>
          {v}
        </Tag>
      ),
    },
    {
      title: "金额",
      dataIndex: "amount",
      width: 130,
      render: (v: number | null) => (v == null ? "无权限" : money(v)),
    },
    {
      title: "关联费用",
      dataIndex: "finance_no",
      width: 175,
      render: (v: string) => v || "独立流水",
    },
    { title: "费用名称", dataIndex: "finance_title", width: 230 },
    { title: "凭证/票号", dataIndex: "voucher_no", width: 150 },
    {
      title: "凭证附件",
      key: "vouchers",
      width: 150,
      render: (_: unknown, r: Transaction) => (
        <Button
          type="link"
          icon={<PaperClipOutlined />}
          onClick={() => openVouchers(r)}
        >
          {r.voucher_count ? `${r.voucher_count} 个附件` : "上传凭证"}
        </Button>
      ),
    },
    { title: "对方单位", dataIndex: "counterparty", width: 190 },
    { title: "登记人", dataIndex: "operator", width: 90, render: (value:string,row:Transaction) => financePersonDisplayName(value,(row as any).operator_display_name) },
    { title: "备注", dataIndex: "remark" },
    ...(role === "admin"
      ? [
          {
            title: "操作",
            key: "action",
            fixed: "right" as const,
            width: 96,
            render: (_: unknown, r: Transaction) => (
              <Button
                danger
                type="link"
                onClick={() => rollbackFinanceTransaction(r)}
              >
                回退
              </Button>
            ),
          },
        ]
      : []),
  ];
  const reconcileColumns = [
    {
      title: "周期",
      dataIndex: "period_type",
      width: 90,
      render: (v: string) => <Tag color="blue">{v}</Tag>,
    },
    { title: "开始日期", dataIndex: "date_from", width: 110 },
    { title: "结束日期", dataIndex: "date_to", width: 110 },
    { title: "流水笔数", dataIndex: "transaction_count", width: 90 },
    { title: "流水金额", dataIndex: "total_amount", width: 140, render: money },
    {
      title: "差异金额",
      dataIndex: "discrepancy_amount",
      width: 130,
      render: (v: number) => (
        <span className={v ? "money-due" : ""}>{money(v)}</span>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 90,
      render: (v: string) => (
        <Tag color={v === "已确认" ? "green" : "orange"}>{v}</Tag>
      ),
    },
    { title: "操作人", dataIndex: "operator", width: 90, render: (value:string,row:Reconciliation) => financePersonDisplayName(value,(row as any).operator_display_name) },
    { title: "备注", dataIndex: "remark" },
    {
      title: "操作",
      key: "action",
      width: 90,
      render: (_: unknown, r: Reconciliation) =>
        r.status === "待确认" ? (
          <Button type="link" onClick={() => confirmReconciliation(r)}>
            确认对账
          </Button>
        ) : (
          "—"
        ),
    },
  ];
  const legacyFinanceKindLabel: Record<LegacyFinanceRecord["record_kind"], string> = {
    ap_payment: "历史请款",
    ar_payment: "历史回款",
    invoice: "历史开票",
    ap_packing: "历史付款打包",
    case_fee: "历史案件应收费用",
  };
  const legacyFinanceAmount = (value: number | null | undefined) =>
    legacyFinanceSummary.amount_visible ? money(Number(value || 0)) : "无权限";
  const legacyFinanceMappingLabel = (value?: string) => {
    const normalized = String(value || "").trim();
    if (!normalized || ["matched", "exact"].includes(normalized)) return "已精确关联";
    if (/parent_not_present|orphan|missing_parent/i.test(normalized)) return "孤儿 / 父级缺失";
    if (normalized === "missing") return "缺少业务关联";
    if (/unmapped|not_mapped|unlinked/i.test(normalized)) return "未关联实时业务";
    return normalized;
  };
  const legacyFinanceStatusLabel = (value?: string) => {
    const normalized = String(value || "").trim();
    const legacyCode = normalized.match(/^legacy_status_(.+)$/i);
    return legacyCode ? `旧状态码 ${legacyCode[1]}` : (normalized || "未标注");
  };
  const legacyFinanceMappingColor = (value?: string) => {
    const normalized = String(value || "");
    if (/parent_not_present|orphan|missing_parent/i.test(normalized)) return "orange";
    if (/unmapped|not_mapped|unlinked/i.test(normalized)) return "default";
    return "green";
  };
  const legacyFinanceSummaryByKind = (kind: LegacyFinanceRecord["record_kind"]) =>
    legacyFinanceSummary.records
      .filter((row) => row.record_kind === kind && (legacyFinanceIncludeInactive || row.is_active))
      .reduce(
        (total, row) => ({ count: total.count + Number(row.count || 0), amount: total.amount + Number(row.primary_amount || 0) }),
        { count: 0, amount: 0 },
      );
  const legacyFinanceColumns = [
    {
      title: "历史编号",
      dataIndex: "legacy_id",
      width: 148,
      render: (value: string, row: LegacyFinanceRecord) => (
        <Button type="link" onClick={() => void openLegacyFinanceDetail(row.id)}>{value || `#${row.id}`}</Button>
      ),
    },
    { title: "账本类型", dataIndex: "record_kind", width: 112, render: (value: LegacyFinanceRecord["record_kind"]) => legacyFinanceKindLabel[value] || value },
    { title: "状态", dataIndex: "status_label", width: 108, render: (value: string, row: LegacyFinanceRecord) => <Tag color={row.is_active ? "blue" : "default"}>{legacyFinanceStatusLabel(value)}</Tag> },
    { title: "合同编号", dataIndex: "legacy_contract_no", width: 150, render: (value: string) => value || "—" },
    { title: "案件编号", dataIndex: "legacy_case_no", width: 150, render: (value: string) => value || "—" },
    { title: "客户编号", dataIndex: "legacy_customer_no", width: 140, render: (value: string) => value || "—" },
    { title: "金额", dataIndex: "primary_amount", align: "right" as const, width: 126, render: legacyFinanceAmount },
    { title: "分配", dataIndex: "allocation_count", align: "right" as const, width: 70 },
    { title: "发票文件", dataIndex: "file_count", align: "right" as const, width: 88 },
    {
      title: "关联状态",
      dataIndex: "mapping_status",
      width: 142,
      render: (value: string) => <Tag color={legacyFinanceMappingColor(value)}>{legacyFinanceMappingLabel(value)}</Tag>,
    },
    { title: "来源表", dataIndex: "source_table", width: 150 },
    { title: "导入时间", dataIndex: "imported_at", width: 170, render: (value: string) => value ? dayjs(value).format("YYYY-MM-DD HH:mm") : "—" },
    { title: "审批记录", dataIndex: "audit_count", align: "right" as const, width: 82 },
  ];
  const shownFees = useMemo(() => {
    let result =
      tab === "audit" ? fees.filter((x) => x.status === "待审批") : fees;
    if (initialView.startsWith("finance-internal"))
      result = result.filter((x) => x.data.fee_type === "内部费用");
    if (initialView.startsWith("finance-settlement"))
      result = result.filter((x) => x.data.fee_type === "结算费用");
    if (initialView.startsWith("finance-archive-fee"))
      result = result.filter((x) => x.data.fee_type === "归档费用");
    if (initialView.endsWith("-audit"))
      result = result.filter((x) => x.status === "待审批");
    if (initialView.endsWith("-waiting") || initialView.endsWith("-payment"))
      result = result.filter((x) => ["已审批", "部分付款"].includes(x.status));
    if (initialView.endsWith("-paid") || initialView.endsWith("-done"))
      result = result.filter((x) => x.status === "已付款");
    if (initialView.endsWith("-refused"))
      result = result.filter((x) => ["已退回", "已驳回"].includes(x.status));
    return result;
  }, [fees, tab, initialView]);
  const shownIncoming = useMemo(
    () =>
      initialView.endsWith("-claim")
        ? incoming.filter((x) => x.status === "待认领")
        : initialView.endsWith("-pending")
          ? incoming.filter((x) => ["待分配", "部分分配"].includes(x.status))
          : initialView.endsWith("-allocated")
            ? incoming.filter((x) => x.status === "已分配")
            : incoming,
    [incoming, initialView],
  );
  const shownInvoices = useMemo(
    () =>
      initialView.endsWith("-pending")
        ? invoices.filter((x) => ["待审批", "待开票"].includes(x.status))
        : initialView.endsWith("-unissued")
          ? invoices.filter(
              (x) => x.status !== "已开票" && x.status !== "已作废",
            )
          : invoices,
    [invoices, initialView],
  );

  const originalFinanceRoutes = [
    "finance-receipts-icbc",
    "finance-receipts-citic",
    "finance-receipts-boc",
    "finance-receipts-manage",
    "finance-receipts-claim",
    "finance-receipts-pending",
    "finance-receipts-allocated",
    "finance-receipts-query",
    "finance-payment-mine",
    "finance-payment-audit",
    "finance-payment-waiting",
    "finance-payment-print",
    "finance-payment-writeoff",
    "finance-payment-query",
    "finance-internal-mine",
    "finance-internal-settle",
    "finance-internal-archive",
    "finance-internal-audit",
    "finance-internal-fee-audit",
    "finance-internal-refused",
    "finance-internal-void",
    "finance-internal-refund-audit",
    "finance-internal-payment",
    "finance-internal-writeoff",
    "finance-internal-query",
    "finance-internal-done",
    "finance-internal-detail",
    "finance-internal-company",
    "finance-invoice-mine",
    "finance-invoice-pending",
    "finance-invoice-company",
    "finance-invoice-unissued",
    "finance-invoice-company-unissued",
    "finance-settlement-pending",
    "finance-settlement-audit",
    "finance-settlement-payment",
    "finance-settlement-paid",
    "finance-settlement-refused",
    "finance-archive-fee-pending",
    "finance-archive-fee-payment",
    "finance-archive-fee-paid",
    "finance-archive-fee-refused",
    "finance-query",
    "finance-fee-query",
    "finance-refund",
  ];
  const originalMode = originalFinanceRoutes.includes(initialView);
  const originalKind =
    initialView === "finance-internal-mine"
      ? "internal"
      : ["finance-query", "finance-fee-query", "finance-refund"].includes(initialView)
        ? "fee-query"
        : "payment";
  const originalTitle: Record<string, string> = {
    "finance-receipts-icbc": "工行银行到账列表",
    "finance-receipts-citic": "中信银行到账列表",
    "finance-receipts-boc": "中国银行到账列表",
    "finance-receipts-manage": "回款查询",
    "finance-receipts-claim": "回款查询",
    "finance-receipts-pending": "回款查询",
    "finance-receipts-allocated": "回款查询",
    "finance-receipts-query": "到账查询",
    "finance-payment-mine": "我的请款单",
    "finance-payment-audit": "请款单审批",
    "finance-payment-waiting": "请款单列表",
    "finance-payment-print": "请款单列表",
    "finance-payment-writeoff": "请款单列表",
    "finance-payment-query": "请款单列表",
    "finance-refund-not-required": "不再办理退费案件",
    "finance-internal-mine": "我的请款单",
    "finance-internal-settle": "内部提成-待结算",
    "finance-internal-archive": "内部提成-待归档",
    "finance-internal-audit": "请款单审批",
    "finance-internal-fee-audit": "请款单审批",
    "finance-internal-refused": "请款单列表",
    "finance-internal-void": "请款单列表",
    "finance-internal-refund-audit": "请款单审批",
    "finance-internal-payment": "待付款列表",
    "finance-internal-writeoff": "付款单-核销",
    "finance-internal-query": "请款单列表",
    "finance-internal-done": "付款单-查询",
    "finance-internal-detail": "内部费用查询",
    "finance-internal-company": "内部费用查询",
    "finance-invoice-mine": "我的开票",
    "finance-invoice-pending": "待处理开票",
    "finance-invoice-company": "公司开票",
    "finance-invoice-unissued": "未开票",
    "finance-invoice-company-unissued": "公司未开票",
    "finance-settlement-pending": "待结算",
    "finance-settlement-audit": "待审核",
    "finance-settlement-payment": "待付款",
    "finance-settlement-paid": "已付款",
    "finance-settlement-refused": "已拒绝",
    "finance-archive-fee-pending": "待归档",
    "finance-archive-fee-payment": "待支付",
    "finance-archive-fee-paid": "已支付",
    "finance-archive-fee-refused": "已拒绝",
    "finance-query": "费用查询",
    "finance-fee-query": "费用查询",
    "finance-refund": "退费查询",
  };
  const displayedOriginalTitle =
    platformMode && initialView === "finance-payment-mine"
      ? "请款单列表"
      : originalTitle[initialView] || "财务中心";
  const paymentStatuses = paymentQueryLegacyStatusMatrix;
  const latestTransaction = (fee: Fee) =>
    transactions
      .filter((item) => item.finance_record_id === fee.id)
      .sort((a, b) =>
        String(b.transaction_date).localeCompare(String(a.transaction_date)),
      )[0];
  const linkedCaseForFee = (fee: Fee) => {
    const data = fee.data || {};
    return cases.find(
      (item) =>
        (data.case_id && Number(data.case_id) === item.id) ||
        (data.case_no && data.case_no === item.serial_no),
    );
  };
  const paymentStatus = (fee: Fee) => {
    if (fee.data.payment_status) return fee.data.payment_status;
    if (fee.data.writeoff_status === "待核销") return "待核销";
    return (
      (
        {
          草稿: "创建待提交",
          待审批: "待审批",
          已审批: "待付款",
          部分付款: "待付款",
          已付款: "已付款",
          已退回: "已驳回",
          已驳回: "已驳回",
          已作废: "已作废",
        } as Record<string, string>
      )[fee.status] || fee.status
    );
  };
  const isInternalRefundFee = (fee: Fee) =>
    fee.data?.fee_type === "内部费用" &&
    (fee.data?.is_refund === true || Number(fee.data?.amount || 0) < 0);
  const originalFinanceRows = useMemo(() => {
    let result = [
      ...fees,
      ...(originalKind === "payment" ? contractPayments : []),
    ];
    if (contractPaymentSource.active) {
      if (!contractPaymentSource.ok) return [];
      const identities = [currentUser.username, currentUser.displayName].filter(
        Boolean,
      );
      return contractPayments.filter(
        (item) =>
          matchesContractPaymentSource(item, contractPaymentSource) &&
          identities.includes(item.data.applicant || item.owner || ""),
      );
    }
    if (originalKind === "internal") {
      result = result.filter((item) => item.data.fee_type === "内部费用");
    }
    if (
      ["finance-payment-mine", "finance-internal-mine"].includes(initialView)
    ) {
      const identities = [currentUser.username, currentUser.displayName].filter(
        Boolean,
      );
      result = result.filter((item) =>
        identities.includes(item.data.applicant || item.owner || ""),
      );
    }
    if (initialView === "finance-payment-audit") {
      result = result.filter((item) => item.status === "待审批");
    }
    if (initialView === "finance-payment-waiting") {
      result = result.filter((item) =>
        item.data?._source_module === "contract_payment"
          ? item.status === "待付款"
          : ["已审批", "部分付款"].includes(item.status),
      );
    }
    if (initialView === "finance-payment-print") {
      result = result.filter((item) => item.status === "已付款");
    }
    if (initialView === "finance-payment-writeoff") {
      result = result.filter(
        (item) =>
          item.status === "已付款" && item.data.writeoff_status !== "已核销",
      );
    }
    const textMatch = (value: unknown, key: string) => {
      const query = String(originalQuery[key] || "")
        .trim()
        .toLowerCase();
      return (
        !query ||
        String(value || "")
          .toLowerCase()
          .includes(query)
      );
    };
    result = result.filter((item) => {
      const tx = latestTransaction(item);
      const applicationDate =
        item.data.application_date || item.created_at || "";
      const deadline = item.data.deadline || item.data.due_date || "";
      const applicationRange = originalQuery.applicationRange;
      const paymentRange = originalQuery.paymentRange;
      return (
        (!originalQuery.status ||
          (initialView === "finance-payment-writeoff" &&
            item.data?._source_module === "contract_payment" &&
            item.status === "已付款") ||
          paymentStatus(item) === originalQuery.status) &&
        textMatch(item.data.applicant || item.owner, "applicant") &&
        textMatch(item.data.contract_no, "contractNo") &&
        textMatch(item.data.case_no, "caseNo") &&
        textMatch(item.data.payee || tx?.counterparty, "payee") &&
        textMatch(item.serial_no, "paymentNo") &&
        textMatch(item.data.fee_type, "feeType") &&
        textMatch(item.customer, "customer") &&
        textMatch(item.title, "title") &&
        textMatch(item.data.handler || item.owner, "handler") &&
        textMatch(item.data.case_stage, "caseStage") &&
        (!applicationRange?.[0] ||
          (!dayjs(applicationDate).isBefore(applicationRange[0], "day") &&
            !dayjs(applicationDate).isAfter(applicationRange[1], "day"))) &&
        (!paymentRange?.[0] ||
          (!dayjs(tx?.transaction_date).isBefore(paymentRange[0], "day") &&
            !dayjs(tx?.transaction_date).isAfter(paymentRange[1], "day"))) &&
        (!originalQuery.deadlineRange?.[0] ||
          (!dayjs(deadline).isBefore(originalQuery.deadlineRange[0], "day") &&
            !dayjs(deadline).isAfter(originalQuery.deadlineRange[1], "day")))
      );
    });
    return result;
  }, [
    fees,
    contractPayments,
    transactions,
    originalQuery,
    originalKind,
    initialView,
    currentUser,
    contractPaymentSource,
  ]);
  useEffect(() => {
    if (tab === "legacy-history") void loadLegacyFinanceHistory(1, legacyFinanceMeta.pageSize);
  }, [tab, legacyFinanceKind, legacyFinanceIncludeInactive]);
  const setOriginalField = (key: string, value: any) =>
    setOriginalQueryDraft((current) => ({ ...current, [key]: value }));
  const queryField = (
    label: string,
    key: string,
    control?: "status" | "feeType" | "date" | "money",
    disabled = false,
  ) => (
    <label className="finance-original-field" key={key}>
      <span>{label}</span>
      {control === "status" ? (
        <Select
          allowClear
          value={originalQueryDraft[key]}
          disabled={disabled || contractPaymentSource.active}
          placeholder="请选择"
          options={paymentStatuses.map((value) => ({ value, label: value }))}
          onChange={(value) => setOriginalField(key, value)}
        />
      ) : control === "feeType" ? (
        <Select
          allowClear
          value={originalQueryDraft[key]}
          disabled={disabled || contractPaymentSource.active}
          placeholder="请选择"
          options={[
            "官方费用",
            "内部费用",
            "结算费用",
            "预损费用",
            "归档费用",
          ].map((value) => ({ value, label: value }))}
          onChange={(value) => setOriginalField(key, value)}
        />
      ) : control === "date" ? (
        <Space.Compact>
          <DatePicker.RangePicker
            value={originalQueryDraft[key]}
            allowClear
            disabled={disabled || contractPaymentSource.active}
            onChange={(value) => setOriginalField(key, value)}
          />
          {["finance-payment-query", "finance-internal-mine"].includes(initialView) && (
            <Button
              size="small"
              disabled={disabled || contractPaymentSource.active}
              onClick={() => setOriginalField(key, undefined)}
            >
              清空
            </Button>
          )}
        </Space.Compact>
      ) : control === "money" ? (
        <Space.Compact>
          <InputNumber
            min={0}
            precision={2}
            disabled={contractPaymentSource.active}
            value={originalQueryDraft[key]?.[0]}
            placeholder="最小金额"
            onChange={(value) =>
              setOriginalField(key, [value, originalQueryDraft[key]?.[1]])
            }
          />
          <Input value="-" readOnly className="finance-money-split" />
          <InputNumber
            min={0}
            precision={2}
            disabled={contractPaymentSource.active}
            value={originalQueryDraft[key]?.[1]}
            placeholder="最大金额"
            onChange={(value) =>
              setOriginalField(key, [originalQueryDraft[key]?.[0], value])
            }
          />
        </Space.Compact>
      ) : (
        <Input
          value={originalQueryDraft[key]}
          disabled={disabled || contractPaymentSource.active}
          onChange={(event) => setOriginalField(key, event.target.value)}
        />
      )}
    </label>
  );
  const paymentQueryFields = [
    queryField("申请日期", "applicationRange", "date"),
    queryField(
      "付款状态",
      "status",
      "status",
      [
        "finance-payment-waiting",
        "finance-payment-print",
        "finance-payment-writeoff",
      ].includes(initialView),
    ),
    queryField(
      "申请人",
      "applicant",
      undefined,
      initialView === "finance-payment-mine",
    ),
    queryField("付款日期", "paymentRange", "date"),
    queryField("合同号", "contractNo"),
    queryField("案件编号", "caseNo"),
    queryField("收款单位", "payee"),
    queryField("请款单号", "paymentNo"),
    queryField(
      "费用类型",
      "feeType",
      paymentQueryFeeTypeControl(initialView),
    ),
    queryField("客户名称", "customer"),
  ];
  const auditQueryFields = [
    queryField("申请日期", "applicationRange", "date"),
    queryField("付款状态", "status", "status", true),
    queryField("案件编号", "caseNo"),
    queryField("请款单号", "paymentNo"),
    queryField("客户名称", "customer"),
    queryField("合同号", "contractNo"),
    queryField("收款单位", "payee"),
    queryField("申请人", "applicant"),
    queryField("费用类型", "feeType", "feeType"),
  ];
  const internalQueryFields = [
    queryField("申请日期", "applicationRange", "date"),
    queryField("付款状态", "status", "status"),
    queryField("申请人", "applicant"),
    queryField("审核日期", "auditRange", "date"),
    queryField("案件编号", "caseNo"),
    queryField("请款单号", "paymentNo"),
    queryField("客户名称", "customer"),
    queryField("案件阶段", "caseStage"),
    queryField("费用类型", "feeType"),
  ];
  const internalMineOperation = (_: unknown, row: Fee) => {
    const maySubmit =
      ["草稿", "已退回"].includes(row.status) &&
      (role === "admin" || role === "manager" || row.owner === currentUser.username);
    const mayEdit =
      row.module === "finance" &&
      row.data.fee_type === "内部费用" &&
      row.status === "草稿" &&
      (canManage || row.owner === currentUser.username);
    const mayCancel =
      canWithdrawFinanceFee(row) && row.data.fee_type === "内部费用";
    return (
      <Space size={0}>
        {maySubmit && (
          <Button type="link" onClick={() => feeAction(row, "submit")}>
            提交审批
          </Button>
        )}
        {mayEdit && (
          <Button type="link" onClick={() => openFeeEdit(row)}>
            编辑
          </Button>
        )}
        {mayCancel && (
          <Button type="link" danger onClick={() => openPaymentCancel(row)}>
            撤回
          </Button>
        )}
        <Button type="link" onClick={() => void openPaymentDetail(row)}>
          查看
        </Button>
      </Space>
    );
  };
  const feeQueryFields = [
    queryField("案件编号", "caseNo"),
    queryField("法院案号", "courtCaseNo"),
    queryField("公证书号", "notaryNo"),
    queryField("退费金额", "refundAmount", "money"),
    queryField("客户名称", "customer"),
    queryField("收款单位", "payee"),
    queryField("付款状态", "status", "status"),
    queryField("付款时间", "paymentRange", "date"),
    queryField("开庭律师", "hearingLawyer"),
    queryField("律师助理", "assistant"),
    queryField("案件阶段", "caseStage"),
    queryField("费用类型", "feeType", "feeType"),
  ];
  const originalOperation = (_: unknown, row: Fee) => (
    initialView === "finance-payment-print" ? (
      <Space size={0}>
        {row.status === "已付款" && (
          <Button type="link" onClick={() => void printPayment(row)}>
            打印
          </Button>
        )}
      </Space>
    ) : [
        "finance-payment-mine",
        "finance-payment-query",
        "finance-internal-mine",
      ].includes(initialView) ? (
      <Space size={0}>
        <Button type="link" onClick={() => void openPaymentDetail(row)}>
          查看
        </Button>
        {initialView === "finance-payment-mine" &&
          row.module === "finance" &&
          row.status === "草稿" &&
          (canManage || row.owner === currentUser.username) && (
            <Button type="link" onClick={() => openFeeEdit(row)}>
              编辑
            </Button>
          )}
        {initialView === "finance-payment-mine" &&
          canWithdrawFinanceFee(row) && (
            <Button type="link" danger onClick={() => openPaymentCancel(row)}>
              撤回请款
            </Button>
          )}
        {initialView === "finance-payment-mine" &&
          ["待审批", "已审批", "待付款"].includes(row.status) &&
          ["admin", "manager", "auditor"].includes(role) && (
            <Button type="link" onClick={() => openPaymentRollback(row)}>
              回滚请款
            </Button>
          )}
      </Space>
    ) : initialView === "finance-internal-payment" ? (
      <Space size={0}>
        <Button type="link" onClick={() => void openPaymentDetail(row)}>
          查看
        </Button>
      </Space>
    ) : initialView === "finance-payment-waiting" ? (
      <Space size={0}>
        <Button type="link" onClick={() => void openPaymentDetail(row)}>
          查看
        </Button>
        {latestTransaction(row) && (
          <Button type="link" onClick={() => void printPayment(row)}>
            打印
          </Button>
        )}
      </Space>
    ) : <Space size={0}>
      {initialView === "finance-payment-writeoff" &&
        row.status === "已付款" &&
        row.data.writeoff_status !== "已核销" && (
          <Button
            type="link"
            onClick={() => {
              writeoffForm.resetFields();
              setWriteoffTarget(row);
            }}
          >
            核销
          </Button>
        )}
      {["草稿", "已退回"].includes(row.status) && (
        <Button type="link" onClick={() => feeAction(row, "submit")}>
          提交
        </Button>
      )}
      {canApprove && row.status === "待审批" && (
        <Button
          type="link"
          onClick={() =>
            isInternalApprovalRoute
              ? setFeeReviewTargets([row])
              : feeAction(row, "approve")
          }
        >
          审批
        </Button>
      )}
      {((row.data?._source_module === "contract_payment" && row.status === "待付款") ||
        ["已审批", "部分付款"].includes(row.status)) && (
        <Button
          type="link"
          onClick={() => {
            transactionForm.setFieldsValue({
              finance_record_id: row.id,
              transaction_type: "付款",
              transaction_date: dayjs(),
              counterparty: row.data.payee || row.customer,
            });
            setTransactionOpen(true);
          }}
        >
          付款
        </Button>
      )}
      {["草稿", "待审批", "已审批", "待付款"].includes(row.status) &&
        (canManage || row.owner === currentUser.username) && (
          <Button type="link" danger onClick={() => openPaymentCancel(row)}>
            撤销请款
          </Button>
        )}
      {["待审批", "已审批", "待付款"].includes(row.status) &&
        ["admin", "manager", "auditor"].includes(role) && (
          <Button type="link" onClick={() => openPaymentRollback(row)}>
            回滚请款
          </Button>
        )}
      {!isInternalApprovalRoute && (
        <Button type="link" onClick={() => openRecordFiles(row, "付款凭证")}>
          附件
        </Button>
      )}
    </Space>
  );
  const openGeneralSettlementReview = (targets: Fee[], approved: boolean) => {
    if (!targets.length) {
      Modal.info({
        title: "提示",
        content: "请选择需要审核的结算申请.",
        okText: "确定",
      });
      return;
    }
    setGeneralSettlementReviewApproved(approved);
    setGeneralSettlementReviewComment("");
    setGeneralSettlementReviewTargets(targets);
  };
  const submitGeneralSettlementReview = async () => {
    if (!generalSettlementReviewTargets.length) return;
    if (!financeActionGates.generalSettlement.tryEnter()) {
      message.info("操作正在提交，请勿重复点击");
      return;
    }
    setGeneralSettlementBusy(true);
    try {
      const response = await api.post(
        "/finance/general-settlements/applications/review",
        {
          application_ids: generalSettlementReviewTargets.map((row) => row.id),
          approved: generalSettlementReviewApproved,
          comment: generalSettlementReviewComment,
        },
      );
      message.success(
        generalSettlementReviewApproved
          ? `已同意 ${response.data.reviewed} 条结算申请`
          : `已拒绝 ${response.data.reviewed} 条结算申请`,
      );
      setGeneralSettlementReviewTargets([]);
      setGeneralSettlementReviewComment("");
      setSelectedOriginalRows([]);
      setGeneralSettlementDetails([]);
      await loadGeneralSettlements(
        originalQuery,
        generalSettlementMeta.page,
        generalSettlementMeta.pageSize,
      );
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "结算审核失败");
      throw error;
    } finally {
      financeActionGates.generalSettlement.leave();
      setGeneralSettlementBusy(false);
    }
  };
  const openGeneralSettlementPayment = (
    targets: Fee[],
    action: "paid" | "rollback",
  ) => {
    if (!targets.length) {
      Modal.info({
        title: "提示",
        content: "请选择回款.",
        okText: "确定",
      });
      return;
    }
    setGeneralSettlementPaymentAction(action);
    setGeneralSettlementPaymentComment("");
    setGeneralSettlementPaymentTargets(targets);
  };
  const submitGeneralSettlementPayment = async () => {
    if (!generalSettlementPaymentTargets.length) return;
    if (
      generalSettlementPaymentAction === "rollback" &&
      !generalSettlementPaymentComment.trim()
    ) {
      message.warning("请输入审核备注.");
      return;
    }
    if (!financeActionGates.generalSettlement.tryEnter()) {
      message.info("操作正在提交，请勿重复点击");
      return;
    }
    setGeneralSettlementBusy(true);
    try {
      const response = await api.post(
        "/finance/general-settlements/applications/payment",
        {
          application_ids: generalSettlementPaymentTargets.map(
            (row) => row.id,
          ),
          action: generalSettlementPaymentAction,
          comment: generalSettlementPaymentComment,
        },
      );
      message.success(
        generalSettlementPaymentAction === "paid"
          ? `已标记 ${response.data.processed} 条结算为已支付`
          : `已回退 ${response.data.processed} 条结算`,
      );
      setGeneralSettlementPaymentTargets([]);
      setGeneralSettlementPaymentComment("");
      setSelectedOriginalRows([]);
      setGeneralSettlementDetails([]);
      await loadGeneralSettlements(
        originalQuery,
        generalSettlementMeta.page,
        generalSettlementMeta.pageSize,
      );
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "结算付款处理失败");
      throw error;
    } finally {
      financeActionGates.generalSettlement.leave();
      setGeneralSettlementBusy(false);
    }
  };
  const openGeneralSettlementReapply = (targets: Fee[]) => {
    if (!targets.length) {
      Modal.info({
        title: "提示",
        content: "请选择回款.",
        okText: "确定",
      });
      return;
    }
    setGeneralSettlementReapplyComment("");
    setGeneralSettlementReapplyTargets(targets);
  };
  const submitGeneralSettlementReapply = async () => {
    if (!generalSettlementReapplyTargets.length) return;
    if (!generalSettlementReapplyComment.trim()) {
      message.warning("请输入备注.");
      return;
    }
    if (!financeActionGates.generalSettlement.tryEnter()) {
      message.info("操作正在提交，请勿重复点击");
      return;
    }
    setGeneralSettlementBusy(true);
    try {
      const response = await api.post(
        "/finance/general-settlements/applications/reapply",
        {
          application_ids: generalSettlementReapplyTargets.map(
            (row) => row.id,
          ),
          comment: generalSettlementReapplyComment,
        },
      );
      message.success(`已重新申请 ${response.data.reapplied} 条结算`);
      setGeneralSettlementReapplyTargets([]);
      setGeneralSettlementReapplyComment("");
      setSelectedOriginalRows([]);
      setGeneralSettlementDetails([]);
      await loadGeneralSettlements(
        originalQuery,
        generalSettlementMeta.page,
        generalSettlementMeta.pageSize,
      );
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "重新申请结算失败");
      throw error;
    } finally {
      financeActionGates.generalSettlement.leave();
      setGeneralSettlementBusy(false);
    }
  };
  const generalSettlementOperation = (_: unknown, row: Fee) => (
    <Space size={0} className="finance-settlement-row-actions">
      <Button
        type="link"
        title="查看分配记录"
        aria-label="查看分配记录"
        icon={
          generalSettlementDetails.includes(row.id) ? (
            <MinusCircleOutlined />
          ) : (
            <PlusCircleOutlined />
          )
        }
        onClick={() =>
          setGeneralSettlementDetails((current) =>
            current.includes(row.id)
              ? current.filter((id) => id !== row.id)
              : [...current, row.id],
          )
        }
      />
      {!isGeneralSettlementPaymentRoute && !isGeneralSettlementPaidRoute && (
        <Button
          type="link"
          title={
            isGeneralSettlementRejectedRoute
              ? "重新申请结算"
              : isGeneralSettlementAuditRoute
                ? "同意结算"
                : "申请结算"
          }
          aria-label={
            isGeneralSettlementRejectedRoute
              ? "重新申请结算"
              : isGeneralSettlementAuditRoute
                ? "同意结算"
                : "申请结算"
          }
          icon={isGeneralSettlementAuditRoute ? <CheckCircleOutlined /> : <ArrowUpOutlined />}
          onClick={() =>
            isGeneralSettlementRejectedRoute
              ? openGeneralSettlementReapply([row])
              : isGeneralSettlementAuditRoute
              ? openGeneralSettlementReview([row], true)
              : void applyGeneralSettlementRows([row.id])
          }
        />
      )}
      <Button
        type="link"
        title="导出结算清单"
        aria-label="导出结算清单"
        icon={<BookOutlined />}
        onClick={() => void exportGeneralSettlement("settlement", [row.id])}
      />
      {(isGeneralSettlementPaymentRoute || isGeneralSettlementPaidRoute) && (
        <>
          <Button
            type="link"
            title="回退结算"
            aria-label="回退结算"
            icon={<RollbackOutlined />}
            onClick={() => openGeneralSettlementPayment([row], "rollback")}
          />
          {isGeneralSettlementPaymentRoute && (
            <Button
              type="link"
              title="标记已支付"
              aria-label="标记已支付"
              icon={<ShareAltOutlined />}
              onClick={() => openGeneralSettlementPayment([row], "paid")}
            />
          )}
        </>
      )}
    </Space>
  );
  const archiveSettlementPendingOperation = (_: unknown, row: any) => (
    <Space size={0} className="finance-settlement-row-actions">
      {isArchiveSettlementPaidRoute || isArchiveSettlementRejectedRoute ? (
        <Button
          type="link"
          title={isArchiveSettlementRejectedRoute ? "回滚归档费" : "回滚归档费结算"}
          aria-label={isArchiveSettlementRejectedRoute ? "回滚归档费" : "回滚归档费结算"}
          icon={<RollbackOutlined />}
          disabled={archiveSettlementBusy}
          onClick={() => openArchiveSettlementRollback([row])}
        />
      ) : (
        <>
          {isArchiveSettlementPaymentRoute && (
            <>
          <Button
            type="link"
            title="同意支付"
            aria-label="同意支付"
            icon={<CheckCircleOutlined />}
            disabled={archiveSettlementBusy}
            onClick={() => openArchiveSettlementReview([row], true)}
          />
          <Button
            type="link"
            title="拒绝支付"
            aria-label="拒绝支付"
            icon={<DeleteOutlined />}
            disabled={archiveSettlementBusy}
            onClick={() => openArchiveSettlementReview([row], false)}
          />
            </>
          )}
          <Button
            type="link"
            title="新建任务"
            aria-label="新建任务"
            onClick={() => openCaseTaskCreate(row)}
          >
            ✉
          </Button>
        </>
      )}
    </Space>
  );
  const paymentPackageOperation = (_: unknown, row: Fee) =>
    initialView === "finance-internal-done" ? (
      <Button
        type="link"
        loading={paymentPackageLoading}
        disabled={paymentPackageLoading}
        onClick={() => setPaymentPackageDetail(row)}
      >
        查看
      </Button>
    ) : (
      <Button
        type="link"
        loading={paymentPackageLoading}
        disabled={paymentPackageLoading}
        onClick={() => {
          paymentPackageWriteoffForm.setFieldsValue({
            package_no: row.serial_no,
            amount: Number(row.data?.total_amount ?? row.data?.amount ?? 0),
            paid_date: dayjs(),
            payment_method: "自动扣款",
            invoice_no: "",
            remark: "",
          });
          setPaymentPackageWriteoffTarget(row);
        }}
      >
        核销
      </Button>
    );
  const internalListOperation = (_: unknown, row: Fee) =>
    initialView === "finance-internal-refused" ? (
      <Button type="link" onClick={() => voidRejectedInternalFee(row)}>
        作废
      </Button>
    ) : ["finance-internal-void", "finance-internal-query"].includes(
        initialView,
      ) ? (
      <Button type="link" onClick={() => setFeeDetail(row)}>
        查看
      </Button>
    ) : null;
  const paymentOriginalColumns = [
    {
      title: "操作",
      key: "action",
      fixed: "left" as const,
      width: 150,
      render: originalOperation,
    },
    { title: "请款单号", dataIndex: "serial_no", width: 165 },
    {
      title: "状态",
      width: 95,
      render: (_: unknown, row: Fee) => paymentStatus(row),
    },
    {
      title: "申请日期",
      width: 110,
      render: (_: unknown, row: Fee) =>
        (row.data.application_date || row.created_at || "—").slice(0, 10),
    },
    {
      title: "申请金额",
      width: 115,
      render: (_: unknown, row: Fee) =>
        row.data.amount == null ? "—" : money(row.data.amount),
    },
    {
      title: "截止日期",
      width: 110,
      render: (_: unknown, row: Fee) =>
        row.data.deadline || row.data.due_date || "—",
    },
    {
      title: "案件编号",
      width: 145,
      render: (_: unknown, row: Fee) => row.data.case_no ? <Button type="link" onClick={() => openCaseDetail(row.data.case_no)}>{row.data.case_no}</Button> : "—",
    },
    {
      title: "案件阶段",
      width: 105,
      render: (_: unknown, row: Fee) => row.data.case_stage || "—",
    },
    {
      title: "合同编号",
      width: 145,
      render: (_: unknown, row: Fee) => row.data.contract_no ? <Button type="link" onClick={() => openContractDetail(row.data.contract_no)}>{row.data.contract_no}</Button> : "—",
    },
    {
      title: "付款日期",
      width: 110,
      render: (_: unknown, row: Fee) =>
        latestTransaction(row)?.transaction_date || "—",
    },
    {
      title: "申请人",
      width: 90,
      render: (_: unknown, row: Fee) => financePersonDisplayName(row.data.applicant || row.owner, row.data.applicant_display_name || (row as any).owner_display_name),
    },
    {
      title: "客户管理人",
      width: 100,
      render: (_: unknown, row: Fee) => financePersonDisplayName(row.data.customer_manager, row.data.customer_manager_display_name),
    },
    {
      title: "交款人",
      width: 90,
      render: (_: unknown, row: Fee) =>
        row.data.payer || row.data.handler || "—",
    },
  ];
  const paymentAuditOriginalColumns = [
    {
      title: "请款单号",
      dataIndex: "serial_no",
      width: 165,
      render: (value: string, row: Fee) => (
        <Button type="link" onClick={() => setFeeReviewTargets([row])}>
          {value}
        </Button>
      ),
    },
    {
      title: "类型",
      width: 95,
      render: (_: unknown, row: Fee) => row.data.fee_type || "—",
    },
    {
      title: "收款单位",
      width: 180,
      render: (_: unknown, row: Fee) => row.data.payee || "—",
    },
    {
      title: "申请人",
      width: 90,
      render: (_: unknown, row: Fee) => financePersonDisplayName(row.data.applicant || row.owner, row.data.applicant_display_name || (row as any).owner_display_name),
    },
    {
      title: "申请付款金额",
      width: 125,
      render: (_: unknown, row: Fee) =>
        row.data.amount == null ? "—" : money(row.data.amount),
    },
    {
      title: "交款截止日期",
      width: 120,
      render: (_: unknown, row: Fee) =>
        row.data.deadline || row.data.due_date || "—",
    },
    {
      title: "案件编号",
      width: 145,
      render: (_: unknown, row: Fee) => row.data.case_no ? <Button type="link" onClick={() => openCaseDetail(row.data.case_no)}>{row.data.case_no}</Button> : "—",
    },
    {
      title: "案件阶段",
      width: 105,
      render: (_: unknown, row: Fee) => row.data.case_stage || "—",
    },
    {
      title: "合同编号",
      width: 145,
      render: (_: unknown, row: Fee) => row.data.contract_no ? <Button type="link" onClick={() => openContractDetail(row.data.contract_no)}>{row.data.contract_no}</Button> : "—",
    },
    {
      title: "合同名称",
      width: 190,
      render: (_: unknown, row: Fee) => row.data.contract_title || "—",
    },
    {
      title: "申请日期",
      width: 110,
      render: (_: unknown, row: Fee) =>
        (row.data.application_date || row.created_at || "—").slice(0, 10),
    },
    {
      title: "状态",
      width: 95,
      render: (_: unknown, row: Fee) => paymentStatus(row),
    },
  ];
  const internalOriginalColumns = [
    {
      title: "操作",
      key: "action",
      width: 70,
      render: internalMineOperation,
    },
    { title: "请款单号", dataIndex: "serial_no", width: 165 },
    {
      title: "状态",
      width: 95,
      render: (_: unknown, row: Fee) => paymentStatus(row),
    },
    {
      title: "申请日期",
      width: 110,
      render: (_: unknown, row: Fee) =>
        (row.data.application_date || row.created_at || "—").slice(0, 10),
    },
    {
      title: "审核日期",
      width: 110,
      render: (_: unknown, row: Fee) =>
        (row.data.audit_date || row.updated_at || "—").slice(0, 10),
    },
    {
      title: "申请金额",
      width: 110,
      render: (_: unknown, row: Fee) =>
        row.data.amount == null ? "—" : money(row.data.amount),
    },
    {
      title: "案件编号",
      width: 145,
      render: (_: unknown, row: Fee) => row.data.case_no ? <Button type="link" onClick={() => openCaseDetail(row.data.case_no)}>{row.data.case_no}</Button> : "—",
    },
    {
      title: "案件阶段",
      width: 105,
      render: (_: unknown, row: Fee) => row.data.case_stage || "—",
    },
    { title: "案件名称", dataIndex: "title", width: 190 },
    {
      title: "付款日期",
      width: 110,
      render: (_: unknown, row: Fee) =>
        latestTransaction(row)?.transaction_date || "—",
    },
    {
      title: "申请人",
      width: 90,
      render: (_: unknown, row: Fee) => financePersonDisplayName(row.data.applicant || row.owner, row.data.applicant_display_name || (row as any).owner_display_name),
    },
  ];
  const feeQueryOriginalColumns = [
    { title: "操作", key: "action", width: 145, render: originalOperation },
    { title: "费用编号", dataIndex: "serial_no", width: 165 },
    {
      title: "费用类型",
      width: 100,
      render: (_: unknown, row: Fee) => row.data.fee_type || "—",
    },
    {
      title: "状态",
      width: 95,
      render: (_: unknown, row: Fee) => paymentStatus(row),
    },
    { title: "费用名称", dataIndex: "title", width: 190 },
    {
      title: "申请金额",
      width: 110,
      render: (_: unknown, row: Fee) =>
        row.data.amount == null ? "—" : money(row.data.amount),
    },
    {
      title: "付款金额",
      width: 110,
      render: (_: unknown, row: Fee) =>
        latestTransaction(row)?.amount == null
          ? "—"
          : money(latestTransaction(row)!.amount!),
    },
    {
      title: "申请日期",
      width: 110,
      render: (_: unknown, row: Fee) =>
        (row.data.application_date || row.created_at || "—").slice(0, 10),
    },
    {
      title: "付款日期",
      width: 110,
      render: (_: unknown, row: Fee) =>
        latestTransaction(row)?.transaction_date || "—",
    },
    {
      title: "案件编号",
      width: 145,
      render: (_: unknown, row: Fee) => row.data.case_no ? <Button type="link" onClick={() => openCaseDetail(row.data.case_no)}>{row.data.case_no}</Button> : "—",
    },
    {
      title: "案件阶段",
      width: 105,
      render: (_: unknown, row: Fee) => row.data.case_stage || "—",
    },
    {
      title: "合同编号",
      width: 145,
      render: (_: unknown, row: Fee) => row.data.contract_no ? <Button type="link" onClick={() => openContractDetail(row.data.contract_no)}>{row.data.contract_no}</Button> : "—",
    },
    { title: "客户名称", dataIndex: "customer", width: 180, render: (value: string, row: Fee) => value ? <Button type="link" onClick={() => openCustomerDetail(value, row.data.customer_no)}>{value}</Button> : "—" },
    {
      title: "申请人",
      width: 90,
      render: (_: unknown, row: Fee) => financePersonDisplayName(row.data.applicant || row.owner, row.data.applicant_display_name || (row as any).owner_display_name),
    },
    {
      title: "经办人",
      width: 90,
      render: (_: unknown, row: Fee) => financePersonDisplayName(row.data.handler || row.owner, row.data.handler_display_name || (row as any).owner_display_name),
    },
    {
      title: "收款单位",
      width: 180,
      render: (_: unknown, row: Fee) =>
        row.data.payee || latestTransaction(row)?.counterparty || "—",
    },
    {
      title: "备注",
      width: 180,
      render: (_: unknown, row: Fee) =>
        row.data.description || row.data.remark || "—",
    },
  ];

  type OriginalFieldSpec = {
    label: string;
    key?: string;
    control?: "date" | "money" | "multi";
    options?: string[];
    defaultValue?: any;
    disabled?: boolean;
    readOnly?: boolean;
    pickerLabel?: string;
  };
  type OriginalRouteConfig = {
    fields: OriginalFieldSpec[];
    headers: string[];
    source:
      | "fees"
      | "incoming"
      | "invoices"
      | "settlements"
      | "generalSettlements"
      | "archiveSettlements"
      | "feeQuery"
      | "refundReviewFees"
      | "paymentPackages"
      | "unissuedFees";
    selectable?: boolean;
    clear?: boolean;
    upload?: boolean;
    export?: boolean;
    note?: string;
  };
  const f = (
    label: string,
    options?: Partial<Omit<OriginalFieldSpec, "label">>,
  ): OriginalFieldSpec => ({ label, ...options });
  const bankFields = [
    f("对方户名"),
    f("对方账号"),
    f("到账日期", { control: "date" }),
    f(initialView === "finance-receipts-boc" ? "导入状态" : "入库状态", {
      options: ["请选择", "未导入", "已导入"],
      defaultValue: "未导入",
    }),
  ];
  const receiptFields = [
    f("回款日期", { control: "date" }),
    f("银行单号"),
    f("客户名称"),
    f("回款单位"),
    f("回款方式"),
    f("合同编号"),
  ];
  const receiptQueryFields = [
    f("案件编号"),
    f("开庭律师"),
    f("律师助理"),
    f("案源人"),
    f("客户管理人"),
    f("调查人"),
    f("客户名称"),
    f("到账单位"),
    f("费用大类", {
      options: ["全部", "官费", "代理费", "其他费用", "第三方费用"],
      defaultValue: "全部",
    }),
    f("到账时间", { control: "date" }),
    f("费用类型"),
    f("分配状态", {
      options: ["全部", "已分配", "未分配"],
      defaultValue: "全部",
    }),
  ];
  const internalSettleFields = [
    f("客户名称"),
    f("案件编号"),
    f("法院案号"),
    f("公证书号"),
    f("开庭律师"),
    f("律师助理"),
    f("案件阶段"),
    f("调查员"),
    f("案源人"),
  ];
  const internalApprovalFields = [
    f("申请日期", { control: "date" }),
    f("付款状态", {
      options:
        initialView === "finance-internal-refund-audit"
          ? ["请选择", ...paymentStatuses]
          : initialView === "finance-internal-archive"
            ? ["待归档", "待审批", "已审批", "已拒绝", "已作废"]
            : ["待审批", "已审批", "已拒绝", "已作废"],
      defaultValue:
        initialView === "finance-internal-archive" ? "待归档" : "待审批",
      disabled: initialView !== "finance-internal-refund-audit",
    }),
    f("申请人"),
    f("付款日期", { control: "date" }),
    f("客户名称"),
    f("案件编号"),
    f("请款单号"),
    f("案件阶段", { disabled: initialView === "finance-internal-audit" }),
    f("费用类型"),
  ];
  const internalListFields = [
    f("申请日期", { control: "date" }),
    f("付款状态", {
      options: ["请选择", "待审批", "已审批", "已拒绝", "已作废"],
      defaultValue:
        initialView === "finance-internal-refused"
          ? "已拒绝"
          : initialView === "finance-internal-void"
            ? "已作废"
            : "请选择",
    }),
    f("申请人"),
    f("审核日期", { control: "date" }),
    f("案件编号"),
    f("请款单号"),
    f("客户名称"),
    f("案件阶段"),
    f("费用类型"),
  ];
  const internalPaymentFields = [
    f("申请日期", { control: "date" }),
    f("付款状态", {
      options: ["请选择", "待付款", "已付款"],
      defaultValue: "待付款",
      disabled: true,
    }),
    f("收款人"),
    f("审核日期", { control: "date" }),
    f("案件编号"),
    f("申请人"),
    f("客户名称"),
    f("案件阶段"),
    f("费用类型"),
  ];
  const paymentPackageFields = [
    f("付款包号码"),
    f("付款日期", { control: "date" }),
    f("收款人"),
    f("付款包状态", {
      options: ["请选择", "待核销", "已付款"],
      defaultValue: "请选择",
      disabled: initialView === "finance-internal-writeoff",
    }),
    f("费用类型", { options: ["请选择", "内部费用", "内部提成"] }),
  ];
  const internalCaseStageOptions = Array.from(
    new Set(
      cases
        .map((item) => item.data?.case_stage || item.status)
        .filter(Boolean)
        .map(String),
    ),
  ).sort((a, b) => a.localeCompare(b, "zh-CN"));
  const internalFeeTypeOptions = Array.from(
    new Set(
      fees
        .filter((item) => item.data?.fee_type === "内部费用")
        .map(
          (item) =>
            item.data?.commission_type ||
            item.data?.fee_type_name ||
            item.title ||
            item.data?.fee_type,
        )
        .filter(Boolean)
        .map(String),
    ),
  ).sort((a, b) => a.localeCompare(b, "zh-CN"));
  const internalDetailFields = [
    f("案件编号"),
    f("经办律师"),
    f("律师助理"),
    f("案源人"),
    f("客户名称"),
    f("客户管理人"),
    f("调查人"),
    f("付款状态", {
      options: ["全部", "已付", "未付"],
      defaultValue: "全部",
    }),
    f("付款时间", { control: "date" }),
    f("收款人", {
      defaultValue:
        initialView === "finance-internal-detail"
          ? currentUser.displayName || "管理者"
          : undefined,
      readOnly: initialView === "finance-internal-detail",
    }),
    f("案件阶段", {
      control: "multi",
      options: internalCaseStageOptions,
      defaultValue: [],
    }),
    f("费用类型", {
      control: "multi",
      options: internalFeeTypeOptions,
      defaultValue: [],
    }),
  ];
  const invoiceBaseFields = [
    f("客户名称"),
    f("请票单号"),
    f("发票类别", { options: ["普票", "专票"] }),
    f("开票抬头"),
    f("发票号码"),
    f("发票状态", {
      options: ["待开票", "已开票", "已撤回", "已作废"],
    }),
    f("开票日期", { control: "date" }),
  ];
  const invoiceFields = [...invoiceBaseFields, f("申请人"), f("案件编号")];
  const invoiceMineFields = [...invoiceBaseFields, f("案件编号")];
  const unissuedFields = [
    f("案件编号"),
    f("法院案号"),
    f("公证书号"),
    f("开票金额", { control: "money" }),
    f("客户名称"),
    f("收款单位"),
    f("发票状态", { options: ["未开票", "已开票"], defaultValue: "未开票" }),
    f("开票时间", { control: "date" }),
    f("开庭律师"),
    f("律师助理"),
    f("案件阶段", {
      control: "multi",
      options: internalCaseStageOptions,
      defaultValue: [],
    }),
    f("付款时间", { control: "date" }),
    f("费用类型", {
      control: "multi",
      options: Array.from(
        new Set([
          "官费",
          "一审诉讼费",
          "二审诉讼费",
          "再审诉讼费",
          "公证费",
          "调解金额",
          "判决金额",
          "保全费",
          "执行费",
          "核定成本",
          "律师代理费",
          "其他费用",
          "内部费用",
          "第三方费用",
          ...fees
            .map((item) =>
              item.data?.fee_type === "代理费"
                ? "律师代理费"
                : item.data?.fee_type_name || item.data?.fee_type,
            )
            .filter(Boolean)
            .map(String),
        ]),
      ),
      defaultValue: ["律师代理费"],
    }),
    f("到款单位"),
    f("到款时间", { control: "date" }),
  ];
  const settlementPendingFields = [
    f("客户名称"),
    f("案件编号"),
    f("回款日期", { control: "date" }),
    f("回款单位"),
    f("回款方式"),
    f("客户名称", { key: "customerSecond" }),
    f("开庭律师"),
    f("律师助理"),
    f("客户管理人"),
    f("案源人"),
  ];
  const settlementFields = [
    f("客户名称"),
    f("案件编号"),
    f("客户管理人"),
    f("回款日期", { control: "date" }),
    f("回款单位"),
    f("回款方式"),
    f("提交人"),
    f("提交日期", { control: "date" }),
    f("开庭律师"),
    f("律师助理"),
    f("审核人"),
    f("审核日期", { control: "date" }),
    f("案源人"),
    ...(initialView === "finance-settlement-paid"
      ? [f("付款日期", { control: "date" })]
      : []),
  ];
  const archiveFields = [
    f("案件类型", {
      options: [
        "请选择",
        "民事争议",
        "刑事案件",
        "行政案件及国家赔偿",
        "法律顾问",
        "仲裁",
      ],
      defaultValue: "请选择",
    }),
    f("案件阶段"),
    f("回款单位"),
    f("回款时间", { control: "date" }),
    f("开庭律师"),
    f("律师助理"),
    f("提交人"),
    ...([
      "finance-archive-fee-pending",
      "finance-archive-fee-payment",
      "finance-archive-fee-paid",
    ].includes(initialView)
      ? [f("结算支付日期", { control: "date" })]
      : [f("提交日期", { control: "date" })]),
    f("案件编号"),
    f("客户名称"),
    f("审核人"),
    ...(initialView === "finance-archive-fee-payment"
      ? [f("归档日期", { control: "date" })]
      : initialView === "finance-archive-fee-paid"
        ? [
            f("归档日期", { control: "date" }),
            f("归档费支付日期", { control: "date" }),
          ]
        : initialView === "finance-archive-fee-refused"
          ? [f("审核日期", { control: "date" })]
          : []),
  ];

  const routeConfigs: Record<string, OriginalRouteConfig> = {
    "finance-payment-print": {
      fields: [
        f("申请日期", { control: "date" }),
        f("付款状态", paymentPrintStatusField(initialView)),
        f("申请人"),
        f("付款日期", { control: "date" }),
        f("合同号"),
        f("案件编号"),
        f("收款单位"),
        f("请款单号"),
        f("费用类型"),
        f("客户名称"),
      ],
      source: "fees",
      selectable: true,
      clear: true,
      export: true,
      headers: [
        "操作",
        "请款单号",
        "状态",
        "申请日期",
        "申请金额",
        "截止日期",
        "案件编号",
        "案件阶段",
        "合同编号",
        "付款日期",
        "申请人",
        "客户管理人",
        "交款人",
      ],
    },
    "finance-receipts-icbc": {
      fields: bankFields,
      source: "incoming",
      selectable: true,
      upload: true,
      headers: [
        "管家卡卡号/收款账号",
        "管家卡卡名称/收款名称",
        "对方账号/回款账号",
        "对方户名/回款单位",
        "金额/回款金额",
        "收付款标志/回款方式",
        "收付款日期/回款日期",
        "渠道",
        "流水号",
        "备注",
        "摘要",
        "状态",
      ],
    },
    "finance-receipts-citic": {
      fields: bankFields,
      source: "incoming",
      selectable: true,
      upload: true,
      headers: [
        "收款账号",
        "收款银行",
        "对方账号/回款账号",
        "对方户名/回款单位",
        "金额/回款金额",
        "收付款标志/回款方式",
        "收付款日期/回款日期",
        "对方账号开户网点名称",
        "柜员交易号",
        "备注",
        "状态",
      ],
    },
    "finance-receipts-boc": {
      fields: bankFields,
      source: "incoming",
      selectable: true,
      upload: true,
      headers: [
        "交易类型/回款方式",
        "交易日期/回款日期",
        "付款人账号/回款账号",
        "付款人名称/回款单位",
        "交易金额/回款金额",
        "交易流水号/银行单号",
        "摘要",
        "用途",
        "交易附言",
        "备注",
        "状态",
      ],
    },
    ...Object.fromEntries(
      [
        "finance-receipts-manage",
        "finance-receipts-claim",
        "finance-receipts-pending",
        "finance-receipts-allocated",
      ].map((route) => [
        route,
        {
          fields: receiptFields,
          source: "incoming",
          selectable: true,
          headers: [
            "操作",
            "客户名称",
            "客户管理人",
            "回款单位",
            "回款日期",
            "回款金额",
            "已分金额",
            "未分金额",
            "已分官费",
            "已分代理费",
            "已分其他费用",
            "回款方式",
            "合同编号",
            "备注",
          ],
        },
      ]),
    ),
    "finance-receipts-query": {
      fields: receiptQueryFields,
      source: "incoming",
      selectable: true,
      clear: true,
      export: true,
      headers: [
        "案号",
        "客户",
        "开庭律师",
        "律师助理",
        "案源人",
        "客户管理人",
        "调查人",
        "费用类型",
        "金额",
        "到账时间",
        "到账单位",
        "到账金额",
        "合同号",
      ],
    },
    "finance-internal-settle": {
      fields: internalSettleFields,
      source: "settlements",
      selectable: true,
      clear: true,
      export: true,
      headers: [
        "案号",
        "原告",
        "被告",
        "金额",
        "回款单位",
        "到账金额",
        "到账时间",
        "结算状态",
        "案件阶段",
        "案源人",
        "开庭律师",
        "律师助理",
        "调查员",
        "品管",
      ],
    },
    ...Object.fromEntries(
      [
        "finance-internal-archive",
        "finance-internal-audit",
        "finance-internal-fee-audit",
      ].map((route) => [
        route,
        {
          fields: internalApprovalFields,
          source: "fees",
          selectable: true,
          headers: [
            "操作",
            "请款单号",
            "状态",
            "申请日期",
            "申请金额",
            "案件编号",
            "案件阶段",
            "案件名称",
            "申请人",
            "客户名称",
          ],
        },
      ]),
    ),
    "finance-internal-refund-audit": {
      fields: internalApprovalFields,
      source: "refundReviewFees",
      selectable: true,
      headers: [
        "操作",
        "请款单号",
        "状态",
        "申请日期",
        "申请金额",
        "案件编号",
        "案件阶段",
        "案件名称",
        "申请人",
        "客户名称",
      ],
    },
    ...Object.fromEntries(
      ["finance-internal-refused", "finance-internal-void"].map((route) => [
        route,
        {
          fields: internalListFields,
          source: "fees",
          headers: [
            "操作",
            "请款单号",
            "状态",
            "申请日期",
            "审核日期",
            "申请金额",
            "案件编号",
            "案件阶段",
            "案件名称",
            "付款日期",
            "申请人",
            "",
          ],
        },
      ]),
    ),
    "finance-internal-payment": {
      fields: internalPaymentFields,
      source: "fees",
      selectable: true,
      headers: [
        "操作",
        "状态",
        "申请人",
        "申请日期",
        "审核日期",
        "收款人",
        "提成类型",
        "基数",
        "参考提成",
        "实际提成",
        "案件编号",
        "案件阶段",
        "案件名称",
        "付款日期",
      ],
    },
    ...Object.fromEntries(
      ["finance-internal-writeoff", "finance-internal-done"].map((route) => [
        route,
        {
          fields: paymentPackageFields,
          source: "paymentPackages",
          clear: ["finance-internal-writeoff", "finance-internal-done"].includes(route),
          headers: [
            "操作",
            "付款包号码",
            "收款人",
            "付款总金额",
            "付款状态",
            "付款日期",
            "付款单据号",
            "备注",
          ],
        },
      ]),
    ),
    "finance-internal-query": {
      fields: internalListFields,
      source: "fees",
      headers: [
        "操作",
        "请款单号",
        "状态",
        "申请日期",
        "审核日期",
        "申请金额",
        "案件编号",
        "案件阶段",
        "案件名称",
        "付款日期",
        "申请人",
        "",
      ],
    },
    ...Object.fromEntries(
      ["finance-internal-detail", "finance-internal-company"].map((route) => [
        route,
        {
          fields: internalDetailFields,
          source: "fees",
          selectable: true,
          clear: true,
          export: true,
          headers: [
            "案号",
            "案件阶段",
            "原告",
            "被告",
            "经办律师",
            "律师助理",
            "案源人",
            "调查人",
            "归档时间",
            "申请时间",
            "内部费用类型",
            "金额",
            "收款人",
            "支付状态",
            "",
          ],
        },
      ]),
    ),
    "finance-invoice-mine": {
      fields: invoiceMineFields,
      source: "invoices",
      selectable: true,
      export: true,
      headers: [
        "操作",
        "请票单号",
        "客户名称",
        "开票金额",
        "高开金额",
        "发票编号",
        "领票人",
        "开票日期",
        "票据状态",
        "备注",
        "",
      ],
    },
    "finance-invoice-pending": {
      fields: invoiceFields,
      source: "invoices",
      selectable: true,
      export: true,
      headers: [
        "操作",
        "请票单号",
        "申请人",
        "客户名称",
        "开票金额",
        "高开金额",
        "开票抬头",
        "备注",
        "",
      ],
    },
    "finance-invoice-company": {
      fields: invoiceFields,
      source: "invoices",
      selectable: true,
      export: true,
      headers: [
        "操作",
        "请票单号",
        "客户名称",
        "开票金额",
        "高开金额",
        "开票抬头",
        "发票号码",
        "申请人",
        "领票人",
        "开票日期",
        "状态",
        "",
      ],
    },
    ...Object.fromEntries(
      ["finance-invoice-unissued", "finance-invoice-company-unissued"].map(
        (route) => [
          route,
          {
            fields: unissuedFields,
            source: "unissuedFees",
            selectable: true,
            clear: true,
            export: true,
            headers: [
              "案号",
              "客户",
              "案件阶段",
              "助理",
              "开庭律师",
              "法院案号",
              "费用类型",
              "金额",
              "开票日期",
              "开票金额",
              "发票查看",
              "到账时间",
              "到账金额",
              "到账单位",
              "付款时间",
              "付款金额",
              "法院名称",
              "付款状态",
              "",
            ],
          },
        ],
      ),
    ),
    "finance-settlement-pending": {
      fields: settlementPendingFields,
      source: "generalSettlements",
      selectable: true,
      headers: [
        "操作",
        "客户名称",
        "客户管理人",
        "回款单位",
        "回款日期",
        "回款金额",
        "已分金额",
        "未分金额",
        "已分官费",
        "已分代理费",
        "已分其他费用",
        "代理费结算金额",
        "扣归档费",
        "实际结算金额",
        "",
      ],
    },
    "finance-settlement-audit": {
      fields: settlementFields,
      source: "generalSettlements",
      selectable: true,
      headers: [
        "操作",
        "客户名称",
        "客户管理人",
        "回款单位",
        "回款日期",
        "回款金额",
        "已分金额",
        "未分金额",
        "已分官费",
        "已分代理费",
        "已分其他费用",
        "代理费结算金额",
        "扣归档费",
        "实际结算金额",
        "",
      ],
    },
    "finance-settlement-payment": {
      fields: settlementFields,
      source: "generalSettlements",
      selectable: true,
      headers: [
        "操作",
        "客户名称",
        "客户管理人",
        "回款单位",
        "回款日期",
        "回款金额",
        "已分金额",
        "未分金额",
        "已分官费",
        "已分代理费",
        "已分其他费用",
        "代理费结算金额",
        "扣归档费",
        "实际结算金额",
        "",
      ],
    },
    "finance-settlement-paid": {
      fields: settlementFields,
      source: "generalSettlements",
      selectable: true,
      clear: true,
      export: true,
      headers: [
        "操作",
        "客户名称",
        "客户管理人",
        "回款单位",
        "回款日期",
        "回款金额",
        "已分金额",
        "未分金额",
        "已分官费",
        "已分代理费",
        "已分其他费用",
        "代理费结算金额",
        "扣归档费",
        "实际结算金额",
        "",
      ],
    },
    "finance-settlement-refused": {
      fields: settlementFields,
      source: "generalSettlements",
      selectable: true,
      clear: true,
      export: true,
      headers: [
        "操作",
        "客户名称",
        "客户管理人",
        "回款单位",
        "回款日期",
        "回款金额",
        "已分金额",
        "未分金额",
        "已分官费",
        "已分代理费",
        "已分其他费用",
        "代理费结算金额",
        "扣归档费",
        "实际结算金额",
        "",
      ],
    },
    ...Object.fromEntries(
      [
        "finance-archive-fee-pending",
        "finance-archive-fee-payment",
        "finance-archive-fee-paid",
        "finance-archive-fee-refused",
      ].map((route) => [
        route,
        {
          fields: archiveFields,
          source:
            [
              "finance-archive-fee-pending",
              "finance-archive-fee-payment",
              "finance-archive-fee-paid",
              "finance-archive-fee-refused",
            ].includes(route)
              ? "archiveSettlements"
              : "fees",
          selectable: true,
          clear: [
            "finance-archive-fee-pending",
            "finance-archive-fee-payment",
            "finance-archive-fee-paid",
            "finance-archive-fee-refused",
          ].includes(route),
          export: [
            "finance-archive-fee-pending",
            "finance-archive-fee-payment",
            "finance-archive-fee-paid",
            "finance-archive-fee-refused",
          ].includes(route),
          headers: [
            "操作",
            "案号",
            "客户",
            "案件阶段",
            "律师助理",
            "开庭律师",
            "客户管理人",
            "费用类型",
            "回款方式",
            "回款时间",
            "回款金额",
            "归档费金额",
            ...(route === "finance-archive-fee-payment"
              ? ["支付时间"]
              : route === "finance-archive-fee-refused"
                ? ["结算时间", "支付状态"]
                : ["结算时间"]),
            "",
          ],
        },
      ]),
    ),
    "finance-fee-query": {
      fields: [
        f("案件编号"),
        f("法院案号"),
        f("公证书号"),
        f("退费金额", { control: "money" }),
        f("客户名称"),
        f("收款单位"),
        f("付款状态", { options: paymentStatuses }),
        f("付款时间", { control: "date" }),
        f("开庭律师"),
        f("律师助理"),
        f("案件阶段"),
        f("费用类型", {
          control: "multi",
          pickerLabel: "从下列案件阶段中选择",
          options: [
            "官费",
            "一审诉讼费",
            "二审诉讼费",
            "再审诉讼费",
            "公证费",
            "调解金额",
            "判决金额",
            "保全费",
            "执行费",
            "核定成本",
            "代理费",
            "其他费用",
            "内部费用",
            "第三方费用",
          ],
        }),
      ],
      source: "feeQuery",
      selectable: true,
      clear: true,
      export: true,
      headers: [
        "案号",
        "客户",
        "案件阶段",
        "助理",
        "开庭律师",
        "法院案号",
        "费用类型",
        "金额",
        "退费金额",
        "已退金额",
        "到账时间",
        "到账金额",
        "付款时间",
        "付款金额",
        "法院名称",
        "付款状态",
      ],
    },
    "finance-refund": {
      fields: [
        f("案件编号"),
        f("法院案号"),
        f("法院名称"),
        f("付款时间", { control: "date" }),
        f("客户名称"),
        f("收款单位"),
        f("退费进度", {
          options: [
            "准备材料",
            "已提交法院",
            "法院处理中",
            "待退款到账",
            "退款已到账",
            "退费完成",
          ],
        }),
        f("退费金额", { control: "money" }),
        f("开庭律师"),
        f("律师助理"),
        f("案件阶段"),
        f("费用类型", {
          control: "multi",
          pickerLabel: "选择费用类型",
          options: [
            "官费",
            "一审诉讼费",
            "二审诉讼费",
            "再审诉讼费",
            "公证费",
            "保全费",
            "执行费",
            "代理费",
            "其他费用",
          ],
        }),
      ],
      source: "feeQuery",
      selectable: true,
      clear: true,
      export: true,
      headers: [
        "案号",
        "原告",
        "被告",
        "案件阶段",
        "律师助理",
        "开庭律师",
        "费用类型",
        "金额",
        "退费金额",
        "新建时间",
        "法院名称",
        "退费进度",
        "进度时长",
        "操作",
      ],
    },
  };

  const configuredField = (spec: OriginalFieldSpec, index: number) => {
    const key = spec.key || `routeField${index}`;
    const value = originalQueryDraft[key] ?? spec.defaultValue;
    const selectedValues = Array.isArray(value) ? value : [];
    const pendingValues = multiPickerDraft[key] ?? selectedValues;
    return (
      <label className="finance-original-field" key={`${key}-${index}`}>
        <span>{spec.label}</span>
        {spec.control === "multi" ? (
          <Popover
            open={multiPickerOpen === key}
            trigger="click"
            placement="bottomLeft"
            onOpenChange={(open) => {
              setMultiPickerOpen(open ? key : null);
              if (open) {
                setMultiPickerDraft((current) => ({
                  ...current,
                  [key]: selectedValues,
                }));
              }
            }}
            content={
              <div className="finance-internal-tree-picker">
                {spec.pickerLabel && (
                  <div className="finance-internal-tree-label">
                    {spec.pickerLabel}
                  </div>
                )}
                <Checkbox.Group
                  value={pendingValues}
                  onChange={(next) =>
                    setMultiPickerDraft((current) => ({
                      ...current,
                      [key]: next.map(String),
                    }))
                  }
                >
                  {(spec.options || []).map((option, optionIndex) => (
                    <Checkbox
                      className={
                        spec.pickerLabel && optionIndex > 0 && optionIndex < 10
                          ? "finance-fee-tree-child"
                          : undefined
                      }
                      key={option}
                      value={option}
                    >
                      {option}
                    </Checkbox>
                  ))}
                </Checkbox.Group>
                {!spec.options?.length && (
                  <div className="finance-internal-tree-empty">暂无选项</div>
                )}
                <div className="finance-internal-tree-actions">
                  <Button
                    size="small"
                    type="primary"
                    onClick={() => {
                      setOriginalField(key, pendingValues);
                      setMultiPickerOpen(null);
                    }}
                  >
                    确定
                  </Button>
                  <Button size="small" onClick={() => setMultiPickerOpen(null)}>
                    取消
                  </Button>
                </div>
              </div>
            }
          >
            <Input
              readOnly
              value={selectedValues.join(",")}
              placeholder={spec.label}
            />
          </Popover>
        ) : spec.options ? (
          <Select
            allowClear
            value={value}
            disabled={spec.disabled}
            placeholder="请选择"
            options={spec.options.map((option) => ({
              value: option,
              label: option,
            }))}
            onChange={(next) => setOriginalField(key, next)}
          />
        ) : spec.control === "date" ? (
          <DatePicker.RangePicker
            value={originalQueryDraft[key]}
            disabled={spec.disabled}
            onChange={(next) => setOriginalField(key, next)}
          />
        ) : spec.control === "money" ? (
          <Space.Compact>
            <InputNumber
              value={originalQueryDraft[key]?.[0]}
              placeholder="最小金额"
              onChange={(next) =>
                setOriginalField(key, [next, originalQueryDraft[key]?.[1]])
              }
            />
            <Input value="-" readOnly className="finance-money-split" />
            <InputNumber
              value={originalQueryDraft[key]?.[1]}
              placeholder="最大金额"
              onChange={(next) =>
                setOriginalField(key, [originalQueryDraft[key]?.[0], next])
              }
            />
          </Space.Compact>
        ) : (
          <Input
            value={value}
            disabled={spec.disabled}
            readOnly={spec.readOnly}
            onChange={(event) => setOriginalField(key, event.target.value)}
          />
        )}
      </label>
    );
  };
  const originalInvoiceOperation = (_: unknown, row: FinanceFlow) => (
    <Space size={0}>
      {["草稿", "已退回"].includes(row.status) && (
        <Button type="link" onClick={() => submitFlow("invoices", row)}>
          提交
        </Button>
      )}
      {canApprove && row.status === "待审批" && (
        <Button type="link" onClick={() => reviewFlow("invoices", row, true)}>
          审批
        </Button>
      )}
      {row.status === "待开票" && (
        <Button
          type="link"
          onClick={() => {
            issueForm.setFieldsValue({ invoice_date: dayjs() });
            setIssueTarget(row);
          }}
        >
          开票
        </Button>
      )}
      <Button type="link" onClick={() => openRecordFiles(row, "发票扫描件")}>
        附件
      </Button>
    </Space>
  );
  const invoiceMineOperation = (_: unknown, row: FinanceFlow) => (
    <Space size={0}>
      <Button type="link" onClick={() => void openInvoiceDetail(row)}>
        查看
      </Button>
      {["草稿", "已驳回"].includes(row.status) && (
        <Button type="link" onClick={() => openInvoiceEdit(row)}>
          编辑
        </Button>
      )}
      <Button type="link" onClick={() => openRecordFiles(row, "发票扫描件")}>
        附件
      </Button>
      {["草稿", "待审批", "待开票", "已驳回"].includes(row.status) && (
        <Button
          type="link"
          onClick={() =>
            Modal.confirm({
              title: "撤回发票申请单",
              content: `确定撤回请票单 ${row.serial_no}？`,
              okText: "确定",
              cancelText: "取消",
              onOk: async () => {
                try {
                  await api.post(`/finance/invoices/${row.id}/withdraw`, {
                    comment: "我的开票列表撤回",
                  });
                  message.success("发票申请已撤回");
                  await loadInvoiceMine(
                    originalQuery,
                    invoiceMineMeta.page,
                    invoiceMineMeta.pageSize,
                  );
                } catch (error: any) {
                  message.error(
                    error?.response?.data?.detail || "发票申请撤回失败",
                  );
                }
              },
            })
          }
        >
          撤回
        </Button>
      )}
    </Space>
  );
  const openInvoiceProcess = (row: FinanceFlow) => {
    issueForm.setFieldsValue({
      invoice_holder:
        financePersonDisplayName(
          row.data?.recipient || currentUser.username,
          row.data?.recipient_display_name || currentUser.displayName,
        ),
      extra_amount: Number(row.data?.extra_amount || 0),
      invoice_no: "",
      invoice_date: dayjs(),
      comment: "",
    });
    setInvoiceProcess(row);
  };
  const invoicePendingOperation = (_: unknown, row: FinanceFlow) => (
    <Space size={0}>
      <Button type="link" onClick={() => void openInvoiceDetail(row)}>
        查看
      </Button>
      <Button type="link" onClick={() => openRecordFiles(row, "发票扫描件")}>
        附件
      </Button>
      <Button type="link" onClick={() => openInvoiceProcess(row)}>
        开票
      </Button>
    </Space>
  );
  const openInvoiceNumberChange = (row: FinanceFlow) => {
    invoiceNumberForm.setFieldsValue({
      application_no: row.serial_no,
      contract_no: row.data?.contract_no || "",
      old_invoice_no: row.data?.invoice_no || "",
      new_invoice_no: "",
    });
    setInvoiceNumberTarget(row);
  };
  const submitInvoiceNumberChange = async () => {
    if (!invoiceNumberTarget) return;
    const invoiceNo = String(
      invoiceNumberForm.getFieldValue("new_invoice_no") || "",
    ).trim();
    if (!invoiceNo) {
      Modal.info({
        title: "提示",
        content: "请输入新发票号码.",
        okText: "确定",
      });
      return;
    }
    setInvoiceMutationLoading(true);
    try {
      await api.post(
        `/finance/invoices/${invoiceNumberTarget.id}/change-number`,
        { invoice_no: invoiceNo },
      );
      message.success("修改成功.");
      setInvoiceNumberTarget(null);
      invoiceNumberForm.resetFields();
      await loadInvoiceCompany(
        originalQuery,
        invoiceCompanyMeta.page,
        invoiceCompanyMeta.pageSize,
      );
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "发票号码修改失败");
    } finally {
      setInvoiceMutationLoading(false);
    }
  };
  const openInvoiceDateChange = (row: FinanceFlow) => {
    invoiceDateForm.setFieldsValue({
      application_no: row.serial_no,
      application_date: dayjs(row.data?.application_date || row.created_at),
      invoice_date: row.data?.invoice_date ? dayjs(row.data.invoice_date) : null,
    });
    setInvoiceDateTarget(row);
  };
  const submitInvoiceDateChange = async () => {
    if (!invoiceDateTarget) return;
    const applicationDate = invoiceDateForm.getFieldValue("application_date");
    const invoiceDate = invoiceDateForm.getFieldValue("invoice_date");
    if (!applicationDate) {
      Modal.info({
        title: "提示",
        content: "请输入发票申请日期.",
        okText: "确定",
      });
      return;
    }
    if (!invoiceDate) {
      Modal.info({
        title: "提示",
        content: "请输入发票开票日期.",
        okText: "确定",
      });
      return;
    }
    setInvoiceMutationLoading(true);
    try {
      await api.post(
        `/finance/invoices/${invoiceDateTarget.id}/change-date`,
        {
          application_date: applicationDate.format("YYYY-MM-DD"),
          invoice_date: invoiceDate.format("YYYY-MM-DD"),
        },
      );
      message.success("修改成功.");
      setInvoiceDateTarget(null);
      invoiceDateForm.resetFields();
      await loadInvoiceCompany(
        originalQuery,
        invoiceCompanyMeta.page,
        invoiceCompanyMeta.pageSize,
      );
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "发票日期修改失败");
    } finally {
      setInvoiceMutationLoading(false);
    }
  };
  const submitInvoiceCancel = async () => {
    if (!invoiceCancel) return;
    const reason = invoiceCancelReason.trim();
    if (!reason) {
      Modal.info({ title: "提示", content: "请输入作废原因.", okText: "确定" });
      return;
    }
    setInvoiceMutationLoading(true);
    try {
      await api.post(`/finance/invoices/${invoiceCancel.id}/void`, { reason });
      message.success("发票已作废并生成冲销流水");
      setInvoiceCancel(null);
      setInvoiceCancelReason("");
      await loadInvoiceCompany(
        originalQuery,
        invoiceCompanyMeta.page,
        invoiceCompanyMeta.pageSize,
      );
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "发票作废失败");
    } finally {
      setInvoiceMutationLoading(false);
    }
  };
  const invoiceCompanyOperation = (_: unknown, row: FinanceFlow) => (
    <Space size={0} wrap>
      <Button type="link" onClick={() => void openInvoiceDetail(row)}>
        查看
      </Button>
      <Button type="link" onClick={() => openRecordFiles(row, "发票扫描件")}>
        附件
      </Button>
      {!['已撤回', '已作废'].includes(row.status) && <>
        <Button
          type="link"
          onClick={() => {
            setInvoiceCancelReason("");
            setInvoiceCancel(row);
          }}
        >
          作废
        </Button>
        <Button type="link" onClick={() => openInvoiceNumberChange(row)}>
          修改发票号
        </Button>
        <Button type="link" onClick={() => openInvoiceDateChange(row)}>
          修改发票日期
        </Button>
      </>}
    </Space>
  );
  const rawCellValue = (row: any, header: string) => {
    const data = row.data || {};
    const tx = row.id && row.data ? latestTransaction(row) : undefined;
    const linkedCase = linkedCaseForFee(row);
    const linkedCaseData = linkedCase?.data || {};
    const values: Record<string, any> = {
      操作: null,
      请款单号: row.serial_no,
      请票单号: row.serial_no,
      费用编号: row.serial_no,
      状态:
        initialView === "finance-internal-payment"
          ? paymentStatus(row)
          : initialView === "finance-internal-refused" &&
              ["已拒绝", "已退回", "已驳回"].includes(row.status)
          ? "已拒绝"
          : row.status,
      付款状态:
        initialView === "finance-internal-refund-audit"
          ? paymentStatus(row)
          : isInvoiceUnissuedRoute
            ? data.payment_status || ""
          : isInternalDetailRoute
            ? data.payment_status || "未付"
          : data.payment_status || row.status,
      票据状态: isFeeQueryRoute ? caseFeeRefundStatusLabel(row) : row.status,
      客户: row.customer || row.claimed_customer,
      客户名称: row.customer || row.claimed_customer,
      客户管理人: financePersonDisplayName(
        row.customer_manager || data.customer_manager || linkedCaseData.customer_manager,
        row.customer_manager_display_name || data.customer_manager_display_name || linkedCaseData.customer_manager_display_name,
      ),
      案号: data.case_no,
      案件编号: data.case_no,
      案件阶段:
        data.case_stage || linkedCaseData.case_stage || linkedCase?.status,
      结算状态: data.settlement_status || row.status,
      案源人: financePersonDisplayName(
        data.case_source || data.source_person || linkedCaseData.case_source || linkedCaseData.business_owner,
        data.case_source_display_name || data.source_person_display_name || linkedCaseData.case_source_display_name || linkedCaseData.business_owner_display_name,
      ),
      调查员: financePersonDisplayName(data.investigator || linkedCaseData.investigator, data.investigator_display_name || linkedCaseData.investigator_display_name),
      调查人: financePersonDisplayName(data.investigator || linkedCaseData.investigator, data.investigator_display_name || linkedCaseData.investigator_display_name),
      经办律师: financePersonDisplayNames(
        data.handling_lawyers || data.handling_lawyer || data.handler || linkedCaseData.handling_lawyers || linkedCaseData.handling_lawyer || linkedCaseData.case_lawyer,
        data.handling_lawyer_display_names || linkedCaseData.handling_lawyer_display_names,
      ),
      律师助理: financePersonDisplayName(
        data.lawyer_assistant || data.assistant || linkedCaseData.lawyer_assistant || linkedCaseData.assistant,
        data.lawyer_assistant_display_name || data.assistant_display_name || linkedCaseData.lawyer_assistant_display_name || linkedCaseData.assistant_display_name,
      ),
      品管: financePersonDisplayName(data.quality_manager || data.quality_control, data.quality_manager_display_name || data.quality_control_display_name),
      公证书号: data.certificate_no,
      助理: financePersonDisplayName(data.assistant || data.lawyer_assistant, data.assistant_display_name || data.lawyer_assistant_display_name),
      开庭律师: financePersonDisplayName(data.hearing_lawyer, data.hearing_lawyer_display_name),
      法院案号: data.court_case_no,
      法院名称: data.court_name,
      案件名称:
        (isInternalApprovalRoute ||
        [
          "finance-internal-refused",
          "finance-internal-void",
          "finance-internal-query",
        ].includes(initialView)
          ? linkedCase?.title
          : "") || row.title,
      原告:
        data.plaintiff ||
        linkedCaseData.plaintiff ||
        linkedCaseData.appellant_names,
      被告:
        data.defendant || data.opponent ||
        linkedCaseData.defendant ||
        linkedCaseData.appellee_names ||
        linkedCaseData.opponent,
      申请人: financePersonDisplayName(data.applicant || row.owner, data.applicant_display_name || row.owner_display_name),
      申请日期: (data.application_date || row.created_at || "").slice?.(0, 10),
      提交人: financePersonDisplayName(
        data.archive_payment_submitted_by || data.submitted_by || row.owner,
        data.archive_payment_submitter_display_name || data.submitted_by_display_name || row.owner_display_name,
      ),
      提交日期: (
        data.archive_payment_submitted_at ||
        data.settlement_paid_at ||
        row.created_at ||
        ""
      ).slice?.(0, 10),
      审核人: financePersonDisplayName(
        data.archive_payment_reviewer || data.reviewer,
        data.archive_payment_reviewer_display_name || data.reviewer_display_name,
      ),
      审核日期: (
        data.archive_payment_reviewed_at ||
        data.audit_date ||
        (["已审批", "已拒绝", "已驳回", "已作废", "已付款"].includes(
          row.status,
        )
          ? row.updated_at
          : "") ||
        ""
      ).slice?.(0, 10),
      付款日期: data.paid_date || tx?.transaction_date || data.payment_date,
      付款时间: data.paid_date || tx?.transaction_date || data.payment_date,
      付款包号码: row.serial_no,
      付款总金额: data.total_amount ?? data.amount,
      付款单据号: data.invoice_no || data.writeoff_voucher_no,
      申请金额: data.amount,
      金额: data.amount ?? row.amount,
      归档时间: data.archive_date || data.audited_time,
      申请时间: (
        data.application_date ||
        row.created_at ||
        ""
      ).slice?.(0, 10),
      新建时间: (data.created_at || row.created_at || "").slice?.(0, 10),
      内部费用类型:
        data.internal_fee_type ||
        data.commission_type ||
        data.fee_type_name ||
        row.title ||
        data.fee_type,
      支付状态: isArchiveSettlementRejectedRoute
        ? row.status
        : data.payment_status || "未付",
      退费金额: isFeeQueryRoute
        ? data.refund_requested_amount
        : data.refund_amount,
      已退金额: data.refunded_amount,
      退费进度: data.refund_status_label || data.refund_status,
      进度时长: data.refund_progress_days,
      付款金额: isInvoiceUnissuedRoute
        ? data.paid_amount
        : tx?.amount || data.payment_amount,
      回款金额:
        isGeneralSettlementRoute || isArchiveSettlementActiveRoute
          ? data.receipt_amount
          : row.amount,
      回款日期: row.received_date || data.received_date,
      回款时间: row.received_date || data.received_date,
      到账时间:
        data.cashed_date || row.received_date || data.receipt_date,
      到账金额: isInvoiceUnissuedRoute
        ? data.cashed_amount
        : row.amount ?? data.receipt_amount,
      回款单位: row.payer_name || data.payer_name || data.payee,
      到账单位:
        data.received_payer_name || row.payer_name || data.payee,
      收款人: data.payee || tx?.counterparty,
      收款单位: data.paid_organization || data.payee || tx?.counterparty,
      提成类型: data.commission_type || row.title || data.fee_type,
      基数: data.commission_base ?? data.base_amount ?? 0,
      参考提成: data.reference_commission ?? data.base_commission ?? 0,
      实际提成: data.actual_commission ?? data.amount,
      备注: row.remark || data.remark,
      银行单号: row.bank_reference,
      流水号: row.bank_reference,
      对方户名: row.payer_name,
      对方账号: row.payer_account,
      入库状态: data.import_status || row.status,
      导入状态: data.import_status || row.status,
      已分金额: row.allocated_amount ?? data.allocated_amount,
      未分金额: row.remaining_amount ?? data.remaining_amount,
      已分官费: data.assigned_official_fee,
      已分代理费: data.assigned_agency_fee,
      已分其他费用: data.assigned_other_fee,
      代理费结算金额: data.agency_settlement_amount,
      扣归档费: data.archive_fee,
      归档费金额: data.archive_fee_amount,
      结算时间: data.settlement_paid_at,
      支付时间: data.settlement_paid_at,
      实际结算金额: data.actual_settlement_amount,
      回款方式: data.payment_method,
      合同号: row.contract_no || data.contract_no,
      合同编号: row.contract_no || data.contract_no,
      发票编号: data.invoice_no,
      发票号码: data.invoice_no,
      开票金额: isInvoiceUnissuedRoute
        ? data.invoice_amount
        : data.amount,
      高开金额: data.extra_amount,
      开票抬头: data.invoice_title,
      开票日期: data.invoice_date,
      发票查看: data.invoice_no,
      领票人: data.recipient,
      费用类型: data.fee_type,
    };
    const direct = values[header];
    if (Object.prototype.hasOwnProperty.call(values, header)) {
      return direct;
    }
    for (const [label, candidate] of Object.entries(values)) {
      if (header.includes(label) && candidate != null && candidate !== "")
        return candidate;
    }
    return undefined;
  };
  const cellValue = (row: any, header: string) => {
    const value = rawCellValue(row, header);
    if (value == null || value === "") return "—";
    if (
      isArchiveSettlementActiveRoute &&
      ["回款时间", "结算时间", "支付时间"].includes(header) &&
      dayjs(String(value)).isValid()
    )
      return dayjs(String(value)).format("YYYY-M-D");
    if (
      typeof value === "number" &&
      activeRouteConfig?.source === "paymentPackages" &&
      header === "付款总金额"
    )
      return String(Number(value));
    if (
      typeof value === "number" &&
      header === "申请金额" &&
      [
        "finance-internal-refused",
        "finance-internal-void",
        "finance-internal-query",
      ].includes(initialView)
    )
      return Number(value).toFixed(2);
    if (
      typeof value === "number" &&
      isInternalDetailRoute &&
      header === "金额"
    )
      return Number(value).toFixed(2);
    if (
      typeof value === "number" &&
      (isInvoiceMineRoute || isInvoicePendingRoute || isInvoiceCompanyRoute) &&
      ["开票金额", "高开金额"].includes(header)
    )
      return String(Number(value));
    if (
      typeof value === "number" &&
      isInvoiceUnissuedRoute &&
      ["金额", "开票金额", "到账金额", "付款金额"].includes(header)
    )
      return Number(value).toFixed(2);
    if (
      typeof value === "number" &&
      isFeeQueryRoute &&
      ["金额", "退费金额", "已退金额", "到账金额", "付款金额"].includes(
        header,
      )
    )
      return Number(value).toFixed(2);
    if (
      typeof value === "number" &&
      isGeneralSettlementRoute &&
      [
        "回款金额",
        "已分金额",
        "未分金额",
        "已分官费",
        "已分代理费",
        "已分其他费用",
        "代理费结算金额",
        "扣归档费",
        "实际结算金额",
      ].includes(header)
    )
      return Number(value).toFixed(2);
    if (
      typeof value === "number" &&
      isArchiveSettlementActiveRoute &&
      ["回款金额", "归档费金额"].includes(header)
    )
      return Number(value).toFixed(2);
    return typeof value === "number" ? money(value) : value;
  };
  const openFinanceCustomerDetail = (row: any, header: string) => {
    const customerNo =
      row.data?.customer_no ||
      row.data?.customer_serial_no ||
      row.customer_no ||
      (header === "客户编号" ? cellValue(row, header) : undefined);
    const customerName =
      header === "客户编号"
        ? row.data?.customer || row.customer || row.data?.claimed_customer || customerNo
        : cellValue(row, header);
    openCustomerDetail(customerName, customerNo);
  };
  const openRowCaseLogs = async (row: Fee) => {
    const caseId = row.data?.case_id;
    if (!caseId) {
      message.warning("无法获取关联案件");
      return;
    }
    setSettlementActionLoading(true);
    try {
      const { data } = await api.get(`/records/${caseId}/history`);
      const items = (data.items || []).map((item: any) => ({
        ...item,
        source_case_no: row.data?.case_no || row.serial_no || "",
      }));
      setSettlementContextRows(items);
      setSettlementContext({ mode: "logs", caseRecords: [row] });
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "案件日志加载失败");
    } finally {
      setSettlementActionLoading(false);
    }
  };
  const refundCaseFeeOperation = (_: unknown, row: Fee) => (
    <Button type="link" onClick={() => void openRowCaseLogs(row)}>
      日志
    </Button>
  );
  const activeRouteConfig = routeConfigs[initialView];
  const settlementColumnWidths = [
    86, 129, 172, 69, 129, 69, 86, 69, 69, 69, 69, 69, 69, 69,
  ];
  const generalSettlementColumnWidths = [
    88, 212, 176, 264, 141, 106, 106, 106, 106, 106, 106, 106, 106, 106,
    17,
  ];
  const archiveSettlementColumnWidths = [
    85, 136, 255, 136, 136, 136, 136, 136, 136, 136, 136, 136, 136, 17,
  ];
  const archiveSettlementRejectedColumnWidths = [
    90, 180, 269, 126, 126, 108, 144, 108, 144, 108, 108, 108, 108, 108, 17,
  ];
  const internalListColumnWidths = [
    50, 167, 134, 134, 134, 134, 134, 167, 501, 167, 167, 17,
  ];
  const invoiceUnissuedColumnWidths = [
    104, 207, 83, 83, 83, 155, 83, 83, 83, 83, 83, 83, 83, 155, 83,
    83, 155, 83, 17,
  ];
  const configuredColumns = activeRouteConfig?.headers.map((header, index) => ({
    title: header.includes("/") ? (
      <span className="finance-stacked-header">
        {header.split("/").map((part) => (
          <span key={part}>{part}</span>
        ))}
      </span>
    ) : (
      header
    ),
    key: `${header}-${index}`,
    width:
      initialView === "finance-internal-settle"
        ? settlementColumnWidths[index]
        : isGeneralSettlementRoute
          ? generalSettlementColumnWidths[index]
        : isArchiveSettlementRejectedRoute
          ? archiveSettlementRejectedColumnWidths[index]
        : isArchiveSettlementActiveRoute
          ? archiveSettlementColumnWidths[index]
        : isInvoiceUnissuedRoute
          ? invoiceUnissuedColumnWidths[index]
        : [
              "finance-internal-refused",
              "finance-internal-void",
              "finance-internal-query",
            ].includes(initialView)
          ? internalListColumnWidths[index]
          : header === "操作"
            ? isInvoiceCompanyRoute
              ? 280
              : 145
            : Math.max(90, Math.min(190, header.length * 17 + 45)),
    fixed:
      header === "操作" &&
      ![
        "finance-internal-refused",
        "finance-internal-void",
        "finance-internal-query",
        "finance-settlement-pending",
        "finance-settlement-audit",
        "finance-archive-fee-pending",
        "finance-archive-fee-payment",
        "finance-archive-fee-paid",
        "finance-archive-fee-refused",
      ].includes(initialView)
        ? ("left" as const)
        : undefined,
    render: (_: unknown, row: any) =>
      header === "" ? null : header === "操作" ? (
        [
          "finance-internal-refused",
          "finance-internal-void",
          "finance-internal-query",
        ].includes(initialView) ? (
          internalListOperation(_, row)
        ) : activeRouteConfig?.source === "invoices" ? (
          isInvoiceMineRoute
            ? invoiceMineOperation(_, row)
            : isInvoicePendingRoute
              ? invoicePendingOperation(_, row)
              : isInvoiceCompanyRoute
                ? invoiceCompanyOperation(_, row)
                : originalInvoiceOperation(_, row)
        ) : activeRouteConfig?.source === "incoming" ? (
          originalIncomingOperation(_, row)
        ) : activeRouteConfig?.source === "generalSettlements" ? (
          generalSettlementOperation(_, row)
        ) : activeRouteConfig?.source === "archiveSettlements" ? (
          archiveSettlementPendingOperation(_, row)
        ) : activeRouteConfig?.source === "paymentPackages" ? (
          paymentPackageOperation(_, row)
        ) : isRefundCaseFeeRoute ? (
          refundCaseFeeOperation(_, row)
        ) : (
          originalOperation(_, row)
        )
      ) : [
          "finance-internal-refused",
          "finance-internal-void",
          "finance-internal-query",
        ].includes(initialView) && header === "请款单号" ? (
        <Button type="link" onClick={() => setFeeDetail(row)}>
          {cellValue(row, header)}
        </Button>
      ) : [
          "finance-internal-refused",
          "finance-internal-void",
          "finance-internal-query",
        ].includes(initialView) && header === "案件编号" ? (
        cellValue(row, header) ? <Button type="link" onClick={() => openCaseDetail(cellValue(row, header))}>{cellValue(row, header)}</Button> : "—"
      ) : initialView === "finance-internal-settle" && header === "案号" ? (
        cellValue(row, header) ? <Button type="link" onClick={() => openCaseDetail(cellValue(row, header))}>{cellValue(row, header)}</Button> : "—"
      ) : isInvoiceUnissuedRoute && header === "案号" ? (
        cellValue(row, header) ? <Button type="link" onClick={() => openCaseDetail(cellValue(row, header))}>{cellValue(row, header)}</Button> : "—"
      ) : isInvoiceUnissuedRoute && header === "发票查看" ? (
        row.data?.invoice_no ? (
          <Button
            type="link"
            onClick={() => {
              const invoice = invoices.find(
                (item) => item.id === Number(row.data?.invoice_record_id || 0),
              );
              if (invoice) void openRecordFiles(invoice, "发票扫描件");
              else message.warning("关联发票记录不存在或无权访问");
            }}
          >
            {row.data.invoice_no}
          </Button>
        ) : null
      ) : isInternalDetailRoute && header === "案号" ? (
        cellValue(row, header) ? <Button type="link" onClick={() => openCaseDetail(cellValue(row, header))}>{cellValue(row, header)}</Button> : "—"
      ) : isArchiveSettlementActiveRoute && header === "案号" ? (
        cellValue(row, header) ? <Button type="link" onClick={() => openCaseDetail(cellValue(row, header))}>{cellValue(row, header)}</Button> : "—"
      ) : isFeeQueryRoute && ["案号", "案件编号"].includes(header) ? (
        cellValue(row, header) ? <Button type="link" onClick={() => openCaseDetail(cellValue(row, header))}>{cellValue(row, header)}</Button> : "—"
      ) : ["客户", "客户名称", "客户编号"].includes(header) ? (
        cellValue(row, header) ? <Button
          type="link"
          onClick={() => openFinanceCustomerDetail(row, header)}
        >
          {cellValue(row, header)}
        </Button> : "—"
      ) : ["合同号", "合同编号"].includes(header) ? (
        cellValue(row, header) ? <Button type="link" onClick={() => openContractDetail(cellValue(row, header))}>{cellValue(row, header)}</Button> : "—"
      ) : (isInvoiceMineRoute || isInvoicePendingRoute || isInvoiceCompanyRoute) && header === "请票单号" ? (
        <Button
          type="link"
          onClick={() =>
            isInvoicePendingRoute
              ? openInvoiceProcess(row)
              : void openInvoiceDetail(row)
          }
        >
          {cellValue(row, header)}
        </Button>
      ) : initialView === "finance-internal-payment" &&
        header === "案件编号" ? (
        cellValue(row, header) ? <Button type="link" onClick={() => openCaseDetail(cellValue(row, header))}>{cellValue(row, header)}</Button> : "—"
      ) : activeRouteConfig?.source === "paymentPackages" &&
        header === "付款包号码" ? (
        <Button type="link" onClick={() => setPaymentPackageDetail(row)}>
          {cellValue(row, header)}
        </Button>
      ) : (
        cellValue(row, header)
      ),
  }));
  const configuredRows = useMemo(() => {
    if (!activeRouteConfig) return originalFinanceRows;
    let rows: any[] = initialView === "finance-payment-print"
      ? [...originalFinanceRows]
      : isFeeQueryRoute
        ? [...feeQueryRows]
      : isInternalDetailRoute
      ? [...internalDetailRows]
      : isInvoiceMineRoute
        ? [...invoiceMineRows]
        : isInvoicePendingRoute
          ? [...invoicePendingRows]
        : isInvoiceCompanyRoute
            ? [...invoiceCompanyRows]
          : isInvoiceUnissuedRoute
            ? [...invoiceUnissuedRows]
            : activeRouteConfig?.source === "incoming"
              ? [...incoming]
              : activeRouteConfig?.source === "generalSettlements"
                ? [...generalSettlementRows]
              : activeRouteConfig?.source === "archiveSettlements"
                ? [...archiveSettlementRows]
              : activeRouteConfig?.source === "settlements"
                ? [...pendingSettlements]
                : activeRouteConfig?.source === "paymentPackages"
                  ? [...paymentPackages]
                  : activeRouteConfig?.source === "refundReviewFees"
                    ? [...refundReviewFees]
                    : activeRouteConfig?.source === "invoices"
                      ? [...invoices]
                      : [...fees];
    if (activeRouteConfig?.source === "archiveSettlements") return rows;
    if (
      initialView.startsWith("finance-internal") &&
      activeRouteConfig?.source !== "paymentPackages"
    )
      rows = rows.filter((row) => row.data?.fee_type === "内部费用");
    if (
      initialView.startsWith("finance-settlement") &&
      activeRouteConfig?.source === "fees"
    )
      rows = rows.filter((row) => row.data?.fee_type === "结算费用");
    if (initialView.startsWith("finance-archive-fee"))
      rows = rows.filter((row) => row.data?.fee_type === "归档费用");
    if (["finance-receipts-claim"].includes(initialView))
      rows = rows.filter((row) => row.status === "待认领");
    if (["finance-receipts-pending"].includes(initialView))
      rows = rows.filter((row) => ["待分配", "部分分配"].includes(row.status));
    if (["finance-receipts-allocated"].includes(initialView))
      rows = rows.filter((row) => row.status === "已分配");
    if (initialView === "finance-invoice-mine") {
      const identities = [currentUser.username, currentUser.displayName].filter(
        Boolean,
      );
      rows = rows.filter((row) =>
        identities.includes(row.data?.applicant || row.owner || ""),
      );
    }
    if (
      [
        "finance-internal-archive",
        "finance-internal-audit",
        "finance-internal-fee-audit",
      ].includes(initialView)
    )
      rows = rows.filter((row) =>
        initialView === "finance-internal-archive"
          ? row.status === "待归档"
          : row.status === "待审批",
      );
    if (initialView === "finance-internal-refund-audit")
      rows = rows.filter((row) => isInternalRefundFee(row));
    if (initialView === "finance-internal-refused")
      rows = rows.filter((row) =>
        ["已拒绝", "已退回", "已驳回"].includes(row.status),
      );
    if (initialView === "finance-internal-void")
      rows = rows.filter((row) => row.status === "已作废");
    if (initialView === "finance-internal-payment")
      rows = rows.filter((row) => row.status === "已审批");
    if (initialView === "finance-internal-writeoff")
      rows = rows.filter((row) => row.status === "待核销");
    const statusByRoute: Record<string, string[]> = {
      "finance-settlement-pending": ["草稿", "待结算"],
      "finance-settlement-audit": ["待审批"],
      "finance-settlement-payment": ["待付款"],
      "finance-settlement-paid": ["已付款"],
      "finance-settlement-refused": ["已拒绝", "已退回", "已驳回"],
      "finance-archive-fee-pending": ["草稿", "待归档"],
      "finance-archive-fee-payment": ["已审批", "待支付", "部分付款"],
      "finance-archive-fee-paid": ["已付款", "已支付"],
      "finance-archive-fee-refused": ["已拒绝", "已退回", "已驳回"],
    };
    if (statusByRoute[initialView])
      rows = rows.filter((row) =>
        statusByRoute[initialView].includes(row.status),
      );
    if (isFeeQueryRoute || isGeneralSettlementRoute || isInternalDetailRoute || isInvoiceMineRoute || isInvoicePendingRoute || isInvoiceCompanyRoute || isInvoiceUnissuedRoute)
      return rows;
    if (!Object.keys(originalQuery).length) return rows;
    return rows.filter((row) =>
      activeRouteConfig.fields.every((spec, index) => {
        const key = spec.key || `routeField${index}`;
        const value = originalQuery[key];
        if (
          value == null ||
          value === "" ||
          ["请选择", "全部"].includes(String(value))
        )
          return true;
        const raw = rawCellValue(row, spec.label);
        if (spec.control === "date") {
          if (!Array.isArray(value) || (!value[0] && !value[1])) return true;
          if (!raw) return false;
          const current = dayjs(String(raw));
          return (
            current.isValid() &&
            (!value[0] || !current.isBefore(value[0], "day")) &&
            (!value[1] || !current.isAfter(value[1], "day"))
          );
        }
        if (spec.control === "money") {
          if (!Array.isArray(value) || (value[0] == null && value[1] == null))
            return true;
          const amount = Number(raw);
          return (
            Number.isFinite(amount) &&
            (value[0] == null || amount >= Number(value[0])) &&
            (value[1] == null || amount <= Number(value[1]))
          );
        }
        if (raw == null) return false;
        return spec.options
          ? String(raw) === String(value)
          : String(raw)
              .toLowerCase()
              .includes(String(value).trim().toLowerCase());
      }),
    );
  }, [
    activeRouteConfig,
    originalFinanceRows,
    incoming,
    generalSettlementRows,
    archiveSettlementRows,
    pendingSettlements,
    paymentPackages,
    refundReviewFees,
    invoices,
    fees,
    initialView,
    originalQuery,
    currentUser,
    internalDetailRows,
    isInternalDetailRoute,
    invoiceMineRows,
    invoicePendingRows,
    invoiceCompanyRows,
    invoiceUnissuedRows,
    isInvoiceMineRoute,
    isInvoicePendingRoute,
    isInvoiceCompanyRoute,
    isInvoiceUnissuedRoute,
    isFeeQueryRoute,
    feeQueryRows,
  ]);
  const submitPaymentQueryQuickPage = () => {
    const pageSize =
      paymentQueryControlledPageSize(initialView, paymentQueryPageSize) ??
      paymentQueryDefaultPageSize(initialView) ??
      15;
    const totalPages =
      initialView === "finance-payment-query"
        ? Math.max(1, Math.ceil(paymentQueryMeta.total / pageSize))
        : Math.max(1, Math.ceil(configuredRows.length / pageSize));
    const result = paymentQueryQuickPageResult(
      paymentQueryQuickPage,
      totalPages,
    );
    if (!result.ok) {
      message.warning(result.message);
      return;
    }
    setPaymentQueryQuickPage(String(result.page));
  };
  const refreshPaymentQueryPage = (page: number, pageSize: number) => {
    setSelectedOriginalRows([]);
    setPaymentQueryPageSize(pageSize);
    void loadPaymentQueryPage(originalQuery, page, pageSize)
      .then(({ data }) => {
        setFees(data.items || []);
        setPaymentQueryMeta({
          total: Number(data.total || 0),
          page: Number(data.page || page),
          pageSize: Number(data.page_size || pageSize),
        });
      })
      .catch(() => message.error(paymentQueryLegacyErrorMessage));
  };
  const feeReviewRows = useMemo(
    () =>
      feeReviewTargets.flatMap((fee) => {
        const details =
          Array.isArray(fee.data?.commission_details) &&
          fee.data.commission_details.length
            ? fee.data.commission_details
            : [{}];
        return details.map((detail: Record<string, any>, index: number) => ({
          key: `${fee.id}-${index}`,
          case_no: detail.case_no ?? fee.data?.case_no,
          commission_type:
            detail.commission_type ??
            detail.type ??
            fee.data?.commission_type ??
            fee.title ??
            fee.data?.fee_type,
          payee:
            detail.payee ??
            detail.payment_target ??
            fee.data?.payee ??
            fee.data?.handler ??
            fee.owner,
          base_amount:
            detail.base_amount ?? fee.data?.commission_base ?? fee.data?.amount,
          base_commission: detail.base_commission ?? fee.data?.base_commission,
          actual_commission:
            detail.actual_commission ??
            fee.data?.actual_commission ??
            fee.data?.amount,
          paid_investigation:
            detail.paid_investigation ?? fee.data?.paid_investigation,
          paid_source: detail.paid_source ?? fee.data?.paid_source,
          paid_document: detail.paid_document ?? fee.data?.paid_document,
          paid_hearing: detail.paid_hearing ?? fee.data?.paid_hearing,
        }));
      }),
    [feeReviewTargets],
  );
  const paymentReviewRows = useMemo(
    () =>
      feeReviewTargets.map((fee) => ({
        key: fee.id,
        case_no: fee.data?.case_no ?? fee.data?.案件编号,
        plaintiff: fee.data?.plaintiff ?? fee.data?.customer_name ?? fee.title,
        amount: fee.data?.amount,
        fee_type: fee.data?.fee_type ?? fee.title,
        payment_remark: fee.data?.remark ?? fee.data?.payment_remark ?? fee.description,
      })),
    [feeReviewTargets],
  );
  const reviewNumber = (value: unknown) =>
    value == null || value === "" || Number.isNaN(Number(value))
      ? "—"
      : Number(value).toFixed(2);
  const submitFeeReview = async (approved: boolean) => {
    if (!feeReviewTargets.length) return;
    setFeeReviewLoading(true);
    try {
      if (feeReviewTargets.every((item) => item.data?._source_module === "contract_payment")) {
        for (const target of feeReviewTargets) {
          await api.post(`/contract-payment-applications/${target.id}/review`, {
            approved,
            comment: feeReviewComment,
          });
        }
      } else if (feeReviewTargets.length === 1) {
        await api.post(`/finance/fees/${feeReviewTargets[0].id}/review`, {
          approved,
          comment: feeReviewComment,
        });
      } else {
        await api.post("/finance/fees/batch-review", {
          fee_ids: feeReviewTargets.map((item) => item.id),
          approved,
          comment: feeReviewComment,
        });
      }
      message.success(approved ? "审批已通过" : "申请已拒绝");
      setFeeReviewTargets([]);
      setFeeReviewComment("");
      setSelectedOriginalRows([]);
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "审批失败");
    } finally {
      setFeeReviewLoading(false);
    }
  };
  const openBatchFeeReview = () => {
    const targets = configuredRows.filter(
      (row) => selectedOriginalRows.includes(row.id) && row.status === "待审批",
    );
    if (!targets.length) {
      if (initialView === "finance-payment-audit") {
        Modal.info({
          title: "提示",
          content: "请选择审批项.",
          okText: "确定",
        });
      } else {
        message.warning("请先选择需要审批的请款单");
      }
      return;
    }
    setFeeReviewTargets(targets);
  };
  const previewInternalPaymentPackage = async () => {
    const targets = configuredRows.filter((row) =>
      selectedOriginalRows.includes(row.id),
    );
    if (!targets.length) {
      Modal.info({
        title: "提示",
        content: paymentPackageEmptySelectionMessage(initialView),
        okText: "确定",
      });
      return;
    }
    const payees = new Set(
      targets.map((row) =>
        String(row.data?.payee || row.data?.applicant || row.owner || "").trim(),
      ),
    );
    if (payees.size !== 1 || payees.has("")) {
      Modal.warning({
        title: "提示",
        content: "请选择同一收款人的提成进行打包付款.",
        okText: "确定",
      });
      return;
    }
    if (!financeActionGates.paymentPackage.tryEnter()) {
      message.info("操作正在提交，请勿重复点击");
      return;
    }
    setPaymentPackageLoading(true);
    try {
      const { data } = await api.post("/finance/payment-packages/preview", {
        fee_ids: targets.map((row) => row.id),
      });
      setPaymentPackagePreview(data);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "付款包预览生成失败");
    } finally {
      financeActionGates.paymentPackage.leave();
      setPaymentPackageLoading(false);
    }
  };
  const submitInternalPaymentPackage = async () => {
    if (!paymentPackagePreview || paymentPackagePreview.submitted) return;
    if (!financeActionGates.paymentPackage.tryEnter()) {
      message.info("操作正在提交，请勿重复点击");
      return;
    }
    setPaymentPackageLoading(true);
    try {
      await api.post("/finance/payment-packages", {
        fee_ids: paymentPackagePreview.items.map((item) => item.fee_id),
        package_no: paymentPackagePreview.package_no,
        comment: "待付款列表打包付款",
      });
      setPaymentPackagePreview({ ...paymentPackagePreview, submitted: true });
      setSelectedOriginalRows([]);
      message.success("付款包已提交，正在打开打印");
      await load();
      window.setTimeout(() => window.print(), 50);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "付款包提交失败");
    } finally {
      financeActionGates.paymentPackage.leave();
      setPaymentPackageLoading(false);
    }
  };
  const configuredDefaults = Object.fromEntries(
    (activeRouteConfig?.fields || [])
      .map((spec, index) => [
        spec.key || `routeField${index}`,
        spec.defaultValue,
      ])
      .filter(([, value]) => value !== undefined),
  );
  const submitConfiguredQuery = () => {
    const next = effectivePaymentQuery(
      initialView,
      { ...configuredDefaults, ...originalQueryDraft },
      feeTypes,
    );
    setOriginalQuery(next);
    setSelectedOriginalRows([]);
    if (initialView === "finance-payment-query") {
      void loadPaymentQueryPage(next, 1, paymentQueryPageSize)
        .then(({ data }) => {
          setFees(data.items || []);
          setPaymentQueryMeta({
            total: Number(data.total || 0),
            page: 1,
            pageSize: Number(data.page_size || paymentQueryPageSize),
          });
        })
        .catch(() => message.error(paymentQueryLegacyErrorMessage));
    }
    if (activeRouteConfig?.source === "paymentPackages") {
      void loadPaymentPackages(next, 1, paymentPackageMeta.pageSize).catch(
        () => message.error("付款包查询失败"),
      );
    }
    if (isFeeQueryRoute) {
      void loadFeeQuery(next, 1, feeQueryMeta.pageSize).catch((error: any) =>
        message.error(error?.response?.data?.detail || "费用查询失败"),
      );
    }
    if (isInternalDetailRoute) {
      void loadInternalDetails(next, 1, internalDetailMeta.pageSize).catch(
        (error: any) =>
          message.error(
            error?.response?.data?.detail || "内部费用明细查询失败",
          ),
      );
    }
    if (isInvoiceMineRoute) {
      void loadInvoiceMine(next, 1, invoiceMineMeta.pageSize).catch(
        (error: any) =>
          message.error(error?.response?.data?.detail || "我的开票查询失败"),
      );
    }
    if (isInvoicePendingRoute) {
      void loadInvoicePending(next, 1, invoicePendingMeta.pageSize).catch(
        (error: any) =>
          message.error(error?.response?.data?.detail || "待处理开票查询失败"),
      );
    }
    if (isInvoiceCompanyRoute) {
      void loadInvoiceCompany(next, 1, invoiceCompanyMeta.pageSize).catch(
        (error: any) =>
          message.error(error?.response?.data?.detail || "公司开票查询失败"),
      );
    }
    if (isInvoiceUnissuedRoute) {
      void loadInvoiceUnissued(next, 1, invoiceUnissuedMeta.pageSize).catch(
        (error: any) =>
          message.error(error?.response?.data?.detail || "未开票查询失败"),
      );
    }
    if (isGeneralSettlementRoute) {
      void loadGeneralSettlements(
        next,
        1,
        generalSettlementMeta.pageSize,
      ).catch((error: any) =>
        message.error(
          error?.response?.data?.detail || "待结算查询失败",
        ),
      );
    }
    if (isArchiveSettlementActiveRoute) {
      void loadArchiveSettlements(
        next,
        1,
        archiveSettlementMeta.pageSize,
      ).catch((error: any) =>
        message.error(
          error?.response?.data?.detail ||
            (isArchiveSettlementRejectedRoute
              ? "已拒绝查询失败"
              : isArchiveSettlementPaymentRoute
                ? "待支付查询失败"
                : "待归档查询失败"),
        ),
      );
    }
  };
  const clearConfiguredQuery = () => {
    if (initialView === "finance-payment-query") {
      setOriginalQueryDraft({});
      setOriginalQuery({});
      setSelectedOriginalRows([]);
      void loadPaymentQueryPage({}, 1, paymentQueryPageSize)
        .then(({ data }) => {
          setFees(data.items || []);
          setPaymentQueryMeta({
            total: Number(data.total || 0),
            page: 1,
            pageSize: Number(data.page_size || paymentQueryPageSize),
          });
        })
        .catch(() => message.error(paymentQueryLegacyErrorMessage));
      return;
    }
    if (activeRouteConfig?.source === "paymentPackages") {
      const next =
        initialView === "finance-internal-writeoff"
          ? { status: "待核销" }
          : {};
      setOriginalQueryDraft(next);
      setOriginalQuery(next);
      setSelectedOriginalRows([]);
      void loadPaymentPackages(next, 1, paymentPackageMeta.pageSize).catch(
        () => message.error("付款包查询清空失败"),
      );
      return;
    }
    if (isFeeQueryRoute) {
      const next = preserveDashboardFeeQueryContext(originalQuery);
      setOriginalQueryDraft(next);
      setOriginalQuery(next);
      setSelectedOriginalRows([]);
      void loadFeeQuery(next, 1, feeQueryMeta.pageSize).catch((error: any) =>
        message.error(error?.response?.data?.detail || "费用查询清空失败"),
      );
      return;
    }
    if (isGeneralSettlementRoute) {
      setOriginalQueryDraft({});
      setOriginalQuery({});
      setSelectedOriginalRows([]);
      setGeneralSettlementDetails([]);
      void loadGeneralSettlements({}, 1, generalSettlementMeta.pageSize).catch(
        () => message.error(settlementLegacyErrorMessage),
      );
      return;
    }
    if (isArchiveSettlementActiveRoute) {
      setOriginalQueryDraft({});
      setOriginalQuery({});
      setSelectedOriginalRows([]);
      void loadArchiveSettlements({}, 1, archiveSettlementMeta.pageSize).catch(
        () => message.error(settlementLegacyErrorMessage),
      );
      return;
    }
    if (isInvoiceMineRoute) {
      setOriginalQueryDraft({});
      setOriginalQuery({});
      setSelectedOriginalRows([]);
      void loadInvoiceMine({}, 1, invoiceMineMeta.pageSize).catch(() =>
        message.error(invoiceLegacyErrorMessage),
      );
      return;
    }
    if (isInvoicePendingRoute) {
      setOriginalQueryDraft({});
      setOriginalQuery({});
      setSelectedOriginalRows([]);
      void loadInvoicePending({}, 1, invoicePendingMeta.pageSize).catch(() =>
        message.error(invoiceLegacyErrorMessage),
      );
      return;
    }
    if (isInvoiceCompanyRoute) {
      setOriginalQueryDraft({});
      setOriginalQuery({});
      setSelectedOriginalRows([]);
      void loadInvoiceCompany({}, 1, invoiceCompanyMeta.pageSize).catch(() =>
        message.error(invoiceLegacyErrorMessage),
      );
      return;
    }
    if (isInvoiceUnissuedRoute) {
      const next = {
        routeField6: "未开票",
        routeField12: ["律师代理费"],
      };
      setOriginalQueryDraft(next);
      setOriginalQuery(next);
      setSelectedOriginalRows([]);
      void loadInvoiceUnissued(next, 1, invoiceUnissuedMeta.pageSize).catch(
        (error: any) =>
          message.error(error?.response?.data?.detail || invoiceLegacyErrorMessage),
      );
      return;
    }
    if (isInternalDetailRoute) {
      const next = {
        ...originalQueryDraft,
        routeField0: "",
        routeField4: "",
        routeField10: [],
        routeField11: [],
        ...(initialView === "finance-internal-detail"
          ? {
              routeField9:
                currentUser.displayName || "姓名待维护",
            }
          : {}),
      };
      setOriginalQueryDraft(next);
      setOriginalQuery(next);
      setSelectedOriginalRows([]);
      void loadInternalDetails(next, 1, internalDetailMeta.pageSize).catch(
        (error: any) =>
          message.error(
            error?.response?.data?.detail || "内部费用明细清空失败",
          ),
      );
      return;
    }
    const next = paymentWriteoffClearQuery(initialView);
    setOriginalQueryDraft(next);
    setOriginalQuery(next);
  };
  const exportFeeQuery = async (selectedOnly: boolean) => {
    if (selectedOnly && !selectedOriginalRows.length) {
      Modal.info({
        title: "提示",
        content: "请选择需要导出的费用.",
        okText: "确定",
      });
      return;
    }
    setFeeQueryExportLoading(true);
    try {
      const response = await api.get(
        isRefundCaseFeeRoute
          ? "/finance/case-fees/refunds/export"
          : "/finance/fees/query/export", {
        params: {
          ...feeQueryParams(originalQuery, 1, feeQueryMeta.pageSize),
          page: undefined,
          page_size: undefined,
          selected_only: selectedOnly,
          ids: selectedOnly ? selectedOriginalRows.join(",") : undefined,
        },
        responseType: "blob",
        },
      );
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${isRefundCaseFeeRoute ? "退费查询" : "费用查询"}-${dayjs().format("YYYY-MM-DD")}.xls`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (error: any) {
      message.error(
        error?.response?.data?.detail ||
          (isRefundCaseFeeRoute ? "退费查询导出失败" : "费用查询导出失败"),
      );
    } finally {
      setFeeQueryExportLoading(false);
    }
  };
  const selectedRefundCaseFeeIds = () =>
    selectedOriginalRows.map(Number).filter((value) => Number.isInteger(value));
  const requireRefundCaseFeeSelection = () => {
    const ids = selectedRefundCaseFeeIds();
    if (!ids.length) message.warning("请选择需要操作的退费记录");
    return ids;
  };
  const submitRefundCaseFeeStatus = async (forcedStatus?: string) => {
    const ids = requireRefundCaseFeeSelection();
    if (!ids.length) return;
    const status = forcedStatus || refundCaseFeeStatus;
    setRefundCaseFeeMutationLoading(true);
    try {
      await api.post("/finance/case-fees/refunds/status", {
        ids,
        status,
        comment: status === "R100" ? "标记不再办理退费" : "退费查询批量修改进度",
      });
      message.success(status === "R100" ? "已标记不再办理退费" : "退费进度已修改");
      setRefundCaseFeeStatusOpen(false);
      setSelectedOriginalRows([]);
      await loadFeeQuery(originalQuery, feeQueryMeta.page, feeQueryMeta.pageSize);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "退费操作失败");
    } finally {
      setRefundCaseFeeMutationLoading(false);
    }
  };
  const submitRefundCaseFeeLog = async () => {
    const ids = requireRefundCaseFeeSelection();
    if (!ids.length || !refundCaseFeeLogKind) return;
    if (refundCaseFeeLogContent.trim().length < 2) {
      message.warning("请输入至少 2 个字的日志内容");
      return;
    }
    setRefundCaseFeeMutationLoading(true);
    try {
      await api.post("/finance/case-fees/refunds/logs", {
        ids,
        kind: refundCaseFeeLogKind,
        content: refundCaseFeeLogContent.trim(),
      });
      message.success("退费日志已保存");
      setRefundCaseFeeLogKind(null);
      setRefundCaseFeeLogContent("");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "退费日志保存失败");
    } finally {
      setRefundCaseFeeMutationLoading(false);
    }
  };
  const exportInternalDetails = async (selectedOnly: boolean) => {
    if (selectedOnly && !selectedOriginalRows.length) {
      message.warning("请选择需要导出的费用.");
      return;
    }
    setInternalDetailExportLoading(true);
    try {
      const params: Record<string, any> = {
        ...internalDetailParams(originalQuery, 1, 15),
      };
      delete params.page;
      delete params.page_size;
      if (selectedOnly) params.ids = selectedOriginalRows.join(",");
      const response = await api.get("/finance/internal-fees/export", {
        params,
        responseType: "blob",
      });
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `内部费用明细-${dayjs().format("YYYY-MM-DD")}.xls`;
      anchor.click();
      URL.revokeObjectURL(url);
      message.success("导出成功.");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "导出失败");
    } finally {
      setInternalDetailExportLoading(false);
    }
  };
  const exportInvoiceList = async (selectedOnly: boolean) => {
    if (selectedOnly && !selectedOriginalRows.length) {
      Modal.info({
        title: "提示",
        content: "请选择需要导出的发票.",
        okText: "确定",
      });
      return;
    }
    setInvoiceExportLoading(true);
    try {
      const params: Record<string, any> = {
        ...(isInvoicePendingRoute
          ? invoicePendingParams(originalQuery, 1, 15)
          : isInvoiceCompanyRoute
            ? invoiceCompanyParams(originalQuery, 1, 15)
            : invoiceMineParams(originalQuery, 1, 15)),
      };
      delete params.page;
      delete params.page_size;
      if (selectedOnly) params.ids = selectedOriginalRows.join(",");
      const response = await api.get("/finance/invoices/export", {
        params,
        responseType: "blob",
      });
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${isInvoicePendingRoute ? "待处理开票" : isInvoiceCompanyRoute ? "公司开票" : "我的开票"}-${dayjs().format("YYYY-MM-DD")}.xls`;
      anchor.click();
      URL.revokeObjectURL(url);
      message.success("导出成功.");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "导出失败");
    } finally {
      setInvoiceExportLoading(false);
    }
  };
  const exportInvoiceUnissued = async (selectedOnly: boolean) => {
    if (selectedOnly && !selectedOriginalRows.length) {
      Modal.info({
        title: "提示",
        content: "请选择需要导出的费用.",
        okText: "确定",
      });
      return;
    }
    setInvoiceExportLoading(true);
    try {
      const params: Record<string, any> = {
        ...invoiceUnissuedParams(originalQuery, 1, 15),
      };
      delete params.page;
      delete params.page_size;
      if (selectedOnly) params.ids = selectedOriginalRows.join(",");
      const response = await api.get(
        "/finance/case-fees/invoice-status/export",
        { params, responseType: "blob" },
      );
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${initialView === "finance-invoice-company-unissued" ? "公司未开票" : "未开票"}-${dayjs().format("YYYY-MM-DD")}.xls`;
      anchor.click();
      URL.revokeObjectURL(url);
      message.success("导出成功.");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "导出失败");
    } finally {
      setInvoiceExportLoading(false);
    }
  };
  const exportGeneralSettlement = async (
    kind: "settlement" | "receipt" | "case",
    ids?: (string | number)[],
  ) => {
    const selectedOnly = ids !== undefined;
    const selectedIds = ids ?? selectedOriginalRows;
    if (!isGeneralSettlementPendingRoute && !selectedOnly) {
      Modal.info({
        title: "提示",
        content: "请选择需要导出的结算申请.",
        okText: "确定",
      });
      return;
    }
    if (selectedOnly && !selectedIds.length) {
      Modal.info({
        title: "提示",
        content: "请选择需要导出的回款.",
        okText: "确定",
      });
      return;
    }
    setGeneralSettlementBusy(true);
    try {
      const response = await api.get("/finance/general-settlements/export", {
        params: selectedOnly
          ? isGeneralSettlementPendingRoute
            ? { kind, ids: selectedIds.join(",") }
            : { kind, application_ids: selectedIds.join(",") }
          : { kind },
        responseType: "blob",
      });
      const names = {
        settlement: "结算清单",
        receipt: "到账清单",
        case: "案件清单",
      };
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${names[kind]}-${dayjs().format("YYYY-MM-DD")}.xls`;
      anchor.click();
      URL.revokeObjectURL(url);
      message.success("导出成功.");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "导出失败");
    } finally {
      setGeneralSettlementBusy(false);
    }
  };
  const exportPendingArchiveSettlements = async () => {
    if (!selectedOriginalRows.length) {
      Modal.info({
        title: "提示",
        content: isArchiveSettlementRejectedRoute
          ? "请选择案件."
          : "请选择需要导出的归档费.",
        okText: "确定",
      });
      return;
    }
    if (!financeActionGates.archiveSettlement.tryEnter()) {
      message.info("操作正在提交，请勿重复点击");
      return;
    }
    setArchiveSettlementBusy(true);
    try {
      const response = await api.get(
        isArchiveSettlementPaidRoute
          ? "/finance/archive-settlements/paid/export"
          : isArchiveSettlementRejectedRoute
            ? "/finance/archive-settlements/rejected/export"
          : isArchiveSettlementPaymentRoute
            ? "/finance/archive-settlements/payment/export"
            : "/finance/archive-settlements/export",
        {
        params: { ids: selectedOriginalRows.join(",") },
        responseType: "blob",
        },
      );
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${
        isArchiveSettlementPaidRoute
          ? "已支付归档费"
          : isArchiveSettlementRejectedRoute
            ? "已拒绝归档费"
          : isArchiveSettlementPaymentRoute
            ? "待支付归档费"
            : "待归档"
      }-${dayjs().format("YYYY-MM-DD")}.xls`;
      anchor.click();
      URL.revokeObjectURL(url);
      message.success("导出成功.");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "导出失败");
    } finally {
      financeActionGates.archiveSettlement.leave();
      setArchiveSettlementBusy(false);
    }
  };
  const openArchiveSettlementReview = (targets: any[], approved: boolean) => {
    if (!targets.length) {
      Modal.info({
        title: "提示",
        content: "请选择归档费.",
        okText: "确定",
      });
      return;
    }
    setArchiveSettlementReviewApproved(approved);
    setArchiveSettlementReviewComment("");
    setArchiveSettlementReviewTargets(targets);
  };
  const submitArchiveSettlementReview = async () => {
    if (!archiveSettlementReviewTargets.length) return;
    if (!archiveSettlementReviewApproved && !archiveSettlementReviewComment.trim()) {
      message.warning("请输入备注.");
      return;
    }
    if (!financeActionGates.archiveSettlement.tryEnter()) {
      message.info("操作正在提交，请勿重复点击");
      return;
    }
    setArchiveSettlementBusy(true);
    try {
      const response = await api.post(
        "/finance/archive-settlements/payment/review",
        {
          settlement_ids: archiveSettlementReviewTargets.map((row) => String(row.id)),
          approved: archiveSettlementReviewApproved,
          comment: archiveSettlementReviewComment,
        },
      );
      message.success(
        archiveSettlementReviewApproved
          ? `同意结算 ${response.data.reviewed} 条归档费`
          : `拒绝结算 ${response.data.reviewed} 条归档费`,
      );
      setArchiveSettlementReviewTargets([]);
      setArchiveSettlementReviewComment("");
      setSelectedOriginalRows([]);
      await loadArchiveSettlements(
        originalQuery,
        archiveSettlementMeta.page,
        archiveSettlementMeta.pageSize,
      );
    } catch (error: any) {
      message.error(
        error?.response?.data?.detail ||
          (archiveSettlementReviewApproved
            ? "标识已结算出错."
            : "拒绝结算出错."),
      );
    } finally {
      financeActionGates.archiveSettlement.leave();
      setArchiveSettlementBusy(false);
    }
  };
  const openArchiveSettlementRollback = (targets: any[]) => {
    if (!targets.length) {
      Modal.info({
        title: "提示",
        content: "请选择归档费.",
        okText: "确定",
      });
      return;
    }
    setArchiveSettlementRollbackComment("");
    setArchiveSettlementRollbackTargets(targets);
  };
  const submitArchiveSettlementRollback = async () => {
    if (!archiveSettlementRollbackTargets.length) return;
    if (!archiveSettlementRollbackComment.trim()) {
      message.warning(
        isArchiveSettlementRejectedRoute ? "请输入审核备注." : "请输入备注.",
      );
      return;
    }
    if (!financeActionGates.archiveSettlement.tryEnter()) {
      message.info("操作正在提交，请勿重复点击");
      return;
    }
    setArchiveSettlementBusy(true);
    try {
      const response = await api.post(
        isArchiveSettlementRejectedRoute
          ? "/finance/archive-settlements/rejected/rollback"
          : "/finance/archive-settlements/paid/rollback",
        {
          record_ids: archiveSettlementRollbackTargets.map((row) => Number(row.id)),
          comment: archiveSettlementRollbackComment.trim(),
        },
      );
      message.success(
        isArchiveSettlementRejectedRoute
          ? `已恢复 ${response.data.rolled_back} 条已拒绝归档费`
          : `已回滚 ${response.data.rolled_back} 条归档费结算`,
      );
      setArchiveSettlementRollbackTargets([]);
      setArchiveSettlementRollbackComment("");
      setSelectedOriginalRows([]);
      await loadArchiveSettlements(
        originalQuery,
        archiveSettlementMeta.page,
        archiveSettlementMeta.pageSize,
      );
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "归档费回滚出错.");
    } finally {
      financeActionGates.archiveSettlement.leave();
      setArchiveSettlementBusy(false);
    }
  };
  const openArchiveSettlementReapply = (targets: any[]) => {
    if (!targets.length) {
      Modal.info({
        title: "提示",
        content: "请选择归档费.",
        okText: "确定",
      });
      return;
    }
    setArchiveSettlementReapplyComment("");
    setArchiveSettlementReapplyTargets(targets);
  };
  const submitArchiveSettlementReapply = async () => {
    if (!archiveSettlementReapplyTargets.length) return;
    if (!financeActionGates.archiveSettlement.tryEnter()) {
      message.info("操作正在提交，请勿重复点击");
      return;
    }
    setArchiveSettlementBusy(true);
    try {
      const response = await api.post(
        "/finance/archive-settlements/rejected/reapply",
        {
          record_ids: archiveSettlementReapplyTargets.map((row) => Number(row.id)),
          comment: archiveSettlementReapplyComment.trim(),
        },
      );
      message.success(`已重新申请 ${response.data.reapplied} 条归档费`);
      setArchiveSettlementReapplyTargets([]);
      setArchiveSettlementReapplyComment("");
      setSelectedOriginalRows([]);
      await loadArchiveSettlements(
        originalQuery,
        archiveSettlementMeta.page,
        archiveSettlementMeta.pageSize,
      );
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "归档费重新申请失败");
    } finally {
      financeActionGates.archiveSettlement.leave();
      setArchiveSettlementBusy(false);
    }
  };
  const applyGeneralSettlementRows = (ids?: (string | number)[]) => {
    const selectedIds = ids ?? selectedOriginalRows;
    if (!selectedIds.length) {
      Modal.info({
        title: "提示",
        content: "请选择需要申请结算的回款.",
        okText: "确定",
      });
      return;
    }
    setGeneralSettlementApplyComment("");
    setGeneralSettlementApplyTargets([...selectedIds]);
  };
  const submitGeneralSettlementApply = async () => {
    if (!generalSettlementApplyTargets.length) return;
    setGeneralSettlementBusy(true);
    try {
      const response = await api.post(
        "/finance/general-settlements/apply",
        {
          receipt_ids: generalSettlementApplyTargets.map(Number),
          comment: generalSettlementApplyComment,
        },
      );
      message.success(`已生成 ${response.data.created} 条结算申请`);
      setGeneralSettlementApplyTargets([]);
      setGeneralSettlementApplyComment("");
      setSelectedOriginalRows([]);
      setGeneralSettlementDetails([]);
      await loadGeneralSettlements(
        originalQuery,
        1,
        generalSettlementMeta.pageSize,
      );
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "申请结算失败");
      throw error;
    } finally {
      setGeneralSettlementBusy(false);
    }
  };
  const exportConfiguredRows = async (selectedOnly: boolean) => {
    if (!activeRouteConfig) return;
    if (
      activeRouteConfig.source === "fees" &&
      initialView.startsWith("finance-internal") &&
      !isInternalDetailRoute
    ) {
      if (selectedOnly && !selectedOriginalRows.length) {
        message.warning("请先选择需要导出的费用");
        return;
      }
      try {
        const response = await api.get("/finance/internal-fees/export", {
          params: internalFeeExportRequestParams({
            scope: initialView === "finance-internal-mine" ? "mine" : "company",
            query: originalQuery,
            ids: selectedOnly ? selectedOriginalRows.map(Number) : [],
            initialView,
          }),
          responseType: "blob",
        });
        const url = URL.createObjectURL(response.data);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = `${displayedOriginalTitle}-${dayjs().format("YYYY-MM-DD")}.xls`;
        anchor.click();
        URL.revokeObjectURL(url);
      } catch (error: any) {
        message.error(error?.response?.data?.detail || "内部费用导出失败");
      }
      return;
    }
    const rows = selectedOnly
      ? configuredRows.filter((row) => selectedOriginalRows.includes(row.id))
      : configuredRows;
    if (!rows.length) {
      message.warning(
        selectedOnly ? "请先选择需要导出的记录" : "当前没有可导出的记录",
      );
      return;
    }
    const headers = activeRouteConfig.headers.filter(
      (header) => header !== "操作",
    );
    const escapeCsv = (value: unknown) =>
      `"${String(value ?? "").replaceAll('"', '""')}"`;
    const csv = [
      headers.map(escapeCsv).join(","),
      ...rows.map((row) =>
        headers.map((header) => escapeCsv(cellValue(row, header))).join(","),
      ),
    ].join("\r\n");
    const url = URL.createObjectURL(
      new Blob(["\ufeff", csv], { type: "text/csv;charset=utf-8" }),
    );
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${displayedOriginalTitle}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  };
  const exportRefunds = async (selectedOnly: boolean) => {
    if (selectedOnly && !selectedRefundRows.length) {
      message.warning("请先选择需要导出的退款记录");
      return;
    }
    const exportParams = selectedOnly
      ? isRefundNotRequiredRoute
        ? refundSelectedExportRequestParams(
            selectedRefundRows,
            activeRefundStatus,
            refundGroupFilter,
          )
        : refundSelectedExportRequestParams(
            selectedRefundRows,
            refundStatusFilter,
            refundGroupFilter,
          )
      : isRefundNotRequiredRoute
        ? refundExportRequestParams(activeRefundStatus, refundGroupFilter)
        : refundExportRequestParams(refundStatusFilter, refundGroupFilter);
    try {
      const response = await api.get(
        selectedOnly
          ? "/finance/refunds/export-selected"
          : "/finance/refunds/export",
        {
          params: exportParams,
          responseType: "blob",
        },
      );
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `诉讼费退款-${selectedOnly ? "选中" : "全部"}-${dayjs().format("YYYY-MM-DD")}.xls`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (error: any) {
      message.error(
        error?.response?.data?.detail ||
          (selectedOnly ? "退款选中导出失败" : "退款全量导出失败"),
      );
    }
  };
  const selectedSettlementRows = configuredRows.filter((row) =>
    selectedOriginalRows.includes(row.id),
  );
  const markCommissionPaid = () => {
    if (!selectedSettlementRows.length) {
      Modal.info({
        title: "提示",
        content: "请选择案件费用。",
        okText: "确定",
      });
      return;
    }
    Modal.confirm({
      title: "标识提成已发",
      content: `确认将已选 ${selectedSettlementRows.length} 条案件费用标识为提成已发？`,
      okText: "确定",
      cancelText: "取消",
      onOk: async () => {
        try {
          const { data } = await api.post(
            "/finance/settlements/mark-commission-paid",
            {
              fee_ids: selectedSettlementRows.map((row) => row.id),
              comment: "待结算列表批量标识",
            },
          );
          message.success(`已标识 ${data.marked} 条案件费用`);
          setSelectedOriginalRows([]);
          await load();
        } catch (error: any) {
          message.error(error?.response?.data?.detail || "标识失败");
        }
      },
    });
  };
  const selectedSettlementCases = () => {
    if (!selectedSettlementRows.length) {
      message.warning(isInvoiceUnissuedRoute ? "请选择案件." : "请先选择案件费用");
      return [];
    }
    const linked = selectedSettlementRows.map((selected) => {
      const caseId = Number(selected.data?.case_id || 0);
      const caseNo = String(selected.data?.case_no || "");
      return cases.find((row) => row.id === caseId || row.serial_no === caseNo);
    });
    if (linked.some((row) => !row)) {
      message.warning("部分费用未关联可操作的案件");
      return [];
    }
    return Array.from(
      new Map((linked as Fee[]).map((row) => [row.id, row])).values(),
    );
  };
  const selectedSettlementCase = () => {
    const linked = selectedSettlementCases();
    if (linked.length !== 1) {
      if (linked.length > 1) message.warning("该操作每次只能选择一个案件");
      return null;
    }
    return linked[0];
  };
  const loadSettlementContextTasks = async (caseId: number) => {
    const firstRequest = settlementContextTasksRequest(caseId, 1);
    const firstResponse = await api.get(firstRequest.url, {
      params: firstRequest.params,
    });
    const firstRows = normalizeSettlementContextRows(firstResponse.data);
    const total = Number(firstResponse.data?.total || firstRows.length);
    const totalPages = Math.max(
      1,
      Math.ceil(total / settlementContextPageSize),
    );
    if (totalPages === 1) return firstRows;
    const restResponses = await Promise.all(
      Array.from({ length: totalPages - 1 }, (_value, index) => {
        const request = settlementContextTasksRequest(caseId, index + 2);
        return api.get(request.url, { params: request.params });
      }),
    );
    return [
      ...firstRows,
      ...restResponses.flatMap((response) =>
        normalizeSettlementContextRows(response.data),
      ),
    ];
  };
  const openSettlementContext = async (mode: "tasks" | "logs" | "log-create" | "task-create") => {
    const linked = selectedSettlementCases();
    if (!linked.length) return;
    if (mode === "log-create") {
      setSettlementLogContent("");
      setSettlementContext({ mode, caseRecords: linked });
      return;
    }
    if (mode === "task-create") {
      const firstAssistant = linked[0]?.data?.assistant || currentUser.username;
      setSettlementTaskForm({
        title: "",
        owner: firstAssistant,
        deadline: dayjs().add(15, "day"),
        priority: "普通",
      });
      setSettlementContext({ mode, caseRecords: linked });
      return;
    }
    setSettlementActionLoading(true);
    try {
      if (mode === "tasks") {
        const groups = await Promise.all(linked.map(async (item) =>
          (await loadSettlementContextTasks(item.id)).map((row: any) => ({ ...row, source_case_no: item.serial_no })),
        ));
        setSettlementContextRows(groups.flat());
      } else {
        const groups = await Promise.all(linked.map(async (item) => {
          const { data } = await api.get(`/cases/${item.id}/logs`);
          return (data.items || []).map((row: any) => ({ ...row, source_case_no: item.serial_no }));
        }));
        setSettlementContextRows(groups.flat());
      }
      setSettlementContext({ mode, caseRecords: linked });
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "案件信息加载失败");
    } finally {
      setSettlementActionLoading(false);
    }
  };
  const submitSettlementLog = async () => {
    const content = settlementLogContent.trim();
    if (!content) {
      message.warning("请输入日志内容");
      return;
    }
    const linked = settlementContext?.caseRecords || [];
    setSettlementActionLoading(true);
    try {
      await Promise.all(linked.map((item) =>
        api.post(`/cases/${item.id}/logs`, { content }),
      ));
      message.success(`已为 ${linked.length} 个案件添加日志`);
      setSettlementContext(null);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "日志添加失败");
    } finally {
      setSettlementActionLoading(false);
    }
  };
  const submitSettlementTask = async () => {
    const form = settlementTaskForm;
    if (!form.title.trim()) {
      message.warning("请输入任务名称");
      return;
    }
    if (!form.owner.trim()) {
      message.warning("请选择负责人");
      return;
    }
    if (!form.deadline) {
      message.warning("请选择截止日期");
      return;
    }
    const linked = settlementContext?.caseRecords || [];
    setSettlementActionLoading(true);
    try {
      await Promise.all(linked.map((item) =>
        api.post("/tasks", {
          title: form.title.trim(),
          owner: form.owner.trim(),
          deadline: form.deadline.format("YYYY-MM-DD"),
          priority: form.priority,
          source: "案件任务",
          case_record_id: item.id,
          case_module: "case",
        }),
      ));
      message.success(`已为 ${linked.length} 个案件创建任务`);
      setSettlementContext(null);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "任务创建失败");
    } finally {
      setSettlementActionLoading(false);
    }
  };
  const generateSettlementDocument = async (
    key: "authorization" | "law-firm-letter" | "identity" | "settlement",
  ) => {
    const linked = selectedSettlementCases();
    if (!linked.length) return;
    const nameMap: Record<string, string> = {
      authorization: "授权委托书",
      "law-firm-letter": "律所函",
      identity: "身份证明",
      settlement: "结算提成表",
    };
    setSettlementActionLoading(true);
    try {
      for (const caseRecord of linked) {
        const response = await api.get(
          `/cases/${caseRecord.id}/documents/generate`,
          { params: { doc_type: key }, responseType: "blob" },
        );
        const url = URL.createObjectURL(response.data);
        const anchor = document.createElement("a");
        anchor.href = url;
        const cd = response.headers["content-disposition"];
        const match = cd && cd.match(/filename\*=UTF-8''([^;]+)/);
        anchor.download = match ? decodeURIComponent(match[1]) : `${nameMap[key]}-${caseRecord.serial_no}.docx`;
        anchor.click();
        URL.revokeObjectURL(url);
      }
      message.success(`${nameMap[key]}已为 ${linked.length} 个案件生成并下载`);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "文书生成失败");
    } finally {
      setSettlementActionLoading(false);
    }
  };
  const openSettlementBatch = () => {
    const linked = selectedSettlementCases();
    if (!linked.length) return;
    settlementBatchForm.resetFields();
    setSettlementBatchOpen(true);
  };
  const submitSettlementBatch = async () => {
    const linked = selectedSettlementCases();
    if (!linked.length) return;
    const values = await settlementBatchForm.validateFields();
    const body: Record<string, any> = {
      case_ids: linked.map((row) => row.id),
      comment: values.comment || "待结算列表批量修改",
    };
    if (values.hearing_lawyer?.trim()) body.hearing_lawyer = values.hearing_lawyer.trim();
    if (values.handling_lawyers?.trim()) {
      body.handling_lawyers = values.handling_lawyers
        .split(/[，,]/)
        .map((item: string) => item.trim())
        .filter(Boolean);
    }
    if (values.assistant?.trim()) body.assistant = values.assistant.trim();
    if (values.source_lawyer?.trim()) body.source_lawyer = values.source_lawyer.trim();
    if (values.case_stage) body.case_stage = values.case_stage;
    if (values.litigation_amount != null) body.litigation_amount = values.litigation_amount;
    if (Object.keys(body).length <= 2) {
      message.warning("请至少修改一个字段");
      return;
    }
    setSettlementActionLoading(true);
    try {
      const { data } = await api.post("/cases/batch-update", body);
      message.success(`已修改 ${data.updated} 个案件`);
      setSettlementBatchOpen(false);
      setSelectedOriginalRows([]);
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "批量修改失败");
    } finally {
      setSettlementActionLoading(false);
    }
  };
  const openRefundBatchFee = (feeType: string) => {
    const linked = selectedSettlementCases();
    if (!linked.length) return;
    const internal = feeType === "内部费用";
    setRefundBatchFeeKind(internal ? "internal" : "ordinary");
    setRefundBatchFeeBaseType(feeType);
    if (!internal) {
      void api.get("/finance/payment-types").then(({ data }) => {
        setRefundBatchPaymentTypes(data.items || []);
      }).catch((error: any) => message.error(error?.response?.data?.detail || "收款单位加载失败"));
    }
    void api.get("/system/parameters/options", { params: { category: "fee_type" } }).then(({ data }) => {
      const items = (data.items || []).filter((item: any) => item.selectable && item.base_fee_type === feeType);
      setRefundBatchFeeSubTypes(items);
    }).catch(() => {
      setRefundBatchFeeSubTypes([]);
    });
    const deadline = dayjs().add(5, "day");
    refundBatchFeeForm.setFieldsValue({
      handler: currentUser.username,
      items: linked.map((item) => ({
        case_id: item.id,
        case_no: item.serial_no,
        customer: item.customer,
        contract_record_id: Number(item.data?.contract_record_id || item.data?.contract_id || 0) || undefined,
        fee_type: feeType,
        fee_type_id: undefined,
        fee_type_name: "",
        amount: undefined,
        payment_amount: undefined,
        payment_type_id: undefined,
        payment_remark: "",
        payee_username: undefined,
        base_amount: undefined,
        reference_commission: undefined,
        remark: "",
        deadline,
      })),
    });
    setRefundBatchFeeStep(0);
    setRefundBatchFeeOpen(true);
  };
  const closeRefundBatchFee = () => {
    setRefundBatchFeeOpen(false);
    setRefundBatchFeeStep(0);
    refundBatchFeeForm.resetFields();
  };
  const syncFirstRefundFeeField = (field: string) => {
    const items = refundBatchFeeForm.getFieldValue("items") || [];
    if (items.length < 2) return;
    const first = items[0] || {};
    const value = first[field];
    if (value === undefined || value === null || value === "") return;
    refundBatchFeeForm.setFieldValue(
      "items",
      items.map((item: Record<string, any>, index: number) =>
        index === 0 ? item : { ...item, [field]: value },
      ),
    );
  };
  const submitRefundBatchFee = async () => {
    const values = await refundBatchFeeForm.validateFields();
    setRefundBatchFeeLoading(true);
    try {
      const { data } = await api.post("/finance/case-fees/batch", {
        handler: values.handler,
        submit_payment: refundBatchFeeBaseType !== "代理费",
        items: values.items.map((item: Record<string, any>) => ({
          case_id: item.case_id,
          contract_record_id: item.contract_record_id || null,
          fee_type_id: item.fee_type_id || null,
          fee_type: item.fee_type,
          amount: item.amount,
          remark: item.remark || "",
          deadline: item.deadline ? formatRequiredDate(item.deadline, "截止日期") : null,
          payment_type_id: item.payment_type_id || null,
          payment_amount: item.payment_amount || Math.abs(Number(item.amount || 0)),
          payment_remark: item.payment_remark || "",
          payee_username: item.payee_username || "",
          base_amount: item.base_amount || 0,
          reference_commission: item.reference_commission || 0,
        })),
      });
      message.success(`已创建 ${data.created} 条案件费用${refundBatchFeeBaseType === "代理费" ? "" : "并提交付款申请"}`);
      closeRefundBatchFee();
      setSelectedOriginalRows([]);
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "批量新增费用失败");
    } finally {
      setRefundBatchFeeLoading(false);
    }
  };
  const runSettlementMoreAction = (key: string) => {
    const feeTypeByKey: Record<string, string> = {
      "official-fee": "官方费用",
      "agency-fee": "代理费",
      "other-fee": "其他费用",
      "internal-fee": "内部费用",
    };
    if (feeTypeByKey[key]) {
      openRefundBatchFee(feeTypeByKey[key]);
      return;
    }
    if (key === "upload") {
      const linked = selectedSettlementCases();
      if (linked.length) void openRecordFiles(linked[0], "普通附件", linked);
    }
    if (key === "batch-modify") openSettlementBatch();
    if (
      ["authorization", "law-firm-letter", "identity", "settlement"].includes(
        key,
      )
    )
      void generateSettlementDocument(
        key as "authorization" | "law-firm-letter" | "identity" | "settlement",
      );
    if (key === "tasks") void openSettlementContext("task-create");
    if (key === "logs") void openSettlementContext("log-create");
  };
  const originalFields = activeRouteConfig
    ? activeRouteConfig.fields.map(configuredField)
    : originalKind === "internal"
      ? internalQueryFields
      : originalKind === "fee-query"
        ? feeQueryFields
        : initialView === "finance-payment-audit"
          ? auditQueryFields
          : paymentQueryFields;
  const contractPaymentSourceNotice = !contractPaymentSource.active ? null : !contractPaymentSource.ok ? (
    <Alert
      type="error"
      showIcon
      message="合同付款来源定位失败"
      description={
        "error" in contractPaymentSource
          ? contractPaymentSource.error
          : "合同付款来源参数无效"
      }
    />
  ) : !financeDataReady || loading ? (
    <Alert
      type="info"
      showIcon
      message="正在定位合同付款来源"
      description={
        "paymentNo" in contractPaymentSource
          ? `请款单 ${contractPaymentSource.paymentNo}｜合同 ${contractPaymentSource.contractNo}`
          : "合同付款来源参数无效"
      }
      action={
        <Button onClick={() => onNavigate?.(contractPaymentSource.returnPage)}>
          返回合同详情
        </Button>
      }
    />
  ) : originalFinanceRows.length ? (
    <Alert
      type="success"
      showIcon
      message="已定位合同付款来源"
      description={`请款单 ${contractPaymentSource.paymentNo}｜合同 ${contractPaymentSource.contractNo}｜客户 ${contractPaymentSource.customer}｜金额 ${money(contractPaymentSource.amount)}｜来源ID ${contractPaymentSource.sourceId}`}
      action={
        <Button onClick={() => onNavigate?.(contractPaymentSource.returnPage)}>
          返回合同详情
        </Button>
      }
    />
  ) : (
    <Alert
      type="error"
      showIcon
      message="合同付款来源定位失败"
      description="未找到合同付款来源记录或当前账号无权查看"
      action={
        <Button onClick={() => onNavigate?.(contractPaymentSource.returnPage)}>
          返回合同详情
        </Button>
      }
    />
  );
  const originalColumns = activeRouteConfig
    ? configuredColumns
    : originalKind === "internal"
      ? internalOriginalColumns
      : originalKind === "fee-query"
        ? feeQueryOriginalColumns
        : initialView === "finance-payment-audit"
          ? paymentAuditOriginalColumns
          : paymentOriginalColumns;
  const isInternalHistoryList = [
    "finance-internal-refused",
    "finance-internal-void",
    "finance-internal-query",
  ].includes(initialView);
  const internalPaymentDetail =
    isInternalHistoryList && feeDetail ? (
      <section className="finance-original-panel finance-internal-payment-detail">
        <div className="finance-original-title finance-payment-detail-title">
          <h5>申请付款</h5>
          <Button size="small" onClick={() => setFeeDetail(null)}>
            返回请款单列表
          </Button>
        </div>
        <div className="finance-payment-flow" aria-label="付款流程">
          <span className="active">付款信息查看</span>
          <span>提交申请</span>
          <span>财务审批</span>
          <span>财务付款</span>
        </div>
        <Descriptions
          className="finance-payment-base-info"
          bordered
          size="small"
          column={2}
        >
          <Descriptions.Item label="案件编号">
            {feeDetail.data.case_no ? <Button type="link" onClick={() => openCaseDetail(feeDetail.data.case_no)}>{feeDetail.data.case_no}</Button> : "—"}
          </Descriptions.Item>
          <Descriptions.Item label="案件名称">
            {linkedCaseForFee(feeDetail)?.title || feeDetail.title || "—"}
          </Descriptions.Item>
          <Descriptions.Item label="合同编号">
            {feeDetail.data.contract_no ? <Button type="link" onClick={() => openContractDetail(feeDetail.data.contract_no)}>{feeDetail.data.contract_no}</Button> : "—"}
          </Descriptions.Item>
          <Descriptions.Item label="合同名称">
            {feeDetail.data.contract_title || "—"}
          </Descriptions.Item>
          <Descriptions.Item label="客户编号">
            {feeDetail.data.customer_no ? <Button type="link" onClick={() => openCustomerDetail(feeDetail.customer, feeDetail.data.customer_no)}>{feeDetail.data.customer_no}</Button> : "—"}
          </Descriptions.Item>
          <Descriptions.Item label="客户名称">
            {feeDetail.customer ? <Button type="link" onClick={() => openCustomerDetail(feeDetail.customer, feeDetail.data.customer_no)}>{feeDetail.customer}</Button> : "—"}
          </Descriptions.Item>
          <Descriptions.Item label="客户管理人">
            {financePersonDisplayName(
              feeDetail.data.customer_manager,
              feeDetail.data.customer_manager_display_name,
            )}
          </Descriptions.Item>
          <Descriptions.Item label="申请编号">
            {feeDetail.serial_no || "—"}
          </Descriptions.Item>
          <Descriptions.Item label="调查提成(已付)">
            {String(Number(feeDetail.data.paid_investigation || 0))}
          </Descriptions.Item>
          <Descriptions.Item label="案源提成(已付)">
            {String(Number(feeDetail.data.paid_source || 0))}
          </Descriptions.Item>
          <Descriptions.Item label="文书提成(已付)">
            {String(Number(feeDetail.data.paid_document || 0))}
          </Descriptions.Item>
          <Descriptions.Item label="开庭提成(已付)">
            {String(Number(feeDetail.data.paid_hearing || 0))}
          </Descriptions.Item>
          <Descriptions.Item label="申请日期">
            {(
              feeDetail.data.application_date ||
              feeDetail.created_at ||
              "—"
            ).slice(0, 10)}
          </Descriptions.Item>
          <Descriptions.Item label="审批意见">
            {feeDetail.data.review_comment ||
              feeDetail.data.approval_comment ||
              "—"}
          </Descriptions.Item>
        </Descriptions>
        <Tabs
          className="finance-payment-info-tabs"
          activeKey="payment"
          items={[
            {
              key: "payment",
              label: "付款信息",
              children: (
                <Table
                  rowKey={() => "payment-detail"}
                  size="small"
                  pagination={false}
                  columns={[
                    { title: "序号", dataIndex: "index", width: 55 },
                    { title: "支付对象", dataIndex: "payee", width: 110 },
                    { title: "提成类型", dataIndex: "fee_type", width: 125 },
                    { title: "基数", dataIndex: "base", width: 90 },
                    { title: "参考提成", dataIndex: "reference", width: 100 },
                    { title: "实际提成", dataIndex: "actual", width: 100 },
                    { title: "本次支付", dataIndex: "current", width: 100 },
                    { title: "备注", dataIndex: "remark", width: 260 },
                  ]}
                  dataSource={[
                    {
                      index: 1,
                      payee:
                        feeDetail.data.payee && !feeDetail.data.payee_username
                          ? feeDetail.data.payee
                          : financePersonDisplayName(
                              feeDetail.data.payee_username ||
                                feeDetail.data.applicant ||
                                feeDetail.owner,
                              feeDetail.data.payee_display_name ||
                                feeDetail.data.applicant_display_name ||
                                feeDetail.data.owner_display_name,
                            ),
                      fee_type: feeDetail.data.fee_type || "—",
                      base: Number(
                        feeDetail.data.commission_base || 0,
                      ).toFixed(2),
                      reference: Number(
                        feeDetail.data.reference_commission || 0,
                      ).toFixed(2),
                      actual: Number(
                        Number(
                          feeDetail.data.actual_commission ??
                            feeDetail.data.amount ??
                            0,
                        ),
                      ).toFixed(2),
                      current: Number(feeDetail.data.amount || 0).toFixed(2),
                      remark:
                        feeDetail.data.remark ||
                        feeDetail.data.description ||
                        "—",
                    },
                  ]}
                  scroll={{ x: 940 }}
                />
              ),
            },
          ]}
        />
      </section>
    ) : null;
  const invoiceReceivedReceiptId = (row: FinanceFlow | null) => {
    const data = row?.data || {};
    return (
      data.receipt_id ||
      data.received_payment_id ||
      data.incoming_payment_id ||
      data.receipt_record_id ||
      data.receipt_no ||
      data.received_payment_no ||
      data.incoming_payment_no ||
      ""
    );
  };
  const openInvoiceReceivedDetail = (row: FinanceFlow | null) => {
    const data = row?.data || {};
    const receiptId = invoiceReceivedReceiptId(row);
    if (!receiptId) {
      message.warning("当前发票未关联到账记录");
      return;
    }
    const nextQuery = {
      routeField13: receiptId,
      receipt_id: receiptId,
      incoming_payment_id: receiptId,
      receipt_no:
        data.receipt_no ||
        data.received_payment_no ||
        data.incoming_payment_no ||
        String(receiptId),
    };
    setOriginalQueryDraft(nextQuery);
    setOriginalQuery(nextQuery);
    setSelectedOriginalRows([]);
    onNavigate?.("finance-receipts-query");
  };
  const invoiceDisplay = invoiceProcess || invoiceCancel || invoiceDetail;
  const invoiceDetailData = invoiceDisplay?.data || {};
  const invoiceDetailCase = invoiceDisplay
    ? cases.find(
        (item) =>
          item.id === Number(invoiceDetailData.case_id || 0) ||
          item.serial_no === invoiceDetailData.case_no,
      )
    : undefined;
  const invoiceDetailPage = invoiceDisplay ? (
    <section className={`finance-invoice-detail-page${invoiceProcess ? " finance-invoice-process-page" : ""}${invoiceCancel ? " finance-invoice-cancel-page" : ""}`}>
      <div className="finance-original-title">
        <h5>{invoiceProcess ? "开票处理" : "开票信息"}</h5>
      </div>
      {invoiceCancel && (
        <div className="finance-invoice-cancel-box">
          <label htmlFor="invoice-cancel-reason">作废原因</label>
          <Input.TextArea
            id="invoice-cancel-reason"
            rows={2}
            value={invoiceCancelReason}
            onChange={(event) => setInvoiceCancelReason(event.target.value)}
          />
          <Button
            type="primary"
            loading={invoiceMutationLoading}
            onClick={() => void submitInvoiceCancel()}
          >
            提交
          </Button>
        </div>
      )}
      {invoiceProcess && (
        <div className="finance-invoice-process-box">
          <div className="finance-invoice-process-title">开票结果</div>
          <Form form={issueForm} layout="horizontal" className="finance-invoice-process-form">
            <Form.Item label="开票结果">
              <Input value="已开票" disabled />
            </Form.Item>
            <Form.Item label="领票人" name="invoice_holder">
              <Input />
            </Form.Item>
            <Form.Item label="高开金额" name="extra_amount">
              <InputNumber min={0} precision={2} placeholder="高开发票金额" style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item label="发票号" name="invoice_no" rules={[{ required: true, message: "请输入发票号码." }]}>
              <Input placeholder="发票号" />
            </Form.Item>
            <Form.Item label="开票意见" name="comment" className="finance-invoice-process-opinion">
              <Input.TextArea rows={2} placeholder="开票意见" />
            </Form.Item>
            <Form.Item name="invoice_date" hidden><DatePicker /></Form.Item>
          </Form>
          <div className="finance-invoice-process-actions">
            <Button type="primary" onClick={() => void issueInvoice()}>开票</Button>
            <Button danger onClick={() => void rejectInvoiceIssue()}>驳回</Button>
          </div>
        </div>
      )}
      <div className="finance-invoice-detail-section-title">发票内容</div>
      <Descriptions size="small" column={4} colon>
        <Descriptions.Item label="发票类别">
          {invoiceDetailData.invoice_type_display ||
            (String(invoiceDetailData.invoice_type || "").includes("专用")
              ? "专票"
              : "普票")}
        </Descriptions.Item>
        <Descriptions.Item label="发票抬头" span={3}>
          {invoiceDetailData.invoice_title || ""}
        </Descriptions.Item>
        <Descriptions.Item label="纳税人识别码">
          {invoiceDetailData.taxpayer_id || ""}
        </Descriptions.Item>
        <Descriptions.Item label="公司电话">
          {invoiceDetailData.invoice_phone || ""}
        </Descriptions.Item>
        <Descriptions.Item label="银行账号">
          {invoiceDetailData.bank_account || ""}
        </Descriptions.Item>
        <Descriptions.Item label="开户银行">
          {invoiceDetailData.bank_name || ""}
        </Descriptions.Item>
        <Descriptions.Item label="发票金额">
          {Number(invoiceDetailData.amount || 0).toFixed(2)}
        </Descriptions.Item>
        <Descriptions.Item label="高开发票金额">
          {Number(invoiceDetailData.extra_amount || 0).toFixed(2)}
        </Descriptions.Item>
        <Descriptions.Item label="开票地址" span={2}>
          {invoiceDetailData.invoice_address || ""}
        </Descriptions.Item>
      </Descriptions>
      <div className="finance-invoice-detail-section-title">申请信息</div>
      <Descriptions size="small" column={4} colon>
        {invoiceProcess ? <>
          <Descriptions.Item label="申请日期">
            {dayjs(invoiceDetailData.application_date || invoiceDisplay.created_at).format("YYYY年MM月DD日")}
          </Descriptions.Item>
          <Descriptions.Item label="开票申请号">{invoiceDisplay.serial_no}</Descriptions.Item>
          <Descriptions.Item label="客户名称">{invoiceDisplay.customer ? <Button type="link" onClick={() => openCustomerDetail(invoiceDisplay.customer, invoiceDetailData.customer_no)}>{invoiceDisplay.customer}</Button> : "—"}</Descriptions.Item>
          <Descriptions.Item label="开票申请人">
            {financePersonDisplayName(
              invoiceDetailData.applicant || invoiceDisplay.owner,
              invoiceDetailData.applicant_display_name || invoiceDetailData.owner_display_name,
            )}
          </Descriptions.Item>
          <Descriptions.Item label="申请备注" span={4}>{invoiceDetailData.remark || ""}</Descriptions.Item>
        </> : invoiceCancel ? <>
          <Descriptions.Item label="合同编号">{invoiceDetailData.contract_no ? <Button type="link" onClick={() => openContractDetail(invoiceDetailData.contract_no)}>{invoiceDetailData.contract_no}</Button> : ""}</Descriptions.Item>
          <Descriptions.Item label="外部合同号">{invoiceDetailData.external_contract_no || ""}</Descriptions.Item>
          <Descriptions.Item label="合同名称">{invoiceDetailData.contract_name || ""}</Descriptions.Item>
          <Descriptions.Item label="客户名称">{invoiceDisplay.customer ? <Button type="link" onClick={() => openCustomerDetail(invoiceDisplay.customer, invoiceDetailData.customer_no)}>{invoiceDisplay.customer}</Button> : "—"}</Descriptions.Item>
          <Descriptions.Item label="开票申请人">
            {financePersonDisplayName(
              invoiceDetailData.applicant || invoiceDisplay.owner,
              invoiceDetailData.applicant_display_name || invoiceDetailData.owner_display_name,
            )}
          </Descriptions.Item>
          <Descriptions.Item label="开票申请号">{invoiceDisplay.serial_no}</Descriptions.Item>
          <Descriptions.Item label="申请日期">
            {dayjs(invoiceDetailData.application_date || invoiceDisplay.created_at).format("YYYY年MM月DD日")}
          </Descriptions.Item>
          <Descriptions.Item label="申请备注">{invoiceDetailData.remark || ""}</Descriptions.Item>
          <Descriptions.Item label="发票号">{invoiceDetailData.invoice_no || ""}</Descriptions.Item>
          <Descriptions.Item label="票据状态">{invoiceDisplay.status}</Descriptions.Item>
          <Descriptions.Item label="领票人">
            {financePersonDisplayName(
              invoiceDetailData.recipient || invoiceDetailData.invoice_holder,
              invoiceDetailData.recipient_display_name || invoiceDetailData.invoice_holder_display_name,
            )}
          </Descriptions.Item>
        </> : <>
          <Descriptions.Item label="开票申请人">
            {financePersonDisplayName(
              invoiceDetailData.applicant || invoiceDisplay.owner,
              invoiceDetailData.applicant_display_name || invoiceDetailData.owner_display_name,
            )}
          </Descriptions.Item>
          <Descriptions.Item label="开票申请号">{invoiceDisplay.serial_no}</Descriptions.Item>
          <Descriptions.Item label="申请日期">
            {dayjs(invoiceDetailData.application_date || invoiceDisplay.created_at).format("YYYY年MM月DD日")}
          </Descriptions.Item>
          <Descriptions.Item label="客户名称">{invoiceDisplay.customer ? <Button type="link" onClick={() => openCustomerDetail(invoiceDisplay.customer, invoiceDetailData.customer_no)}>{invoiceDisplay.customer}</Button> : "—"}</Descriptions.Item>
          <Descriptions.Item label="发票号">{invoiceDetailData.invoice_no || ""}</Descriptions.Item>
          <Descriptions.Item label="票据状态">{invoiceDisplay.status}</Descriptions.Item>
          <Descriptions.Item label="领票人">
            {financePersonDisplayName(
              invoiceDetailData.recipient || invoiceDetailData.invoice_holder,
              invoiceDetailData.recipient_display_name || invoiceDetailData.invoice_holder_display_name,
            )}
          </Descriptions.Item>
          <Descriptions.Item label="申请备注">{invoiceDetailData.remark || ""}</Descriptions.Item>
          <Descriptions.Item label="开票意见" span={4}>{invoiceDetailData.invoiced_opinion || invoiceDetailData.review_comment || ""}</Descriptions.Item>
        </>}
      </Descriptions>
      <div className="finance-invoice-detail-section-title">服务项</div>
      <table className="finance-invoice-detail-table">
        <thead>
          <tr>
            {["序号", "服务名称", "数量", "单价", "金额", "税率", "税额"].map(
              (header) => <th key={header}>{header}</th>,
            )}
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>1</td>
            <td>{invoiceDetailData.invoice_content || "法律服务费"}</td>
            <td>1</td>
            <td>{Number(invoiceDetailData.amount || 0).toFixed(2)}</td>
            <td>{Number(invoiceDetailData.amount || 0).toFixed(2)}</td>
            <td>{invoiceDetailData.tax_rate || 0}</td>
            <td>{Number(invoiceDetailData.tax_amount || 0).toFixed(2)}</td>
          </tr>
          <tr className="finance-invoice-detail-total">
            <th>合计:</th>
            <td colSpan={3} />
            <td>{Number(invoiceDetailData.amount || 0).toFixed(2)}</td>
            <td colSpan={2} />
          </tr>
        </tbody>
      </table>
      <div className="finance-invoice-detail-section-title">合同信息</div>
      <table className="finance-invoice-detail-table">
        <thead>
          <tr>
            {(invoiceProcess
              ? ["序号", "案件类型", "案件名称", "案号", "合同号", "外部合同号", "费用类型", "金额", "已到账金额", "开票金额"]
              : invoiceCancel
                ? ["序号", "案件类型", "案件名称", "案号", "费用类型", "金额", "到账金额", "开票金额", ""]
              : ["序号", "合同编号", "外部合同号", "案件类型", "案件名称", "案号", "费用类型", "金额", "到账金额", "开票金额"]).map(
              (header) => <th key={header}>{header}</th>,
            )}
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>1</td>
            {(invoiceProcess
              ? [
                  invoiceDetailCase?.data?.case_type || "",
                  invoiceDetailCase?.title || "",
                  invoiceDetailData.case_no || "",
                  invoiceDetailData.contract_no || "",
                  invoiceDetailData.external_contract_no || "",
                ]
              : invoiceCancel
                ? [
                    invoiceDetailCase?.data?.case_type || "",
                    invoiceDetailCase?.title || "",
                    invoiceDetailData.case_no || "",
                  ]
              : [
                  invoiceDetailData.contract_no || "",
                  invoiceDetailData.external_contract_no || "",
                  invoiceDetailCase?.data?.case_type || "",
                  invoiceDetailCase?.title || "",
                  invoiceDetailData.case_no || "",
                ]).map((value, index) =>
                  !invoiceProcess && !invoiceCancel && index === 0 && value ? (
                    <td key={index}>
                      <Button
                        type="link"
                        onClick={() => openContractDetail(invoiceDetailData.contract_no)}
                      >
                        {value}
                      </Button>
                    </td>
                  ) : index === (invoiceProcess ? 2 : invoiceCancel ? 2 : 4) && value ? (
                    <td key={index}><Button type="link" onClick={() => openCaseDetail(value)}>{value}</Button></td>
                  ) : <td key={index}>{value}</td>,
                )}
            <td>{invoiceDetailData.fee_type || "律师代理费"}</td>
            <td>{Number(invoiceDetailData.amount || 0).toFixed(2)}</td>
            <td>
              <Button
                type="link"
                onClick={() => openInvoiceReceivedDetail(invoiceDisplay)}
                disabled={!invoiceReceivedReceiptId(invoiceDisplay)}
                title={
                  invoiceReceivedReceiptId(invoiceDisplay)
                    ? undefined
                    : "当前发票未关联到账记录"
                }
              >
                {Number(invoiceDetailData.received_amount || 0).toFixed(2)}
              </Button>
            </td>
            <td>{Number(invoiceDetailData.amount || 0).toFixed(2)}</td>
            {invoiceCancel && <td />}
          </tr>
        </tbody>
      </table>
      <div className="finance-invoice-detail-actions">
        <Button onClick={() => invoiceProcess ? setInvoiceProcess(null) : invoiceCancel ? setInvoiceCancel(null) : setInvoiceDetail(null)}>
          {invoiceProcess ? "返回待处理开票" : invoiceCancel || isInvoiceCompanyRoute ? "返回公司开票" : "返回我的开票"}
        </Button>
      </div>
    </section>
  ) : null;
  const paymentPrintPreviewPage = paymentPrintPreview ? (
    <section className="finance-original-panel finance-payment-package-print">
      <div className="finance-original-title finance-payment-package-actions">
        <h5>付款单打印</h5>
        <Space size={8}>
          <Button
            type="link"
            icon={<DownloadOutlined />}
            loading={paymentWordExportLoading}
            onClick={() => void downloadPaymentPrintWord()}
          >
            下载 Word
          </Button>
          <Button type="link" onClick={() => window.print()}>
            打印
          </Button>
          <Button size="small" onClick={() => setPaymentPrintPreview(null)}>
            取消
          </Button>
        </Space>
      </div>
      <div className="finance-payment-print-sheet" aria-label="付款申请单">
        <div className="finance-payment-print-heading">
          <strong>上海申浩律师事务所</strong>
          <h2>付款申请单</h2>
        </div>
        <table className="finance-payment-print-meta">
          <tbody>
            <tr>
              <th>打包流水号：</th>
              <td>{paymentPrintPreview.packageNo || "—"}</td>
              <th>打印日期：</th>
              <td>{paymentPrintPreview.printTime.slice(0, 10) || "—"}</td>
              <th />
              <td />
            </tr>
            <tr>
              <th>收款单位：</th>
              <td>{paymentPrintPreview.payee || "—"}</td>
              <th>付款总金额：</th>
              <td>{paymentPrintPreview.amount || "—"}</td>
              <th>属性：</th>
              <td>{paymentPrintPreview.attribute || "—"}</td>
            </tr>
            <tr>
              <th>请款单号：</th>
              <td>{paymentPrintPreview.serialNo || "—"}</td>
              <th>合同编号：</th>
              <td>{paymentPrintPreview.contractNo || "—"}</td>
              <th>合同名称：</th>
              <td>{paymentPrintPreview.contractTitle || "—"}</td>
            </tr>
            <tr>
              <th>付款日期：</th>
              <td>{paymentPrintPreview.paymentDate || "—"}</td>
              <th>付款凭证号：</th>
              <td>{paymentPrintPreview.voucherNo || "—"}</td>
              <th>经办人：</th>
              <td>{financePersonDisplayName(paymentPrintPreview.operator, paymentPrintPreview.operatorDisplayName)}</td>
            </tr>
          </tbody>
        </table>
        <table className="finance-payment-print-items">
          <thead>
            <tr>
              <th>案号</th>
              <th>付款金额</th>
              <th>费用类型</th>
              <th>费用名称</th>
              <th>申请人</th>
              <th>交款人</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{paymentPrintPreview.caseNo || "—"}</td>
              <td>{paymentPrintPreview.amount || "—"}</td>
              <td>{paymentPrintPreview.feeType || "—"}</td>
              <td>{paymentPrintPreview.feeTitle || "—"}</td>
              <td>{financePersonDisplayName(paymentPrintPreview.applicant, paymentPrintPreview.applicantDisplayName)}</td>
              <td>{financePersonDisplayName(paymentPrintPreview.payer, paymentPrintPreview.payerDisplayName)}</td>
            </tr>
            <tr>
              <th>备注：</th>
              <td colSpan={5}>{paymentPrintPreview.remark || "—"}</td>
            </tr>
            <tr className="finance-payment-print-subtotal">
              <td colSpan={4}>
                制单：{financePersonDisplayName(paymentPrintPreview.creator, paymentPrintPreview.creator)}　打印时间：
                {paymentPrintPreview.printTime || "—"}
              </td>
              <th>小计</th>
              <td>{paymentPrintPreview.amount || "—"}</td>
            </tr>
          </tbody>
        </table>
        <div className="finance-payment-print-signatures">
          <span>客户管理人签字：</span>
          <span>审批人签字：</span>
          <span>出纳签字：</span>
        </div>
      </div>
    </section>
  ) : null;
  const paymentPackagePrintData: PaymentPackagePreview | null =
    paymentPackagePreview ||
    (paymentPackageDetail
      ? {
          package_no: paymentPackageDetail.serial_no,
          print_date:
            paymentPackageDetail.data?.payment_date ||
            paymentPackageDetail.created_at?.slice(0, 10) ||
            dayjs().format("YYYY-MM-DD"),
          payee: paymentPackageDetail.data?.payee || "",
          total_amount: Number(
            paymentPackageDetail.data?.total_amount ??
              paymentPackageDetail.data?.amount ??
              0,
          ),
          items: paymentPackageDetail.data?.items || [],
          submitted: true,
        }
      : null);
  const paymentPackagePrintPage = paymentPackagePrintData ? (
      <section className="finance-original-panel finance-payment-package-print">
        <div className="finance-original-title finance-payment-package-actions">
          <h5>付款单打印</h5>
          <Space size={8}>
            {paymentPackagePreview ? (
              <Button
                type="link"
                loading={paymentPackageLoading}
                disabled={paymentPackagePreview.submitted}
                onClick={() => void submitInternalPaymentPackage()}
              >
                {paymentPackagePreview.submitted ? "已提交" : "提交并打印"}
              </Button>
            ) : (
              <Button
                type="link"
                loading={paymentWordExportLoading}
                onClick={() => void downloadPaymentPrintWord(paymentPackagePrintData.package_no)}
              >
                下载 Word
              </Button>
            )}
            {(!paymentPackagePreview || paymentPackagePreview.submitted) && (
              <Button
                type="link"
                icon={<DownloadOutlined />}
                loading={paymentWordExportLoading}
                onClick={() => void downloadPaymentPrintWord(paymentPackagePrintData.package_no)}
              >
                下载 Word
              </Button>
            )}
            {(!paymentPackagePreview || paymentPackagePreview.submitted) && (
              <Button type="link" onClick={() => window.print()}>
                打印
              </Button>
            )}
            <Button
              size="small"
              onClick={() => {
                setPaymentPackagePreview(null);
                setPaymentPackageDetail(null);
                setSelectedOriginalRows([]);
              }}
            >
              {paymentPackagePreview ? "返回待付款列表" : "返回付款包列表"}
            </Button>
          </Space>
        </div>
        <div className="finance-payment-print-sheet" aria-label="提成付款申请单">
          <div className="finance-payment-print-heading">
            <strong>上海申浩律师事务所</strong>
            <h2>提成付款申请单</h2>
          </div>
          <table className="finance-payment-print-meta">
            <tbody>
              <tr>
                <th>打包流水号：</th>
                <td>{paymentPackagePrintData.package_no}</td>
                <th>打印日期：</th>
                <td>{paymentPackagePrintData.print_date}</td>
                <th>付款总金额：</th>
                <td>￥{Number(paymentPackagePrintData.total_amount).toFixed(2)}</td>
              </tr>
            </tbody>
          </table>
          <table className="finance-payment-print-items">
            <thead>
              <tr>
                <th>案号</th>
                <th>案件名称</th>
                <th>付款金额</th>
                <th>提成类型</th>
                <th>收款人</th>
                <th>备注</th>
              </tr>
            </thead>
            <tbody>
              {paymentPackagePrintData.items.flatMap((item) => [
                <tr key={`${item.fee_id}-item`}>
                  <td>{item.case_no || "—"}</td>
                  <td>{item.case_name || "—"}</td>
                  <td>￥{Number(item.amount).toFixed(2)}</td>
                  <td>{item.commission_type || "—"}</td>
                  <td>{item.payee || "—"}</td>
                  <td>{item.remark || "—"}</td>
                </tr>,
                <tr key={`${item.fee_id}-subtotal`} className="finance-payment-print-subtotal">
                  <td colSpan={4}>备注：{item.remark || ""}</td>
                  <th>小计</th>
                  <td>￥{Number(item.amount).toFixed(2)}</td>
                </tr>,
              ])}
            </tbody>
          </table>
          <div className="finance-payment-print-signatures">
            <span>收款人签字：</span>
            <span>审批人签字：</span>
            <span>出纳签字：</span>
          </div>
        </div>
      </section>
    ) : null;
  const incomingPaymentDetailPage = incomingDetailTarget ? (
    <section className="finance-original-panel finance-incoming-applied-page">
      <div className="finance-incoming-applied-titlebar">
        <h2>已分配回款</h2>
        <Button onClick={() => {
          setIncomingDetailTarget(null);
          onNavigate?.("finance-incoming-company");
        }}>返回回款列表</Button>
      </div>
      <div className="finance-incoming-applied-heading">回款信息</div>
      <Descriptions
        className="finance-incoming-applied-summary"
        column={5}
        size="small"
        colon
      >
        <Descriptions.Item label="回款单位">{incomingDetailTarget.payer_name || "—"}</Descriptions.Item>
        <Descriptions.Item label="到账日期">{incomingDetailTarget.received_date || "—"}</Descriptions.Item>
        <Descriptions.Item label="银行单号">{incomingDetailTarget.bank_reference || "—"}</Descriptions.Item>
        <Descriptions.Item label="回款方式">{incomingDetailTarget.payment_method || incomingDetailTarget.bank_source || "—"}</Descriptions.Item>
        <Descriptions.Item label="合同号">{incomingDetailTarget.contract_no || "—"}</Descriptions.Item>
        <Descriptions.Item label="客户名称">{incomingDetailTarget.customer_name || incomingDetailTarget.claimed_customer || "—"}</Descriptions.Item>
        <Descriptions.Item label="到账金额">{incomingDetailTarget.amount == null ? "无权限" : money(incomingDetailTarget.amount)}</Descriptions.Item>
        <Descriptions.Item label="已分配额">{incomingDetailTarget.allocated_amount == null ? "无权限" : money(incomingDetailTarget.allocated_amount)}</Descriptions.Item>
        <Descriptions.Item label="未分配额">{incomingDetailTarget.remaining_amount == null ? "无权限" : money(incomingDetailTarget.remaining_amount)}</Descriptions.Item>
        <Descriptions.Item label="领款人">{incomingDetailTarget.claimant_display_name || incomingDetailTarget.claimant || "—"}</Descriptions.Item>
        <Descriptions.Item label="备注" span={5}>{incomingDetailTarget.remark || "—"}</Descriptions.Item>
      </Descriptions>
      <div className="finance-incoming-applied-heading">费用分配明细</div>
      <Table
        className="finance-incoming-applied-table"
        rowKey={(row, index) => row.detail_id || `${row.case_no || "row"}-${index}`}
        size="small"
        pagination={false}
        dataSource={incomingDetailTarget.allocation_details || []}
        locale={{ emptyText: "没有查询到符合条件的记录" }}
        columns={[
          { title: <><Checkbox disabled /> 全选</>, width: 76, render: () => <Checkbox disabled /> },
          { title: "案件类型", dataIndex: "case_type", width: 110, render: (value: string) => value || "—" },
          { title: "案件名称", dataIndex: "case_name", width: 220, render: (value: string) => value || "—" },
          { title: "案号", dataIndex: "case_no", width: 150, render: (value: string) => value ? <Button type="link" onClick={() => openCaseDetail(value)}>{value}</Button> : "—" },
          { title: "合同号", dataIndex: "contract_no", width: 150, render: (value: string) => value ? <Button type="link" onClick={() => openContractDetail(value)}>{value}</Button> : "—" },
          { title: "费用类型", dataIndex: "fee_type", width: 120, render: (value: string) => value || "—" },
          { title: "总额", dataIndex: "fee_total_amount", width: 110, align: "right" as const, render: (value: number | null) => value == null ? "无权限" : money(value) },
          { title: "已收", dataIndex: "fee_allocated_amount", width: 110, align: "right" as const, render: (value: number | null) => value == null ? "无权限" : money(value) },
          { title: "待收", width: 110, align: "right" as const, render: (_: unknown, row) => row.fee_total_amount == null || row.fee_allocated_amount == null ? "无权限" : money(Math.max(row.fee_total_amount - row.fee_allocated_amount, 0)) },
          { title: "本次回款", dataIndex: "current_amount", width: 120, align: "right" as const, render: (value: number | null) => value == null ? "无权限" : money(value) },
        ]}
      />
    </section>
  ) : null;

  if (initialView === "finance-receipts-new") return <ReceiptCreatePage />;

  return (
    <>
      {incomingPaymentDetailPage ||
        invoiceDetailPage ||
        paymentPrintPreviewPage ||
        paymentPackagePrintPage ||
        internalPaymentDetail ||
        (originalMode ? (
          <section
            className={`finance-original-panel${
              initialView === "finance-internal-mine"
                ? " finance-original-internal-mine"
                : isInvoiceMineRoute
                  ? " finance-original-invoice-mine"
                : isInvoicePendingRoute
                  ? " finance-original-invoice-pending"
                : isInvoiceCompanyRoute
                  ? " finance-original-invoice-company"
                : isInvoiceUnissuedRoute
                  ? " finance-original-invoice-unissued"
                : isGeneralSettlementRoute
                  ? isGeneralSettlementPaidRoute
                    ? " finance-original-settlement-paid"
                    : isGeneralSettlementRejectedRoute
                      ? " finance-original-settlement-audit finance-original-settlement-rejected"
                    : isGeneralSettlementAuditRoute ||
                        isGeneralSettlementPaymentRoute
                    ? " finance-original-settlement-audit"
                    : " finance-original-settlement-pending"
                : isArchiveSettlementActiveRoute
                  ? ` finance-original-archive-pending${
                      isArchiveSettlementPaidRoute
                        ? " finance-original-archive-paid"
                        : isArchiveSettlementRejectedRoute
                          ? " finance-original-archive-rejected"
                        : ""
                    }`
                : isFeeQueryRoute
                  ? " finance-original-fee-query"
                : initialView === "finance-internal-settle"
                  ? " finance-original-internal-settle"
                  : initialView === "finance-internal-payment"
                    ? " finance-original-internal-payment"
                  : [
                          "finance-internal-writeoff",
                          "finance-internal-done",
                        ].includes(initialView)
                      ? " finance-original-payment-packages"
                  : isInternalDetailRoute
                    ? " finance-original-internal-detail"
                  : [
                        "finance-internal-refused",
                        "finance-internal-void",
                        "finance-internal-query",
                      ].includes(initialView)
                    ? " finance-original-internal-list"
                    : isInternalApprovalRoute
                      ? " finance-original-internal-approval"
                      : ""
            }`}
          >
            <input
              ref={bankUploadRef}
              hidden
              type="file"
              accept=".csv,text/csv"
              onChange={(event) =>
                void importBankStatement(event.target.files?.[0])
              }
            />
            <div className="finance-original-title">
              <h5>{displayedOriginalTitle}</h5>
            </div>
            {contractPaymentSourceNotice}
            <div className="finance-original-query-grid">{originalFields}</div>
            <div className="finance-original-query-actions">
              <Button
                type="primary"
                disabled={contractPaymentSource.active}
                onClick={submitConfiguredQuery}
              >
                查询
              </Button>
              {["finance-payment-mine", "finance-internal-mine"].includes(initialView) && (
                <Button
                  icon={<ReloadOutlined />}
                  disabled={contractPaymentSource.active}
                  onClick={() => void load()}
                >
                  刷新
                </Button>
              )}
              {initialView === "finance-payment-audit" && (
                <Button
                  icon={<ReloadOutlined />}
                  disabled={contractPaymentSource.active}
                  onClick={() => void load()}
                >
                  刷新
                </Button>
              )}
              {initialView === "finance-payment-waiting" && (
                <Button
                  icon={<ReloadOutlined />}
                  disabled={contractPaymentSource.active}
                  onClick={() => void load()}
                >
                  刷新
                </Button>
              )}
              {initialView === "finance-payment-writeoff" && (
                <Button
                  icon={<ReloadOutlined />}
                  disabled={contractPaymentSource.active}
                  onClick={() => void load()}
                >
                  刷新
                </Button>
              )}
              {activeRouteConfig?.upload && (
                <Button
                  icon={<UploadOutlined />}
                  onClick={() => bankUploadRef.current?.click()}
                >
                  上传
                </Button>
              )}
              {(originalKind === "fee-query" ||
                activeRouteConfig?.clear ||
                initialView === "finance-payment-writeoff" ||
                [
                  "finance-settlement-pending",
                  "finance-settlement-audit",
                  "finance-settlement-payment",
                  "finance-settlement-refused",
                ].includes(initialView)) && (
                <Button onClick={clearConfiguredQuery}>
                  清空
                </Button>
              )}
            </div>
            <div className="finance-original-table-wrap">
              <Table
                rowKey="id"
                size="small"
                tableLayout={isInvoiceUnissuedRoute ? "fixed" : undefined}
                loading={loading}
                columns={originalColumns}
                dataSource={configuredRows}
                expandable={
                  isGeneralSettlementRoute
                    ? {
                        showExpandColumn: false,
                        expandedRowKeys: configuredRows.map((row) => row.id),
                        expandedRowRender: (row: Fee) => (
                          <div className="finance-settlement-expanded">
                            {isGeneralSettlementPaymentRoute ||
                            isGeneralSettlementPaidRoute ? (
                              <div className="finance-settlement-payment-context">
                                <span>
                                  审核时间: {String(row.data?.reviewed_at || "").replace("T", " ")}
                                  <br />提交时间: {String(row.data?.applied_at || row.created_at || "").replace("T", " ")}
                                </span>
                                <span>
                                  审核人: {financePersonDisplayName(row.data?.reviewer, row.data?.reviewer_display_name)}
                                  <br />提交人: {financePersonDisplayName(row.data?.applied_by || row.owner, row.data?.applied_by_display_name || row.data?.owner_display_name)}
                                </span>
                                <span>
                                  审核备注: <em>{row.data?.review_comment || ""}</em>
                                  <br />提交备注: {row.description || ""}
                                </span>
                                {isGeneralSettlementPaidRoute && (
                                  <span>
                                    <br />付款日期: {String(row.data?.paid_at || "").replace("T", " ")}
                                  </span>
                                )}
                                <span>
                                  回款方式: {row.data?.payment_method || "—"}
                                  <br />银行备注: {row.data?.bank_remark || ""}
                                </span>
                              </div>
                            ) : isGeneralSettlementRejectedRoute ? (
                              <div className="finance-settlement-rejected-context">
                                <span>
                                  审核时间: {String(row.data?.reviewed_at || "").replace("T", " ")}
                                  <br />提交时间: {String(row.data?.applied_at || row.created_at || "").replace("T", " ")}
                                </span>
                                <span>
                                  审核人: {financePersonDisplayName(row.data?.reviewer, row.data?.reviewer_display_name)}
                                  <br />提交人: {financePersonDisplayName(row.data?.applied_by || row.owner, row.data?.applied_by_display_name || row.data?.owner_display_name)}
                                </span>
                                <span>
                                  审核备注: <em>{row.data?.review_comment || row.data?.rejection_comment || ""}</em>
                                  <br />提交备注: {row.description || ""}
                                </span>
                                <span>
                                  回款方式: {row.data?.payment_method || "—"}
                                  <br />银行备注: {row.data?.bank_remark || ""}
                                </span>
                              </div>
                            ) : isGeneralSettlementAuditRoute ? (
                              <div className="finance-settlement-audit-context">
                                <span>
                                  提交时间: {String(row.data?.applied_at || row.created_at || "").replace("T", " ")}
                                  <br />提交人: {financePersonDisplayName(row.data?.applied_by || row.owner, row.data?.applied_by_display_name || row.data?.owner_display_name)}
                                </span>
                                <span>
                                  提交备注:
                                  <br />{row.description || ""}
                                </span>
                                <span>
                                  回款方式: {row.data?.payment_method || "—"}
                                  <br />银行备注: {row.data?.bank_remark || ""}
                                </span>
                              </div>
                            ) : (
                              <>
                                <div className="finance-settlement-context">
                                  <span>
                                    回款方式: {row.data?.payment_method || "—"}
                                  </span>
                                  <span>
                                    银行备注: {row.data?.bank_remark || ""}
                                  </span>
                                </div>
                                <div className="finance-settlement-review-note">
                                  回退结算审核备注: {row.data?.rejection_comment || ""}
                                </div>
                              </>
                            )}
                            {generalSettlementDetails.includes(row.id) && (
                              <Table
                                className="finance-settlement-detail-table"
                                rowKey={(detail: any) => detail.detail_id}
                                size="small"
                                pagination={false}
                                dataSource={row.data?.allocation_details || []}
                                scroll={{ x: 1889 }}
                                columns={[
                                  {
                                    title: <span className="finance-stacked-header"><span>序</span><span>号</span></span>,
                                    width: 43,
                                    render: (_v, _detail, index) => index + 1,
                                  },
                                  {
                                    title: <span className="finance-stacked-header"><span>操</span><span>作</span></span>,
                                    width: 115,
                                    render: (_v, detail: any) => (
                                      <Space size={0}>
                                        <Button type="link" title="新建案件任务" onClick={() => openCaseTaskCreate(detail)}>✉</Button>
                                        <Button type="link" title="导出结算清单" onClick={() => void exportGeneralSettlement("settlement", [row.id])}>▣</Button>
                                        <Button type="link" title="导出结算列表" onClick={() => void exportGeneralSettlement("case", [row.id])}>▦</Button>
                                      </Space>
                                    ),
                                  },
                                  { title: "案号", dataIndex: "case_no", width: 144, render: (value) => value ? <Button type="link" onClick={() => openCaseDetail(value)}>{value}</Button> : "—" },
                                  { title: "阶段", dataIndex: "case_stage", width: 115 },
                                  { title: <span className="finance-stacked-header"><span>费用</span><span>类型</span></span>, dataIndex: "fee_type", width: 115 },
                                  { title: <span className="finance-stacked-header"><span>费用</span><span>总金额</span></span>, dataIndex: "fee_total_amount", width: 115, align: "right", render: (value) => value == null ? "—" : Number(value).toFixed(2) },
                                  { title: <span className="finance-stacked-header"><span>费用</span><span>分配金额</span></span>, dataIndex: "fee_allocated_amount", width: 115, align: "right", render: (value) => value == null ? "—" : Number(value).toFixed(2) },
                                  { title: <span className="finance-stacked-header"><span>本笔</span><span>分配金额</span></span>, dataIndex: "current_amount", width: 115, align: "right", render: (value) => value == null ? "—" : Number(value).toFixed(2) },
                                  { title: <span className="finance-stacked-header"><span>本笔</span><span>分配日期</span></span>, dataIndex: "allocated_at", width: 173, render: (value) => String(value || "").replace("T", " ") || "—" },
                                  { title: <span className="finance-stacked-header"><span>本笔</span><span>结算金额</span></span>, dataIndex: "settlement_amount", width: 115, align: "right", render: (value) => value == null ? "—" : Number(value).toFixed(2) },
                                  { title: <span className="finance-stacked-header"><span>本笔</span><span>归档费</span></span>, dataIndex: "archive_fee", width: 115, align: "right", render: (value) => value == null ? "—" : Number(value).toFixed(2) },
                                  { title: "客户", dataIndex: "customer", width: 216, render: (value, detail: any) => value ? <Button type="link" onClick={() => openCustomerDetail(value, detail.customer_no)}>{value}</Button> : "—" },
                                  { title: <span className="finance-stacked-header"><span>经办</span><span>律师</span></span>, dataIndex: "handling_lawyer", width: 115, render: (value, detail: any) => financePersonDisplayNames(detail.handling_lawyers || value, detail.handling_lawyer_display_names || detail.handling_lawyer_display_name) },
                                  { title: <span className="finance-stacked-header"><span>律师</span><span>助理</span></span>, dataIndex: "assistant", width: 115, render: (value, detail: any) => financePersonDisplayName(value, detail.assistant_display_name || detail.lawyer_assistant_display_name) },
                                  { title: "合同号", dataIndex: "contract_no", width: 144, render: (value) => value ? <Button type="link" onClick={() => openContractDetail(value)}>{value}</Button> : "—" },
                                ]}
                              />
                            )}
                          </div>
                        ),
                      }
                    : isArchiveSettlementPaymentRoute ||
                        isArchiveSettlementPaidRoute ||
                        isArchiveSettlementRejectedRoute
                      ? {
                          showExpandColumn: false,
                          expandedRowKeys: configuredRows.map((row) => row.id),
                          expandedRowRender: (row: any) => (
                            <div className="finance-archive-payment-context">
                              <span>
                                {(isArchiveSettlementPaidRoute || isArchiveSettlementRejectedRoute) && (
                                  <>归档费审核人: {financePersonDisplayName(row.data?.archive_payment_reviewer, row.data?.archive_payment_reviewer_display_name)}<br /></>
                                )}
                                归档审核人: {financePersonDisplayName(row.data?.archive_reviewer, row.data?.archive_reviewer_display_name)}
                                <br />归档申请人: {financePersonDisplayName(row.data?.archive_submitter, row.data?.archive_submitter_display_name)}
                              </span>
                              <span>
                                {(isArchiveSettlementPaidRoute || isArchiveSettlementRejectedRoute) && (
                                  <>归档费审核时间: {row.data?.archive_payment_reviewed_at ? dayjs(row.data.archive_payment_reviewed_at).format("YYYY-M-D H:m:s") : "—"}<br /></>
                                )}
                                归档审核时间: {row.data?.archive_reviewed_at ? dayjs(row.data.archive_reviewed_at).format("YYYY-M-D H:m:s") : "—"}
                                <br />归档提交时间: {row.data?.archive_submitted_at ? dayjs(row.data.archive_submitted_at).format("YYYY-M-D H:m:s") : "—"}
                              </span>
                              <span>
                                {(isArchiveSettlementPaidRoute || isArchiveSettlementRejectedRoute) && (
                                  <>归档费审核备注: {row.data?.archive_payment_comment || ""}<br /></>
                                )}
                                归档审核备注: {row.data?.archive_review_comment || ""}
                                <br />归档提交备注: {row.data?.archive_submit_comment || ""}
                              </span>
                              <span>
                                {(isArchiveSettlementPaidRoute || isArchiveSettlementRejectedRoute) && (
                                  <>归档费支付状态: <span className={isArchiveSettlementRejectedRoute ? "finance-archive-rejected-status" : ""}>{row.status || "已支付"}</span><br /></>
                                )}
                                归档号: {row.data?.archive_no || "—"}
                                <br />归档审核状态: {row.data?.archive_status || "审核通过"}
                              </span>
                            </div>
                          ),
                        }
                    : undefined
                }
                components={
                  initialView === "finance-payment-query" && configuredRows.length
                    ? {
                        body: {
                          wrapper: ({ children, ...bodyProps }: any) => (
                            <tbody {...bodyProps}>
                              <tr className="finance-payment-query-page-total">
                                {paymentOriginalColumns.map((_column, index) => (
                                  <td key={`payment-query-total-${index}`}>
                                    {index === 4
                                      ? paymentQueryPageTotal(configuredRows)
                                      : null}
                                  </td>
                                ))}
                              </tr>
                              {children}
                            </tbody>
                          ),
                        },
                      }
                  : isFeeQueryRoute && configuredRows.length
                    ? {
                        body: {
                          wrapper: ({ children, ...bodyProps }: any) => (
                            <tbody {...bodyProps}>
                              <tr className="finance-fee-query-grand-total">
                                <td />
                                {activeRouteConfig.headers.map((header, index) => {
                                  const keyByHeader: Record<string, string> = {
                                    金额: "amount",
                                    退费金额: "refund_requested_amount",
                                    已退金额: "refunded_amount",
                                    到账金额: "cashed_amount",
                                    付款金额: "paid_amount",
                                  };
                                  const totalKey = keyByHeader[header];
                                  const totalValue = totalKey
                                    ? feeQueryMeta.totals[totalKey]
                                    : null;
                                  return (
                                    <td key={`${header}-${index}`}>
                                      {totalValue == null
                                        ? null
                                        : Number(totalValue).toFixed(2)}
                                    </td>
                                  );
                                })}
                              </tr>
                              {children}
                            </tbody>
                          ),
                        },
                      }
                  : isGeneralSettlementRoute && configuredRows.length
                    ? {
                        body: {
                          wrapper: ({ children, ...bodyProps }: any) => (
                            <tbody {...bodyProps}>
                              <tr className="finance-settlement-grand-total">
                                <td />
                                {activeRouteConfig.headers.map((header, index) => {
                                  const keyByHeader: Record<string, string> = {
                                    回款金额: "receipt_amount",
                                    已分金额: "allocated_amount",
                                    未分金额: "remaining_amount",
                                    已分官费: "assigned_official_fee",
                                    已分代理费: "assigned_agency_fee",
                                    已分其他费用: "assigned_other_fee",
                                    代理费结算金额: "agency_settlement_amount",
                                    扣归档费: "archive_fee",
                                    实际结算金额: "actual_settlement_amount",
                                  };
                                  const totalKey = keyByHeader[header];
                                  const hidePaymentTotal =
                                    (isGeneralSettlementPaymentRoute ||
                                      isGeneralSettlementPaidRoute) &&
                                    ["代理费结算金额", "实际结算金额"].includes(
                                      header,
                                    );
                                  const hideRejectedTotal =
                                    isGeneralSettlementRejectedRoute &&
                                    [
                                      "代理费结算金额",
                                      "扣归档费",
                                      "实际结算金额",
                                    ].includes(header);
                                  return (
                                    <td key={`${header}-${index}`}>
                                      {totalKey && !hidePaymentTotal && !hideRejectedTotal
                                        ? Number(generalSettlementMeta.totals[totalKey] || 0).toFixed(2)
                                        : null}
                                    </td>
                                  );
                                })}
                              </tr>
                              {children}
                            </tbody>
                          ),
                        },
                      }
                    : isArchiveSettlementActiveRoute && configuredRows.length
                      ? {
                          body: {
                            wrapper: ({ children, ...bodyProps }: any) => (
                              <tbody {...bodyProps}>
                                <tr className="finance-archive-settlement-grand-total">
                                  <td />
                                  {activeRouteConfig.headers.map((header, index) => (
                                    <td key={`${header}-${index}`}>
                                      {header === "回款金额"
                                        ? Number(archiveSettlementMeta.totals.receipt_amount || 0).toFixed(2)
                                        : header === "归档费金额"
                                          ? Number(archiveSettlementMeta.totals.archive_fee_amount || 0).toFixed(2)
                                          : null}
                                    </td>
                                  ))}
                                </tr>
                                {children}
                              </tbody>
                            ),
                          },
                        }
                    : activeRouteConfig?.source === "paymentPackages"
                    ? {
                        body: {
                          wrapper: ({ children, ...bodyProps }: any) => (
                            <tbody {...bodyProps}>
                              <tr className="finance-payment-package-grand-total">
                                {activeRouteConfig.headers.map(
                                  (header, index) => (
                                    <td key={`${header}-${index}`}>
                                      {header === "付款总金额"
                                        ? configuredRows
                                            .reduce(
                                              (sum, row) =>
                                                sum +
                                                Number(
                                                  row.data?.total_amount ??
                                                    row.data?.amount ??
                                                    0,
                                                ),
                                              0,
                                            )
                                            .toFixed(2)
                                        : null}
                                    </td>
                                  ),
                                )}
                              </tr>
                              {children}
                            </tbody>
                          ),
                        },
                      }
                    : isInternalDetailRoute && configuredRows.length
                      ? {
                          body: {
                            wrapper: ({ children, ...bodyProps }: any) => (
                              <tbody {...bodyProps}>
                                <tr className="finance-internal-detail-grand-total">
                                  <td />
                                  {activeRouteConfig.headers.map(
                                    (header, index) => (
                                      <td key={`${header}-${index}`}>
                                        {header === "金额"
                                          ? internalDetailMeta.totalAmount.toFixed(
                                              2,
                                            )
                                          : null}
                                      </td>
                                    ),
                                  )}
                                </tr>
                                {children}
                              </tbody>
                            ),
                          },
                        }
                    : isInvoiceUnissuedRoute && configuredRows.length
                      ? {
                          body: {
                            wrapper: ({ children, ...bodyProps }: any) => (
                              <tbody {...bodyProps}>
                                <tr className="finance-invoice-unissued-grand-total">
                                  <td />
                                  {activeRouteConfig.headers.map(
                                    (header, index) => (
                                      <td key={`${header}-${index}`}>
                                        {header === "金额"
                                          ? invoiceUnissuedMeta.totalAmount.toFixed(2)
                                          : header === "开票金额"
                                            ? invoiceUnissuedMeta.totalInvoiceAmount.toFixed(2)
                                            : header === "到账金额"
                                              ? invoiceUnissuedMeta.totalCashedAmount.toFixed(2)
                                              : header === "付款金额"
                                                ? invoiceUnissuedMeta.totalPaidAmount.toFixed(2)
                                                : null}
                                      </td>
                                    ),
                                  )}
                                </tr>
                                {children}
                              </tbody>
                            ),
                          },
                        }
                    : (isInvoiceMineRoute || isInvoicePendingRoute || isInvoiceCompanyRoute) && configuredRows.length
                      ? {
                          body: {
                            wrapper: ({ children, ...bodyProps }: any) => (
                              <tbody {...bodyProps}>
                                <tr className="finance-invoice-grand-total">
                                  <td />
                                  {activeRouteConfig.headers.map(
                                    (header, index) => (
                                      <td key={`${header}-${index}`}>
                                        {header === "开票金额"
                                          ? isInvoicePendingRoute
                                            ? invoicePendingMeta.totalAmount
                                            : isInvoiceCompanyRoute
                                              ? invoiceCompanyMeta.totalAmount
                                              : invoiceMineMeta.totalAmount
                                          : header === "高开金额"
                                            ? isInvoicePendingRoute
                                              ? invoicePendingMeta.totalExtraAmount
                                              : isInvoiceCompanyRoute
                                                ? invoiceCompanyMeta.totalExtraAmount
                                                : invoiceMineMeta.totalExtraAmount
                                            : null}
                                      </td>
                                    ),
                                  )}
                                </tr>
                                {children}
                              </tbody>
                            ),
                          },
                        }
                    : undefined
                }
                summary={
                  initialView === "finance-payment-query"
                    ? (pageData) =>
                        pageData.length ? (
                          <Table.Summary.Row className="finance-payment-query-page-total-bottom">
                            {paymentOriginalColumns.map((_column, index) => (
                              <Table.Summary.Cell
                                key={`payment-query-summary-${index}`}
                                index={index}
                              >
                                {index === 4
                                  ? paymentQueryPageTotal(pageData)
                                  : null}
                              </Table.Summary.Cell>
                            ))}
                          </Table.Summary.Row>
                        ) : null
                    : isFeeQueryRoute
                    ? (pageData) =>
                        pageData.length ? (
                          <Table.Summary.Row className="finance-fee-query-page-total">
                            <Table.Summary.Cell index={0} />
                            {activeRouteConfig.headers.map((header, index) => {
                              const keyByHeader: Record<string, string> = {
                                金额: "amount",
                                退费金额: "refund_requested_amount",
                                已退金额: "refunded_amount",
                                到账金额: "cashed_amount",
                                付款金额: "paid_amount",
                              };
                              const totalKey = keyByHeader[header];
                              return (
                                <Table.Summary.Cell
                                  key={`${header}-${index}`}
                                  index={index + 1}
                                >
                                  {totalKey
                                    ? pageData
                                        .reduce(
                                          (sum, row) =>
                                            sum + Number(row.data?.[totalKey] || 0),
                                          0,
                                        )
                                        .toFixed(2)
                                    : null}
                                </Table.Summary.Cell>
                              );
                            })}
                          </Table.Summary.Row>
                        ) : null
                  : initialView === "finance-internal-payment"
                    ? (pageData) => (
                        <Table.Summary.Row className="finance-internal-list-summary">
                          <Table.Summary.Cell index={0} />
                          {activeRouteConfig.headers.map((header, index) => (
                            <Table.Summary.Cell key={header} index={index + 1}>
                              {header === "实际提成"
                                ? pageData
                                    .reduce(
                                      (sum, row) =>
                                        sum +
                                        Number(
                                          row.data?.actual_commission ??
                                            row.data?.amount ??
                                            0,
                                        ),
                                      0,
                                    )
                                    .toFixed(2)
                                : null}
                            </Table.Summary.Cell>
                          ))}
                        </Table.Summary.Row>
                      )
                    : [
                          "finance-internal-writeoff",
                          "finance-internal-done",
                        ].includes(initialView)
                      ? (pageData) => (
                          <Table.Summary.Row className="finance-payment-package-summary">
                            {activeRouteConfig.headers.map((header, index) => (
                              <Table.Summary.Cell key={header} index={index}>
                                {header === "付款总金额"
                                  ? pageData
                                      .reduce(
                                        (sum, row) =>
                                          sum +
                                          Number(
                                            row.data?.total_amount ??
                                              row.data?.amount ??
                                              0,
                                          ),
                                        0,
                                      )
                                      .toFixed(2)
                                  : null}
                              </Table.Summary.Cell>
                            ))}
                          </Table.Summary.Row>
                        )
                      : isInternalDetailRoute
                        ? (pageData) =>
                            pageData.length ? (
                              <Table.Summary.Row className="finance-internal-detail-summary">
                              <Table.Summary.Cell index={0} />
                              {activeRouteConfig.headers.map(
                                (header, index) => (
                                  <Table.Summary.Cell
                                    key={`${header}-${index}`}
                                    index={index + 1}
                                  >
                                    {header === "金额"
                                      ? pageData
                                          .reduce(
                                            (sum, row) =>
                                              sum +
                                              Number(row.data?.amount || 0),
                                            0,
                                          )
                                          .toFixed(2)
                                      : null}
                                  </Table.Summary.Cell>
                                ),
                              )}
                              </Table.Summary.Row>
                            ) : null
                      : isInvoiceUnissuedRoute
                        ? (pageData) =>
                            pageData.length ? (
                              <Table.Summary.Row className="finance-invoice-unissued-page-total">
                                <Table.Summary.Cell index={0} />
                                {activeRouteConfig.headers.map(
                                  (header, index) => (
                                    <Table.Summary.Cell
                                      key={`${header}-${index}`}
                                      index={index + 1}
                                    >
                                      {header === "金额"
                                        ? pageData.reduce(
                                            (sum, row) =>
                                              sum + Number(row.data?.amount || 0),
                                            0,
                                          ).toFixed(2)
                                        : header === "开票金额"
                                          ? pageData.reduce(
                                              (sum, row) =>
                                                sum + Number(row.data?.invoice_amount || 0),
                                              0,
                                            ).toFixed(2)
                                          : header === "到账金额"
                                            ? pageData.reduce(
                                                (sum, row) =>
                                                  sum + Number(row.data?.cashed_amount || 0),
                                                0,
                                              ).toFixed(2)
                                            : header === "付款金额"
                                              ? pageData.reduce(
                                                  (sum, row) =>
                                                    sum + Number(row.data?.paid_amount || 0),
                                                  0,
                                                ).toFixed(2)
                                              : null}
                                    </Table.Summary.Cell>
                                  ),
                                )}
                              </Table.Summary.Row>
                            ) : null
                      : isInvoiceMineRoute || isInvoicePendingRoute || isInvoiceCompanyRoute
                        ? (pageData) =>
                            pageData.length ? (
                              <Table.Summary.Row className="finance-invoice-page-total">
                                <Table.Summary.Cell index={0} />
                                {activeRouteConfig.headers.map(
                                  (header, index) => (
                                    <Table.Summary.Cell
                                      key={`${header}-${index}`}
                                      index={index + 1}
                                    >
                                      {header === "开票金额"
                                        ? pageData
                                            .filter((row) =>
                                              isInvoicePendingRoute ||
                                              !["已撤回", "已作废"].includes(row.status),
                                            )
                                            .reduce(
                                              (sum, row) =>
                                                sum +
                                                Number(row.data?.amount || 0),
                                              0,
                                            )
                                        : header === "高开金额"
                                          ? pageData
                                              .filter((row) =>
                                                isInvoicePendingRoute ||
                                                !["已撤回", "已作废"].includes(row.status),
                                              )
                                              .reduce(
                                                (sum, row) =>
                                                  sum +
                                                  Number(
                                                    row.data?.extra_amount || 0,
                                                  ),
                                                0,
                                              )
                                          : null}
                                    </Table.Summary.Cell>
                                  ),
                                )}
                              </Table.Summary.Row>
                            ) : null
                      : [
                          "finance-internal-refused",
                          "finance-internal-void",
                          "finance-internal-query",
                        ].includes(initialView)
                      ? (pageData) => (
                          <Table.Summary.Row className="finance-internal-list-summary">
                            {activeRouteConfig.headers.map((_header, index) => (
                              <Table.Summary.Cell key={index} index={index}>
                                {index === 5
                                  ? pageData
                                      .reduce(
                                        (sum, row) =>
                                          sum + Number(row.data?.amount || 0),
                                        0,
                                      )
                                      .toFixed(2)
                                  : null}
                              </Table.Summary.Cell>
                            ))}
                          </Table.Summary.Row>
                        )
                      : undefined
                }
                rowSelection={
                  activeRouteConfig?.selectable ||
                  initialView === "finance-payment-audit" ||
                  initialView === "finance-payment-waiting" ||
                  initialView === "finance-payment-writeoff" ||
                  initialView === "finance-payment-query"
                    ? {
                        selectedRowKeys: selectedOriginalRows,
                        onChange: (keys) =>
                          setSelectedOriginalRows(
                            keys as (string | number)[],
                          ),
                        getTitleCheckboxProps: () =>
                          initialView === "finance-payment-waiting"
                            ? { disabled: false }
                            : {},
                        getCheckboxProps: (row) => ({
                          disabled:
                            initialView === "finance-internal-refund-audit" &&
                            row.status !== "待审批",
                        }),
                        ...(isArchiveSettlementActiveRoute
                          ? {
                              columnWidth: isArchiveSettlementRejectedRoute
                                ? 54
                                : 51,
                            }
                          : {}),
                      }
                    : undefined
                }
                rowClassName={(row) =>
                  isInvoiceMineRoute &&
                  ["已撤回", "已作废"].includes(row.status)
                    ? "finance-invoice-cancelled-row"
                    : ""
                }
                scroll={{
                  x: activeRouteConfig
                    ? isGeneralSettlementRoute
                      ? 1904
                    : isArchiveSettlementActiveRoute
                      ? 1904
                    : initialView === "finance-internal-settle"
                      ? 1246
                      : isInvoiceUnissuedRoute
                        ? 1904
                      : [
                            "finance-internal-refused",
                            "finance-internal-void",
                            "finance-internal-query",
                          ].includes(initialView)
                        ? 1904
                        : Math.max(1200, activeRouteConfig.headers.length * 125)
                    : originalKind === "fee-query"
                      ? 2100
                      : 1650,
                }}
                pagination={{
                  size: "small",
                  pageSize: isGeneralSettlementRoute
                    ? generalSettlementMeta.pageSize
                    : isArchiveSettlementActiveRoute
                      ? archiveSettlementMeta.pageSize
                    : isFeeQueryRoute
                      ? feeQueryMeta.pageSize
                    : initialView === "finance-payment-audit"
                      ? paymentAuditPageSize
                    : activeRouteConfig?.source === "paymentPackages"
                      ? paymentPackageMeta.pageSize
                    : paymentQueryControlledPageSize(
                        initialView,
                        paymentQueryPageSize,
                      ) ?? paymentQueryDefaultPageSize(initialView) ??
                      ([
                    "finance-payment-mine",
                    "finance-internal-mine",
                    "finance-internal-settle",
                    "finance-internal-refused",
                    "finance-internal-void",
                    "finance-internal-payment",
                    "finance-internal-writeoff",
                    "finance-internal-query",
                    "finance-internal-done",
                    ...internalApprovalRoutes,
                    ].includes(initialView)
                      ? 15
                      : isInvoiceMineRoute
                      ? invoiceMineMeta.pageSize
                    : isInvoicePendingRoute
                      ? invoicePendingMeta.pageSize
                    : isInvoiceCompanyRoute
                      ? invoiceCompanyMeta.pageSize
                    : isInvoiceUnissuedRoute
                      ? invoiceUnissuedMeta.pageSize
                    : isInternalDetailRoute
                      ? internalDetailMeta.pageSize
                      : 20),
                  pageSizeOptions:
                    activeRouteConfig?.source === "paymentPackages"
                      ? paymentPackagePageSizeOptions
                      : paymentQueryPageSizeOptions(initialView) ??
                    ([
                    "finance-payment-mine",
                    "finance-settlement-pending",
                    "finance-settlement-audit",
                    "finance-archive-fee-pending",
                    "finance-archive-fee-payment",
                    "finance-archive-fee-paid",
                    "finance-archive-fee-refused",
                    "finance-internal-mine",
                    "finance-internal-settle",
                    "finance-internal-refused",
                    "finance-internal-void",
                    "finance-internal-payment",
                    "finance-internal-writeoff",
                    "finance-internal-query",
                    "finance-internal-done",
                    "finance-internal-detail",
                    "finance-internal-company",
                    "finance-invoice-mine",
                    "finance-invoice-pending",
                    "finance-invoice-company",
                    "finance-invoice-unissued",
                    "finance-invoice-company-unissued",
                    "finance-fee-query",
                    ...internalApprovalRoutes,
                    ].includes(initialView)
                      ? [10, 15, 20, 50, 100, 200]
                      : undefined),
                  showQuickJumper: paymentQueryQuickJumper(initialView),
                  showSizeChanger: true,
                  ...(initialView === "finance-payment-query"
                    ? {
                        onShowSizeChange: (_page: number, pageSize: number) => {
                          setSelectedOriginalRows([]);
                          setPaymentQueryPageSize(pageSize);
                          refreshPaymentQueryPage(1, pageSize);
                        },
                      }
                    : {}),
                  ...(initialView === "finance-payment-audit"
                    ? {
                        onShowSizeChange: (_page: number, pageSize: number) => {
                          setSelectedOriginalRows([]);
                          setPaymentAuditPageSize(pageSize);
                        },
                      }
                    : {}),
                  ...(activeRouteConfig?.source === "paymentPackages"
                    ? {
                        onShowSizeChange: (_page: number, pageSize: number) => {
                          setSelectedOriginalRows([]);
                          void loadPaymentPackages(originalQuery, 1, pageSize).catch(
                            () => message.error("付款包查询失败"),
                          );
                        },
                      }
                    : {}),
                  ...(isFeeQueryRoute
                    ? {
                        current: feeQueryMeta.page,
                        total: feeQueryMeta.total,
                        onChange: (page: number, pageSize: number) => {
                          setSelectedOriginalRows([]);
                          void loadFeeQuery(originalQuery, page, pageSize).catch(
                            (error: any) =>
                              message.error(
                                error?.response?.data?.detail ||
                                  "费用查询翻页失败",
                              ),
                          );
                        },
                      }
                    : activeRouteConfig?.source === "paymentPackages"
                      ? {
                          current: paymentPackageMeta.page,
                          total: paymentPackageMeta.total,
                          onChange: (page: number, pageSize: number) => {
                            setSelectedOriginalRows([]);
                            void loadPaymentPackages(originalQuery, page, pageSize).catch(
                              () => message.error("付款包查询失败"),
                            );
                          },
                        }
                    : initialView === "finance-payment-query"
                      ? {
                          current: paymentQueryMeta.page,
                          total: paymentQueryMeta.total,
                          onChange: (page: number, pageSize: number) => {
                            refreshPaymentQueryPage(page, pageSize);
                          },
                        }
                      : {}),
                  ...(isInternalDetailRoute
                    ? {
                        current: internalDetailMeta.page,
                        total: internalDetailMeta.total,
                        onChange: (page: number, pageSize: number) => {
                          setSelectedOriginalRows([]);
                          void loadInternalDetails(
                            originalQuery,
                            page,
                            pageSize,
                          ).catch((error: any) =>
                            message.error(
                              error?.response?.data?.detail ||
                                "内部费用明细翻页失败",
                            ),
                          );
                        },
                      }
                    : {}),
                  ...(isInvoiceMineRoute
                    ? {
                        current: invoiceMineMeta.page,
                        total: invoiceMineMeta.total,
                        onChange: (page: number, pageSize: number) => {
                          setSelectedOriginalRows([]);
                          void loadInvoiceMine(
                            originalQuery,
                            page,
                            pageSize,
                          ).catch((error: any) =>
                            message.error(
                              error?.response?.data?.detail ||
                                "我的开票翻页失败",
                            ),
                          );
                        },
                      }
                    : {}),
                  ...(isInvoicePendingRoute
                    ? {
                        current: invoicePendingMeta.page,
                        total: invoicePendingMeta.total,
                        onChange: (page: number, pageSize: number) => {
                          setSelectedOriginalRows([]);
                          void loadInvoicePending(
                            originalQuery,
                            page,
                            pageSize,
                          ).catch((error: any) =>
                            message.error(
                              error?.response?.data?.detail ||
                                "待处理开票翻页失败",
                            ),
                          );
                        },
                      }
                    : {}),
                  ...(isInvoiceCompanyRoute
                    ? {
                        current: invoiceCompanyMeta.page,
                        total: invoiceCompanyMeta.total,
                        onChange: (page: number, pageSize: number) => {
                          setSelectedOriginalRows([]);
                          void loadInvoiceCompany(
                            originalQuery,
                            page,
                            pageSize,
                          ).catch((error: any) =>
                            message.error(
                              error?.response?.data?.detail ||
                                "公司开票翻页失败",
                            ),
                          );
                        },
                      }
                    : {}),
                  ...(isInvoiceUnissuedRoute
                    ? {
                        current: invoiceUnissuedMeta.page,
                        total: invoiceUnissuedMeta.total,
                        onChange: (page: number, pageSize: number) => {
                          setSelectedOriginalRows([]);
                          void loadInvoiceUnissued(
                            originalQuery,
                            page,
                            pageSize,
                          ).catch((error: any) =>
                            message.error(
                              error?.response?.data?.detail ||
                                "未开票列表翻页失败",
                            ),
                          );
                        },
                      }
                    : {}),
                  ...(isGeneralSettlementRoute
                    ? {
                        current: generalSettlementMeta.page,
                        total: generalSettlementMeta.total,
                        onChange: (page: number, pageSize: number) => {
                          setSelectedOriginalRows([]);
                          setGeneralSettlementDetails([]);
                          void loadGeneralSettlements(
                            originalQuery,
                            page,
                            pageSize,
                          ).catch((error: any) =>
                            message.error(
                              error?.response?.data?.detail ||
                                "待结算翻页失败",
                            ),
                          );
                        },
                      }
                    : {}),
                  ...(isArchiveSettlementActiveRoute
                    ? {
                        current: archiveSettlementMeta.page,
                        total: archiveSettlementMeta.total,
                        onChange: (page: number, pageSize: number) => {
                          setSelectedOriginalRows([]);
                          void loadArchiveSettlements(
                            originalQuery,
                            page,
                            pageSize,
                          ).catch((error: any) =>
                            message.error(
                              error?.response?.data?.detail ||
                                (isArchiveSettlementPaymentRoute
                                  ? "待支付翻页失败"
                                  : isArchiveSettlementRejectedRoute
                                    ? "已拒绝翻页失败"
                                  : "待归档翻页失败"),
                            ),
                          );
                        },
                      }
                    : {}),
                  showTotal: (total) =>
                    [
                      "finance-settlement-pending",
                      "finance-settlement-audit",
                      "finance-settlement-payment",
                      "finance-settlement-paid",
                      "finance-settlement-refused",
                      "finance-archive-fee-pending",
                      "finance-archive-fee-payment",
                      "finance-archive-fee-paid",
                      "finance-archive-fee-refused",
                      "finance-internal-mine",
                      "finance-internal-settle",
                      "finance-internal-refused",
                      "finance-internal-void",
                      "finance-internal-payment",
                      "finance-internal-writeoff",
                      "finance-internal-query",
                      "finance-internal-done",
                      "finance-internal-detail",
                      "finance-internal-company",
                      "finance-invoice-mine",
                      "finance-invoice-pending",
                      "finance-invoice-company",
                      "finance-invoice-unissued",
                      "finance-invoice-company-unissued",
                      "finance-fee-query",
                      ...internalApprovalRoutes,
                    ].includes(initialView)
                      ? `共有${total}条，每页显示`
                      : `共 ${total} 条`,
                }}
                locale={{
                  emptyText:
                    isInternalDetailRoute ||
                    isFeeQueryRoute ||
                    initialView === "finance-payment-query"
                    ? "没有查询到符合条件的记录 。"
                    : "没有查询到符合条件的记录。",
                }}
              />
              {paymentQueryShowsSinglePageGo(
                initialView,
                configuredRows.length,
                paymentQueryControlledPageSize(
                  initialView,
                  paymentQueryPageSize,
                ) ?? paymentQueryDefaultPageSize(initialView) ?? 20,
              ) && (
                <div
                  className="finance-payment-query-single-page-go"
                  style={{
                    display: "flex",
                    justifyContent: "flex-end",
                    alignItems: "center",
                    gap: 8,
                    padding: "0 16px 16px",
                  }}
                >
                  <Input
                    aria-label="跳转页码"
                    size="small"
                    value={paymentQueryQuickPage}
                    onChange={(event) =>
                      setPaymentQueryQuickPage(event.target.value)
                    }
                    style={{ width: 50 }}
                  />
                  <Button
                    size="small"
                    onClick={submitPaymentQueryQuickPage}
                  >
                    GO
                  </Button>
                </div>
              )}
            </div>
            {isArchiveSettlementActiveRoute && archiveSettlementMeta.total > 0 && (
              <div className="finance-archive-settlement-footer">
                <Space size={7}>
                  {isArchiveSettlementPaymentRoute && (
                    <>
                      <Button
                        loading={archiveSettlementBusy}
                        onClick={() =>
                          openArchiveSettlementReview(
                            configuredRows.filter((row) =>
                              selectedOriginalRows.includes(row.id),
                            ),
                            true,
                          )
                        }
                      >
                        同意支付
                      </Button>
                      <Button
                        loading={archiveSettlementBusy}
                        onClick={() =>
                          openArchiveSettlementReview(
                            configuredRows.filter((row) =>
                              selectedOriginalRows.includes(row.id),
                            ),
                            false,
                          )
                        }
                      >
                        拒绝支付
                      </Button>
                    </>
                  )}
                  {isArchiveSettlementPaidRoute && (
                    <Button
                      loading={archiveSettlementBusy}
                      onClick={() =>
                        openArchiveSettlementRollback(
                          configuredRows.filter((row) =>
                            selectedOriginalRows.includes(row.id),
                          ),
                        )
                      }
                    >
                      回滚归档费结算
                    </Button>
                  )}
                  {isArchiveSettlementRejectedRoute && (
                    <Button
                      loading={archiveSettlementBusy}
                      onClick={() =>
                        openArchiveSettlementReapply(
                          configuredRows.filter((row) =>
                            selectedOriginalRows.includes(row.id),
                          ),
                        )
                      }
                    >
                      重新申请
                    </Button>
                  )}
                  <Button
                    loading={archiveSettlementBusy}
                    onClick={() => void exportPendingArchiveSettlements()}
                  >
                    导出选中
                  </Button>
                </Space>
              </div>
            )}
            {isGeneralSettlementRoute && generalSettlementMeta.total > 0 && (
              <div className="finance-settlement-footer">
                <Space size={7}>
                  {!isGeneralSettlementPaidRoute && (
                    <Button
                      loading={generalSettlementBusy}
                      onClick={() =>
                        isGeneralSettlementRejectedRoute
                          ? openGeneralSettlementReapply(
                              configuredRows.filter((row) =>
                                selectedOriginalRows.includes(row.id),
                              ),
                            )
                          : isGeneralSettlementPaymentRoute
                          ? openGeneralSettlementPayment(
                              configuredRows.filter((row) =>
                                selectedOriginalRows.includes(row.id),
                              ),
                              "paid",
                            )
                          : isGeneralSettlementAuditRoute
                          ? openGeneralSettlementReview(
                              configuredRows.filter((row) =>
                                selectedOriginalRows.includes(row.id),
                              ),
                              true,
                            )
                          : void applyGeneralSettlementRows()
                        }
                    >
                      {isGeneralSettlementRejectedRoute
                        ? "重新申请"
                        : isGeneralSettlementPaymentRoute
                        ? "标记已支付"
                        : isGeneralSettlementAuditRoute
                          ? "同意结算"
                          : "申请结算"}
                    </Button>
                  )}
                  {isGeneralSettlementAuditRoute && (
                    <Button
                      loading={generalSettlementBusy}
                      onClick={() =>
                        openGeneralSettlementReview(
                          configuredRows.filter((row) =>
                            selectedOriginalRows.includes(row.id),
                          ),
                          false,
                        )
                      }
                    >
                      拒绝结算
                    </Button>
                  )}
                  <Button
                    loading={generalSettlementBusy}
                    onClick={() =>
                      void exportGeneralSettlement("settlement")
                    }
                  >
                    导出结算清单
                  </Button>
                  <Button
                    loading={generalSettlementBusy}
                    onClick={() => void exportGeneralSettlement("receipt")}
                  >
                    导出到账清单
                  </Button>
                  <Button
                    loading={generalSettlementBusy}
                    onClick={() => void exportGeneralSettlement("case")}
                  >
                    导出案件清单
                  </Button>
                </Space>
              </div>
            )}
            {activeRouteConfig?.note && (
              <div className="finance-original-note">
                {activeRouteConfig.note}
              </div>
            )}
            {initialView === "finance-internal-payment" && (
              <div className="finance-original-payment-footer">
                <Button
                  loading={paymentPackageLoading}
                  onClick={() => void previewInternalPaymentPackage()}
                >
                  打包付款
                </Button>
                <span>提示:选择同一收款进行打包付款.</span>
              </div>
            )}
            {isInternalApprovalRoute &&
              configuredRows.some((row) => row.status === "待审批") && (
                <div className="finance-original-approval-footer">
                  <Button onClick={openBatchFeeReview}>审批</Button>
                  <span>已选择 {selectedOriginalRows.length} 条</span>
                </div>
              )}
            {activeRouteConfig?.export && (
              <div className="finance-original-footer">
                {initialView === "finance-payment-print" ? (
                  <Button
                    onClick={() => void previewInternalPaymentPackage()}
                    loading={paymentPackageLoading}
                  >
                    合并打印
                  </Button>
                ) : isInvoiceUnissuedRoute ? (
                  <Space size={7}>
                    <Dropdown
                      trigger={["click"]}
                      menu={{
                        items: [
                          { key: "selected", label: "导出选中" },
                          { key: "all", label: "导出全部" },
                        ],
                        onClick: ({ key }) =>
                          void exportInvoiceUnissued(key === "selected"),
                      }}
                    >
                      <Button
                        disabled={!configuredRows.length}
                        loading={invoiceExportLoading}
                      >
                        导出
                      </Button>
                    </Dropdown>
                    <Dropdown
                      trigger={["click"]}
                      menu={{
                        items: [
                          { key: "upload", label: "上传案件文档" },
                          {
                            key: "new-fee",
                            label: "新增案件费用",
                            children: [
                              { key: "official-fee", label: "新增官费" },
                              { key: "agency-fee", label: "新增代理费" },
                              { key: "other-fee", label: "新增其他费用" },
                            ],
                          },
                          { key: "internal-fee", label: "新增内部费用" },
                          {
                            key: "batch-modify",
                            label: "批量修改",
                            children: [
                              { key: "hearing_lawyer", label: "修改开庭律师" },
                              { key: "handling_lawyers", label: "修改经办律师" },
                              { key: "assistant", label: "修改律师助理" },
                              { key: "case_stage", label: "修改案件阶段" },
                            ],
                          },
                          { key: "authorization", label: "生成授权委托书" },
                          { key: "law-firm-letter", label: "生成律所函" },
                          { key: "identity", label: "生成身份证明" },
                          { key: "settlement", label: "生成结算提成表" },
                          { key: "tasks", label: "案件任务" },
                          { key: "logs", label: "案件日志" },
                        ],
                        onClick: ({ key }) => runSettlementMoreAction(key),
                      }}
                    >
                      <Button
                        disabled={!configuredRows.length}
                        loading={settlementActionLoading}
                      >
                        更多操作
                      </Button>
                    </Dropdown>
                  </Space>
                ) : isInternalDetailRoute ? (
                  <Dropdown
                    trigger={["click"]}
                    menu={{
                      items: [
                        { key: "selected", label: "导出选中" },
                        { key: "all", label: "导出全部" },
                      ],
                      onClick: ({ key }) =>
                        void exportInternalDetails(key === "selected"),
                    }}
                  >
                    <Button loading={internalDetailExportLoading}>导出</Button>
                  </Dropdown>
                ) : isInvoiceMineRoute || isInvoicePendingRoute || isInvoiceCompanyRoute ? (
                  <Space size={7}>
                    <Button
                      disabled={!configuredRows.length}
                      loading={invoiceExportLoading}
                      onClick={() => void exportInvoiceList(false)}
                    >
                      导出全部
                    </Button>
                    <Button
                      disabled={!configuredRows.length}
                      loading={invoiceExportLoading}
                      onClick={() => void exportInvoiceList(true)}
                    >
                      导出选中
                    </Button>
                  </Space>
                ) : initialView === "finance-internal-settle" ? (
                  <Space size={7}>
                    <Dropdown
                      trigger={["click"]}
                      menu={{
                        items: [
                          { key: "selected", label: "导出选中" },
                          { key: "all", label: "导出全部" },
                        ],
                        onClick: ({ key }) =>
                          exportConfiguredRows(key === "selected"),
                      }}
                    >
                      <Button>导出 ▾</Button>
                    </Dropdown>
                    <Dropdown
                      trigger={["click"]}
                      menu={{
                        items: [
                          { key: "upload", label: "上传案件文档" },
                          {
                            key: "new-fee",
                            label: "新增案件费用",
                            children: [
                              { key: "official-fee", label: "新增官费" },
                              { key: "agency-fee", label: "新增代理费" },
                              { key: "other-fee", label: "新增其他费用" },
                              { key: "internal-fee", label: "新增内部费用" },
                            ],
                          },
                          {
                            key: "batch-modify",
                            label: "批量修改",
                            children: [
                              { key: "hearing_lawyer", label: "修改开庭律师" },
                              {
                                key: "handling_lawyers",
                                label: "修改经办律师",
                              },
                              { key: "assistant", label: "修改律师助理" },
                              { key: "case_stage", label: "修改案件阶段" },
                            ],
                          },
                          { key: "authorization", label: "生成授权委托书" },
                          { key: "law-firm-letter", label: "生成律所函" },
                          { key: "identity", label: "生成身份证明" },
                          { key: "settlement", label: "生成结算提成表" },
                          { key: "tasks", label: "案件任务" },
                          { key: "logs", label: "案件日志" },
                        ],
                        onClick: ({ key }) => runSettlementMoreAction(key),
                      }}
                    >
                      <Button loading={settlementActionLoading}>
                        更多操作 ▾
                      </Button>
                    </Dropdown>
                    <Button onClick={markCommissionPaid}>标识提成已发</Button>
                  </Space>
                ) : isRefundCaseFeeRoute ? (
                  <Space size={7} wrap>
                    <Dropdown
                      trigger={["click"]}
                      menu={{
                        items: [
                          { key: "selected", label: "导出选中" },
                          { key: "all", label: "导出全部" },
                        ],
                        onClick: ({ key }) => void exportFeeQuery(key === "selected"),
                      }}
                    >
                      <Button loading={feeQueryExportLoading}>导出 ▾</Button>
                    </Dropdown>
                    <Dropdown
                      trigger={["click"]}
                      menu={{
                        items: [
                          { key: "upload", label: "上传案件文档" },
                          {
                            key: "new-fee",
                            label: "新增案件费用",
                            children: [
                              { key: "official-fee", label: "新增官费" },
                              { key: "agency-fee", label: "新增代理费" },
                              { key: "other-fee", label: "新增其他费用" },
                            ],
                          },
                          { key: "internal-fee", label: "新增内部费用" },
                          {
                            key: "batch-modify",
                            label: "批量修改",
                            children: [
                              { key: "hearing_lawyer", label: "修改开庭律师" },
                              { key: "handling_lawyers", label: "修改经办律师" },
                              { key: "assistant", label: "修改律师助理" },
                              { key: "case_stage", label: "修改案件阶段" },
                            ],
                          },
                          { key: "authorization", label: "生成授权委托书" },
                          { key: "law-firm-letter", label: "生成律所函" },
                          { key: "identity", label: "生成身份证明" },
                          { key: "settlement", label: "生成结算提成表" },
                          { key: "tasks", label: "案件任务" },
                          { key: "logs", label: "案件日志" },
                        ],
                        onClick: ({ key }) => runSettlementMoreAction(key),
                      }}
                    >
                      <Button loading={settlementActionLoading}>更多操作 ▾</Button>
                    </Dropdown>
                    <Dropdown
                      trigger={["click"]}
                      menu={{
                        items: [
                          { key: "status", label: "退费进度修改" },
                          { key: "court", label: "添加法院日志" },
                          { key: "received", label: "添加到账日志" },
                          { key: "other", label: "添加其他日志" },
                        ],
                        onClick: ({ key }) => {
                          if (!requireRefundCaseFeeSelection().length) return;
                          if (key === "status") {
                            const firstId = selectedOriginalRows[0];
                            const firstRow = configuredRows.find((row) => row.id === firstId);
                            const currentStatus = firstRow?.data?.refund_status || "R10";
                            setRefundCaseFeeStatus(currentStatus);
                            setRefundCaseFeeStatusOpen(true);
                          } else {
                            const templates: Record<string, string> = {
                              court: "提交法院时间:\n法院联系人:\n联系电话:\n快递单号:",
                              received: "法院打款时间:\n账户:",
                              other: "",
                            };
                            setRefundCaseFeeLogContent(templates[key] || "");
                            setRefundCaseFeeLogKind(key as "court" | "received" | "other");
                          }
                        },
                      }}
                    >
                      <Button>退费操作 ▾</Button>
                    </Dropdown>
                    {canManage && (
                      <Button
                        danger
                        loading={refundCaseFeeMutationLoading}
                        onClick={() => {
                          if (!requireRefundCaseFeeSelection().length) return;
                          Modal.confirm({
                            title: "标记不再办理退费",
                            content: "确认将选中费用移出待退费列表？",
                            okText: "确认标记",
                            cancelText: "取消",
                            onOk: () => submitRefundCaseFeeStatus("R100"),
                          });
                        }}
                      >
                        标记不再办理退费
                      </Button>
                    )}
                  </Space>
                ) : isFeeQueryRoute ? (
                  <Space size={7}>
                    <Dropdown
                      trigger={["click"]}
                      menu={{
                        items: [
                          { key: "selected", label: "导出选中" },
                          { key: "all", label: "导出全部" },
                        ],
                        onClick: ({ key }) =>
                          void exportFeeQuery(key === "selected"),
                      }}
                    >
                      <Button loading={feeQueryExportLoading}>导出 ▾</Button>
                    </Dropdown>
                    <Dropdown
                      trigger={["click"]}
                      menu={{
                        items: [
                          { key: "upload", label: "上传案件文档" },
                          { key: "official-fee", label: "新增案件费用" },
                          { key: "internal-fee", label: "新增内部费用" },
                          { key: "batch-modify", label: "批量修改" },
                          { key: "authorization", label: "生成授权委托书" },
                          { key: "law-firm-letter", label: "生成律所函" },
                          { key: "identity", label: "生成身份证明" },
                          { key: "settlement", label: "生成结算提成表" },
                          { key: "tasks", label: "案件任务" },
                          { key: "logs", label: "案件日志" },
                        ],
                        onClick: ({ key }) => runSettlementMoreAction(key),
                      }}
                    >
                      <Button loading={settlementActionLoading}>
                        更多操作 ▾
                      </Button>
                    </Dropdown>
                  </Space>
                ) : (
                  <Space>
                    <Button
                      disabled={!selectedOriginalRows.length}
                      onClick={() => exportConfiguredRows(true)}
                    >
                      导出选中
                    </Button>
                    <Button onClick={() => exportConfiguredRows(false)}>
                      导出全部
                    </Button>
                  </Space>
                )}
                {!isInternalDetailRoute && !isInvoiceMineRoute && !isInvoicePendingRoute && !isInvoiceCompanyRoute && !isInvoiceUnissuedRoute && (
                  <span>已选择 {selectedOriginalRows.length} 条</span>
                )}
              </div>
            )}
          </section>
        ) : (
          <>
            {isRefundNotRequiredRoute && (
              <div className="finance-original-title">
                <h5>不再办理退费案件</h5>
              </div>
            )}
            <Alert
              className="finance-rule"
              type="info"
              showIcon
              title="费用审批要素"
              description="官方费用提交前必须具备案件人员、法院和缴费通知文档三要素；内部费用允许用负数冲销，金额按两位小数进位。审批通过后才能付款。"
            />
            <div className="finance-stats">
              <Card>
                <Statistic
                  title="费用总额"
                  value={
                    summary.amount_visible === false
                      ? "无权限"
                      : summary.total_fee_amount
                  }
                  formatter={(v) =>
                    typeof v === "number" ? money(v) : String(v)
                  }
                />
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
                  title="已审批"
                  value={summary.approved}
                  styles={{ content: { color: "#3c8dbc" } }}
                />
              </Card>
              <Card>
                <Statistic
                  title="付款金额"
                  value={
                    summary.amount_visible === false
                      ? "无权限"
                      : summary.paid_amount
                  }
                  formatter={(v) =>
                    typeof v === "number" ? money(v) : String(v)
                  }
                  styles={{ content: { color: "#00a65a" } }}
                />
              </Card>
              <Card>
                <Statistic
                  title="开票金额"
                  value={
                    summary.amount_visible === false
                      ? "无权限"
                      : summary.invoice_amount
                  }
                  formatter={(v) =>
                    typeof v === "number" ? money(v) : String(v)
                  }
                />
              </Card>
              <Card>
                <Statistic
                  title="退费金额"
                  value={
                    summary.amount_visible === false
                      ? "无权限"
                      : summary.refund_amount
                  }
                  formatter={(v) =>
                    typeof v === "number" ? money(v) : String(v)
                  }
                  styles={{ content: { color: "#dd4b39" } }}
                />
              </Card>
            </div>
            <Card
              className="panel"
              title="财务中心"
              extra={
                <Space>
                  {["fees", "audit"].includes(tab) && (
                    <RecordImportButton module="finance" onImported={load} />
                  )}
                  <Button icon={<ReloadOutlined />} onClick={load}>
                    刷新
                  </Button>
                  {tab === "receipts" && (
                    <Button
                      disabled={selectedIncomingRows.length !== 1}
                      onClick={() => {
                        const selected = incoming.find(
                          (row) => row.id === selectedIncomingRows[0],
                        );
                        if (!selected) {
                          message.warning("请选择一笔回款记录");
                          return;
                        }
                        setIncomingAllocationTarget(selected);
                      }}
                    >
                      已分配记录
                    </Button>
                  )}
                  {["fees", "audit"].includes(tab) && (
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={() => {
                        setFeeEditTarget(null);
                        feeForm.resetFields();
                        feeForm.setFieldsValue({
                          fee_type: "官方费用",
                          handler:
                            currentUser.displayName || "姓名待维护",
                        });
                        setFeeTypeOverride("官方费用");
                        setFeeOpen(true);
                      }}
                    >
                      新增费用
                    </Button>
                  )}
                  {tab === "receipts" && canManage && (
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={() => {
                        incomingForm.resetFields();
                        incomingForm.setFieldsValue({ received_date: dayjs() });
                        setIncomingOpen(true);
                      }}
                    >
                      登记银行到账
                    </Button>
                  )}
                  {tab === "invoices" && (
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={() => {
                        void (async () => {
                          try {
                            await loadInvoiceReferenceData();
                          } catch {
                            return;
                          }
                          setInvoiceEditTarget(null);
                          setInvoiceSourceFeeId(null);
                          setInvoiceSelectedFeeIds([]);
                          setInvoiceFeeAmounts({});
                          invoiceForm.resetFields();
                          invoiceForm.setFieldsValue({
                            invoice_type: "增值税普通发票",
                            invoice_content: "法律服务费",
                            delivery_method: "电子发票",
                          });
                          setInvoiceOpen(true);
                        })();
                      }}
                    >
                      发票申请
                    </Button>
                  )}
                  {tab === "refunds" && (
                    <>
                      <Select
                        aria-label="退款业务组筛选"
                        value={refundGroupFilter || undefined}
                        placeholder="全部业务组"
                        allowClear
                        options={[
                          { label: "律所", value: "lawfirm" },
                          { label: "商标", value: "trad" },
                        ]}
                        onChange={(value) => {
                          const nextGroup = value || "";
                          setRefundGroupFilter(nextGroup);
                          void loadRefunds(
                            1,
                            refundMeta.pageSize,
                            activeRefundStatus,
                            true,
                            nextGroup,
                          );
                        }}
                        style={{ minWidth: 130 }}
                      />
                      <Select
                        aria-label="退款状态筛选"
                        value={activeRefundStatus}
                        disabled={isRefundNotRequiredRoute}
                        options={refundStatusOptions.map((value) => ({
                          label: value,
                          value,
                        }))}
                        onChange={(value) => {
                          if (isRefundNotRequiredRoute) return;
                          setRefundStatusFilter(value);
                          void loadRefunds(
                            1,
                            refundMeta.pageSize,
                            value,
                            true,
                            refundGroupFilter,
                          );
                        }}
                        style={{ minWidth: 130 }}
                      />
                      <Button
                        onClick={() => {
                          setRefundStatusFilter(isRefundNotRequiredRoute ? "R100" : "全部");
                          setRefundGroupFilter("");
                          setSelectedRefundRows([]);
                          void loadRefunds(1, refundMeta.pageSize, refundStatusForRoute(initialView, ""), true, "");
                        }}
                      >
                        清空
                      </Button>
                      <Button onClick={() => void exportRefunds(false)}>
                        导出全部
                      </Button>
                      <Button
                        disabled={!selectedRefundRows.length}
                        onClick={() => void exportRefunds(true)}
                      >
                        导出选中
                      </Button>
                      <Button
                        onClick={() => {
                          if (!selectedRefundRows.length) {
                            message.warning("请选择需要修改退费进度的记录");
                            return;
                          }
                          setRefundBatchStatus("待审批");
                          setRefundBatchStatusOpen(true);
                        }}
                      >
                        退费进度修改
                      </Button>
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={() => {
                        refundForm.setFieldsValue({
                          applicant: currentUser.displayName || "姓名待维护",
                          reason: "诉讼费退费",
                        });
                        setRefundOpen(true);
                      }}
                    >
                      退款申请
                    </Button>
                    </>
                  )}
                  {tab === "reconcile" && canApprove && (
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={() => {
                        reconcileForm.setFieldsValue({
                          period_type: "周对账",
                          period: [
                            dayjs().startOf("week"),
                            dayjs().endOf("week"),
                          ],
                          discrepancy_amount: 0,
                        });
                        setReconcileOpen(true);
                      }}
                    >
                      生成对账单
                    </Button>
                  )}
                </Space>
              }
            >
              <Tabs
                activeKey={tab}
                onChange={setTab}
                items={[
                  { key: "legacy-history", label: "历史财务账本" },
                  { key: "fees", label: "费用管理" },
                  {
                    key: "audit",
                    label: `费用审批（${summary.pending || 0}）`,
                  },
                  {
                    key: "receipts",
                    label: `回款管理（待认领 ${summary.incoming_unclaimed || 0}）`,
                  },
                  {
                    key: "invoices",
                    label: `发票申请（${invoices.filter((x) => x.status === "待审批").length}）`,
                  },
                  {
                    key: "refunds",
                    label: `诉讼费退款（${refunds.filter((x) => x.status === "待审批").length}）`,
                  },
                  { key: "transactions", label: "财务流水" },
                  { key: "reconcile", label: "周/月对账" },
                ]}
              />
              {["fees", "audit"].includes(tab) ? (
                <Table
                  rowKey="id"
                  loading={loading}
                  size="small"
                  columns={feeColumns}
                  dataSource={shownFees}
                  scroll={{ x: 1500 }}
                />
              ) : tab === "receipts" ? (
                <Table
                  rowKey="id"
                  loading={loading}
                  size="small"
                  columns={incomingColumns}
                  dataSource={shownIncoming}
                  scroll={{ x: 1700 }}
                  rowSelection={{
                    selectedRowKeys: selectedIncomingRows,
                    onChange: (keys) => setSelectedIncomingRows(keys as number[]),
                  }}
                />
              ) : tab === "invoices" ? (
                <Table
                  rowKey="id"
                  loading={loading}
                  size="small"
                  columns={invoiceColumns}
                  dataSource={shownInvoices}
                  scroll={{ x: 1650 }}
                />
              ) : tab === "refunds" ? (
                <Table
                  rowKey="id"
                  loading={loading}
                  size="small"
                  columns={refundColumns}
                  dataSource={refunds}
                  rowSelection={{
                    selectedRowKeys: selectedRefundRows,
                    onChange: (keys) => setSelectedRefundRows(keys as number[]),
                  }}
                  pagination={{
                    current: refundMeta.page,
                    pageSize: refundMeta.pageSize,
                    total: refundMeta.total,
                    showSizeChanger: true,
                    pageSizeOptions: refundPageSizeOptions,
                    onShowSizeChange: (_current, size) => {
                      if (isRefundNotRequiredRoute) {
                        void loadRefunds(1, size, activeRefundStatus, true, refundGroupFilter);
                      } else {
                        void loadRefunds(1, size, refundStatusFilter, true, refundGroupFilter);
                      }
                    },
                    onChange: (page, size) => {
                      if (isRefundNotRequiredRoute) {
                        void loadRefunds(page, size, activeRefundStatus, true, refundGroupFilter);
                      } else {
                        void loadRefunds(page, size, refundStatusFilter, true, refundGroupFilter);
                      }
                    },
                  }}
                  scroll={{ x: 1700 }}
                />
              ) : tab === "transactions" ? (
                <Table
                  rowKey="id"
                  loading={loading}
                  size="small"
                  columns={transactionColumns}
                  dataSource={transactions}
                  scroll={{ x: 1500 }}
                />
              ) : tab === "legacy-history" ? (
                <>
                  <Alert
                    className="finance-rule"
                    type="info"
                    showIcon
                    title="历史财务账本"
                    description="历史请款、回款、开票及付款打包与实时财务口径完全分离；仅可检索和查看原始迁移信息。"
                  />
                  <div className="finance-stats">
                    {(["ap_payment", "ar_payment", "invoice", "ap_packing", "case_fee"] as LegacyFinanceRecord["record_kind"][]).map((kind) => {
                      const item = legacyFinanceSummaryByKind(kind);
                      return (
                        <Card key={kind} size="small">
                          <Statistic
                            title={legacyFinanceKindLabel[kind]}
                            value={legacyFinanceSummary.amount_visible ? item.amount : item.count}
                            suffix={legacyFinanceSummary.amount_visible ? "元" : "条"}
                            formatter={(value) => legacyFinanceSummary.amount_visible ? money(Number(value || 0)) : String(value)}
                          />
                          <div className="finance-stat-caption">{item.count.toLocaleString("zh-CN")} 条记录</div>
                        </Card>
                      );
                    })}
                    {(legacyFinanceSummary.orphan_allocations.length || legacyFinanceSummary.orphan_files.length || legacyFinanceSummary.orphan_audits.length) ? (
                      <Card size="small">
                        <Statistic
                          title="孤儿历史引用"
                          value={legacyFinanceSummary.orphan_allocations.reduce((sum, item) => sum + Number(item.count || 0), 0) + legacyFinanceSummary.orphan_files.reduce((sum, item) => sum + Number(item.count || 0), 0) + legacyFinanceSummary.orphan_audits.reduce((sum, item) => sum + Number(item.count || 0), 0)}
                          suffix="条"
                        />
                        <div className="finance-stat-caption">父记录在旧库快照中缺失，已保留来源信息</div>
                      </Card>
                    ) : null}
                  </div>
                  <Space wrap style={{ margin: "8px 0 12px" }}>
                    <Input.Search
                      aria-label="历史财务账本检索"
                      placeholder="历史编号、合同、案件或客户编号"
                      value={legacyFinanceKeyword}
                      onChange={(event) => setLegacyFinanceKeyword(event.target.value)}
                      onSearch={() => void loadLegacyFinanceHistory(1, legacyFinanceMeta.pageSize)}
                      style={{ width: 250 }}
                    />
                    <Input
                      aria-label="旧库状态码"
                      placeholder="旧库状态码"
                      value={legacyFinanceStatusCode}
                      onChange={(event) => setLegacyFinanceStatusCode(event.target.value)}
                      onPressEnter={() => void loadLegacyFinanceHistory(1, legacyFinanceMeta.pageSize)}
                      style={{ width: 118 }}
                    />
                    <Select
                      aria-label="历史财务账本类型"
                      value={legacyFinanceKind || undefined}
                      placeholder="全部账本类型"
                      allowClear
                      options={(["ap_payment", "ar_payment", "invoice", "ap_packing", "case_fee"] as LegacyFinanceRecord["record_kind"][]).map((kind) => ({ value: kind, label: legacyFinanceKindLabel[kind] }))}
                      onChange={(value) => setLegacyFinanceKind(value || "")}
                      style={{ width: 150 }}
                    />
                    <Checkbox checked={legacyFinanceIncludeInactive} onChange={(event) => setLegacyFinanceIncludeInactive(event.target.checked)}>显示已停用</Checkbox>
                    <Button icon={<ReloadOutlined />} onClick={() => void loadLegacyFinanceHistory()}>刷新</Button>
                    <Tag color="default">只读</Tag>
                    {legacyFinanceSummary.amount_visible === false && <Tag color="orange">金额无查看权限</Tag>}
                  </Space>
                  <Table
                    rowKey="id"
                    loading={legacyFinanceLoading}
                    size="small"
                    columns={legacyFinanceColumns}
                    dataSource={legacyFinanceRows}
                    pagination={{
                      current: legacyFinanceMeta.page,
                      pageSize: legacyFinanceMeta.pageSize,
                      total: legacyFinanceMeta.total,
                      showSizeChanger: true,
                      pageSizeOptions: [30, 50, 100, 200],
                      onChange: (page, pageSize) => void loadLegacyFinanceHistory(page, pageSize),
                    }}
                    scroll={{ x: 1550 }}
                  />
                </>
              ) : (
                <Table
                  rowKey="id"
                  loading={loading}
                  size="small"
                  columns={reconcileColumns}
                  dataSource={reconciliations}
                  scroll={{ x: 1150 }}
                />
              )}
            </Card>
          </>
        ))}
      <Drawer
        open={legacyFinanceDetailLoading || Boolean(legacyFinanceDetail)}
        title="历史财务账本明细"
        width={760}
        placement="right"
        onClose={() => {
          setLegacyFinanceDetail(null);
          setLegacyFinanceDetailLoading(false);
        }}
        footer={<Tag color="default">只读历史镜像</Tag>}
      >
        {legacyFinanceDetailLoading ? (
          <div className="finance-empty">正在加载历史财务明细...</div>
        ) : legacyFinanceDetail ? (
          <>
            <Alert
              type={/parent_not_present|orphan|missing_parent/i.test(String(legacyFinanceDetail.mapping_status || "")) ? "warning" : "info"}
              showIcon
              title={legacyFinanceMappingLabel(legacyFinanceDetail.mapping_status)}
              description="此记录来自旧 FAM 数据迁移，仅用于审计追溯，不参与实时财务汇总或业务操作。"
            />
            <Descriptions column={2} size="small" bordered style={{ marginTop: 12 }}>
              <Descriptions.Item label="历史编号">{legacyFinanceDetail.legacy_id || `#${legacyFinanceDetail.id}`}</Descriptions.Item>
              <Descriptions.Item label="账本类型">{legacyFinanceKindLabel[legacyFinanceDetail.record_kind]}</Descriptions.Item>
              <Descriptions.Item label="状态">{legacyFinanceStatusLabel(legacyFinanceDetail.status_label)}</Descriptions.Item>
              <Descriptions.Item label="金额">{legacyFinanceAmount(legacyFinanceDetail.primary_amount)}</Descriptions.Item>
              <Descriptions.Item label="合同编号">{legacyFinanceDetail.legacy_contract_no || "—"}</Descriptions.Item>
              <Descriptions.Item label="案件编号">{legacyFinanceDetail.legacy_case_no || "—"}</Descriptions.Item>
              <Descriptions.Item label="客户编号">{legacyFinanceDetail.legacy_customer_no || "—"}</Descriptions.Item>
              <Descriptions.Item label="来源表">{legacyFinanceDetail.source_table || "—"}</Descriptions.Item>
              <Descriptions.Item label="关联状态">{legacyFinanceMappingLabel(legacyFinanceDetail.mapping_status)}</Descriptions.Item>
              <Descriptions.Item label="导入时间">{legacyFinanceDetail.imported_at ? dayjs(legacyFinanceDetail.imported_at).format("YYYY-MM-DD HH:mm") : "—"}</Descriptions.Item>
              <Descriptions.Item label="币种来源">{legacyFinanceDetail.currency === "UNRECORDED_IN_LEGACY_SCHEMA" ? "旧库未记录" : (legacyFinanceDetail.currency || "旧库未记录")}</Descriptions.Item>
              <Descriptions.Item label="审批记录数">{legacyFinanceDetail.audit_count || 0}</Descriptions.Item>
            </Descriptions>
            <Tabs
              style={{ marginTop: 14 }}
              items={[
                {
                  key: "allocations",
                  label: `分配行（${legacyFinanceDetail.allocations?.length || 0}）`,
                  children: <Table size="small" rowKey="id" pagination={false} dataSource={legacyFinanceDetail.allocations || []} columns={[
                    { title: "来源键", dataIndex: "legacy_key", width: 120 },
                    { title: "类型", dataIndex: "allocation_kind", width: 100 },
                    { title: "案件编号", dataIndex: "legacy_case_no", width: 140, render: (value: string) => value || "—" },
                    { title: "金额", dataIndex: "amount", align: "right" as const, width: 110, render: legacyFinanceAmount },
                    { title: "关联状态", dataIndex: "mapping_status", width: 130, render: (value: string) => legacyFinanceMappingLabel(value) },
                  ]} scroll={{ x: 620 }} />,
                },
                {
                  key: "files",
                  label: `发票文件（${legacyFinanceDetail.files?.length || 0}）`,
                  children: <Table size="small" rowKey="id" pagination={false} dataSource={legacyFinanceDetail.files || []} columns={[
                    { title: "文件名", dataIndex: "filename", render: (value: string) => value || "未保留文件名" },
                    { title: "大小", dataIndex: "size_bytes", width: 100, render: (value: number) => value ? `${Math.ceil(Number(value) / 1024)} KB` : "—" },
                    { title: "物理文件", dataIndex: "physical_file_verified", width: 100, render: (value: boolean) => <Tag color={value ? "green" : "orange"}>{value ? "已验证" : "仅元数据"}</Tag> },
                    { title: "开票日期", dataIndex: "invoice_date", width: 110, render: (value: string) => value || "—" },
                  ]} scroll={{ x: 620 }} />,
                },
                {
                  key: "legacy-fields",
                  label: "旧库原始金额与状态",
                  children: <Descriptions column={2} size="small" bordered>
                    {Object.entries(legacyFinanceDetail.legacy_statuses || {}).map(([key, value]) => <Descriptions.Item key={`status-${key}`} label={key}>{String(value ?? "")}</Descriptions.Item>)}
                    {Object.entries(legacyFinanceDetail.legacy_amounts || {}).map(([key, value]) => <Descriptions.Item key={`amount-${key}`} label={key}>{String(value ?? "")}</Descriptions.Item>)}
                  </Descriptions>,
                },
                {
                  key: "audits",
                  label: `审批历史（${legacyFinanceDetail.audits?.length || 0}）`,
                  children: <Table size="small" rowKey="id" pagination={false} dataSource={legacyFinanceDetail.audits || []} columns={[
                    { title: "审批编号", dataIndex: "legacy_id", width: 92 },
                    { title: "状态码", dataIndex: "audit_status_code", width: 70 },
                    { title: "流程", dataIndex: "audit_flow_id", width: 70 },
                    { title: "节点", dataIndex: "audit_flow_node_id", width: 70 },
                    { title: "轮次", dataIndex: "audit_round_id", width: 70 },
                    { title: "审批人", dataIndex: "auditor_display_name", width: 100, render: (value: string) => value || "—" },
                    { title: "审批时间", dataIndex: "audit_date", width: 160, render: (value: string) => value ? dayjs(value).format("YYYY-MM-DD HH:mm") : "-" },
                    { title: "审批意见", dataIndex: "audit_content", width: 220, render: (value: string) => value || "-" },
                  ]} scroll={{ x: 900 }} />,
                },
                {
                  key: "payload",
                  label: "源数据",
                  children: <pre className="finance-source-payload">{JSON.stringify(legacyFinanceDetail.source_payload || {}, null, 2)}</pre>,
                },
              ]}
            />
          </>
        ) : null}
      </Drawer>
      <Drawer
        open={Boolean(feeReviewTargets.length)}
        title={<h5>{initialView === "finance-payment-audit" ? "付款审批" : "提成审批"}</h5>}
        width={580}
        placement="right"
        mask={false}
        closable={{ placement: "end" }}
        rootClassName="finance-review-drawer"
        onClose={() => {
          setFeeReviewTargets([]);
          setFeeReviewComment("");
        }}
        footer={
          <Button
            onClick={() => {
              setFeeReviewTargets([]);
              setFeeReviewComment("");
            }}
          >
            取消
          </Button>
        }
      >
        <Input.TextArea
          aria-label="审批意见"
          placeholder="审批意见"
          value={feeReviewComment}
          onChange={(event) => setFeeReviewComment(event.target.value)}
          rows={2}
        />
        <Space className="finance-review-actions">
          <Button
            type="primary"
            loading={feeReviewLoading}
            onClick={() => void submitFeeReview(true)}
          >
            同意
          </Button>
          <Button
            danger
            loading={feeReviewLoading}
            onClick={() => void submitFeeReview(false)}
          >
            拒绝
          </Button>
        </Space>
        <Table
          rowKey="key"
          size="small"
          pagination={false}
          tableLayout="fixed"
          columns={initialView === "finance-payment-audit" ? [
            {
              title: "案号",
              dataIndex: "case_no",
              width: 100,
              render: (value) => value ? <Button type="link" onClick={() => openCaseDetail(value)}>{value}</Button> : "—",
            },
            { title: "原告", dataIndex: "plaintiff", width: 100 },
            { title: "金额", dataIndex: "amount", width: 80, render: reviewNumber },
            { title: "费用类型", dataIndex: "fee_type", width: 90 },
            { title: "付款备注", dataIndex: "payment_remark", width: 120 },
          ] : [
            {
              title: "案号",
              dataIndex: "case_no",
              width: 88,
              render: (value) => value ? <Button type="link" onClick={() => openCaseDetail(value)}>{value}</Button> : "—",
            },
            {
              title: (
                <span className="finance-stacked-header">
                  <span>提成</span>
                  <span>类型</span>
                </span>
              ),
              dataIndex: "commission_type",
              width: 54,
              render: (value) => value || "—",
            },
            {
              title: (
                <span className="finance-stacked-header">
                  <span>支付</span>
                  <span>对象</span>
                </span>
              ),
              dataIndex: "payee",
              width: 54,
              render: (value) => value || "—",
            },
            {
              title: "基数",
              dataIndex: "base_amount",
              width: 54,
              render: reviewNumber,
            },
            {
              title: (
                <span className="finance-stacked-header">
                  <span>基数</span>
                  <span>提成</span>
                </span>
              ),
              dataIndex: "base_commission",
              width: 54,
              render: reviewNumber,
            },
            {
              title: (
                <span className="finance-stacked-header">
                  <span>实际</span>
                  <span>提成</span>
                </span>
              ),
              dataIndex: "actual_commission",
              width: 54,
              render: reviewNumber,
            },
            {
              title: (
                <span className="finance-stacked-header">
                  <span>已付</span>
                  <span>调查费</span>
                </span>
              ),
              dataIndex: "paid_investigation",
              width: 47,
              render: reviewNumber,
            },
            {
              title: (
                <span className="finance-stacked-header">
                  <span>已付</span>
                  <span>案源费</span>
                </span>
              ),
              dataIndex: "paid_source",
              width: 47,
              render: reviewNumber,
            },
            {
              title: (
                <span className="finance-stacked-header">
                  <span>已付</span>
                  <span>文书费</span>
                </span>
              ),
              dataIndex: "paid_document",
              width: 47,
              render: reviewNumber,
            },
            {
              title: (
                <span className="finance-stacked-header">
                  <span>已付</span>
                  <span>开庭费</span>
                </span>
              ),
              dataIndex: "paid_hearing",
              width: 47,
              render: reviewNumber,
            },
          ]}
          dataSource={(initialView === "finance-payment-audit" ? paymentReviewRows : feeReviewRows) as any}
        />
      </Drawer>
      <Drawer
        open={refundBatchFeeOpen}
        title={refundBatchFeeKind === "internal" ? "新增内部费用" : "新增费用"}
        width="min(1000px, 95vw)"
        onClose={closeRefundBatchFee}
        destroyOnHidden
        footer={
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <Button onClick={closeRefundBatchFee}>取消</Button>
            {refundBatchFeeStep === 1 && <Button onClick={() => setRefundBatchFeeStep(0)}>上一步</Button>}
            {refundBatchFeeStep === 0 ? (
              <Button type="primary" onClick={async () => {
                await refundBatchFeeForm.validateFields();
                setRefundBatchFeeStep(1);
              }}>下一步</Button>
            ) : (
              <Button type="primary" loading={refundBatchFeeLoading} onClick={() => void submitRefundBatchFee()}>
                {refundBatchFeeBaseType === "代理费" ? "保存费用" : "申请付款"}
              </Button>
            )}
          </div>
        }
      >
        <Steps
          size="small"
          current={refundBatchFeeStep}
          items={[{ title: "新增费用" }, { title: "申请付款" }]}
          style={{ marginBottom: 16 }}
        />
        <Form form={refundBatchFeeForm} layout="vertical">
          <Form.Item name="handler" hidden><Input /></Form.Item>
          {refundBatchFeeStep === 0 ? (
            <>
            <Alert
              type="info"
              showIcon
              style={{ marginBottom: 12 }}
              description={
                refundBatchFeeKind === "internal" ? (
                  <>
                    <p style={{ margin: 0 }}>1. 申请付款按照每个案号生成一个申请单。</p>
                    <p style={{ margin: "2px 0 0" }}>2. 点击表格头部（费用类型，基数，实际金额，备注）会把第一行数据同步到各行。</p>
                    <p style={{ margin: "2px 0 0" }}>3. 基数用于计算提成的分母数，点击基数会把第一行数据同步到各行，同时自动计算提成。</p>
                  </>
                ) : (
                  <>
                    <p style={{ margin: 0 }}>1. 同一付款单位可以申请付款，否则请按实际业务进行操作。</p>
                    <p style={{ margin: "2px 0 0" }}>2. 申请付款按照每个合同号生成一个申请单。</p>
                    <p style={{ margin: "2px 0 0" }}>3. 点击表格头部（费用类型，金额，备注，截止日期）会把第一行数据同步到各行。</p>
                    <p style={{ margin: "2px 0 0" }}>4. 截止日期默认为申请之日第5天，如有特殊情况，在申请时自行修改。</p>
                  </>
                )
              }
            />
              <Form.List name="items">
                {(fields, { add, remove }) => (
                  <div className={`finance-refund-batch-fee-table ${refundBatchFeeKind === "internal" ? "is-internal" : "is-ordinary"}`}>
                    <div className="finance-refund-batch-fee-head">
                      {refundBatchFeeKind === "internal" ? (
                        <>
                          <span>案号</span>
                          <span><a style={{ color: "inherit", cursor: "pointer" }} onClick={() => syncFirstRefundFeeField("fee_type_id")}>费用类型</a></span>
                          <span>支付对象</span>
                          <span><a style={{ color: "inherit", cursor: "pointer" }} onClick={() => syncFirstRefundFeeField("base_amount")}>基数</a></span>
                          <span>参考提成</span>
                          <span><a style={{ color: "inherit", cursor: "pointer" }} onClick={() => syncFirstRefundFeeField("amount")}>实际金额</a></span>
                          <span><a style={{ color: "inherit", cursor: "pointer" }} onClick={() => syncFirstRefundFeeField("remark")}>备注</a></span>
                          <span>操作</span>
                        </>
                      ) : (
                        <>
                          <span>案号</span>
                          <span>合同号</span>
                          <span><a style={{ color: "inherit", cursor: "pointer" }} onClick={() => syncFirstRefundFeeField("fee_type_id")}>费用类型</a></span>
                          <span><a style={{ color: "inherit", cursor: "pointer" }} onClick={() => syncFirstRefundFeeField("amount")}>金额</a></span>
                          <span><a style={{ color: "inherit", cursor: "pointer" }} onClick={() => syncFirstRefundFeeField("remark")}>备注</a></span>
                          <span><a style={{ color: "inherit", cursor: "pointer" }} onClick={() => syncFirstRefundFeeField("deadline")}>截止日期</a></span>
                          <span>操作</span>
                        </>
                      )}
                    </div>
                    {fields.map((field) => {
                      const row = refundBatchFeeForm.getFieldValue(["items", field.name]) || {};
                      const contractOptions = contracts
                        .filter((contract) => contract.customer === row.customer)
                        .map((contract) => ({ value: contract.id, label: contract.serial_no }));
                      return (
                        <div className="finance-refund-batch-fee-row" key={field.key}>
                          <div className="finance-refund-batch-fee-case">
                            <strong>{row.case_no}</strong><small>{row.customer}</small>
                            <Form.Item name={[field.name, "case_id"]} hidden><Input /></Form.Item>
                            <Form.Item name={[field.name, "case_no"]} hidden><Input /></Form.Item>
                            <Form.Item name={[field.name, "customer"]} hidden><Input /></Form.Item>
                          </div>
                          {refundBatchFeeKind === "ordinary" && <Form.Item name={[field.name, "contract_record_id"]} rules={[{ required: true, message: "请选择合同" }]}>
                              <Select showSearch optionFilterProp="label" options={contractOptions} placeholder="请选择" />
                            </Form.Item>}
                          <Form.Item name={[field.name, "fee_type_id"]} rules={[{ required: true, message: "请选择费用类型" }]}>
                            <Select
                              showSearch
                              optionFilterProp="label"
                              placeholder="请选择"
                              options={(refundBatchFeeSubTypes.length
                                ? refundBatchFeeSubTypes.map((item: any) => ({ value: item.id, label: item.name }))
                                : [{ value: refundBatchFeeBaseType, label: refundBatchFeeBaseType, disabled: true }]) as any[]}
                              onChange={(_value, option: any) => {
                                refundBatchFeeForm.setFieldValue(
                                  [field.name, "fee_type_name"],
                                  option?.label || "",
                                );
                              }}
                            />
                          </Form.Item>
                          <Form.Item name={[field.name, "fee_type"]} hidden><Input /></Form.Item>
                          {refundBatchFeeKind === "internal" ? <>
                            <Form.Item name={[field.name, "payee_username"]} rules={[{ required: true, message: "请选择支付对象" }]}>
                              <Select showSearch optionFilterProp="label" options={financePeople.map((person) => ({ value: person.username, label: person.label }))} />
                            </Form.Item>
                            <Form.Item name={[field.name, "base_amount"]} rules={[{ required: true, message: "请输入基数" }]}><InputNumber min={0} precision={2} style={{ width: "100%" }} /></Form.Item>
                            <Form.Item name={[field.name, "reference_commission"]} rules={[{ required: true, message: "请输入参考提成" }]}><InputNumber min={0} precision={2} style={{ width: "100%" }} /></Form.Item>
                          </> : null}
                          <Form.Item name={[field.name, "amount"]} rules={[{ required: true, message: "请输入金额" }, { validator: (_, value) => value === 0 ? Promise.reject(new Error("金额不能为0")) : Promise.resolve() }]}>
                            <InputNumber precision={2} style={{ width: "100%" }} />
                          </Form.Item>
                          <Form.Item name={[field.name, "remark"]}><Input placeholder="备注" /></Form.Item>
                          {refundBatchFeeKind === "ordinary" && <Form.Item name={[field.name, "deadline"]} rules={[{ required: true, message: "请选择截止日期" }]}><DatePicker style={{ width: "100%" }} /></Form.Item>}
                          <Space size={2}>
                            <Button type="text" aria-label="复制费用行" icon={<PlusOutlined />} onClick={() => add({ ...row, amount: undefined, remark: "" }, field.name + 1)} />
                            <Button type="text" danger aria-label="删除费用行" icon={<MinusCircleOutlined />} disabled={fields.length === 1} onClick={() => remove(field.name)} />
                          </Space>
                        </div>
                      );
                    })}
                  </div>
                )}
              </Form.List>
            </>
          ) : (
            <>
              <Alert type="info" showIcon title={refundBatchFeeBaseType === "代理费" ? "代理费不允许申请付款，本次仅保存费用。" : "同一收款单位可批量申请；系统按每个合同号分别形成付款申请。"} style={{ marginBottom: 12 }} />
              <Form.List name="items">
                {(fields) => <div className="finance-refund-payment-table">
                  <div className="finance-refund-payment-head"><span>案号</span><span>费用类型</span><span>付款金额</span><span>付款备注</span><span>收款单位/支付对象</span></div>
                  {fields.map((field) => {
                    const row = refundBatchFeeForm.getFieldValue(["items", field.name]) || {};
                    const agency = refundBatchFeeBaseType === "代理费";
                    return <div className="finance-refund-payment-row" key={field.key}>
                      <strong>{row.case_no}</strong><span>{row.fee_type_name || row.fee_type}</span>
                      <Form.Item name={[field.name, "payment_amount"]} initialValue={Math.abs(Number(row.amount || 0))} rules={agency ? [] : [{ required: true, message: "请输入付款金额" }]}><InputNumber disabled={agency} min={0.01} precision={2} style={{ width: "100%" }} /></Form.Item>
                      <Form.Item name={[field.name, "payment_remark"]}><Input disabled={agency} /></Form.Item>
                      {refundBatchFeeKind === "internal" ? <Form.Item name={[field.name, "payee_username"]} rules={[{ required: true, message: "请选择支付对象" }]}><Select disabled options={financePeople.map((person) => ({ value: person.username, label: person.label }))} /></Form.Item> : <Form.Item name={[field.name, "payment_type_id"]} rules={agency ? [] : [{ required: true, message: "请选择收款单位" }]}><Select disabled={agency} showSearch optionFilterProp="label" options={refundBatchPaymentTypes.map((item) => ({ value: item.id, label: `${item.payee}｜${item.account_bank}｜${item.account}` }))} /></Form.Item>}
                    </div>;
                  })}
                </div>}
              </Form.List>
            </>
          )}
        </Form>
      </Drawer>
      <Modal
        width={640}
        open={settlementBatchOpen}
        title="批量修改案件信息"
        okText="保存修改"
        cancelText="取消"
        confirmLoading={settlementActionLoading}
        onOk={submitSettlementBatch}
        onCancel={() => setSettlementBatchOpen(false)}
        destroyOnHidden
      >
        <Alert
          type="info"
          showIcon
          title={`将修改已选费用关联的 ${selectedSettlementCases().length} 个案件（仅填写的字段会被修改）`}
          style={{ marginBottom: 16 }}
        />
        <Form form={settlementBatchForm} layout="vertical">
          <div className="form-grid">
            <Form.Item label="开庭律师" name="hearing_lawyer">
              <Select
                showSearch
                optionFilterProp="label"
                allowClear
                placeholder="不修改请留空"
                options={financePeople.map((person) => ({ value: person.username, label: person.label }))}
              />
            </Form.Item>
            <Form.Item label="律师助理" name="assistant">
              <Select
                showSearch
                optionFilterProp="label"
                allowClear
                placeholder="不修改请留空"
                options={financePeople.map((person) => ({ value: person.username, label: person.label }))}
              />
            </Form.Item>
          </div>
          <Form.Item label="经办律师（多人用逗号分隔）" name="handling_lawyers">
            <Input placeholder="不修改请留空，例如：张律师，李律师" />
          </Form.Item>
          <Form.Item label="案源人" name="source_lawyer">
            <Select
              showSearch
              optionFilterProp="label"
              allowClear
              placeholder="不修改请留空"
              options={financePeople.map((person) => ({ value: person.username, label: person.label }))}
            />
          </Form.Item>
          <div className="form-grid">
            <Form.Item label="诉讼标的（元）" name="litigation_amount">
              <InputNumber min={0} precision={2} style={{ width: "100%" }} placeholder="不修改请留空" />
            </Form.Item>
            <Form.Item label="案件阶段" name="case_stage">
              <Input placeholder="不修改请留空" />
            </Form.Item>
          </div>
          <Form.Item label="修改说明" name="comment">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        width={900}
        open={Boolean(settlementContext)}
        title={
          settlementContext?.mode === "log-create"
            ? `新增案件日志（${settlementContext?.caseRecords.length || 0} 个案件）`
            : settlementContext?.mode === "task-create"
              ? `新增案件任务（${settlementContext?.caseRecords.length || 0} 个案件）`
              : `已选 ${settlementContext?.caseRecords.length || 0} 个案件｜${settlementContext?.mode === "tasks" ? "案件任务" : "案件日志"}`
        }
        footer={
          settlementContext?.mode === "log-create" ? (
            <>
              <Button onClick={() => setSettlementContext(null)}>取消</Button>
              <Button type="primary" loading={settlementActionLoading} onClick={() => void submitSettlementLog()}>保存日志</Button>
            </>
          ) : settlementContext?.mode === "task-create" ? (
            <>
              <Button onClick={() => setSettlementContext(null)}>取消</Button>
              <Button type="primary" loading={settlementActionLoading} onClick={() => void submitSettlementTask()}>创建任务</Button>
            </>
          ) : (
            <Button onClick={() => setSettlementContext(null)}>关闭</Button>
          )
        }
        onCancel={() => setSettlementContext(null)}
        destroyOnHidden
      >
        {settlementContext?.mode === "log-create" ? (
          <div>
            <Alert
              type="info"
              showIcon
              message={`将为以下 ${settlementContext?.caseRecords.length || 0} 个案件添加相同的日志：`}
              description={
                <div style={{ maxHeight: 120, overflowY: "auto", marginTop: 8 }}>
                  {(settlementContext?.caseRecords || []).map((row: Fee) => (
                    <div key={row.id} style={{ fontSize: 12, lineHeight: "20px" }}>
                      {row.data?.case_no || row.serial_no}
                    </div>
                  ))}
                </div>
              }
              style={{ marginBottom: 16 }}
            />
            <Input.TextArea
              rows={8}
              value={settlementLogContent}
              onChange={(e) => setSettlementLogContent(e.target.value)}
              placeholder="请输入日志内容..."
            />
          </div>
        ) : settlementContext?.mode === "task-create" ? (
          <div>
            <Alert
              type="info"
              showIcon
              message={`将为以下 ${settlementContext?.caseRecords.length || 0} 个案件创建相同的任务：`}
              description={
                <div style={{ maxHeight: 120, overflowY: "auto", marginTop: 8 }}>
                  {(settlementContext?.caseRecords || []).map((row: Fee) => (
                    <div key={row.id} style={{ fontSize: 12, lineHeight: "20px" }}>
                      {row.data?.case_no || row.serial_no}
                    </div>
                  ))}
                </div>
              }
              style={{ marginBottom: 16 }}
            />
            <Form layout="vertical">
              <Form.Item label="任务名称" required>
                <Input
                  value={settlementTaskForm.title}
                  onChange={(e) => setSettlementTaskForm({ ...settlementTaskForm, title: e.target.value })}
                  placeholder="请输入任务名称"
                />
              </Form.Item>
              <div className="form-grid">
                <Form.Item label="负责人" required>
                  <Select
                    showSearch
                    optionFilterProp="label"
                    value={settlementTaskForm.owner || undefined}
                    onChange={(val) => setSettlementTaskForm({ ...settlementTaskForm, owner: val })}
                    placeholder="请选择负责人"
                    options={financePeople.map((person) => ({ value: person.username, label: person.label }))}
                  />
                </Form.Item>
                <Form.Item label="优先级">
                  <Select
                    value={settlementTaskForm.priority}
                    onChange={(val) => setSettlementTaskForm({ ...settlementTaskForm, priority: val })}
                    options={[
                      { value: "紧急", label: "紧急" },
                      { value: "高", label: "高" },
                      { value: "普通", label: "普通" },
                      { value: "低", label: "低" },
                    ]}
                  />
                </Form.Item>
              </div>
              <Form.Item label="截止日期" required>
                <DatePicker
                  style={{ width: "100%" }}
                  value={settlementTaskForm.deadline}
                  onChange={(val) => setSettlementTaskForm({ ...settlementTaskForm, deadline: val })}
                />
              </Form.Item>
            </Form>
          </div>
        ) : (
          <Table
            rowKey="id"
            size="small"
            dataSource={settlementContextRows}
            pagination={{ pageSize: 10, showTotal: (total) => `共 ${total} 条` }}
            locale={{
              emptyText:
                settlementContext?.mode === "tasks"
                  ? "当前案件没有任务"
                  : "当前案件没有日志",
            }}
            columns={
              settlementContext?.mode === "tasks"
                ? [
                    { title: "案号", dataIndex: "source_case_no", width: 150 },
                    { title: "任务编号", dataIndex: "serial_no", width: 150 },
                    { title: "任务名称", dataIndex: "title", width: 200 },
                    { title: "状态", dataIndex: "status", width: 90 },
                    { title: "负责人", dataIndex: "owner", width: 100, render: (value: string, row: any) => financePersonDisplayName(value, row.owner_display_name) },
                    { title: "截止日期", dataIndex: "deadline", width: 120 },
                  ]
                : [
                    { title: "案号", dataIndex: "source_case_no", width: 150 },
                    { title: "操作", dataIndex: "action", width: 130 },
                    {
                      title: "状态变化",
                      key: "status",
                      width: 150,
                      render: (_: unknown, row: any) =>
                        `${row.from_status || "—"} → ${row.to_status || "—"}`,
                    },
                    { title: "操作人", dataIndex: "operator", width: 100, render: (value: string, row: any) => financePersonDisplayName(value, row.operator_display_name) },
                    { title: "说明", dataIndex: "comment" },
                    {
                      title: "时间",
                      dataIndex: "created_at",
                      width: 170,
                      render: (value: string) =>
                        value ? dayjs(value).format("YYYY-MM-DD HH:mm") : "—",
                    },
                  ]
            }
          />
        )}
      </Modal>
      <Modal
        open={incomingOpen}
        title="登记银行到账"
        okText="保存为待认领"
        cancelText="取消"
        onOk={createIncoming}
        onCancel={() => setIncomingOpen(false)}
      >
        <Alert
          type="info"
          showIcon
          title="银行到账先登记为待认领，不能直接计入合同或案件。"
          style={{ marginBottom: 16 }}
        />
        <Form form={incomingForm} layout="vertical">
          <div className="form-grid">
            <Form.Item
              label="到账日期"
              name="received_date"
              rules={[{ required: true }]}
            >
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item
              label="到账金额"
              name="amount"
              rules={[{ required: true }]}
            >
              <InputNumber min={0.01} precision={2} style={{ width: "100%" }} />
            </Form.Item>
          </div>
          <Form.Item
            label="付款单位/账户名"
            name="payer_name"
            rules={[{ required: true, min: 2 }]}
          >
            <AutoComplete
              allowClear
              placeholder="输入回款单位，或从系统客户中选择"
              options={customers.map((customer) => ({
                value: customer.title,
                label: customer.serial_no
                  ? `${customer.title}｜${customer.serial_no}`
                  : customer.title,
              }))}
              filterOption={(inputValue, option) =>
                String(option?.label || "")
                  .toLowerCase()
                  .includes(inputValue.trim().toLowerCase())
              }
            />
          </Form.Item>
          <Form.Item
            label="银行流水号"
            name="bank_reference"
            rules={[{ required: true, min: 2 }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label="银行摘要/备注" name="remark">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        width={760}
        rootClassName="finance-claim-modal"
        open={Boolean(claimTarget)}
        title="回款领取"
        okText="领取"
        cancelText="取消"
        onOk={claimIncoming}
        onCancel={() => {
          setClaimTarget(null);
          claimForm.resetFields();
        }}
      >
        <div className="finance-claim-tip">
          温馨提示：请根据回款单位匹配系统客户，认领前核对流水号、金额和银行单号。
        </div>
        <Form form={claimForm} layout="horizontal" labelCol={{ span: 5 }} wrapperCol={{ span: 17 }}>
          <Form.Item label="回款流水号">
            <Input value={claimTarget?.receipt_no || ""} readOnly />
          </Form.Item>
          <Form.Item label="回款单位">
            <Input value={claimTarget?.payer_name || ""} readOnly />
          </Form.Item>
          <Form.Item
            label="客户名称"
            name="customer"
            rules={[{ required: true, message: "请选择系统客户" }]}
          >
            <Select
              showSearch
              filterOption={false}
              loading={claimCustomersLoading}
              onSearch={(keyword) => void searchClaimCustomers(keyword)}
              placeholder="请选择客户"
              options={claimCustomers.map((x) => ({
                value: x.title,
                label: x.serial_no ? `${x.title}｜${x.serial_no}` : x.title,
              }))}
              notFoundContent={claimCustomersLoading ? "正在查询系统客户..." : "没有匹配的系统客户"}
            />
          </Form.Item>
          <Form.Item label="回款时间">
            <Input value={claimTarget?.received_date || ""} readOnly />
          </Form.Item>
          <Form.Item label="回款金额">
            <Input value={claimTarget?.amount == null ? "无权限" : money(claimTarget.amount)} readOnly />
          </Form.Item>
          <Form.Item label="回款方式">
            <Input value={claimTarget?.bank_source || "—"} readOnly />
          </Form.Item>
          <Form.Item label="银行单号">
            <Input value={claimTarget?.bank_reference || ""} readOnly />
          </Form.Item>
          <Form.Item label="合同编号">
            <Input value={claimTarget?.contract_no || ""} readOnly />
          </Form.Item>
          <Form.Item label="登记备注">
            <Input.TextArea value={claimTarget?.remark || ""} rows={2} readOnly />
          </Form.Item>
          <Form.Item label="领取备注" name="comment">
            <Input.TextArea rows={2} placeholder="可选" />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        width={920}
        open={Boolean(incomingAllocationTarget)}
        title={`历史分配记录：${incomingAllocationTarget?.receipt_no || ""}`}
        footer={null}
        onCancel={() => setIncomingAllocationTarget(null)}
      >
        <Table
          rowKey={(row: any, index) =>
            String(row.transaction_id || row.receivable_plan_id || index)
          }
          size="small"
          pagination={{ pageSize: 20, showSizeChanger: false }}
          dataSource={incomingAllocationTarget?.allocations || []}
          locale={{ emptyText: "暂无分配记录" }}
          columns={[
            { title: "合同号", dataIndex: "contract_no", width: 150, render: (v: string) => v ? <Button type="link" onClick={() => openContractDetail(v)}>{v}</Button> : "—" },
            { title: "案号", dataIndex: "case_no", width: 140, render: (v: string) => v ? <Button type="link" onClick={() => openCaseDetail(v)}>{v}</Button> : "—" },
            { title: "费用阶段", dataIndex: "phase", width: 120 },
            {
              title: "分配金额",
              dataIndex: "amount",
              width: 120,
              render: (value: number) => money(value),
            },
            { title: "分配方式", dataIndex: "payment_method", width: 110 },
            { title: "分配人", dataIndex: "allocated_by", width: 100, render: (value: string, row: any) => financePersonDisplayName(value, row.allocated_by_display_name) },
            { title: "分配时间", dataIndex: "allocated_at", width: 180 },
          ]}
        />
      </Modal>
      <Modal
        width="calc(100vw - 48px)"
        style={{ top: 24 }}
        rootClassName="finance-allocation-modal"
        open={Boolean(allocateTarget)}
        title={`分配回款：${allocateTarget?.receipt_no || ""}`}
        okText="确认分配"
        cancelText="取消"
        onOk={allocateIncoming}
        onCancel={() => {
          setAllocateTarget(null);
          setAllocationCandidates([]);
          setSelectedAllocationKeys([]);
          setAllocationValidationError("");
        }}
      >
        {allocationValidationError && (
          <Alert
            type="error"
            showIcon
            message={allocationValidationError}
            style={{ marginBottom: 12 }}
          />
        )}
        <section className="finance-allocation-section">
          <div className="finance-allocation-heading">回款信息</div>
          <Descriptions size="small" column={5} colon={false}>
            <Descriptions.Item label="回款单位">{allocateTarget?.payer_name || "—"}</Descriptions.Item>
            <Descriptions.Item label="到账日期">{allocateTarget?.received_date || "—"}</Descriptions.Item>
            <Descriptions.Item label="银行单号">{allocateTarget?.bank_reference || "—"}</Descriptions.Item>
            <Descriptions.Item label="到账金额">{money(Number(allocateTarget?.amount || 0))}</Descriptions.Item>
            <Descriptions.Item label="已分配">{money(Number(allocateTarget?.allocated_amount || 0))}</Descriptions.Item>
            <Descriptions.Item label="客户名称">{allocateTarget?.claimed_customer || "—"}</Descriptions.Item>
            <Descriptions.Item label="未分配余额">{money(Number(allocateTarget?.remaining_amount || 0))}</Descriptions.Item>
            <Descriptions.Item label="备注" span={3}>{allocateTarget?.remark || "—"}</Descriptions.Item>
          </Descriptions>
        </section>
        <section className="finance-allocation-section">
          <div className="finance-allocation-heading">案件费用明细</div>
          <div className="finance-allocation-filters">
            <label>客户名称<Input value={allocateTarget?.claimed_customer || ""} disabled /></label>
            <label>关键字<Input value={allocationKeyword} onChange={(event) => setAllocationKeyword(event.target.value)} placeholder="案号、原告、被告、案件名称" allowClear /></label>
            <label>案件阶段<Select allowClear value={allocationStage || undefined} onChange={(value) => setAllocationStage(value || "")} options={Array.from(new Set(allocationCandidates.map((row) => row.case_stage))).filter(Boolean).map((value) => ({ value, label: value }))} /></label>
            <label>费用类型<Select allowClear value={allocationFeeType || undefined} onChange={(value) => setAllocationFeeType(value || "")} options={Array.from(new Set(allocationCandidates.map((row) => row.fee_type))).filter(Boolean).map((value) => ({ value, label: value }))} /></label>
            <Button type="primary" onClick={() => undefined}>查询</Button>
            <Button onClick={() => { setAllocationKeyword(""); setAllocationStage(""); setAllocationFeeType(""); }}>清空</Button>
          </div>
          <Table<AllocationCandidate>
            className="finance-allocation-table"
            loading={allocationLoading}
            size="small"
            bordered
            rowKey="key"
            scroll={{ x: 1370, y: 390 }}
            pagination={{ pageSize: 20, showSizeChanger: false, showTotal: (total) => `共 ${total} 条` }}
            dataSource={filteredAllocationCandidates}
            locale={{ emptyText: "该客户名下暂无未回款案件费用" }}
            rowSelection={{
              selectedRowKeys: selectedAllocationKeys,
              preserveSelectedRowKeys: true,
              onChange: (keys) => setSelectedAllocationKeys(keys.map((key) => String(key))),
            }}
            columns={[
              { title: "原告", dataIndex: "plaintiff", width: 170, ellipsis: true },
              { title: "被告", dataIndex: "defendant", width: 210, ellipsis: true },
              { title: "案号", dataIndex: "case_no", width: 135, render: (value) => value ? <Button type="link" onClick={() => openCaseDetail(value)}>{value}</Button> : "—" },
              { title: "案件阶段", dataIndex: "case_stage", width: 105 },
              { title: "提交日期", dataIndex: "submission_date", width: 100 },
              { title: "费用类型", dataIndex: "fee_type", width: 125 },
              { title: "总额", dataIndex: "total_amount", width: 90, render: money },
              { title: "已回", dataIndex: "received_amount", width: 90, render: money },
              { title: "待回", dataIndex: "remaining_amount", width: 90, render: money },
              {
                title: "本次回款",
                key: "allocation_amount",
                width: 125,
                render: (_, row) => (
                  <InputNumber
                    aria-label={`本次回款-${row.case_no || row.contract_no}-${row.fee_type}`}
                    min={0.01}
                    max={row.remaining_amount}
                    precision={2}
                    value={allocationAmounts[row.key]}
                    onChange={(value) => {
                      setAllocationAmounts((current) => ({ ...current, [row.key]: Number(value || 0) }));
                      if (value && !selectedAllocationKeys.includes(row.key)) {
                        setSelectedAllocationKeys((current) => [...current, row.key]);
                      }
                    }}
                  />
                ),
              },
              {
                title: "全部回款",
                key: "all",
                width: 80,
                align: "center",
                render: (_, row) => (
                  <Checkbox
                    checked={selectedAllocationKeys.includes(row.key) && Number(allocationAmounts[row.key]) === Number(row.remaining_amount)}
                    onChange={(event) => {
                      setAllocationAmounts((current) => ({ ...current, [row.key]: row.remaining_amount }));
                      setSelectedAllocationKeys((current) => event.target.checked
                        ? Array.from(new Set([...current, row.key]))
                        : current.filter((key) => key !== row.key));
                    }}
                  />
                ),
              },
            ]}
          />
          <div className="finance-allocation-comment">
            <span>分配说明</span>
            <Input value={allocationComment} onChange={(event) => setAllocationComment(event.target.value)} placeholder="可选" />
          </div>
        </section>
      </Modal>
      <Modal
        open={Boolean(writeoffTarget)}
        title={`付款核销：${writeoffTarget?.serial_no || ""}`}
        okText="确认核销"
        cancelText="取消"
        onOk={writeoffFee}
        onCancel={() => {
          setWriteoffTarget(null);
          writeoffForm.resetFields();
        }}
      >
        <Form form={writeoffForm} layout="vertical">
          <Form.Item
            label="核销日期"
            name="writeoff_date"
            initialValue={dayjs()}
            rules={[{ required: true, message: "请选择核销日期" }]}
          >
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item
            label="核销凭证号"
            name="voucher_no"
            rules={[{ required: true, min: 2, message: "请输入核销凭证号" }]}
          >
            <Input placeholder="例如：HX-20260715-001" />
          </Form.Item>
          <Form.Item label="核销说明" name="comment">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(paymentCancelTarget)}
        title={`撤销请款单：${paymentCancelTarget?.serial_no || ""}`}
        okText="撤销"
        okButtonProps={{ danger: true }}
        cancelText="取消"
        onOk={() => void submitPaymentCancel()}
        onCancel={() => {
          setPaymentCancelTarget(null);
          setPaymentCancelReason("");
        }}
      >
        <Input.TextArea
          rows={4}
          value={paymentCancelReason}
          onChange={(event) => setPaymentCancelReason(event.target.value)}
          placeholder="请输入撤回原因"
          aria-label="撤回原因"
        />
      </Modal>
      <Modal
        open={Boolean(paymentRollbackTarget)}
        title={`回滚请款单：${paymentRollbackTarget?.serial_no || ""}`}
        okText="回滚"
        cancelText="取消"
        onOk={() => void submitPaymentRollback()}
        onCancel={() => {
          setPaymentRollbackTarget(null);
          setPaymentRollbackComment("");
        }}
      >
        <Input.TextArea
          rows={4}
          value={paymentRollbackComment}
          onChange={(event) => setPaymentRollbackComment(event.target.value)}
          placeholder="请输入回滚备注（可选）"
          aria-label="回滚备注"
        />
      </Modal>
      <Modal
        className="finance-payment-package-writeoff-modal"
        width={600}
        style={{ top: 30 }}
        open={Boolean(paymentPackageWriteoffTarget)}
        title="付款核销"
        okText="确定"
        cancelText="取消"
        confirmLoading={paymentPackageLoading}
        onOk={() => void writeoffPaymentPackage()}
        onCancel={() => {
          setPaymentPackageWriteoffTarget(null);
          paymentPackageWriteoffForm.resetFields();
        }}
      >
        <Form form={paymentPackageWriteoffForm} layout="vertical">
          <Form.Item
            label="付款打包号"
            name="package_no"
            required
          >
            <Input readOnly />
          </Form.Item>
          <Form.Item
            label="请确认付款金额"
            name="amount"
            rules={[{ required: true, message: "请确认付款金额." }]}
          >
            <InputNumber
              precision={2}
              readOnly
              controls={false}
              style={{ width: "100%" }}
            />
          </Form.Item>
          <Form.Item
            label="请输入付款日期"
            name="paid_date"
            rules={[{ required: true, message: "请输入付款日期." }]}
          >
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item
            label="请选择付款方式"
            name="payment_method"
            rules={[{ required: true, message: "请选择付款方式." }]}
          >
            <Select
              options={["自动扣款", "银行卡", "现金"].map((value) => ({
                label: value,
                value,
              }))}
            />
          </Form.Item>
          <Form.Item
            label="请输入付款单据号"
            name="invoice_no"
            rules={[{ required: true, message: "请输入付款单据号." }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label="请输入付款备注" name="remark">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        width={760}
        open={Boolean(feeDetail) && !isInternalHistoryList}
        title="请款单详情"
        footer={null}
        onCancel={() => setFeeDetail(null)}
      >
        {feeDetail && (
          <Descriptions bordered size="small" column={2}>
            <Descriptions.Item label="请款单号">
              {feeDetail.serial_no || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              {initialView === "finance-internal-refused"
                ? "已拒绝"
                : paymentStatus(feeDetail)}
            </Descriptions.Item>
            <Descriptions.Item label="付款包号">
              {feeDetail.data.payment_package_no ||
                feeDetail.data.package_no ||
                feeDetail.data.payment_package_context?.serial_no ||
                "—"}
            </Descriptions.Item>
            <Descriptions.Item label="付款包状态">
              {feeDetail.data.payment_package_context?.status || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="申请日期">
              {(
                feeDetail.data.application_date ||
                feeDetail.created_at ||
                "—"
              ).slice(0, 10)}
            </Descriptions.Item>
            <Descriptions.Item label="审核日期">
              {(feeDetail.data.audit_date || feeDetail.updated_at || "—").slice(
                0,
                10,
              )}
            </Descriptions.Item>
            <Descriptions.Item label="申请金额">
              {feeDetail.data.amount == null
                ? "—"
                : money(feeDetail.data.amount)}
            </Descriptions.Item>
            <Descriptions.Item label="费用类型">
              {feeDetail.data.fee_type || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="案件编号">
              {feeDetail.data.case_no ? <Button type="link" onClick={() => openCaseDetail(feeDetail.data.case_no)}>{feeDetail.data.case_no}</Button> : "—"}
            </Descriptions.Item>
            <Descriptions.Item label="合同编号">
              {feeDetail.data.contract_no ? (
                <Button
                  type="link"
                  onClick={() => openContractDetail(feeDetail.data.contract_no)}
                >
                  {feeDetail.data.contract_no}
                </Button>
              ) : (
                "—"
              )}
            </Descriptions.Item>
            <Descriptions.Item label="案件阶段">
              {feeDetail.data.case_stage ||
                linkedCaseForFee(feeDetail)?.data.case_stage ||
                linkedCaseForFee(feeDetail)?.status ||
                "—"}
            </Descriptions.Item>
            <Descriptions.Item label="案件名称" span={2}>
              {linkedCaseForFee(feeDetail)?.title || feeDetail.title || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="客户名称">
              {feeDetail.customer ? <Button type="link" onClick={() => openCustomerDetail(feeDetail.customer, feeDetail.data.customer_no)}>{feeDetail.customer}</Button> : "—"}
            </Descriptions.Item>
            <Descriptions.Item label="收款单位">
              {feeDetail.data.payee || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="付款日期">
              {latestTransaction(feeDetail)?.transaction_date || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="申请人">
              {financePersonDisplayName(
                feeDetail.data.applicant || feeDetail.owner,
                feeDetail.data.applicant_display_name || feeDetail.data.owner_display_name,
              )}
            </Descriptions.Item>
            <Descriptions.Item label="缴费法院/机构">
              {feeDetail.data.court || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="缴费通知文号">
              {feeDetail.data.document_no || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="说明" span={2}>
              {feeDetail.data.description || "—"}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
      <Modal
        width={760}
        open={Boolean(refundDetail)}
        title={`退款申请详情：${refundDetail?.serial_no || ""}`}
        footer={null}
        onCancel={() => setRefundDetail(null)}
      >
        {refundDetail && (
          <Descriptions bordered size="small" column={2}>
            <Descriptions.Item label="退款申请号">{refundDetail.serial_no || "—"}</Descriptions.Item>
            <Descriptions.Item label="状态"><Tag color={statusColors[refundDetail.status] || "default"}>{refundDetail.status || "—"}</Tag></Descriptions.Item>
            <Descriptions.Item label="关联案号">{refundDetail.data.case_no ? <Button type="link" onClick={() => openCaseDetail(refundDetail.data.case_no)}>{refundDetail.data.case_no}</Button> : "—"}</Descriptions.Item>
            <Descriptions.Item label="客户">{refundDetail.customer ? <Button type="link" onClick={() => openCustomerDetail(refundDetail.customer, refundDetail.data.customer_no)}>{refundDetail.customer}</Button> : "—"}</Descriptions.Item>
            <Descriptions.Item label="退款金额">{refundDetail.data.amount == null ? "—" : money(refundDetail.data.amount)}</Descriptions.Item>
            <Descriptions.Item label="预计到账">{refundDetail.data.expected_date || "—"}</Descriptions.Item>
            <Descriptions.Item label="原缴费票号">{refundDetail.data.original_payment_no || "—"}</Descriptions.Item>
            <Descriptions.Item label="退款账户">{refundDetail.data.refund_account_name || "—"}</Descriptions.Item>
            <Descriptions.Item label="实际到账">{refundDetail.data.actual_date || "—"}</Descriptions.Item>
            <Descriptions.Item label="退款凭证号">{refundDetail.data.voucher_no || "—"}</Descriptions.Item>
            <Descriptions.Item label="申请人">{financePersonDisplayName(refundDetail.data.applicant || refundDetail.owner, refundDetail.data.applicant_display_name || refundDetail.data.owner_display_name)}</Descriptions.Item>
            <Descriptions.Item label="说明" span={2}>{refundDetail.description || refundDetail.data.remark || "—"}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
      <Modal
        open={feeOpen}
        title={feeEditTarget ? "编辑费用" : "新增费用"}
        okText={feeEditTarget ? "保存修改" : "保存草稿"}
        cancelText="取消"
        onOk={createFee}
        onCancel={closeFeeModal}
      >
        <Form form={feeForm} layout="vertical">
          <Form.Item name="case_record_id" hidden>
            <Input />
          </Form.Item>
          <Form.Item name="contract_record_id" hidden>
            <Input />
          </Form.Item>
          <Form.Item label="费用名称" name="title" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <div className="form-grid">
            <Form.Item
              label="费用类型"
              name="fee_type"
              rules={[{ required: true }]}
            >
              <Select
                options={feeTypes.map((v) => ({ value: v, label: v }))}
                onChange={(value) => setFeeTypeOverride(value || "")}
              />
            </Form.Item>
            <Form.Item
              label="金额"
              name="amount"
              rules={[
                { required: true },
                {
                  validator: (_, value) =>
                    value === 0
                      ? Promise.reject(new Error("金额不能为 0"))
                      : Promise.resolve(),
                },
              ]}
            >
              <InputNumber
                min={selectedFeeType === "内部费用" ? undefined : 0.01}
                precision={3}
                style={{ width: "100%" }}
                placeholder={
                  selectedFeeType === "内部费用" ? "允许负数冲销" : "请输入正数"
                }
              />
            </Form.Item>
            <Form.Item
              label="经办人员"
              name="handler"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              label="关联案号"
              name="case_no"
              rules={[{ required: true, message: "请选择或填写关联案号" }]}
            >
              <Input />
            </Form.Item>
            <Form.Item label="客户" name="customer">
              <Input />
            </Form.Item>
            <Form.Item label="收款单位" name="payee">
              <Input />
            </Form.Item>
          </div>
          <Form.Item label="缴费法院/机构" name="court">
            <Input />
          </Form.Item>
          <Form.Item label="缴费通知文号" name="document_no">
            <Input />
          </Form.Item>
          <Form.Item label="说明" name="description">
            <Input.TextArea rows={2} />
          </Form.Item>
          {selectedFeeType === "代理费" && (
            <Form.List name="commission_details">
              {(fields, { add, remove }) => (
                <section className="finance-fee-commission-details">
                  <div className="finance-fee-commission-header">
                    <strong>员工提成</strong>
                    <Button
                      type="dashed"
                      icon={<PlusOutlined />}
                      onClick={() =>
                        add({ commission_type: "员工提成", amount: undefined, remark: "" })
                      }
                    >
                      新建员工提成
                    </Button>
                  </div>
                  {fields.map((field) => (
                    <div className="finance-fee-commission-row" key={field.key}>
                      <Form.Item
                        {...field}
                        name={[field.name, "employee_username"]}
                        label="员工"
                        rules={[{ required: true, message: "请选择员工" }]}
                      >
                        <Select
                          showSearch
                          optionFilterProp="label"
                          options={financePeople.map((person) => ({
                            value: person.username,
                            label: person.label,
                          }))}
                        />
                      </Form.Item>
                      <Form.Item
                        {...field}
                        name={[field.name, "commission_type"]}
                        label="提成类型"
                        rules={[{ required: true }]}
                      >
                        <Input />
                      </Form.Item>
                      <Form.Item
                        {...field}
                        name={[field.name, "amount"]}
                        label="提成金额"
                        rules={[{ required: true, message: "请输入提成金额" }]}
                      >
                        <InputNumber min={0.01} precision={2} style={{ width: "100%" }} />
                      </Form.Item>
                      <Form.Item {...field} name={[field.name, "remark"]} label="备注">
                        <Input />
                      </Form.Item>
                      <Button
                        danger
                        type="text"
                        aria-label="删除员工提成"
                        icon={<DeleteOutlined />}
                        onClick={() => remove(field.name)}
                      />
                    </div>
                  ))}
                  {feeCommissionDetails.length > 0 && (
                    <div className="finance-fee-commission-total">
                      已分配员工提成：{feeCommissionDetails.reduce((sum: number, detail: Record<string, any>) => sum + Number(detail?.amount || 0), 0).toFixed(2)}
                    </div>
                  )}
                </section>
              )}
            </Form.List>
          )}
        </Form>
      </Modal>
      <Drawer
        className="finance-invoice-request-drawer"
        width="min(1180px, calc(100vw - 32px))"
        open={invoiceOpen}
        title={invoiceEditTarget ? "编辑发票申请" : "新增发票申请"}
        destroyOnHidden
        onClose={() => {
          setInvoiceOpen(false);
          setInvoiceEditTarget(null);
          setInvoiceSelectedFeeIds([]);
          setInvoiceFeeAmounts({});
          setInvoiceSourceFeeId(null);
          invoiceForm.resetFields();
        }}
        footer={
          <Space>
            <Button onClick={() => setInvoiceOpen(false)}>取消</Button>
            <Button type="primary" onClick={() => void createInvoice()}>
              {invoiceEditTarget ? "保存修改" : "保存草稿"}
            </Button>
          </Space>
        }
      >
        <Form form={invoiceForm} layout="vertical" className="finance-invoice-request-form">
          <Form.Item name="case_record_id" hidden><Input /></Form.Item>
          <Form.Item name="contract_record_id" hidden><Input /></Form.Item>
          <Form.Item name="case_fee_ids" hidden><Input /></Form.Item>
          <section className="finance-invoice-request-section">
            <h3>申请信息</h3>
            <div className="finance-invoice-request-grid">
              <Form.Item label="来源案件" name="case_no">
                <Input readOnly placeholder="从发票明细自动带入" />
              </Form.Item>
              <Form.Item label="合同编号" name="contract_no">
                <Input readOnly placeholder="从发票明细自动带入" />
              </Form.Item>
              <Form.Item label="外部合同号" name="external_contract_no">
                <Input readOnly placeholder="从发票明细自动带入" />
              </Form.Item>
              <Form.Item label="客户名称" name="customer" rules={[{ required: true }]}>
                <Input readOnly placeholder="从发票明细自动带入" />
              </Form.Item>
              <Form.Item label="申请开票金额" name="amount" rules={[{ required: true }]}>
                <InputNumber min={0.01} precision={2} style={{ width: "100%" }} />
              </Form.Item>
            </div>
          </section>
          <section className="finance-invoice-request-section">
            <h3>发票内容</h3>
            <div className="finance-invoice-request-grid">
              <Form.Item label="发票抬头" name="invoice_title" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item label="纳税人识别号" name="taxpayer_id" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item label="公司电话" name="invoice_phone"><Input /></Form.Item>
              <Form.Item label="银行账号" name="bank_account"><Input /></Form.Item>
              <Form.Item label="开户银行" name="bank_name"><Input /></Form.Item>
              <Form.Item className="span-2" label="开票地址" name="invoice_address"><Input /></Form.Item>
            </div>
          </section>
          <section className="finance-invoice-request-section">
            <h3>服务项</h3>
            <div className="finance-invoice-request-grid">
              <Form.Item label="发票类型" name="invoice_type" rules={[{ required: true }]}>
                <Select options={["增值税普通发票", "增值税专用发票", "电子普通发票", "电子专用发票"].map((value) => ({ value, label: value }))} />
              </Form.Item>
              <Form.Item label="开票内容" name="invoice_content" rules={[{ required: true }]}><Input /></Form.Item>
              <Form.Item label="高开发票金额" name="extra_amount"><InputNumber min={0} precision={2} style={{ width: "100%" }} /></Form.Item>
              <Form.Item label="交付方式" name="delivery_method"><Select options={["电子发票", "邮寄纸质发票", "现场领取"].map((value) => ({ value, label: value }))} /></Form.Item>
              <Form.Item label="接收邮箱" name="email"><Input /></Form.Item>
              <Form.Item label="收件人" name="recipient"><Input /></Form.Item>
              <Form.Item label="联系电话" name="recipient_phone"><Input /></Form.Item>
              <Form.Item className="span-2" label="邮寄地址" name="delivery_address"><Input /></Form.Item>
              <Form.Item className="span-2" label="备注" name="remark"><Input.TextArea rows={2} /></Form.Item>
            </div>
          </section>
          <section className="finance-invoice-request-section finance-invoice-request-details">
            <div className="finance-invoice-request-section-heading">
              <h3>发票明细</h3>
              <span>{invoiceSourceFeeId ? "来源费用已自动绑定" : "选择费用后自动带入案件、合同和客户"}</span>
            </div>
            <div className="finance-invoice-request-table-wrap">
              <table className="finance-invoice-request-table">
                <thead>
                  <tr>
                    <th>选择</th><th>合同编号</th><th>外部合同号</th><th>案件名称</th><th>案件阶段</th><th>案号</th><th>费用类型</th><th>费用金额</th><th>已到账金额</th><th>已开票金额</th><th>本次开票</th>
                  </tr>
                </thead>
                <tbody>
                  {invoiceFeeOptions.map((fee) => {
                    const feeData = fee.data || {};
                    const availableAmount = invoiceFeeAvailableAmount(fee);
                    const selected = invoiceSelectedFeeIds.includes(fee.id);
                    const currentAmount = invoiceFeeAmounts[fee.id] ?? availableAmount;
                    return <tr key={fee.id} className={selected ? "is-selected" : undefined}>
                      <td><Checkbox checked={selected} disabled={Boolean(invoiceSourceFeeId)} onChange={(event) => {
                        const nextIds = event.target.checked
                          ? [...invoiceSelectedFeeIds, fee.id]
                          : invoiceSelectedFeeIds.filter((id) => id !== fee.id);
                        applyInvoiceFeeSelection(nextIds);
                      }} /></td>
                      <td>{feeData.contract_no || "—"}</td><td>{feeData.external_contract_no || "—"}</td><td>{feeData.case_name || feeData.case_title || fee.title || "—"}</td><td>{feeData.case_stage || feeData.stage || "—"}</td><td>{feeData.case_no || "—"}</td><td>{feeData.fee_type || fee.title || "—"}</td><td>{Number(feeData.amount || 0).toFixed(2)}</td><td>{Number(feeData.received_amount ?? feeData.cashed_amount ?? feeData.paid_amount ?? 0).toFixed(2)}</td><td>{invoiceFeeIssuedAmount(fee).toFixed(2)}</td>
                      <td><InputNumber min={0} max={availableAmount} precision={2} disabled={!selected || Boolean(invoiceSourceFeeId)} value={currentAmount} onChange={(value) => {
                        const nextAmount = Math.min(availableAmount, Math.max(0, Number(value || 0)));
                        const nextAmounts = { ...invoiceFeeAmounts, [fee.id]: nextAmount };
                        setInvoiceFeeAmounts(nextAmounts);
                        invoiceForm.setFieldValue("amount", Number(invoiceSelectedFeeIds.reduce((total, id) => total + Number(nextAmounts[id] ?? invoiceFeeAvailableAmount(invoiceFeeOptions.find((item) => item.id === id) || fee)), 0).toFixed(2)));
                      }} /></td>
                    </tr>;
                  })}
                  {!invoiceFeeOptions.length && <tr><td colSpan={11}>暂无可申请开票的费用</td></tr>}
                </tbody>
              </table>
            </div>
          </section>
        </Form>
      </Drawer>
      <Modal
        width={760}
        open={refundOpen}
        title="新增诉讼费退款申请"
        okText="保存草稿"
        cancelText="取消"
        onOk={createRefund}
        onCancel={() => setRefundOpen(false)}
      >
        <Form form={refundForm} layout="vertical">
          <Form.Item name="fee_record_id" hidden>
            <Input />
          </Form.Item>
          <div className="form-grid">
            <Form.Item
              className="span-2"
              label="关联案件"
              name="case_no"
              rules={[{ required: true }]}
            >
              <Select
                showSearch
                optionFilterProp="label"
                options={cases.map((x) => ({
                  value: x.serial_no,
                  label: `${x.serial_no}｜${x.customer}｜${x.title}`,
                }))}
                onChange={(no) => {
                  const item = cases.find((x) => x.serial_no === no);
                  if (item) {
                    refundForm.setFieldValue("customer", item.customer);
                    refundForm.setFieldValue("court", item.data.court || "");
                  }
                }}
              />
            </Form.Item>
            <Form.Item
              label="客户"
              name="customer"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              label="退款法院"
              name="court"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              label="原缴费票号"
              name="original_payment_no"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              label="退款金额"
              name="amount"
              rules={[{ required: true }]}
            >
              <InputNumber min={0.01} precision={2} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item
              label="申请人"
              name="applicant"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <Form.Item label="预计到账日" name="expected_date">
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item
              label="退款账户名"
              name="refund_account_name"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              label="退款银行"
              name="refund_bank"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              className="span-2"
              label="退款账号"
              name="refund_account"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <Form.Item label="退款原因" name="reason">
              <Input />
            </Form.Item>
            <Form.Item label="备注" name="remark">
              <Input />
            </Form.Item>
          </div>
        </Form>
      </Modal>
      <Modal
        open={Boolean(invoiceNumberTarget)}
        title="修改发票编号"
        okText="确定"
        cancelText="取消"
        confirmLoading={invoiceMutationLoading}
        onOk={() => void submitInvoiceNumberChange()}
        onCancel={() => {
          setInvoiceNumberTarget(null);
          invoiceNumberForm.resetFields();
        }}
      >
        <Form form={invoiceNumberForm} layout="horizontal" labelCol={{ span: 6 }}>
          <Form.Item label="请票单号" name="application_no">
            <Input readOnly />
          </Form.Item>
          <Form.Item label="合同编号" name="contract_no">
            <Input readOnly />
          </Form.Item>
          <Form.Item label="原发票号码" name="old_invoice_no">
            <Input readOnly />
          </Form.Item>
          <Form.Item label="新发票号码" name="new_invoice_no" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(invoiceDateTarget)}
        title="修改发票日期"
        okText="确定"
        cancelText="取消"
        confirmLoading={invoiceMutationLoading}
        onOk={() => void submitInvoiceDateChange()}
        onCancel={() => {
          setInvoiceDateTarget(null);
          invoiceDateForm.resetFields();
        }}
      >
        <Form form={invoiceDateForm} layout="horizontal" labelCol={{ span: 6 }}>
          <Form.Item label="请票单号" name="application_no">
            <Input readOnly />
          </Form.Item>
          <Form.Item label="发票申请日期" name="application_date" rules={[{ required: true }]}>
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="发票开票日期" name="invoice_date" rules={[{ required: true }]}>
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(issueTarget)}
        title={`登记开票：${issueTarget?.serial_no || ""}`}
        okText="确认开票"
        cancelText="取消"
        onOk={issueInvoice}
        onCancel={() => setIssueTarget(null)}
      >
        <Form form={issueForm} layout="vertical">
          <Form.Item
            label="发票号码"
            name="invoice_no"
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="开票日期"
            name="invoice_date"
            rules={[{ required: true }]}
          >
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="开票备注" name="comment">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(voidTarget)}
        title={`作废发票：${voidTarget?.data.invoice_no || voidTarget?.serial_no || ""}`}
        okText="确认作废"
        okButtonProps={{ danger: true }}
        cancelText="取消"
        onOk={voidInvoice}
        onCancel={() => setVoidTarget(null)}
      >
        <Alert
          type="warning"
          showIcon
          title="作废后系统会生成等额负数开票流水进行冲销。"
          style={{ marginBottom: 16 }}
        />
        <Form form={voidForm} layout="vertical">
          <Form.Item
            label="作废原因"
            name="reason"
            rules={[{ required: true, min: 2 }]}
          >
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(refundAmountTarget)}
        title={`修改退款金额：${refundAmountTarget?.serial_no || ""}`}
        okText="保存"
        cancelText="取消"
        confirmLoading={refundMutationLoading}
        onOk={updateRefundAmount}
        onCancel={() => {
          setRefundAmountTarget(null);
          refundAmountForm.resetFields();
        }}
      >
        <Form form={refundAmountForm} layout="vertical">
          <Form.Item
            label="退款金额"
            name="amount"
            rules={[{ required: true, type: "number", min: 0.01 }]}
          >
            <InputNumber min={0.01} precision={2} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="修改说明" name="comment">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={refundCaseFeeStatusOpen}
        title={`退费进度修改（已选 ${selectedOriginalRows.length} 条）`}
        okText="确定"
        cancelText="取消"
        confirmLoading={refundCaseFeeMutationLoading}
        onOk={() => void submitRefundCaseFeeStatus()}
        onCancel={() => setRefundCaseFeeStatusOpen(false)}
      >
        <Select
          aria-label="案件费用退费进度"
          value={refundCaseFeeStatus}
          onChange={setRefundCaseFeeStatus}
          options={[
            ["R10", "准备材料"],
            ["R20", "已提交法院"],
            ["R30", "法院处理中"],
            ["R35", "待退款到账"],
            ["R40", "退款已到账"],
            ["R50", "退费完成"],
          ].map(([value, label]) => ({ value, label }))}
          style={{ width: "100%" }}
        />
      </Modal>
      <Modal
        open={Boolean(refundCaseFeeLogKind)}
        title={{ court: "添加法院日志", received: "添加到账日志", other: "添加其他日志" }[refundCaseFeeLogKind || "other"]}
        okText="保存"
        cancelText="取消"
        confirmLoading={refundCaseFeeMutationLoading}
        onOk={() => void submitRefundCaseFeeLog()}
        onCancel={() => {
          setRefundCaseFeeLogKind(null);
          setRefundCaseFeeLogContent("");
        }}
      >
        <Input.TextArea
          aria-label="退费日志内容"
          rows={4}
          value={refundCaseFeeLogContent}
          onChange={(event) => setRefundCaseFeeLogContent(event.target.value)}
          placeholder="请输入日志内容"
        />
      </Modal>
      <Modal
        open={refundBatchStatusOpen}
        title={`退费进度修改（已选 ${selectedRefundRows.length} 条）`}
        okText="确定"
        cancelText="取消"
        confirmLoading={refundMutationLoading}
        onOk={updateRefundBatchStatus}
        onCancel={() => setRefundBatchStatusOpen(false)}
      >
        <Select
          aria-label="批量退费进度"
          value={refundBatchStatus}
          onChange={setRefundBatchStatus}
          options={["待审批", "退款办理中", "已驳回"].map((value) => ({
            value,
            label: value,
          }))}
          style={{ width: "100%" }}
        />
      </Modal>
      <Modal
        open={Boolean(refundCompleteTarget)}
        title={`登记退款到账：${refundCompleteTarget?.serial_no || ""}`}
        okText="确认到账"
        cancelText="取消"
        onOk={completeRefund}
        onCancel={() => setRefundCompleteTarget(null)}
      >
        <Form form={refundCompleteForm} layout="vertical">
          <Form.Item
            label="实际到账日期"
            name="actual_date"
            rules={[{ required: true }]}
          >
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item
            label="退款凭证号"
            name="voucher_no"
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label="到账说明" name="comment">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        width={760}
        open={Boolean(recordFileTarget)}
        title={recordFileTargets.length > 1 ? `批量上传案件文档（已选 ${recordFileTargets.length} 个案件）` : `业务凭证：${recordFileTarget?.serial_no || ""}`}
        footer={null}
        onCancel={() => { setRecordFileTarget(null); setRecordFileTargets([]); }}
      >
        <Table
          rowKey="id"
          size="small"
          pagination={false}
          dataSource={recordFiles}
          locale={{ emptyText: "尚未上传凭证" }}
          columns={[
            {
              title: "凭证类型",
              dataIndex: "category",
              width: 120,
              render: (v: string) => <Tag color="blue">{v}</Tag>,
            },
            { title: "文件名", dataIndex: "original_name" },
            {
              title: "大小",
              dataIndex: "size",
              width: 90,
              render: (v: number) => `${(v / 1024).toFixed(1)} KB`,
            },
            { title: "上传人", dataIndex: "uploader", width: 85 },
            {
              title: "操作",
              width: 130,
              render: (_: unknown, r: Attachment) => (
                <Space size={0}>
                  <Button type="link" onClick={() => downloadVoucher(r)}>
                    下载
                  </Button>
                  {role === "admin" && (
                    <Button
                      type="link"
                      danger
                      onClick={() => deleteRecordFile(r)}
                    >
                      删除
                    </Button>
                  )}
                </Space>
              ),
            },
          ]}
        />
        <Form form={recordFileForm} layout="vertical" style={{ marginTop: 16 }}>
          <div className="form-grid">
            <Form.Item
              label="凭证类型"
              name="category"
              rules={[{ required: true }]}
            >
              {recordFileTargets.length > 1 ? (
                <TreeSelect
                  treeData={recordFileTypeTree.length ? recordFileTypeTree : [
                    {
                      title: "案件文件",
                      value: "CASE_GROUP",
                      children: [
                        { title: "主体及委托资料", value: "主体及委托资料" },
                        { title: "起诉材料及证据", value: "起诉材料及证据" },
                        { title: "答辩材料及证据", value: "答辩材料及证据" },
                        { title: "法院诉讼文书", value: "法院诉讼文书" },
                        { title: "庭审及庭后文件", value: "庭审及庭后文件" },
                        { title: "普通附件", value: "普通附件" },
                      ],
                    },
                    {
                      title: "调查文档",
                      value: "INVESTIGATION_GROUP",
                      children: [
                        { title: "鉴别资料", value: "鉴别资料" },
                        { title: "调查文档", value: "调查文档" },
                        { title: "取证文档", value: "取证文档" },
                      ],
                    },
                  ]}
                  treeDefaultExpandAll
                  placeholder="请选择文档类型"
                  treeNodeFilterProp="title"
                  showSearch
                />
              ) : (
                <Select
                  options={[
                    "发票扫描件",
                    "退费凭证",
                    "法院退费通知",
                    "银行回单",
                    "其他财务材料",
                  ].map((v) => ({ value: v, label: v }))}
                />
              )}
            </Form.Item>
            {recordFileTargets.length > 0 && <Form.Item label="参考日期" name="document_date" rules={[{ required: true }]}><DatePicker style={{ width: "100%" }} /></Form.Item>}
            <Form.Item label="选择文件" required>
              <input
                type="file"
                multiple={recordFileTargets.length > 0}
                accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.xls,.xlsx"
                onChange={(e) => {
                  const files = Array.from(e.target.files || []);
                  setRecordUploadFiles(files);
                  setRecordFile(files[0] || null);
                }}
              />
            </Form.Item>
          </div>
          <Form.Item label="说明" name="remark">
            <Input />
          </Form.Item>
          <Button
            type="primary"
            icon={<UploadOutlined />}
            onClick={uploadRecordFile}
          >
            上传凭证
          </Button>
        </Form>
      </Modal>
      <Modal
        open={transactionOpen}
        title="登记财务流水"
        okText="保存流水"
        cancelText="取消"
        onOk={createTransaction}
        onCancel={() => setTransactionOpen(false)}
      >
        <Form form={transactionForm} layout="vertical">
          <Form.Item label="关联费用" name="finance_record_id">
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              options={fees.map((x) => ({
                value: x.id,
                label: `${x.serial_no}｜${x.title}`,
              }))}
            />
          </Form.Item>
          <div className="form-grid">
            <Form.Item
              label="流水类型"
              name="transaction_type"
              rules={[{ required: true }]}
            >
              <Select
                options={["付款", "开票", "回款", "退费"].map((v) => ({
                  value: v,
                  label: v,
                }))}
              />
            </Form.Item>
            <Form.Item label="金额" name="amount" rules={[{ required: true }]}>
              <InputNumber min={0.01} precision={2} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item
              label="日期"
              name="transaction_date"
              rules={[{ required: true }]}
            >
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item label="凭证/票号" name="voucher_no">
              <Input />
            </Form.Item>
          </div>
          <Form.Item label="对方单位" name="counterparty">
            <Input />
          </Form.Item>
          <Form.Item label="备注" name="remark">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        width={760}
        open={voucherOpen}
        title={`财务凭证：${voucherTarget?.transaction_type || ""} #${voucherTarget?.id || ""}`}
        footer={null}
        onCancel={() => setVoucherOpen(false)}
      >
        <Alert
          type="info"
          showIcon
          title="凭证与本笔流水单独关联，可在文件中心统一检索和下载。"
        />
        <Table
          className="voucher-table"
          rowKey="id"
          size="small"
          pagination={false}
          dataSource={voucherTarget?.vouchers || []}
          locale={{ emptyText: "尚未上传凭证" }}
          columns={[
            {
              title: "凭证类型",
              dataIndex: "category",
              width: 110,
              render: (v: string) => <Tag color="blue">{v}</Tag>,
            },
            { title: "文件名", dataIndex: "original_name", ellipsis: true },
            {
              title: "大小",
              dataIndex: "size",
              width: 90,
              render: (v: number) => `${(v / 1024).toFixed(1)} KB`,
            },
            { title: "上传人", dataIndex: "uploader", width: 80 },
            {
              title: "操作",
              key: "action",
              width: 125,
              render: (_: unknown, r: Attachment) => (
                <Space size={0}>
                  <Button
                    type="link"
                    icon={<DownloadOutlined />}
                    onClick={() => downloadVoucher(r)}
                  >
                    下载
                  </Button>
                  <Button
                    danger
                    type="link"
                    icon={<DeleteOutlined />}
                    onClick={() => deleteVoucher(r)}
                  >
                    删除
                  </Button>
                </Space>
              ),
            },
          ]}
        />
        <Form
          form={voucherForm}
          layout="vertical"
          className="voucher-upload-form"
        >
          <div className="form-grid">
            <Form.Item
              label="凭证类型"
              name="category"
              rules={[{ required: true }]}
            >
              <Select
                options={["付款凭证", "发票扫描件", "回款凭证", "退费凭证"].map(
                  (v) => ({ value: v, label: v }),
                )}
              />
            </Form.Item>
            <Form.Item label="选择文件" required>
              <input
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.xls,.xlsx"
                onChange={(e) => setVoucherFile(e.target.files?.[0] || null)}
              />
            </Form.Item>
          </div>
          <Form.Item label="附件说明" name="remark">
            <Input />
          </Form.Item>
          <Button
            type="primary"
            icon={<UploadOutlined />}
            onClick={uploadVoucher}
          >
            上传凭证
          </Button>
        </Form>
      </Modal>
      <Modal
        className="finance-settlement-review-modal"
        open={generalSettlementApplyTargets.length > 0}
        title="申请结算"
        okText="申请结算"
        cancelText="取消"
        confirmLoading={generalSettlementBusy}
        onOk={() => void submitGeneralSettlementApply()}
        onCancel={() => {
          setGeneralSettlementApplyTargets([]);
          setGeneralSettlementApplyComment("");
        }}
        destroyOnHidden
      >
        <label className="finance-settlement-review-field">
          <span>备注:</span>
          <Input
            value={generalSettlementApplyComment}
            maxLength={2000}
            onChange={(event) =>
              setGeneralSettlementApplyComment(event.target.value)
            }
          />
        </label>
      </Modal>
      <Modal
        className="finance-settlement-review-modal"
        open={generalSettlementReviewTargets.length > 0}
        title={generalSettlementReviewApproved ? "同意结算" : "拒绝结算"}
        okText={generalSettlementReviewApproved ? "同意" : "提交"}
        cancelText="取消"
        confirmLoading={generalSettlementBusy}
        onOk={() => void submitGeneralSettlementReview()}
        onCancel={() => {
          setGeneralSettlementReviewTargets([]);
          setGeneralSettlementReviewComment("");
        }}
        destroyOnHidden
      >
        <label className="finance-settlement-review-field">
          <span>备注:</span>
          <Input
            value={generalSettlementReviewComment}
            maxLength={2000}
            onChange={(event) =>
              setGeneralSettlementReviewComment(event.target.value)
            }
          />
        </label>
      </Modal>
      <Modal
        className="finance-settlement-review-modal"
        open={generalSettlementPaymentTargets.length > 0}
        title={
          generalSettlementPaymentAction === "paid"
            ? "标记已支付"
            : "回退结算"
        }
        okText="提交"
        cancelText="取消"
        confirmLoading={generalSettlementBusy}
        onOk={() => void submitGeneralSettlementPayment()}
        onCancel={() => {
          setGeneralSettlementPaymentTargets([]);
          setGeneralSettlementPaymentComment("");
        }}
        destroyOnHidden
      >
        <label className="finance-settlement-review-field">
          <span>
            {generalSettlementPaymentAction === "rollback"
              ? "审核备注:"
              : "备注:"}
          </span>
          <Input
            value={generalSettlementPaymentComment}
            maxLength={2000}
            onChange={(event) =>
              setGeneralSettlementPaymentComment(event.target.value)
            }
          />
        </label>
      </Modal>
      <Modal
        className="finance-settlement-review-modal"
        open={archiveSettlementReviewTargets.length > 0}
        title={archiveSettlementReviewApproved ? "同意结算" : "拒绝结算"}
        okText={archiveSettlementReviewApproved ? "同意" : "提交"}
        cancelText="取消"
        confirmLoading={archiveSettlementBusy}
        onOk={() => void submitArchiveSettlementReview()}
        onCancel={() => {
          setArchiveSettlementReviewTargets([]);
          setArchiveSettlementReviewComment("");
        }}
        destroyOnHidden
      >
        <label className="finance-settlement-review-field">
          <span>备注:</span>
          <Input
            value={archiveSettlementReviewComment}
            maxLength={2000}
            onChange={(event) =>
              setArchiveSettlementReviewComment(event.target.value)
            }
          />
        </label>
      </Modal>
      <Modal
        className="finance-settlement-review-modal"
        open={archiveSettlementRollbackTargets.length > 0}
        title={isArchiveSettlementRejectedRoute ? "回滚归档费" : "回滚归档费结算"}
        okText="回滚"
        cancelText="取消"
        confirmLoading={archiveSettlementBusy}
        onOk={() => void submitArchiveSettlementRollback()}
        onCancel={() => {
          setArchiveSettlementRollbackTargets([]);
          setArchiveSettlementRollbackComment("");
        }}
        destroyOnHidden
      >
        <label className="finance-settlement-review-field">
          <span>{isArchiveSettlementRejectedRoute ? "审核备注:" : "备注:"}</span>
          <Input
            value={archiveSettlementRollbackComment}
            maxLength={2000}
            onChange={(event) =>
              setArchiveSettlementRollbackComment(event.target.value)
            }
          />
        </label>
      </Modal>
      <Modal
        className="finance-settlement-review-modal"
        open={archiveSettlementReapplyTargets.length > 0}
        title="重新申请"
        okText="提交"
        cancelText="取消"
        confirmLoading={archiveSettlementBusy}
        onOk={() => void submitArchiveSettlementReapply()}
        onCancel={() => {
          setArchiveSettlementReapplyTargets([]);
          setArchiveSettlementReapplyComment("");
        }}
        destroyOnHidden
      >
        <label className="finance-settlement-review-field">
          <span>备注:</span>
          <Input
            value={archiveSettlementReapplyComment}
            maxLength={2000}
            onChange={(event) =>
              setArchiveSettlementReapplyComment(event.target.value)
            }
          />
        </label>
      </Modal>
      <Modal
        className="finance-settlement-review-modal"
        open={generalSettlementReapplyTargets.length > 0}
        title="重新申请结算"
        okText="提交"
        cancelText="取消"
        confirmLoading={generalSettlementBusy}
        onOk={() => void submitGeneralSettlementReapply()}
        onCancel={() => {
          setGeneralSettlementReapplyTargets([]);
          setGeneralSettlementReapplyComment("");
        }}
        destroyOnHidden
      >
        <label className="finance-settlement-review-field">
          <span>备注:</span>
          <Input
            value={generalSettlementReapplyComment}
            maxLength={2000}
            onChange={(event) =>
              setGeneralSettlementReapplyComment(event.target.value)
            }
          />
        </label>
      </Modal>
      <Modal
        open={reconcileOpen}
        title="生成对账单"
        okText="生成"
        cancelText="取消"
        onOk={createReconciliation}
        onCancel={() => setReconcileOpen(false)}
      >
        <Form form={reconcileForm} layout="vertical">
          <Form.Item
            label="对账周期"
            name="period_type"
            rules={[{ required: true }]}
          >
            <Select
              options={["周对账", "月对账"].map((v) => ({
                value: v,
                label: v,
              }))}
            />
          </Form.Item>
          <Form.Item
            label="起止日期"
            name="period"
            rules={[{ required: true }]}
          >
            <DatePicker.RangePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="差异金额" name="discrepancy_amount">
            <InputNumber precision={2} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="备注" name="remark">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
