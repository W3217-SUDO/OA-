import { isAxiosError } from "axios";

const SAFE_CODES: Record<string, string> = {
  authentication_required: "登录已失效，请重新登录",
  permission_denied: "没有操作此个人连接的权限",
  validation_error: "配置校验失败，请检查地址、传输方式和认证字段",
  revision_conflict: "连接配置已变化，请重新载入后操作",
  unsafe_url: "连接地址被安全策略拒绝，请使用公网 HTTPS 443 地址，不能访问内网或本机",
  upstream_auth_failed: "MCP 服务拒绝认证，请修改 Key / Token",
  upstream_unreachable: "MCP 服务不可达，请检查地址与网络",
};

const SAFE_DETAILS: Record<string, string> = {
  "不能连接内网、回环或保留地址": SAFE_CODES.unsafe_url,
  "服务域名解析失败": "MCP 服务域名解析失败，请检查地址",
  "连接验证只允许HTTPS默认端口443": "连接地址仅支持 HTTPS 默认端口 443",
  "连接验证只允许不含用户名和密码的HTTPS服务地址": "连接地址不能包含用户名和密码",
  "请通过请求头配置密钥，不要把凭据放入服务地址": "连接地址不能包含密钥，请改用独立 Key 输入框",
  "MCP地址不能包含凭据；请移除查询参数中的密钥并改用请求头": "连接地址不能包含密钥或签名参数，请改用独立 Key 输入框",
};

export function personalMcpError(failure: unknown, action: string) {
  if (!isAxiosError(failure)) return `${action}失败，服务响应未通过校验，请刷新个人连接核对状态`;
  const data = failure.response?.data;
  const code = data?.error_code ?? data?.detail?.error_code ?? data?.detail?.code;
  if (typeof code === "string" && Object.hasOwn(SAFE_CODES, code)) return `${action}失败：${SAFE_CODES[code]}`;
  if (typeof data?.detail === "string" && Object.hasOwn(SAFE_DETAILS, data.detail)) return `${action}失败：${SAFE_DETAILS[data.detail]}`;
  const statuses: Record<number, string> = {
    401: SAFE_CODES.authentication_required,
    403: SAFE_CODES.permission_denied,
    404: "个人连接不存在或已被删除，请刷新列表",
    409: SAFE_CODES.revision_conflict,
    422: SAFE_CODES.validation_error,
    429: "请求过于频繁，请稍后重试",
    502: SAFE_CODES.upstream_unreachable,
    503: "连接服务暂不可用，请稍后重试",
    504: "MCP 服务响应超时，请检查服务状态",
  };
  if (failure.response) return `${action}失败：${statuses[failure.response.status] || `服务返回 HTTP ${failure.response.status}，请联系管理员核对`}`;
  return `${action}失败：${failure.code === "ECONNABORTED" ? "请求超时" : "网络请求未完成"}，请刷新个人连接核对实际状态，勿重复创建`;
}

export function personalMcpVerificationError(code: unknown) {
  return typeof code === "string" && Object.hasOwn(SAFE_CODES, code) ? SAFE_CODES[code] : "握手或工具目录检测失败，请检查地址、认证和网络";
}
