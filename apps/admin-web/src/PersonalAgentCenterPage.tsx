import { useEffect, useRef, useState, type ReactNode } from "react";
import { Alert, Button, Input, Modal, Segmented, Select, Skeleton, Space, Tag, Tooltip, message } from "antd";
import { AppstoreAddOutlined, ArrowDownOutlined, ArrowUpOutlined, AuditOutlined, BulbOutlined, CheckOutlined, CloseOutlined, FileTextOutlined, FolderOpenOutlined, LockOutlined, PaperClipOutlined, ReloadOutlined, RobotOutlined, ScheduleOutlined, StopOutlined, TeamOutlined, ThunderboltOutlined, WalletOutlined } from "@ant-design/icons";
import { AgentOperationPreview, agentOperationName, hasAgentOperationPreview } from "./AgentOperationPreview";
import { AgentToolRequests } from "./AgentToolRequests";
import { AgentToolResult } from "./AgentToolResult";
import { CaseMaterialsPicker } from "./personal-agent/CaseMaterialsPicker";
import { SkillManager } from "./personal-agent/SkillManager";
import { MaterialPreview } from "./personal-agent/MaterialPreview";
import { WorkPanel } from "./personal-agent/WorkPanel";
import { ConversationMessage } from "./personal-agent/ConversationMessage";
import { MATERIAL_ACCEPT, usePersonalWorkspace } from "./personal-agent/usePersonalWorkspace";
import { errorText, type Material, type PendingAction, type ResponseMode, type WorkspaceCommand } from "./personal-agent/types";
import "./personal-agent-center.css";

const commandIcons: Record<string, ReactNode> = { today: <ScheduleOutlined />, task: <CheckOutlined />, approval: <AuditOutlined />, case: <FolderOpenOutlined />, finance: <WalletOutlined />, seal: <FileTextOutlined />, customer: <TeamOutlined /> };

