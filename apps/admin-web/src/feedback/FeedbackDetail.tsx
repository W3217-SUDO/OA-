import { KeywordPersonSelect } from "../components/KeywordPersonSelect";
import { useCallback, useEffect, useRef, useState } from "react";
import { Alert, Button, Descriptions, Input, message, Space, Spin, Tag, Timeline } from "antd";
import dayjs from "dayjs";
import { api } from "../api";
import type { FeedbackDetails } from "./types";
import FeedbackEventImage from "./FeedbackEventImage";
import FeedbackAttachments from "./FeedbackAttachments";
import "./feedback.css";

type Props = { feedbackId: number; onBack: () => void; onNavigate: (route: string) => void };
type PersonOption = { username: string; label: string };

const requiresComment = new Set(["请求补充", "提交修复", "重新打开"]);
const statusColors: Record<string, string> = {
  待处理: "default", 处理中: "processing", 待补充: "warning", 待验证: "cyan", 已处理: "green", 已解决: "success",
};

export default function FeedbackDetail({ feedbackId, onBack, onNavigate }: Props) {
  const [feedback, setFeedback] = useState<FeedbackDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [comment, setComment] = useState("");
  const [screenshot, setScreenshot] = useState<File | null>(null);
  const screenshotInput = useRef<HTMLInputElement>(null);
  const [people, setPeople] = useState<PersonOption[]>([]);
  const [assignee, setAssignee] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get<FeedbackDetails>(`/feedback/${feedbackId}`);
      setFeedback(data);
      setAssignee(data.assignee);
    } catch (failure: any) {
      setError(failure?.response?.data?.detail || "反馈详情加载失败");
    } finally {
      setLoading(false);
    }
  }, [feedbackId]);

  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    if (!feedback?.can_assign) return;
    let cancelled = false;
    void api.get<{ items: PersonOption[] }>("/people/options").then(({ data }) => {
      if (!cancelled) setPeople(data.items);
    }).catch(() => {
      if (!cancelled) message.error("处理人列表加载失败");
    });
    return () => { cancelled = true; };
  }, [feedback?.can_assign]);

  const perform = async (path: string, body: object, success: string, method: "post" | "put" = "post") => {
    setBusy(true);
    try {
      await api[method](`/feedback/${feedbackId}/${path}`, body);
      message.success(success);
      setComment("");
      if (path === "messages") {
        setScreenshot(null);
        if (screenshotInput.current) screenshotInput.current.value = "";
      }
      await load();
      window.dispatchEvent(new Event("sunhold:notifications-updated"));
    } catch (failure: any) {
      message.error(failure?.response?.data?.detail || "操作失败");
      if (failure?.response?.status === 409) await load();
    } finally {
      setBusy(false);
    }
  };

  const reply = () => {
    if (!comment.trim()) { message.warning("请填写回复内容"); return; }
    const body = new FormData();
    body.append("content", comment.trim());
    if (screenshot) body.append("screenshot", screenshot);
    void perform("messages", body, "回复已发送");
  };
  const transition = (action: string) => {
    if (requiresComment.has(action) && comment.trim().length < 5) {
      message.warning("请先填写至少 5 字的处理说明");
      return;
    }
    void perform("transitions", { action, comment: comment.trim() }, "状态已更新");
  };
  const assign = () => {
    if (!assignee) { message.warning("请选择处理人"); return; }
    void perform("assignee", { username: assignee }, "处理人已指派", "put");
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
      { key: "assignee", label: "处理人", children: feedback.assignee_display_name || feedback.assignee || "未指派" },
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
    {feedback.can_assign && <Space wrap style={{ marginTop: 20 }}>
      <KeywordPersonSelect showSearch value={assignee || undefined} placeholder="选择处理人" aria-label="选择处理人"
        style={{ minWidth: 240 }} optionFilterProp="label"
        options={people.map((person) => ({ value: person.username, label: `${person.label}（${person.username}）` }))}
        onChange={setAssignee} />
      <Button disabled={busy || !assignee || assignee === feedback.assignee} onClick={assign}>指派处理人</Button>
    </Space>}
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
        {event.has_screenshot && <FeedbackEventImage feedbackId={feedbackId} eventId={event.id} />}
      </div>,
    }))} />
    <Input.TextArea value={comment} rows={4} maxLength={2000} showCount aria-label="回复或处理说明"
      placeholder="回复或填写处理说明" onChange={(event) => setComment(event.target.value)}
      style={{ maxWidth: 850, marginBottom: 12 }} />
    <div style={{ marginBottom: 12 }}>
      <input ref={screenshotInput} type="file" accept="image/png,image/jpeg,image/webp"
        aria-label="补充截图" onChange={(event) => setScreenshot(event.target.files?.[0] || null)} />
    </div>
    <div><Space wrap>
      <Button type="primary" disabled={busy || !comment.trim()} loading={busy} onClick={reply}>发送回复</Button>
      {feedback.available_actions.map((action) => <Button key={action}
        type={["标记已处理", "确认解决"].includes(action) ? "primary" : "default"} disabled={busy}
        onClick={() => transition(action)}>{action}</Button>)}
    </Space></div>
  </section>;
}
