import axios from "axios";
import { api } from "../api";
import type { LibreOfficeEditorTarget, LibreOfficeSession, LibreOfficeSessionStatus } from "./types";

function sessionPath(target: LibreOfficeEditorTarget): string {
  return `/cases/${target.caseId}/attachments/${target.attachmentId}/libreoffice`;
}

export async function createLibreOfficeSession(target: LibreOfficeEditorTarget): Promise<LibreOfficeSession> {
  return (await api.post<LibreOfficeSession>(`${sessionPath(target)}/session`, {})).data;
}

export async function getLibreOfficeSession(target: LibreOfficeEditorTarget, sessionId: string): Promise<LibreOfficeSessionStatus> {
  return (await api.get<LibreOfficeSessionStatus>(`${sessionPath(target)}/sessions/${encodeURIComponent(sessionId)}`)).data;
}

export async function closeLibreOfficeSession(target: LibreOfficeEditorTarget, sessionId: string): Promise<LibreOfficeSessionStatus> {
  return (await api.post<LibreOfficeSessionStatus>(`${sessionPath(target)}/sessions/${encodeURIComponent(sessionId)}/close`, {})).data;
}

export function libreOfficeError(error: unknown, operation: string): string {
  if (axios.isAxiosError(error)) {
    const detail: unknown = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail === "object" && "message" in detail && typeof detail.message === "string") return detail.message;
    return `${operation}失败${error.response ? `（HTTP ${error.response.status}）` : "，服务器未响应"}`;
  }
  return error instanceof Error ? error.message : `${operation}失败`;
}
