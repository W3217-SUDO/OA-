import { api } from "../api";

type LoginResult = { access_token: string; user: any; must_change_password?: boolean };
type BindingRequired = { binding_required: true };
let callbackRequest: Promise<LoginResult | BindingRequired> | null = null;

export function clearDingTalkWebCallback(): void {
  callbackRequest = null;
}

export function consumeDingTalkWebCallback(): Promise<LoginResult | BindingRequired> | null {
  if (callbackRequest) return callbackRequest;
  const url = new URL(window.location.href);
  const authCode = url.searchParams.get("authCode");
  const state = url.searchParams.get("state");
  const error = url.searchParams.get("error");
  if (!state || (!authCode && !error)) return null;
  // 单次授权码不能因 StrictMode 或组件重渲染重复消费，也不保留在地址栏中。
  for (const key of ["authCode", "state", "error", "error_description"]) url.searchParams.delete(key);
  window.history.replaceState(null, "", url.toString());
  callbackRequest = error
    ? Promise.reject(new Error("钉钉授权已取消或失败，请重新扫码"))
    : api.post("/auth/dingtalk/web/login", { auth_code: authCode, state }).then(({ data }) => data).catch((failure) => {
      if (failure?.response?.status === 403 && failure.response.data?.binding_required === true) return { binding_required: true };
      throw failure;
    });
  return callbackRequest;
}

export async function startDingTalkWebLogin(): Promise<void> {
  const { data } = await api.get<{ authorize_url: string }>("/auth/dingtalk/web/start");
  const url = new URL(data.authorize_url);
  if (url.origin !== "https://login.dingtalk.com" || url.pathname !== "/oauth2/auth") throw new Error("钉钉登录授权地址无效");
  window.location.assign(url.toString());
}

export async function bindDingTalkWebLogin(values: { username: string; password: string }): Promise<LoginResult> {
  const { data } = await api.post<LoginResult>("/auth/dingtalk/web/bind", values);
  return data;
}
