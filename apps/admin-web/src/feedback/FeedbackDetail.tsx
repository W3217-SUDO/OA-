import { useCallback, useEffect, useState } from "react";
import { Alert, Button, Descriptions, Input, message, Space, Spin, Tag, Timeline } from "antd";
import dayjs from "dayjs";
import { api } from "../api";
import type { FeedbackDetails } from "./types";
import FeedbackEventImage from "./FeedbackEventImage";
import FeedbackFileDrop from "./FeedbackFileDrop";
import { feedbackErrorText, uploadFeedbackFiles } from "./upload";
import FeedbackAttachments from "./FeedbackAttachments";
import "./feedback.css";

type Props = { feedbackId: number; onBack: () => void; onNavigate: (route: string) => void };

const requiresComment = new Set(["未解决，重新打开"]);
const primaryActions = new Set(["处理完成，请验证", "验证通过"]);
const statusColors: Record<string, string> = {
  待处理: "warning", 待验证: "processing", 已解决: "success",
};

export default function FeedbackDetail({ feedbackId, onBack, onNavigate }: Props) {
  const [feedback, setFeedback] = useState<FeedbackDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [comment, setComment] = useState("");
  const [files, setFiles] = useState<File[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get<FeedbackDetails>(`/feedback/${feedbackId}`);
      setFeedback(data);
    } catch (failure: any) {
      setError(failure?.response?.data?.detail || "反馈详情加载失败");
    } finally {
      setLoading(false);
    }
  }, [feedbackId]);

  useEffect(() => { void load(); }, [load]);

  // 回复带的截图和附件走回复接口；点状态按钮时如果已经选了文件，先作为一条回复发出，再改状态。
  // 回复文字走 JSON，截图和附件再逐个上传到这条回复（见 upload.ts）；返回没传上去的文件名。
  const sendFiles = async (content: string) => {
    const { data } = await api.post(`/feedback/${feedbackId}/replies`, { content, file_count: files.length });
    return uploadFeedbackFiles(feedbackId, files, data.event_id);
  };
  const perform = async (path: "messages" | "transitions", body: object | null, success: string) => {
    setBusy(true);
    try {
      let failed: string[] = [];
      if (path === "messages") failed = await sendFiles(comment.trim());
      else {
        if (files.length) failed = await sendFiles(comment.trim());
        await api.post(`/feedback/${feedbackId}/transitions`, files.length ? { ...body, comment: "" } : body);
      }
      if (failed.length) message.warning(`${success}，但 ${failed.join("、")} 没有传上去，请重新添加后再发一次`, 6);
      else message.success(success);
      setComment("");
      setFiles([]);
      await load();
      window.dispatchEvent(new Event("sunhold:notifications-updated"));
    } catch (failure: any) {
      message.error(feedbackErrorText(failure, "操作失败"));
      if (failure?.response?.status === 409) await load();
    } finally {
      setBusy(false);
    }
  };

  const reply = () => {
    if (!comment.trim() && !files.length) { message.warning("请填写回复内容或添加截图、附件"); return; }
    void perform("messages", null, "回复已发送");
  };
  const transition = (action: string) => {
    if (requiresComment.has(action) && !comment.trim()) {
      message.warning("请在上面写明哪里还没解决");
      return;
    }
    void perform("transitions", { action, comment: comment.trim() }, "状态已更新");
  };

  if (loading && !feedback) return <Spin />;
  if (error && !feedback) return <Alert type="error" showIcon title={error} action={<Button onClick={onBack}>返回列表</Button>} />;
  if (!feedback) return null;

  return <section aria-label="反馈详情">
    <Space wrap style={{ marginBottom: 16 }}>
      <Button onClick={onBack}>返回列表</Button>
      <Button onClick={() => void load()} loading={loading}>刷新</Button>
      <Tag color={statusColors[feedback.status] || "default"}>{feedback.status}</Tag>
    </Space>
    {error && <Alert type="error" showIcon title={error} style={{ marginBottom: 16 }} />}
    <Descriptions bordered size="small" column={{ xs: 1, sm: 2, md: 2 }} items={[
      { key: "serial", label: "反馈编号", children: feedback.serial_no },
      { key: "owner", label: "提交人", children: feedback.owner_display_name || feedback.owner },
      { key: "date", label: "提交时间", children: dayjs(feedback.created_at).format("YYYY-MM-DD HH:mm:ss") },
      { key: "page", label: "问题页面", span: 2, children: <Space wrap size={4}>
        <span style={{ overflowWrap: "anywhere" }}>{feedback.page || "—"}</span>
        {feedback.route && <Button type="link" size="small" onClick={() => onNavigate(feedback.route)}>前往该页面</Button>}
      </Space> },
      ...(feedback.controls?.length ? [{ key: "controls", label: "涉及按钮", span: 2,
        children: <Space wrap size={4}>{feedback.controls.map((name) => <Tag key={name}>{name}</Tag>)}</Space> }] : []),
      { key: "description", label: "问题描述", span: 2,
        children: <div style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{feedback.description}</div> },
    ]} />
    <FeedbackAttachments feedbackId={feedbackId} attachments={feedback.attachments || []} />
    <h3 style={{ marginTop: 24, marginBottom: 16 }}>处理记录</h3>
    <Timeline items={feedback.events.map((event) => ({
      key: event.id,
      children: <div>
        <Space wrap size={8}>
          <strong>{event.action}</strong>
          <span>{event.operator_display_name || event.operator}</span>
          {event.from_status !== event.to_status && <Tag color={statusColors[event.to_status] || "default"}>{event.to_status}</Tag>}
          <span style={{ color: "var(--oa-text-2)" }}>{dayjs(event.created_at).format("YYYY-MM-DD HH:mm:ss")}</span>
        </Space>
        {event.comment && <div style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere", marginTop: 4 }}>{event.comment}</div>}
        {event.attachments?.length
          ? <FeedbackAttachments feedbackId={feedbackId} attachments={event.attachments} compact />
          : event.has_screenshot && <FeedbackEventImage feedbackId={feedbackId} eventId={event.id} />}
      </div>,
    }))} />
    {feedback.available_actions.includes("验证通过") && <Alert type="info" showIcon style={{ maxWidth: 850, marginBottom: 12 }}
      title="已处理完成，请验证问题是否已解决：解决了点“验证通过”，没解决写明情况后点“未解决，重新打开”。" />}
    {feedback.available_actions.includes("处理完成，请验证") && <Alert type="info" showIcon style={{ maxWidth: 850, marginBottom: 12 }}
      title="处理完成后点“处理完成，请验证”，会通知提交人验证；可以先在下面写处理说明。" />}
    <Input.TextArea value={comment} rows={4} aria-label="回复或处理说明"
      placeholder="回复或填写处理说明（随状态操作一起提交）" onChange={(event) => setComment(event.target.value)}
      style={{ maxWidth: 850, marginBottom: 12 }} />
    <div style={{ maxWidth: 850, marginBottom: 12 }}>
      <FeedbackFileDrop files={files} onChange={setFiles} compact disabled={busy} />
    </div>
    <div><Space wrap>
      {feedback.available_actions.map((action) => <Button key={action}
        type={primaryActions.has(action) ? "primary" : "default"} danger={action === "未解决，重新打开"} disabled={busy}
        onClick={() => transition(action)}>{action}</Button>)}
      <Button disabled={busy || (!comment.trim() && !files.length)} loading={busy} onClick={reply}>发送回复</Button>
    </Space></div>
  </section>;
}