export default function PersonalAgentCenterPage({ onNavigate }: { onNavigate: (route: string) => void }) {
  const workspace = usePersonalWorkspace();
  const { status, state, skills, skillId, input, loading, sending, uploading, selectedCase } = workspace;
  const [view, setView] = useState<"workspace" | "chat">("workspace");
  const [refreshToken, setRefreshToken] = useState(0);
  const [skillsOpen, setSkillsOpen] = useState(false);
  const [pickerMode, setPickerMode] = useState<"case" | "materials" | null>(null);
  const [follow, setFollow] = useState(true);
  const [dragging, setDragging] = useState(false);
  const [previewMaterial, setPreviewMaterial] = useState<Material | null>(null);
  const [activeAction, setActiveAction] = useState<PendingAction | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const canUseCases = status?.commands.some((item) => item.id === "cases");
  const busy = loading || sending || uploading || !!workspace.decisionId;
  useEffect(() => { if (follow) bottomRef.current?.scrollIntoView({ block: "end" }); }, [state.messages, follow, view]);
  const showAssistant = () => { if (window.matchMedia("(max-width: 1100px)").matches) setView("chat"); };
  const prepare = (command: WorkspaceCommand) => { workspace.setSkillId(command.skill_id); workspace.setInput(command.prompt); showAssistant(); };
  const draft = () => { workspace.setSkillId("general-office"); workspace.setInput("根据我提供的材料起草一份办公文档，缺失信息标为待补充"); showAssistant(); };
  const copy = (value: string) => {
    // 现有 OA 使用 HTTP，采用允许用户点击触发的浏览器复制命令。
    const selection = document.createElement("textarea");
    const focused = document.activeElement as HTMLElement | null;
    selection.value = value;
    selection.style.position = "fixed";
    selection.style.top = "-9999px";
    document.body.appendChild(selection);
    try { selection.select(); if (!document.execCommand("copy")) throw new Error("浏览器未允许复制"); message.success("已复制"); }
    catch (error) { message.error(errorText(error, "复制失败")); }
    finally { selection.remove(); focused?.focus(); }
  };
  const openSkills = async () => {
    setSkillsOpen(true);
    try { await workspace.refreshSkills(); }
    catch (error) { message.error(errorText(error, "技能加载失败")); }
  };
  return <div className="personal-agent-page" data-testid="personal-agent-center-page">
    <header className="personal-agent-header">
      <div className="personal-agent-title"><div className="workspace-brand-icon"><RobotOutlined /></div><h2>智能体中心</h2><span>律所工作台</span></div>
      <Space className="workspace-header-actions" size={8}>
        <Segmented aria-label="切换工作视图" value={view} options={[{ value: "workspace", label: "工作台" }, { value: "chat", label: "对话" }]} onChange={(value) => setView(value as "workspace" | "chat")} />
        <Tooltip title={status?.ready ? `当前模型：${status.model}` : "模型服务未就绪"}><span className={`workspace-service ${status?.ready ? "ready" : ""}`}><i />{status?.ready ? "已连接" : loading ? "连接中" : "未就绪"}</span></Tooltip>
        {canUseCases && <Button className="workspace-case-link" size="small" icon={<FolderOpenOutlined />} onClick={() => onNavigate("case-agent-center")}>案件智能体</Button>}
        <Tooltip title="刷新工作台与会话"><Button type="text" icon={<ReloadOutlined />} aria-label="刷新工作台与会话" disabled={busy} onClick={() => { setRefreshToken((value) => value + 1); void workspace.load(); }} /></Tooltip>
      </Space>
    </header>
    {workspace.loadError && <Alert type="error" showIcon title={workspace.loadError} />}
    {!loading && !workspace.loadError && !status?.ready && <Alert type="warning" showIcon title="模型服务未就绪，请检查系统模型配置" />}
    <div className="personal-agent-layout" data-view={view}>
      <WorkPanel status={status} skills={skills} busy={busy} refreshToken={refreshToken} decisionResult={workspace.decisionResult} onNavigate={onNavigate} onPrepare={prepare} onSkill={(skill) => { workspace.setSkillId(skill.id); if (skill.quick_prompts?.[0]) workspace.setInput(skill.quick_prompts[0]); showAssistant(); }} onUpload={() => { showAssistant(); fileRef.current?.click(); }} onSkills={() => void openSkills()} onDraft={draft} />
      <main className="personal-agent-chat">
        <div className="workspace-thread-heading"><div className="workspace-assistant-title"><span><RobotOutlined /> 办公助手</span><Tooltip title="仅当前账号可见的会话"><small><LockOutlined /> 个人会话</small></Tooltip></div><Space>{selectedCase && <Tooltip title={selectedCase.title}><span className="workspace-current-case"><FolderOpenOutlined /> {selectedCase.serial_no}</span></Tooltip>}<AgentToolRequests buttonLabel="操作记录" titlePrefix="智能体" /></Space></div>
        <div ref={scrollRef} className="personal-agent-messages" onScroll={() => { const element = scrollRef.current; if (element) setFollow(element.scrollHeight - element.scrollTop - element.clientHeight < 100); }}>
          <div className="workspace-thread">
            {loading ? <Skeleton active paragraph={{ rows: 4 }} /> : !state.messages.length && <div className="workspace-empty"><div className="workspace-empty-symbol"><RobotOutlined /></div><h3>开始今天的工作</h3><div className="workspace-start-actions">{status?.commands.slice(0, 4).map((command) => <button key={command.id} onClick={() => prepare(command)}>{commandIcons[command.icon]}<span>{command.label}</span><ArrowUpOutlined /></button>)}</div></div>}
            {state.messages.map((item, index) => <ConversationMessage key={`${item.created_at || "message"}-${index}`} item={item} generating={sending && index === state.messages.length - 1} readingMaterials={!!(workspace.materials.length + workspace.caseMaterials.length)} progress={workspace.progress} saved={!!workspace.savedDocuments[index]} busy={busy} onCopy={copy} onPreview={setPreviewMaterial} onSave={() => workspace.saveWord(item, index)} />)}
            <AgentToolResult result={[state.structured_results, workspace.decisionResult]} />
            <div ref={bottomRef} />
          </div>
          {!follow && <div className="workspace-scroll-bottom-wrap"><Button className="workspace-scroll-bottom" shape="circle" icon={<ArrowDownOutlined />} aria-label="查看最新回答" onClick={() => { setFollow(true); bottomRef.current?.scrollIntoView({ block: "end", behavior: "smooth" }); }} /></div>}
        </div>
        {!!state.pending_actions.length && <div className="workspace-pending"><div className="workspace-section-heading"><b><AuditOutlined /> 待确认操作</b><Tag>{state.pending_actions.length}</Tag></div>{state.pending_actions.filter((action) => action.status === "pending").map((action) => <div className="workspace-pending-row" key={action.id}><div><b>{agentOperationName(action)}</b><p>{action.summary}</p></div><Button size="small" type="primary" icon={<CheckOutlined />} disabled={busy} onClick={() => setActiveAction(action)}>查看并确认</Button></div>)}</div>}
        <div className="personal-agent-composer-wrap">
          <div className={`personal-agent-composer${dragging ? " dragging" : ""}`} onDragOver={(event) => { if (event.dataTransfer.types.includes("Files")) { event.preventDefault(); setDragging(true); } }} onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node)) setDragging(false); }} onDrop={(event) => { event.preventDefault(); setDragging(false); void workspace.upload(Array.from(event.dataTransfer.files)); }}>
            <div className="workspace-composer-context"><Select aria-label="选择办公技能" value={skillId} disabled={busy} onChange={workspace.setSkillId} popupMatchSelectWidth={300} options={skills.map((item) => ({ value: item.id, label: item.name, disabled: !item.available, title: item.description }))} />{status?.supports_response_modes && <Tooltip title="快速用于日常办公查询；深度用于复杂分析">
              <Segmented size="small" aria-label="回答模式" value={workspace.responseMode} disabled={busy} options={[{ value: "fast", label: "快速", icon: <ThunderboltOutlined /> }, { value: "deep", label: "深度", icon: <BulbOutlined /> }]} onChange={(value) => workspace.setResponseMode(value as ResponseMode)} />
            </Tooltip>}{canUseCases && <Tooltip title={selectedCase?.title || "选择本轮问题关联的案件"}><Button type="text" size="small" icon={<FolderOpenOutlined />} disabled={busy} onClick={() => setPickerMode("case")}>{selectedCase?.serial_no || "关联案件"}</Button></Tooltip>}</div>
            {(!!workspace.materials.length || !!workspace.caseMaterials.length) && <div className="workspace-selected-files">{[...workspace.materials.map((item) => ({ ...item, source: "upload" })), ...workspace.caseMaterials.map((item) => ({ ...item, source: "case" }))].map((item) => <div className="workspace-file-chip" key={`${item.source}-${item.id}`}><FileTextOutlined /><Tooltip title={item.name}><button className="workspace-file-name" onClick={() => setPreviewMaterial(item)}>{item.name}</button></Tooltip><Tooltip title="移除材料"><Button type="text" size="small" icon={<CloseOutlined />} aria-label={`移除${item.name}`} disabled={busy} onClick={() => item.source === "upload" ? workspace.setMaterials((current) => current.filter((file) => file.id !== item.id)) : workspace.setCaseMaterials((current) => current.filter((file) => file.id !== item.id))} /></Tooltip></div>)}</div>}
            <Input.TextArea value={input} maxLength={8000} onChange={(event) => workspace.setInput(event.target.value)} disabled={sending || loading} variant="borderless" autoSize={{ minRows: 1, maxRows: 5 }} placeholder="安排工作、查询待办，或结合材料提问…" onPressEnter={(event) => { if (!event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); setFollow(true); void workspace.send(); } }} onPaste={(event) => { const files = Array.from(event.clipboardData.files); if (files.length) { event.preventDefault(); void workspace.upload(files); } }} />
            <div className="workspace-composer-tools"><Space size={2}>
              <input ref={fileRef} hidden type="file" multiple accept={MATERIAL_ACCEPT} onChange={(event) => { void workspace.upload(Array.from(event.target.files || [])); event.target.value = ""; }} />
              <Tooltip title="上传文件"><Button type="text" icon={<PaperClipOutlined />} aria-label="上传文件" loading={uploading} disabled={busy} onClick={() => fileRef.current?.click()} /></Tooltip>
              {selectedCase && <Tooltip title="从案件文件夹选择材料"><Button type="text" icon={<FolderOpenOutlined />} aria-label="选择案件材料" disabled={busy} onClick={() => setPickerMode("materials")} /></Tooltip>}
              <Tooltip title="管理和上传技能"><Button type="text" icon={<AppstoreAddOutlined />} aria-label="管理技能" disabled={busy} onClick={() => void openSkills()} /></Tooltip>
            </Space><div className="workspace-send-area">{uploading && <span>正在上传</span>}{sending ? <Tooltip title="停止生成"><Button danger type="text" icon={<StopOutlined />} aria-label="停止生成" onClick={workspace.stop} /></Tooltip> : <Tooltip title="发送"><Button type="primary" icon={<ArrowUpOutlined />} aria-label="发送" disabled={busy || !input.trim() || !status?.ready || !!workspace.loadError} onClick={() => { setFollow(true); void workspace.send(); }} /></Tooltip>}</div></div>
          </div>
        </div>
      </main>
    </div>
    <SkillManager open={skillsOpen} onClose={() => setSkillsOpen(false)} skills={skills} refresh={workspace.refreshSkills} onSelect={workspace.setSkillId} />
    <Modal open={!!activeAction} title="智能体操作确认" width={760} maskClosable={!workspace.decisionId} onCancel={() => { if (!workspace.decisionId) setActiveAction(null); }} footer={activeAction && <Space><Button icon={<CloseOutlined />} disabled={!!workspace.decisionId} onClick={async () => { if (await workspace.decide(activeAction, "rejected")) setActiveAction(null); }}>取消操作</Button><Button type="primary" icon={<CheckOutlined />} loading={!!workspace.decisionId} disabled={!!workspace.decisionId || !hasAgentOperationPreview(activeAction)} onClick={async () => { if (await workspace.decide(activeAction, "approved")) setActiveAction(null); }}>确认并执行</Button></Space>}>
      {activeAction && <div style={{ maxHeight: "60dvh", overflowY: "auto" }}><AgentOperationPreview action={activeAction} /></div>}
    </Modal>
    <MaterialPreview item={previewMaterial} onClose={() => setPreviewMaterial(null)} />
    <CaseMaterialsPicker mode={pickerMode} onClose={() => setPickerMode(null)} selectedCase={selectedCase} onCase={workspace.chooseCase} selectedMaterials={workspace.caseMaterials} onMaterials={workspace.setCaseMaterials} privateCount={workspace.materials.length} />
  </div>;
}
