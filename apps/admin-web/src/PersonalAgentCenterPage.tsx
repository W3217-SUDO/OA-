import { useEffect, useRef, useState, type ReactNode } from "react";
import { Alert, Button, Drawer, Input, Modal, Select, Skeleton, Space, Tag, Tooltip, message } from "antd";
import { AppstoreAddOutlined, ArrowDownOutlined, ArrowUpOutlined, AuditOutlined, CheckOutlined, CloseOutlined, CopyOutlined, FileTextOutlined, FileWordOutlined, FolderOpenOutlined, LockOutlined, MenuOutlined, PaperClipOutlined, ReloadOutlined, RobotOutlined, ScheduleOutlined, StopOutlined, TeamOutlined, WalletOutlined } from "@ant-design/icons";
import { AgentMessageContent } from "./AgentMessageContent";
import { AgentOperationPreview, agentOperationName, hasAgentOperationPreview } from "./AgentOperationPreview";
import { AgentToolRequests } from "./AgentToolRequests";
import { AgentToolResult } from "./AgentToolResult";
import { CaseMaterialsPicker } from "./personal-agent/CaseMaterialsPicker";
import { SkillManager } from "./personal-agent/SkillManager";
import { MaterialPreview } from "./personal-agent/MaterialPreview";
import { MATERIAL_ACCEPT, usePersonalWorkspace } from "./personal-agent/usePersonalWorkspace";
import { errorText, type Material, type PendingAction, type WorkspaceCommand } from "./personal-agent/types";
import "./personal-agent-center.css";

const commandIcons: Record<string, ReactNode> = { today: <ScheduleOutlined />, task: <CheckOutlined />, approval: <AuditOutlined />, case: <FolderOpenOutlined />, finance: <WalletOutlined />, seal: <FileTextOutlined />, customer: <TeamOutlined /> };
const formatTime = (value?: string) => value ? new Date(value).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }) : "";

