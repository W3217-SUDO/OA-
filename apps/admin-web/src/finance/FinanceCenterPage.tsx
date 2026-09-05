import {
ArrowUpOutlined,
BookOutlined,
CheckCircleOutlined,
DeleteOutlined,
DownloadOutlined,
MinusCircleOutlined,
PlusCircleOutlined,
RollbackOutlined,
ShareAltOutlined
} from "@ant-design/icons";
import {
Alert,
Button,
Checkbox,
DatePicker,
Descriptions,
Form,
Input,
InputNumber,
message,
Modal,
Popover,
Select,
Space,
Table,
Tabs
} from "antd";
import dayjs from "dayjs";
import { useEffect,useMemo,useRef,useState } from "react";
import { api } from "../api";
import { consumeBusinessRecordDetailTarget } from "../businessRecordDetailNavigation";
import {
consumeDashboardFeeQuery,
preserveDashboardFeeQueryContext,
} from "../dashboardFeeNavigation.mjs";
import "../finance-center.css";
import {
caseFeeRefundStatusLabel,
createLatestRequestGuard,
refundStatusForRoute
} from "../financeRefundHelpers.mjs";
import { resolveIncomingPaymentDetailTarget } from "../incomingPaymentDetailNavigation";
import JarFeeManager from "../JarFeeManager";
import { ReceiptCreatePage } from "../PlatformFinancePage";
import { createConfiguredColumns } from "./columns/configuredColumns";
import { createFeeColumns } from "./columns/feeColumns";
import { createFeeQueryOriginalColumns } from "./columns/feeQueryOriginalColumns";
import { createIncomingColumns } from "./columns/incomingColumns";
import { createInternalOriginalColumns } from "./columns/internalOriginalColumns";
import { createInvoiceColumns } from "./columns/invoiceColumns";
import { createPaymentAuditOriginalColumns } from "./columns/paymentAuditOriginalColumns";
import { createPaymentOriginalColumns } from "./columns/paymentOriginalColumns";
import { createReconcileColumns } from "./columns/reconcileColumns";
import { createRefundColumns } from "./columns/refundColumns";
import { createTransactionColumns } from "./columns/transactionColumns";
import { createRouteConfigs } from "./config/routeConfigs";
import {
buildInvoiceSourceFields,
effectivePaymentQuery,
feeTypes,
internalApprovalRoutes,
invoiceFeeAvailableAmount,
invoiceLegacyDefaultPageSize,
invoiceLegacyErrorMessage,
matchesContractPaymentSource,
money,
paymentQueryControlledPageSize,
paymentQueryDefaultPageSize,
paymentQueryFeeTypeControl,
paymentQueryLegacyErrorMessage,
paymentQueryLegacyStatusMatrix,
paymentQueryQuickPageResult,
paymentWriteoffClearQuery,
settlementLegacyErrorMessage,
voucherCategory
} from "./constants";
import { FinanceCenterView } from "./FinanceCenterView";
import { useFinanceRuntimeContext } from "./hooks/useFinanceRuntimeContext";
import { createFinanceAccountingActions } from "./services/accountingActions";
import { createFinanceDocumentsActions } from "./services/documentsActions";
import { createFinanceInvoicesActions } from "./services/invoicesActions";
import { createFinancePaymentsActions } from "./services/paymentsActions";
import { createFinanceQueriesActions } from "./services/queriesActions";
import { createFinanceRefundsActions } from "./services/refundsActions";
import { createFinanceSettlementsActions } from "./services/settlementsActions";
import { createFinanceWorkflowActions } from "./services/workflowActions";
import type {
AllocationCandidate,
Attachment,
Fee,
FinanceFlow,
FinancePersonOption,
IncomingPayment,
LegacyFinanceRecord,
LegacyFinanceSummary,OriginalFieldSpec,OriginalRouteConfig,PaymentPackagePreview,
PaymentPrintDocumentData,
Receivable,
Reconciliation,
Transaction
} from "./types";

