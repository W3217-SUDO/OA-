import type { InputHTMLAttributes,ReactNode } from "react";

/** File selection is shared; permission checks and upload requests stay with each area. */
export function AttachmentFileInput({ onFileChange, ...props }: Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "onChange"> & { onFileChange: (file: File | null) => void }) {
  return <input {...props} type="file" onChange={(event) => onFileChange(event.target.files?.[0] || null)} />;
}

export type PreviewAttachment = { name: string; kind: string; url?: string; text?: string };

/** Common image/text rendering; callers can supply an authenticated PDF page renderer. */
export function AttachmentPreviewContent({ preview, pdfContent }: { preview: PreviewAttachment | null; pdfContent?: ReactNode }) {
  return <>
    {preview?.kind === "image" && <img src={preview.url} alt={preview.name} style={{ display: "block", maxWidth: "100%", maxHeight: "72vh", margin: "0 auto" }} />}
    {preview?.kind === "pdf" && (pdfContent ?? <iframe title={preview.name} src={preview.url} style={{ width: "100%", height: "72vh", border: 0 }} />)}
    {(preview?.kind === "text" || preview?.kind === "docx") && <pre style={{ maxHeight: "70vh", overflow: "auto", margin: 0, whiteSpace: "pre-wrap", overflowWrap: "anywhere", fontFamily: "inherit", lineHeight: 1.7 }}>{preview.text}</pre>}
  </>;
}
