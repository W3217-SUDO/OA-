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

export async function financeDownloadErrorDetail(error: unknown): Promise<string | undefined> {
  if (!isRecord(error) || !isRecord(error.response)) return undefined;
  const data = error.response.data;
  if (!(data instanceof Blob) || !data.type.includes("json")) return financeErrorDetail(error);
  let payload: unknown;
  try {
    payload = JSON.parse(await data.text());
  } catch {
    return "服务器返回的导出错误信息格式无效";
  }
  const detail = financeErrorDetail({ response: { data: payload } });
  if (detail) return detail;
  if (isRecord(payload) && Array.isArray(payload.detail)) {
    const messages = payload.detail.filter(isRecord).map((entry) => {
      const path = Array.isArray(entry.loc) ? entry.loc.join(".") : "";
      return typeof entry.msg === "string" ? `${path ? `${path}：` : ""}${entry.msg}` : "";
    }).filter(Boolean);
    if (messages.length) return messages.join("；");
  }
  return "服务器返回的导出错误信息缺少 detail";
}
