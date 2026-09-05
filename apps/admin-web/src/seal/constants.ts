import type { SealRow, SealPreviewMode } from "./types";

export const personDisplayName = (value?: unknown) =>
  String(value || "").trim() || "姓名待维护";

export function getSealPreviewMode(payload: { kind?: string }): SealPreviewMode {
  if (payload.kind === "image" || payload.kind === "pdf") return "binary";
  if (payload.kind === "docx" || payload.kind === "text") return "text";
  return "unsupported";
}

export const sealUploadExtensions = new Set([
  ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
  ".txt", ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".zip", ".rar",
  ".ini", ".conf", ".eml",
]);

export function validateSealUploadFile(file: File | undefined): string | null {
  if (!file || !file.name || file.size <= 0) return "请选择上传文件.";
  const suffix = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  if (!sealUploadExtensions.has(suffix)) return "不支持的文件格式";
  if (file.size > 20 * 1024 * 1024) return "单个文件不能超过 20MB";
  return null;
}

export function sealActionFailureMessage(type: "approve" | "reject" | "stamp" | "archive"): string {
  return {
    approve: "审批失败",
    reject: "审批失败",
    stamp: "登记实际用印失败",
    archive: "归档失败",
  }[type];
}

export function sealAttachmentDeleteFailureMessage(status?: number): string {
  if (status === 403) return "当前账号无权删除该用印文件";
  if (status === 409) return "仅草稿用印申请可以删除文件";
  return "用印文件删除失败";
}

export function sealPackageDownloadFailureMessage(status?: number): string {
  if (status === 403) return "当前账号无权下载所选用印附件";
  if (status === 404) return "所选用印申请暂无可下载附件";
  return "打包下载失败";
}

export function sealAttachmentDownloadFailureMessage(status?: number): string {
  if (status === 403) return "当前账号无权下载该用印文件";
  if (status === 404) return "附件不存在或文件实体不存在";
  if (status === 409) return "当前状态不允许下载该用印文件";
  return "用印文件下载失败";
}

export function sealAttachmentPreviewFailureMessage(status?: number): string {
  if (status === 403) return "当前账号无权预览该用印文件";
  if (status === 404) return "附件不存在或文件实体不存在";
  if (status === 409) return "当前状态不允许预览该用印文件";
  return "文件预览失败";
}

export const statusColors: Record<string, string> = {
  草稿: "default",
  待审批: "orange",
  待用印: "blue",
  已用印: "green",
  已归档: "cyan",
  已拒绝: "red",
  已撤回: "default",
};

export const sealStatusOptions = [
  { value: "待审批", label: "待审核" },
  { value: "待用印", label: "已审待用印" },
  { value: "已拒绝", label: "审核拒绝" },
  { value: "已撤回", label: "已撤回" },
  { value: "已用印", label: "已用印" },
  { value: "已归档", label: "已归档" },
];

export const assetColors: Record<string, string> = {
  可用: "green",
  停用: "default",
  维修: "orange",
  遗失: "red",
};

export const sealTypes = [
  "合同章",
  "公章",
  "所函专用章",
  "法人章",
  "发票章",
  "财务专用章",
  "财务三排章",
];

export const SEAL_APPLICATION_FILE_CATEGORY = "用印文件";
export const SEAL_STAMPED_FILE_CATEGORY = "盖章文件";

export const sealAttachmentLabel = (category?: string) =>
  category === SEAL_STAMPED_FILE_CATEGORY ? SEAL_STAMPED_FILE_CATEGORY : SEAL_APPLICATION_FILE_CATEGORY;

export const sealAttachmentListLabel = "用印附件";

export const listSealRowFileNames = (row: SealRow): string[] => {
  const names: string[] = [];
  const append = (value: unknown) => {
    if (!value) return;
    if (Array.isArray(value)) {
      value.forEach(append);
      return;
    }
    if (typeof value === "object") {
      const item = value as Record<string, unknown>;
      append(item.original_name || item.file_name || item.FileName || item.name);
      return;
    }
    String(value)
      .split(/[\n\r,;；、|]+/)
      .map((name) => name.trim())
      .filter(Boolean)
      .forEach((name) => names.push(name));
  };

  append(row.data.file_names);
  append(row.data.fileNames);
  append(row.application_file_names);
  append(row.stamped_file_names);
  append(row.data.application_file_names);
  append(row.data.stamped_file_names);
  append(row.data.attachments);
  append(row.data.files);
  append(row.data.document_names);
  append(row.data.documentNames);

  return Array.from(new Set(names)).slice(0, 5);
};

export const displayStatus = (status: string): string => {
  const found = sealStatusOptions.find((item) => item.value === status);
  return found ? found.label : status;
};
