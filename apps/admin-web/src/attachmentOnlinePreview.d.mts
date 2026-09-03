import type { AxiosInstance } from "axios";

export type OnlinePreviewAttachment = {
  id: number;
  original_name?: string;
};

export type OnlinePreviewOptions = {
  openWindow?: () => Window | null;
  createObjectURL?: (blob: Blob) => string;
  revokeObjectURL?: (url: string) => void;
};

export function openAttachmentOnlinePreview(
  api: AxiosInstance,
  attachment: OnlinePreviewAttachment,
  options?: OnlinePreviewOptions,
): Promise<string>;
