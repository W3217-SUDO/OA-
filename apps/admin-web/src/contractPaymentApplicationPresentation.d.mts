export type ContractPaymentApplicationLine = {
  contract_object_id: number;
  case_record_id: number;
  case_no: string;
  fee_type: string;
  requested_amount: number;
};

export type ContractPaymentApplicationRow = {
  id: number;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
  owner: string;
  department: string;
  description: string;
  data: {
    amount: number;
    signed_at: string;
    type: string;
    lines: ContractPaymentApplicationLine[];
    line_summary: string;
    [key: string]: unknown;
  };
  lines: ContractPaymentApplicationLine[];
  line_summary: string;
};

export declare const normalizeContractPaymentApplications: (
  payload?: { items?: unknown[] },
  contract?: { id?: number; serial_no?: string },
) => ContractPaymentApplicationRow[];
