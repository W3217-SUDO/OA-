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
