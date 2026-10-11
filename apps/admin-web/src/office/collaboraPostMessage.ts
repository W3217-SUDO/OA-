import type { CollaboraMessage, LibreOfficeSession } from "./types";

function containsTokenParameter(url: URL): boolean {
  return Array.from(url.searchParams.keys()).some((name) => /^(access_token|access_token_ttl)$/i.test(name));
}

export function validateLibreOfficeSession(session: LibreOfficeSession, hostOrigin: string): void {
  if (!session.session_id || !session.access_token || !session.filename) {
    throw new Error("编辑会话配置不完整");
  }
  if (!Number.isSafeInteger(session.access_token_ttl) || session.access_token_ttl <= Date.now()) {
    throw new Error("编辑会话令牌有效期无效或已过期");
  }
  if (!/(?:Z|[+-]\d{2}:\d{2})$/.test(session.expires_at) || !Number.isFinite(Date.parse(session.expires_at))) {
    throw new Error("编辑会话有效期必须包含时区");
  }
  const editor = new URL(session.editor_url);
  if (!["http:", "https:"].includes(editor.protocol) || editor.username || editor.password || editor.hash) {
    throw new Error("编辑器地址配置无效");
  }
  if (session.editor_origin !== editor.origin || session.postmessage_origin !== hostOrigin) {
    throw new Error("编辑器通信源与服务器配置不一致");
  }
  const wopiSource = editor.searchParams.get("WOPISrc");
  if (containsTokenParameter(editor) || editor.href.includes(session.access_token)
    || (wopiSource && containsTokenParameter(new URL(wopiSource)))) {
    throw new Error("编辑器地址不得包含访问令牌");
  }
}

export function readCollaboraMessage(event: MessageEvent, frame: HTMLIFrameElement | null, origin: string): CollaboraMessage | null {
  if (!frame?.contentWindow || event.source !== frame.contentWindow || event.origin !== origin) return null;
  let value: unknown = event.data;
  if (typeof value === "string") {
    try {
      value = JSON.parse(value);
    } catch {
      throw new Error("编辑器通信数据格式无效");
    }
  }
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const message = value as Record<string, unknown>;
  if (typeof message.MessageId !== "string") return null;
  if (!["App_LoadingStatus", "UI_Close", "Action_Save_Resp", "Action_Load_Resp"].includes(message.MessageId)) return null;
  if (message.MessageId === "UI_Close" && (message.Values === undefined || message.Values === null)) {
    return { MessageId: message.MessageId, Values: message.Values };
  }
  if (!message.Values || typeof message.Values !== "object" || Array.isArray(message.Values)) {
    throw new Error("编辑器通信参数格式无效");
  }
  const values = message.Values as Record<string, unknown>;
  if (message.MessageId === "App_LoadingStatus" && (typeof values.Status !== "string" || !values.Status)) {
    throw new Error("编辑器加载状态参数格式无效");
  }
  if ((message.MessageId === "Action_Save_Resp" || message.MessageId === "Action_Load_Resp") && typeof values.success !== "boolean") {
    throw new Error("编辑器保存或加载结果参数格式无效");
  }
  return { MessageId: message.MessageId, Values: values };
}

export function postCollaboraMessage(frame: HTMLIFrameElement | null, origin: string, message: CollaboraMessage): void {
  if (!frame?.contentWindow) throw new Error("编辑器窗口尚未就绪");
  frame.contentWindow.postMessage(JSON.stringify({ ...message, SendTime: Date.now() }), origin);
}

export function prepareCollaboraHost(frame: HTMLIFrameElement | null, origin: string): void {
  postCollaboraMessage(frame, origin, { MessageId: "Host_PostmessageReady" });
  postCollaboraMessage(frame, origin, { MessageId: "Disable_Default_UIAction", Values: { action: "UI_Close", disable: true } });
}
