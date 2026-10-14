export type ConnectorConfiguration = Record<string, any>;
export type ConnectorSecretField = { path: string[]; label: string; configured: boolean; template: string };
export type ServerAuth = { mode: "none" | "bearer" | "apiKey" | "existing"; headerName: string };

const AUTH_HEADER = /^(authorization|(?:x-)?api[-_]?key|(?:x-)?(?:auth|access)[-_]?token)$/i;
const HEADER_NAME = /^[!#$%&'*+.^_`|~0-9A-Za-z-]+$/;
const BLOCKED_HEADERS = new Set(["host", "content-length", "connection", "proxy-authorization"]);

export function validApiKeyHeader(name: string) {
  return HEADER_NAME.test(name) && !BLOCKED_HEADERS.has(name.toLowerCase()) && name.toLowerCase() !== "authorization";
}

export function safePublicUrl(value: string) {
  if (!/^https?:\/\//i.test(value) || value.length > 2048 || /[\s\x00-\x1f\x7f]/.test(value) || value.includes("${")) return null;
  try {
    const url = new URL(value);
    if (!url.hostname || url.username || url.password || value.slice(value.indexOf("://") + 3).split(/[/?#]/, 1)[0].includes("@")) return null;
    if ([...url.searchParams.keys()].some(key => /token|secret|password|api[-_]?key|authorization/i.test(key))) return null;
    return value;
  } catch { return null; }
}

export function inferServerAuth(server: ConnectorConfiguration, fields: ConnectorSecretField[], serverName: string): ServerAuth {
  const headers = Object.keys(server.headers || {});
  if (!headers.length) return { mode: "none", headerName: "" };
  const authHeaders = headers.filter(key => AUTH_HEADER.test(key));
  if (authHeaders.length === 1) {
    const headerName = authHeaders[0];
    const field = fields.find(field => field.path.length === 5 && field.path[2] === serverName && field.path[3] === "headers" && field.path[4] === headerName);
    const value = server.headers[headerName] || field?.template || "";
    if (headerName.toLowerCase() === "authorization") {
      if (/^Bearer\s/i.test(value)) return { mode: "bearer", headerName };
    } else if (/api[-_]?key/i.test(headerName)) return { mode: "apiKey", headerName };
  }
  return { mode: "existing", headerName: "" };
}

export function changeServerAuth(server: ConnectorConfiguration, previous: ServerAuth, mode: ServerAuth["mode"]) {
  const next = structuredClone(server);
  const headers = { ...next.headers };
  const removed = Object.keys(headers).filter(key => AUTH_HEADER.test(key) || (previous.mode !== "existing" && key === previous.headerName));
  for (const key of removed) delete headers[key];
  const auth: ServerAuth = { mode, headerName: mode === "bearer" ? "Authorization" : mode === "apiKey" ? "X-API-Key" : "" };
  if (auth.headerName) {
    headers[auth.headerName] = "";
  }
  if (Object.keys(headers).length) next.headers = headers;
  else delete next.headers;
  return { server: next, auth, removed };
}

export function editableSecretFields(configuration: ConnectorConfiguration | null, saved: ConnectorSecretField[]) {
  const fields: ConnectorSecretField[] = [];
  for (const [serverName, server] of Object.entries<ConnectorConfiguration>(configuration?.["mcp.json"]?.mcpServers || {})) {
    for (const group of ["headers", "env"]) {
      if (!server[group] || typeof server[group] !== "object" || Array.isArray(server[group])) continue;
      for (const key of Object.keys(server[group])) {
        const path = ["mcp.json", "mcpServers", serverName, group, key];
        fields.push(saved.find(field => JSON.stringify(field.path) === JSON.stringify(path)) || { path, label: serverName + " · " + key, configured: false, template: "" });
      }
    }
  }
  return fields;
}
