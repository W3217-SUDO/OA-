import { forwardRef, useCallback, useEffect, useRef, useState, type ComponentRef } from "react";
import { Alert, Button, Input, List } from "antd";
import { ArrowUpOutlined, CheckOutlined, CloseOutlined, ReloadOutlined, StopOutlined } from "@ant-design/icons";
import AssistantStart, { shortcuts, type AssistantSuggestion } from "./AssistantStart";
import { ConversationManager } from "./ConversationManager";
import { actionLabel } from "./types";
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
  onOpenCaseAgent: () => void;
};

// 工作台里的个人智能体：对话和输入框合在一个面板内，会话可并行进行；问候语放在工作台顶部。
const AssistantPanel = forwardRef<HTMLElement, Props>(function AssistantPanel(
  { workspace, suggestions, focusRequested, onFocusHandled, onOpenCaseAgent },
  ref,
) {
  const { status, state, loading, loadError, sending, stopping, input, setInput, send, stop, decide, load } = workspace;
  const threadRef = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);
  const inputRef = useRef<ComponentRef<typeof Input.TextArea>>(null);
  const lastMessage = state.messages[state.messages.length - 1];
  const followBottom = useCallback(() => {
    const element = threadRef.current;
    stickToBottom.current = true;
    // 流式输出期间直接跟随，不做平滑动画，避免每个分片重启滚动动画造成跳动。
    if (element) element.scrollTop = element.scrollHeight;
  }, []);

  useEffect(() => {
    if (!stickToBottom.current) return;
    const element = threadRef.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, [state.messages.length, lastMessage?.content.length]);
  useEffect(() => { stickToBottom.current = true; }, [state.conversation_id]);
  useEffect(() => {
    if (!focusRequested) return;
    inputRef.current?.focus({ preventScroll: true });
    onFocusHandled();
  }, [focusRequested, onFocusHandled]);

  const submit = (text: string) => {
    const content = text.trim();
    if (!content) return;
    // 快捷问题与提醒直接带上内容；输入框发送沿用工作区里按会话保存的草稿。
    setInput("");
    followBottom();
    void send(content);
  };

  // 允许同一账号下多个会话同时回答；当前会话正在回答只禁用当前会话的输入。
  const runningIds = workspace.runningIds;

  return (
    <section className={`assistant${state.messages.length ? "" : " is-empty"}`} aria-label="个人智能体" ref={ref}>
      <div className="assistant-bar">
        <span className="assistant-bar-title">助手对话</span>
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
        />
      </div>
      {loadError && (
        <Alert className="assistant-alert" type="error" showIcon title={loadError} action={<Button size="small" onClick={() => void load()}>重试</Button>} />
      )}
      {!loadError && status && !status.ready && (
        <Alert className="assistant-alert" type="warning" showIcon title="个人智能体暂未就绪，请检查当前 OA 配置的大模型服务" />
      )}
      {state.messages.length === 0 && <AssistantStart suggestions={suggestions} disabled={sending} onPick={submit} />}
      {state.messages.length > 0 && (
        <div
          className="assistant-thread"
          ref={threadRef}
          aria-live="polite"
          onScroll={() => {
            const element = threadRef.current;
            if (element) stickToBottom.current = element.scrollHeight - element.scrollTop - element.clientHeight < FOLLOW_THRESHOLD;
          }}
        >
          {state.messages.map((item, index) => (
            <div key={`${item.created_at || "message"}-${index}`} className={`assistant-message is-${item.role}`}>
              <div className={`assistant-bubble${item.failed ? " is-failed" : ""}`}>
                {item.content
                  ? (item.role === "user" ? <MessageText content={item.content} /> : item.content)
                  : (sending && index === state.messages.length - 1 ? <span className="assistant-thinking">{workspace.progress || "正在思考"}</span> : "")}
              </div>
            </div>
          ))}
        </div>
      )}
      {!stickToBottom.current && state.messages.length > 0 && (
        <button type="button" className="assistant-jump" onClick={followBottom}>回到最新回答</button>
      )}
      {!!state.pending_actions.length && (
        <div className="assistant-pending">
          <b>待你确认的操作</b>
          <List
            size="small"
            dataSource={state.pending_actions}
            renderItem={(item) => (
              <List.Item
                actions={[
                  <Button key="approve" type="primary" size="small" icon={<CheckOutlined />} onClick={() => void decide(item, "approved")}>确认</Button>,
                  <Button key="reject" size="small" icon={<CloseOutlined />} onClick={() => void decide(item, "rejected")}>取消</Button>,
                ]}
              >
                <List.Item.Meta title={actionLabel(item)} description={item.summary} />
              </List.Item>
            )}
          />
        </div>
      )}
      <form className="assistant-composer" onSubmit={(event) => { event.preventDefault(); submit(input); }}>
        <Input.TextArea
          ref={inputRef}
          variant="borderless"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onPressEnter={(event) => { if (!event.shiftKey) { event.preventDefault(); submit(input); } }}
          autoSize={{ minRows: 1, maxRows: 5 }}
          placeholder="告诉智能体你要完成的 OA 工作"
          disabled={loading || !status?.ready}
          aria-label="给智能体的指令"
        />
        {sending
          ? <Button className="assistant-send" shape="circle" danger icon={<StopOutlined />} loading={stopping} aria-label="停止回答" onClick={() => void stop()} />
          : <Button className="assistant-send" shape="circle" type="primary" icon={<ArrowUpOutlined />} aria-label="发送" htmlType="submit" disabled={workspace.conversationBusy || !input.trim()} />}
      </form>
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
      <div className="assistant-meta">
        <span>{runningIds.length > 1 ? `${runningIds.length} 个对话正在同时回答` : "所有查询和操作都受 OA 原有权限控制，写入系统前需要你确认"}</span>
        <span className="assistant-tools">
          <span className={`assistant-status ${status?.ready ? "is-ready" : "is-down"}`}>
            {loading ? "连接中" : status?.ready ? "服务已连接" : "模型未就绪"}
          </span>
          <Button type="text" size="small" icon={<ReloadOutlined />} aria-label="刷新智能体" title="刷新智能体" disabled={loading || !!runningIds.length} onClick={() => void load()} />
          <Button type="link" size="small" onClick={onOpenCaseAgent}>案件智能体</Button>
        </span>
      </div>
    </section>
  );
});

export default AssistantPanel;
