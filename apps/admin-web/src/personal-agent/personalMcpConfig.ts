import { safePublicUrl, validApiKeyHeader } from "../capability-market/connectorAuth";

export type PersonalMcpDraft = {
  server_name: string;
  name: string;
  server_url: string;
  transport: "streamable_http" | "sse";
  auth_type: "none" | "bearer" | "api_key";
  credential: string;
  api_key_header: string;
  // 整段粘贴多个服务时合成一个分组：共用一个认证方式和 Key，单个服务时为空，仍用上面的地址字段。
  services: PersonalMcpService[];
  // 本机命令型服务（command / npx）无法在服务器运行，载入时跳过，只记名称用于提示。
  skipped: string[];
};

export type PersonalMcpService = { server_name: string; server_url: string; transport: "streamable_http" | "sse" };

export const LOCAL_COMMAND_SKIPPED = "服务器不支持本机命令型 MCP，已跳过";
export const MAX_GROUP_SERVICES = 12;

export const emptyMcpDraft = (): PersonalMcpDraft => ({ server_name: "default", name: "", server_url: "", transport: "streamable_http", auth_type: "none", credential: "", api_key_header: "X-API-Key", services: [], skipped: [] });

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

// 完整配置提交后端处理；等待期间的消息气泡不展示原始凭据。
export function mcpChatMessage(raw: string): string {
  return hasConnectionCredential(raw) || isMcpConnectionInput(raw)
    ? "请配置此 MCP 连接（地址与凭据已提交，等待处理结果）。" : raw;
}

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("配置必须是 JSON 对象");
  return value as Record<string, unknown>;
}

// 各家配置示例常带说明、超时、开关等字段，与连接无关，载入时忽略。
const IGNORED_FIELDS = new Set(["description", "timeout", "disabled", "enabled", "autoApprove", "alwaysAllow", "note", "notes", "title", "icon", "category", "tags", "readTimeout", "connectTimeout", "sse_read_timeout"]);
const KNOWN_PROVIDERS: [RegExp, string][] = [[/(^|\.)qcc\.com$/i, "企查查"], [/(^|\.)tianyancha\.com$/i, "天眼查"], [/(^|\.)pkulaw\.(com|cn)$/i, "北大法宝"], [/(^|\.)baidu\.com$/i, "百度"]];

type ParsedServer = Omit<PersonalMcpDraft, "services" | "skipped">;

const isLocalCommand = (server: Record<string, unknown>) => server.command !== undefined || server.args !== undefined || (server.env !== undefined && server.url === undefined && server.server_url === undefined);

