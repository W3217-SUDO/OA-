import { useEffect, useState, type InputHTMLAttributes, ReactNode } from "react";
import mammoth from "mammoth";

/** File selection is shared; permission checks and upload requests stay with each area. */
export function AttachmentFileInput({ onFileChange, ...props }: Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "onChange"> & { onFileChange: (file: File | null) => void }) {
  return <input {...props} type="file" onChange={(event) => onFileChange(event.target.files?.[0] || null)} />;
}

export type PreviewAttachment = { name: string; kind: string; url?: string; text?: string; blob?: Blob };

const docxPreviewStyle: React.CSSProperties = {
  maxWidth: "900px",
  margin: "0 auto",
  padding: "32px 40px",
  background: "#fff",
  border: "1px solid #dfe2e7",
  lineHeight: 1.8,
  fontSize: 14,
  color: "#1f2329",
  maxHeight: "70vh",
  overflow: "auto",
};

function DocxPreview({ attachment }: { attachment: PreviewAttachment & { blob?: Blob; url?: string; text?: string } }) {
  const [html, setHtml] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function render() {
      setLoading(true);
      setError("");
      try {
        let blob: Blob | undefined = attachment.blob;
        if (!blob && attachment.url) {
          const resp = await fetch(attachment.url);
          blob = await resp.blob();
        }
        if (!blob) {
          throw new Error("没有可渲染的文件数据");
        }
        const arrayBuffer = await blob.arrayBuffer();
        const result = await mammoth.convertToHtml({ arrayBuffer });
        if (!cancelled) {
          setHtml(result.value);
        }
      } catch (e: any) {
        if (!cancelled) {
          setError(e.message || "渲染失败");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    render();
    return () => { cancelled = true; };
  }, [attachment.url, attachment.blob]);

  if (loading) return <div style={docxPreviewStyle}>正在渲染 Word 文档...</div>;
  if (error) return (
    <div>
      <div style={{ ...docxPreviewStyle, background: "#fff7e8", borderColor: "#ffd591", color: "#d46b08", marginBottom: 12 }}>
        渲染 Word 排版失败：{error}，以下为纯文本预览：
      </div>
      <pre style={{ maxHeight: "60vh", overflow: "auto", margin: 0, whiteSpace: "pre-wrap", overflowWrap: "anywhere", fontFamily: "inherit", lineHeight: 1.7, padding: "16px", background: "#fff", border: "1px solid #dfe2e7" }}>{attachment.text}</pre>
    </div>
  );

  return (
    <div
      style={docxPreviewStyle}
      className="docx-preview"
      dangerouslySetInnerHTML={{ __html: html || '<p style="color:#86909c">（文件没有可显示的内容）</p>' }}
    />
  );
}

/** Common image/text rendering; callers can supply an authenticated PDF page renderer. */
export function AttachmentPreviewContent({ preview, pdfContent }: { preview: PreviewAttachment | null; pdfContent?: ReactNode }) {
  return <>
    {preview?.kind === "image" && <img src={preview.url} alt={preview.name} style={{ display: "block", maxWidth: "100%", maxHeight: "72vh", margin: "0 auto" }} />}
    {preview?.kind === "pdf" && (pdfContent ?? <iframe title={preview.name} src={preview.url} style={{ width: "100%", height: "72vh", border: 0 }} />)}
    {preview?.kind === "text" && <pre style={{ maxHeight: "70vh", overflow: "auto", margin: 0, whiteSpace: "pre-wrap", overflowWrap: "anywhere", fontFamily: "inherit", lineHeight: 1.7 }}>{preview.text}</pre>}
    {preview?.kind === "docx" && <DocxPreview attachment={preview} />}
  </>;
}
