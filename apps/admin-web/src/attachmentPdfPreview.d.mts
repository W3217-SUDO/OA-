export type AttachmentPdfPreviewTarget = {
  readonly document: Document;
  addEventListener(type: "beforeunload", listener: () => void, options?: AddEventListenerOptions): void;
  removeEventListener?(type: "beforeunload", listener: () => void): void;
};

export const pdfPreviewBody: string;
export const pdfPreviewStyle: string;
export function renderAttachmentPdfPreview(
  target: AttachmentPdfPreviewTarget,
  blob: Blob,
  options?: { root?: HTMLElement; signal?: AbortSignal },
): Promise<void>;
