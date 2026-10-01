import { Button } from "antd";
import { IncomingAllocationRecordsPage } from "./IncomingAllocationRecordsPage";
import { InvoiceApplicationPage } from "./InvoiceApplicationPage";
import { PaymentApplicationPage } from "./PaymentApplicationPage";
import { FeeReviewDrawer } from "./FeeReviewDrawer";
import { IncomingAllocationModal, type IncomingAllocationModalProps } from "./IncomingAllocationModal";
import { SettlementReviewModals, type SettlementReviewModalsProps } from "./SettlementReviewModals";
import { SettlementContextModal, type SettlementContextModalProps } from "./SettlementContextModal";
import { PaymentReversalModals, type PaymentReversalModalsProps } from "./PaymentReversalModals";
import { PaymentWriteoffModal, type PaymentWriteoffModalProps } from "./PaymentWriteoffModal";
import { InvoiceMaintenanceModals, type InvoiceMaintenanceModalsProps } from "./InvoiceMaintenanceModals";
import { InvoiceLifecycleModals, type InvoiceLifecycleModalsProps } from "./InvoiceLifecycleModals";
import { RefundCreationModal, type RefundCreationModalProps } from "./RefundCreationModal";
import { RefundAmountModal, RefundCompleteModal, type RefundMaintenanceModalsProps } from "./RefundMaintenanceModals";
import { RefundBatchFeeDrawer, type RefundBatchFeeDrawerProps } from "./RefundBatchFeeDrawer";
import { PaymentPackageEditorModal, PaymentPackageWriteoffModal, type PaymentPackageEditorModalProps, type PaymentPackageWriteoffModalProps } from "./PaymentPackageEditorModal";
import { RecordFilesModal, VoucherModal, type RecordFilesModalProps, type VoucherModalProps } from "./FinanceDocumentModals";
import { TransactionModal, ReconciliationModal, type TransactionModalProps, type ReconciliationModalProps } from "./FinanceLedgerModals";
import { FinanceOriginalRoutesView, type FinanceOriginalRoutesViewProps } from "./FinanceOriginalRoutesView";
import { FinanceStandardTabsView, type FinanceStandardTabsViewProps } from "./FinanceStandardTabsView";
import { SettlementBatchModal, type SettlementBatchModalProps } from "./SettlementBatchModal";
import { IncomingRegistrationModal, IncomingClaimModal, type IncomingRegistrationModalProps, type IncomingClaimModalProps } from "./FinanceIncomingModals";
import { FeeDetailModal, FeeEditorModal, type FeeDetailModalProps, type FeeEditorModalProps } from "./FinanceFeeModals";
import { RefundDetailModal, RefundBatchStatusModal, type RefundDetailModalProps, type RefundBatchStatusModalProps } from "./FinanceRefundDetailModals";
import { RefundCaseFeeModals, type RefundCaseFeeModalsProps } from "./RefundCaseFeeActions";
import type { Fee, FinanceFlow, IncomingPayment } from "./types";

export interface FinanceCenterViewProps {
  originalRoutesView: FinanceOriginalRoutesViewProps;
  standardTabsView: FinanceStandardTabsViewProps;
  settlementBatchModal: SettlementBatchModalProps;
  incomingRegistrationModal: IncomingRegistrationModalProps;
  incomingClaimModal: IncomingClaimModalProps;
  paymentPackageWriteoffModal: PaymentPackageWriteoffModalProps;
  feeDetailModal: FeeDetailModalProps;
  feeEditorModal: FeeEditorModalProps;
  refundDetailModal: RefundDetailModalProps;
  refundBatchStatusModal: RefundBatchStatusModalProps;
  settlementContextModal: SettlementContextModalProps;
  // Route / view state
  initialView: string;
  originalMode: boolean;
  isInternalHistoryList: boolean;

  // Page / detail pages
  incomingPaymentDetailPage: React.ReactNode;
  invoiceDetailPage: React.ReactNode;
  contractPaymentEditPage: React.ReactNode;
  paymentPrintPreviewPage: React.ReactNode;
  paymentPackagePrintPage: React.ReactNode;
  internalPaymentDetail: React.ReactNode;

  // Original mode - display
  onMergePrint: () => Promise<void>;

