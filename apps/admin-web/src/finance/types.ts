export type Fee = {
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

export type FinanceFlow = Fee;

export type LegacyFinanceRecord = {
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

export type LegacyFinanceSummary = {
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

export type InvoiceCustomerDefaults = {
  customer: string;
  customer_no: string;
  invoice_title: string;
  taxpayer_id: string;
  invoice_phone: string;
  bank_account: string;
  bank_name: string;
  invoice_address: string;
};

export type InvoiceSourceFields = {
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

export type FinancePersonOption = { value: string; label: string; username: string };

export type Attachment = {
  id: number;
  original_name: string;
  category: string;
  size: number;
  uploader: string;
  created_at: string;
};

export type Transaction = {
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

export type PaymentPackagePreview = {
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

export type Reconciliation = {
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

export type IncomingPayment = {
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

export type Receivable = {
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

export type AllocationCandidate = {
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

export type ContractPaymentSourceSuccess = {
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

export type ContractPaymentSourceState =
  | { active: false }
  | { active: true; ok: false; error: string }
  | ContractPaymentSourceSuccess;

export type PaymentPrintDocumentData = {
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

export type OriginalFieldSpec = {
    label: string;
    key?: string;
    control?: "date" | "money" | "multi";
    options?: string[];
    defaultValue?: any;
    disabled?: boolean;
    readOnly?: boolean;
    pickerLabel?: string;
  };
export type OriginalRouteConfig = {
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