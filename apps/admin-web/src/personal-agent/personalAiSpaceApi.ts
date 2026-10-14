import { api } from "../api";

export type PersonalAiSpaceInfo = {
  owner_user_id: number;
  owner_name: string;
  employee_record_id: number | null;
  folder: string;
  storage_backend: "oss";
  configured: boolean;
};

export type PersonalAiFile = {
  id: string;
  attachment_id: number | null;
  name: string;
  content_type: string;
  size: number;
  sha256: string;
  status: "uploading" | "available" | "failed" | "uncertain" | "deleting" | "delete_failed" | "delete_uncertain";
  storage_backend: "oss";
  owner_user_id: number;
  owner_name: string;
  source_kind: string;
  conversation_id: string | null;
  source_request_id: string | null;
  case_id: number | null;
  created_at: string;
  download_url: string | null;
  error: string | null;
  supersedes?: string | null;
  can_delete: boolean;
};

export type PersonalAiFilePage = { items: PersonalAiFile[]; total: number; page: number; page_size: number };
export type PersonalAiDocument = { id: string; name: string; content: string };
export type PersonalAiFileEditResult = { file: PersonalAiFile; supersedes: string };
export type PersonalAiFileDeleteResult = { id: string; status: "deleted"; blob_status: "retained" };
export type PersonalAiDocumentRequest = { conversation_id: string; message_index: number; name: string; expected_content_sha256: string; format?: "word" | "xlsx" };

export async function personalAiMessageSha256(content: string): Promise<string> {
  if (!globalThis.crypto?.subtle) throw new Error("当前连接不支持安全摘要计算，请使用 HTTPS 或本机安全连接");
  const digest = await globalThis.crypto.subtle.digest("SHA-256", new TextEncoder().encode(content));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export async function downloadPersonalAiFile(file: PersonalAiFile): Promise<void> {
  const { data: current } = await api.get<PersonalAiFile>(`/personal-agent/ai-space/files/${encodeURIComponent(file.id)}`);
  if (current.id !== file.id || current.status !== "available" || !current.download_url) throw new Error("文件尚未可用，不能下载，请刷新核对保存状态");
  const { data } = await api.get<Blob>(`/personal-agent/ai-space/files/${encodeURIComponent(file.id)}/download`, { responseType: "blob" });
  const url = URL.createObjectURL(data);
  try {
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = current.name.replace(/[\\/:*?"<>|\u0000-\u001f]/g, "_");
    anchor.click();
  } finally {
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
}
