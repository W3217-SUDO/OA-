import { useEffect, useRef, useState, type ReactNode } from "react";
import { Alert, Button, Input, Segmented, Select, Skeleton, Space, Tag, Tooltip, message } from "antd";
import { AppstoreAddOutlined, ArrowDownOutlined, ArrowUpOutlined, AuditOutlined, BulbOutlined, CheckOutlined, CloseOutlined, FileTextOutlined, FolderOpenOutlined, LockOutlined, PaperClipOutlined, ReloadOutlined, RobotOutlined, ScheduleOutlined, SettingOutlined, StopOutlined, TeamOutlined, ThunderboltOutlined, WalletOutlined } from "@ant-design/icons";
import { AgentToolRequests } from "./AgentToolRequests";
import { AgentToolResult } from "./AgentToolResult";
import { agentOperationMessage } from "./AgentOperationPreview";
import { CaseMaterialsPicker } from "./personal-agent/CaseMaterialsPicker";
import { SkillManager } from "./personal-agent/SkillManager";
import { availableAgentSkillId, DEFAULT_AGENT_SKILL, NO_AGENT_SKILL_OPTION } from "./agentSkillRouting";
import { skillChoiceLabel } from "./personal-agent/skillScope";
import { MaterialPreview } from "./personal-agent/MaterialPreview";
import { WorkPanel } from "./personal-agent/WorkPanel";
import { ConversationMessage } from "./personal-agent/ConversationMessage";
import { ConversationManager } from "./personal-agent/ConversationManager";
import { PersonalAiSpace } from "./personal-agent/PersonalAiSpace";
import { CaseAgentFileFolderModal } from "./personal-agent/CaseAgentFileFolderModal";
import { MemoryControlPanel } from "./personal-agent/MemoryControlPanel";
import { MobileComposerOptions } from "./personal-agent/MobileComposerOptions";
import { ActionConfirmation } from "./personal-agent/ActionConfirmation";
import { ConfirmationHistory } from "./personal-agent/ConfirmationHistory";
import { MATERIAL_ACCEPT, usePersonalWorkspace } from "./personal-agent/usePersonalWorkspace";
import { errorText, workspaceDocumentSaveTarget, type ConfirmationDetail, type Material, type PendingAction, type ResponseMode, type WorkspaceCommand } from "./personal-agent/types";
import "./personal-agent-center.css";

const commandIcons: Record<string, ReactNode> = { today: <ScheduleOutlined />, task: <CheckOutlined />, approval: <AuditOutlined />, case: <FolderOpenOutlined />, finance: <WalletOutlined />, seal: <FileTextOutlined />, customer: <TeamOutlined /> };

