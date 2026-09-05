import {
DeleteOutlined,
DownloadOutlined,
MinusCircleOutlined,
PlusOutlined,
ReloadOutlined,
UploadOutlined,
} from "@ant-design/icons";
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
Modal,
Select,
Space,
Steps,
Table,
Tabs,
Tag,
TreeSelect,
message,
} from "antd";
import dayjs from "dayjs";
import RecordImportButton from "../RecordImportButton";
import {
refundPageSizeOptions,
refundStatusOptions,
} from "../financeRefundHelpers.mjs";
import { FeeReviewDrawer } from "./FeeReviewDrawer";
import { FinanceStatsCards } from "./FinanceStatsCards";
import { IncomingAllocationModal } from "./IncomingAllocationModal";
import { LegacyHistoryPanel } from "./LegacyHistoryPanel";
import { SettlementReviewModals } from "./SettlementReviewModals";
import {
feeTypes,
internalApprovalRoutes,
invoiceFeeAvailableAmount,
invoiceFeeIssuedAmount,
money,
paymentPackagePageSizeOptions,
paymentQueryControlledPageSize,
paymentQueryDefaultPageSize,
paymentQueryPageSizeOptions,
paymentQueryPageTotal,
paymentQueryQuickJumper,
paymentQueryShowsSinglePageGo,
statusColors,
} from "./constants";
import type {
AllocationCandidate,
Attachment,
Fee,
FinancePersonOption,
IncomingPayment
} from "./types";

export interface FinanceCenterViewProps {
  // Route / view state
  initialView: string;
  originalMode: boolean;
  originalKind: string;
  tab: string;
  setTab: (tab: string) => void;
  isInvoiceMineRoute: boolean;
  isInvoicePendingRoute: boolean;
  isInvoiceCompanyRoute: boolean;
  isInvoiceUnissuedRoute: boolean;
  isGeneralSettlementRoute: boolean;
  isGeneralSettlementPaidRoute: boolean;
  isGeneralSettlementRejectedRoute: boolean;
  isGeneralSettlementAuditRoute: boolean;
  isGeneralSettlementPaymentRoute: boolean;
  isArchiveSettlementActiveRoute: boolean;
  isArchiveSettlementPaidRoute: boolean;
  isArchiveSettlementRejectedRoute: boolean;
  isArchiveSettlementPaymentRoute: boolean;
  isFeeQueryRoute: boolean;
  isInternalDetailRoute: boolean;
  isInternalApprovalRoute: boolean;
  isRefundNotRequiredRoute: boolean;
  isRefundCaseFeeRoute: boolean;
  isInternalHistoryList: boolean;
  activeRouteConfig: any;
  activeRefundStatus: string;

  // Page / detail pages
  incomingPaymentDetailPage: React.ReactNode;
  invoiceDetailPage: React.ReactNode;
  paymentPrintPreviewPage: React.ReactNode;
  paymentPackagePrintPage: React.ReactNode;
  internalPaymentDetail: React.ReactNode;

  // Refs
  bankUploadRef: React.RefObject<HTMLInputElement | null>;

  // Loading states
  loading: boolean;
  paymentPackageLoading: boolean;
  invoiceExportLoading: boolean;
  feeQueryExportLoading: boolean;
  settlementActionLoading: boolean;
  generalSettlementBusy: boolean;
  archiveSettlementBusy: boolean;
  internalDetailExportLoading: boolean;
  refundMutationLoading: boolean;
  refundCaseFeeMutationLoading: boolean;
  invoiceMutationLoading: boolean;

  // Summary / stats
  summary: any;
  canManage: boolean;
  canApprove: boolean;
  role: string;
  currentUser: any;

  // Original mode - display
  displayedOriginalTitle: string;
  contractPaymentSourceNotice: React.ReactNode;
  contractPaymentSource: any;
  originalFields: React.ReactNode;
  originalColumns: any[];
  paymentOriginalColumns: any[];
  configuredRows: any[];
  selectedOriginalRows: (string | number)[];
  setSelectedOriginalRows: (keys: (string | number)[]) => void;

  // Original mode - pagination metadata
  paymentQueryMeta: any;
  paymentQueryPageSize: number;
  setPaymentQueryPageSize: (size: number) => void;
  paymentAuditPageSize: number;
  setPaymentAuditPageSize: (size: number) => void;
  paymentQueryQuickPage: string;
  setPaymentQueryQuickPage: (value: string) => void;
  feeQueryMeta: any;
  paymentPackageMeta: any;
  invoiceMineMeta: any;
  invoicePendingMeta: any;
  invoiceCompanyMeta: any;
  invoiceUnissuedMeta: any;
  generalSettlementMeta: any;
  archiveSettlementMeta: any;
  internalDetailMeta: any;

