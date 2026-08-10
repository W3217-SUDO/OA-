import { useEffect, useMemo, useRef, useState } from "react";
import { Alert, Button, Empty, Input, List, message, Space, Spin, Tag } from "antd";
import { CloseOutlined, ReloadOutlined, RobotOutlined, SendOutlined } from "@ant-design/icons";
import { api } from "./api";
import "./agent-center.css";

type CaseOption = { id: number; serial_no: string; title: string; customer: string; status: string };
type AgentMessage = { id?: string; role: "user" | "assistant"; content: string; created_at?: string };
type AgentAction = { id: string; type: string; summary: string; status: "pending" | "approved" | "rejected" };
type AgentState = { messages: AgentMessage[]; pending_actions: AgentAction[] };
type AgentStatus = { ready: boolean; model: string; checkpoint_backend: string; write_requires_approval: boolean };

export default function AgentCenterPage() {
  const [cases, setCases] = useState<CaseOption[]>([]);
  const [selected, setSelected] = useState<CaseOption | null>(null);
  const [keyword, setKeyword] = useState("");
  const [listLoading, setListLoading] = useState(false);
  const [agentLoading, setAgentLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [decisionLoading, setDecisionLoading] = useState("");
  const [status, setStatus] = useState<AgentStatus | null>(null);
  const [state, setState] = useState<AgentState | null>(null);
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadCases = async (nextKeyword = keyword) => {
    setListLoading(true);
    try {
      const { data } = await api.get("/records", { params: { module: "case", keyword: nextKeyword.trim(), page: 1, page_size: 100, exclude_archived: true } });
      const items = (data.items || data || []) as CaseOption[];
      setCases(items);
      setSelected((current) => current && items.some((item) => item.id === current.id) ? current : items[0] || null);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "案件空间加载失败");
    } finally {
      setListLoading(false);
    }
  };
  const loadAgent = async (record: CaseOption) => {
    setAgentLoading(true);
    try {
      const [statusRes, stateRes] = await Promise.all([
        api.get(`/case-spaces/${record.id}/agent/status`),
        api.get(`/case-spaces/${record.id}/agent/state`),
      ]);
      setStatus(statusRes.data);
      setState(stateRes.data);
    } catch (error: any) {
      setStatus(null);
      setState(null);
      message.error(error?.response?.data?.detail || "智能体会话加载失败");
    } finally {
      setAgentLoading(false);
    }
  };
  useEffect(() => { void loadCases(""); }, []);
  useEffect(() => {
    if (selected) void loadAgent(selected);
    else { setStatus(null); setState(null); }
  }, [selected?.id]);
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ block: "end" }); }, [state?.messages.length]);

  const send = async (preset?: string) => {
    if (!selected || sending) return;
    const content = String(preset ?? input).trim();
    if (!content) return message.warning("请输入要询问的问题");
    setSending(true);
    try {
      const { data } = await api.post(`/case-spaces/${selected.id}/agent/messages`, { message: content });
      setState(data);
      setInput("");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "智能体响应失败");
    } finally {
      setSending(false);
    }
  };
  const decide = async (action: AgentAction, decision: "approved" | "rejected") => {
    if (!selected || decisionLoading) return;
    setDecisionLoading(action.id);
    try {
      const { data } = await api.post(`/case-spaces/${selected.id}/agent/actions/${action.id}/decision`, { decision, comment: "智能体中心人工审批" });
      setState(data);
      message.success(decision === "approved" ? "已记录批准决定" : "已记录驳回决定");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "审批失败");
    } finally {
      setDecisionLoading("");
    }
  };
  const pendingActions = useMemo(() => (state?.pending_actions || []).filter((item) => item.status === "pending"), [state]);

  return <div className="agent-center-page" data-testid="agent-center-page">
    <header className="agent-center-header">
      <div><h2>智能体中心</h2><span>统一业务空间</span></div>
      <Space wrap><Tag>客户</Tag><Tag>合同</Tag><Tag>案件</Tag><Tag>线索</Tag><Tag>调查</Tag><Tag>财务</Tag></Space>
    </header>
    <div className="agent-center-layout">
      <aside className="agent-space-list">
        <div className="agent-space-search">
          <Input.Search value={keyword} allowClear placeholder="搜索案号、案件名或客户" onChange={(event) => setKeyword(event.target.value)} onSearch={(value) => void loadCases(value)} />
          <Button type="text" icon={<ReloadOutlined />} title="刷新空间" onClick={() => void loadCases()} />
        </div>
        <Spin spinning={listLoading}>
          <List
            dataSource={cases}
            locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无可访问的业务空间" /> }}
            renderItem={(item) => <List.Item className={selected?.id === item.id ? "agent-space-active" : ""} onClick={() => setSelected(item)}>
              <div className="agent-space-item"><strong>{item.serial_no}</strong><span>{item.title}</span><small>{item.customer || "—"} · {item.status}</small></div>
            </List.Item>}
          />
        </Spin>
      </aside>
      <main className="agent-workspace">
        {!selected ? <Empty description="请选择业务空间" /> : <>
          <div className="agent-workspace-status">
            <div><strong>{selected.serial_no}</strong><span>{selected.title}</span></div>
            <Space wrap><Tag color={status?.ready ? "success" : "warning"}>{status?.ready ? "服务正常" : "服务未就绪"}</Tag><Tag>{status?.model || "模型未配置"}</Tag><Tag color="blue">关系图</Tag><Tag color="gold">人工审批</Tag></Space>
          </div>
          {pendingActions.length > 0 && <section className="agent-global-actions">
            <Alert type="info" showIcon title="待审批操作不会自动改写业务数据" />
            {pendingActions.map((action) => <div key={action.id}><span><strong>{action.summary}</strong><small>{action.type}</small></span><Space><Button size="small" type="primary" loading={decisionLoading === action.id} onClick={() => void decide(action, "approved")}>批准</Button><Button size="small" danger icon={<CloseOutlined />} onClick={() => void decide(action, "rejected")}>驳回</Button></Space></div>)}
          </section>}
          <div className="agent-global-messages">
            {!agentLoading && !state?.messages?.length && <div className="agent-global-empty"><RobotOutlined /><strong>开始分析当前业务空间</strong><span>回答会综合关联的客户、合同、案件、线索、调查和财务数据。</span></div>}
            {state?.messages?.map((item, index) => <div key={item.id || index} className={`agent-global-message agent-global-message-${item.role}`}><small>{item.role === "user" ? "我" : "智能体"}</small><div>{item.content}</div></div>)}
            {(agentLoading || sending) && <div className="agent-global-loading"><RobotOutlined /> {sending ? "正在分析关联业务数据..." : "正在加载会话..."}</div>}
            <div ref={messagesEndRef} />
          </div>
          {!state?.messages?.length && status?.ready && <div className="agent-global-suggestions">{["概括业务空间现状", "检查期限与任务风险", "汇总合同、费用与发票", "梳理线索和调查进度"].map((text) => <Button key={text} size="small" onClick={() => void send(text)}>{text}</Button>)}</div>}
          <div className="agent-global-composer"><Input.TextArea value={input} autoSize={{ minRows: 2, maxRows: 5 }} placeholder="询问当前空间的业务信息" disabled={!status?.ready || sending} onChange={(event) => setInput(event.target.value)} onPressEnter={(event) => { if (!event.shiftKey) { event.preventDefault(); void send(); } }} /><Button type="primary" icon={<SendOutlined />} title="发送" loading={sending} disabled={!status?.ready || !input.trim()} onClick={() => void send()} /></div>
        </>}
      </main>
    </div>
  </div>;
}
