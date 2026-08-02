export const CONTRACT_ATTACHMENT_ACCEPT: string;
export const CONTRACT_ATTACHMENT_MAX_BYTES: number;
export const CONTRACT_ATTACHMENT_LOCKED_STATUSES: readonly string[];
export const CONTRACT_DRAFT_EDITABLE_STATUSES: readonly string[];
export function buildContractDraftDefaults(input: {
  serialNo: string;
  profile: { username?: string; department?: string };
  customer?: { id: number; title?: string } | null;
}): {
  serial_no: string;
  status: string;
  owner: string;
  department: string;
  type: string;
  contract_body: string;
  fee_type: string;
  amount: number;
  signed_at: Date;
  customer_id: number | undefined;
  title: string | undefined;
};
export function validateContractDraftValues(values: Record<string, unknown>): string[];
export function resolveContractCustomerSelection<T extends { id: number }>(customerId: number | undefined, customers: T[], linkedCustomer: { id: number; name: string; serial_no?: string } | null, profile: { username?: string }): T | { id: number; serial_no: string; title: string; owner: string; data: { customer_managers: string[] } } | null;
export function filterContractCaseOptions<T extends { customer?: string }>(cases: T[], customer: string): T[];
export function canActOnContractApproval(status: string, approver: string, username: string, role: string): boolean;
export function buildContractApprovalPayload(approved: boolean, comment: unknown): { approved: boolean; comment: string };
export function canMutateContractAttachments(status: string): boolean;
export function validateContractAttachment(file: { size?: number } | null | undefined): string | null;