  // Original mode - query
  originalQuery: any;
  submitConfiguredQuery: () => void;
  clearConfiguredQuery: () => void;
  submitPaymentQueryQuickPage: () => void;
  refreshPaymentQueryPage: (page: number, pageSize: number) => void;

  // Original mode - actions / loaders
  load: () => Promise<void>;
  importBankStatement: (file: File | undefined) => Promise<void>;
  loadPaymentPackages: (query: any, page: number, pageSize: number) => Promise<any>;
  loadFeeQuery: (query: any, page: number, pageSize: number) => Promise<any>;
  loadInvoiceMine: (query: any, page: number, pageSize: number) => Promise<any>;
  loadInvoicePending: (query: any, page: number, pageSize: number) => Promise<any>;
  loadInvoiceCompany: (query: any, page: number, pageSize: number) => Promise<any>;
  loadInvoiceUnissued: (query: any, page: number, pageSize: number) => Promise<any>;
  loadGeneralSettlements: (query: any, page: number, pageSize: number) => Promise<any>;
  loadArchiveSettlements: (query: any, page: number, pageSize: number) => Promise<any>;
  loadInternalDetails: (query: any, page: number, pageSize: number) => Promise<any>;
  exportConfiguredRows: (selectedOnly: boolean) => void;
  exportInvoiceUnissued: (selectedOnly: boolean) => Promise<void>;
  exportInternalDetails: (selectedOnly: boolean) => Promise<void>;
  exportInvoiceList: (selectedOnly: boolean) => Promise<void>;
  exportFeeQuery: (selectedOnly: boolean) => Promise<void>;
  exportGeneralSettlement: (kind: "settlement" | "receipt" | "case", ids?: (string | number)[]) => Promise<void>;
  exportPendingArchiveSettlements: () => Promise<void>;
  markCommissionPaid: () => void;
  runSettlementMoreAction: (key: string) => void;
  openBatchFeeReview: () => void;
  openCaseTaskCreate: (detail: any) => void;
  openCaseDetail: (caseNo: unknown) => void;
  openCustomerDetail: (customer: string, customerNo?: string) => void;
  openContractDetail: (contractNo: string) => void;
  financePersonDisplayName: (username?: string, displayName?: string) => string;
  financePersonDisplayNames: (usernames?: string, displayNames?: string) => string;

  // Payment packages
  openPaymentPackageEditor: (target?: any) => void;
  previewInternalPaymentPackage: () => Promise<void>;
  paymentPackageWriteoffTarget: any;
  setPaymentPackageWriteoffTarget: (target: any) => void;
  paymentPackageWriteoffForm: any;
  writeoffPaymentPackage: () => Promise<void>;
  paymentPackageEditorOpen: boolean;
  paymentPackageEditTarget: any;
  setPaymentPackageEditTarget: (target: any) => void;
  setPaymentPackageEditorOpen: (open: boolean) => void;
  paymentPackageSelectedFeeIds: number[];
  setPaymentPackageSelectedFeeIds: (ids: number[]) => void;
  paymentPackageEditForm: any;
  paymentPackageCandidates: Fee[];
  submitPaymentPackageEditor: () => Promise<void>;

  // General settlement
  generalSettlementDetails: (number | string)[];
  setGeneralSettlementDetails: (ids: (number | string)[]) => void;
  openArchiveSettlementReview: (rows: any[], approved: boolean) => void;
  openArchiveSettlementRollback: (rows: any[]) => void;
  openArchiveSettlementReapply: (rows: any[]) => void;
  openGeneralSettlementReapply: (rows: any[]) => void;
  openGeneralSettlementPayment: (targets: Fee[], action: "paid" | "rollback") => void;
  openGeneralSettlementReview: (rows: any[], approved: boolean) => void;
  applyGeneralSettlementRows: () => void;
  generalSettlementApplyTargets: any[];
  setGeneralSettlementApplyTargets: (targets: any[]) => void;
  generalSettlementApplyComment: string;
  setGeneralSettlementApplyComment: (comment: string) => void;
  submitGeneralSettlementApply: () => Promise<void>;
  generalSettlementReapplyTargets: any[];
  setGeneralSettlementReapplyTargets: (targets: any[]) => void;
  generalSettlementReapplyComment: string;
  setGeneralSettlementReapplyComment: (comment: string) => void;
  submitGeneralSettlementReapply: () => Promise<void>;

