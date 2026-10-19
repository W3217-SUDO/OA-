import { safePublicUrl, validApiKeyHeader } from "../capability-market/connectorAuth";

export type PersonalMcpDraft = {
  server_name: string;
  name: string;
  server_url: string;
  transport: "streamable_http" | "sse";
  auth_type: "none" | "bearer" | "api_key";
  credential: string;
  api_key_header: string;
};

export const emptyMcpDraft = (): PersonalMcpDraft => ({ server_name: "default", name: "", server_url: "", transport: "streamable_http", auth_type: "none", credential: "", api_key_header: "X-API-Key" });

const SENSITIVE_QUERY = /^(?:key|(?:api|access|secret|private|client|x[-_]?api)[_-]?key(?:[_-]?id)?|credentials?|signature|(?:(?:access|refresh|id|auth)[_-]?)?token|secret|client[_-]?secret|password|authorization|passwd|sig|auth|ossaccesskeyid|x[-_]amz[-_](?:signature|credential|security[-_]token))$/i;

export function personalMcpUrl(value: string) {
  if (!safePublicUrl(value)) return false;
  const url = new URL(value);
  return url.protocol === "https:" && (!url.port || url.port === "443") && !url.hash && ![...url.searchParams.keys()].some(key => SENSITIVE_QUERY.test(key));
}

