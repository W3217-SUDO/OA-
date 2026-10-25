import Constants from "expo-constants";

export const API_BASE_URL: string = (Constants.expoConfig?.extra?.apiBaseUrl as string) || "https://huzhilawfirm.com/api/v1";
export const APP_VERSION = Constants.expoConfig?.version || "0.0.0";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

let currentToken: string | null = null;
let onUnauthorized: (() => void) | null = null;

export function setApiToken(token: string | null) {
  currentToken = token;
}

export function setUnauthorizedHandler(handler: (() => void) | null) {
  onUnauthorized = handler;
}

export function authHeaders(): Record<string, string> {
  return {
    // 后端审计可据此区分请求来自 App 及其版本。
    "X-OA-Client": `mobile/${APP_VERSION}`,
    ...(currentToken ? { Authorization: `Bearer ${currentToken}` } : {}),
  };
}

/** FastAPI 的 detail 可能是字符串，也可能是校验错误数组。 */
export function errorDetail(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail.map((item) => (item as { msg?: string })?.msg || "").filter(Boolean).join("；") || fallback;
  }
  return fallback;
}

type RequestOptions = {
  method?: string;
  params?: Record<string, string | number | boolean | undefined | null>;
  json?: unknown;
  form?: Record<string, string>;
  multipart?: FormData;
  headers?: Record<string, string>;
  signal?: AbortSignal;
};

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const query = Object.entries(options.params || {})
    .filter(([, value]) => value !== undefined && value !== null && value !== "")
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
    .join("&");
  const headers: Record<string, string> = { Accept: "application/json", ...authHeaders(), ...options.headers };
  let body: string | FormData | undefined;
  if (options.multipart) {
    // 边界由 fetch 自动生成，不能手动设置 Content-Type。
    body = options.multipart;
  } else if (options.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.json);
  } else if (options.form) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    body = Object.entries(options.form).map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join("&");
  }
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}${query ? `?${query}` : ""}`, {
      method: options.method || (body ? "POST" : "GET"),
      headers,
      body,
      signal: options.signal,
    });
  } catch {
    throw new ApiError(0, "网络连接失败，请检查网络后重试");
  }
  const text = await response.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }
  if (!response.ok) {
    if (response.status === 401 && currentToken) onUnauthorized?.();
    throw new ApiError(response.status, errorDetail(data, `请求失败（${response.status}）`));
  }
  return data as T;
}

export const api = {
  get: <T>(path: string, params?: RequestOptions["params"]) => request<T>(path, { params }),
  post: <T>(path: string, json?: unknown, headers?: Record<string, string>) => request<T>(path, { method: "POST", json: json ?? {}, headers }),
};
