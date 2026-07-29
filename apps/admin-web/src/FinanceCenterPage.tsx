import { useEffect, useMemo, useRef, useState } from "react";
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
  Popover,
  Select,
  Space,
  Statistic,
  Table,
  Tabs,
  Tag,
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
import { formatRequiredDate } from "./formSafety";
import RecordImportButton from "./RecordImportButton";
import { ReceiptCreatePage } from "./PlatformFinancePage";
import "./finance-center.css";

type Fee = {
  id: number;
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
const initialSessionUser = () => {
  try {
    return JSON.parse(localStorage.getItem("user") || "{}");
  } catch {
    return {};
  }
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
  const [invoices, setInvoices] = useState<FinanceFlow[]>([]);
  const [refunds, setRefunds] = useState<FinanceFlow[]>([]);
  const [cases, setCases] = useState<Fee[]>([]);
  const openCaseDetail = (caseNo: unknown) => {
    const serialNo = String(caseNo || "").trim();
    if (!serialNo || serialNo === "—") {
      message.warning("当前记录未关联案件");
      return;
    }
    rememberCaseDetailTarget({ serial_no: serialNo });
    onNavigate?.("case-company");
  };
  const openContractDetail = (contractNo: unknown) => {
    const serialNo = String(contractNo || "").trim();
    if (!serialNo || serialNo === "—") {
      message.warning("当前记录未关联合同");
      return;
    }
    rememberContractDetailTarget({ serial_no: serialNo });
    onNavigate?.("contract-company");
  };
  const openCustomerDetail = (customer: unknown, customerNo?: unknown) => {
    const title = String(customer || "").trim();
    const serialNo = String(customerNo || "").trim();
    if (!title && !serialNo) {
      message.warning("当前记录未关联客户");
      return;
    }
    rememberCustomerDetailTarget({ title, serial_no: serialNo });
    onNavigate?.("customer-company");
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
  const [loading, setLoading] = useState(false);
  const [role, setRole] = useState(sessionUser.role || "user");
  const [currentUser, setCurrentUser] = useState({
    username: sessionUser.username || "",
    displayName: sessionUser.display_name || "",
  });
  const [originalQueryDraft, setOriginalQueryDraft] = useState<
    Record<string, any>
  >({});
  const [originalQuery, setOriginalQuery] = useState<Record<string, any>>({});
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
    pageSize: 15,
  });
  const [invoicePendingRows, setInvoicePendingRows] = useState<FinanceFlow[]>([]);
  const [invoicePendingMeta, setInvoicePendingMeta] = useState({
    total: 0,
    totalAmount: 0,
    totalExtraAmount: 0,
    page: 1,
    pageSize: 15,
  });
  const [invoiceCompanyRows, setInvoiceCompanyRows] = useState<FinanceFlow[]>([]);
  const [invoiceCompanyMeta, setInvoiceCompanyMeta] = useState({
    total: 0,
    totalAmount: 0,
    totalExtraAmount: 0,
    page: 1,
    pageSize: 15,
  });
  const [invoiceUnissuedRows, setInvoiceUnissuedRows] = useState<FinanceFlow[]>([]);
  const [invoiceUnissuedMeta, setInvoiceUnissuedMeta] = useState({
    total: 0,
    totalAmount: 0,
    totalInvoiceAmount: 0,
    totalCashedAmount: 0,
    totalPaidAmount: 0,
    page: 1,
    pageSize: 15,
  });
  const [feeQueryRows, setFeeQueryRows] = useState<Fee[]>([]);
  const [feeQueryMeta, setFeeQueryMeta] = useState({
    total: 0,
    page: 1,
    pageSize: 15,
    totals: {} as Record<string, number | null>,
  });
  const [feeQueryExportLoading, setFeeQueryExportLoading] = useState(false);
  const [invoiceExportLoading, setInvoiceExportLoading] = useState(false);
  const [invoiceDetail, setInvoiceDetail] = useState<FinanceFlow | null>(null);
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
  const [settlementBatchAction, setSettlementBatchAction] = useState<
    "hearing_lawyer" | "handling_lawyers" | "assistant" | "case_stage" | null
  >(null);
  const [settlementContext, setSettlementContext] = useState<{
    mode: "tasks" | "logs";
    caseRecord: Fee;
  } | null>(null);
  const [settlementContextRows, setSettlementContextRows] = useState<any[]>([]);
  const [settlementActionLoading, setSettlementActionLoading] = useState(false);
  const [feeOpen, setFeeOpen] = useState(false);
  const [feeDetail, setFeeDetail] = useState<Fee | null>(null);
  useEffect(() => {
    const target = consumeBusinessRecordDetailTarget("finance");
    if (!target) return;
    void (async () => {
      try {
        const { data } = await api.get(`/records/${target.id}`);
        if (data.module !== "finance") throw new Error("关联记录不是费用申请");
        setFeeDetail(data);
      } catch (error: any) {
        message.error(error?.response?.data?.detail || error?.message || "费用详情加载失败");
      }
    })();
  }, []);
  const [invoiceOpen, setInvoiceOpen] = useState(false);
  const [refundOpen, setRefundOpen] = useState(false);
  const [transactionOpen, setTransactionOpen] = useState(false);
  const [reconcileOpen, setReconcileOpen] = useState(false);
  const [incomingOpen, setIncomingOpen] = useState(false);
  const [claimTarget, setClaimTarget] = useState<IncomingPayment | null>(null);
  const [allocateTarget, setAllocateTarget] = useState<IncomingPayment | null>(
    null,
  );
  const [issueTarget, setIssueTarget] = useState<FinanceFlow | null>(null);
  const [voidTarget, setVoidTarget] = useState<FinanceFlow | null>(null);
  const [refundCompleteTarget, setRefundCompleteTarget] =
    useState<FinanceFlow | null>(null);
  const [recordFileTarget, setRecordFileTarget] = useState<FinanceFlow | null>(
    null,
  );
  const [recordFiles, setRecordFiles] = useState<Attachment[]>([]);
  const [recordFile, setRecordFile] = useState<File | null>(null);
  const [voucherOpen, setVoucherOpen] = useState(false);
  const [voucherTarget, setVoucherTarget] = useState<Transaction | null>(null);
  const [voucherFile, setVoucherFile] = useState<File | null>(null);
  const [writeoffTarget, setWriteoffTarget] = useState<Fee | null>(null);
  const bankUploadRef = useRef<HTMLInputElement>(null);
  const [feeForm] = Form.useForm();
  const [invoiceForm] = Form.useForm();
  const [refundForm] = Form.useForm();
  const [issueForm] = Form.useForm();
  const [voidForm] = Form.useForm();
  const [invoiceNumberForm] = Form.useForm();
  const [invoiceDateForm] = Form.useForm();
  const [refundCompleteForm] = Form.useForm();
  const [transactionForm] = Form.useForm();
  const [reconcileForm] = Form.useForm();
  const [voucherForm] = Form.useForm();
  const [writeoffForm] = Form.useForm();
  const [paymentPackageWriteoffForm] = Form.useForm();
  const [recordFileForm] = Form.useForm();
  const [incomingForm] = Form.useForm();
  const [claimForm] = Form.useForm();
  const [allocateForm] = Form.useForm();
  const [settlementBatchForm] = Form.useForm();
  const selectedFeeType = Form.useWatch("fee_type", feeForm);
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
  const isFeeQueryRoute = initialView === "finance-fee-query";
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
    const refundRange = query.routeField3;
    const paidRange = query.routeField7;
    const listValue = (value: unknown) =>
      Array.isArray(value) ? value.join(",") : String(value || "");
    return {
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
    const response = await api.get("/finance/fees/query", {
      params: feeQueryParams(query, page, pageSize),
    });
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
          ? currentUser.displayName || currentUser.username
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
    pageSize = 15,
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
    pageSize = 15,
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
    pageSize = 15,
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
    pageSize = 15,
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
  const load = async () => {
    setLoading(true);
    try {
      const [
        feeRes,
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
      ] = await Promise.all([
        api.get("/records", { params: { module: "finance", page_size: 100 } }),
        api.get("/records", { params: { module: "invoice", page_size: 100 } }),
        api.get("/records", { params: { module: "refund", page_size: 100 } }),
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
        api.get("/finance/payment-packages"),
        isInternalDetailRoute
          ? api.get("/finance/internal-fees", {
              params: internalDetailParams(
                initialView === "finance-internal-detail"
                  ? {
                      routeField7: "全部",
                      routeField9:
                        currentUser.displayName || currentUser.username,
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
              params: invoiceMineParams({}, 1, 15),
            })
          : Promise.resolve({
              data: {
                items: [],
                total: 0,
                total_amount: 0,
                total_extra_amount: 0,
                page: 1,
                page_size: 15,
              },
            }),
        isInvoicePendingRoute
          ? api.get("/finance/invoices", {
              params: invoicePendingParams({}, 1, 15),
            })
          : Promise.resolve({
              data: {
                items: [],
                total: 0,
                total_amount: 0,
                total_extra_amount: 0,
                page: 1,
                page_size: 15,
              },
            }),
        isInvoiceCompanyRoute
          ? api.get("/finance/invoices", {
              params: invoiceCompanyParams({}, 1, 15),
            })
          : Promise.resolve({
              data: {
                items: [],
                total: 0,
                total_amount: 0,
                total_extra_amount: 0,
                page: 1,
                page_size: 15,
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
                15,
              ),
            })
          : Promise.resolve({
              data: {
                items: [],
                total: 0,
                totals: {},
                page: 1,
                page_size: 15,
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
          ? api.get("/finance/fees/query", {
              params: feeQueryParams({}, 1, 15),
            })
          : Promise.resolve({
              data: { items: [], total: 0, totals: {}, page: 1, page_size: 15 },
            }),
      ]);
      setFees(feeRes.data.items);
      setInvoices(invoiceRes.data.items);
      setRefunds(refundRes.data.items);
      setCases(caseRes.data.items);
      setCustomers(customerRes.data.items);
      setReceivables(receivableRes.data.items);
      setIncoming(incomingRes.data.items);
      setTransactions(txRes.data.items);
      setReconciliations(recRes.data.items);
      setSummary(sumRes.data);
      setRole(profileRes.data.role);
      setCurrentUser({
        username: profileRes.data.username || "",
        displayName: profileRes.data.display_name || "",
      });
      setPendingSettlements(settlementRes.data.items);
      setRefundReviewFees(refundReviewRes.data.items);
      setPaymentPackages(paymentPackageRes.data.items);
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
    }
  };
  useEffect(() => {
    setTab(first);
    const defaults =
      initialView === "finance-payment-audit"
        ? { status: "待审批" }
        : initialView === "finance-payment-waiting"
          ? { status: "待付款" }
          : initialView === "finance-payment-print"
            ? { status: "已付款" }
            : initialView === "finance-payment-writeoff"
              ? { status: "待核销" }
              : initialView === "finance-internal-refund-audit"
                ? { routeField1: "待审批" }
                : initialView === "finance-internal-detail"
                  ? {
                      routeField7: "全部",
                      routeField9:
                        currentUser.displayName || currentUser.username,
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
                : {};
    setOriginalQueryDraft(defaults);
    setOriginalQuery(defaults);
    setSelectedOriginalRows([]);
    setPaymentPackagePreview(null);
    setPaymentPackageDetail(null);
    setPaymentPackageWriteoffTarget(null);
    setGeneralSettlementDetails([]);
    load();
  }, [initialView]);
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
  const allocateIncoming = async () => {
    if (!allocateTarget) return;
    const v = await allocateForm.validateFields();
    const amount = Number(v.amount || 0);
    const settlementAmount = v.settlement_amount == null ? null : Number(v.settlement_amount);
    const archiveFee = Number(v.archive_fee || 0);
    if (settlementAmount != null && settlementAmount > amount + 0.001) {
      message.warning("结算金额不能大于本次分配金额");
      return;
    }
    if (archiveFee > 0 && (settlementAmount == null || archiveFee > settlementAmount + 0.001)) {
      message.warning("归档费不能大于结算金额");
      return;
    }
    try {
      await api.post(
        `/finance/incoming-payments/${allocateTarget.id}/allocate`,
        {
          allocations: [
            {
              receivable_plan_id: v.receivable_plan_id,
              amount: v.amount,
              case_no: v.case_no || "",
              settlement_items: v.case_no && settlementAmount != null
                ? [{
                    fee_type: v.settlement_fee_type || "代理费",
                    amount: v.amount,
                    settlement_amount: settlementAmount,
                    archive_fee: archiveFee,
                  }]
                : [],
            },
          ],
          comment: v.comment || "",
        },
      );
      message.success("回款已分配并同步更新合同应收");
      setAllocateTarget(null);
      allocateForm.resetFields();
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "回款分配失败");
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
  const createFee = async () => {
    const v = await feeForm.validateFields();
    try {
      await api.post("/finance/fees", v);
      message.success("费用已创建");
      setFeeOpen(false);
      feeForm.resetFields();
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
    try {
      await api.post(`/finance/fees/${writeoffTarget.id}/writeoff`, values);
      message.success("付款已核销并留痕");
      setWriteoffTarget(null);
      writeoffForm.resetFields();
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "付款核销失败");
    }
  };
  const writeoffPaymentPackage = async () => {
    if (!paymentPackageWriteoffTarget) return;
    const values = await paymentPackageWriteoffForm.validateFields();
    setPaymentPackageLoading(true);
    try {
      await api.post(
        `/finance/payment-packages/${paymentPackageWriteoffTarget.id}/writeoff`,
        {
          amount: values.amount,
          paid_date: formatRequiredDate(values.paid_date, "付款日期"),
          payment_method: values.payment_method,
          invoice_no: values.invoice_no,
          remark: values.remark || "",
        },
      );
      message.success("核销成功.");
      setPaymentPackageWriteoffTarget(null);
      paymentPackageWriteoffForm.resetFields();
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "付款包核销失败");
    } finally {
      setPaymentPackageLoading(false);
    }
  };
  const printPayment = (row: Fee) => {
    const payment = transactions
      .filter(
        (item) =>
          item.finance_record_id === row.id && item.transaction_type === "付款",
      )
      .sort((a, b) =>
        String(b.transaction_date).localeCompare(String(a.transaction_date)),
      )[0];
    if (!payment) {
      message.warning("该请款单尚无付款流水，不能打印付款单");
      return;
    }
    const escape = (value: unknown) =>
      String(value ?? "—").replace(
        /[&<>"']/g,
        (char) =>
          ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;",
          })[char] || char,
      );
    const html = `<!doctype html><html><head><meta charset="utf-8"><title>${escape(row.serial_no)}付款单</title><style>body{font-family:Arial,"Microsoft YaHei",sans-serif;padding:32px;color:#222}h2{text-align:center}table{width:100%;border-collapse:collapse}th,td{padding:10px;border:1px solid #999;text-align:left}th{width:22%;background:#f5f5f5}.footer{margin-top:40px;display:flex;justify-content:space-between}</style></head><body><h2>付款单</h2><table><tr><th>请款单号</th><td>${escape(row.serial_no)}</td><th>付款日期</th><td>${escape(payment.transaction_date)}</td></tr><tr><th>费用名称</th><td colspan="3">${escape(row.title)}</td></tr><tr><th>客户</th><td>${escape(row.customer)}</td><th>案件编号</th><td>${escape(row.data.case_no)}</td></tr><tr><th>收款单位</th><td>${escape(payment.counterparty || row.data.payee)}</td><th>付款金额</th><td>${escape(money(payment.amount || 0))}</td></tr><tr><th>付款凭证号</th><td>${escape(payment.voucher_no)}</td><th>经办人</th><td>${escape(payment.operator)}</td></tr><tr><th>备注</th><td colspan="3">${escape(payment.remark || row.data.description || row.data.remark)}</td></tr></table><div class="footer"><span>制单：${escape(currentUser.displayName || currentUser.username)}</span><span>打印时间：${escape(dayjs().format("YYYY-MM-DD HH:mm"))}</span></div><script>window.onload=()=>window.print()<\/script></body></html>`;
    const url = URL.createObjectURL(
      new Blob([html], { type: "text/html;charset=utf-8" }),
    );
    const popup = window.open(url, "_blank", "noopener,noreferrer");
    if (!popup) message.warning("浏览器拦截了打印窗口，请允许弹出窗口后重试");
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
  };
  const createInvoice = async () => {
    const v = await invoiceForm.validateFields();
    try {
      await api.post("/finance/invoices", v);
      message.success("发票申请草稿已创建");
      setInvoiceOpen(false);
      invoiceForm.resetFields();
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "发票申请创建失败");
    }
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
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "退款申请创建失败");
    }
  };
  const submitFlow = async (kind: "invoices" | "refunds", row: FinanceFlow) => {
    try {
      await api.post(`/finance/${kind}/${row.id}/submit`, {
        comment: "提交财务审批",
      });
      message.success("已提交审批");
      load();
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
          load();
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
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "退款到账登记失败");
    }
  };
  const openRecordFiles = async (row: FinanceFlow, category: string) => {
    try {
      const { data } = await api.get("/attachments", {
        params: { record_id: row.id },
      });
      setRecordFiles(data.items);
      setRecordFileTarget(row);
      setRecordFile(null);
      recordFileForm.setFieldsValue({ category, remark: "" });
    } catch {
      message.error("业务凭证加载失败");
    }
  };
  const uploadRecordFile = async () => {
    if (!recordFileTarget || !recordFile) return message.warning("请选择文件");
    const v = await recordFileForm.validateFields();
    const form = new FormData();
    form.append("file", recordFile);
    form.append("record_id", String(recordFileTarget.id));
    form.append("category", v.category);
    form.append("remark", v.remark || "");
    try {
      await api.post("/attachments", form);
      message.success("业务凭证已上传");
      await openRecordFiles(recordFileTarget, v.category);
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
  const originalIncomingOperation = (_: unknown, r: IncomingPayment) => (
    <Space size={0}>
      {r.status === "待认领" && (
        <Button
          type="link"
          onClick={() => {
            claimForm.resetFields();
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
            onClick={() => {
              allocateForm.resetFields();
              allocateForm.setFieldsValue({ amount: r.remaining_amount });
              setAllocateTarget(r);
            }}
          >
            分配
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
      render: (v: string) => v || "—",
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
    { title: "登记人", dataIndex: "operator", width: 90 },
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
    { title: "操作人", dataIndex: "operator", width: 90 },
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
  ];
  const originalMode = originalFinanceRoutes.includes(initialView);
  const originalKind =
    initialView === "finance-internal-mine"
      ? "internal"
      : ["finance-query", "finance-fee-query"].includes(initialView)
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
    "finance-internal-mine": "我的请款单",
    "finance-internal-settle": "内部提成-待结算",
    "finance-internal-archive": "请款单审批",
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
  };
  const displayedOriginalTitle =
    platformMode && initialView === "finance-payment-mine"
      ? "请款单列表"
      : originalTitle[initialView] || "财务中心";
  const paymentStatuses = [
    "创建待提交",
    "待审批",
    "待付款",
    "待核销",
    "已付款",
    "已驳回",
    "已作废",
  ];
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
    let result = [...fees];
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
        ["已审批", "部分付款"].includes(item.status),
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
    transactions,
    originalQuery,
    originalKind,
    initialView,
    currentUser,
  ]);
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
          disabled={disabled}
          placeholder="请选择"
          options={paymentStatuses.map((value) => ({ value, label: value }))}
          onChange={(value) => setOriginalField(key, value)}
        />
      ) : control === "feeType" ? (
        <Select
          allowClear
          value={originalQueryDraft[key]}
          disabled={disabled}
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
        <DatePicker.RangePicker
          value={originalQueryDraft[key]}
          disabled={disabled}
          onChange={(value) => setOriginalField(key, value)}
        />
      ) : control === "money" ? (
        <Space.Compact>
          <InputNumber
            min={0}
            precision={2}
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
          disabled={disabled}
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
    queryField("费用类型", "feeType", "feeType"),
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
    return (
      <Space size={0}>
        {maySubmit && (
          <Button type="link" onClick={() => feeAction(row, "submit")}>
            提交审批
          </Button>
        )}
        <Button type="link" onClick={() => setFeeDetail(row)}>
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
    <Space size={0}>
      {initialView === "finance-payment-print" && row.status === "已付款" && (
        <Button type="link" onClick={() => printPayment(row)}>
          打印付款单
        </Button>
      )}
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
      {["已审批", "部分付款"].includes(row.status) && (
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
          title="回滚归档费"
          aria-label="回滚归档费"
          icon={<RollbackOutlined />}
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
            onClick={() => openArchiveSettlementReview([row], true)}
          />
          <Button
            type="link"
            title="拒绝支付"
            aria-label="拒绝支付"
            icon={<DeleteOutlined />}
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
      <Button type="link" onClick={() => setPaymentPackageDetail(row)}>
        查看
      </Button>
    ) : (
      <Button
        type="link"
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
      render: (_: unknown, row: Fee) => row.data.applicant || row.owner || "—",
    },
    {
      title: "客户管理人",
      width: 100,
      render: (_: unknown, row: Fee) => row.data.customer_manager || "—",
    },
    {
      title: "交款人",
      width: 90,
      render: (_: unknown, row: Fee) =>
        row.data.payer || row.data.handler || "—",
    },
  ];
  const paymentAuditOriginalColumns = [
    { title: "请款单号", dataIndex: "serial_no", width: 165 },
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
      render: (_: unknown, row: Fee) => row.data.applicant || row.owner || "—",
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
      render: (_: unknown, row: Fee) => row.data.applicant || row.owner || "—",
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
      render: (_: unknown, row: Fee) => row.data.applicant || row.owner || "—",
    },
    {
      title: "经办人",
      width: 90,
      render: (_: unknown, row: Fee) => row.data.handler || row.owner || "—",
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
          : ["待审批", "已审批", "已拒绝", "已作废"],
      defaultValue: "待审批",
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
      <Button type="link" onClick={() => setInvoiceDetail(row)}>
        查看
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
        row.data?.recipient || currentUser.displayName || currentUser.username,
      extra_amount: Number(row.data?.extra_amount || 0),
      invoice_no: "",
      invoice_date: dayjs(),
      comment: "",
    });
    setInvoiceProcess(row);
  };
  const invoicePendingOperation = (_: unknown, row: FinanceFlow) => (
    <Button type="link" onClick={() => openInvoiceProcess(row)}>
      开票
    </Button>
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
      <Button type="link" onClick={() => setInvoiceDetail(row)}>
        查看
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
      票据状态: row.status,
      客户: row.customer || row.claimed_customer,
      客户名称: row.customer || row.claimed_customer,
      客户管理人: data.customer_manager || linkedCaseData.customer_manager,
      案号: data.case_no,
      案件编号: data.case_no,
      案件阶段:
        data.case_stage || linkedCaseData.case_stage || linkedCase?.status,
      结算状态: data.settlement_status || row.status,
      案源人:
        data.case_source ||
        data.source_person ||
        linkedCaseData.case_source ||
        linkedCaseData.business_owner,
      调查员: data.investigator || linkedCaseData.investigator,
      调查人: data.investigator || linkedCaseData.investigator,
      经办律师:
        data.handling_lawyer ||
        data.handler ||
        linkedCaseData.handling_lawyer ||
        linkedCaseData.case_lawyer,
      律师助理:
        data.lawyer_assistant ||
        data.assistant ||
        linkedCaseData.lawyer_assistant ||
        linkedCaseData.assistant,
      品管: data.quality_manager || data.quality_control,
      公证书号: data.certificate_no,
      助理: data.assistant || data.lawyer_assistant,
      开庭律师: data.hearing_lawyer,
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
        data.defendant ||
        linkedCaseData.defendant ||
        linkedCaseData.appellee_names ||
        linkedCaseData.opponent,
      申请人: data.applicant || row.owner,
      申请日期: (data.application_date || row.created_at || "").slice?.(0, 10),
      提交人:
        data.archive_payment_submitted_by || data.submitted_by || row.owner,
      提交日期: (
        data.archive_payment_submitted_at ||
        data.settlement_paid_at ||
        row.created_at ||
        ""
      ).slice?.(0, 10),
      审核人: data.archive_payment_reviewer || data.reviewer,
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
      合同号: data.contract_no,
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
        <Button type="link" onClick={() => openCaseDetail(cellValue(row, header))}>
          {cellValue(row, header)}
        </Button>
      ) : initialView === "finance-internal-settle" && header === "案号" ? (
        <Button type="link" onClick={() => openCaseDetail(cellValue(row, header))}>
          {cellValue(row, header)}
        </Button>
      ) : isInvoiceUnissuedRoute && header === "案号" ? (
        <Button type="link" onClick={() => openCaseDetail(cellValue(row, header))}>
          {cellValue(row, header)}
        </Button>
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
        <Button type="link" onClick={() => openCaseDetail(cellValue(row, header))}>
          {cellValue(row, header)}
        </Button>
      ) : isArchiveSettlementActiveRoute && header === "案号" ? (
        <Button type="link" onClick={() => openCaseDetail(cellValue(row, header))}>
          {cellValue(row, header)}
        </Button>
      ) : isFeeQueryRoute && ["案号", "案件编号"].includes(header) ? (
        <Button type="link" onClick={() => openCaseDetail(cellValue(row, header))}>
          {cellValue(row, header)}
        </Button>
      ) : ["客户", "客户名称", "客户编号"].includes(header) ? (
        <Button
          type="link"
          onClick={() => openFinanceCustomerDetail(row, header)}
        >
          {cellValue(row, header)}
        </Button>
      ) : ["合同号", "合同编号"].includes(header) ? (
        <Button type="link" onClick={() => openContractDetail(cellValue(row, header))}>
          {cellValue(row, header) || "—"}
        </Button>
      ) : (isInvoiceMineRoute || isInvoicePendingRoute || isInvoiceCompanyRoute) && header === "请票单号" ? (
        <Button
          type="link"
          onClick={() =>
            isInvoicePendingRoute
              ? openInvoiceProcess(row)
              : setInvoiceDetail(row)
          }
        >
          {cellValue(row, header)}
        </Button>
      ) : initialView === "finance-internal-payment" &&
        header === "案件编号" ? (
        <Button type="link" onClick={() => openCaseDetail(cellValue(row, header))}>
          {cellValue(row, header)}
        </Button>
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
    let rows: any[] = isFeeQueryRoute
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
      rows = rows.filter((row) => row.status === "待审批");
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
  const reviewNumber = (value: unknown) =>
    value == null || value === "" || Number.isNaN(Number(value))
      ? "—"
      : Number(value).toFixed(2);
  const submitFeeReview = async (approved: boolean) => {
    if (!feeReviewTargets.length) return;
    setFeeReviewLoading(true);
    try {
      if (feeReviewTargets.length === 1) {
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
      message.warning("请先选择需要审批的请款单");
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
        content: "请选择提成.",
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
    setPaymentPackageLoading(true);
    try {
      const { data } = await api.post("/finance/payment-packages/preview", {
        fee_ids: targets.map((row) => row.id),
      });
      setPaymentPackagePreview(data);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "付款包预览生成失败");
    } finally {
      setPaymentPackageLoading(false);
    }
  };
  const submitInternalPaymentPackage = async () => {
    if (!paymentPackagePreview || paymentPackagePreview.submitted) return;
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
    const next = { ...configuredDefaults, ...originalQueryDraft };
    setOriginalQuery(next);
    setSelectedOriginalRows([]);
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
    if (isFeeQueryRoute) {
      setOriginalQueryDraft({});
      setOriginalQuery({});
      setSelectedOriginalRows([]);
      void loadFeeQuery({}, 1, feeQueryMeta.pageSize).catch((error: any) =>
        message.error(error?.response?.data?.detail || "费用查询清空失败"),
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
          message.error(error?.response?.data?.detail || "未开票清空失败"),
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
                currentUser.displayName || currentUser.username || "管理者",
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
    setOriginalQueryDraft({});
    setOriginalQuery({});
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
      const response = await api.get("/finance/fees/query/export", {
        params: {
          ...feeQueryParams(originalQuery, 1, feeQueryMeta.pageSize),
          page: undefined,
          page_size: undefined,
          selected_only: selectedOnly,
          ids: selectedOnly ? selectedOriginalRows.join(",") : undefined,
        },
        responseType: "blob",
      });
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `费用查询-${dayjs().format("YYYY-MM-DD")}.xls`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "费用查询导出失败");
    } finally {
      setFeeQueryExportLoading(false);
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
    const selectedIds = ids || selectedOriginalRows;
    if (!selectedIds.length) {
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
        params: isGeneralSettlementPendingRoute
          ? { kind, ids: selectedIds.join(",") }
          : { kind, application_ids: selectedIds.join(",") },
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
          ? `已同意支付 ${response.data.reviewed} 条归档费`
          : `已拒绝支付 ${response.data.reviewed} 条归档费`,
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
      message.error(error?.response?.data?.detail || "归档费支付审核失败");
    } finally {
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
          : `已回滚 ${response.data.rolled_back} 条归档费支付`,
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
      message.error(error?.response?.data?.detail || "归档费支付回滚失败");
    } finally {
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
      setArchiveSettlementBusy(false);
    }
  };
  const applyGeneralSettlementRows = async (ids?: (string | number)[]) => {
    const selectedIds = ids || selectedOriginalRows;
    if (!selectedIds.length) {
      Modal.info({
        title: "提示",
        content: "请选择需要申请结算的回款.",
        okText: "确定",
      });
      return;
    }
    Modal.confirm({
      title: "申请结算",
      content: `确认将选中的 ${selectedIds.length} 条回款提交结算审批？`,
      okText: "申请结算",
      cancelText: "取消",
      onOk: async () => {
        setGeneralSettlementBusy(true);
        try {
          const response = await api.post(
            "/finance/general-settlements/apply",
            { receipt_ids: selectedIds.map(Number), comment: "待结算页面提交" },
          );
          message.success(`已生成 ${response.data.created} 条结算申请`);
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
      },
    });
  };
  const exportConfiguredRows = (selectedOnly: boolean) => {
    if (!activeRouteConfig) return;
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
  const openSettlementContext = async (mode: "tasks" | "logs") => {
    const linked = selectedSettlementCase();
    if (!linked) return;
    setSettlementActionLoading(true);
    try {
      const { data } = await api.get(
        mode === "tasks"
          ? `/cases/${linked.id}/tasks`
          : `/records/${linked.id}/history`,
      );
      setSettlementContextRows(data.items || []);
      setSettlementContext({ mode, caseRecord: linked });
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "案件信息加载失败");
    } finally {
      setSettlementActionLoading(false);
    }
  };
  const generateSettlementDocument = async (
    key: "authorization" | "law-firm-letter" | "identity" | "settlement",
  ) => {
    const linked = selectedSettlementCase();
    if (!linked) return;
    const specs = {
      authorization: {
        name: "授权委托书",
        category: "诉讼文书",
        fields: ["委托人", "受托人", "委托事项", "委托权限", "委托期限"],
      },
      "law-firm-letter": {
        name: "律所函",
        category: "诉讼文书",
        fields: ["收函单位", "案件基本信息", "律师意见", "联系方式"],
      },
      identity: {
        name: "身份证明",
        category: "诉讼文书",
        fields: ["主体信息", "法定代表人或负责人", "身份证明事项", "签章"],
      },
      settlement: {
        name: "结算提成表",
        category: "内部表单",
        fields: ["案件信息", "费用明细", "提成计算", "复核意见"],
      },
    } as const;
    const spec = specs[key];
    setSettlementActionLoading(true);
    try {
      const templateResponse = await api.get("/templates");
      let template = templateResponse.data.items.find(
        (item: any) => item.is_active !== false && item.name === spec.name,
      );
      if (!template) {
        template = (
          await api.post("/templates", {
            name: spec.name,
            category: spec.category,
            version: "1.0",
            description: "内部提成待结算页案件文书模板",
            fields: [...spec.fields],
          })
        ).data;
      }
      const title = `${spec.name}-${linked.serial_no}`;
      const generated = await api.post("/agent/documents", {
        template_id: template.id,
        record_id: linked.id,
        title,
        instruction:
          "请依据案件现有资料生成；不得虚构事实，缺失信息标记为【待补充】。",
      });
      const response = await api.get(
        `/agent/documents/${generated.data.id}/download`,
        { responseType: "blob" },
      );
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${title}.docx`;
      anchor.click();
      URL.revokeObjectURL(url);
      message.success(`${spec.name}已生成并下载`);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "文书生成失败");
    } finally {
      setSettlementActionLoading(false);
    }
  };
  const openSettlementBatch = (
    action: "hearing_lawyer" | "handling_lawyers" | "assistant" | "case_stage",
  ) => {
    const linked = selectedSettlementCases();
    if (!linked.length) return;
    settlementBatchForm.resetFields();
    setSettlementBatchAction(action);
  };
  const submitSettlementBatch = async () => {
    if (!settlementBatchAction) return;
    const linked = selectedSettlementCases();
    if (!linked.length) return;
    const values = await settlementBatchForm.validateFields();
    const value = String(values.value || "").trim();
    const body: Record<string, any> = {
      case_ids: linked.map((row) => row.id),
      comment: values.comment || "待结算列表批量修改",
    };
    body[settlementBatchAction] =
      settlementBatchAction === "handling_lawyers"
        ? value
            .split(/[，,]/)
            .map((item) => item.trim())
            .filter(Boolean)
        : value;
    setSettlementActionLoading(true);
    try {
      const { data } = await api.post("/cases/batch-update", body);
      message.success(`已修改 ${data.updated} 个案件`);
      setSettlementBatchAction(null);
      setSelectedOriginalRows([]);
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "批量修改失败");
    } finally {
      setSettlementActionLoading(false);
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
      const linked = selectedSettlementCase();
      if (!linked) return;
      feeForm.resetFields();
      feeForm.setFieldsValue({
        fee_type: feeTypeByKey[key],
        case_no: linked.serial_no,
        customer: linked.customer,
        handler: currentUser.username,
      });
      setFeeOpen(true);
      return;
    }
    if (key === "upload") {
      const linked = selectedSettlementCase();
      if (linked) void openRecordFiles(linked, "案件文档");
    }
    if (
      [
        "hearing_lawyer",
        "handling_lawyers",
        "assistant",
        "case_stage",
      ].includes(key)
    )
      openSettlementBatch(
        key as
          "hearing_lawyer" | "handling_lawyers" | "assistant" | "case_stage",
      );
    if (
      ["authorization", "law-firm-letter", "identity", "settlement"].includes(
        key,
      )
    )
      void generateSettlementDocument(
        key as "authorization" | "law-firm-letter" | "identity" | "settlement",
      );
    if (key === "tasks") void openSettlementContext("tasks");
    if (key === "logs") void openSettlementContext("logs");
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
            {feeDetail.data.customer_manager || "—"}
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
                        feeDetail.data.payee ||
                        feeDetail.data.applicant ||
                        feeDetail.owner ||
                        "—",
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
            {(invoiceDetailData.applicant || invoiceDisplay.owner) === currentUser.username
              ? currentUser.displayName || currentUser.username
              : invoiceDetailData.applicant || invoiceDisplay.owner}
          </Descriptions.Item>
          <Descriptions.Item label="申请备注" span={4}>{invoiceDetailData.remark || ""}</Descriptions.Item>
        </> : invoiceCancel ? <>
          <Descriptions.Item label="合同编号">{invoiceDetailData.contract_no ? <Button type="link" onClick={() => openContractDetail(invoiceDetailData.contract_no)}>{invoiceDetailData.contract_no}</Button> : ""}</Descriptions.Item>
          <Descriptions.Item label="外部合同号">{invoiceDetailData.external_contract_no || ""}</Descriptions.Item>
          <Descriptions.Item label="合同名称">{invoiceDetailData.contract_name || ""}</Descriptions.Item>
          <Descriptions.Item label="客户名称">{invoiceDisplay.customer ? <Button type="link" onClick={() => openCustomerDetail(invoiceDisplay.customer, invoiceDetailData.customer_no)}>{invoiceDisplay.customer}</Button> : "—"}</Descriptions.Item>
          <Descriptions.Item label="开票申请人">
            {(invoiceDetailData.applicant || invoiceDisplay.owner) === currentUser.username
              ? currentUser.displayName || currentUser.username
              : invoiceDetailData.applicant || invoiceDisplay.owner}
          </Descriptions.Item>
          <Descriptions.Item label="开票申请号">{invoiceDisplay.serial_no}</Descriptions.Item>
          <Descriptions.Item label="申请日期">
            {dayjs(invoiceDetailData.application_date || invoiceDisplay.created_at).format("YYYY年MM月DD日")}
          </Descriptions.Item>
          <Descriptions.Item label="申请备注">{invoiceDetailData.remark || ""}</Descriptions.Item>
          <Descriptions.Item label="发票号">{invoiceDetailData.invoice_no || ""}</Descriptions.Item>
          <Descriptions.Item label="票据状态">{invoiceDisplay.status}</Descriptions.Item>
          <Descriptions.Item label="领票人">{invoiceDetailData.recipient || ""}</Descriptions.Item>
        </> : <>
          <Descriptions.Item label="开票申请人">
            {(invoiceDetailData.applicant || invoiceDisplay.owner) === currentUser.username
              ? currentUser.displayName || currentUser.username
              : invoiceDetailData.applicant || invoiceDisplay.owner}
          </Descriptions.Item>
          <Descriptions.Item label="开票申请号">{invoiceDisplay.serial_no}</Descriptions.Item>
          <Descriptions.Item label="申请日期">
            {dayjs(invoiceDetailData.application_date || invoiceDisplay.created_at).format("YYYY年MM月DD日")}
          </Descriptions.Item>
          <Descriptions.Item label="客户名称">{invoiceDisplay.customer ? <Button type="link" onClick={() => openCustomerDetail(invoiceDisplay.customer, invoiceDetailData.customer_no)}>{invoiceDisplay.customer}</Button> : "—"}</Descriptions.Item>
          <Descriptions.Item label="发票号">{invoiceDetailData.invoice_no || ""}</Descriptions.Item>
          <Descriptions.Item label="票据状态">{invoiceDisplay.status}</Descriptions.Item>
          <Descriptions.Item label="领票人">{invoiceDetailData.recipient || ""}</Descriptions.Item>
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
                  index === (invoiceProcess ? 2 : invoiceCancel ? 2 : 4) && value ? (
                    <td key={index}><Button type="link" onClick={() => openCaseDetail(value)}>{value}</Button></td>
                  ) : <td key={index}>{value}</td>,
                )}
            <td>{invoiceDetailData.fee_type || "律师代理费"}</td>
            <td>{Number(invoiceDetailData.amount || 0).toFixed(2)}</td>
            <td>{Number(invoiceDetailData.received_amount || 0).toFixed(2)}</td>
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
  if (initialView === "finance-receipts-new") return <ReceiptCreatePage />;

  return (
    <>
      {invoiceDetailPage ||
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
            <div className="finance-original-query-grid">{originalFields}</div>
            <div className="finance-original-query-actions">
              <Button
                type="primary"
                onClick={submitConfiguredQuery}
              >
                查询
              </Button>
              {activeRouteConfig?.upload && (
                <Button
                  icon={<UploadOutlined />}
                  onClick={() => bankUploadRef.current?.click()}
                >
                  上传
                </Button>
              )}
              {(originalKind === "fee-query" || activeRouteConfig?.clear) && (
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
                                  审核人: {row.data?.reviewer || "—"}
                                  <br />提交人: {row.data?.applied_by || row.owner || "—"}
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
                                  审核人: {row.data?.reviewer || "—"}
                                  <br />提交人: {row.data?.applied_by || row.owner || "—"}
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
                                  <br />提交人: {row.data?.applied_by || row.owner || "—"}
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
                                  { title: "案号", dataIndex: "case_no", width: 144, render: (value) => <Button type="link" onClick={() => openCaseDetail(value)}>{value || "—"}</Button> },
                                  { title: "阶段", dataIndex: "case_stage", width: 115 },
                                  { title: <span className="finance-stacked-header"><span>费用</span><span>类型</span></span>, dataIndex: "fee_type", width: 115 },
                                  { title: <span className="finance-stacked-header"><span>费用</span><span>总金额</span></span>, dataIndex: "fee_total_amount", width: 115, align: "right", render: (value) => value == null ? "—" : Number(value).toFixed(2) },
                                  { title: <span className="finance-stacked-header"><span>费用</span><span>分配金额</span></span>, dataIndex: "fee_allocated_amount", width: 115, align: "right", render: (value) => value == null ? "—" : Number(value).toFixed(2) },
                                  { title: <span className="finance-stacked-header"><span>本笔</span><span>分配金额</span></span>, dataIndex: "current_amount", width: 115, align: "right", render: (value) => value == null ? "—" : Number(value).toFixed(2) },
                                  { title: <span className="finance-stacked-header"><span>本笔</span><span>分配日期</span></span>, dataIndex: "allocated_at", width: 173, render: (value) => String(value || "").replace("T", " ") || "—" },
                                  { title: <span className="finance-stacked-header"><span>本笔</span><span>结算金额</span></span>, dataIndex: "settlement_amount", width: 115, align: "right", render: (value) => value == null ? "—" : Number(value).toFixed(2) },
                                  { title: <span className="finance-stacked-header"><span>本笔</span><span>归档费</span></span>, dataIndex: "archive_fee", width: 115, align: "right", render: (value) => value == null ? "—" : Number(value).toFixed(2) },
                                  { title: "客户", dataIndex: "customer", width: 216, render: (value, detail: any) => value ? <Button type="link" onClick={() => openCustomerDetail(value, detail.customer_no)}>{value}</Button> : "—" },
                                  { title: <span className="finance-stacked-header"><span>经办</span><span>律师</span></span>, dataIndex: "handling_lawyer", width: 115 },
                                  { title: <span className="finance-stacked-header"><span>律师</span><span>助理</span></span>, dataIndex: "assistant", width: 115 },
                                  { title: "合同号", dataIndex: "contract_no", width: 144, render: (value) => <Button type="link" onClick={() => openContractDetail(value)}>{value || "—"}</Button> },
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
                                  <>归档费审核人: {row.data?.archive_payment_reviewer || "—"}<br /></>
                                )}
                                归档审核人: {row.data?.archive_reviewer || "—"}
                                <br />归档申请人: {row.data?.archive_submitter || "—"}
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
                  isFeeQueryRoute && configuredRows.length
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
                  isFeeQueryRoute
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
                  activeRouteConfig
                    ? activeRouteConfig.selectable
                      ? {
                          selectedRowKeys: selectedOriginalRows,
                          onChange: (keys) =>
                            setSelectedOriginalRows(
                              keys as (string | number)[],
                            ),
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
                    : [
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
                      : 20,
                  pageSizeOptions: [
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
                    : undefined,
                  showSizeChanger: true,
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
                  emptyText: isInternalDetailRoute || isFeeQueryRoute
                    ? "没有查询到符合条件的记录 。"
                    : "没有查询到符合条件的记录。",
                }}
              />
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
                        同意结算
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
                        拒绝结算
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
                {isInvoiceUnissuedRoute ? (
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
                      <Button loading={invoiceExportLoading}>导出</Button>
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
                      <Button loading={settlementActionLoading}>
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
                      loading={invoiceExportLoading}
                      onClick={() => void exportInvoiceList(false)}
                    >
                      导出全部
                    </Button>
                    <Button
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
                  {["fees", "audit"].includes(tab) && (
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={() => {
                        feeForm.setFieldsValue({
                          fee_type: "官方费用",
                          handler:
                            currentUser.displayName ||
                            currentUser.username ||
                            "管理者",
                        });
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
                        invoiceForm.setFieldsValue({
                          invoice_type: "增值税普通发票",
                          invoice_content: "法律服务费",
                          delivery_method: "电子发票",
                        });
                        setInvoiceOpen(true);
                      }}
                    >
                      发票申请
                    </Button>
                  )}
                  {tab === "refunds" && (
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={() => {
                        refundForm.setFieldsValue({
                          applicant:
                            currentUser.displayName ||
                            currentUser.username ||
                            "管理者",
                          reason: "诉讼费退费",
                        });
                        setRefundOpen(true);
                      }}
                    >
                      退款申请
                    </Button>
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
        open={Boolean(feeReviewTargets.length)}
        title={<h5>提成审批</h5>}
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
          dataSource={feeReviewRows}
          columns={[
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
        />
      </Drawer>
      <Modal
        open={Boolean(settlementBatchAction)}
        title={
          {
            hearing_lawyer: "批量修改开庭律师",
            handling_lawyers: "批量修改经办律师",
            assistant: "批量修改律师助理",
            case_stage: "批量修改案件阶段",
          }[settlementBatchAction || "hearing_lawyer"]
        }
        okText="保存修改"
        cancelText="取消"
        confirmLoading={settlementActionLoading}
        onOk={submitSettlementBatch}
        onCancel={() => setSettlementBatchAction(null)}
        destroyOnHidden
      >
        <Alert
          type="info"
          showIcon
          title={`将修改已选费用关联的 ${new Set(selectedSettlementRows.map((row) => row.data?.case_id || row.data?.case_no).filter(Boolean)).size} 个案件`}
          style={{ marginBottom: 16 }}
        />
        <Form form={settlementBatchForm} layout="vertical">
          <Form.Item
            label={
              settlementBatchAction === "handling_lawyers"
                ? "经办律师（多人用逗号分隔）"
                : "修改为"
            }
            name="value"
            rules={[{ required: true, message: "请输入修改后的内容" }]}
          >
            <Input
              placeholder={
                settlementBatchAction === "handling_lawyers"
                  ? "例如：张律师，李律师"
                  : "请输入"
              }
            />
          </Form.Item>
          <Form.Item label="修改说明" name="comment">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        width={900}
        open={Boolean(settlementContext)}
        title={`${settlementContext?.caseRecord.serial_no || ""}｜${settlementContext?.mode === "tasks" ? "案件任务" : "案件日志"}`}
        footer={
          <Button onClick={() => setSettlementContext(null)}>关闭</Button>
        }
        onCancel={() => setSettlementContext(null)}
      >
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
                  { title: "任务编号", dataIndex: "serial_no", width: 150 },
                  { title: "任务名称", dataIndex: "title", width: 200 },
                  { title: "状态", dataIndex: "status", width: 90 },
                  { title: "负责人", dataIndex: "owner", width: 100 },
                  { title: "截止日期", dataIndex: "deadline", width: 120 },
                ]
              : [
                  { title: "操作", dataIndex: "action", width: 130 },
                  {
                    title: "状态变化",
                    key: "status",
                    width: 150,
                    render: (_: unknown, row: any) =>
                      `${row.from_status || "—"} → ${row.to_status || "—"}`,
                  },
                  { title: "操作人", dataIndex: "operator", width: 100 },
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
            <Input />
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
        open={Boolean(claimTarget)}
        title={`认领到账：${claimTarget?.receipt_no || ""}`}
        okText="确认认领"
        cancelText="取消"
        onOk={claimIncoming}
        onCancel={() => setClaimTarget(null)}
      >
        <Alert
          type="warning"
          showIcon
          title={`付款户名：${claimTarget?.payer_name || ""}；金额：${claimTarget?.amount == null ? "无权限" : money(claimTarget.amount)}`}
          description="请核对付款单位和客户主体，认领错误会影响后续合同结算。"
          style={{ marginBottom: 16 }}
        />
        <Form form={claimForm} layout="vertical">
          <Form.Item
            label="认领至客户"
            name="customer"
            rules={[{ required: true }]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              options={customers.map((x) => ({
                value: x.title,
                label: `${x.title}｜${x.owner}`,
              }))}
            />
          </Form.Item>
          <Form.Item label="认领说明" name="comment">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        width={720}
        open={Boolean(allocateTarget)}
        title={`分配回款：${allocateTarget?.receipt_no || ""}`}
        okText="确认分配"
        cancelText="取消"
        onOk={allocateIncoming}
        onCancel={() => setAllocateTarget(null)}
      >
        <Alert
          type="info"
          showIcon
          title={`认领客户：${allocateTarget?.claimed_customer || ""}；未分配余额：${allocateTarget?.remaining_amount == null ? "无权限" : money(allocateTarget.remaining_amount)}`}
          description="本次可分配到一个合同应收计划及其案件；剩余金额可继续分配。"
          style={{ marginBottom: 16 }}
        />
        <Form form={allocateForm} layout="vertical">
          <Form.Item
            label="合同应收计划"
            name="receivable_plan_id"
            rules={[{ required: true }]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              options={receivables
                .filter(
                  (x) =>
                    x.customer === allocateTarget?.claimed_customer &&
                    x.remaining_amount > 0,
                )
                .map((x) => ({
                  value: x.id,
                  label: `${x.contract_no}｜${x.phase}｜未收 ${money(x.remaining_amount)}`,
                }))}
              onChange={(id) => {
                const plan = receivables.find((x) => x.id === id);
                if (plan && allocateTarget?.remaining_amount != null) {
                  const allocationAmount = Math.min(
                    plan.remaining_amount,
                    allocateTarget.remaining_amount,
                  );
                  allocateForm.setFieldValue(
                    "amount",
                    allocationAmount,
                  );
                  allocateForm.setFieldValue("settlement_amount", allocationAmount);
                }
                allocateForm.setFieldValue("case_no", undefined);
              }}
            />
          </Form.Item>
          <Form.Item label="关联合同案件（可选）" name="case_no">
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              options={cases
                .filter((x) => x.customer === allocateTarget?.claimed_customer)
                .map((x) => ({
                  value: x.serial_no,
                  label: `${x.serial_no}｜${x.title}`,
                }))}
            />
          </Form.Item>
          <Form.Item
            label="本次分配金额"
            name="amount"
            rules={[{ required: true }]}
          >
            <InputNumber
              min={0.01}
              max={allocateTarget?.remaining_amount || undefined}
              precision={2}
              style={{ width: "100%" }}
            />
          </Form.Item>
          <Form.Item label="分配说明" name="comment">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item label="结算费用类型" name="settlement_fee_type" initialValue="代理费">
            <Select options={["代理费", "官方费用", "其他费用"].map((value) => ({ value, label: value }))} />
          </Form.Item>
          <Form.Item label="本笔结算金额" name="settlement_amount">
            <InputNumber min={0} precision={2} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="本笔归档费" name="archive_fee" initialValue={0}>
            <InputNumber min={0} precision={2} style={{ width: "100%" }} />
          </Form.Item>
        </Form>
        {Boolean(allocateTarget?.allocations?.length) && (
          <Table
            style={{ marginTop: 16 }}
            size="small"
            pagination={false}
            rowKey="transaction_id"
            dataSource={allocateTarget?.allocations || []}
            columns={[
              { title: "已分配合同", dataIndex: "contract_no", render: (v: string) => v ? <Button type="link" onClick={() => openContractDetail(v)}>{v}</Button> : "—" },
              { title: "应收阶段", dataIndex: "phase" },
              {
                title: "案件",
                dataIndex: "case_no",
                render: (v: string) => v ? <Button type="link" onClick={() => openCaseDetail(v)}>{v}</Button> : "—",
              },
              { title: "金额", dataIndex: "amount", render: money },
            ]}
          />
        )}
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
            <InputNumber precision={2} style={{ width: "100%" }} />
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
              {feeDetail.data.applicant || feeDetail.owner || "—"}
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
        open={feeOpen}
        title="新增费用"
        okText="保存草稿"
        cancelText="取消"
        onOk={createFee}
        onCancel={() => setFeeOpen(false)}
      >
        <Form form={feeForm} layout="vertical">
          <Form.Item label="费用名称" name="title" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <div className="form-grid">
            <Form.Item
              label="费用类型"
              name="fee_type"
              rules={[{ required: true }]}
            >
              <Select options={feeTypes.map((v) => ({ value: v, label: v }))} />
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
        </Form>
      </Modal>
      <Modal
        width={760}
        open={invoiceOpen}
        title="新增发票申请"
        okText="保存草稿"
        cancelText="取消"
        onOk={createInvoice}
        onCancel={() => setInvoiceOpen(false)}
      >
        <Form form={invoiceForm} layout="vertical">
          <div className="form-grid">
            <Form.Item className="span-2" label="关联案件" name="case_no">
              <Select
                allowClear
                showSearch
                optionFilterProp="label"
                options={cases.map((x) => ({
                  value: x.serial_no,
                  label: `${x.serial_no}｜${x.customer}｜${x.title}`,
                }))}
                onChange={(no) => {
                  const item = cases.find((x) => x.serial_no === no);
                  if (item)
                    invoiceForm.setFieldValue("customer", item.customer);
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
              label="开票金额"
              name="amount"
              rules={[{ required: true }]}
            >
              <InputNumber min={0.01} precision={2} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item
              label="发票抬头"
              name="invoice_title"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              label="纳税人识别号"
              name="taxpayer_id"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <Form.Item label="公司电话" name="invoice_phone"><Input /></Form.Item>
            <Form.Item label="银行账号" name="bank_account"><Input /></Form.Item>
            <Form.Item label="开户银行" name="bank_name"><Input /></Form.Item>
            <Form.Item label="开票地址" name="invoice_address"><Input /></Form.Item>
            <Form.Item label="高开发票金额" name="extra_amount">
              <InputNumber min={0} precision={2} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item
              label="发票类型"
              name="invoice_type"
              rules={[{ required: true }]}
            >
              <Select
                options={[
                  "增值税普通发票",
                  "增值税专用发票",
                  "电子普通发票",
                  "电子专用发票",
                ].map((v) => ({ value: v, label: v }))}
              />
            </Form.Item>
            <Form.Item
              label="开票内容"
              name="invoice_content"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <Form.Item label="交付方式" name="delivery_method">
              <Select
                options={["电子发票", "邮寄纸质发票", "现场领取"].map((v) => ({
                  value: v,
                  label: v,
                }))}
              />
            </Form.Item>
            <Form.Item label="接收邮箱" name="email">
              <Input />
            </Form.Item>
            <Form.Item label="收件人" name="recipient">
              <Input />
            </Form.Item>
            <Form.Item label="联系电话" name="recipient_phone">
              <Input />
            </Form.Item>
            <Form.Item
              className="span-2"
              label="邮寄地址"
              name="delivery_address"
            >
              <Input />
            </Form.Item>
            <Form.Item className="span-2" label="备注" name="remark">
              <Input.TextArea rows={2} />
            </Form.Item>
          </div>
        </Form>
      </Modal>
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
        title={`业务凭证：${recordFileTarget?.serial_no || ""}`}
        footer={null}
        onCancel={() => setRecordFileTarget(null)}
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
              <Select
                options={[
                  "发票扫描件",
                  "退费凭证",
                  "法院退费通知",
                  "银行回单",
                  "其他财务材料",
                ].map((v) => ({ value: v, label: v }))}
              />
            </Form.Item>
            <Form.Item label="选择文件" required>
              <input
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.xls,.xlsx"
                onChange={(e) => setRecordFile(e.target.files?.[0] || null)}
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
        title={archiveSettlementReviewApproved ? "同意支付" : "拒绝支付"}
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
        title={isArchiveSettlementRejectedRoute ? "回滚归档费" : "回滚支付"}
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
