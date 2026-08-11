import { useEffect, useMemo, useRef, useState, type ClipboardEvent } from "react";
import { Alert, Button, Empty, Image, Input, List, message, Progress, Select, Space, Spin, Tabs, Tag, Tooltip } from "antd";
import { CheckCircleOutlined, CloseOutlined, ClockCircleOutlined, PaperClipOutlined, ReloadOutlined, RobotOutlined, SendOutlined, StopOutlined, TeamOutlined } from "@ant-design/icons";
import { api } from "./api";
import { DEFAULT_AGENT_SKILL, encodeAgentSkillMessage, type AgentSkill } from "./agentSkillRouting";
import "./agent-center.css";

type CaseOption = { id: number; serial_no: string; title: string; customer: string; status: string };
type AgentAttachment = { id: number; name: string; mime_type?: string; preview_url?: string };
type AgentMessage = { id?: string; role: "user" | "assistant"; content: string; created_at?: string; attachments?: AgentAttachment[] };
type AgentAction = { id: string; type: string; summary: string; status: "pending" | "approved" | "rejected" };
type AgentState = { messages: AgentMessage[]; pending_actions: AgentAction[]; active_skill?: string };
type AgentStatus = { ready: boolean; model: string; checkpoint_backend: string; write_requires_approval: boolean; skills?: AgentSkill[] };
type WorkflowPhase = { code: string; name: string; state: "completed" | "current" | "pending"; target_days?: number | null; warning_days?: number | null };
type WorkflowDeadline = { code: string; title: string; deadline: string; risk: "overdue" | "critical" | "high" | "medium" | "normal"; days_remaining: number; source: string; owner_role: string };
type WorkflowMaterial = { code: string; name: string; required: boolean; status: "uploaded" | "missing" | "optional"; matched_document_count: number };
type WorkflowRoleTask = { role: string; owner_name: string; task: string; assignment_status: "assigned" | "unassigned"; task_status: string };
type WorkflowGuide = {
  manual: { name: string; version: string };
  current_phase: WorkflowPhase;
  phases: WorkflowPhase[];
  deadlines: WorkflowDeadline[];
  deadline_missing_inputs: string[];
  materials: WorkflowMaterial[];
  material_progress: { completed: number; required: number };
  role_tasks: WorkflowRoleTask[];
  agent_rules: string[];
  risk_summary: { overdue: number; critical: number; missing_required_materials: number; unassigned_roles: number };
};

