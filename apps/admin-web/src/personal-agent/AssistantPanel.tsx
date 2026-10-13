import { forwardRef, useCallback, useEffect, useRef, useState, type ComponentRef } from "react";
import { Alert, Button, Input, List, Tooltip } from "antd";
import { ArrowLeftOutlined, ArrowUpOutlined, CheckOutlined, CloseOutlined, ReloadOutlined } from "@ant-design/icons";
import AssistantStart, { shortcuts, type AssistantSuggestion } from "./AssistantStart";
import { ConversationManager } from "./ConversationManager";
import { AssistantWorkspaceTools } from "./AssistantWorkspaceTools";
import { ActionConfirmation } from "./ActionConfirmation";
import { ConfirmationHistory } from "./ConfirmationHistory";
import { errorText, type PendingAction } from "./types";
import type { usePersonalWorkspace } from "./usePersonalWorkspace";
import "./assistant-panel.css";

export type { AssistantSuggestion };

// 距底部小于该距离就视为“跟着最新回答”，超出则由用户自行滚动，不再强制拉回。
const FOLLOW_THRESHOLD = 48;

const LONG_MESSAGE_LENGTH = 120;

// 从提醒里发出的问题带有完整明细，较长时先折叠，需要时再展开。
function MessageText({ content }: { content: string }) {
  const [expanded, setExpanded] = useState(false);
  if (content.length <= LONG_MESSAGE_LENGTH) return <>{content}</>;
  return (
    <>
      {expanded ? content : `${content.slice(0, LONG_MESSAGE_LENGTH)}...`}
      <button type="button" className="assistant-expand" onClick={() => setExpanded((value) => !value)}>
        {expanded ? "收起" : "展开全文"}
      </button>
    </>
  );
}

type Props = {
  workspace: ReturnType<typeof usePersonalWorkspace>;
  suggestions: AssistantSuggestion[];
  focusRequested: boolean;
  onFocusHandled: () => void;
  onReturnOverview?: () => void;
  name?: string;
  logoSrc?: string;
  returnLabel?: string;
};

