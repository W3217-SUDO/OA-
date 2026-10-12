import { forwardRef, useEffect, useRef, useState, type ComponentRef } from "react";
import { Alert, Button, Input, List } from "antd";
import { ArrowUpOutlined, CheckOutlined, CloseOutlined, ReloadOutlined, StopOutlined } from "@ant-design/icons";
import AssistantStart, { shortcuts, type AssistantSuggestion } from "./AssistantStart";
import { actionLabel, type PersonalAgent } from "./usePersonalAgent";
import "./assistant-panel.css";

export type { AssistantSuggestion };

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
  agent: PersonalAgent;
  suggestions: AssistantSuggestion[];
  focusRequested: boolean;
  onFocusHandled: () => void;
  onOpenCaseAgent: () => void;
};

// 工作台里的个人智能体：对话和输入框合在一个面板内，问候语放在工作台顶部。
const AssistantPanel = forwardRef<HTMLElement, Props>(function AssistantPanel(
  { agent, suggestions, focusRequested, onFocusHandled, onOpenCaseAgent },
  ref,
) {
  const { status, state, loading, sending, send, stop, decide, reload } = agent;
  const [input, setInput] = useState("");
  const threadRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<ComponentRef<typeof Input.TextArea>>(null);

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: "smooth" });
  }, [state.messages.length, sending]);
  useEffect(() => {
    if (!focusRequested) return;
    inputRef.current?.focus({ preventScroll: true });
    onFocusHandled();
  }, [focusRequested, onFocusHandled]);

  const submit = (text: string) => {
    const content = text.trim();
    if (!content || sending) return;
    setInput("");
    void send(content);
  };

  return (
    <section className={`assistant${state.messages.length ? "" : " is-empty"}`} aria-label="个人智能体" ref={ref}>
      {status && !status.ready && (
        <Alert className="assistant-alert" type="warning" showIcon title="个人智能体暂未就绪，请检查当前 OA 配置的大模型服务" />
      )}
      {state.messages.length === 0 && <AssistantStart suggestions={suggestions} disabled={sending} onPick={submit} />}
      {state.messages.length > 0 && (
        <div className="assistant-thread" ref={threadRef} aria-live="polite">
          {state.messages.map((item, index) => (
            <div key={`${item.created_at || "message"}-${index}`} className={`assistant-message is-${item.role}`}>
              <div className="assistant-bubble">
                {item.content
                  ? (item.role === "user" ? <MessageText content={item.content} /> : item.content)
                  : (sending && index === state.messages.length - 1 ? <span className="assistant-thinking">正在思考</span> : "")}
              </div>
            </div>
          ))}
        </div>
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
          disabled={sending}
          aria-label="给智能体的指令"
        />
        {sending
          ? <Button className="assistant-send" shape="circle" danger icon={<StopOutlined />} aria-label="停止回答" onClick={stop} />
          : <Button className="assistant-send" shape="circle" type="primary" icon={<ArrowUpOutlined />} aria-label="发送" htmlType="submit" disabled={!input.trim()} />}
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
        <span>所有查询和操作都受 OA 原有权限控制，写入系统前需要你确认</span>
        <span className="assistant-tools">
          <span className={`assistant-status ${status?.ready ? "is-ready" : "is-down"}`}>
            {loading ? "连接中" : status?.ready ? "服务已连接" : "模型未就绪"}
          </span>
          <Button type="text" size="small" icon={<ReloadOutlined />} aria-label="刷新智能体" title="刷新智能体" onClick={() => void reload()} />
          <Button type="link" size="small" onClick={onOpenCaseAgent}>案件智能体</Button>
        </span>
      </div>
    </section>
  );
});

export default AssistantPanel;
