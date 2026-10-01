import type { Dayjs } from "dayjs";

export interface PaymentWriteoffFormValues {
  writeoff_date?: Dayjs;
  voucher_no?: string;
  comment?: string;
}

export interface InvoiceNumberFormValues {
  application_no?: string;
  contract_no?: string;
  old_invoice_no?: string;
  new_invoice_no?: string;
}

export interface InvoiceDateFormValues {
  application_no?: string;
  application_date?: Dayjs | null;
  invoice_date?: Dayjs | null;
}

export interface InvoiceIssueFormValues {
  invoice_holder?: string;
  extra_amount?: number;
  invoice_no?: string;
  invoice_date?: Dayjs;
  comment?: string;
}

export interface InvoiceVoidFormValues {
  reason?: string;
}

export interface RefundCreationFormValues {
  fee_record_id?: number;
  case_no?: string;
  customer?: string;
  court?: string;
  original_payment_no?: string;
  amount?: number;
  applicant?: string;
  expected_date?: Dayjs | null;
  refund_account_name?: string;
  refund_bank?: string;
  refund_account?: string;
  reason?: string;
  remark?: string;
}

export interface RefundAmountFormValues {
  amount?: number;
  comment?: string;
}

export interface RefundCompleteFormValues {
  actual_date?: Dayjs;
  voucher_no?: string;
  comment?: string;
}

export interface IncomingPaymentFormValues {
  received_date: Dayjs;
  amount: number;
  payer_name: string;
  bank_reference: string;
  remark?: string;
}

export interface IncomingClaimFormValues {
  customer: string;
  comment?: string;
}

export interface TransactionFormValues {
  finance_record_id?: number;
  transaction_type: string;
  amount: number;
  transaction_date: Dayjs;
  voucher_no?: string;
  counterparty?: string;
  remark?: string;
}

export interface ReconciliationFormValues {
  period_type: string;
  period: [Dayjs, Dayjs];
  discrepancy_amount?: number;
  remark?: string;
}

export interface RefundBatchFeeItemValues {
  case_id?: number;
  case_no?: string;
  customer?: string;
  contract_record_id?: number | null;
  fee_type_id?: number | string;
  fee_type_name?: string;
  fee_type?: string;
  amount?: number;
  remark?: string;
  deadline?: Dayjs;
  payment_type_id?: number | null;
  payment_amount?: number;
  payment_remark?: string;
  payee_username?: string;
  base_amount?: number;
  reference_commission?: number;
}

export interface RefundBatchFeeFormValues {
  handler?: string;
  items: RefundBatchFeeItemValues[];
}

export interface PaymentPackageEditorFormValues {
  comment?: string;
}

export interface RecordFileFormValues {
  category: string;
  document_date?: Dayjs;
  remark?: string;
}

export interface VoucherFormValues {
  category: string;
  remark?: string;
}

export interface SettlementBatchFormValues {
  hearing_lawyer?: string;
  assistant?: string;
  handling_lawyers?: string;
  source_lawyer?: string;
  litigation_amount?: number;
  case_stage?: string;
  comment?: string;
}

export interface PaymentPackageWriteoffFormValues {
  package_no: string;
  amount: number;
  paid_date: Dayjs;
  payment_method: string;
  invoice_no: string;
  remark?: string;
}

export interface FeeEditorFormValues {
  case_record_id?: number;
  contract_record_id?: number;
  title?: string;
  fee_type?: string;
  expense_subtype?: string;
  expense_scope?: string;
  fee_type_id?: number;
  amount?: number;
  handler?: string;
  case_no?: string;
  customer?: string;
  payee?: string;
  court?: string;
  document_no?: string;
  description?: string;
  commission_mode?: "automatic" | "manual";
  commission_details?: unknown[];
}