  // Original mode - actions / loaders
  load: () => Promise<void>;
  openCaseDetail: (caseNo: unknown) => void;
  openContractDetail: (contractNo: string) => void;

  // Payment packages
  paymentPackageWriteoffTarget: Fee | null;
  setPaymentPackageWriteoffTarget: (target: Fee | null) => void;
  paymentPackageEditor: PaymentPackageEditorModalProps;

  // General settlement
  settlementReviewModals: SettlementReviewModalsProps;

  // Refund case fee
  refundCaseFeeModals: RefundCaseFeeModalsProps;

  // Refund batch fee
  refundBatchFeeDrawer: RefundBatchFeeDrawerProps;

  // Fee detail modal
  feeDetail: Fee | null;
  setFeeDetail: (fee: Fee | null) => void;

  // Incoming
  incomingAllocationTarget: IncomingPayment | null;
  setIncomingAllocationTarget: (target: IncomingPayment | null) => void;

  // Allocation
  incomingAllocationModal: IncomingAllocationModalProps;

  // Writeoff
  paymentWriteoffModal: PaymentWriteoffModalProps;

  // Payment cancel / rollback
  paymentReversalModals: PaymentReversalModalsProps;

  // Invoices tab
  invoiceOpen: boolean;
  invoiceEditTarget: FinanceFlow | null;
  invoiceSelectedFeeIds: number[];
  closeInvoiceApplication: () => void;
  invoiceForm: any;
  createInvoice: (submit?: boolean) => Promise<void>;
  invoiceFeeOptions: Fee[];
  applyInvoiceFeeSelection: (nextIds: number[]) => void;
  loadInvoiceReferenceData: (options?: Record<string, any>) => Promise<any>;

  // Invoice mutation
  invoiceMaintenanceModals: InvoiceMaintenanceModalsProps;
  invoiceLifecycleModals: InvoiceLifecycleModalsProps;

  // Refunds tab
  refundCreationModal: RefundCreationModalProps;
  refundMaintenanceModals: RefundMaintenanceModalsProps;

  // Transactions tab
  transactionModal: TransactionModalProps;

  // Voucher
  voucherModal: VoucherModalProps;

  // Record files
  recordFilesModal: RecordFilesModalProps;

  // Reconcile
  reconciliationModal: ReconciliationModalProps;

  // Fee review drawer (passed to FeeReviewDrawer component)
  feeReviewTargets: Fee[];
  setFeeReviewTargets: (targets: Fee[]) => void;
  feeReviewComment: string;
  setFeeReviewComment: (comment: string) => void;
  submitFeeReview: (approved: boolean) => Promise<void>;
  feeReviewLoading: boolean;
  paymentReviewRows: any[];
  feeReviewRows: any[];
  reviewNumber: (value: unknown) => React.ReactNode;

}

