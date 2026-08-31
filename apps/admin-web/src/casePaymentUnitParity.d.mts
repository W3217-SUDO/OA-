export const buildCasePaymentTypeSelectOptions: (items?: Array<Record<string, unknown>>) => Array<{ value: number; label: string }>;
export const buildExternalPaymentRequestPayload: (values?: Record<string, unknown>, comment?: string) => { amount: number; payment_type_id: number; payment_remark: string; comment: string };
