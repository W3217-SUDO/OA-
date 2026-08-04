export function getIprCaseActionValidationError(input: {
  action?: unknown;
  role?: unknown;
  status?: unknown;
  applicationNo?: unknown;
  approved?: unknown;
  comment?: unknown;
}): string;

export function buildIprCaseActionPayload(input: {
  action?: unknown;
  approved?: unknown;
  comment?: unknown;
}): { approved?: boolean; comment: string };

export function normalizeIprCaseActionResponse(
  response: unknown,
  fallback: string,
): { ok: boolean; message: string };

export function getIprCaseActionErrorMessage(
  error: unknown,
  fallback: string,
): string;