const deadlineRiskMeta = {
  overdue: { color: "error", label: "已逾期" },
  critical: { color: "error", label: "3天内" },
  high: { color: "warning", label: "7天内" },
  medium: { color: "processing", label: "30天内" },
  normal: { color: "default", label: "正常" },
} as const;

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
  const [workflowGuide, setWorkflowGuide] = useState<WorkflowGuide | null>(null);
  const [input, setInput] = useState("");
  const [skillId, setSkillId] = useState(DEFAULT_AGENT_SKILL);
  const [screenshots, setScreenshots] = useState<AgentAttachment[]>([]);
  const [screenshotUploading, setScreenshotUploading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const screenshotInputRef = useRef<HTMLInputElement>(null);
  const screenshotPreviewUrlsRef = useRef(new Map<number, string>());
  const activeAgentRequestRef = useRef<AbortController | null>(null);

  const stateWithScreenshotPreviews = (nextState: AgentState) => ({
    ...nextState,
    messages: (nextState.messages || []).map((item) => ({
      ...item,
      attachments: item.attachments?.map((attachment) => ({
        ...attachment,
        preview_url: screenshotPreviewUrlsRef.current.get(attachment.id),
      })),
    })),
  });
  const clearScreenshotPreviews = () => {
    screenshotPreviewUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
    screenshotPreviewUrlsRef.current.clear();
  };
  const removeScreenshot = (attachment: AgentAttachment) => {
    const previewUrl = screenshotPreviewUrlsRef.current.get(attachment.id);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    screenshotPreviewUrlsRef.current.delete(attachment.id);
    setScreenshots((current) => current.filter((entry) => entry.id !== attachment.id));
  };

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
    setWorkflowGuide(null);
    void api.get(`/case-spaces/${record.id}/workflow-guide`)
      .then((response) => setWorkflowGuide(response.data || null))
      .catch(() => setWorkflowGuide(null));
    try {
      const [statusRes, stateRes] = await Promise.all([
        api.get(`/case-spaces/${record.id}/agent/status`),
        api.get(`/case-spaces/${record.id}/agent/state`),
      ]);
      setStatus(statusRes.data);
      setState(stateRes.data);
      const activeSkill = String(stateRes.data?.active_skill || DEFAULT_AGENT_SKILL);
      const activeAvailable = (statusRes.data?.skills || []).some((item: AgentSkill) => item.id === activeSkill && item.available);
      setSkillId(activeAvailable ? activeSkill : DEFAULT_AGENT_SKILL);
    } catch (error: any) {
      setStatus(null);
      setState(null);
      setWorkflowGuide(null);
      message.error(error?.response?.data?.detail || "智能体会话加载失败");
    } finally {
      setAgentLoading(false);
    }
  };
  useEffect(() => { void loadCases(""); }, []);
  useEffect(() => {
    clearScreenshotPreviews();
    setScreenshots([]);
    if (selected) void loadAgent(selected);
    else { setStatus(null); setState(null); setWorkflowGuide(null); }
  }, [selected?.id]);
  useEffect(() => () => clearScreenshotPreviews(), []);
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ block: "end" }); }, [state?.messages.length]);

  const send = async (preset?: string) => {
    if (!selected) return;
    const content = String(preset ?? input).trim() || (skillId === "screenshot-evidence" && screenshots.length ? "请分析上传的截图证据" : "");
    if (!content) return message.warning("请输入要询问的问题");
    if (sending) activeAgentRequestRef.current?.abort();
    const outgoingScreenshots = [...screenshots];
    const optimisticId = `pending-${Date.now()}`;
    setState((current) => current ? {
      ...current,
      messages: [...(current.messages || []), { id: optimisticId, role: "user", content, attachments: outgoingScreenshots }],
    } : current);
    setInput("");
    setScreenshots([]);
    const controller = new AbortController();
    activeAgentRequestRef.current = controller;
    setSending(true);
    try {
      const { data } = await api.post(`/case-spaces/${selected.id}/agent/messages`, {
        message: encodeAgentSkillMessage(skillId, content),
        attachment_ids: outgoingScreenshots.map((item) => item.id),
      }, { signal: controller.signal });
      setState(stateWithScreenshotPreviews(data));
    } catch (error: any) {
      if (!controller.signal.aborted) {
        setState((current) => current ? { ...current, messages: current.messages.filter((item) => item.id !== optimisticId) } : current);
        setInput(content);
        setScreenshots(outgoingScreenshots);
        message.error(error?.response?.data?.detail || "智能体响应失败");
      }
    } finally {
      if (activeAgentRequestRef.current === controller) {
        activeAgentRequestRef.current = null;
        setSending(false);
      }
    }
  };
  const stopAgentResponse = () => {
    activeAgentRequestRef.current?.abort();
    activeAgentRequestRef.current = null;
    setSending(false);
    message.info("已停止本轮生成，可以继续补充要求");
  };
  const uploadScreenshot = async (file?: File) => {
    if (!file || !selected) return;
    if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) {
      message.error("截图仅支持 PNG、JPG、JPEG 或 WebP");
      return;
    }
    if (file.size > 6 * 1024 * 1024) {
      message.error("单张截图不能超过 6MB");
      return;
    }
    if (screenshots.length >= 4) {
      message.warning("单次最多分析 4 张截图");
      return;
    }
    const form = new FormData();
    form.append("file", file);
    form.append("record_id", String(selected.id));
    form.append("category", "智能体截图证据");
    form.append("remark", "由智能体中心上传，用于截图证据分析");
    setScreenshotUploading(true);
    try {
      const { data } = await api.post("/attachments", form);
      const attachment = data.attachment || data;
      const id = Number(attachment.id);
      const previewUrl = URL.createObjectURL(file);
      screenshotPreviewUrlsRef.current.set(id, previewUrl);
      setScreenshots((current) => [...current, { id, name: String(attachment.original_name || file.name), mime_type: file.type, preview_url: previewUrl }]);
      message.success("截图已加入当前案件空间");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "截图上传失败");
    } finally {
      setScreenshotUploading(false);
      if (screenshotInputRef.current) screenshotInputRef.current.value = "";
    }
  };
  const pasteScreenshot = (event: ClipboardEvent<HTMLTextAreaElement>) => {
    const itemFile = Array.from(event.clipboardData.items)
      .find((item) => item.kind === "file" && item.type.startsWith("image/"))
      ?.getAsFile();
    const file = itemFile || Array.from(event.clipboardData.files).find((item) => item.type.startsWith("image/"));
    if (!file) return;
    event.preventDefault();
    if (skillId !== "screenshot-evidence") setSkillId("screenshot-evidence");
    void uploadScreenshot(file);
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
  const skills = status?.skills || [];
  const selectedSkill = skills.find((item) => item.id === skillId);

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
          <div className="agent-skill-bar">
            <span><RobotOutlined /> 办公技能</span>
            <Select
              value={skillId}
              onChange={setSkillId}
              options={skills.map((item) => ({ value: item.id, label: `${item.name}${item.available ? "" : "（待配置）"}`, disabled: !item.available }))}
              optionRender={(option) => {
                const item = skills.find((skill) => skill.id === option.value);
                return <Tooltip title={item?.available ? item?.description : item?.unavailable_reason}>{option.label}</Tooltip>;
              }}
            />
            <small>{selectedSkill?.description || "选择技能后，LangGraph 会按对应办公流程处理本轮对话"}</small>
          </div>
          {workflowGuide && <section className="agent-standard-workflow" data-testid="case-standard-workflow">
            <div className="agent-standard-workflow-header">
              <span><strong>案件标准化工作台</strong><small>{workflowGuide.manual.name} · {workflowGuide.manual.version}</small></span>
              <Space wrap>
                <Tag color="blue">当前：{workflowGuide.current_phase.name}</Tag>
                <Tag color={workflowGuide.risk_summary.overdue ? "error" : "success"}>逾期 {workflowGuide.risk_summary.overdue}</Tag>
                <Tag color={workflowGuide.risk_summary.missing_required_materials ? "warning" : "success"}>缺材料 {workflowGuide.risk_summary.missing_required_materials}</Tag>
              </Space>
            </div>
            <Tabs size="small" items={[
              {
                key: "phases", label: "案件流程", children: <div className="agent-workflow-phases">{workflowGuide.phases.map((phase) => <div key={phase.code} className={`agent-workflow-phase agent-workflow-phase-${phase.state}`}><CheckCircleOutlined /><span>{phase.name}</span>{phase.target_days ? <small>目标 {phase.target_days} 天</small> : null}</div>)}</div>,
              },
              {
                key: "deadlines", label: `期限提醒 ${workflowGuide.deadlines.length}`, children: <div className="agent-workflow-list">{workflowGuide.deadlines.length ? workflowGuide.deadlines.map((item) => { const meta = deadlineRiskMeta[item.risk]; return <div key={item.code}><ClockCircleOutlined /><span><strong>{item.title}</strong><small>{item.deadline} · {item.owner_role} · {item.source}</small></span><Tag color={meta.color}>{meta.label}</Tag></div>; }) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无已登记期限" />}{workflowGuide.deadline_missing_inputs.length ? <Alert type="warning" showIcon title="期限起算信息待补充" description={workflowGuide.deadline_missing_inputs.join("；")} /> : null}</div>,
              },
              {
                key: "materials", label: "材料清单", children: <div className="agent-workflow-materials"><div className="agent-material-progress"><span>必备材料 {workflowGuide.material_progress.completed}/{workflowGuide.material_progress.required}</span><Progress percent={workflowGuide.material_progress.required ? Math.round(workflowGuide.material_progress.completed / workflowGuide.material_progress.required * 100) : 100} showInfo={false} /></div>{workflowGuide.materials.map((item) => <div key={item.code}><span>{item.name}</span><Tag color={item.status === "uploaded" ? "success" : item.status === "missing" ? "error" : "default"}>{item.status === "uploaded" ? `已上传${item.matched_document_count ? ` ${item.matched_document_count}` : ""}` : item.status === "missing" ? "缺失" : "按需"}</Tag></div>)}</div>,
              },
              {
                key: "roles", label: "岗位任务", children: <div className="agent-workflow-list">{workflowGuide.role_tasks.map((item) => <div key={`${item.role}-${item.task}`}><TeamOutlined /><span><strong>{item.role}{item.owner_name ? ` · ${item.owner_name}` : ""}</strong><small>{item.task}</small></span><Tag color={item.assignment_status === "assigned" ? "success" : "warning"}>{item.assignment_status === "assigned" ? "已明确" : "待指定"}</Tag></div>)}</div>,
              },
              {
                key: "agent-rules", label: "智能体规则", children: <div className="agent-workflow-rules">{workflowGuide.agent_rules.map((rule, index) => <div key={rule}><span>{index + 1}</span><p>{rule}</p></div>)}</div>,
              },
            ]} />
          </section>}
          {pendingActions.length > 0 && <section className="agent-global-actions">
            <Alert type="info" showIcon title="待审批操作不会自动改写业务数据" />
            {pendingActions.map((action) => <div key={action.id}><span><strong>{action.summary}</strong><small>{action.type}</small></span><Space><Button size="small" type="primary" loading={decisionLoading === action.id} onClick={() => void decide(action, "approved")}>批准</Button><Button size="small" danger icon={<CloseOutlined />} onClick={() => void decide(action, "rejected")}>驳回</Button></Space></div>)}
          </section>}
          <div className="agent-global-messages">
            {!agentLoading && !state?.messages?.length && <div className="agent-global-empty"><RobotOutlined /><strong>开始分析当前业务空间</strong><span>回答会综合关联的客户、合同、案件、线索、调查和财务数据。</span></div>}
            {state?.messages?.map((item, index) => <div key={item.id || index} className={`agent-global-message agent-global-message-${item.role}`}><small>{item.role === "user" ? "我" : "智能体"}</small><div>{item.attachments?.length ? <div className="agent-message-attachments">{item.attachments.map((attachment) => attachment.preview_url ? <figure key={attachment.id}><Image src={attachment.preview_url} alt={attachment.name} preview /><figcaption>{attachment.name}</figcaption></figure> : <Tag key={attachment.id}>{attachment.name}</Tag>)}</div> : null}{item.content}</div></div>)}
            {(agentLoading || sending) && <div className="agent-global-loading"><RobotOutlined /> {sending ? "正在分析关联业务数据..." : "正在加载会话..."}</div>}
            <div ref={messagesEndRef} />
          </div>
          {!state?.messages?.length && status?.ready && <div className="agent-global-suggestions">{(selectedSkill?.quick_prompts?.length ? selectedSkill.quick_prompts : ["概括业务空间现状", "检查期限与任务风险"]).map((text) => <Button key={text} size="small" onClick={() => void send(text)}>{text}</Button>)}</div>}
          <div className="agent-global-composer">
            {screenshots.length ? <div className="agent-composer-attachments" aria-label="待发送截图">{screenshots.map((item) => <div key={item.id}><Image src={item.preview_url} alt={item.name} preview /><span title={item.name}>{item.name}</span><Button type="text" icon={<CloseOutlined />} title="移除截图" onClick={() => removeScreenshot(item)} /></div>)}</div> : null}
            <input ref={screenshotInputRef} hidden type="file" accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp" onChange={(event) => void uploadScreenshot(event.target.files?.[0])} />
            <Button className="agent-composer-upload" type="text" icon={<PaperClipOutlined />} title="上传截图" loading={screenshotUploading} disabled={!status?.ready || screenshots.length >= 4} onClick={() => screenshotInputRef.current?.click()} />
            <Input.TextArea value={input} autoSize={{ minRows: 2, maxRows: 5 }} placeholder={skillId === "screenshot-evidence" ? "可直接粘贴截图，并补充需要核验的问题" : "询问当前空间的业务信息，可直接粘贴截图"} disabled={!status?.ready} onChange={(event) => setInput(event.target.value)} onPaste={pasteScreenshot} onPressEnter={(event) => { if (!event.shiftKey) { event.preventDefault(); void send(); } }} /><Button type="primary" icon={sending && !input.trim() && !screenshots.length ? <StopOutlined /> : <SendOutlined />} title={sending && !input.trim() && !screenshots.length ? "停止生成" : sending ? "发送引导并打断当前生成" : "发送"} disabled={!status?.ready || (!sending && !input.trim() && !screenshots.length)} onClick={() => sending && !input.trim() && !screenshots.length ? stopAgentResponse() : void send()} />
          </div>
        </>}
      </main>
    </div>
  </div>;
}