  // Settlement context (tasks / logs)
  settlementContext: any;
  setSettlementContext: (ctx: any) => void;
  settlementContextRows: any[];
  settlementLogContent: string;
  setSettlementLogContent: (content: string) => void;
  settlementTaskForm: any;
  setSettlementTaskForm: (form: any) => void;
  submitSettlementLog: () => Promise<void>;
  submitSettlementTask: () => Promise<void>;
  selectedSettlementCases: (notify?: boolean) => any[];

  // Settlement batch modify
  settlementBatchOpen: boolean;
  setSettlementBatchOpen: (open: boolean) => void;
  settlementBatchForm: any;
  submitSettlementBatch: () => Promise<void>;

  // Refund case fee
  refundCaseFeeStatusOpen: boolean;
  setRefundCaseFeeStatusOpen: (open: boolean) => void;
  refundCaseFeeStatus: string;
  setRefundCaseFeeStatus: (status: string) => void;
  submitRefundCaseFeeStatus: (status?: string) => Promise<void>;
  refundCaseFeeLogKind: "court" | "other" | "received" | null;
  setRefundCaseFeeLogKind: React.Dispatch<React.SetStateAction<"court" | "other" | "received" | null>>;
  refundCaseFeeLogContent: string;
  setRefundCaseFeeLogContent: (content: string) => void;
  submitRefundCaseFeeLog: () => Promise<void>;
  requireRefundCaseFeeSelection: () => any[];

  // Refund batch fee
  refundBatchFeeOpen: boolean;
  refundBatchFeeKind: "internal" | "ordinary";
  refundBatchFeeStep: number;
  setRefundBatchFeeStep: (step: number) => void;
  refundBatchFeeForm: any;
  refundBatchFeeBaseType: string;
  refundBatchFeeSubTypes: any[];
  refundBatchPaymentTypes: any[];
  refundBatchFeeLoading: boolean;
  closeRefundBatchFee: () => void;
  submitRefundBatchFee: () => Promise<void>;
  syncFirstRefundFeeField: (field: string) => void;

  // Fee detail modal
  feeDetail: Fee | null;
  setFeeDetail: (fee: Fee | null) => void;
  paymentStatus: (fee: Fee) => string;
  latestTransaction: (fee: Fee) => any;
  linkedCaseForFee: (fee: Fee) => any;

  // Incoming
  incoming: IncomingPayment[];
  shownIncoming: IncomingPayment[];
  incomingColumns: any[];
  selectedIncomingRows: number[];
  setSelectedIncomingRows: (keys: number[]) => void;
  incomingOpen: boolean;
  setIncomingOpen: (open: boolean) => void;
  incomingForm: any;
  createIncoming: () => Promise<void>;
  incomingAllocationTarget: IncomingPayment | null;
  setIncomingAllocationTarget: (target: IncomingPayment | null) => void;

  // Claim
  claimTarget: IncomingPayment | null;
  setClaimTarget: (target: IncomingPayment | null) => void;
  claimForm: any;
  claimIncoming: () => Promise<void>;
  claimCustomers: any[];
  claimCustomersLoading: boolean;
  searchClaimCustomers: (keyword: string) => Promise<void>;

  // Allocation
  allocateTarget: IncomingPayment | null;
  setAllocateTarget: (target: IncomingPayment | null) => void;
  allocateIncoming: () => Promise<void>;
  allocationCandidates: AllocationCandidate[];
  filteredAllocationCandidates: AllocationCandidate[];
  allocationLoading: boolean;
  allocationKeyword: string;
  setAllocationKeyword: (keyword: string) => void;
  allocationStage: string;
  setAllocationStage: (stage: string) => void;
  allocationFeeType: string;
  setAllocationFeeType: (type: string) => void;
  selectedAllocationKeys: (string | number)[];
  setSelectedAllocationKeys: React.Dispatch<React.SetStateAction<(string | number)[]>>;
  allocationAmounts: Record<string, number>;
  setAllocationAmounts: React.Dispatch<React.SetStateAction<Record<string, number>>>;
  allocationValidationError: string;
  setAllocationValidationError: (error: string) => void;
  allocationComment: string;
  setAllocationComment: (comment: string) => void;
  setAllocationCandidates: (candidates: AllocationCandidate[]) => void;

