import { useEffect, useMemo, useRef, useState, type ClipboardEvent } from "react";
import { Button, Empty, Form, Image, Input, List, message, Modal, Select, Space, Spin, Switch, Tag } from "antd";
import { AppstoreAddOutlined, CheckCircleOutlined, CloseOutlined, DeleteOutlined, EditOutlined, PaperClipOutlined, ReloadOutlined, RobotOutlined, SendOutlined, StopOutlined, UploadOutlined } from "@ant-design/icons";
import { api } from "./api";
import { DEFAULT_AGENT_SKILL, encodeAgentSkillMessage, type AgentSkill } from "./agentSkillRouting";
import "./agent-center.css";

type CaseOption = { id: number; serial_no: string; title: string; customer: string; status: string };
type AgentAttachment = { id: number; name: string; mime_type?: string; preview_url?: string };
type AgentMessage = { id?: string; role: "user" | "assistant"; content: string; created_at?: string; attachments?: AgentAttachment[] };
type AgentActionPreview = { target?: string; changes?: { field: string; before: unknown; after: unknown }[]; create?: Record<string, unknown> };
type AgentAction = { id: string; type: string; summary: string; payload?: Record<string, unknown>; preview?: AgentActionPreview; status: "pending" | "approved" | "rejected" };
type AgentState = { messages: AgentMessage[]; pending_actions: AgentAction[]; active_skill?: string };
type AgentStatus = { ready: boolean; model: string; checkpoint_backend: string; write_requires_approval: boolean; skills?: AgentSkill[] };
type CustomAgentSkill = AgentSkill & { custom?: boolean; enabled?: boolean; instruction?: string };
type WorkflowPhase = { code: string; name: string; state: "completed" | "current" | "pending"; target_days?: number | null };
type WorkflowGuide = { phases: WorkflowPhase[] };
const PHASE_SHORT_NAMES: Record<string, string> = {
  "document-preparation": "文书",
  "customer-seal": "盖章",
  "waiting-filing": "待立案",
  "supplement-evidence": "补取证",
  filing: "提立案",
  "first-instance": "一审",
  "second-instance": "二审",
  retrial: "再审",
  enforcement: "执行",
  archive: "归档",
};
const ACTION_TYPE_NAMES: Record<string, string> = {
  "case.update": "修改案件字段",
  "case.data.update": "修改案件信息",
  "case.task.create": "新建案件任务",
  "case.reminder.create": "新建期限提醒",
  "customer.update": "修改客户资料",
  "contract.update": "修改合同资料",
};
const ACTION_FIELD_NAMES: Record<string, string> = {
  title: "名称", customer: "客户", status: "状态", description: "说明",
  court: "法院", first_instance_court: "一审法院", first_instance_case_no: "一审案号",
  second_instance_court: "二审法院", second_instance_case_no: "二审案号",
  cause_or_charge: "案由", case_stage: "案件阶段", filing_date: "立案日期",
  acceptance_date: "受理日期", judgment_date: "判决日期", effective_date: "生效日期",
  archive_no: "档案号", paper_archive_location: "纸质档案位置", client_position: "客户诉讼地位",
  owner: "负责人", deadline: "截止日期", reminder_date: "提醒日期", priority: "优先级", content: "提醒内容",
};
const actionValue = (value: unknown) => value === null || value === undefined || value === "" ? "—" : typeof value === "object" ? JSON.stringify(value, null, 2) : String(value);
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
  const [skillManagerOpen, setSkillManagerOpen] = useState(false);
  const [skillSaving, setSkillSaving] = useState(false);
  const [editingSkillId, setEditingSkillId] = useState("");
  const [skillForm] = Form.useForm();
  const [screenshots, setScreenshots] = useState<AgentAttachment[]>([]);
  const [screenshotUploading, setScreenshotUploading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const screenshotInputRef = useRef<HTMLInputElement>(null);
  const skillFileInputRef = useRef<HTMLInputElement>(null);
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
        skill_id: skillId,
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
      message.success(decision === "approved" ? "操作已批准并写入系统" : "操作已驳回，系统数据未修改");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "审批失败");
    } finally {
      setDecisionLoading("");
    }
  };
  const refreshSkillCatalog = async () => {
    const { data } = await api.get("/agent/skills");
    const items = (data.items || []) as CustomAgentSkill[];
    setStatus((current) => current ? { ...current, skills: items } : current);
    if (!items.some((item) => item.id === skillId && item.available)) setSkillId(DEFAULT_AGENT_SKILL);
    return items;
  };
  const openSkillManager = async () => {
    setSkillManagerOpen(true);
    try { await refreshSkillCatalog(); } catch (error: any) { message.error(error?.response?.data?.detail || "技能库加载失败"); }
  };
  const resetSkillEditor = () => {
    setEditingSkillId("");
    skillForm.resetFields();
  };
  const editSkill = (skill: CustomAgentSkill) => {
    setEditingSkillId(skill.id);
    skillForm.setFieldsValue({
      name: skill.name,
      category: skill.category,
      description: skill.description,
      instruction: skill.instruction || "",
      quick_prompts: (skill.quick_prompts || []).join("\n"),
    });
  };
  const saveSkill = async (values: Record<string, string>) => {
    setSkillSaving(true);
    const payload = {
      ...values,
      quick_prompts: String(values.quick_prompts || "").split(/\r?\n/).map((item) => item.trim()).filter(Boolean),
    };
    try {
      if (editingSkillId) await api.patch(`/agent/skills/${editingSkillId}`, payload);
      else await api.post("/agent/skills", payload);
      await refreshSkillCatalog();
      resetSkillEditor();
      message.success(editingSkillId ? "技能已更新" : "技能已添加");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "技能保存失败");
    } finally { setSkillSaving(false); }
  };
  const uploadSkill = async (file?: File) => {
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    setSkillSaving(true);
    try {
      const { data } = await api.post("/agent/skills/upload", form);
      await refreshSkillCatalog();
      setSkillId(data.id);
      message.success("技能已上传并选中");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "技能上传失败");
    } finally {
      setSkillSaving(false);
      if (skillFileInputRef.current) skillFileInputRef.current.value = "";
    }
  };
  const toggleSkill = async (skill: CustomAgentSkill, enabled: boolean) => {
    try {
      await api.patch(`/agent/skills/${skill.id}`, { enabled });
      await refreshSkillCatalog();
      message.success(enabled ? "技能已启用" : "技能已停用");
    } catch (error: any) { message.error(error?.response?.data?.detail || "技能状态更新失败"); }
  };
  const deleteSkill = (skill: CustomAgentSkill) => {
    Modal.confirm({
      title: `删除技能“${skill.name}”？`,
      content: "删除后不会影响既有聊天记录。",
      okText: "删除",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onOk: async () => {
        await api.delete(`/agent/skills/${skill.id}`);
        await refreshSkillCatalog();
        if (editingSkillId === skill.id) resetSkillEditor();
        message.success("技能已删除");
      },
    });
  };
  const pendingActions = useMemo(() => (state?.pending_actions || []).filter((item) => item.status === "pending"), [state]);
  const activeAction = pendingActions[0] || null;
  const skills = (status?.skills || []) as CustomAgentSkill[];
  const selectedSkill = skills.find((item) => item.id === skillId);

  return <div className="agent-center-page" data-testid="agent-center-page">
    <header className="agent-center-header">
      <div><h2>智能体中心</h2><span>统一业务空间</span></div>
      <Space wrap><Tag>客户</Tag><Tag>合同</Tag><Tag>案件</Tag><Tag>线索</Tag><Tag>调查</Tag><Tag>财务</Tag></Space>
    </header>
    <Modal open={skillManagerOpen} title="我的技能" width={760} footer={null} onCancel={() => { setSkillManagerOpen(false); resetSkillEditor(); }}>
      <div className="agent-skill-manager" data-testid="agent-skill-manager">
        <div className="agent-skill-list">
          <div className="agent-skill-list-head">
            <strong>自定义技能</strong>
            <Space>
              <input ref={skillFileInputRef} hidden type="file" accept=".json,.md,.markdown,.docx,application/json,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={(event) => void uploadSkill(event.target.files?.[0])} />
              <Button icon={<UploadOutlined />} title="支持 JSON、Markdown 和 Word（.docx），Word 将自动转为 Markdown" loading={skillSaving} onClick={() => skillFileInputRef.current?.click()}>上传</Button>
              <Button type="primary" icon={<AppstoreAddOutlined />} onClick={resetSkillEditor}>新增</Button>
            </Space>
          </div>
          {skills.filter((item) => item.custom).length ? skills.filter((item) => item.custom).map((skill) => <div className="agent-skill-row" key={skill.id}>
            <div><strong>{skill.name}</strong><span>{skill.description}</span><small>{skill.category}</small></div>
            <Space>
              <Switch size="small" checked={skill.available} onChange={(checked) => void toggleSkill(skill, checked)} />
              <Button type="text" icon={<EditOutlined />} title="编辑技能" onClick={() => editSkill(skill)} />
              <Button type="text" danger icon={<DeleteOutlined />} title="删除技能" onClick={() => deleteSkill(skill)} />
            </Space>
          </div>) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无自定义技能" />}
        </div>
        <Form form={skillForm} layout="vertical" className="agent-skill-form" onFinish={(values) => void saveSkill(values)}>
          <div className="agent-skill-form-title"><strong>{editingSkillId ? "编辑技能" : "新增技能"}</strong>{editingSkillId ? <Button type="link" onClick={resetSkillEditor}>取消编辑</Button> : null}</div>
          <div className="agent-skill-form-grid">
            <Form.Item label="技能名称" name="name" rules={[{ required: true, min: 2, max: 64 }]}><Input /></Form.Item>
            <Form.Item label="分类" name="category" initialValue="自定义" rules={[{ required: true, max: 32 }]}><Input /></Form.Item>
          </div>
          <Form.Item label="说明" name="description" rules={[{ required: true, min: 2, max: 500 }]}><Input /></Form.Item>
          <Form.Item label="技能指令" name="instruction" rules={[{ required: true, min: 10, max: 6000 }]}><Input.TextArea autoSize={{ minRows: 5, maxRows: 10 }} /></Form.Item>
          <Form.Item label="快捷指令" name="quick_prompts"><Input.TextArea autoSize={{ minRows: 2, maxRows: 4 }} /></Form.Item>
          <Button type="primary" htmlType="submit" loading={skillSaving}>{editingSkillId ? "保存修改" : "添加技能"}</Button>
        </Form>
      </div>
    </Modal>
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
            {workflowGuide?.phases?.length ? <div className="agent-phase-strip" data-testid="case-phase-strip">
              {workflowGuide.phases.map((phase) => <div key={phase.code} title={phase.target_days ? `${phase.name} · 目标 ${phase.target_days} 天` : phase.name} className={`agent-phase-strip-item agent-phase-strip-${phase.state}`}>
                <CheckCircleOutlined />
                <span>{PHASE_SHORT_NAMES[phase.code] || phase.name}</span>
              </div>)}
            </div> : <div className="agent-phase-strip-placeholder" />}
            <Space wrap><Tag color={status?.ready ? "success" : "warning"}>{status?.ready ? "服务正常" : "服务未就绪"}</Tag><Tag>{status?.model || "模型未配置"}</Tag><Tag color="blue">已关联业务数据</Tag><Tag color="gold">人工审批</Tag></Space>
          </div>
          <Modal
            open={Boolean(activeAction)}
            title="智能体操作审批"
            closable={false}
            maskClosable={false}
            width={680}
            footer={activeAction ? [
              <Button key="reject" danger icon={<CloseOutlined />} disabled={Boolean(decisionLoading)} onClick={() => void decide(activeAction, "rejected")}>驳回，不修改</Button>,
              <Button key="approve" type="primary" loading={decisionLoading === activeAction.id} onClick={() => void decide(activeAction, "approved")}>批准并执行</Button>,
            ] : null}
          >
            {activeAction ? <div className="agent-action-approval" data-testid="agent-action-approval">
              <div className="agent-action-summary"><Tag color="processing">{ACTION_TYPE_NAMES[activeAction.type] || activeAction.type}</Tag><strong>{activeAction.summary}</strong><small>目标：{activeAction.preview?.target || selected.serial_no}</small></div>
              <div className="agent-action-warning">操作权限继承当前账号原有业务权限。批准后将立即写入系统并记录操作日志；驳回不会修改任何数据。</div>
              {activeAction.preview?.changes?.length ? <div className="agent-action-changes">
                <div className="agent-action-change-head"><span>字段</span><span>修改前</span><span>修改后</span></div>
                {activeAction.preview.changes.map((change) => <div key={change.field}><strong>{ACTION_FIELD_NAMES[change.field] || change.field}</strong><span>{actionValue(change.before)}</span><span>{actionValue(change.after)}</span></div>)}
              </div> : null}
              {activeAction.preview?.create ? <div className="agent-action-create">
                {Object.entries(activeAction.preview.create).map(([field, value]) => <div key={field}><strong>{ACTION_FIELD_NAMES[field] || field}</strong><span>{actionValue(value)}</span></div>)}
              </div> : null}
            </div> : null}
          </Modal>
          <div className="agent-global-messages">
            {!agentLoading && !state?.messages?.length && <div className="agent-global-empty"><RobotOutlined /><strong>开始分析当前业务空间</strong><span>回答会综合关联的客户、合同、案件、线索、调查和财务数据。</span></div>}
            {state?.messages?.map((item, index) => <div key={item.id || index} className={`agent-global-message agent-global-message-${item.role}`}><small>{item.role === "user" ? "我" : "智能体"}</small><div>{item.attachments?.length ? <div className="agent-message-attachments">{item.attachments.map((attachment) => attachment.preview_url ? <figure key={attachment.id}><Image src={attachment.preview_url} alt={attachment.name} preview /><figcaption>{attachment.name}</figcaption></figure> : <Tag key={attachment.id}>{attachment.name}</Tag>)}</div> : null}{item.content}</div></div>)}
            {(agentLoading || sending) && <div className="agent-global-loading"><RobotOutlined /> {sending ? "正在分析关联业务数据..." : "正在加载会话..."}</div>}
            <div ref={messagesEndRef} />
          </div>
          {!state?.messages?.length && status?.ready && <div className="agent-global-suggestions">{(selectedSkill?.quick_prompts?.length ? selectedSkill.quick_prompts : ["概括业务空间现状", "检查期限与任务风险"]).map((text) => <Button key={text} size="small" onClick={() => void send(text)}>{text}</Button>)}</div>}
          <div className="agent-global-composer">
            <div className="agent-composer-skill">
              <Select
                value={skillId}
                onChange={setSkillId}
                options={skills.map((skill) => ({ value: skill.id, label: skill.custom ? `${skill.name} · 我的` : skill.name, disabled: !skill.available }))}
                popupMatchSelectWidth={false}
              />
              <Button type="text" icon={<AppstoreAddOutlined />} title="管理我的技能" onClick={() => void openSkillManager()} />
            </div>
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