export default function PersonalAgentCenterPage() {
  const workspace = usePersonalWorkspace();
  const { status, state, skills, skillId, input, loading, sending, uploading, selectedCase } = workspace;
  const [sidebarOpen, setSidebarOpen] = useState(false);
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
  useEffect(() => { if (follow) bottomRef.current?.scrollIntoView({ block: "end" }); }, [state.messages, follow]);
  const prepare = (command: WorkspaceCommand) => { workspace.setSkillId(command.skill_id); workspace.setInput(command.prompt); setSidebarOpen(false); };
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
  const sidebar = <>
    <div className="workspace-user"><div className="workspace-user-avatar"><TeamOutlined /></div><div><strong>{status?.identity.display_name || "当前用户"}</strong><span>{[status?.identity.department, status?.identity.permission_role || status?.identity.staff_role || status?.identity.position || status?.identity.role].filter(Boolean).join(" · ")}</span></div></div>
    <div className="workspace-nav-label">我的工作</div>
    <nav className="workspace-work-nav">{status?.commands.map((command) => <button key={command.id} disabled={busy} onClick={() => prepare(command)}>{commandIcons[command.icon]}<span>{command.label}</span></button>)}</nav>
    <div className="workspace-nav-label workspace-tools-label">办公工具</div>
    <nav className="workspace-work-nav">
      <button disabled={busy} onClick={() => { workspace.setSkillId("pdf-review"); setSidebarOpen(false); fileRef.current?.click(); }}><PaperClipOutlined /><span>材料审阅</span></button>
      <button disabled={busy} onClick={() => { workspace.setSkillId("general-office"); workspace.setInput("根据我提供的材料起草一份办公文档，缺失信息标为待补充"); setSidebarOpen(false); }}><FileWordOutlined /><span>文档起草</span></button>
      <button disabled={busy} onClick={() => void openSkills()}><AppstoreAddOutlined /><span>我的技能</span><small>{skills.filter((item) => item.custom).length || ""}</small></button>
    </nav>
    <div className="workspace-private-label"><LockOutlined /> 私人办公会话</div>
  </>;
  return <div className="personal-agent-page" data-testid="personal-agent-center-page">
    <header className="personal-agent-header">
      <div className="personal-agent-title"><Button className="workspace-mobile-menu" type="text" icon={<MenuOutlined />} aria-label="打开工作菜单" onClick={() => setSidebarOpen(true)} /><RobotOutlined /><h2>智能体中心</h2><span>律所工作台</span></div>
      <Space size={6}>
        <Tooltip title={status?.ready ? `当前模型：${status.model}` : "模型服务未就绪"}><span className={`workspace-service ${status?.ready ? "ready" : ""}`}><i />{status?.ready ? "已连接" : loading ? "连接中" : "未就绪"}</span></Tooltip>
        {canUseCases && <Button className="workspace-case-link" size="small" icon={<FolderOpenOutlined />} onClick={() => { window.location.href = "?page=case-agent-center"; }}>案件智能体</Button>}
        <Tooltip title="刷新会话"><Button type="text" icon={<ReloadOutlined />} aria-label="刷新会话" disabled={busy} onClick={() => void workspace.load()} /></Tooltip>
      </Space>
    </header>
    {workspace.loadError && <Alert type="error" showIcon title={workspace.loadError} />}
    {!loading && !workspace.loadError && !status?.ready && <Alert type="warning" showIcon title="模型服务未就绪，请检查系统模型配置" />}
    <div className="personal-agent-layout">
      <aside className="personal-agent-sidebar">{loading ? <Skeleton active paragraph={{ rows: 5 }} /> : sidebar}</aside>
      <main className="personal-agent-chat">
        <div className="workspace-thread-heading"><span><LockOutlined /> 办公对话</span><Space>{selectedCase && <span className="workspace-current-case"><FolderOpenOutlined /> {selectedCase.serial_no}</span>}<AgentToolRequests buttonLabel="操作记录" titlePrefix="智能体" /></Space></div>
        <div ref={scrollRef} className="personal-agent-messages" onScroll={() => { const element = scrollRef.current; if (element) setFollow(element.scrollHeight - element.scrollTop - element.clientHeight < 100); }}>
          <div className="workspace-thread">
            {loading ? <Skeleton active paragraph={{ rows: 4 }} /> : !state.messages.length && <div className="workspace-empty"><div className="workspace-empty-symbol"><RobotOutlined /></div><h3>开始今天的工作</h3><div className="workspace-start-actions">{status?.commands.slice(0, 4).map((command) => <button key={command.id} onClick={() => prepare(command)}>{commandIcons[command.icon]}<span>{command.label}</span><ArrowUpOutlined /></button>)}</div></div>}
            {state.messages.map((item, index) => <article key={`${item.created_at || "message"}-${index}`} className={`personal-message ${item.role}${item.failed ? " failed" : ""}`}>
              <div className="workspace-message-heading"><span>{item.role === "user" ? "我" : <><RobotOutlined /> 智能体</>}</span><time>{formatTime(item.created_at)}</time>{item.role === "assistant" && item.skill_name && <small>{item.skill_name}</small>}</div>
              <div className="workspace-message-body">{item.role === "assistant" ? item.content ? <AgentMessageContent content={item.content} /> : <span className="workspace-thinking">{sending ? workspace.materials.length + workspace.caseMaterials.length ? "正在读取材料并处理问题…" : "正在处理…" : "未收到回答"}</span> : <div className="workspace-user-content">{item.content}</div>}</div>
              {!!item.attachments?.length && <div className="workspace-message-files">{item.attachments.map((file) => <button key={file.id} onClick={() => setPreviewMaterial(file)}><PaperClipOutlined />{file.name}</button>)}</div>}
              {item.role === "assistant" && !!item.content && !item.failed && !(sending && index === state.messages.length - 1) && <div className="workspace-message-actions">
                <Tooltip title="复制回答"><Button type="text" size="small" icon={<CopyOutlined />} aria-label="复制回答" onClick={() => void copy(item.content)} /></Tooltip>
                {!!item.can_save_document && <Tooltip title={`将回答保存为 Word 到 ${item.case_no} 的 AI 空间`}><Button type="text" size="small" icon={<FileWordOutlined />} disabled={!!workspace.savedDocuments[index] || busy} onClick={() => workspace.saveWord(item, index)}>{workspace.savedDocuments[index] ? "已存入 AI 空间" : "保存 Word"}</Button></Tooltip>}
              </div>}
            </article>)}
            <AgentToolResult result={[state.structured_results, workspace.decisionResult]} />
            <div ref={bottomRef} />
          </div>
        </div>
        {!follow && <Button className="workspace-scroll-bottom" shape="circle" icon={<ArrowDownOutlined />} aria-label="查看最新回答" onClick={() => { setFollow(true); bottomRef.current?.scrollIntoView({ block: "end", behavior: "smooth" }); }} />}
        {!!state.pending_actions.length && <div className="workspace-pending"><div className="workspace-section-heading"><b><AuditOutlined /> 待确认操作</b><Tag>{state.pending_actions.length}</Tag></div>{state.pending_actions.filter((action) => action.status === "pending").map((action) => <div className="workspace-pending-row" key={action.id}><div><b>{agentOperationName(action)}</b><p>{action.summary}</p></div><Button size="small" type="primary" icon={<CheckOutlined />} disabled={busy} onClick={() => setActiveAction(action)}>查看并确认</Button></div>)}</div>}
        <div className="personal-agent-composer-wrap">
          <div className={`personal-agent-composer${dragging ? " dragging" : ""}`} onDragOver={(event) => { if (event.dataTransfer.types.includes("Files")) { event.preventDefault(); setDragging(true); } }} onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node)) setDragging(false); }} onDrop={(event) => { event.preventDefault(); setDragging(false); void workspace.upload(Array.from(event.dataTransfer.files)); }}>
            <div className="workspace-composer-context"><Select aria-label="选择办公技能" value={skillId} disabled={busy} onChange={workspace.setSkillId} popupMatchSelectWidth={300} options={skills.map((item) => ({ value: item.id, label: item.name, disabled: !item.available, title: item.description }))} />{canUseCases && <Tooltip title={selectedCase?.title || "选择本轮问题关联的案件"}><Button type="text" size="small" icon={<FolderOpenOutlined />} disabled={busy} onClick={() => setPickerMode("case")}>{selectedCase?.serial_no || "关联案件"}</Button></Tooltip>}</div>
            {(!!workspace.materials.length || !!workspace.caseMaterials.length) && <div className="workspace-selected-files">{[...workspace.materials.map((item) => ({ ...item, source: "upload" })), ...workspace.caseMaterials.map((item) => ({ ...item, source: "case" }))].map((item) => <div className="workspace-file-chip" key={`${item.source}-${item.id}`}><FileTextOutlined /><Tooltip title={item.name}><button className="workspace-file-name" onClick={() => setPreviewMaterial(item)}>{item.name}</button></Tooltip><Tooltip title="移除材料"><Button type="text" size="small" icon={<CloseOutlined />} aria-label={`移除${item.name}`} disabled={busy} onClick={() => item.source === "upload" ? workspace.setMaterials((current) => current.filter((file) => file.id !== item.id)) : workspace.setCaseMaterials((current) => current.filter((file) => file.id !== item.id))} /></Tooltip></div>)}</div>}
            <Input.TextArea value={input} maxLength={8000} onChange={(event) => workspace.setInput(event.target.value)} disabled={sending || loading} variant="borderless" autoSize={{ minRows: 2, maxRows: 5 }} placeholder="安排工作、查询待办，或结合材料提问…" onPressEnter={(event) => { if (!event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); setFollow(true); void workspace.send(); } }} onPaste={(event) => { const files = Array.from(event.clipboardData.files); if (files.length) { event.preventDefault(); void workspace.upload(files); } }} />
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
    <Drawer title="律所工作台" open={sidebarOpen} onClose={() => setSidebarOpen(false)} placement="left" size={280}><div className="workspace-drawer-sidebar">{sidebar}</div></Drawer>
    <SkillManager open={skillsOpen} onClose={() => setSkillsOpen(false)} skills={skills} refresh={workspace.refreshSkills} onSelect={workspace.setSkillId} />
    <Modal open={!!activeAction} title="智能体操作确认" width={760} maskClosable={!workspace.decisionId} onCancel={() => { if (!workspace.decisionId) setActiveAction(null); }} footer={activeAction && <Space><Button icon={<CloseOutlined />} disabled={!!workspace.decisionId} onClick={async () => { if (await workspace.decide(activeAction, "rejected")) setActiveAction(null); }}>取消操作</Button><Button type="primary" icon={<CheckOutlined />} loading={!!workspace.decisionId} disabled={!!workspace.decisionId || !hasAgentOperationPreview(activeAction)} onClick={async () => { if (await workspace.decide(activeAction, "approved")) setActiveAction(null); }}>确认并执行</Button></Space>}>
      {activeAction && <div style={{ maxHeight: "60dvh", overflowY: "auto" }}><AgentOperationPreview action={activeAction} /></div>}
    </Modal>
    <MaterialPreview item={previewMaterial} onClose={() => setPreviewMaterial(null)} />
    <CaseMaterialsPicker mode={pickerMode} onClose={() => setPickerMode(null)} selectedCase={selectedCase} onCase={workspace.chooseCase} selectedMaterials={workspace.caseMaterials} onMaterials={workspace.setCaseMaterials} privateCount={workspace.materials.length} />
  </div>;
}
