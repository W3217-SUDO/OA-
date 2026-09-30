import { useEffect, useState } from "react";
import { Alert, Button, Descriptions, Image, Spin } from "antd";
import dayjs from "dayjs";
import { api } from "../api";
import type { FeedbackRecord } from "./types";

type Props = { feedback: FeedbackRecord; onBack: () => void };

export default function FeedbackDetail({ feedback, onBack }: Props) {
  const [imageUrl, setImageUrl] = useState("");
  const [imageError, setImageError] = useState("");
  const [loadingImage, setLoadingImage] = useState(false);

  useEffect(() => {
    setImageUrl("");
    setImageError("");
    setLoadingImage(false);
    if (!feedback.has_screenshot) return;
    const controller = new AbortController();
    let objectUrl = "";
    setLoadingImage(true);
    void api.get<Blob>(`/feedback/${feedback.id}/screenshot`, {
      responseType: "blob", signal: controller.signal,
    }).then(({ data }) => {
      if (controller.signal.aborted) return;
      objectUrl = URL.createObjectURL(data);
      setImageUrl(objectUrl);
    }).catch(async (failure: any) => {
      if (controller.signal.aborted) return;
      let detail = failure?.response?.data?.detail;
      if (failure?.response?.data instanceof Blob) {
        const text = await failure.response.data.text();
        try { detail = JSON.parse(text).detail; }
        catch { detail = text; }
      }
      if (!controller.signal.aborted) setImageError(typeof detail === "string" && detail ? detail : "截图加载失败");
    }).finally(() => {
      if (!controller.signal.aborted) setLoadingImage(false);
    });
    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [feedback.id, feedback.has_screenshot]);

  return <section aria-label="反馈详情">
      <Button onClick={onBack} style={{ marginBottom: 16 }}>返回列表</Button>
      <Descriptions bordered size="small" column={1} items={[
        { key: "serial", label: "反馈编号", children: feedback.serial_no },
        { key: "owner", label: "提交人", children: feedback.owner_display_name ? `${feedback.owner_display_name}（${feedback.owner}）` : feedback.owner },
        { key: "date", label: "提交时间", children: dayjs(feedback.created_at).format("YYYY-MM-DD HH:mm:ss") },
        { key: "page", label: "提交页面", children: <span style={{ overflowWrap: "anywhere" }}>{feedback.page}</span> },
        { key: "description", label: "问题描述", children: <div style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{feedback.description}</div> },
      ]} />
      <div style={{ marginTop: 16 }}>
        <div style={{ marginBottom: 8 }}>反馈截图</div>
        {!feedback.has_screenshot && <span>未上传截图</span>}
        {loadingImage && <Spin />}
        {imageError && <Alert type="error" showIcon title={imageError} />}
        {imageUrl && !imageError && <Image src={imageUrl} alt="用户提交的问题截图" style={{ maxWidth: "100%" }}
          onError={() => setImageError("截图无法显示，请重新打开详情重试")} />}
      </div>
  </section>;
}
