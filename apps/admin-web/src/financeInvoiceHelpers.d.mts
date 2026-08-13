export declare const buildInvoiceApplicationPayload: (input: {
  values?: Record<string, any>;
  cases?: any[];
  contracts?: any[];
  caseFees?: any[];
  requireSource?: boolean;
}) =>
  | { ok: false; error: string }
  | { ok: true; payload: Record<string, any> };
