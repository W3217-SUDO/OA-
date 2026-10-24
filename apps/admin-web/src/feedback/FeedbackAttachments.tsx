import { useEffect, useState } from "react";
import { Alert, Button, Image, Spin } from "antd";
import { PaperClipOutlined } from "@ant-design/icons";
import { api } from "../api";
import type { FeedbackAttachment } from "./types";

// 附件接口需要登录头，图片先取成 Blob 再预览；非图片点击时再下载。
export default function FeedbackAttachments({ feedbackId, attachments }: { feedbackId: number; attachments: FeedbackAttachment[] }) {
  const [urls, setUrls] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const images = attachments.filter((item) => item.is_image);
  const others = attachments.filter((item) => !item.is_image);

  useEffect(() => {
    if (!images.length) return;
    const controller = new AbortController();
    const created: string[] = [];
    setLoading(true);
    setError("");
    void Promise.all(images.map((item) => api.get<Blob>(`/feedback/${feedbackId}/attachments/${item.id}`, {
      responseType: "blob", signal: controller.signal,
    }).then(({ data }) => {
      const url = URL.createObjectURL(data);
      created.push(url);
      return [item.id, url] as const;
    }))).then((entries) => {
      if (!controller.signal.aborted) setUrls(Object.fromEntries(entries));
    }).catch(() => {
      if (!controller.signal.aborted) setError("截图加载失败");
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => {
      controller.abort();
      created.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [feedbackId, attachments]);

  const download = async (item: FeedbackAttachment) => {
    try {
      const { data } = await api.get<Blob>(`/feedback/${feedbackId}/attachments/${item.id}`, { responseType: "blob" });
      const url = URL.createObjectURL(data);
      const link = document.createElement("a");
      link.href = url;
      link.download = item.name;
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      setError(`${item.name} 下载失败`);
    }
  };

  if (!attachments.length) return null;
  return <div style={{ marginTop: 16 }}>
    <div style={{ marginBottom: 8 }}>截图和附件（{attachments.length}）</div>
    {error && <Alert type="error" showIcon title={error} style={{ marginBottom: 8 }} />}
    {loading && <Spin />}
    {!!images.length && <Image.PreviewGroup>
      <div className="feedback-attachments">
        {images.map((item) => urls[item.id] && <Image key={item.id} src={urls[item.id]} alt={item.name} />)}
      </div>
    </Image.PreviewGroup>}
    {!!others.length && <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", marginTop: 8 }}>
      {others.map((item) => <Button key={item.id} type="link" size="small" icon={<PaperClipOutlined />}
        onClick={() => void download(item)}>{item.name}</Button>)}
    </div>}
  </div>;
}