// 工作台里的个人智能体：对话和输入框合在一个面板内，会话可并行进行；问候语放在工作台顶部。
const AssistantPanel = forwardRef<HTMLElement, Props>(function AssistantPanel(
  { workspace, suggestions, focusRequested, onFocusHandled, onReturnOverview, name, logoSrc, returnLabel = "返回工作概况" },
  ref,
) {
  const { status, state, loading, loadError, sending, stopping, input, setInput, send, stop, decide, load } = workspace;
  const threadRef = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);
  const [awayFromBottom, setAwayFromBottom] = useState(false);
  const inputRef = useRef<ComponentRef<typeof Input.TextArea>>(null);
  const [composing, setComposing] = useState(false);
  const [activeAction, setActiveAction] = useState<PendingAction | null>(null);
  const [decisionError, setDecisionError] = useState("");
  const hasMessages = state.messages.length > 0;
  const lastMessage = state.messages[state.messages.length - 1];
  const sendBlocked = loading || !!loadError || !status?.ready || workspace.conversationBusy || workspace.uploading || !!workspace.decisionId || stopping || composing;
  const progressText = (workspace.progress || "正在思考").replace(/[.\u2026]+$/, "");
  const followBottom = useCallback(() => {
    const element = threadRef.current;
    stickToBottom.current = true;
    setAwayFromBottom(false);
    // 流式输出期间直接跟随，不做平滑动画，避免每个分片重启滚动动画造成跳动。
    if (element) element.scrollTop = element.scrollHeight;
  }, []);

  useEffect(() => {
    stickToBottom.current = true;
    setAwayFromBottom(false);
    setActiveAction(null);
    setDecisionError("");
  }, [state.conversation_id]);
  useEffect(() => {
    if (!stickToBottom.current) return;
    const element = threadRef.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, [state.conversation_id, state.messages.length, lastMessage?.content.length]);
  useEffect(() => {
    const element = threadRef.current;
    if (!element) return;
    const mobileViewport = window.matchMedia("(max-width: 991px)");
    // 键盘或输入框改变消息区高度时，只延续已有的底部跟随，不打断用户查看历史。
    const observer = new ResizeObserver(() => {
      if (mobileViewport.matches && stickToBottom.current) element.scrollTop = element.scrollHeight;
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, [state.conversation_id, hasMessages]);
  useEffect(() => {
    if (!focusRequested) return;
    inputRef.current?.focus({ preventScroll: true });
    onFocusHandled();
  }, [focusRequested, onFocusHandled]);

  const submit = (text?: string) => {
    const content = (text ?? input).trim();
    if (!content || sendBlocked) return;
    // 草稿的清空和失败恢复交给工作区，避免拒绝发送或停止失败时丢失输入。
    followBottom();
    void send(text === undefined ? undefined : content);
  };

  const runningIds = workspace.runningIds;
  const conversationTitle = state.conversation_title || name || "沪知助手";
  const decisionBusy = loading || sending || workspace.conversationBusy || !!workspace.decisionId;
  const reject = async (action: PendingAction) => {
    if (decisionBusy) return;
    setDecisionError("");
    try { await decide(action, "rejected"); }
    catch (error) { setDecisionError(errorText(error, "取消操作失败，请核对实际状态")); }
  };

  return (
    <section className={`assistant${hasMessages ? "" : " is-empty"}`} aria-label={name || "个人智能体"} ref={ref}>
      <div className="assistant-bar">
        {onReturnOverview && <Tooltip title={returnLabel}>
          <Button className="assistant-mobile-control" type="text" icon={<ArrowLeftOutlined />} aria-label={returnLabel} onClick={onReturnOverview} />
        </Tooltip>}
        <span className="assistant-bar-summary">
          {logoSrc && <img className="assistant-brand-logo" src={logoSrc} alt="" width={24} height={24} />}
          <span className="assistant-bar-title">{name || "助手对话"}</span>
          {name && state.conversation_title && <span className="assistant-selected-title" title={state.conversation_title}>{state.conversation_title}</span>}
          {runningIds.length > 1 && <span className="assistant-running">{runningIds.length} 个对话正在回答</span>}
        </span>
        <span className={`assistant-mobile-title${name || logoSrc ? " is-branded" : ""}`} title={conversationTitle}>
          {logoSrc && <img className="assistant-brand-logo" src={logoSrc} alt="" width={24} height={24} />}
          {name || logoSrc ? <span className="assistant-title-body">
            <span>{name || conversationTitle}</span>
            {name && state.conversation_title && <small>{state.conversation_title}</small>}
          </span> : conversationTitle}
        </span>
        <div className="assistant-bar-actions">
          <ConfirmationHistory />
          <Tooltip title="刷新智能体">
            <Button
              className="assistant-refresh"
              type="text"
              icon={<ReloadOutlined />}
              aria-label="刷新智能体"
              disabled={loading || !!runningIds.length}
              onClick={() => void load()}
            />
          </Tooltip>
          <ConversationManager
            items={workspace.conversations}
            activeId={state.conversation_id}
            busy={loading || workspace.conversationBusy}
            runningIds={runningIds}
            onCreate={workspace.createConversation}
            onSelect={workspace.selectConversation}
            onDelete={workspace.deleteConversation}
            drawerClassName="assistant-conversation-drawer"
            listClassName="assistant-conversation-list"
            rowClassName="assistant-conversation-row"
            selectClassName="assistant-conversation-select"
            showHistoryLabel
          />
        </div>
      </div>
      {loadError && (
        <Alert className="assistant-alert" type="error" showIcon title={loadError} action={<Button size="small" onClick={() => void load()}>重试</Button>} />
      )}
      {!loadError && status && !status.ready && (
        <Alert className="assistant-alert" type="warning" showIcon title="个人智能体暂未就绪，请检查当前 OA 配置的大模型服务" />
      )}
      {!hasMessages && <div className={`assistant-empty-state${logoSrc ? " has-logo" : ""}`}>
        {logoSrc && <img className="assistant-empty-logo" src={logoSrc} alt="" width={56} height={56} />}
        <AssistantStart suggestions={suggestions} disabled={sending} onPick={submit} />
        <div className="assistant-mobile-empty">
          <h2>今天想处理什么？</h2>
          <div className="assistant-mobile-suggestions">
            {suggestions.slice(0, 1).map((item) => <button key={item.kind} type="button" disabled={sendBlocked} onClick={() => submit(item.prompt)}>
              {item.label}<em>{item.count}</em>
            </button>)}
            {shortcuts.slice(0, 2).map((item) => <button key={item.label} type="button" disabled={sendBlocked} onClick={() => submit(item.prompt)}>{item.label}</button>)}
          </div>
        </div>
      </div>}
      {hasMessages && (
        <div className="assistant-thread-region">
          <div
            className="assistant-thread"
            ref={threadRef}
            aria-live="polite"
            onScroll={() => {
              const element = threadRef.current;
              if (!element) return;
              const following = element.scrollHeight - element.scrollTop - element.clientHeight < FOLLOW_THRESHOLD;
              stickToBottom.current = following;
              setAwayFromBottom(!following);
            }}
          >
            {state.messages.map((item, index) => {
              const thinking = !item.content && !item.stopped && sending && index === state.messages.length - 1;
              return (
                <div key={`${item.created_at || "message"}-${index}`} className={`assistant-message is-${item.role}`}>
                  <div className={`assistant-bubble${item.failed ? " is-failed" : ""}${thinking ? " is-thinking" : ""}`}>
                    {item.content
                      ? (item.role === "user" ? <MessageText content={item.content} /> : item.content)
                      : (thinking ? <span className="assistant-thinking" role="status" title={progressText}><span>{progressText}</span></span> : "")}
                    {item.stopped && <span className="assistant-stopped">{item.content ? "已停止，已保留生成内容" : "已停止"}</span>}
                  </div>
                </div>
              );
            })}
          </div>
          {awayFromBottom && <button type="button" className="assistant-jump" onClick={followBottom}>回到最新回答</button>}
        </div>
      )}
      {!!state.pending_actions.length && (
        <div className="assistant-pending">
          <b>待你确认的操作</b>
          {decisionError && <Alert type="error" showIcon title="操作未完成" description={decisionError} />}
          <List
            size="small"
            dataSource={state.pending_actions.filter((action) => action.status === "pending")}
            renderItem={(item) => (
              <List.Item
                actions={[
                  <Button key="approve" type="primary" size="small" icon={<CheckOutlined />} disabled={decisionBusy} onClick={() => { setDecisionError(""); setActiveAction(item); }}>查看并确认</Button>,
                  <Button key="reject" size="small" icon={<CloseOutlined />} disabled={decisionBusy} loading={workspace.decisionId === item.id} onClick={() => void reject(item)}>取消</Button>,
                ]}
              >
                <List.Item.Meta title={item.summary} />
              </List.Item>
            )}
          />
        </div>
      )}
      <ActionConfirmation action={activeAction} deciding={!!workspace.decisionId} onDecide={decide} onClose={() => setActiveAction(null)} />
      <div className="assistant-composer"
        onDragOver={(event) => { if (event.dataTransfer.types.includes("Files")) event.preventDefault(); }}
        onDrop={(event) => {
          if (!event.dataTransfer.files.length) return;
          event.preventDefault();
          void workspace.upload(Array.from(event.dataTransfer.files));
        }}
      >
        <AssistantWorkspaceTools key={state.conversation_id || "new"} workspace={workspace} />
        <form className="assistant-composer-input" onSubmit={(event) => { event.preventDefault(); submit(); }}>
          <Input.TextArea
            ref={inputRef}
            variant="borderless"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onCompositionStart={() => setComposing(true)}
            onCompositionEnd={() => setComposing(false)}
            onPressEnter={(event) => {
              if (event.shiftKey || event.nativeEvent.isComposing || event.keyCode === 229 || composing) return;
              event.preventDefault();
              submit();
            }}
            onPaste={(event) => {
              if (event.clipboardData.files.length) { event.preventDefault(); void workspace.upload(Array.from(event.clipboardData.files)); }
            }}
            maxLength={8000}
            autoSize={{ minRows: 1, maxRows: 5 }}
            placeholder="告诉智能体你要完成的 OA 工作"
            disabled={loading || !status?.ready}
            aria-label="给智能体的指令"
          />
          <div className="assistant-composer-actions">
            {sending && <Tooltip title={stopping ? "正在停止回答" : "停止回答"}>
              <Button
                className="assistant-send assistant-stop"
                shape="circle"
                icon={<span className="assistant-stop-glyph" aria-hidden="true" />}
                loading={stopping}
                disabled={stopping}
                aria-label={stopping ? "正在停止回答" : "停止回答"}
                onClick={() => void stop()}
              />
            </Tooltip>}
            {(!sending || !!input.trim()) && <Tooltip title={sending ? "打断并发送" : "发送"}>
              <Button className="assistant-send" shape="circle" type="primary" icon={<ArrowUpOutlined />} aria-label={sending ? "打断并发送" : "发送"} htmlType="submit" disabled={sendBlocked || !input.trim()} />
            </Tooltip>}
          </div>
        </form>
      </div>
      <div className="assistant-chips">
        {suggestions.map((item) => (
          <button key={item.kind} type="button" className="is-context" disabled={sending} onClick={() => submit(item.prompt)}>
            {item.label}<em>{item.count}</em>
          </button>
        ))}
        {shortcuts.map((item) => (
          <button key={item.label} type="button" disabled={sending} onClick={() => submit(item.prompt)}>{item.label}</button>
        ))}
      </div>
    </section>
  );
});

export default AssistantPanel;
