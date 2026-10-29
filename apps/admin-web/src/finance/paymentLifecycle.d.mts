export type PaymentLifecycleRow = {
  id?: number;
  module?: string;
  status?: string;
  data?: {
    _source_module?: string;
    writeoff_status?: string;
    paid_amount?: number | string | null;
    payment_status?: string;
    payment_package_id?: number | string | null;
  };
};

export type PaymentLineCandidate = {
  case_fee_id?: number | null;
  contract_object_id?: number | null;
  remaining_amount?: number | null;
};

export type ContractPaymentEditValues = {
  payment_type_id: number;
  payer_name?: string;
  application_date: string;
  remark?: string;
};

export type ContractPaymentEditPayload = {
  payment_type_id: number;
  payer_name: string;
  application_date: string;
  remark: string;
  lines: Array<{
    case_fee_id: number | null;
    contract_object_id: number | null;
    amount: number;
    remark: string;
  }>;
};

export function isContractPayment(row: PaymentLifecycleRow): boolean;
export function paymentActionPath(row: PaymentLifecycleRow & { id: number }, action: string): string;
export function paymentApplicationDate(row: { created_at?: string | null; data?: { payment_applied_at?: unknown; application_date?: unknown } | null } | null | undefined): string;
export function isPendingWriteoffPackage(row: PaymentLifecycleRow | null | undefined): boolean;
export function canEditContractPayment(row: PaymentLifecycleRow): boolean;
export function paymentLifecycleStatus(row: PaymentLifecycleRow): string;
export function unifiedPaymentQueryParams(params: Record<string, unknown>): Record<string, unknown> & {
  page: number;
  page_size: number;
};
export function paymentLineKey(row: PaymentLineCandidate): string;
export function contractPaymentEditPayload(
  values: ContractPaymentEditValues,
  selectedKeys: string[],
  candidates: PaymentLineCandidate[],
  amounts: Record<string, number | null | undefined>,
  remarks?: Record<string, string>,
): ContractPaymentEditPayload;