  // Writeoff
  writeoffTarget: any;
  setWriteoffTarget: (target: any) => void;
  writeoffForm: any;
  writeoffFee: () => Promise<void>;

  // Payment cancel / rollback
  paymentCancelTarget: any;
  setPaymentCancelTarget: (target: any) => void;
  paymentCancelReason: string;
  setPaymentCancelReason: (reason: string) => void;
  submitPaymentCancel: () => Promise<void>;
  paymentRollbackTarget: any;
  setPaymentRollbackTarget: (target: any) => void;
  paymentRollbackComment: string;
  setPaymentRollbackComment: (comment: string) => void;
  submitPaymentRollback: () => Promise<void>;

  // Fees tab
  shownFees: Fee[];
  feeColumns: any[];
  fees: Fee[];

  // Invoices tab
  shownInvoices: any[];
  invoiceColumns: any[];
  invoices: any[];
  invoiceOpen: boolean;
  setInvoiceOpen: (open: boolean) => void;
  invoiceEditTarget: any;
  setInvoiceEditTarget: (target: any) => void;
  invoiceSelectedFeeIds: number[];
  setInvoiceSelectedFeeIds: (ids: number[]) => void;
  invoiceFeeAmounts: Record<number, number>;
  setInvoiceFeeAmounts: (amounts: Record<number, number>) => void;
  invoiceSourceFeeId: number | null;
  setInvoiceSourceFeeId: (id: number | null) => void;
  invoiceForm: any;
  createInvoice: () => Promise<void>;
  invoiceFeeOptions: Fee[];
  applyInvoiceFeeSelection: (nextIds: number[]) => void;
  loadInvoiceReferenceData: () => Promise<{ contractRows: any; customerRows: any; candidateRows: any }>;

  // Invoice mutation
  invoiceNumberTarget: any;
  setInvoiceNumberTarget: (target: any) => void;
  invoiceNumberForm: any;
  submitInvoiceNumberChange: () => Promise<void>;
  invoiceDateTarget: any;
  setInvoiceDateTarget: (target: any) => void;
  invoiceDateForm: any;
  submitInvoiceDateChange: () => Promise<void>;
  issueTarget: any;
  setIssueTarget: (target: any) => void;
  issueForm: any;
  issueInvoice: () => Promise<void>;
  voidTarget: any;
  setVoidTarget: (target: any) => void;
  voidForm: any;
  voidInvoice: () => Promise<void>;

  // Refunds tab
  refundColumns: any[];
  refunds: any[];
  selectedRefundRows: number[];
  setSelectedRefundRows: (keys: number[]) => void;
  refundMeta: any;
  refundStatusFilter: string;
  setRefundStatusFilter: (status: string) => void;
  refundGroupFilter: string;
  setRefundGroupFilter: (group: string) => void;
  loadRefunds: (page: number, pageSize: number, status: string, reset?: boolean, group?: string) => Promise<any>;
  exportRefunds: (selectedOnly: boolean) => Promise<void>;
  refundBatchStatus: string;
  setRefundBatchStatus: (status: string) => void;
  refundBatchStatusOpen: boolean;
  setRefundBatchStatusOpen: (open: boolean) => void;
  updateRefundBatchStatus: () => Promise<void>;
  refundOpen: boolean;
  setRefundOpen: (open: boolean) => void;
  refundForm: any;
  createRefund: () => Promise<void>;
  refundDetail: any;
  setRefundDetail: (detail: any) => void;
  refundAmountTarget: any;
  setRefundAmountTarget: (target: any) => void;
  refundAmountForm: any;
  updateRefundAmount: () => Promise<void>;
  refundCompleteTarget: any;
  setRefundCompleteTarget: (target: any) => void;
  refundCompleteForm: any;
  completeRefund: () => Promise<void>;
  refundStatusForRoute: (view: string, fallback: string) => string;

  // Transactions tab
  transactions: any[];
  transactionColumns: any[];
  transactionOpen: boolean;
  setTransactionOpen: (open: boolean) => void;
  transactionForm: any;
  createTransaction: () => Promise<void>;

  // Voucher
  voucherOpen: boolean;
  setVoucherOpen: (open: boolean) => void;
  voucherTarget: any;
  voucherForm: any;
  uploadVoucher: () => Promise<void>;
  setVoucherFile: (file: File | null) => void;
  downloadVoucher: (voucher: Attachment) => void;
  deleteVoucher: (voucher: Attachment) => void;

