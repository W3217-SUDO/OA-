function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object";
}

export function financeErrorDetail(error: unknown): string | undefined {
  if (!isRecord(error)) return undefined;
  const response = error.response;
  if (!isRecord(response) || !isRecord(response.data)) return undefined;
  const detail = response.data.detail;
  return typeof detail === "string" && detail ? detail : undefined;
}

export function financeErrorMessageText(error: unknown): string | undefined {
  if (!isRecord(error)) return undefined;
  return typeof error.message === "string" && error.message ? error.message : undefined;
}