export default function PersonalAgentCenterPage({ onNavigate }: { onNavigate: (route: string) => void }) {
  const workspace = usePersonalWorkspace();
  const { status, state, skills, skillId, input, loading, sending, uploading, selectedCase } = workspace;
  const [view, setView] = useState<"workspace" | "chat">("workspace");
  const [refreshToken, setRefreshToken] = useState(0);
  const [skillsOpen, setSkillsOpen] = useState(false);
  const [personalSpaceOpen, setPersonalSpaceOpen] = useState(false);
  const [caseAgentFolderOpen, setCaseAgentFolderOpen] = useState(false);
  const [memoryOpen, setMemoryOpen] = useState(false);
  const [pickerMode, setPickerMode] = useState<"case" | "materials" | null>(null);
  const [follow, setFollow] = useState(true);
  const [dragging, setDragging] = useState(false);
  const [previewMaterial, setPreviewMaterial] = useState<Material | null>(null);
  const [activeAction, setActiveAction] = useState<PendingAction | null>(null);
  const [historyAction, setHistoryAction] = useState<{ conversationId: string; actionId: string } | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const canUseCases = status?.commands.some((item) => item.id === "cases");
  const messageCaseId = state.messages.find((item) => item.case_id)?.case_id || state.messages.map((item) => String(item.content || "")).join("\n").match(/案件ID[：:]\s*(\d+)/)?.[1];
  const workspaceProjects = Array.isArray(workspace.workspaceProjects) ? workspace.workspaceProjects : [];
  const listedCaseProject = workspaceProjects.find((item) => item.kind === "case" && item.available);
  const activeCaseId = workspace.currentWorkspace?.kind === "case"
    ? Number(workspace.currentWorkspace.case_id)
    : messageCaseId ? Number(messageCaseId) : Number(listedCaseProject?.case_id) || null;
  const activeCaseProject = activeCaseId
    ? workspaceProjects.find((item) => item.kind === "case" && Number(item.case_id) === activeCaseId)
    : undefined;
  const showCaseAgent = canUseCases || workspace.currentWorkspace?.kind === "case";
  const openCaseAgent = () => {
    if (activeCaseId && activeCaseProject?.serial_no) {
      onNavigate(`case-detail-${activeCaseId}-${encodeURIComponent(activeCaseProject.serial_no)}-agent`);
      return;
    }
    onNavigate("case-agent-center");
  };
  const busy = loading || sending || uploading || !!workspace.decisionId || workspace.conversationBusy;
  const navigationBusy = loading || uploading || !!workspace.decisionId || workspace.conversationBusy;
  useEffect(() => { if (follow) bottomRef.current?.scrollIntoView({ block: "end" }); }, [state.messages, follow, view]);
  useEffect(() => { setFollow(true); setActiveAction(null); }, [state.conversation_id]);
  useEffect(() => { if (historyAction && state.conversation_id !== historyAction.conversationId) setHistoryAction(null); }, [state.conversation_id]);
  const reopen = async (detail: ConfirmationDetail) => {
    const selected = await workspace.reopenConfirmation(detail);
    setActiveAction(null); setHistoryAction(selected); setView("chat");
  };
  const dismiss = async (action: PendingAction) => {
    try { await workspace.dismissAction(action); }
    catch (error) { message.error(errorText(error, "操作卡收起失败")); }
  };
  const activeId = historyAction && historyAction.conversationId === state.conversation_id ? historyAction.actionId : activeAction?.id;
  const showAssistant = () => { if (window.matchMedia("(max-width: 1100px)").matches) setView("chat"); };
  const prepare = (command: WorkspaceCommand) => { workspace.setSkillId(command.skill_id); workspace.setInput(command.prompt); showAssistant(); };
  const draft = () => { workspace.setSkillId(availableAgentSkillId(DEFAULT_AGENT_SKILL, skills)); workspace.setInput("根据我提供的材料起草一份办公文档，缺失信息标为待补充"); showAssistant(); };
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
  const responseModeControl = status?.supports_response_modes && <Tooltip title="快速用于日常办公查询；深度用于复杂分析">
    <Segmented size="small" aria-label="回答模式" value={workspace.responseMode} disabled={busy} options={[{ value: "fast", label: "快速", icon: <ThunderboltOutlined /> }, { value: "deep", label: "深度", icon: <BulbOutlined /> }]} onChange={(value) => workspace.setResponseMode(value as ResponseMode)} />
  </Tooltip>;
  return <div className="personal-agent-page" data-testid="personal-agent-center-page">
    <header className="personal-agent-header">
      <div className="personal-agent-title"><div className="workspace-brand-icon"><RobotOutlined /></div><h2>智能体中心</h2><span>律所工作台</span></div>
      <Space className="workspace-header-actions" size={8} wrap>
        <Button className="personal-ai-space-trigger" icon={<FolderOpenOutlined />} onClick={() => setPersonalSpaceOpen(true)}>个人空间</Button>
        <Button className="personal-ai-memory-trigger" icon={<SettingOutlined />} aria-label="记忆管理" title="记忆管理" onClick={() => setMemoryOpen(true)}>记忆管理</Button>
        <Button icon={<AppstoreAddOutlined />} disabled={busy} onClick={() => void openSkills()}>技能包</Button>
        <Segmented aria-label="切换工作视图" value={view} options={[{ value: "workspace", label: "工作台" }, { value: "chat", label: "对话" }]} onChange={(value) => setView(value as "workspace" | "chat")} />
        <Tooltip title={status?.ready ? `当前模型：${status.model}` : "模型服务未就绪"}><span className={`workspace-service ${status?.ready ? "ready" : ""}`}><i />{status?.ready ? "已连接" : loading ? "连接中" : "未就绪"}</span></Tooltip>
        {showCaseAgent && <><Tooltip title="打开案件智能体"><Button className="workspace-case-link" size="small" icon={<FolderOpenOutlined />} aria-label="案件智能体" title="案件智能体" onClick={openCaseAgent}>案件智能体</Button></Tooltip>{activeCaseId && <Button size="small" icon={<FolderOpenOutlined />} aria-label="案件智能体文件夹" onClick={() => setCaseAgentFolderOpen(true)}>案件智能体文件夹</Button>}</>}
        <ConfirmationHistory onReopen={reopen} busy={navigationBusy || !!workspace.dismissalId} />
        <Tooltip title="刷新工作台与会话"><Button type="text" icon={<ReloadOutlined />} aria-label="刷新工作台与会话" disabled={navigationBusy || !!workspace.runningIds.length} onClick={() => { setRefreshToken((value) => value + 1); void workspace.load(); }} /></Tooltip>
      </Space>
    </header>
    {workspace.loadError && <Alert type="error" showIcon title={workspace.loadError} />}
    {!loading && !workspace.loadError && !status?.ready && <Alert type="warning" showIcon title="模型服务未就绪，请检查系统模型配置" />}
    {caseAgentFolderOpen && activeCaseId && <CaseAgentFileFolderModal open caseId={activeCaseId} serialNo={activeCaseProject?.serial_no} onClose={() => setCaseAgentFolderOpen(false)} />}
    <div className="personal-agent-layout" data-view={view}>
      <WorkPanel status={status} skills={skills} busy={busy} refreshToken={refreshToken} decisionResult={workspace.decisionResult} onNavigate={onNavigate} onPrepare={prepare} onSkill={(skill) => { workspace.setSkillId(skill.id); if (skill.quick_prompts?.[0]) workspace.setInput(skill.quick_prompts[0]); showAssistant(); }} onUpload={() => { showAssistant(); fileRef.current?.click(); }} onSkills={() => void openSkills()} onDraft={draft} />
      <main className="personal-agent-chat">
        <div className="workspace-thread-heading"><div className="workspace-assistant-title"><span><RobotOutlined /> 办公助手</span><Tooltip title="仅当前账号可见的会话"><small className="workspace-conversation-title"><LockOutlined /> {state.conversation_title || "个人会话"}</small></Tooltip></div><Space wrap>{selectedCase && <Tooltip title={selectedCase.title}><span className="workspace-current-case"><FolderOpenOutlined /> {selectedCase.serial_no}</span></Tooltip>}<ConversationManager items={workspace.conversations} activeId={state.conversation_id} busy={navigationBusy} runningIds={workspace.runningIds} onCreate={workspace.createConversation} onSelect={workspace.selectConversation} onDelete={workspace.deleteConversation} /><AgentToolRequests className="workspace-operation-record" buttonLabel="操作记录" titlePrefix="智能体" /></Space></div>
        <div ref={scrollRef} className="personal-agent-messages" onScroll={() => { const element = scrollRef.current; if (element) setFollow(element.scrollHeight - element.scrollTop - element.clientHeight < 100); }}>
          <div className="workspace-thread">
            {loading ? <Skeleton active paragraph={{ rows: 4 }} /> : !state.messages.length && <div className="workspace-empty"><div className="workspace-empty-symbol"><RobotOutlined /></div><h3>开始今天的工作</h3><div className="workspace-start-actions">{status?.commands.slice(0, 4).map((command) => <button key={command.id} onClick={() => prepare(command)}>{commandIcons[command.icon]}<span>{command.label}</span><ArrowUpOutlined /></button>)}</div></div>}
            {state.memory_summary_metadata?.compressed_at && <div className="workspace-compression-notice" role="status"><span className="workspace-compression-notice-title">上下文已自动压缩</span><span>{state.memory_summary_updated_at ? new Date(state.memory_summary_updated_at).toLocaleString("zh-CN") : "刚刚"}</span>{(state.memory_summary_metadata?.covered_message_range || state.memory_summary_metadata?.message_range) ? <span>覆盖消息：{String(state.memory_summary_metadata.covered_message_range || state.memory_summary_metadata.message_range)}</span> : state.memory_summary_metadata?.covered_message_count != null || state.memory_summary_metadata?.covered_messages != null ? <span>覆盖消息：{String(state.memory_summary_metadata.covered_message_count ?? state.memory_summary_metadata.covered_messages)} 条</span> : null}{(state.memory_summary_metadata?.summary_token_count != null || state.memory_summary_metadata?.token_count != null) && <span>摘要 Token：{String(state.memory_summary_metadata.summary_token_count ?? state.memory_summary_metadata.token_count)}</span>}<span>原始消息仍保留在会话记录中</span></div>}
            {state.messages.map((item, index) => <ConversationMessage key={`${item.created_at || "message"}-${index}`} item={item} generating={sending && index === state.messages.length - 1} readingMaterials={!!(workspace.materials.length + workspace.caseMaterials.length)} progress={workspace.progress} saved={!!workspace.savedDocuments[index]} busy={busy} onCopy={copy} onPreview={setPreviewMaterial} onSave={() => workspace.saveWord(item, index)} onViewFiles={() => { if (workspaceDocumentSaveTarget(item) === "case") onNavigate(`case-detail-${item.case_id}-${encodeURIComponent(item.case_no || "")}`); else setPersonalSpaceOpen(true); }} />)}
            <AgentToolResult result={[state.structured_results, workspace.decisionResult]} />
            <div ref={bottomRef} />
          </div>
          {!follow && <div className="workspace-scroll-bottom-wrap"><Button className="workspace-scroll-bottom" shape="circle" icon={<ArrowDownOutlined />} aria-label="查看最新回答" onClick={() => { setFollow(true); bottomRef.current?.scrollIntoView({ block: "end", behavior: "smooth" }); }} /></div>}
        </div>
        {Object.values(workspace.decisionFailures).filter((failure) => !failure.hidden && !state.pending_actions.some((action) => action.id === failure.actionId)).map((failure) => <Alert key={failure.actionId} type="error" showIcon closable={{ onClose: () => workspace.hideDecisionFailure(failure.actionId) }} title="操作未完成" description={failure.message} />)}
        {!!workspace.visibleActions.length && <div className="workspace-pending"><div className="workspace-section-heading"><b><AuditOutlined /> 操作状态</b><Tag>{workspace.visibleActions.length}</Tag></div>{workspace.visibleActions.map((action) => <div className="workspace-pending-row" key={action.id}><div><b>{action.summary}</b>{action.status !== "pending" && <Tag color={action.status === "failed" ? "error" : "processing"}>{({ failed: "执行失败", executing: "执行中", succeeded: "已执行", approved: "已批准", rejected: "已取消" })[action.status]}</Tag>}{action.error != null && <Alert type="error" showIcon title={agentOperationMessage(action.error)} />}{action.error == null && workspace.decisionFailures[action.id] && <Alert type="error" showIcon title="操作未完成" description={workspace.decisionFailures[action.id].message} />}</div><Button size="small" type={action.status === "pending" ? "primary" : "default"} icon={<CheckOutlined />} disabled={navigationBusy || !!workspace.dismissalId} onClick={() => { setHistoryAction(null); setActiveAction(action); }}>{action.status === "pending" ? "查看并确认" : "查看状态"}</Button><Tooltip title="收起操作卡"><Button type="text" icon={<CloseOutlined />} aria-label={`收起操作卡：${action.summary}`} disabled={navigationBusy || !!workspace.dismissalId} loading={workspace.dismissalId === action.id} onClick={() => void dismiss(action)} /></Tooltip></div>)}</div>}
        <div className="personal-agent-composer-wrap">
          <div className={`personal-agent-composer${dragging ? " dragging" : ""}`} onDragOver={(event) => { if (event.dataTransfer.types.includes("Files")) { event.preventDefault(); setDragging(true); } }} onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node)) setDragging(false); }} onDrop={(event) => { event.preventDefault(); setDragging(false); void workspace.upload(Array.from(event.dataTransfer.files)); }}>
            <div className="workspace-composer-context"><Select aria-label="选择办公技能" value={skillId} disabled={busy} allowClear onChange={value => workspace.setSkillId(value ?? "")} popupMatchSelectWidth={300} options={[NO_AGENT_SKILL_OPTION, ...skills.map((item) => ({ value: item.id, label: skillChoiceLabel(item), disabled: !item.available, title: item.description }))]} />{responseModeControl}{canUseCases && <Tooltip title={selectedCase?.title || "选择本轮问题关联的案件"}><Button type="text" size="small" icon={<FolderOpenOutlined />} disabled={busy} onClick={() => setPickerMode("case")}>{selectedCase?.serial_no || "关联案件"}</Button></Tooltip>}</div>
            {(selectedCase || !!workspace.materials.length || !!workspace.caseMaterials.length) && <div className={`workspace-selected-files${!workspace.materials.length && !workspace.caseMaterials.length ? " workspace-case-only" : ""}`}>
              {selectedCase && <div className="workspace-file-chip workspace-mobile-case-chip"><FolderOpenOutlined /><Tooltip title={selectedCase.title}><button className="workspace-file-name" aria-label={`关联案件：${selectedCase.serial_no}，${selectedCase.title}`} disabled={busy} onClick={() => setPickerMode("case")}>{selectedCase.serial_no}</button></Tooltip><Tooltip title="取消案件关联"><Button type="text" size="small" icon={<CloseOutlined />} aria-label={`取消案件关联：${selectedCase.serial_no}`} disabled={busy} onClick={() => workspace.chooseCase(null)} /></Tooltip></div>}
              {[...workspace.materials.map((item) => ({ ...item, source: "upload" })), ...workspace.caseMaterials.map((item) => ({ ...item, source: "case" }))].map((item) => <div className="workspace-file-chip" key={`${item.source}-${item.id}`}><FileTextOutlined /><Tooltip title={item.name}><button className="workspace-file-name" onClick={() => setPreviewMaterial(item)}>{item.name}</button></Tooltip><Tooltip title="移除材料"><Button type="text" size="small" icon={<CloseOutlined />} aria-label={`移除${item.name}`} disabled={busy} onClick={() => item.source === "upload" ? workspace.setMaterials((current) => current.filter((file) => file.id !== item.id)) : workspace.setCaseMaterials((current) => current.filter((file) => file.id !== item.id))} /></Tooltip></div>)}
            </div>}
            <Input.TextArea value={input} maxLength={8000} onChange={(event) => workspace.setInput(event.target.value)} disabled={loading || workspace.conversationBusy || workspace.stopping} variant="borderless" autoSize={{ minRows: 1, maxRows: 5 }} placeholder="安排工作、查询待办，或结合材料提问…" onPressEnter={(event) => { if (!event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); setFollow(true); void workspace.send(); } }} onPaste={(event) => { const files = Array.from(event.clipboardData.files); if (files.length) { event.preventDefault(); void workspace.upload(files); } }} />
            <div className="workspace-composer-tools"><Space className="workspace-desktop-composer-tools" size={2}>
              <input ref={fileRef} hidden type="file" multiple accept={MATERIAL_ACCEPT} onChange={(event) => { void workspace.upload(Array.from(event.target.files || [])); event.target.value = ""; }} />
              <Tooltip title="上传文件"><Button type="text" icon={<PaperClipOutlined />} aria-label="上传文件" loading={uploading} disabled={busy} onClick={() => fileRef.current?.click()} /></Tooltip>
              {selectedCase && <Tooltip title="从案件文件夹选择材料"><Button type="text" icon={<FolderOpenOutlined />} aria-label="选择案件材料" disabled={busy} onClick={() => setPickerMode("materials")} /></Tooltip>}
              <Tooltip title="管理和上传技能"><Button type="text" icon={<AppstoreAddOutlined />} aria-label="管理技能" disabled={busy} onClick={() => void openSkills()} /></Tooltip>
            </Space>
              <MobileComposerOptions skills={skills} skillId={skillId} busy={busy} uploading={uploading} canUseCases={!!canUseCases} selectedCase={selectedCase} onSkill={workspace.setSkillId} onCase={() => setPickerMode("case")} onMaterials={() => setPickerMode("materials")} onUpload={() => fileRef.current?.click()} onSkills={() => void openSkills()} />
              {status?.supports_response_modes && <div className="workspace-mobile-response-mode">{responseModeControl}</div>}
              <div className="workspace-send-area">{uploading && <span>正在上传</span>}{sending && <Tooltip title="停止当前对话的回答"><Button danger type="text" icon={<StopOutlined />} aria-label="停止生成" loading={workspace.stopping} disabled={workspace.stopping} onClick={() => void workspace.stop()} /></Tooltip>}{(!sending || !!input.trim()) && <Tooltip title={sending ? "打断并发送" : "发送"}><Button type="primary" icon={<ArrowUpOutlined />} aria-label={sending ? "打断并发送" : "发送"} disabled={navigationBusy || workspace.stopping || !input.trim() || !status?.ready || !!workspace.loadError} onClick={() => { setFollow(true); void workspace.send(); }} /></Tooltip>}</div>
            </div>
          </div>
        </div>
      </main>
    </div>
    <SkillManager open={skillsOpen} onClose={() => setSkillsOpen(false)} skills={skills} refresh={workspace.refreshSkills} onSelect={workspace.setSkillId} />
    <PersonalAiSpace open={personalSpaceOpen} onClose={() => setPersonalSpaceOpen(false)} revision={workspace.documentRevision} busy={navigationBusy} onOpenConversation={workspace.selectConversation} onSkillsChanged={workspace.refreshSkills} />
    {memoryOpen && <MemoryControlPanel open onClose={() => setMemoryOpen(false)} />}
    <ActionConfirmation action={state.pending_actions.find((action) => action.id === activeId) ?? null} deciding={!!workspace.decisionId} decisionFailure={activeId ? workspace.decisionFailures[activeId] : undefined} onDecide={workspace.decide} onClose={() => { setActiveAction(null); setHistoryAction(null); }} />
    <MaterialPreview item={previewMaterial} onClose={() => setPreviewMaterial(null)} />
    <CaseMaterialsPicker mode={pickerMode} onClose={() => setPickerMode(null)} selectedCase={selectedCase} onCase={workspace.chooseCase} selectedMaterials={workspace.caseMaterials} onMaterials={workspace.setCaseMaterials} privateCount={workspace.materials.length} />
  </div>;
}
