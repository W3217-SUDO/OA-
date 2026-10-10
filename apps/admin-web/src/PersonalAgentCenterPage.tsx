import { useEffect, useRef, useState } from "react";
import { Alert, Button, Card, Empty, Input, List, Modal, Space, Spin, Tag, message } from "antd";
import { CheckOutlined, CloseOutlined, IdcardOutlined, ReloadOutlined, RobotOutlined, SendOutlined, StopOutlined } from "@ant-design/icons";
import { api } from "./api";
import { AgentOperationPreview, agentOperationError, agentOperationName, hasAgentOperationPreview, type AgentActionPreview } from "./AgentOperationPreview";
import { AgentToolRequests } from "./AgentToolRequests";
import { AgentToolResult } from "./AgentToolResult";
import "./personal-agent-center.css";

type MessageItem = { role: "user" | "assistant"; content: string; created_at?: string };
type PendingAction = { id: string; type: string; summary: string; payload?: Record<string, unknown>; preview?: AgentActionPreview; status: "pending" | "approved" | "rejected" };
type AgentState = { messages: MessageItem[]; pending_actions: PendingAction[]; structured_results?: unknown[] };
type AgentStatus = { ready: boolean; model: string; model_provider?: string; write_requires_confirmation: boolean; identity: { display_name?: string; department?: string; role?: string; position?: string } };