  // Record files
  recordFileTarget: any;
  setRecordFileTarget: (target: any) => void;
  recordFileTargets: any[];
  setRecordFileTargets: (targets: any[]) => void;
  recordFiles: Attachment[];
  recordFileForm: any;
  recordFileTypeTree: any[];
  uploadRecordFile: () => Promise<boolean | undefined>;
  setRecordUploadFiles: (files: File[]) => void;
  setRecordFile: (file: File | null) => void;
  deleteRecordFile: (file: Attachment) => void;

  // Fee modal
  feeOpen: boolean;
  setFeeOpen: (open: boolean) => void;
  feeEditTarget: Fee | null;
  setFeeEditTarget: (fee: Fee | null) => void;
  feeForm: any;
  feeTypeOverride: string;
  setFeeTypeOverride: (type: string) => void;
  selectedFeeType: string;
  createFee: () => Promise<void>;
  closeFeeModal: () => void;
  feeCommissionDetails: any[];

  // Legacy history
  legacyFinanceRows: any[];
  legacyFinanceLoading: boolean;
  legacyFinanceMeta: any;
  legacyFinanceSummary: any;
  legacyFinanceDetail: any;
  setLegacyFinanceDetail: (detail: any) => void;
  legacyFinanceDetailLoading: boolean;
  setLegacyFinanceDetailLoading: (loading: boolean) => void;
  legacyFinanceKeyword: string;
  setLegacyFinanceKeyword: (keyword: string) => void;
  legacyFinanceKind: string;
  setLegacyFinanceKind: (kind: string) => void;
  legacyFinanceStatusCode: string;
  setLegacyFinanceStatusCode: (code: string) => void;
  legacyFinanceIncludeInactive: boolean;
  setLegacyFinanceIncludeInactive: (include: boolean) => void;
  loadLegacyFinanceHistory: (...args: any[]) => Promise<void>;
  openLegacyFinanceDetail: (record: any) => void;

  // Reconcile
  reconcileColumns: any[];
  reconciliations: any[];
  reconcileOpen: boolean;
  setReconcileOpen: (open: boolean) => void;
  reconcileForm: any;
  createReconciliation: () => Promise<void>;

  // Fee review drawer (passed to FeeReviewDrawer component)
  feeReviewTargets: any[];
  setFeeReviewTargets: (targets: any[]) => void;
  feeReviewComment: string;
  setFeeReviewComment: (comment: string) => void;
  submitFeeReview: (approved: boolean) => Promise<void>;
  feeReviewLoading: boolean;
  paymentReviewRows: any[];
  feeReviewRows: any[];
  reviewNumber: (value: any) => React.ReactNode;

  // Settlement review modals (passed to SettlementReviewModals component)
  generalSettlementReviewTargets: any[];
  setGeneralSettlementReviewTargets: (targets: any[]) => void;
  generalSettlementReviewApproved: boolean;
  generalSettlementReviewComment: string;
  setGeneralSettlementReviewComment: (comment: string) => void;
  submitGeneralSettlementReview: () => Promise<void>;
  generalSettlementPaymentTargets: any[];
  setGeneralSettlementPaymentTargets: (targets: any[]) => void;
  generalSettlementPaymentAction: string;
  generalSettlementPaymentComment: string;
  setGeneralSettlementPaymentComment: (comment: string) => void;
  submitGeneralSettlementPayment: () => Promise<void>;
  archiveSettlementReviewTargets: any[];
  setArchiveSettlementReviewTargets: (targets: any[]) => void;
  archiveSettlementReviewApproved: boolean;
  archiveSettlementReviewComment: string;
  setArchiveSettlementReviewComment: (comment: string) => void;
  submitArchiveSettlementReview: () => Promise<void>;
  archiveSettlementRollbackTargets: any[];
  setArchiveSettlementRollbackTargets: (targets: any[]) => void;
  archiveSettlementRollbackComment: string;
  setArchiveSettlementRollbackComment: (comment: string) => void;
  submitArchiveSettlementRollback: () => Promise<void>;
  archiveSettlementReapplyTargets: any[];
  setArchiveSettlementReapplyTargets: (targets: any[]) => void;
  archiveSettlementReapplyComment: string;
  setArchiveSettlementReapplyComment: (comment: string) => void;
  submitArchiveSettlementReapply: () => Promise<void>;

  // Reference data
  financePeople: FinancePersonOption[];
  customers: any[];
  cases: any[];
  contracts: Fee[];
}

