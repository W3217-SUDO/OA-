import { useEffect, useState } from "react";
import { Alert, Button, Image, Spin } from "antd";
import { api } from "../api";

export default function FeedbackEventImage({ feedbackId, eventId }: { feedbackId: number; eventId: number }) {
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    let objectUrl = "";
    setLoading(true);
    void api.get<Blob>(`/feedback/${feedbackId}/events/${eventId}/screenshot`, {
      responseType: "blob", signal: controller.signal,
    }).then(({ data }) => {
      if (controller.signal.aborted) return;
      objectUrl = URL.createObjectURL(data);
      setUrl(objectUrl);
    }).catch(() => {
      if (!controller.signal.aborted) setError("补充截图加载失败");
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [open, feedbackId, eventId]);

  if (!open) return <Button type="link" size="small" onClick={() => setOpen(true)}>查看补充截图</Button>;
  return <div style={{ marginTop: 8 }}>
    {loading && <Spin />}
    {error && <Alert type="error" showIcon title={error} />}
    {url && !error && <Image src={url} alt="反馈补充截图"
      style={{ maxWidth: 320, maxHeight: 240, objectFit: "contain" }}
      onError={() => setError("补充截图无法显示")} />}
  </div>;
}