export function isMcpConnectionInput(text: string, connecting = false) {
  return /(?:连接|接入|添加|配置|绑定|创建|新建|链接|接通|导入|我的|查看|connect|add|setup)[\s\S]*mcp|mcp[\s\S]*(?:连接|接入|添加|配置|绑定|创建|新建|链接|接通|导入|url|https?:\/\/)/i.test(text)
    || /["'](?:mcpServers|mcp\.json)["']\s*:/.test(text)
    || /https?:\/\/[^\s"'{}]+\/mcp(?:[/?#\s"']|$)/i.test(text)
    || (connecting && /^\s*https?:\/\/\S+\s*$/i.test(text));
}

export function hasConnectionCredential(text: string) {
  const urls = text.match(/https?:\/\/[^\s"'<>}]+/gi) || [];
  const urlCredential = urls.some(value => {
    try {
      const url = new URL(value);
      return !!url.username || !!url.password || [...url.searchParams.keys()].some(key => SENSITIVE_QUERY.test(key));
    } catch {
      const queryStart = value.indexOf("?");
      if (queryStart < 0) return false;
      const query = new URLSearchParams(value.slice(queryStart + 1).split("#", 1)[0]);
      return [...query.keys()].some(key => SENSITIVE_QUERY.test(key));
    }
  });
  const nonUrlText = text.replace(/https?:\/\/[^\s"'<>}]+/gi, "");
  return urlCredential || /["'](?:authorization|api[-_]?key|(?:x-)?api[-_]key|credential|access_token|refresh_token|password|secret)["']\s*:\s*["'][^"'\s]+/i.test(nonUrlText)
    || /(?:authorization\s*[:=]\s*\S+|bearer\s+\S+|(?:api[-_ ]?key|token|密钥)\s*[:：=]\s*\S+)/i.test(nonUrlText);
}

// 配置只把公开连接信息交给模型，原始请求头和密钥不能进入普通消息。
export function mcpChatMessage(raw: string): string {
  if (!isMcpConnectionInput(raw) || !/^\s*(?:```(?:json)?\s*)?\{/.test(raw)) return raw;
  const draft = parsePersonalMcpConfig(raw);
  return `请帮我连接 MCP。连接名称：${draft.name || draft.server_name}；MCP 地址：${draft.server_url}；传输方式：${draft.transport}；认证方式：${draft.auth_type}。${draft.auth_type === "api_key" ? `认证请求头名称：${draft.api_key_header}。` : ""}${draft.credential ? "配置中的密钥没有发送给模型，请在连接确认时让我通过安全输入重新填写。" : "如需密钥，请让我通过安全输入填写。"}`;
}

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("配置必须是 JSON 对象");
  return value as Record<string, unknown>;
}

export function parsePersonalMcpConfig(raw: string): PersonalMcpDraft {
  const text = raw.trim().replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "");
  const draft = emptyMcpDraft();
  if (/^https?:\/\/\S+$/i.test(text)) {
    if (!personalMcpUrl(text)) throw new Error("仅支持 HTTPS 443 地址，不能包含账号、密码或密钥参数；凭据请在独立 Key 输入框填写");
    return { ...draft, server_url: text };
  }
  let parsed: unknown;
  try { parsed = JSON.parse(text); }
  catch { throw new Error("配置不是有效 JSON，请重新粘贴完整配置，或分别填写地址和 Key"); }
  let server = object(parsed);
  if (server["mcp.json"] !== undefined) server = object(server["mcp.json"]);
  if (server.mcpServers !== undefined) {
    const servers = Object.entries(object(server.mcpServers));
    if (servers.length !== 1) throw new Error("每次只能连接一个 MCP，请只粘贴本次需要连接的服务配置");
    draft.name = servers[0][0];
    draft.server_name = servers[0][0];
    server = object(servers[0][1]);
  }
  if (server.command || server.args || server.env) throw new Error("当前仅支持远程 HTTP / SSE MCP，不支持本机命令或环境变量配置");
  const allowed = new Set(["name", "url", "server_url", "type", "transport", "headers", "auth_type", "credential", "api_key_header"]);
  if (Object.keys(server).some(key => !allowed.has(key))) throw new Error("配置含暂不支持的字段，请仅保留远程地址、名称、传输方式和认证字段");
  const url = server.server_url ?? server.url;
  if (typeof url !== "string" || !personalMcpUrl(url)) throw new Error("请提供不含账号、密码或密钥参数的 HTTPS 443 MCP 地址");
  draft.server_url = url;
  if (server.name !== undefined && typeof server.name !== "string") throw new Error("连接名称必须是文本");
  if (typeof server.name === "string") draft.name = server.name;
  const transport = server.transport ?? server.type ?? "streamable_http";
  if (!["http", "streamableHttp", "streamable-http", "streamable_http", "sse"].includes(String(transport))) throw new Error("仅支持 HTTP / SSE 传输方式");
  draft.transport = transport === "sse" ? "sse" : "streamable_http";
  if (server.headers !== undefined) {
    const headers = Object.entries(object(server.headers));
    if (headers.length > 1) throw new Error("当前每个连接仅支持一个认证请求头，请分别填写认证方式和 Key");
    if (headers.length === 1) {
      const [header, value] = headers[0];
      if (typeof value !== "string") throw new Error("认证请求头的 Key 必须是文本");
      if (header.toLowerCase() === "authorization") {
        if (value && !/^Bearer\s+\S+/i.test(value)) throw new Error("Authorization 仅支持 Bearer 认证");
        draft.auth_type = "bearer";
        draft.credential = value.replace(/^Bearer\s+/i, "");
      } else {
        if (!validApiKeyHeader(header)) throw new Error("API Key 请求头名称不合法");
        draft.auth_type = "api_key";
        draft.api_key_header = header;
        draft.credential = value;
      }
    }
  }
  if (server.auth_type !== undefined) {
    if (!["none", "bearer", "api_key"].includes(String(server.auth_type))) throw new Error("不支持该认证方式");
    if (server.headers !== undefined) throw new Error("请勿同时使用 headers 和独立认证字段");
    draft.auth_type = server.auth_type as PersonalMcpDraft["auth_type"];
    if (server.credential !== undefined && typeof server.credential !== "string") throw new Error("Key 必须是文本");
    draft.credential = typeof server.credential === "string" ? server.credential : "";
    if (server.api_key_header !== undefined && typeof server.api_key_header !== "string") throw new Error("请求头名称必须是文本");
    if (typeof server.api_key_header === "string") draft.api_key_header = server.api_key_header;
  } else if (server.credential !== undefined || server.api_key_header !== undefined) throw new Error("独立认证字段必须同时指定 auth_type");
  if (draft.auth_type === "none" && draft.credential) throw new Error("无需 Token 模式不能同时提交 Key，请选择正确的认证方式");
  return draft;
}

export function validatePersonalMcpDraft(draft: PersonalMcpDraft, credentialSaved = false) {
  if (!draft.name.trim()) return "请填写连接名称";
  if (!personalMcpUrl(draft.server_url.trim())) return "请填写不含账号、密码或密钥参数的 HTTPS 443 MCP 地址";
  if (draft.auth_type !== "none" && !draft.credential.trim() && !credentialSaved) return "请填写 Key / Token";
  if (/\$\{|\*{3,}|^<.*>$/.test(draft.credential)) return "请填写真实 Key，不能使用占位符或脱敏值";
  if (draft.auth_type === "api_key" && !validApiKeyHeader(draft.api_key_header.trim())) return "请填写合法的 API Key 请求头名称";
  return "";
}

export function personalMcpConfiguration(draft: PersonalMcpDraft) {
  const headers: Record<string, string> = {};
  if (draft.auth_type === "bearer") headers.Authorization = draft.credential ? `Bearer ${draft.credential}` : "";
  if (draft.auth_type === "api_key") headers[draft.api_key_header.trim()] = draft.credential;
  return { "mcp.json": { mcpServers: { [draft.server_name]: { url: draft.server_url.trim(), type: draft.transport === "sse" ? "sse" : "streamableHttp", ...(Object.keys(headers).length ? { headers } : {}) } } } };
}
