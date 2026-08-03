export function buildCaseHearingPayload(values: unknown): Record<string, unknown>;
export function getCaseHearingValidationError(values: unknown): string;
export function getCaseHearingDeleteValidationError(role: unknown): string;
export function getCaseArchiveReviewValidationError(input: { role?: unknown; status?: unknown }): string;
export function getCaseUnarchiveReviewValidationError(input: {
  role?: unknown;
  status?: unknown;
  requestStatus?: unknown;
  requestedBy?: unknown;
  currentUsername?: unknown;
  approved?: unknown;
  comment?: unknown;
}): string;
export function buildCaseUnarchiveReviewPayload(input: { approved?: unknown; comment?: unknown }): {
  approved: boolean;
  comment: string;
};
