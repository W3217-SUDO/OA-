import { forwardRef, useCallback, useEffect, useRef, useState, type ComponentRef } from "react";
import { Alert, Button, Input, List, Tag, Tooltip, message } from "antd";
import { ApiOutlined, ArrowLeftOutlined, ArrowUpOutlined, CheckOutlined, CloseOutlined, FileExcelOutlined, FileWordOutlined, FolderOpenOutlined, ReloadOutlined } from "@ant-design/icons";
import AssistantStart, { shortcuts, type AssistantSuggestion } from "./AssistantStart";
import AgentAvatar from "./AgentAvatar";
import { ConversationManager } from "./ConversationManager";
import { AssistantWorkspaceTools, type AssistantWorkspaceToolsHandle } from "./AssistantWorkspaceTools";
import { AssistantWorkspaceSidebar } from "./AssistantWorkspaceSidebar";
import { MemoryControlPanel } from "./MemoryControlPanel";
import { ActionConfirmation } from "./ActionConfirmation";
import { ConfirmationHistory } from "./ConfirmationHistory";
import { PersonalAiSpace } from "./PersonalAiSpace";
import { CaseAgentFileFolderModal } from "./CaseAgentFileFolderModal";
import { PersonalMcpConnectionCard } from "./PersonalMcpConnectionCard";
import { hasConnectionCredential, isMcpConnectionInput } from "./personalMcpConfig";
import { agentOperationMessage, userFacingAgentText } from "../AgentOperationPreview";
import { errorText, workspaceDocumentSaveTarget, type CaseAgentConversationSummary, type ConfirmationDetail, type PendingAction, type WorkspaceMessage, type WorkspaceState } from "./types";
import type { usePersonalWorkspace } from "./usePersonalWorkspace";
import "./assistant-panel.css";

export type { AssistantSuggestion };

// 距底部小于该距离就视为“跟着最新回答”，超出则由用户自行滚动，不再强制拉回。
const FOLLOW_THRESHOLD = 48;

const LONG_MESSAGE_LENGTH = 120;