export function FinanceCenterView(props: FinanceCenterViewProps) {
  const {
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
    incomingPaymentDetailPage,
    invoiceDetailPage,
    paymentPrintPreviewPage,
    paymentPackagePrintPage,
    internalPaymentDetail,
    bankUploadRef,
    loading,
    paymentPackageLoading,
    invoiceExportLoading,
    feeQueryExportLoading,
    settlementActionLoading,
    generalSettlementBusy,
    archiveSettlementBusy,
    internalDetailExportLoading,
    refundMutationLoading,
    refundCaseFeeMutationLoading,
    invoiceMutationLoading,
    summary,
    canManage,
    canApprove,
    role,
    currentUser,
    displayedOriginalTitle,
    contractPaymentSourceNotice,
    contractPaymentSource,
    originalFields,
    originalColumns,
    paymentOriginalColumns,
    configuredRows,
    selectedOriginalRows,
    setSelectedOriginalRows,
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
    originalQuery,
    submitConfiguredQuery,
    clearConfiguredQuery,
    submitPaymentQueryQuickPage,
    refreshPaymentQueryPage,
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
    generalSettlementReapplyTargets,
    setGeneralSettlementReapplyTargets,
    generalSettlementReapplyComment,
    setGeneralSettlementReapplyComment,
    submitGeneralSettlementReapply,
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
    settlementBatchOpen,
    setSettlementBatchOpen,
    settlementBatchForm,
    submitSettlementBatch,
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
    feeDetail,
    setFeeDetail,
    paymentStatus,
    latestTransaction,
    linkedCaseForFee,
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
    claimTarget,
    setClaimTarget,
    claimForm,
    claimIncoming,
    claimCustomers,
    claimCustomersLoading,
    searchClaimCustomers,
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
    writeoffTarget,
    setWriteoffTarget,
    writeoffForm,
    writeoffFee,
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
    shownFees,
    feeColumns,
    fees,
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
    transactions,
    transactionColumns,
    transactionOpen,
    setTransactionOpen,
    transactionForm,
    createTransaction,
    voucherOpen,
    setVoucherOpen,
    voucherTarget,
    voucherForm,
    uploadVoucher,
    setVoucherFile,
    downloadVoucher,
    deleteVoucher,
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
    reconcileColumns,
    reconciliations,
    reconcileOpen,
    setReconcileOpen,
    reconcileForm,
    createReconciliation,
    feeReviewTargets,
    setFeeReviewTargets,
    feeReviewComment,
    setFeeReviewComment,
    submitFeeReview,
    feeReviewLoading,
    paymentReviewRows,
    feeReviewRows,
    reviewNumber,
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
    financePeople,
    customers,
    cases,
    contracts,
  } = props;

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
              {initialView === "finance-payment-package-manage" && (
                <>
                  <Button icon={<ReloadOutlined />} onClick={() => void loadPaymentPackages(originalQuery, paymentPackageMeta.page, paymentPackageMeta.pageSize)}>
                    刷新
                  </Button>
                  <Button type="primary" icon={<PlusOutlined />} onClick={() => openPaymentPackageEditor()}>
                    新增付款包
                  </Button>
                </>
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
                                {activeRouteConfig.headers.map((header: any, index: any) => {
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
                                {activeRouteConfig.headers.map((header: any, index: any) => {
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
                                  {activeRouteConfig.headers.map((header: any, index: any) => (
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
                                  (header: any, index: any) => (
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
                                    (header: any, index: any) => (
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
                                    (header: any, index: any) => (
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
                                    (header: any, index: any) => (
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
                            {activeRouteConfig.headers.map((header: any, index: any) => {
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
                          {activeRouteConfig.headers.map((header: any, index: any) => (
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
                            {activeRouteConfig.headers.map((header: any, index: any) => (
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
                                (header: any, index: any) => (
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
                                  (header: any, index: any) => (
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
                                  (header: any, index: any) => (
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
                            {activeRouteConfig.headers.map((_header: any, index: any) => (
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
                  <Dropdown
                    trigger={["click"]}
                    menu={{
                      items: [
                        { key: "settlement", label: "导出结算清单" },
                        { key: "receipt", label: "导出到账清单" },
                        { key: "case", label: "导出案件清单" },
                      ],
                      onClick: ({ key }) =>
                        void exportGeneralSettlement(
                          key as "settlement" | "receipt" | "case",
                        ),
                    }}
                  >
                    <Button loading={generalSettlementBusy}>导出 ▾</Button>
                  </Dropdown>
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
            <FinanceStatsCards summary={summary} />
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
                <LegacyHistoryPanel
                  rows={legacyFinanceRows}
                  loading={legacyFinanceLoading}
                  meta={legacyFinanceMeta}
                  summary={legacyFinanceSummary}
                  detail={legacyFinanceDetail}
                  detailLoading={legacyFinanceDetailLoading}
                  keyword={legacyFinanceKeyword}
                  kind={legacyFinanceKind}
                  statusCode={legacyFinanceStatusCode}
                  includeInactive={legacyFinanceIncludeInactive}
                  onKeywordChange={setLegacyFinanceKeyword}
                  onKindChange={setLegacyFinanceKind}
                  onStatusCodeChange={setLegacyFinanceStatusCode}
                  onIncludeInactiveChange={setLegacyFinanceIncludeInactive}
                  onLoad={loadLegacyFinanceHistory}
                  onOpenDetail={openLegacyFinanceDetail}
                  onCloseDetail={() => {
                    setLegacyFinanceDetail(null);
                    setLegacyFinanceDetailLoading(false);
                  }}
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
      <FeeReviewDrawer
        open={Boolean(feeReviewTargets.length)}
        initialView={initialView}
        reviewComment={feeReviewComment}
        reviewLoading={feeReviewLoading}
        paymentReviewRows={paymentReviewRows as any[]}
        feeReviewRows={feeReviewRows as any[]}
        reviewNumber={reviewNumber}
        onClose={() => {
          setFeeReviewTargets([]);
          setFeeReviewComment("");
        }}
        onCommentChange={setFeeReviewComment}
        onSubmit={(approved) => void submitFeeReview(approved)}
        onOpenCaseDetail={openCaseDetail}
      />
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
          title={`将修改已选费用关联的 ${selectedSettlementCases(false).length} 个案件（仅填写的字段会被修改）`}
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
      <IncomingAllocationModal
        open={Boolean(allocateTarget)}
        allocateTarget={allocateTarget}
        allocationValidationError={allocationValidationError}
        allocationKeyword={allocationKeyword}
        allocationStage={allocationStage}
        allocationFeeType={allocationFeeType}
        allocationLoading={allocationLoading}
        allocationCandidates={allocationCandidates}
        filteredAllocationCandidates={filteredAllocationCandidates}
        selectedAllocationKeys={selectedAllocationKeys as string[]}
        allocationAmounts={allocationAmounts}
        allocationComment={allocationComment}
        onOk={allocateIncoming}
        onCancel={() => {
          setAllocateTarget(null);
          setAllocationCandidates([]);
          setSelectedAllocationKeys([]);
          setAllocationValidationError("");
        }}
        onKeywordChange={setAllocationKeyword}
        onStageChange={setAllocationStage}
        onFeeTypeChange={setAllocationFeeType}
        onClearFilters={() => {
          setAllocationKeyword("");
          setAllocationStage("");
          setAllocationFeeType("");
        }}
        onSelectedKeysChange={setSelectedAllocationKeys}
        onAmountChange={(key, value) =>
          setAllocationAmounts((current) => ({ ...current, [key]: value }))
        }
        onCommentChange={setAllocationComment}
        onOpenCaseDetail={openCaseDetail}
      />
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
        width={860}
        open={paymentPackageEditorOpen}
        title={paymentPackageEditTarget ? `编辑付款包：${paymentPackageEditTarget.serial_no}` : "新增付款包"}
        okText="保存"
        cancelText="取消"
        confirmLoading={paymentPackageLoading}
        onOk={() => void submitPaymentPackageEditor()}
        onCancel={() => {
          setPaymentPackageEditTarget(null);
          setPaymentPackageEditorOpen(false);
          setPaymentPackageSelectedFeeIds([]);
          paymentPackageEditForm.resetFields();
        }}
      >
        <Alert
          type="info"
          showIcon
          message="请选择同一收款人的已审批内部费用"
          description="编辑后会重新计算金额，并同步更新所选费用。已核销付款包不可编辑。"
          style={{ marginBottom: 12 }}
        />
        <Table
          rowKey="id"
          size="small"
          pagination={{ pageSize: 6, size: "small" }}
          dataSource={paymentPackageCandidates}
          rowSelection={{
            selectedRowKeys: paymentPackageSelectedFeeIds,
            onChange: (keys) => setPaymentPackageSelectedFeeIds(keys.map(Number)),
          }}
          columns={[
            { title: "请款单号", dataIndex: "serial_no", width: 180 },
            { title: "收款人", render: (_: unknown, fee: Fee) => fee.data?.payee || fee.data?.applicant || fee.owner || "—" },
            { title: "金额", render: (_: unknown, fee: Fee) => money(Number(fee.data?.actual_commission ?? fee.data?.amount ?? 0)) },
            { title: "状态", dataIndex: "status", width: 100 },
          ]}
        />
        <Form form={paymentPackageEditForm} layout="vertical" style={{ marginTop: 12 }}>
          <Form.Item label="备注" name="comment" rules={[{ max: 500, message: "备注不能超过500个字符" }]}>
            <Input.TextArea rows={3} placeholder="可选，记录本次付款打包说明" />
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
      <SettlementReviewModals
        generalApplyTargets={generalSettlementApplyTargets}
        generalApplyComment={generalSettlementApplyComment}
        generalApplyBusy={generalSettlementBusy}
        onGeneralApplyCommentChange={setGeneralSettlementApplyComment}
        onGeneralApplySubmit={() => void submitGeneralSettlementApply()}
        onGeneralApplyCancel={() => {
          setGeneralSettlementApplyTargets([]);
          setGeneralSettlementApplyComment("");
        }}
        generalReviewTargets={generalSettlementReviewTargets}
        generalReviewApproved={generalSettlementReviewApproved}
        generalReviewComment={generalSettlementReviewComment}
        generalReviewBusy={generalSettlementBusy}
        onGeneralReviewCommentChange={setGeneralSettlementReviewComment}
        onGeneralReviewSubmit={() => void submitGeneralSettlementReview()}
        onGeneralReviewCancel={() => {
          setGeneralSettlementReviewTargets([]);
          setGeneralSettlementReviewComment("");
        }}
        generalPaymentTargets={generalSettlementPaymentTargets}
        generalPaymentAction={generalSettlementPaymentAction}
        generalPaymentComment={generalSettlementPaymentComment}
        generalPaymentBusy={generalSettlementBusy}
        onGeneralPaymentCommentChange={setGeneralSettlementPaymentComment}
        onGeneralPaymentSubmit={() => void submitGeneralSettlementPayment()}
        onGeneralPaymentCancel={() => {
          setGeneralSettlementPaymentTargets([]);
          setGeneralSettlementPaymentComment("");
        }}
        generalReapplyTargets={generalSettlementReapplyTargets}
        generalReapplyComment={generalSettlementReapplyComment}
        generalReapplyBusy={generalSettlementBusy}
        onGeneralReapplyCommentChange={setGeneralSettlementReapplyComment}
        onGeneralReapplySubmit={() => void submitGeneralSettlementReapply()}
        onGeneralReapplyCancel={() => {
          setGeneralSettlementReapplyTargets([]);
          setGeneralSettlementReapplyComment("");
        }}
        archiveReviewTargets={archiveSettlementReviewTargets}
        archiveReviewApproved={archiveSettlementReviewApproved}
        archiveReviewComment={archiveSettlementReviewComment}
        archiveReviewBusy={archiveSettlementBusy}
        onArchiveReviewCommentChange={setArchiveSettlementReviewComment}
        onArchiveReviewSubmit={() => void submitArchiveSettlementReview()}
        onArchiveReviewCancel={() => {
          setArchiveSettlementReviewTargets([]);
          setArchiveSettlementReviewComment("");
        }}
        archiveRollbackTargets={archiveSettlementRollbackTargets}
        archiveRollbackComment={archiveSettlementRollbackComment}
        archiveRollbackBusy={archiveSettlementBusy}
        isArchiveRejectedRoute={isArchiveSettlementRejectedRoute}
        onArchiveRollbackCommentChange={setArchiveSettlementRollbackComment}
        onArchiveRollbackSubmit={() => void submitArchiveSettlementRollback()}
        onArchiveRollbackCancel={() => {
          setArchiveSettlementRollbackTargets([]);
          setArchiveSettlementRollbackComment("");
        }}
        archiveReapplyTargets={archiveSettlementReapplyTargets}
        archiveReapplyComment={archiveSettlementReapplyComment}
        archiveReapplyBusy={archiveSettlementBusy}
        onArchiveReapplyCommentChange={setArchiveSettlementReapplyComment}
        onArchiveReapplySubmit={() => void submitArchiveSettlementReapply()}
        onArchiveReapplyCancel={() => {
          setArchiveSettlementReapplyTargets([]);
          setArchiveSettlementReapplyComment("");
        }}
      />
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

export default FinanceCenterView;
