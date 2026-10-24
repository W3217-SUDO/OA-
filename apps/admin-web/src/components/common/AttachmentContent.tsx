import { useEffect, useRef, useState, type InputHTMLAttributes, ReactNode } from "react";
import { Tabs } from "antd";
import { renderAsync as renderDocxAsync } from "docx-preview";
import * as XLSX from "xlsx";

/** File selection is shared; permission checks and upload requests stay with each area. */
export function AttachmentFileInput({ onFileChange, ...props }: Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "onChange"> & { onFileChange: (file: File | null) => void }) {
  return <input {...props} type="file" onChange={(event) => onFileChange(event.target.files?.[0] || null)} />;
}

export type PreviewAttachment = { name: string; kind: string; url?: string; text?: string; blob?: Blob };

const docxPreviewStyle: React.CSSProperties = {
  maxHeight: "70vh",
  overflow: "auto",
  padding: "16px",
  background: "var(--oa-fill)",
  border: "1px solid var(--oa-border)",
};

function DocxPreview({ attachment }: { attachment: PreviewAttachment & { blob?: Blob; url?: string; text?: string } }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function render() {
      setLoading(true);
      setError("");
      const container = containerRef.current;
      container?.replaceChildren();
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
        if (cancelled || !container) return;
        await renderDocxAsync(arrayBuffer, container, container, {
          breakPages: true,
          ignoreWidth: false,
          ignoreHeight: false,
          ignoreFonts: false,
          renderHeaders: true,
          renderFooters: true,
          renderFootnotes: true,
          renderEndnotes: true,
          useBase64URL: true,
        });
        if (cancelled) container.replaceChildren();
      } catch (e: any) {
        if (!cancelled) {
          setError(e.message || "渲染失败");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    render();
    return () => {
      cancelled = true;
      containerRef.current?.replaceChildren();
    };
  }, [attachment.url, attachment.blob]);

  return (
    <div style={docxPreviewStyle}>
      {loading && <div style={{ padding: 24, textAlign: "center", color: "var(--oa-text-3)" }}>正在还原 Word 模板版式...</div>}
      {error && <>
      <div style={{ ...docxPreviewStyle, background: "color-mix(in srgb, #fff7e8 var(--oa-tint), var(--oa-surface))", borderColor: "color-mix(in srgb, #ffd591 var(--oa-tint), var(--oa-surface))", color: "var(--oa-warning)", marginBottom: 12 }}>
        Word 模板版式渲染失败：{error}。以下为纯文本内容，请通过下载查看原文件：
      </div>
      <pre style={{ maxHeight: "60vh", overflow: "auto", margin: 0, whiteSpace: "pre-wrap", overflowWrap: "anywhere", fontFamily: "inherit", lineHeight: 1.7, padding: "16px", background: "var(--oa-surface)", border: "1px solid var(--oa-border)" }}>{attachment.text}</pre>
      </>}
      <div ref={containerRef} style={{ display: error ? "none" : undefined }} />
    </div>
  );
}

function XlsxPreview({ attachment }: { attachment: PreviewAttachment & { blob?: Blob; url?: string; text?: string } }) {
  const [sheets, setSheets] = useState<{ name: string; html: string }[]>([]);
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
        const workbook = XLSX.read(arrayBuffer, { type: "array" });
        const sheetNames = workbook.SheetNames;
        const sheetData = sheetNames.map((name) => {
          const sheet = workbook.Sheets[name];
          const html = XLSX.utils.sheet_to_html(sheet, { editable: false });
          return { name, html };
        });
        if (!cancelled) {
          setSheets(sheetData);
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

  if (loading) return <div style={{ padding: 40, textAlign: "center", color: "var(--oa-text-3)" }}>正在渲染 Excel 表格...</div>;
  if (error) return (
    <div>
      <div style={{ padding: "16px 20px", background: "color-mix(in srgb, #fff7e8 var(--oa-tint), var(--oa-surface))", border: "1px solid color-mix(in srgb, #ffd591 var(--oa-tint), var(--oa-surface))", color: "var(--oa-warning)", borderRadius: 4, marginBottom: 12 }}>
        渲染 Excel 表格失败：{error}，以下为纯文本预览：
      </div>
      <pre style={{ maxHeight: "60vh", overflow: "auto", margin: 0, whiteSpace: "pre-wrap", overflowWrap: "anywhere", fontFamily: "inherit", lineHeight: 1.7, padding: "16px", background: "var(--oa-surface)", border: "1px solid var(--oa-border)" }}>{attachment.text}</pre>
    </div>
  );

  if (!sheets.length) {
    return <div style={{ padding: 40, textAlign: "center", color: "var(--oa-text-3)" }}>（该 Excel 文件没有可显示的工作表）</div>;
  }

  const tabItems = sheets.map((sheet, idx) => ({
    key: String(idx),
    label: sheet.name,
    children: (
      <div style={{ overflow: "auto", maxHeight: "62vh", border: "1px solid var(--oa-border)", borderTop: 0 }}>
        <div
          dangerouslySetInnerHTML={{ __html: sheet.html.replace(/<table/, '<table style="border-collapse:collapse;width:100%;font-size:12px"') }}
          style={{ padding: 0 }}
        />
      </div>
    ),
  }));

  return (
    <Tabs
      items={tabItems}
      defaultActiveKey="0"
      size="small"
      style={{ background: "var(--oa-surface)" }}
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
    {preview?.kind === "xlsx" && <XlsxPreview attachment={preview} />}
  </>;
}
