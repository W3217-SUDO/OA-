import { POPUP_WIDTH } from "../components/common/popupSize";
import { useEffect, useRef, useState } from "react";
import { Alert, Button, Modal, Spin } from "antd";
import { DownloadOutlined, EditOutlined } from "@ant-design/icons";
import { api } from "../api";
import { AttachmentPreviewContent, type PreviewAttachment } from "../components/common/AttachmentContent";
import { personalAiFilePreviewKind, type PersonalAiFile } from "./personalAiSpaceApi";
import { errorText } from "./types";
import { PersonalAiFileShare } from "./PersonalAiFileShare";

type Props = {
  file: PersonalAiFile;
  blob?: Blob;
  downloading: boolean;
  downloadError: string;
  onClose: () => void;
  onDownload: () => void;
  onEdit: () => void;
};

function PersonalAiPdfContent({ blob }: { blob: Blob }) {
  const host = useRef<HTMLDivElement>(null);
  const [rendering, setRendering] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    const container = host.current!;
    setRendering(true); setError("");
    void (async () => {
      const renderer = await import("../attachmentPdfPreview.mjs");
      if (controller.signal.aborted) return;
      // 仅挂载项目已有的静态画布模板，不向原生 PDF 查看器传入文件地址。
      container.innerHTML = renderer.pdfPreviewBody;
      const style = container.ownerDocument.createElement("style");
      style.textContent = renderer.pdfPreviewStyle;
      container.prepend(style);
      await renderer.renderAttachmentPdfPreview(window, blob, {
        root: container.querySelector<HTMLElement>(".pdf-preview")!, signal: controller.signal,
      });
    })().catch((failure) => {
      if (!controller.signal.aborted) setError(errorText(failure, "PDF 页面渲染失败"));
    }).finally(() => { if (!controller.signal.aborted) setRendering(false); });
    return () => controller.abort();
  }, [blob]);
  return <>
    {error && <Alert type="error" showIcon title="PDF 页面渲染失败" description={error} />}
    <Spin spinning={rendering}><div ref={host} className="personal-ai-pdf-content" /></Spin>
  </>;
}

export function PersonalAiFilePreview({ file, blob, downloading, downloadError, onClose, onDownload, onEdit }: Props) {
  const [preview, setPreview] = useState<(PreviewAttachment & { blob: Blob }) | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    let objectUrl = "";
    setLoading(true); setError(""); setPreview(null);
    void (async () => {
      try {
        const kind = personalAiFilePreviewKind(file.name);
        if (!kind) throw new Error("当前文件格式不支持在线查看，请下载后查看");
        const content = blob ?? (await api.get<Blob>(`/personal-agent/ai-space/files/${encodeURIComponent(file.id)}/download`, {
          responseType: "blob", signal: controller.signal,
        })).data;
        const value: PreviewAttachment & { blob: Blob } = { name: file.name, kind, blob: content };
        if (kind === "text") value.text = await content.text();
        if (controller.signal.aborted) return;
        if (kind === "image") { objectUrl = URL.createObjectURL(content); value.url = objectUrl; }
        setPreview(value);
      } catch (failure) { if (!controller.signal.aborted) setError(errorText(failure, "文件在线查看加载失败")); }
      finally { if (!controller.signal.aborted) setLoading(false); }
    })();
    return () => { controller.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [file.id, file.name, blob]);
  return <Modal open title={`在线查看：${file.name}`} width={POPUP_WIDTH.lg}
    rootClassName="personal-ai-file-preview" onCancel={onClose} destroyOnHidden footer={<>
      <Button onClick={onClose}>关闭</Button>
      {/\.(docx|xlsx|xls|md|txt)$/i.test(file.name) && <Button icon={<EditOutlined />} disabled={loading || downloading} onClick={onEdit}>编辑并保存</Button>}
      <Button type="primary" icon={<DownloadOutlined />} loading={downloading} onClick={onDownload}>下载到本地</Button>
      <PersonalAiFileShare file={file} disabled={loading || downloading} />
    </>}>
    {error && <Alert type="error" showIcon title="文件查看未完成" description={error} />}
    {downloadError && <Alert type="error" showIcon title="文件下载未完成" description={downloadError} />}
    <Spin spinning={loading}><div className="personal-ai-file-preview-content"><AttachmentPreviewContent preview={preview}
      pdfContent={preview?.kind === "pdf" ? <PersonalAiPdfContent blob={preview.blob} /> : undefined} /></div></Spin>
  </Modal>;
}
