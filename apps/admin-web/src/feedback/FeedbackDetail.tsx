import { useCallback, useEffect, useRef, useState } from "react";
import { Alert, Button, Descriptions, Input, message, Popconfirm, Space, Spin, Tag, Tooltip } from "antd";
import { ArrowUpOutlined, PaperClipOutlined, PictureOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { api } from "../api";
import type { FeedbackDetails } from "./types";
import FeedbackFileDrop from "./FeedbackFileDrop";
import { feedbackErrorText, uploadFeedbackFiles } from "./upload";
import FeedbackAttachments from "./FeedbackAttachments";
import FeedbackChatEntry from "./FeedbackChatEntry";
import "./feedback.css";

type Props = { feedbackId: number; onBack: () => void; onNavigate: (route: string) => void };

// 必须先在输入框写内容的操作，以及没写时的提示。
const requiresComment: Record<string, string> = {
  "未解决，重新打开": "请在上面写明哪里还没解决",
  "请确认修改方案": "请在上面写明打算怎么改",
};
const primaryActions = new Set(["确认修改", "处理完成，请验证", "验证通过"]);
const statusColors: Record<string, string> = {
  待处理: "warning", 待确认: "gold", 待验证: "processing", 已解决: "success",
};

export default function FeedbackDetail({ feedbackId, onBack, onNavigate }: Props) {
  const [feedback, setFeedback] = useState<FeedbackDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [comment, setComment] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [composing, setComposing] = useState(false);
  const openPicker = useRef<(() => void) | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get<FeedbackDetails>(`/feedback/${feedbackId}`);
      setFeedback(data);
    } catch (failure: any) {
      // 链接里的问题不存在或没有权限：提示后回到列表。
      if (failure?.response?.status === 404 || failure?.response?.status === 403) {
        message.warning("这个问题不存在，或你没有权限查看", 4);
        onBack();
        return;
      }
      setError(failure?.response?.data?.detail || "反馈详情加载失败");
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [feedbackId]);

  useEffect(() => { void load(); }, [load]);
  // 打开或有新消息时滚到最新一条，和聊天软件一样。
  const listEnd = useRef<HTMLDivElement>(null);
  const eventCount = feedback?.events.length ?? 0;
  useEffect(() => {
    if (!eventCount) return;
    const scroll = () => listEnd.current?.scrollIntoView({ block: "end" });
    scroll();
    // 气泡里的截图是异步取回的，加载后内容变高，再滚一次。
    const timer = window.setTimeout(scroll, 600);
    return () => window.clearTimeout(timer);
  }, [eventCount]);

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

  // 管理员删除问题：逻辑删除，回收站可恢复；删完回到列表。
  const remove = async () => {
    if (!feedback) return;
    setBusy(true);
    try {
      await api.delete(`/feedback/${feedbackId}`);
      message.success(`已删除问题 ${feedback.serial_no}`);
      window.dispatchEvent(new Event("sunhold:notifications-updated"));
      onBack();
    } catch (failure: any) {
      message.error(failure?.response?.data?.detail || "删除失败");
      setBusy(false);
    }
  };

  const reply = () => {
    if (!comment.trim() && !files.length) { message.warning("请填写回复内容或添加截图、附件"); return; }
    void perform("messages", null, "回复已发送");
  };
  const transition = (action: string) => {
    if (requiresComment[action] && !comment.trim()) {
      message.warning(requiresComment[action]);
      return;
    }
    void perform("transitions", { action, comment: comment.trim() }, "状态已更新");
  };

  if (loading && !feedback) return <Spin />;
  if (error && !feedback) return <Alert type="error" showIcon title={error} action={<Button onClick={onBack}>返回列表</Button>} />;
  if (!feedback) return null;
  const actions = feedback.available_actions;
  const hint = actions.includes("确认修改")
    ? "没问题点“确认修改”，确认后才开始改；有意见直接回复。"
    : actions.includes("验证通过") ? "解决了点“验证通过”，没解决写明情况后点“未解决，重新打开”。"
    : actions.includes("请确认修改方案") ? "改之前先写好打算怎么改，点“请确认修改方案”交提交人确认。" : "";

  return <section aria-label="反馈详情">
    <Space wrap style={{ marginBottom: 16 }}>
      <Button onClick={onBack}>返回列表</Button>
      <Button onClick={() => void load()} loading={loading}>刷新</Button>
      <Tag color={statusColors[feedback.status] || "default"}>{feedback.status}</Tag>
      {feedback.can_delete && <Popconfirm title={`删除问题 ${feedback.serial_no}？`}
        description="删除后可由管理员在“系统管理 → 回收站”恢复。" okText="删除" cancelText="取消"
        okButtonProps={{ danger: true }} onConfirm={() => remove()}>
        <Button danger loading={busy}>删除问题</Button>
      </Popconfirm>}
    </Space>
    {error && <Alert type="error" showIcon title={error} style={{ marginBottom: 16 }} />}
    <Descriptions bordered size="small" column={{ xs: 1, sm: 2, md: 2 }} items={[
      { key: "serial", label: "反馈编号", children: feedback.legacy_serial_no
        ? `${feedback.serial_no}（原编号 ${feedback.legacy_serial_no}）` : feedback.serial_no },
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
    <section className="feedback-chat" aria-label="处理记录">
      <h3 className="feedback-chat-title">处理记录</h3>
      <div className="feedback-chat-list">
        {feedback.events.map((event) => <FeedbackChatEntry key={event.id} feedbackId={feedbackId} event={event} />)}
      </div>
      <div className="feedback-chat-composer">
        {hint && <div className="feedback-chat-hint">{hint}</div>}
        <FeedbackFileDrop files={files} onChange={setFiles} disabled={busy} inline pickerRef={openPicker} />
        {/* 参照钉钉聊天框：第一行输入条（发送在条内），第二行一排工具和状态操作，不竖着堆。 */}
        <div className="feedback-chat-input">
          <Input.TextArea value={comment} variant="borderless" autoSize={{ minRows: 1, maxRows: 5 }} aria-label="回复或处理说明"
            placeholder="输入回复，可粘贴截图" onChange={(event) => setComment(event.target.value)}
            onCompositionStart={() => setComposing(true)} onCompositionEnd={() => setComposing(false)}
            onPressEnter={(event) => {
              if (event.shiftKey || event.nativeEvent.isComposing || event.keyCode === 229 || composing) return;
              event.preventDefault();
              if (!busy && (comment.trim() || files.length)) reply();
            }} />
          <Button className="feedback-chat-send" shape="circle" type="primary" icon={<ArrowUpOutlined />} aria-label="发送"
            disabled={busy || (!comment.trim() && !files.length)} loading={busy} onClick={reply} />
        </div>
        <div className="feedback-chat-toolbar" role="toolbar" aria-label="回复工具和状态操作">
          <Tooltip title="添加截图（也可直接粘贴或拖进来）">
            <Button type="text" shape="circle" icon={<PictureOutlined />} aria-label="添加截图" disabled={busy} onClick={() => openPicker.current?.()} />
          </Tooltip>
          <Tooltip title="添加附件">
            <Button type="text" shape="circle" icon={<PaperClipOutlined />} aria-label="添加附件" disabled={busy} onClick={() => openPicker.current?.()} />
          </Tooltip>
          {actions.map((action) => <button key={action} type="button" disabled={busy}
            className={`feedback-chat-action${primaryActions.has(action) ? " is-primary" : ""}${action === "未解决，重新打开" ? " is-danger" : ""}`}
            onClick={() => transition(action)}>{action}</button>)}
        </div>
      </div>
      <div ref={listEnd} className="feedback-chat-end" />
    </section>
  </section>;
}