export function FinanceCenterView(props: FinanceCenterViewProps) {
  const {
    originalRoutesView,
    standardTabsView,
    settlementBatchModal,
    incomingRegistrationModal,
    incomingClaimModal,
    paymentPackageWriteoffModal,
    feeDetailModal,
    feeEditorModal,
    refundDetailModal,
    refundBatchStatusModal,
    settlementContextModal,
    initialView,
    originalMode,
    isInternalHistoryList,
    incomingPaymentDetailPage,
    invoiceDetailPage,
    contractPaymentEditPage,
    paymentPrintPreviewPage,
    paymentPackagePrintPage,
    internalPaymentDetail,
    onMergePrint,
    load,
    openCaseDetail,
    openContractDetail,
    paymentPackageWriteoffTarget,
    setPaymentPackageWriteoffTarget,
    paymentPackageEditor,
    settlementReviewModals,
    refundCaseFeeModals,
    refundBatchFeeDrawer,
    feeDetail,
    setFeeDetail,
    incomingAllocationTarget,
    setIncomingAllocationTarget,
    incomingAllocationModal,
    paymentWriteoffModal,
    paymentReversalModals,
    invoiceOpen,
    invoiceEditTarget,
    invoiceSelectedFeeIds,
    closeInvoiceApplication,
    invoiceForm,
    createInvoice,
    invoiceFeeOptions,
    applyInvoiceFeeSelection,
    loadInvoiceReferenceData,
    invoiceMaintenanceModals,
    invoiceLifecycleModals,
    refundCreationModal,
    refundMaintenanceModals,
    transactionModal,
    voucherModal,
    recordFilesModal,
    reconciliationModal,
    feeReviewTargets,
    setFeeReviewTargets,
    feeReviewComment,
    setFeeReviewComment,
    submitFeeReview,
    feeReviewLoading,
    paymentReviewRows,
    feeReviewRows,
    reviewNumber,
  } = props;

  if (paymentPackageWriteoffTarget) {
    return <PaymentApplicationPage key={paymentPackageWriteoffTarget.id} record={paymentPackageWriteoffTarget} onClose={() => setPaymentPackageWriteoffTarget(null)} onChange={load} onCase={openCaseDetail} onContract={openContractDetail} />;
  }
  if (incomingAllocationTarget) {
    return <IncomingAllocationRecordsPage key={incomingAllocationTarget.id} paymentId={incomingAllocationTarget.id} onClose={() => setIncomingAllocationTarget(null)} onChange={load} onCase={openCaseDetail} onContract={openContractDetail} />;
  }
  if (feeDetail && !isInternalHistoryList && (feeDetail.data?.application_items || initialView.startsWith("finance-payment-") && (feeDetail.module === "contract_payment" || feeDetail.data?.expense_scope !== "内部" && feeDetail.data?.fee_type !== "内部费用"))) {
    return <PaymentApplicationPage key={feeDetail.id} record={feeDetail} onClose={() => setFeeDetail(null)} onChange={load} onCase={openCaseDetail} onContract={openContractDetail} />;
  }
  return (
    <>
      {initialView === "finance-payment-waiting" && <Button style={{ margin: 8 }} onClick={() => void onMergePrint()}>合并打印</Button>}
      {contractPaymentEditPage || (invoiceOpen ? <InvoiceApplicationPage form={invoiceForm} target={invoiceEditTarget} fees={invoiceFeeOptions}
        selectedIds={invoiceSelectedFeeIds} onSelect={applyInvoiceFeeSelection} onSave={createInvoice}
        loadReference={loadInvoiceReferenceData}
        openCase={openCaseDetail} openContract={openContractDetail}
        onClose={closeInvoiceApplication} /> : null) || incomingPaymentDetailPage ||
        invoiceDetailPage ||
        paymentPrintPreviewPage ||
        paymentPackagePrintPage ||
        internalPaymentDetail ||
        (originalMode ? (
          <FinanceOriginalRoutesView {...originalRoutesView} />
        ) : (
          <FinanceStandardTabsView {...standardTabsView} />
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
      <RefundBatchFeeDrawer {...refundBatchFeeDrawer} />
      <SettlementBatchModal {...settlementBatchModal} />
      <SettlementContextModal {...settlementContextModal} />
      <IncomingRegistrationModal {...incomingRegistrationModal} />
      <IncomingClaimModal {...incomingClaimModal} />
      <IncomingAllocationModal {...incomingAllocationModal} />
      <PaymentWriteoffModal {...paymentWriteoffModal} />
      <PaymentReversalModals {...paymentReversalModals} />
      <PaymentPackageWriteoffModal {...paymentPackageWriteoffModal} />
      <PaymentPackageEditorModal {...paymentPackageEditor} />
      <FeeDetailModal {...feeDetailModal} />
      <RefundDetailModal {...refundDetailModal} />
      <FeeEditorModal {...feeEditorModal} />
      <RefundCreationModal {...refundCreationModal} />
      <InvoiceMaintenanceModals {...invoiceMaintenanceModals} />
      <InvoiceLifecycleModals {...invoiceLifecycleModals} />
      <RefundAmountModal {...refundMaintenanceModals.amount} />
      <RefundCaseFeeModals {...refundCaseFeeModals} />
      <RefundBatchStatusModal {...refundBatchStatusModal} />
      <RefundCompleteModal {...refundMaintenanceModals.complete} />
      <RecordFilesModal {...recordFilesModal} />
      <TransactionModal {...transactionModal} />
      <VoucherModal {...voucherModal} />
      <SettlementReviewModals {...settlementReviewModals} />
      <ReconciliationModal {...reconciliationModal} />
    </>
  );
}

export default FinanceCenterView;
