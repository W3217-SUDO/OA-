export function isContractPayment(row: any): boolean;
export function paymentActionPath(row: any, action: string): string;
export function canEditContractPayment(row: any): boolean;
export function unifiedPaymentQueryParams(params: Record<string, any>): Record<string, any>;
export function paymentLineKey(row: any): string;
export function contractPaymentEditPayload(values: Record<string, any>, selectedKeys: string[], candidates: any[], amounts: Record<string, number | null>, remarks?: Record<string, string>): {
  payment_type_id: number; payer_name: string; application_date: string; remark: string;
  lines: Array<{ case_fee_id: number | null; contract_object_id: number | null; amount: number; remark: string }>;
};
