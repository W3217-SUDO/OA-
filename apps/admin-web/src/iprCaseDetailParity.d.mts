export function getIprCaseCustomerValidationError(input: { customerIds?: unknown; primaryCustomerId?: unknown }): string;
export function buildIprCaseCustomerPayload(input: { customerIds?: unknown; primaryCustomerId?: unknown }): { customer_ids: number[]; primary_customer_id: number };
export function buildIprCaseContactPayload(input: { customerId?: unknown; documentContactIds?: unknown; technologyContactIds?: unknown }): { customer_id: number; document_contact_ids: string[]; technology_contact_ids: string[] };
export function buildIprCaseLawFirmPayload(input: { lawFirmIds?: unknown }): { law_firm_ids: number[] };
export function getIprCaseDeletionConfirmation(kind: unknown, label?: unknown): { title: string; content: string; okText: string; cancelText: string };
export function getIprApiErrorMessage(error: unknown, fallback?: string): string;
export function getIprSectionLoadError(section: "files" | "logs" | "reminders" | "assistedFees", error: unknown): string;
export function getIprCompatibleFileCategory(input: { category?: unknown; caseKinds?: unknown; fileTypes?: unknown }): string | undefined;
export function buildIprDeadlineFromOffset(input: { baseDate?: unknown; years?: unknown; months?: unknown; days?: unknown }): string;