export default function FinanceCenterPage({
  initialView,
  platformMode = false,
  onNavigate,
}: {
  initialView: string;
  platformMode?: boolean;
  onNavigate?: (route: string) => void;
}) {
  const { sessionUser, financeActionGates, refundRequestGuard, invoiceDetailRequestGuard, refundDetailRequestGuard, contractPaymentSourceSearch, contractPaymentSource } = useFinanceRuntimeContext(initialView);

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
  const { openCaseDetail, openContractDetail, openCustomerDetail, loadInternalDetails, load, loadLegacyFinanceHistory, openLegacyFinanceDetail, exportInternalDetails, exportConfiguredRows } = createFinanceQueriesActions({
    get onNavigate() { return onNavigate; },
    get internalDetailMeta() { return internalDetailMeta; },
    get internalDetailParams() { return internalDetailParams; },
    get setInternalDetailRows() { return setInternalDetailRows; },
    get setInternalDetailMeta() { return setInternalDetailMeta; },
    get setLoading() { return setLoading; },
    get setFinanceDataReady() { return setFinanceDataReady; },
    get initialView() { return initialView; },
    get loadPaymentQueryPage() { return loadPaymentQueryPage; },
    get paymentQueryPageSize() { return paymentQueryPageSize; },
    get contractPaymentSource() { return contractPaymentSource; },
    get loadRefunds() { return loadRefunds; },
    get refundMeta() { return refundMeta; },
    get activeRefundStatus() { return activeRefundStatus; },
    get isRefundNotRequiredRoute() { return isRefundNotRequiredRoute; },
    get paymentPackageMeta() { return paymentPackageMeta; },
    get isInternalDetailRoute() { return isInternalDetailRoute; },
    get currentUser() { return currentUser; },
    get isInvoiceMineRoute() { return isInvoiceMineRoute; },
    get invoiceMineParams() { return invoiceMineParams; },
    get isInvoicePendingRoute() { return isInvoicePendingRoute; },
    get invoicePendingParams() { return invoicePendingParams; },
    get isInvoiceCompanyRoute() { return isInvoiceCompanyRoute; },
    get invoiceCompanyParams() { return invoiceCompanyParams; },
    get isInvoiceUnissuedRoute() { return isInvoiceUnissuedRoute; },
    get invoiceUnissuedParams() { return invoiceUnissuedParams; },
    get isGeneralSettlementRoute() { return isGeneralSettlementRoute; },
    get isGeneralSettlementPendingRoute() { return isGeneralSettlementPendingRoute; },
    get generalSettlementParams() { return generalSettlementParams; },
    get isArchiveSettlementActiveRoute() { return isArchiveSettlementActiveRoute; },
    get isArchiveSettlementPaymentRoute() { return isArchiveSettlementPaymentRoute; },
    get isArchiveSettlementPaidRoute() { return isArchiveSettlementPaidRoute; },
    get isArchiveSettlementRejectedRoute() { return isArchiveSettlementRejectedRoute; },
    get archiveSettlementParams() { return archiveSettlementParams; },
    get isFeeQueryRoute() { return isFeeQueryRoute; },
    get isRefundCaseFeeRoute() { return isRefundCaseFeeRoute; },
    get feeQueryParams() { return feeQueryParams; },
    get dashboardFeeQuerySeed() { return dashboardFeeQuerySeed; },
    get setFees() { return setFees; },
    get setFinanceFeeListMeta() { return setFinanceFeeListMeta; },
    get setPaymentQueryMeta() { return setPaymentQueryMeta; },
    get setContractPayments() { return setContractPayments; },
    get setInvoices() { return setInvoices; },
    get setRefunds() { return setRefunds; },
    get setRefundMeta() { return setRefundMeta; },
    get setSelectedRefundRows() { return setSelectedRefundRows; },
    get setCases() { return setCases; },
    get setCustomers() { return setCustomers; },
    get setReceivables() { return setReceivables; },
    get setIncoming() { return setIncoming; },
    get setSelectedIncomingRows() { return setSelectedIncomingRows; },
    get setTransactions() { return setTransactions; },
    get setReconciliations() { return setReconciliations; },
    get setSummary() { return setSummary; },
    get setRole() { return setRole; },
    get setCurrentUser() { return setCurrentUser; },
    get setFinancePeople() { return setFinancePeople; },
    get setPendingSettlements() { return setPendingSettlements; },
    get setRefundReviewFees() { return setRefundReviewFees; },
    get setPaymentPackages() { return setPaymentPackages; },
    get setPaymentPackageMeta() { return setPaymentPackageMeta; },
    get setInvoiceMineRows() { return setInvoiceMineRows; },
    get setInvoiceMineMeta() { return setInvoiceMineMeta; },
    get setInvoicePendingRows() { return setInvoicePendingRows; },
    get setInvoicePendingMeta() { return setInvoicePendingMeta; },
    get setInvoiceCompanyRows() { return setInvoiceCompanyRows; },
    get setInvoiceCompanyMeta() { return setInvoiceCompanyMeta; },
    get setInvoiceUnissuedRows() { return setInvoiceUnissuedRows; },
    get setInvoiceUnissuedMeta() { return setInvoiceUnissuedMeta; },
    get setGeneralSettlementRows() { return setGeneralSettlementRows; },
    get setGeneralSettlementMeta() { return setGeneralSettlementMeta; },
    get setArchiveSettlementRows() { return setArchiveSettlementRows; },
    get setArchiveSettlementMeta() { return setArchiveSettlementMeta; },
    get setFeeQueryRows() { return setFeeQueryRows; },
    get setFeeQueryMeta() { return setFeeQueryMeta; },
    get legacyFinanceMeta() { return legacyFinanceMeta; },
    get setLegacyFinanceLoading() { return setLegacyFinanceLoading; },
    get legacyFinanceKind() { return legacyFinanceKind; },
    get legacyFinanceStatusCode() { return legacyFinanceStatusCode; },
    get legacyFinanceKeyword() { return legacyFinanceKeyword; },
    get legacyFinanceIncludeInactive() { return legacyFinanceIncludeInactive; },
    get setLegacyFinanceRows() { return setLegacyFinanceRows; },
    get setLegacyFinanceMeta() { return setLegacyFinanceMeta; },
    get setLegacyFinanceSummary() { return setLegacyFinanceSummary; },
    get setLegacyFinanceDetailLoading() { return setLegacyFinanceDetailLoading; },
    get setLegacyFinanceDetail() { return setLegacyFinanceDetail; },
    get selectedOriginalRows() { return selectedOriginalRows; },
    get setInternalDetailExportLoading() { return setInternalDetailExportLoading; },
    get originalQuery() { return originalQuery; },
    get activeRouteConfig() { return activeRouteConfig; },
    get displayedOriginalTitle() { return displayedOriginalTitle; },
    get configuredRows() { return configuredRows; },
    get cellValue() { return cellValue; },
  });

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
  const [paymentPackageEditTarget, setPaymentPackageEditTarget] =
    useState<Fee | null>(null);
  const [paymentPackageEditorOpen, setPaymentPackageEditorOpen] = useState(false);
  const [paymentPackageSelectedFeeIds, setPaymentPackageSelectedFeeIds] =
    useState<number[]>([]);
  const [paymentPackageCandidates, setPaymentPackageCandidates] = useState<Fee[]>([]);
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
  const { openPaymentDetail, loadFeeQuery, loadPaymentQueryPage, loadPaymentPackages, createFee, feeAction, refreshCurrentFinanceFeeList, submitPaymentCancel, submitPaymentRollback, writeoffFee, writeoffPaymentPackage, downloadPaymentPrintWord, printPayment, submitFeeReview, previewInternalPaymentPackage, submitInternalPaymentPackage, openPaymentPackageDetail, submitPaymentPackageEditor, exportFeeQuery } = createFinancePaymentsActions({
    get setFeeDetail() { return setFeeDetail; },
    get feeQueryMeta() { return feeQueryMeta; },
    get isRefundCaseFeeRoute() { return isRefundCaseFeeRoute; },
    get feeQueryParams() { return feeQueryParams; },
    get setFeeQueryRows() { return setFeeQueryRows; },
    get setFeeQueryMeta() { return setFeeQueryMeta; },
    get paymentQueryPageSize() { return paymentQueryPageSize; },
    get paymentPackageMeta() { return paymentPackageMeta; },
    get initialView() { return initialView; },
    get setPaymentPackages() { return setPaymentPackages; },
    get setPaymentPackageMeta() { return setPaymentPackageMeta; },
    get feeForm() { return feeForm; },
    get feeEditTarget() { return feeEditTarget; },
    get closeFeeModal() { return closeFeeModal; },
    get load() { return load; },
    get financeFeeRefreshGuard() { return financeFeeRefreshGuard; },
    get setFees() { return setFees; },
    get setFinanceFeeListMeta() { return setFinanceFeeListMeta; },
    get paymentCancelTarget() { return paymentCancelTarget; },
    get paymentCancelReason() { return paymentCancelReason; },
    get setPaymentCancelTarget() { return setPaymentCancelTarget; },
    get setPaymentCancelReason() { return setPaymentCancelReason; },
    get financeFeeListMeta() { return financeFeeListMeta; },
    get originalQuery() { return originalQuery; },
    get paymentRollbackTarget() { return paymentRollbackTarget; },
    get paymentRollbackComment() { return paymentRollbackComment; },
    get setPaymentRollbackTarget() { return setPaymentRollbackTarget; },
    get setPaymentRollbackComment() { return setPaymentRollbackComment; },
    get writeoffTarget() { return writeoffTarget; },
    get writeoffForm() { return writeoffForm; },
    get contractPayments() { return contractPayments; },
    get setWriteoffTarget() { return setWriteoffTarget; },
    get paymentStatus() { return paymentStatus; },
    get feeDetail() { return feeDetail; },
    get paymentPackageWriteoffTarget() { return paymentPackageWriteoffTarget; },
    get paymentPackageWriteoffForm() { return paymentPackageWriteoffForm; },
    get financeActionGates() { return financeActionGates; },
    get setPaymentPackageLoading() { return setPaymentPackageLoading; },
    get setPaymentPackageWriteoffTarget() { return setPaymentPackageWriteoffTarget; },
    get paymentPrintPreview() { return paymentPrintPreview; },
    get setPaymentWordExportLoading() { return setPaymentWordExportLoading; },
    get transactions() { return transactions; },
    get currentUser() { return currentUser; },
    get setPaymentPrintPreview() { return setPaymentPrintPreview; },
    get feeReviewTargets() { return feeReviewTargets; },
    get setFeeReviewLoading() { return setFeeReviewLoading; },
    get feeReviewComment() { return feeReviewComment; },
    get setFeeReviewTargets() { return setFeeReviewTargets; },
    get setFeeReviewComment() { return setFeeReviewComment; },
    get setSelectedOriginalRows() { return setSelectedOriginalRows; },
    get configuredRows() { return configuredRows; },
    get selectedOriginalRows() { return selectedOriginalRows; },
    get setPaymentPackagePreview() { return setPaymentPackagePreview; },
    get paymentPackagePreview() { return paymentPackagePreview; },
    get setPaymentPackageDetail() { return setPaymentPackageDetail; },
    get paymentPackageSelectedFeeIds() { return paymentPackageSelectedFeeIds; },
    get paymentPackageEditForm() { return paymentPackageEditForm; },
    get paymentPackageEditTarget() { return paymentPackageEditTarget; },
    get setPaymentPackageEditTarget() { return setPaymentPackageEditTarget; },
    get setPaymentPackageEditorOpen() { return setPaymentPackageEditorOpen; },
    get setPaymentPackageSelectedFeeIds() { return setPaymentPackageSelectedFeeIds; },
    get setFeeQueryExportLoading() { return setFeeQueryExportLoading; },
  });
  const { openInvoiceDetail, loadInvoiceMine, loadInvoiceCompany, loadInvoiceUnissued, loadInvoicePending, loadInvoiceReferenceData, createInvoice, issueInvoice, rejectInvoiceIssue, voidInvoice, submitInvoiceNumberChange, submitInvoiceDateChange, submitInvoiceCancel, exportInvoiceList, exportInvoiceUnissued } = createFinanceInvoicesActions({
    get invoiceDetailRequestGuard() { return invoiceDetailRequestGuard; },
    get setInvoiceDetail() { return setInvoiceDetail; },
    get invoiceMineMeta() { return invoiceMineMeta; },
    get invoiceMineParams() { return invoiceMineParams; },
    get setInvoiceMineRows() { return setInvoiceMineRows; },
    get setInvoiceMineMeta() { return setInvoiceMineMeta; },
    get invoiceCompanyMeta() { return invoiceCompanyMeta; },
    get invoiceCompanyParams() { return invoiceCompanyParams; },
    get setInvoiceCompanyRows() { return setInvoiceCompanyRows; },
    get setInvoiceCompanyMeta() { return setInvoiceCompanyMeta; },
    get invoiceUnissuedMeta() { return invoiceUnissuedMeta; },
    get invoiceUnissuedParams() { return invoiceUnissuedParams; },
    get setInvoiceUnissuedRows() { return setInvoiceUnissuedRows; },
    get setInvoiceUnissuedMeta() { return setInvoiceUnissuedMeta; },
    get invoicePendingMeta() { return invoicePendingMeta; },
    get invoicePendingParams() { return invoicePendingParams; },
    get setInvoicePendingRows() { return setInvoicePendingRows; },
    get setInvoicePendingMeta() { return setInvoicePendingMeta; },
    get setContracts() { return setContracts; },
    get setCustomers() { return setCustomers; },
    get setInvoiceCandidateFees() { return setInvoiceCandidateFees; },
    get invoiceForm() { return invoiceForm; },
    get cases() { return cases; },
    get contracts() { return contracts; },
    get invoiceCandidateFees() { return invoiceCandidateFees; },
    get fees() { return fees; },
    get invoiceEditTarget() { return invoiceEditTarget; },
    get invoices() { return invoices; },
    get setInvoiceOpen() { return setInvoiceOpen; },
    get setInvoiceEditTarget() { return setInvoiceEditTarget; },
    get load() { return load; },
    get issueTarget() { return issueTarget; },
    get invoiceProcess() { return invoiceProcess; },
    get issueForm() { return issueForm; },
    get setIssueTarget() { return setIssueTarget; },
    get setInvoiceProcess() { return setInvoiceProcess; },
    get originalQuery() { return originalQuery; },
    get voidTarget() { return voidTarget; },
    get voidForm() { return voidForm; },
    get setVoidTarget() { return setVoidTarget; },
    get invoiceNumberTarget() { return invoiceNumberTarget; },
    get invoiceNumberForm() { return invoiceNumberForm; },
    get setInvoiceMutationLoading() { return setInvoiceMutationLoading; },
    get setInvoiceNumberTarget() { return setInvoiceNumberTarget; },
    get invoiceDateTarget() { return invoiceDateTarget; },
    get invoiceDateForm() { return invoiceDateForm; },
    get setInvoiceDateTarget() { return setInvoiceDateTarget; },
    get invoiceCancel() { return invoiceCancel; },
    get invoiceCancelReason() { return invoiceCancelReason; },
    get setInvoiceCancel() { return setInvoiceCancel; },
    get setInvoiceCancelReason() { return setInvoiceCancelReason; },
    get selectedOriginalRows() { return selectedOriginalRows; },
    get setInvoiceExportLoading() { return setInvoiceExportLoading; },
    get isInvoicePendingRoute() { return isInvoicePendingRoute; },
    get isInvoiceCompanyRoute() { return isInvoiceCompanyRoute; },
    get initialView() { return initialView; },
  });
  const { openRefundDetail, loadRefunds, refreshRefundList, createRefund, updateRefundAmount, updateRefundBatchStatus, completeRefund, submitRefundCaseFeeStatus, submitRefundCaseFeeLog, exportRefunds, submitRefundBatchFee } = createFinanceRefundsActions({
    get refundDetailRequestGuard() { return refundDetailRequestGuard; },
    get setRefundDetail() { return setRefundDetail; },
    get refundMeta() { return refundMeta; },
    get initialView() { return initialView; },
    get refundStatusFilter() { return refundStatusFilter; },
    get refundGroupFilter() { return refundGroupFilter; },
    get refundRequestGuard() { return refundRequestGuard; },
    get setRefunds() { return setRefunds; },
    get setRefundMeta() { return setRefundMeta; },
    get setSelectedRefundRows() { return setSelectedRefundRows; },
    get refunds() { return refunds; },
    get activeRefundStatus() { return activeRefundStatus; },
    get refundForm() { return refundForm; },
    get setRefundOpen() { return setRefundOpen; },
    get refundAmountTarget() { return refundAmountTarget; },
    get refundAmountForm() { return refundAmountForm; },
    get setRefundMutationLoading() { return setRefundMutationLoading; },
    get setRefundAmountTarget() { return setRefundAmountTarget; },
    get selectedRefundRows() { return selectedRefundRows; },
    get refundBatchStatus() { return refundBatchStatus; },
    get setRefundBatchStatusOpen() { return setRefundBatchStatusOpen; },
    get refundCompleteTarget() { return refundCompleteTarget; },
    get refundCompleteForm() { return refundCompleteForm; },
    get setRefundCompleteTarget() { return setRefundCompleteTarget; },
    get requireRefundCaseFeeSelection() { return requireRefundCaseFeeSelection; },
    get refundCaseFeeStatus() { return refundCaseFeeStatus; },
    get setRefundCaseFeeMutationLoading() { return setRefundCaseFeeMutationLoading; },
    get setRefundCaseFeeStatusOpen() { return setRefundCaseFeeStatusOpen; },
    get setSelectedOriginalRows() { return setSelectedOriginalRows; },
    get loadFeeQuery() { return loadFeeQuery; },
    get originalQuery() { return originalQuery; },
    get feeQueryMeta() { return feeQueryMeta; },
    get refundCaseFeeLogKind() { return refundCaseFeeLogKind; },
    get refundCaseFeeLogContent() { return refundCaseFeeLogContent; },
    get setRefundCaseFeeLogKind() { return setRefundCaseFeeLogKind; },
    get setRefundCaseFeeLogContent() { return setRefundCaseFeeLogContent; },
    get isRefundNotRequiredRoute() { return isRefundNotRequiredRoute; },
    get refundBatchFeeForm() { return refundBatchFeeForm; },
    get setRefundBatchFeeLoading() { return setRefundBatchFeeLoading; },
    get refundBatchFeeBaseType() { return refundBatchFeeBaseType; },
    get closeRefundBatchFee() { return closeRefundBatchFee; },
    get load() { return load; },
  });
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
  const [paymentPackageEditForm] = Form.useForm();
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
  const { loadGeneralSettlements, loadArchiveSettlements, submitGeneralSettlementReview, submitGeneralSettlementPayment, submitGeneralSettlementReapply, exportGeneralSettlement, exportPendingArchiveSettlements, submitArchiveSettlementReview, submitArchiveSettlementRollback, submitArchiveSettlementReapply, submitGeneralSettlementApply, loadSettlementContextTasks, openSettlementContext, submitSettlementLog, submitSettlementTask, generateSettlementDocument, submitSettlementBatch } = createFinanceSettlementsActions({
    get generalSettlementMeta() { return generalSettlementMeta; },
    get isGeneralSettlementPendingRoute() { return isGeneralSettlementPendingRoute; },
    get generalSettlementParams() { return generalSettlementParams; },
    get setGeneralSettlementRows() { return setGeneralSettlementRows; },
    get setGeneralSettlementMeta() { return setGeneralSettlementMeta; },
    get archiveSettlementMeta() { return archiveSettlementMeta; },
    get isArchiveSettlementPaymentRoute() { return isArchiveSettlementPaymentRoute; },
    get isArchiveSettlementPaidRoute() { return isArchiveSettlementPaidRoute; },
    get isArchiveSettlementRejectedRoute() { return isArchiveSettlementRejectedRoute; },
    get archiveSettlementParams() { return archiveSettlementParams; },
    get setArchiveSettlementRows() { return setArchiveSettlementRows; },
    get setArchiveSettlementMeta() { return setArchiveSettlementMeta; },
    get generalSettlementReviewTargets() { return generalSettlementReviewTargets; },
    get financeActionGates() { return financeActionGates; },
    get setGeneralSettlementBusy() { return setGeneralSettlementBusy; },
    get generalSettlementReviewApproved() { return generalSettlementReviewApproved; },
    get generalSettlementReviewComment() { return generalSettlementReviewComment; },
    get setGeneralSettlementReviewTargets() { return setGeneralSettlementReviewTargets; },
    get setGeneralSettlementReviewComment() { return setGeneralSettlementReviewComment; },
    get setSelectedOriginalRows() { return setSelectedOriginalRows; },
    get setGeneralSettlementDetails() { return setGeneralSettlementDetails; },
    get originalQuery() { return originalQuery; },
    get generalSettlementPaymentTargets() { return generalSettlementPaymentTargets; },
    get generalSettlementPaymentAction() { return generalSettlementPaymentAction; },
    get generalSettlementPaymentComment() { return generalSettlementPaymentComment; },
    get setGeneralSettlementPaymentTargets() { return setGeneralSettlementPaymentTargets; },
    get setGeneralSettlementPaymentComment() { return setGeneralSettlementPaymentComment; },
    get generalSettlementReapplyTargets() { return generalSettlementReapplyTargets; },
    get generalSettlementReapplyComment() { return generalSettlementReapplyComment; },
    get setGeneralSettlementReapplyTargets() { return setGeneralSettlementReapplyTargets; },
    get setGeneralSettlementReapplyComment() { return setGeneralSettlementReapplyComment; },
    get selectedOriginalRows() { return selectedOriginalRows; },
    get setArchiveSettlementBusy() { return setArchiveSettlementBusy; },
    get archiveSettlementReviewTargets() { return archiveSettlementReviewTargets; },
    get archiveSettlementReviewApproved() { return archiveSettlementReviewApproved; },
    get archiveSettlementReviewComment() { return archiveSettlementReviewComment; },
    get setArchiveSettlementReviewTargets() { return setArchiveSettlementReviewTargets; },
    get setArchiveSettlementReviewComment() { return setArchiveSettlementReviewComment; },
    get archiveSettlementRollbackTargets() { return archiveSettlementRollbackTargets; },
    get archiveSettlementRollbackComment() { return archiveSettlementRollbackComment; },
    get setArchiveSettlementRollbackTargets() { return setArchiveSettlementRollbackTargets; },
    get setArchiveSettlementRollbackComment() { return setArchiveSettlementRollbackComment; },
    get archiveSettlementReapplyTargets() { return archiveSettlementReapplyTargets; },
    get archiveSettlementReapplyComment() { return archiveSettlementReapplyComment; },
    get setArchiveSettlementReapplyTargets() { return setArchiveSettlementReapplyTargets; },
    get setArchiveSettlementReapplyComment() { return setArchiveSettlementReapplyComment; },
    get generalSettlementApplyTargets() { return generalSettlementApplyTargets; },
    get generalSettlementApplyComment() { return generalSettlementApplyComment; },
    get setGeneralSettlementApplyTargets() { return setGeneralSettlementApplyTargets; },
    get setGeneralSettlementApplyComment() { return setGeneralSettlementApplyComment; },
    get selectedSettlementCases() { return selectedSettlementCases; },
    get setSettlementLogContent() { return setSettlementLogContent; },
    get setSettlementContext() { return setSettlementContext; },
    get currentUser() { return currentUser; },
    get setSettlementTaskForm() { return setSettlementTaskForm; },
    get setSettlementActionLoading() { return setSettlementActionLoading; },
    get setSettlementContextRows() { return setSettlementContextRows; },
    get settlementLogContent() { return settlementLogContent; },
    get settlementContext() { return settlementContext; },
    get settlementTaskForm() { return settlementTaskForm; },
    get settlementBatchForm() { return settlementBatchForm; },
    get setSettlementBatchOpen() { return setSettlementBatchOpen; },
    get load() { return load; },
  });
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
    setPaymentPackageEditTarget(null);
    setPaymentPackageEditorOpen(false);
    setPaymentPackageSelectedFeeIds([]);
    paymentPackageEditForm.resetFields();
    setPaymentPackageWriteoffTarget(null);
    setPaymentPackageMeta({ total: 0, page: 1, pageSize: 15 });
    setGeneralSettlementDetails([]);
    load();
  }, [initialView, contractPaymentSourceSearch]);
  const { createIncoming, claimIncoming, openIncomingAllocation, allocateIncoming, deleteIncoming, createTransaction, createReconciliation, confirmReconciliation } = createFinanceAccountingActions({
    get incomingForm() { return incomingForm; },
    get setIncomingOpen() { return setIncomingOpen; },
    get load() { return load; },
    get claimTarget() { return claimTarget; },
    get claimForm() { return claimForm; },
    get setClaimTarget() { return setClaimTarget; },
    get setAllocateTarget() { return setAllocateTarget; },
    get setAllocationLoading() { return setAllocationLoading; },
    get setSelectedAllocationKeys() { return setSelectedAllocationKeys; },
    get setAllocationAmounts() { return setAllocationAmounts; },
    get setAllocationKeyword() { return setAllocationKeyword; },
    get setAllocationStage() { return setAllocationStage; },
    get setAllocationFeeType() { return setAllocationFeeType; },
    get setAllocationComment() { return setAllocationComment; },
    get setAllocationValidationError() { return setAllocationValidationError; },
    get setAllocationCandidates() { return setAllocationCandidates; },
    get allocateTarget() { return allocateTarget; },
    get allocationCandidates() { return allocationCandidates; },
    get selectedAllocationKeys() { return selectedAllocationKeys; },
    get allocationAmounts() { return allocationAmounts; },
    get allocationComment() { return allocationComment; },
    get transactionForm() { return transactionForm; },
    get contractPayments() { return contractPayments; },
    get setTransactionOpen() { return setTransactionOpen; },
    get openVouchers() { return openVouchers; },
    get reconcileForm() { return reconcileForm; },
    get setReconcileOpen() { return setReconcileOpen; },
  });
  const { importBankStatement, searchClaimCustomers, submitFlow, openRowCaseLogs } = createFinanceWorkflowActions({
    get load() { return load; },
    get bankUploadRef() { return bankUploadRef; },
    get claimCustomerSearchRequest() { return claimCustomerSearchRequest; },
    get setClaimCustomersLoading() { return setClaimCustomersLoading; },
    get setClaimCustomers() { return setClaimCustomers; },
    get refreshRefundList() { return refreshRefundList; },
    get setSettlementActionLoading() { return setSettlementActionLoading; },
    get setSettlementContextRows() { return setSettlementContextRows; },
    get setSettlementContext() { return setSettlementContext; },
  });

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

  const openPaymentCancel = (row: Fee) => {
    setPaymentCancelReason("");
    setPaymentCancelTarget(row);
  };

  const openPaymentRollback = (row: Fee) => {
    setPaymentRollbackComment("");
    setPaymentRollbackTarget(row);
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

  const { openRecordFiles, uploadRecordFile, deleteRecordFile, uploadVoucher, downloadVoucher, deleteVoucher } = createFinanceDocumentsActions({
    get setRecordFiles() { return setRecordFiles; },
    get setRecordFileTarget() { return setRecordFileTarget; },
    get setRecordFileTargets() { return setRecordFileTargets; },
    get setRecordFile() { return setRecordFile; },
    get setRecordUploadFiles() { return setRecordUploadFiles; },
    get recordFileForm() { return recordFileForm; },
    get recordFileTypeTree() { return recordFileTypeTree; },
    get setRecordFileTypeTree() { return setRecordFileTypeTree; },
    get recordFileTarget() { return recordFileTarget; },
    get recordFile() { return recordFile; },
    get recordUploadFiles() { return recordUploadFiles; },
    get recordFileTargets() { return recordFileTargets; },
    get voucherTarget() { return voucherTarget; },
    get voucherForm() { return voucherForm; },
    get voucherFile() { return voucherFile; },
    get setVoucherTarget() { return setVoucherTarget; },
    get setVoucherFile() { return setVoucherFile; },
    get load() { return load; },
  });

  const openVouchers = (row: Transaction) => {
    setVoucherTarget(row);
    setVoucherFile(null);
    voucherForm.setFieldsValue({
      category: voucherCategory[row.transaction_type],
      remark: "",
    });
    setVoucherOpen(true);
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
  const incomingColumns = createIncomingColumns({
    get financePersonDisplayName() { return financePersonDisplayName; },
    get originalIncomingOperation() { return originalIncomingOperation; },
  });
  const feeColumns = createFeeColumns({
    get openCustomerDetail() { return openCustomerDetail; },
    get openCaseDetail() { return openCaseDetail; },
    get feeAction() { return feeAction; },
    get canApprove() { return canApprove; },
    get transactionForm() { return transactionForm; },
    get setTransactionOpen() { return setTransactionOpen; },
  });
  const invoiceColumns = createInvoiceColumns({
    get openCustomerDetail() { return openCustomerDetail; },
    get openCaseDetail() { return openCaseDetail; },
    get openRecordFiles() { return openRecordFiles; },
    get openInvoiceDetail() { return openInvoiceDetail; },
    get submitFlow() { return submitFlow; },
    get canApprove() { return canApprove; },
    get reviewFlow() { return reviewFlow; },
    get canManage() { return canManage; },
    get issueForm() { return issueForm; },
    get setIssueTarget() { return setIssueTarget; },
    get setVoidTarget() { return setVoidTarget; },
  });
  const refundColumns = createRefundColumns({
    get openCaseDetail() { return openCaseDetail; },
    get openCustomerDetail() { return openCustomerDetail; },
    get openRecordFiles() { return openRecordFiles; },
    get openRefundDetail() { return openRefundDetail; },
    get refundAmountForm() { return refundAmountForm; },
    get setRefundAmountTarget() { return setRefundAmountTarget; },
    get submitFlow() { return submitFlow; },
    get canApprove() { return canApprove; },
    get reviewFlow() { return reviewFlow; },
    get canManage() { return canManage; },
    get refundCompleteForm() { return refundCompleteForm; },
    get setRefundCompleteTarget() { return setRefundCompleteTarget; },
  });
  const transactionColumns = createTransactionColumns({
    get openVouchers() { return openVouchers; },
    get financePersonDisplayName() { return financePersonDisplayName; },
    get role() { return role; },
    get rollbackFinanceTransaction() { return rollbackFinanceTransaction; },
  });
  const reconcileColumns = createReconcileColumns({
    get financePersonDisplayName() { return financePersonDisplayName; },
    get confirmReconciliation() { return confirmReconciliation; },
  });
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
    "finance-payment-package-manage",
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
    "finance-payment-package-manage": "付款打包-管理",
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
    initialView === "finance-payment-package-manage" ? (
      <Space size={0}>
        <Button type="link" onClick={() => void openPaymentPackageDetail(row)}>
          查看
        </Button>
        {row.status === "待核销" && (
          <Button type="link" onClick={() => openPaymentPackageEditor(row)}>
            编辑
          </Button>
        )}
        {role === "admin" && (
          <Button type="link" danger onClick={() => deletePaymentPackage(row)}>
            删除
          </Button>
        )}
      </Space>
    ) : initialView === "finance-internal-done" ? (
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
  const paymentOriginalColumns = createPaymentOriginalColumns({
    get originalOperation() { return originalOperation; },
    get paymentStatus() { return paymentStatus; },
    get openCaseDetail() { return openCaseDetail; },
    get openContractDetail() { return openContractDetail; },
    get latestTransaction() { return latestTransaction; },
    get financePersonDisplayName() { return financePersonDisplayName; },
  });
  const paymentAuditOriginalColumns = createPaymentAuditOriginalColumns({
    get setFeeReviewTargets() { return setFeeReviewTargets; },
    get financePersonDisplayName() { return financePersonDisplayName; },
    get openCaseDetail() { return openCaseDetail; },
    get openContractDetail() { return openContractDetail; },
    get paymentStatus() { return paymentStatus; },
  });
  const internalOriginalColumns = createInternalOriginalColumns({
    get internalMineOperation() { return internalMineOperation; },
    get paymentStatus() { return paymentStatus; },
    get openCaseDetail() { return openCaseDetail; },
    get latestTransaction() { return latestTransaction; },
    get financePersonDisplayName() { return financePersonDisplayName; },
  });
  const feeQueryOriginalColumns = createFeeQueryOriginalColumns({
    get originalOperation() { return originalOperation; },
    get paymentStatus() { return paymentStatus; },
    get latestTransaction() { return latestTransaction; },
    get openCaseDetail() { return openCaseDetail; },
    get openContractDetail() { return openContractDetail; },
    get openCustomerDetail() { return openCustomerDetail; },
    get financePersonDisplayName() { return financePersonDisplayName; },
  });

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

  const routeConfigs: Record<string, OriginalRouteConfig> = createRouteConfigs({
    get f() { return f; },
    get initialView() { return initialView; },
    get bankFields() { return bankFields; },
    get receiptFields() { return receiptFields; },
    get receiptQueryFields() { return receiptQueryFields; },
    get internalSettleFields() { return internalSettleFields; },
    get internalApprovalFields() { return internalApprovalFields; },
    get internalListFields() { return internalListFields; },
    get internalPaymentFields() { return internalPaymentFields; },
    get paymentPackageFields() { return paymentPackageFields; },
    get internalDetailFields() { return internalDetailFields; },
    get invoiceMineFields() { return invoiceMineFields; },
    get invoiceFields() { return invoiceFields; },
    get unissuedFields() { return unissuedFields; },
    get settlementPendingFields() { return settlementPendingFields; },
    get settlementFields() { return settlementFields; },
    get archiveFields() { return archiveFields; },
    get paymentStatuses() { return paymentStatuses; },
  });

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
  
  const openInvoiceDateChange = (row: FinanceFlow) => {
    invoiceDateForm.setFieldsValue({
      application_no: row.serial_no,
      application_date: dayjs(row.data?.application_date || row.created_at),
      invoice_date: row.data?.invoice_date ? dayjs(row.data.invoice_date) : null,
    });
    setInvoiceDateTarget(row);
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
  const configuredColumns = createConfiguredColumns({
    get activeRouteConfig() { return activeRouteConfig; },
    get initialView() { return initialView; },
    get settlementColumnWidths() { return settlementColumnWidths; },
    get isGeneralSettlementRoute() { return isGeneralSettlementRoute; },
    get generalSettlementColumnWidths() { return generalSettlementColumnWidths; },
    get isArchiveSettlementRejectedRoute() { return isArchiveSettlementRejectedRoute; },
    get archiveSettlementRejectedColumnWidths() { return archiveSettlementRejectedColumnWidths; },
    get isArchiveSettlementActiveRoute() { return isArchiveSettlementActiveRoute; },
    get archiveSettlementColumnWidths() { return archiveSettlementColumnWidths; },
    get isInvoiceUnissuedRoute() { return isInvoiceUnissuedRoute; },
    get invoiceUnissuedColumnWidths() { return invoiceUnissuedColumnWidths; },
    get internalListColumnWidths() { return internalListColumnWidths; },
    get isInvoiceCompanyRoute() { return isInvoiceCompanyRoute; },
    get internalListOperation() { return internalListOperation; },
    get isInvoiceMineRoute() { return isInvoiceMineRoute; },
    get invoiceMineOperation() { return invoiceMineOperation; },
    get isInvoicePendingRoute() { return isInvoicePendingRoute; },
    get invoicePendingOperation() { return invoicePendingOperation; },
    get invoiceCompanyOperation() { return invoiceCompanyOperation; },
    get originalInvoiceOperation() { return originalInvoiceOperation; },
    get originalIncomingOperation() { return originalIncomingOperation; },
    get generalSettlementOperation() { return generalSettlementOperation; },
    get archiveSettlementPendingOperation() { return archiveSettlementPendingOperation; },
    get paymentPackageOperation() { return paymentPackageOperation; },
    get isRefundCaseFeeRoute() { return isRefundCaseFeeRoute; },
    get refundCaseFeeOperation() { return refundCaseFeeOperation; },
    get originalOperation() { return originalOperation; },
    get setFeeDetail() { return setFeeDetail; },
    get cellValue() { return cellValue; },
    get openCaseDetail() { return openCaseDetail; },
    get invoices() { return invoices; },
    get openRecordFiles() { return openRecordFiles; },
    get isInternalDetailRoute() { return isInternalDetailRoute; },
    get isFeeQueryRoute() { return isFeeQueryRoute; },
    get openFinanceCustomerDetail() { return openFinanceCustomerDetail; },
    get openContractDetail() { return openContractDetail; },
    get openInvoiceProcess() { return openInvoiceProcess; },
    get openInvoiceDetail() { return openInvoiceDetail; },
    get openPaymentPackageDetail() { return openPaymentPackageDetail; },
  });
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

  const openPaymentPackageEditor = (row?: Fee) => {
    const target = row || null;
    const currentIds = target?.data?.fee_ids || [];
    setPaymentPackageEditTarget(target);
    setPaymentPackageEditorOpen(true);
    setPaymentPackageSelectedFeeIds(currentIds.map((id: any) => Number(id)));
    paymentPackageEditForm.setFieldsValue({ comment: target?.data?.comment || target?.description || "" });
    void api.get("/finance/payment-packages/candidates", { params: target ? { package_id: target.id } : {} })
      .then(({ data }) => setPaymentPackageCandidates(data.items || []))
      .catch((error: any) => message.error(error?.response?.data?.detail || "付款包候选费用加载失败"));
  };
  
  const deletePaymentPackage = (row: Fee) => {
    Modal.confirm({
      title: `删除付款包：${row.serial_no}`,
      content: "仅待核销付款包可以删除；已核销付款包必须通过受控冲正流程处理。",
      okText: "删除",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onOk: async () => {
        try {
          await api.delete(`/finance/payment-packages/${row.id}`);
          message.success("付款包已删除，关联费用已恢复待付款");
          const nextPage = paymentPackages.length === 1 && paymentPackageMeta.page > 1
            ? paymentPackageMeta.page - 1 : paymentPackageMeta.page;
          await loadPaymentPackages(originalQuery, nextPage, paymentPackageMeta.pageSize);
        } catch (error: any) {
          message.error(error?.response?.data?.detail || "付款包删除失败");
        }
      },
    });
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
  
  const selectedRefundCaseFeeIds = () =>
    selectedOriginalRows.map(Number).filter((value) => Number.isInteger(value));
  const requireRefundCaseFeeSelection = () => {
    const ids = selectedRefundCaseFeeIds();
    if (!ids.length) message.warning("请选择需要操作的退费记录");
    return ids;
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
  const selectedSettlementCases = (notify = true) => {
    if (!selectedSettlementRows.length) {
      if (notify) message.warning(isInvoiceUnissuedRoute ? "请选择案件." : "请先选择案件费用");
      return [];
    }
    const linked = selectedSettlementRows.map((selected) => {
      const caseId = Number(selected.data?.case_id || 0);
      const caseNo = String(selected.data?.case_no || "");
      return cases.find((row) => row.id === caseId || row.serial_no === caseNo);
    });
    if (linked.some((row) => !row)) {
      if (notify) message.warning("部分费用未关联可操作的案件");
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

  const openSettlementBatch = () => {
    const linked = selectedSettlementCases();
    if (!linked.length) return;
    settlementBatchForm.resetFields();
    setSettlementBatchOpen(true);
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

  if (initialView === "finance-jar") {
    return <JarFeeManager onNavigate={onNavigate} />;
  }

  const viewProps = {
    // Route / view state
    initialView,
    originalMode,
    originalKind,
    tab,
    setTab,
    isInvoiceMineRoute,
    isInvoicePendingRoute,
    isInvoiceCompanyRoute,
    isInvoiceUnissuedRoute,
    isGeneralSettlementRoute,
    isGeneralSettlementPaidRoute,
    isGeneralSettlementRejectedRoute,
    isGeneralSettlementAuditRoute,
    isGeneralSettlementPaymentRoute,
    isArchiveSettlementActiveRoute,
    isArchiveSettlementPaidRoute,
    isArchiveSettlementRejectedRoute,
    isArchiveSettlementPaymentRoute,
    isFeeQueryRoute,
    isInternalDetailRoute,
    isInternalApprovalRoute,
    isRefundNotRequiredRoute,
    isRefundCaseFeeRoute,
    isInternalHistoryList,
    activeRouteConfig,
    activeRefundStatus,

    // Page / detail pages
    incomingPaymentDetailPage,
    invoiceDetailPage,
    paymentPrintPreviewPage,
    paymentPackagePrintPage,
    internalPaymentDetail,

    // Refs
    bankUploadRef,

    // Loading states
    loading,
    paymentPackageLoading,
    invoiceExportLoading,
    feeQueryExportLoading,
    settlementActionLoading,
    feeReviewLoading,
    generalSettlementBusy,
    archiveSettlementBusy,
    internalDetailExportLoading,
    refundMutationLoading,
    refundCaseFeeMutationLoading,
    invoiceMutationLoading,

    // Summary / stats
    summary,
    canManage,
    canApprove,
    role,
    currentUser,

    // Original mode - display
    displayedOriginalTitle,
    contractPaymentSourceNotice,
    contractPaymentSource,
    originalFields,
    originalColumns,
    paymentOriginalColumns,
    configuredRows,
    selectedOriginalRows,
    setSelectedOriginalRows,

    // Original mode - pagination metadata
    paymentQueryMeta,
    paymentQueryPageSize,
    setPaymentQueryPageSize,
    paymentAuditPageSize,
    setPaymentAuditPageSize,
    paymentQueryQuickPage,
    setPaymentQueryQuickPage,
    feeQueryMeta,
    paymentPackageMeta,
    invoiceMineMeta,
    invoicePendingMeta,
    invoiceCompanyMeta,
    invoiceUnissuedMeta,
    generalSettlementMeta,
    archiveSettlementMeta,
    internalDetailMeta,

    // Original mode - query
    originalQuery,
    submitConfiguredQuery,
    clearConfiguredQuery,
    submitPaymentQueryQuickPage,
    refreshPaymentQueryPage,

    // Original mode - actions / loaders
    load,
    importBankStatement,
    loadPaymentPackages,
    loadFeeQuery,
    loadInvoiceMine,
    loadInvoicePending,
    loadInvoiceCompany,
    loadInvoiceUnissued,
    loadGeneralSettlements,
    loadArchiveSettlements,
    loadInternalDetails,
    exportConfiguredRows,
    exportInvoiceUnissued,
    exportInternalDetails,
    exportInvoiceList,
    exportFeeQuery,
    exportGeneralSettlement,
    exportPendingArchiveSettlements,
    markCommissionPaid,
    runSettlementMoreAction,
    openBatchFeeReview,
    openCaseTaskCreate,
    openCaseDetail,
    openCustomerDetail,
    openContractDetail,
    financePersonDisplayName,
    financePersonDisplayNames,

    // Payment packages
    openPaymentPackageEditor,
    previewInternalPaymentPackage,
    paymentPackageWriteoffTarget,
    setPaymentPackageWriteoffTarget,
    paymentPackageWriteoffForm,
    writeoffPaymentPackage,
    paymentPackageEditorOpen,
    paymentPackageEditTarget,
    setPaymentPackageEditTarget,
    setPaymentPackageEditorOpen,
    paymentPackageSelectedFeeIds,
    setPaymentPackageSelectedFeeIds,
    paymentPackageEditForm,
    paymentPackageCandidates,
    submitPaymentPackageEditor,

    // General settlement
    generalSettlementDetails,
    setGeneralSettlementDetails,
    openArchiveSettlementReview,
    openArchiveSettlementRollback,
    openArchiveSettlementReapply,
    openGeneralSettlementReapply,
    openGeneralSettlementPayment,
    openGeneralSettlementReview,
    applyGeneralSettlementRows,
    generalSettlementApplyTargets,
    setGeneralSettlementApplyTargets,
    generalSettlementApplyComment,
    setGeneralSettlementApplyComment,
    submitGeneralSettlementApply,
    generalSettlementReviewTargets,
    setGeneralSettlementReviewTargets,
    generalSettlementReviewApproved,
    generalSettlementReviewComment,
    setGeneralSettlementReviewComment,
    submitGeneralSettlementReview,
    generalSettlementPaymentTargets,
    setGeneralSettlementPaymentTargets,
    generalSettlementPaymentAction,
    generalSettlementPaymentComment,
    setGeneralSettlementPaymentComment,
    submitGeneralSettlementPayment,
    generalSettlementReapplyTargets,
    setGeneralSettlementReapplyTargets,
    generalSettlementReapplyComment,
    setGeneralSettlementReapplyComment,
    submitGeneralSettlementReapply,
    archiveSettlementReviewTargets,
    setArchiveSettlementReviewTargets,
    archiveSettlementReviewApproved,
    archiveSettlementReviewComment,
    setArchiveSettlementReviewComment,
    submitArchiveSettlementReview,
    archiveSettlementRollbackTargets,
    setArchiveSettlementRollbackTargets,
    archiveSettlementRollbackComment,
    setArchiveSettlementRollbackComment,
    submitArchiveSettlementRollback,
    archiveSettlementReapplyTargets,
    setArchiveSettlementReapplyTargets,
    archiveSettlementReapplyComment,
    setArchiveSettlementReapplyComment,
    submitArchiveSettlementReapply,

    // Settlement context (tasks / logs)
    settlementContext,
    setSettlementContext,
    settlementContextRows,
    settlementLogContent,
    setSettlementLogContent,
    settlementTaskForm,
    setSettlementTaskForm,
    submitSettlementLog,
    submitSettlementTask,
    selectedSettlementCases,

    // Settlement batch modify
    settlementBatchOpen,
    setSettlementBatchOpen,
    settlementBatchForm,
    submitSettlementBatch,

    // Refund case fee
    refundCaseFeeStatusOpen,
    setRefundCaseFeeStatusOpen,
    refundCaseFeeStatus,
    setRefundCaseFeeStatus,
    submitRefundCaseFeeStatus,
    refundCaseFeeLogKind,
    setRefundCaseFeeLogKind,
    refundCaseFeeLogContent,
    setRefundCaseFeeLogContent,
    submitRefundCaseFeeLog,
    requireRefundCaseFeeSelection,

    // Refund batch fee
    refundBatchFeeOpen,
    refundBatchFeeKind,
    refundBatchFeeStep,
    setRefundBatchFeeStep,
    refundBatchFeeForm,
    refundBatchFeeBaseType,
    refundBatchFeeSubTypes,
    refundBatchPaymentTypes,
    refundBatchFeeLoading,
    closeRefundBatchFee,
    submitRefundBatchFee,
    syncFirstRefundFeeField,

    // Fee review drawer
    feeReviewTargets,
    setFeeReviewTargets,
    feeReviewComment,
    setFeeReviewComment,
    submitFeeReview,
    paymentReviewRows,
    feeReviewRows,
    reviewNumber,

    // Fee detail modal
    feeDetail,
    setFeeDetail,
    paymentStatus,
    latestTransaction,
    linkedCaseForFee,

    // Incoming
    incoming,
    shownIncoming,
    incomingColumns,
    selectedIncomingRows,
    setSelectedIncomingRows,
    incomingOpen,
    setIncomingOpen,
    incomingForm,
    createIncoming,
    incomingAllocationTarget,
    setIncomingAllocationTarget,

    // Claim
    claimTarget,
    setClaimTarget,
    claimForm,
    claimIncoming,
    claimCustomers,
    claimCustomersLoading,
    searchClaimCustomers,

    // Allocation
    allocateTarget,
    setAllocateTarget,
    allocateIncoming,
    allocationCandidates,
    filteredAllocationCandidates,
    allocationLoading,
    allocationKeyword,
    setAllocationKeyword,
    allocationStage,
    setAllocationStage,
    allocationFeeType,
    setAllocationFeeType,
    selectedAllocationKeys,
    setSelectedAllocationKeys,
    allocationAmounts,
    setAllocationAmounts,
    allocationComment,
    setAllocationComment,
    allocationValidationError,
    setAllocationValidationError,
    setAllocationCandidates,

    // Writeoff
    writeoffTarget,
    setWriteoffTarget,
    writeoffForm,
    writeoffFee,

    // Payment cancel / rollback
    paymentCancelTarget,
    setPaymentCancelTarget,
    paymentCancelReason,
    setPaymentCancelReason,
    submitPaymentCancel,
    paymentRollbackTarget,
    setPaymentRollbackTarget,
    paymentRollbackComment,
    setPaymentRollbackComment,
    submitPaymentRollback,

    // Fees tab
    shownFees,
    feeColumns,
    fees,

    // Invoices tab
    shownInvoices,
    invoiceColumns,
    invoices,
    invoiceOpen,
    setInvoiceOpen,
    invoiceEditTarget,
    setInvoiceEditTarget,
    invoiceSelectedFeeIds,
    setInvoiceSelectedFeeIds,
    invoiceFeeAmounts,
    setInvoiceFeeAmounts,
    invoiceSourceFeeId,
    setInvoiceSourceFeeId,
    invoiceForm,
    createInvoice,
    invoiceFeeOptions,
    applyInvoiceFeeSelection,
    loadInvoiceReferenceData,

    // Invoice mutation
    invoiceNumberTarget,
    setInvoiceNumberTarget,
    invoiceNumberForm,
    submitInvoiceNumberChange,
    invoiceDateTarget,
    setInvoiceDateTarget,
    invoiceDateForm,
    submitInvoiceDateChange,
    issueTarget,
    setIssueTarget,
    issueForm,
    issueInvoice,
    voidTarget,
    setVoidTarget,
    voidForm,
    voidInvoice,

    // Refunds tab
    refundColumns,
    refunds,
    selectedRefundRows,
    setSelectedRefundRows,
    refundMeta,
    refundStatusFilter,
    setRefundStatusFilter,
    refundGroupFilter,
    setRefundGroupFilter,
    loadRefunds,
    exportRefunds,
    refundBatchStatus,
    setRefundBatchStatus,
    refundBatchStatusOpen,
    setRefundBatchStatusOpen,
    updateRefundBatchStatus,
    refundOpen,
    setRefundOpen,
    refundForm,
    createRefund,
    refundDetail,
    setRefundDetail,
    refundAmountTarget,
    setRefundAmountTarget,
    refundAmountForm,
    updateRefundAmount,
    refundCompleteTarget,
    setRefundCompleteTarget,
    refundCompleteForm,
    completeRefund,
    refundStatusForRoute,

    // Transactions tab
    transactions,
    transactionColumns,
    transactionOpen,
    setTransactionOpen,
    transactionForm,
    createTransaction,

    // Voucher
    voucherOpen,
    setVoucherOpen,
    voucherTarget,
    voucherForm,
    uploadVoucher,
    setVoucherFile,
    downloadVoucher,
    deleteVoucher,

    // Record files
    recordFileTarget,
    setRecordFileTarget,
    recordFileTargets,
    setRecordFileTargets,
    recordFiles,
    recordFileForm,
    recordFileTypeTree,
    uploadRecordFile,
    setRecordUploadFiles,
    setRecordFile,
    deleteRecordFile,

    // Fee modal
    feeOpen,
    setFeeOpen,
    feeEditTarget,
    setFeeEditTarget,
    feeForm,
    feeTypeOverride,
    setFeeTypeOverride,
    selectedFeeType,
    createFee,
    closeFeeModal,
    feeCommissionDetails,

    // Legacy history
    legacyFinanceRows,
    legacyFinanceLoading,
    legacyFinanceMeta,
    legacyFinanceSummary,
    legacyFinanceDetail,
    setLegacyFinanceDetail,
    legacyFinanceDetailLoading,
    setLegacyFinanceDetailLoading,
    legacyFinanceKeyword,
    setLegacyFinanceKeyword,
    legacyFinanceKind,
    setLegacyFinanceKind,
    legacyFinanceStatusCode,
    setLegacyFinanceStatusCode,
    legacyFinanceIncludeInactive,
    setLegacyFinanceIncludeInactive,
    loadLegacyFinanceHistory,
    openLegacyFinanceDetail,

    // Reconcile
    reconcileColumns,
    reconciliations,
    reconcileOpen,
    setReconcileOpen,
    reconcileForm,
    createReconciliation,

    // Reference data
    financePeople,
    customers,
    cases,
    contracts,
  };

  return <FinanceCenterView {...viewProps} />;
}
