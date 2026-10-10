import { api } from "../api";
import type { OfficeEditorSession, OfficeEditorTarget, OfficeSessionStatus } from "./types";

const sessionPath = (target: OfficeEditorTarget, sessionId?: string) => {
  const path = `/cases/${target.caseId}/attachments/${target.attachmentId}/office-editor/session`;
  return sessionId ? `${path}/${encodeURIComponent(sessionId)}` : path;
};

export async function createOfficeSession(target: OfficeEditorTarget): Promise<OfficeEditorSession> {
  const { data } = await api.post<OfficeEditorSession>(sessionPath(target), {});
  return data;
}

export async function getOfficeSession(target: OfficeEditorTarget, sessionId: string): Promise<OfficeSessionStatus> {
  const { data } = await api.get<OfficeSessionStatus>(sessionPath(target, sessionId));
  return data;
}

export async function renewOfficeSession(target: OfficeEditorTarget, sessionId: string): Promise<OfficeSessionStatus> {
  const { data } = await api.post<OfficeSessionStatus>(`${sessionPath(target, sessionId)}/renew`, {});
  return data;
}

export async function closeOfficeSession(target: OfficeEditorTarget, sessionId: string): Promise<OfficeSessionStatus> {
  const { data } = await api.post<OfficeSessionStatus>(`${sessionPath(target, sessionId)}/close`, {});
  return data;
}

export function officeErrorMessage(error: unknown): string {
  const requestError = error as { response?: { data?: { detail?: unknown } }; message?: string };
  const detail = requestError?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && "message" in detail && typeof detail.message === "string") return detail.message;
  return requestError?.message || "Office 会话请求失败";
}
