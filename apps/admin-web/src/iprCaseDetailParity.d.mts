export function getIprCaseCustomerValidationError(input: { customerIds?: unknown; primaryCustomerId?: unknown }): string;
export function buildIprCaseCustomerPayload(input: { customerIds?: unknown; primaryCustomerId?: unknown }): { customer_ids: number[]; primary_customer_id: number };
export function buildIprCaseContactPayload(input: { customerId?: unknown; documentContactIds?: unknown; technologyContactIds?: unknown }): { customer_id: number; document_contact_ids: string[]; technology_contact_ids: string[] };
export function buildIprCaseLawFirmPayload(input: { lawFirmIds?: unknown }): { law_firm_ids: number[] };
export function getIprCaseDeletionConfirmation(kind: unknown, label?: unknown): { title: string; content: string; okText: string; cancelText: string };