function parseServer(input: Record<string, unknown>, serverName: string): ParsedServer {
  const draft: ParsedServer = { ...emptyMcpDraft(), server_name: serverName, name: serverName === "default" ? "" : serverName };
  const server = Object.fromEntries(Object.entries(input).filter(([key]) => !IGNORED_FIELDS.has(key)));
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

// 分组名默认取已知服务商名称，其次取服务名共同前缀，最后取域名主体，用户可改。
export function defaultGroupName(services: PersonalMcpService[]) {
  const hosts = [...new Set(services.map(service => new URL(service.server_url).hostname.toLowerCase()))];
  for (const [pattern, label] of KNOWN_PROVIDERS) if (hosts.every(host => pattern.test(host))) return label;
  const names = services.map(service => service.server_name);
  let prefix = names[0] || "";
  for (const name of names.slice(1)) while (prefix && !name.startsWith(prefix)) prefix = prefix.slice(0, -1);
  prefix = prefix.replace(/[\s._\-/:]+$/, "");
  if (prefix.length >= 2) return prefix;
  const domains = [...new Set(hosts.map(host => { const parts = host.split("."); return parts.length > 1 ? parts.at(-2)! : host; }))];
  return domains.length === 1 ? domains[0] : "MCP 分组";
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
  if (server.mcpServers === undefined) return { ...draft, ...parseServer(server, "default") };
  const entries = Object.entries(object(server.mcpServers)).map(([name, value]) => [name, object(value)] as const);
  if (!entries.length) throw new Error("没有找到要配置的 MCP 服务，请粘贴完整配置");
  const skipped = entries.filter(([, value]) => isLocalCommand(value)).map(([name]) => name);
  const remote = entries.filter(([, value]) => !isLocalCommand(value));
  if (!remote.length) throw new Error(`${LOCAL_COMMAND_SKIPPED}：${skipped.join("、")}。请改用服务方提供的远程地址（https 开头）`);
  if (remote.length > MAX_GROUP_SERVICES) throw new Error(`一个 MCP 分组最多 ${MAX_GROUP_SERVICES} 个远程服务，这次有 ${remote.length} 个，请分组粘贴`);
  const servers = remote.map(([name, value]) => {
    if (!name.trim() || name.length > 80) throw new Error("服务名称须为 1 至 80 个字符");
    try { return parseServer(value, name); }
    catch (failure) { throw new Error(`服务「${name}」：${failure instanceof Error ? failure.message : "配置无效"}`); }
  });
  if (servers.length === 1) return { ...draft, ...servers[0], name: servers[0].name || servers[0].server_name, skipped };
  const [first] = servers;
  // 同一分组共用一个认证方式和 Key，只保存一份；各服务 Key 不同就不能合成一组。
  if (servers.some(item => item.auth_type !== first.auth_type || item.credential !== first.credential || (item.auth_type === "api_key" && item.api_key_header !== first.api_key_header)))
    throw new Error("这些服务的认证方式或 Key 不一致，不能合成一个分组；请把使用同一个 Key 的服务放在一起粘贴");
  const services = servers.map(item => ({ server_name: item.server_name, server_url: item.server_url, transport: item.transport }));
  return { ...draft, auth_type: first.auth_type, credential: first.credential, api_key_header: first.api_key_header,
    server_name: first.server_name, server_url: first.server_url, transport: first.transport,
    name: defaultGroupName(services), services, skipped };
}

export function validatePersonalMcpDraft(draft: PersonalMcpDraft, credentialSaved = false) {
  if (!draft.name.trim()) return "请填写连接名称";
  if (draft.services.length > 1) {
    if (draft.services.length > MAX_GROUP_SERVICES) return `一个 MCP 分组最多 ${MAX_GROUP_SERVICES} 个服务`;
    const bad = draft.services.find(service => !personalMcpUrl(service.server_url.trim()));
    if (bad) return `服务「${bad.server_name}」的地址须为不含账号、密码或密钥参数的 HTTPS 443 地址`;
  } else if (!personalMcpUrl(draft.server_url.trim())) return "请填写不含账号、密码或密钥参数的 HTTPS 443 MCP 地址";
  if (draft.auth_type !== "none" && !draft.credential.trim() && !credentialSaved) return "请填写 Key / Token";
  if (/\$\{|\*{3,}|^<.*>$/.test(draft.credential)) return "请填写真实 Key，不能使用占位符或脱敏值";
  if (draft.auth_type === "api_key" && !validApiKeyHeader(draft.api_key_header.trim())) return "请填写合法的 API Key 请求头名称";
  return "";
}

export function personalMcpConfiguration(draft: PersonalMcpDraft) {
  const headers: Record<string, string> = {};
  if (draft.auth_type === "bearer") headers.Authorization = draft.credential ? `Bearer ${draft.credential}` : "";
  if (draft.auth_type === "api_key") headers[draft.api_key_header.trim()] = draft.credential;
  const services = draft.services.length > 1 ? draft.services : [{ server_name: draft.server_name, server_url: draft.server_url, transport: draft.transport }];
  // 分组内每个服务带同一个认证头；服务端把重复的 Key 合成一份加密保存。
  return { "mcp.json": { mcpServers: Object.fromEntries(services.map(service => [service.server_name, { url: service.server_url.trim(), type: service.transport === "sse" ? "sse" : "streamableHttp", ...(Object.keys(headers).length ? { headers: { ...headers } } : {}) }])) } };
}