export default function PersonalAgentCenterPage() {
  const [status, setStatus] = useState<AgentStatus | null>(null);
  const [state, setState] = useState<AgentState>({ messages: [], pending_actions: [] });
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [activeAction, setActiveAction] = useState<PendingAction | null>(null);
  const [decisionLoading, setDecisionLoading] = useState(false);
  const [decisionResult, setDecisionResult] = useState<unknown>();
  const decisionRef = useRef(false);
  const requestRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const load = async () => {
    setLoading(true);
    try {
      const [statusResponse, stateResponse] = await Promise.all([
        api.get("/personal-agent/status"),
        api.get("/personal-agent/state"),
      ]);
      setStatus(statusResponse.data);
      setState(stateResponse.data);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "智能体中心加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [state.messages.length, sending]);
  useEffect(() => () => requestRef.current?.abort(), []);

  const decide = async (action: PendingAction, decision: "approved" | "rejected") => {
    if (decisionRef.current) return;
    decisionRef.current = true;
    setDecisionLoading(true);
    try {
      const { data } = await api.post(`/personal-agent/actions/${action.id}/decision`, { decision }, { headers: { "X-OA-Agent-Confirmation": "frontend" } });
      setState(data.state);
      setDecisionResult(data.result);
      setActiveAction(null);
      message.success(decision === "approved" ? "操作已完成" : "已取消操作");
    } catch (error: any) {
      message.error(agentOperationError(error, "操作未完成，请刷新查看执行状态"));
      setActiveAction(null);
      void load();
    } finally {
      decisionRef.current = false;
      setDecisionLoading(false);
    }
  };

  const send = async (preset?: string) => {
    const content = (preset || input).trim();
    if (!content || sending) return;
    setInput("");
    setSending(true);
    const controller = new AbortController();
    requestRef.current = controller;
    const assistantIndex = state.messages.length + 1;
    setState((current) => ({ ...current, messages: [...current.messages, { role: "user", content }, { role: "assistant", content: "" }] }));
    try {
      const response = await fetch("/api/v1/personal-agent/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("access_token") || ""}` },
        body: JSON.stringify({ content }),
        signal: controller.signal,
      });
      if (!response.ok || !response.body) {
        const detail = await response.text();
        throw new Error(detail || "个人智能体响应失败");
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      const consume = (chunk: string) => {
        buffer += chunk;
        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() || "";
        for (const block of blocks) {
          const line = block.split("\n").find((item) => item.startsWith("data:"));
          if (!line) continue;
          const event = JSON.parse(line.slice(5).trim()) as { type: string; content?: string; detail?: string; state?: AgentState };
          if (event.type === "delta") {
            setState((current) => ({ ...current, messages: current.messages.map((item, index) => index === assistantIndex ? { ...item, content: `${item.content}${event.content || ""}` } : item) }));
          } else if (event.type === "state" && event.state) {
            setState(event.state);
          } else if (event.type === "error") {
            throw new Error(event.detail || "个人智能体处理失败");
          }
        }
      };
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        consume(decoder.decode(value, { stream: true }));
      }
    } catch (error: any) {
      if (error?.name !== "AbortError") {
        setState((current) => ({ ...current, messages: current.messages.map((item, index) => index === assistantIndex ? { ...item, content: error?.message || "个人智能体处理失败" } : item) }));
      }
    } finally {
      requestRef.current = null;
      setSending(false);
    }
  };

  if (loading) return <div className="personal-agent-loading"><Spin /> 正在加载个人工作空间...</div>;

  return <div className="personal-agent-page" data-testid="personal-agent-center-page">
    <header className="personal-agent-header">
      <div className="personal-agent-title">
        <div className="personal-agent-icon"><RobotOutlined /></div>
        <div><h2>智能体中心</h2><span>你的 OA 办公空间</span></div>
      </div>
      <Space wrap>
        <Button size="small" onClick={() => { window.location.href = "?page=case-agent-center"; }}>案件智能体</Button>
        <Tag color={status?.ready ? "success" : "error"}>{status?.ready ? "服务已连接" : "模型未就绪"}</Tag>
        <Tag>{status?.model || "未配置模型"}</Tag>
        <Button icon={<ReloadOutlined />} onClick={() => void load()}>刷新</Button>
      </Space>
    </header>
    <div style={{ padding: "6px 14px", borderBottom: "1px solid #dfe5ea", background: "#fff" }}><AgentToolRequests /></div>
    {!status?.ready && <Alert className="personal-agent-alert" type="warning" showIcon message="个人智能体暂未就绪" description="请检查当前 OA 配置的大模型服务。" />}
    <div className="personal-agent-layout">
      <aside className="personal-agent-sidebar">
        <Card className="identity-card" bordered={false}>
          <div className="identity-heading"><IdcardOutlined /><span>我的身份</span></div>
          <strong>{status?.identity?.display_name || "当前用户"}</strong>
          <div className="identity-line">{status?.identity?.department || "—"} · {status?.identity?.position || status?.identity?.role || "—"}</div>
        </Card>
        <div className="personal-agent-shortcuts">
          <span>快捷办公</span>
          <Button block onClick={() => void send("列出我今天优先处理的审批和任务")}>今日优先事项</Button>
          <Button block onClick={() => void send("查询我当前待审批的合同")}>我的合同审批</Button>
          <Button block onClick={() => void send("列出我负责的案件和当前阶段")}>我的案件</Button>
        </div>
        <div className="permission-note">所有查询和操作都受 OA 原有权限控制。写入系统前需要你确认。</div>
      </aside>
      <section className="personal-agent-chat">
        <div className="chat-heading"><div><b>办公对话</b><span>只属于当前账号的会话</span></div><Tag color="blue">个人会话</Tag></div>
        <div className="personal-agent-messages">
          {!state.messages.length && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="从一个 OA 工作开始" />}
          {state.messages.map((item, index) => <div key={`${item.created_at || "message"}-${index}`} className={`personal-message ${item.role}`}>
            <div className="message-role">{item.role === "user" ? "我" : "个人智能体"}</div>
            <div className="message-bubble">{item.content || (sending && index === state.messages.length - 1 ? "正在思考..." : "")}</div>
          </div>)}
          <AgentToolResult result={[state.structured_results, decisionResult]} />
          <div ref={bottomRef} />
        </div>
        {!!state.pending_actions.filter((item) => item.status === "pending").length && <div className="pending-actions">
          <div className="pending-title">待确认操作</div>
          <List size="small" dataSource={state.pending_actions.filter((item) => item.status === "pending")} renderItem={(item) => <List.Item actions={[
            <Button key="approve" type="primary" size="small" icon={<CheckOutlined />} disabled={decisionLoading} onClick={() => setActiveAction(item)}>查看并确认</Button>,
          ]}><List.Item.Meta title={agentOperationName(item)} description={item.summary} /></List.Item>} />
        </div>}
        <div className="personal-agent-composer">
          <Input.TextArea value={input} onChange={(event) => setInput(event.target.value)} onPressEnter={(event) => { if (!event.shiftKey) { event.preventDefault(); void send(); } }} autoSize={{ minRows: 2, maxRows: 6 }} placeholder="告诉智能体你要完成的 OA 工作" disabled={sending} />
          <div className="composer-actions">
            <span>Enter 发送 · Shift+Enter 换行</span>
            {sending ? <Button danger icon={<StopOutlined />} onClick={() => requestRef.current?.abort()}>停止</Button> : <Button type="primary" icon={<SendOutlined />} onClick={() => void send()} disabled={!input.trim()}>发送</Button>}
          </div>
        </div>
      </section>
    </div>
    <Modal open={Boolean(activeAction)} title="智能体操作确认" width={760} maskClosable={!decisionLoading} onCancel={() => { if (!decisionLoading) setActiveAction(null); }} footer={activeAction ? [
      <Button key="reject" icon={<CloseOutlined />} disabled={decisionLoading} onClick={() => void decide(activeAction, "rejected")}>取消操作</Button>,
      <Button key="approve" type="primary" icon={<CheckOutlined />} loading={decisionLoading} disabled={decisionLoading || !hasAgentOperationPreview(activeAction)} onClick={() => void decide(activeAction, "approved")}>确认并执行</Button>,
    ] : null}>
      {activeAction && <div style={{ maxHeight: "60dvh", overflowY: "auto" }}><AgentOperationPreview action={activeAction} /></div>}
    </Modal>
  </div>;
}