// 从提醒里发出的问题带有完整明细，较长时先折叠，需要时再展开。
function MessageText({ content }: { content: string }) {
  const displayContent = userFacingAgentText(content);
  const [expanded, setExpanded] = useState(false);
  if (displayContent.length <= LONG_MESSAGE_LENGTH) return <>{displayContent}</>;
  return (
    <>
      {expanded ? displayContent : `${displayContent.slice(0, LONG_MESSAGE_LENGTH)}...`}
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
  desktopWorkspace?: boolean;
  onOpenAgentCenter?: () => void;
  onOpenCaseAgent?: (caseId: number, serialNo: string) => void;
};

// 工作台里的个人智能体：对话和输入框合在一个面板内，会话可并行进行；问候语放在工作台顶部。
const AssistantPanel = forwardRef<HTMLElement, Props>(function AssistantPanel(
  { workspace, suggestions, focusRequested, onFocusHandled, onReturnOverview, name, logoSrc, returnLabel = "返回工作概况", desktopWorkspace = false, onOpenAgentCenter, onOpenCaseAgent },
  ref,
) {
  const { status, state, loading, loadError, sending, stopping, input, setInput, send, stop, decide, load } = workspace;
  const mcp = workspace.mcpConnection;
  const threadRef = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);
  const [awayFromBottom, setAwayFromBottom] = useState(false);
  const inputRef = useRef<ComponentRef<typeof Input.TextArea>>(null);
  const workspaceToolsRef = useRef<AssistantWorkspaceToolsHandle>(null);
  const [composing, setComposing] = useState(false);
  const [activeAction, setActiveAction] = useState<PendingAction | null>(null);
  const [decisionError, setDecisionError] = useState("");
  const [historyAction, setHistoryAction] = useState<{ conversationId: string; actionId: string } | null>(null);
  const [dismissalError, setDismissalError] = useState("");
  const [personalSpaceOpen, setPersonalSpaceOpen] = useState(false);
  const [caseAgentFolderOpen, setCaseAgentFolderOpen] = useState(false);
  const [memoryOpen, setMemoryOpen] = useState(false);
  const [caseSession, setCaseSession] = useState<{ item: CaseAgentConversationSummary; state: WorkspaceState; loading: boolean; sending: boolean } | null>(null);
  const lastMessage = state.messages[state.messages.length - 1];
  const displayedState = caseSession?.state || state;
  const hasDisplayedMessages = displayedState.messages.length > 0;
  const sendBlocked = caseSession ? caseSession.loading || caseSession.sending || composing : loading || !!loadError || !status?.ready || workspace.conversationBusy || workspace.uploading || !!workspace.decisionId || stopping || composing;
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
    setDismissalError("");
  }, [displayedState.conversation_id]);
  useEffect(() => {
    if (historyAction && displayedState.conversation_id !== historyAction.conversationId) setHistoryAction(null);
  }, [displayedState.conversation_id]);
  useEffect(() => {
    if (!stickToBottom.current) return;
    const element = threadRef.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, [displayedState.conversation_id, displayedState.messages.length, lastMessage?.content.length]);
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
  }, [displayedState.conversation_id, hasDisplayedMessages]);
  useEffect(() => {
    if (!focusRequested) return;
    inputRef.current?.focus({ preventScroll: true });
    onFocusHandled();
  }, [focusRequested, onFocusHandled]);

  const openCaseConversation = async (item: CaseAgentConversationSummary) => {
    mcp.close();
    setCaseSession({ item, loading: true, sending: false, state: { conversation_id: String(item.id), conversation_title: item.title, messages: [], pending_actions: [], dismissed_action_ids: [], workspace: { kind: "case", case_id: item.case_id } } });
    try {
      const response = await fetch(`/api/v1/case-spaces/${item.case_id}/agent/state?agent_id=${encodeURIComponent(item.agent_id)}&conversation_id=${encodeURIComponent(item.id)}`, { headers: { Authorization: `Bearer ${localStorage.getItem("access_token") || ""}` } });
      if (!response.ok) throw new Error((await response.text()) || "案件会话读取失败");
      const data = await response.json() as { messages?: Array<{ id?: string; role: "user" | "assistant"; content: string; created_at?: string }> };
      const messages: WorkspaceMessage[] = (data.messages || []).map((entry) => ({ ...entry, case_id: item.case_id, case_no: item.case_serial_no, can_save_case_document: entry.role === "assistant" }));
      setCaseSession((current) => current?.item.id === item.id ? { ...current, loading: false, state: { ...current.state, messages } } : current);
      setInput("");
    } catch (error) {
      setCaseSession(null);
      message.error(errorText(error, "案件会话读取失败"));
    }
  };

  const sendCaseMessage = async (content: string) => {
    if (!caseSession || caseSession.loading || caseSession.sending) return;
    const { item } = caseSession;
    const userMessage: WorkspaceMessage = { role: "user", content, case_id: item.case_id, case_no: item.case_serial_no };
    setInput("");
    setCaseSession((current) => current ? { ...current, sending: true, state: { ...current.state, messages: [...current.state.messages, userMessage, { role: "assistant", content: "", case_id: item.case_id, case_no: item.case_serial_no }] } } : current);
    try {
      const response = await fetch(`/api/v1/case-spaces/${item.case_id}/agent/messages`, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("access_token") || ""}` }, body: JSON.stringify({ message: content, skill_id: "general-office", attachment_ids: [], document_ids: [], stream: true, agent_id: item.agent_id, conversation_id: item.id }) });
      if (!response.ok || !response.body) throw new Error((await response.text()) || "案件智能体响应失败");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let assistantContent = "";
      const apply = (event: any) => {
        if (event.type === "delta") assistantContent += String(event.content || "");
        if (event.type === "state" && event.state) {
          const messages: WorkspaceMessage[] = (event.state.messages || []).map((entry: any) => ({ ...entry, case_id: item.case_id, case_no: item.case_serial_no, can_save_case_document: entry.role === "assistant" }));
          setCaseSession((current) => current ? { ...current, state: { ...current.state, messages, pending_actions: [] } } : current);
          return;
        }
        setCaseSession((current) => current ? { ...current, state: { ...current.state, messages: current.state.messages.map((entry, index, all) => index === all.length - 1 && entry.role === "assistant" ? { ...entry, content: assistantContent } : entry) } } : current);
      };
      while (true) {
        const { done, value } = await reader.read();
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines) if (line.trim()) apply(JSON.parse(line));
        if (done) break;
      }
    } catch (error) {
      message.error(errorText(error, "案件智能体响应失败"));
    } finally {
      setCaseSession((current) => current ? { ...current, sending: false } : current);
    }
  };

  const submit = (text?: string) => {
    const content = (text ?? input).trim();
    if (mcp.intercept(content)) { setInput(""); return; }
    if (!content || sendBlocked) return;
    // 草稿的清空和失败恢复交给工作区，避免拒绝发送或停止失败时丢失输入。
    followBottom();
    if (caseSession) void sendCaseMessage(content);
    else void send(text === undefined ? undefined : content);
  };

  const runningIds = workspace.runningIds;
  const conversationTitle = displayedState.conversation_title || name || "沪知助手";
  const currentProject = desktopWorkspace ? workspace.workspaceProjects.find((item) => item.kind === workspace.currentWorkspace?.kind && (item.kind === "personal" || item.case_id === workspace.currentWorkspace?.case_id)) : undefined;
  const currentCaseProject = currentProject?.kind === "case" && currentProject.serial_no ? currentProject : undefined;
  const decisionBusy = loading || workspace.conversationBusy || !!workspace.decisionId || !!workspace.dismissalId;
  const dismiss = async (action: PendingAction) => {
    setDismissalError("");
    try { await workspace.dismissAction(action); }
    catch (error) { setDismissalError(errorText(error, "操作卡收起失败")); }
  };
  const dismissVisible = async () => {
    setDismissalError("");
    try { await workspace.dismissActions(workspace.visibleActions); }
    catch (error) { setDismissalError(errorText(error, "操作状态收起失败")); }
  };
  const reopen = async (detail: ConfirmationDetail) => {
    const selected = await workspace.reopenConfirmation(detail);
    setActiveAction(null); setHistoryAction(selected);
  };
  const activeId = historyAction && historyAction.conversationId === state.conversation_id ? historyAction.actionId : activeAction?.id;
  const reject = async (action: PendingAction) => {
    if (decisionBusy) return;
    setDecisionError("");
    try { await decide(action, "rejected"); }
    catch (error) { setDecisionError(errorText(error, "取消操作失败，请核对实际状态")); }
  };

  const content = (
    <>
      <div className="assistant-bar">
        {!desktopWorkspace && onReturnOverview && <Tooltip title={returnLabel}>
          <Button className="assistant-mobile-control" type="text" icon={<ArrowLeftOutlined />} aria-label={returnLabel} onClick={onReturnOverview} />
        </Tooltip>}
        <span className="assistant-bar-summary">
          {desktopWorkspace && currentProject && <span className="assistant-workspace-current" title={currentProject.title}>{currentProject.kind === "case" ? `${currentProject.serial_no} · ${currentProject.title}` : currentProject.title}</span>}
          {logoSrc && <img className="assistant-brand-logo" src={logoSrc} alt="" width={24} height={24} />}
          <span className="assistant-bar-title">{name || "助手对话"}</span>
          {name && displayedState.conversation_title && <span className="assistant-selected-title" title={displayedState.conversation_title}>{displayedState.conversation_title}</span>}
          {caseSession && <Tag color="green">案件智能体 · {caseSession.item.case_serial_no}</Tag>}
          {runningIds.length > 1 && <span className="assistant-running">{runningIds.length} 个对话正在回答</span>}
        </span>
        <span className={`assistant-mobile-title${name || logoSrc ? " is-branded" : ""}`} title={conversationTitle}>
          {logoSrc && <img className="assistant-brand-logo" src={logoSrc} alt="" width={24} height={24} />}
          {name || logoSrc ? <span className="assistant-title-body">
            <span>{name || conversationTitle}</span>
            {name && state.conversation_title && <small>{state.conversation_title}</small>}
          </span> : conversationTitle}
        </span>
        {desktopWorkspace && currentCaseProject && <><Tooltip title="案件智能体"><Button className="workspace-case-link" size="small" icon={<FolderOpenOutlined />} aria-label="案件智能体" title="案件智能体" onClick={() => onOpenCaseAgent?.(currentCaseProject.case_id!, currentCaseProject.serial_no!)}>案件智能体</Button></Tooltip><Button size="small" icon={<FolderOpenOutlined />} aria-label="案件智能体文件夹" onClick={() => setCaseAgentFolderOpen(true)}>案件智能体文件夹</Button></>}
        {!desktopWorkspace && <div className="assistant-bar-actions">
          <Tooltip title="个人 AI 空间"><Button className="personal-ai-space-trigger" type="text" icon={<FolderOpenOutlined />} aria-label="个人 AI 空间" onClick={() => setPersonalSpaceOpen(true)}><span className="personal-ai-space-label">个人 AI 空间</span></Button></Tooltip>
          <ConfirmationHistory onReopen={reopen} busy={loading || workspace.conversationBusy || !!workspace.decisionId || !!workspace.dismissalId || workspace.uploading} />
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
            activeId={caseSession ? null : state.conversation_id}
            busy={loading || workspace.conversationBusy}
            runningIds={runningIds}
            onCreate={workspace.createConversation}
            onSelect={(id) => { mcp.close(); setCaseSession(null); return workspace.selectConversation(id); }}
            onDelete={workspace.deleteConversation}
            drawerClassName="assistant-conversation-drawer"
            listClassName="assistant-conversation-list"
            rowClassName="assistant-conversation-row"
            selectClassName="assistant-conversation-select"
            showHistoryLabel
          />
        </div>}
      </div>
      <div className="assistant-mobile-space-access"><Button icon={<FolderOpenOutlined />} onClick={() => setPersonalSpaceOpen(true)}>个人 AI 空间 · 查看文件</Button></div>
      {loadError && (
        <Alert className="assistant-alert" type="error" showIcon title={loadError} action={<Button size="small" onClick={() => void load()}>重试</Button>} />
      )}
      {!loadError && status && !status.ready && (
        <Alert className="assistant-alert" type="warning" showIcon title="个人智能体暂未就绪，请检查当前 OA 配置的大模型服务" />
      )}
      {!hasDisplayedMessages && !mcp.open && <div className={`assistant-empty-state${logoSrc ? " has-logo" : ""}`}>
        {logoSrc && <img className="assistant-empty-logo" src={logoSrc} alt="" width={56} height={56} />}
        {desktopWorkspace ? <div className="assistant-workspace-greeting"><h1>今天想处理什么？</h1></div> : <AssistantStart suggestions={suggestions} disabled={sending} onPick={submit} />}
        {!desktopWorkspace && <div className="assistant-mobile-empty">
          <h2>今天想处理什么？</h2>
          <div className="assistant-mobile-suggestions">
            {suggestions.slice(0, 1).map((item) => <button key={item.kind} type="button" disabled={sendBlocked} onClick={() => submit(item.prompt)}>
              {item.label}<em>{item.count}</em>
            </button>)}
            {shortcuts.slice(0, 2).map((item) => <button key={item.label} type="button" disabled={sendBlocked} onClick={() => submit(item.prompt)}>{item.label}</button>)}
          </div>
        </div>}
      </div>}
      {hasDisplayedMessages && (
        <div className="assistant-thread-region">
          <div
            className={`assistant-thread${awayFromBottom ? " has-jump" : ""}`}
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
            {displayedState.messages.map((item, index) => {
              const thinking = !item.content && !item.stopped && (caseSession?.sending || sending) && index === displayedState.messages.length - 1;
              const documentTarget = workspaceDocumentSaveTarget(item);
              return (
                <div key={`${item.created_at || "message"}-${index}`} className={`assistant-message is-${item.role}`}>
                  {item.role === "assistant" && <div className="assistant-message-avatar" role="img" aria-label={name || "AI助手"}>
                    {logoSrc ? <img src={logoSrc} alt="" width={32} height={32} /> : <AgentAvatar size={32} />}
                  </div>}
                  <div className={`assistant-bubble${item.failed ? " is-failed" : ""}${thinking ? " is-thinking" : ""}`}>
                    {item.content
                      ? <MessageText content={item.content} />
                      : (thinking ? <span className="assistant-thinking" role="status" title={progressText}><span>{progressText}</span></span> : "")}
                    {item.stopped && <span className="assistant-stopped">{item.content ? "已停止，已保留生成内容" : "已停止"}</span>}
                    {item.role === "assistant" && item.personal_document_save_error && !item.failed && !(sending && index === displayedState.messages.length - 1) && <Alert type="warning" showIcon title="个人文档暂不可保存" description={item.personal_document_save_error} />}
                    {item.role === "assistant" && documentTarget && !!item.content && !item.failed && !item.stopped && !(sending && index === displayedState.messages.length - 1) && !displayedState.pending_actions.some((action) => action.status === "pending" && action.preview?.path?.endsWith("/ai-space/files")) && <div className="personal-ai-document-actions">
                      {workspace.savedDocuments[index] ? <>
                        <span className="personal-ai-document-saved"><FileWordOutlined />{documentTarget === "case" ? "已存入案件 AI 空间" : "已存入个人 AI 空间"}</span>
                        {documentTarget === "personal" ? <Button type="link" icon={<FolderOpenOutlined />} onClick={() => setPersonalSpaceOpen(true)}>查看文件</Button> : <Button type="link" icon={<FolderOpenOutlined />} href={`?page=case-detail-${item.case_id}-${encodeURIComponent(item.case_no || "")}`} title="在案件文档的 AI 空间目录中查看">查看案件文件</Button>}
                      </> : <Tooltip title={documentTarget === "case" ? "保存 Word 到案件 AI 空间" : "保存 Word 到个人 AI 空间"}><Button type="text" icon={<FileWordOutlined />} disabled={loading || workspace.conversationBusy} onClick={() => void workspace.saveWord(item, index)}>{documentTarget === "case" ? "保存到案件 AI 空间" : "保存 Word"}</Button></Tooltip>}
                      {documentTarget === "personal" && item.can_save_spreadsheet && (workspace.savedSpreadsheets[index] ? <span className="personal-ai-document-saved"><FileExcelOutlined />已存入个人 AI 空间</span> : <Tooltip title="将回答中的 Markdown 表格保存为 Excel 到个人 AI 空间"><Button type="text" icon={<FileExcelOutlined />} disabled={loading || workspace.conversationBusy} onClick={() => void workspace.saveSpreadsheet(item, index)}>保存 Excel</Button></Tooltip>)}
                    </div>}
                  </div>
                </div>
              );
            })}
          </div>
          {awayFromBottom && <button type="button" className="assistant-jump" onClick={followBottom}>回到最新回答</button>}
        </div>
      )}
      {dismissalError && <Alert className="assistant-alert" type="error" showIcon title="操作卡未收起" description={dismissalError} />}
      {Object.values(workspace.decisionFailures).filter((failure) => !failure.hidden && !state.pending_actions.some((action) => action.id === failure.actionId)).map((failure) => <Alert key={failure.actionId} className="assistant-decision-failure" type="error" showIcon closable={{ onClose: () => workspace.hideDecisionFailure(failure.actionId) }} title="操作未完成" description={failure.message} />)}
      {!!workspace.visibleActions.length && (
        <div className="assistant-pending">
          <div className="assistant-pending-heading">
            <b>{workspace.visibleActions.some((action) => action.status === "pending") ? "待你确认的操作" : "操作状态"}</b>
            <Tooltip title="收起当前操作状态"><Button className="assistant-action-dismiss" type="text" icon={<CloseOutlined />} aria-label="收起当前操作状态" disabled={loading || workspace.conversationBusy || !!workspace.decisionId || !!workspace.dismissalId} loading={!!workspace.dismissalId} onClick={() => void dismissVisible()} /></Tooltip>
          </div>
          {decisionError && <Alert type="error" showIcon title="操作未完成" description={decisionError} />}
          <List
            size="small"
            dataSource={workspace.visibleActions}
            renderItem={(item) => (
              <List.Item
                actions={[
                  <Button key="approve" type={item.status === "pending" ? "primary" : "default"} size="small" icon={<CheckOutlined />} disabled={decisionBusy} onClick={() => { setDecisionError(""); setHistoryAction(null); setActiveAction(item); }}>{item.status === "pending" ? "查看并确认" : "查看状态"}</Button>,
                  ...(item.status === "pending" ? [<Button key="reject" size="small" icon={<CloseOutlined />} disabled={decisionBusy} loading={workspace.decisionId === item.id} onClick={() => void reject(item)}>取消</Button>] : []),
                  <Tooltip key="dismiss" title="收起操作卡"><Button className="assistant-action-dismiss" type="text" size="small" icon={<CloseOutlined />} aria-label={`收起操作卡：${item.summary}`} disabled={loading || workspace.conversationBusy || !!workspace.decisionId || !!workspace.dismissalId} loading={workspace.dismissalId === item.id} onClick={() => void dismiss(item)} /></Tooltip>,
                ]}
              >
                <List.Item.Meta title={item.summary} description={item.status === "pending" && !workspace.decisionFailures[item.id] ? undefined : <>
                  {item.status !== "pending" && <Tag color={item.status === "failed" ? "error" : "processing"}>{({ failed: "执行失败", executing: "执行中", succeeded: "已执行", approved: "已批准", rejected: "已取消" })[item.status]}</Tag>}
                  {item.error != null && <Alert type="error" showIcon title={agentOperationMessage(item.error)} />}
                  {item.error == null && workspace.decisionFailures[item.id] && <Alert type="error" showIcon title="操作未完成" description={workspace.decisionFailures[item.id].message} />}
                </>} />
              </List.Item>
            )}
          />
        </div>
      )}
      <ActionConfirmation action={state.pending_actions.find((action) => action.id === activeId) ?? null} deciding={!!workspace.decisionId} decisionFailure={activeId ? workspace.decisionFailures[activeId] : undefined} onDecide={decide} onClose={() => { setActiveAction(null); setHistoryAction(null); }} />
      <PersonalAiSpace open={personalSpaceOpen} onClose={() => setPersonalSpaceOpen(false)} revision={workspace.documentRevision} busy={loading || workspace.conversationBusy || !!workspace.decisionId || !!workspace.dismissalId || workspace.uploading} onOpenConversation={workspace.selectConversation} onSkillsChanged={workspace.refreshSkills} label={desktopWorkspace ? "AI生成文件夹" : undefined} />
      {mcp.open && <PersonalMcpConnectionCard key={`${workspace.draftKey}:${caseSession?.item.id || "personal"}`} connection={mcp} />}
      <div className="assistant-composer"
        onDragOver={(event) => { if (event.dataTransfer.types.includes("Files")) event.preventDefault(); }}
        onDrop={(event) => {
          if (!event.dataTransfer.files.length) return;
          event.preventDefault();
          void workspace.upload(Array.from(event.dataTransfer.files));
        }}
      >
        <AssistantWorkspaceTools key={workspace.draftKey} ref={workspaceToolsRef} workspace={workspace} desktopWorkspace={desktopWorkspace} onOpenPersonalAiSpace={() => setPersonalSpaceOpen(true)} onOpenMemory={() => setMemoryOpen(true)} />
        <div><Button type="text" icon={<ApiOutlined />} onClick={mcp.show}>连接我的 MCP</Button></div>
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
              const pasted = event.clipboardData.getData("text");
              if (isMcpConnectionInput(pasted, mcp.open) || hasConnectionCredential(pasted)) { event.preventDefault(); mcp.intercept(pasted); setInput(""); return; }
              if (event.clipboardData.files.length) { event.preventDefault(); void workspace.upload(Array.from(event.clipboardData.files)); }
            }}
            maxLength={8000}
            autoSize={{ minRows: 1, maxRows: 5 }}
            placeholder="告诉智能体你要完成的 OA 工作"
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
              <Button className="assistant-send" shape="circle" type="primary" icon={<ArrowUpOutlined />} aria-label={sending ? "打断并发送" : "发送"} htmlType="submit" disabled={!input.trim() || (sendBlocked && !isMcpConnectionInput(input, mcp.open) && !hasConnectionCredential(input))} />
            </Tooltip>}
          </div>
        </form>
      </div>
      {!desktopWorkspace && <div className="assistant-chips">
        {suggestions.map((item) => (
          <button key={item.kind} type="button" className="is-context" disabled={sending} onClick={() => submit(item.prompt)}>
            {item.label}<em>{item.count}</em>
          </button>
        ))}
        {shortcuts.map((item) => (
          <button key={item.label} type="button" disabled={sending} onClick={() => submit(item.prompt)}>{item.label}</button>
        ))}
      </div>}
    </>
  );
  return (
    <section className={`assistant${hasDisplayedMessages ? "" : " is-empty"}${desktopWorkspace ? " is-desktop-workspace" : ""}`} aria-label={name || "个人智能体"} ref={ref}>
      {desktopWorkspace && <AssistantWorkspaceSidebar
        workspace={workspace}
        name={name || "AI助手"}
        logoSrc={logoSrc}
        onOpenPersonalSpace={() => setPersonalSpaceOpen(true)}
        onOpenMemory={() => setMemoryOpen(true)}
        onImportSkills={() => workspaceToolsRef.current?.importSkills()}
        onOpenAgentCenter={onOpenAgentCenter}
        onOpenCaseAgentConversation={(item: CaseAgentConversationSummary) => void openCaseConversation(item)}
        onReopenConfirmation={reopen}
        onReturnWorkbench={onReturnOverview}
      />}
      {desktopWorkspace ? <div className="assistant-workspace-main">{content}</div> : content}
      {caseAgentFolderOpen && currentCaseProject?.case_id && <CaseAgentFileFolderModal open caseId={currentCaseProject.case_id} serialNo={currentCaseProject.serial_no} onClose={() => setCaseAgentFolderOpen(false)} />}
      {memoryOpen && <MemoryControlPanel open onClose={() => setMemoryOpen(false)} />}
    </section>
  );
});

export default AssistantPanel;
