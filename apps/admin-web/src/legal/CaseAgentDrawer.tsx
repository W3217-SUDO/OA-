import { CaseAgentDock } from "./CaseAgentDock";
import {
CheckOutlined,
CloseOutlined,
DownOutlined,
FileWordOutlined,
FolderOpenOutlined,
FolderOutlined,
InfoCircleOutlined,
MessageOutlined,
PaperClipOutlined,
PlusOutlined,
ReloadOutlined,
SendOutlined,
StopOutlined,
} from "@ant-design/icons";
import { Alert,Button,Dropdown,Image,Input,message,Popover,Select,Space,Tag,Tooltip,Tree } from "antd";
import "../agentPending.css";
import "../composerSingleBox.css";
import { actionResultLine, mergeByTime } from "../agentActionResult";
import { useEffect, useState } from "react";
import { CaseAgentConfirmFloat } from "./CaseAgentConfirmFloat";
import { AgentToolResult } from "../AgentToolResult";
import { NO_AGENT_SKILL_OPTION } from "../agentSkillRouting";
import { api } from "../api";
import { CaseWordTemplateModal, matchWordTemplate, type WordTemplate } from "./CaseWordTemplateModal";
import type { ClipboardEvent,Key,PointerEvent as ReactPointerEvent } from "react";
import {
AGENT_DOCUMENT_LIMIT,
buildAgentDocumentTree,
} from "./constants";
import { AgentIcon } from "../personal-agent/AgentAvatar";
import AgentMascot from "../personal-agent/AgentMascot";
import type {
CaseAgentAction,
CaseAgentAttachment,
CaseAgentDocument,
CaseAgentConversation,
CaseAgentState,
CaseAgentStatus,
CaseDetailCapabilities,
CaseRow
} from "./types";

// 新建会话的默认名称：会话 + 当前日期时间，不再让用户先起名。
export const caseConversationTitle = (now = new Date()) => `会话 ${now.getMonth() + 1}-${String(now.getDate()).padStart(2, "0")} ${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;

interface CaseAgentDrawerProps {
  agentOpen: boolean;
  agentRevealKey?: number;
  /** 501185：案件详情打开着时，智能体没开也在右侧显示收起状态的小按钮。 */
  agentIdleTab?: boolean;
  openIdleAgent?: () => void;
  /** 501185：案件有已逾期或 7 天内到期的提醒。 */
  agentTabAlert?: boolean;
  closeCaseAgent: () => void;
  agentCase: CaseRow | null;
  agentDrawerWidth: number;
  startAgentDrawerResize: (event: ReactPointerEvent<HTMLDivElement>) => void;
  agentStatus: CaseAgentStatus | null;
  agentLoading: boolean;
  agentSending: boolean;
  /** 智能体正在做的步骤（如“正在调用：修改案件信息…”），没有时显示默认提示。 */
  agentProgress?: string;
  agentSkillId: string;
  setAgentSkillId: (id: string) => void;
  loadCaseAgent: (row: CaseRow, resetMaterials?: boolean) => Promise<unknown>;
  openAgentFolder: () => void;
  agentConversations: CaseAgentConversation[];
  conversationId: number | null;
  switchCaseConversation: (id: number) => void;
  createCaseConversation: (title: string) => Promise<unknown>;
  agentState: CaseAgentState | null;
  agentDecisionLoading: string;
  decideCaseAgentAction: (action: CaseAgentAction, decision: "approved" | "rejected") => Promise<string | void>;
  restoreCaseAgentAction: (action: CaseAgentAction) => Promise<unknown>;
  counselDetailCapabilities: CaseDetailCapabilities;
  agentHistoryExpanded: boolean;
  setAgentHistoryExpanded: (expanded: boolean) => void;
  sendCaseAgentMessage: (preset?: string) => Promise<unknown>;
  agentMaterialPickerOpen: boolean;
  setAgentMaterialPickerOpen: (open: boolean | ((current: boolean) => boolean)) => void;
  toggleAgentMaterialPicker: () => void;
  agentDocuments: CaseAgentDocument[];
  agentDocumentsLoading: boolean;
  agentDocumentIds: number[];
  setAgentDocumentIds: (ids: number[] | ((current: number[]) => number[])) => void;
  updateAgentDocumentSelection: (checkedKeys: Key[] | { checked: Key[]; halfChecked: Key[] }) => void;
  agentScreenshots: CaseAgentAttachment[];
  removeAgentScreenshot: (attachment: CaseAgentAttachment) => void;
  agentScreenshotInputRef: React.RefObject<HTMLInputElement | null>;
  uploadCaseAgentScreenshot: (file?: File) => Promise<unknown>;
  agentScreenshotUploading: boolean;
  agentInput: string;
  setAgentInput: (value: string) => void;
  pasteCaseAgentScreenshot: (event: ClipboardEvent<HTMLTextAreaElement>) => void;
  stopCaseAgentResponse: () => void;
  agentMessagesEndRef: React.RefObject<HTMLDivElement | null>;
}

export const CaseAgentDrawer = ({
  agentOpen,
  agentRevealKey,
  agentIdleTab,
  openIdleAgent,
  agentTabAlert,
  closeCaseAgent,
  agentCase,
  agentStatus,
  agentLoading,
  agentSending,
  agentProgress,
  agentSkillId,
  setAgentSkillId,
  loadCaseAgent,
  openAgentFolder,
  agentConversations,
  conversationId,
  switchCaseConversation,
  createCaseConversation,
  agentState,
  agentDecisionLoading,
  decideCaseAgentAction,
  restoreCaseAgentAction,
  counselDetailCapabilities,
  agentHistoryExpanded,
  setAgentHistoryExpanded,
  sendCaseAgentMessage,
  agentMaterialPickerOpen,
  setAgentMaterialPickerOpen,
  toggleAgentMaterialPicker,
  agentDocuments,
  agentDocumentsLoading,
  agentDocumentIds,
  setAgentDocumentIds,
  updateAgentDocumentSelection,
  agentScreenshots,
  removeAgentScreenshot,
  agentScreenshotInputRef,
  uploadCaseAgentScreenshot,
  agentScreenshotUploading,
  agentInput,
  setAgentInput,
  pasteCaseAgentScreenshot,
  stopCaseAgentResponse,
  agentMessagesEndRef,
}: CaseAgentDrawerProps) => {
  // 501634：浮动确认窗口。currentId 是正在看的那项；minimizedIds 是点了“缩小”的（不算处理，仍待确认）。
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const [minimizedIds, setMinimizedIds] = useState<string[]>([]);
  // 换案件或重新打开智能体：缩小记录清空，还有待确认的会再弹出来。
  useEffect(() => { setConfirmOpen(false); setConfirmId(null); setMinimizedIds([]); }, [agentCase?.id, agentOpen]);
  // 按固定模板生成文书（陶国南 11-03）：说“生成撤诉申请书”或点按钮，打开模板填字段，不让智能体改写正文。
  const [wordTemplates, setWordTemplates] = useState<WordTemplate[]>([]);
  const [wordTemplate, setWordTemplate] = useState<{ open: boolean; id?: string }>({ open: false });
  useEffect(() => {
    if (!agentOpen) return;
    api.get<{ items: WordTemplate[] }>("/case-word-templates").then(({ data }) => setWordTemplates(data.items)).catch(() => setWordTemplates([]));
  }, [agentOpen]);
  const sendOrGenerate = (preset?: string) => {
    const hit = matchWordTemplate(preset ?? agentInput, wordTemplates);
    if (hit && !agentScreenshots.length) {
      if (preset === undefined) setAgentInput("");
      setWordTemplate({ open: true, id: hit.id });
      return Promise.resolve();
    }
    return sendCaseAgentMessage(preset);
  };
  // 501298：确认或驳回成功后卡片收起，对话里留一行结果；失败的留在卡片里写明原因。
  const [decisionFailures, setDecisionFailures] = useState<Record<string, string>>({});
  const decideAction = async (action: CaseAgentAction, decision: "approved" | "rejected") => {
    if (agentDecisionLoading) return;
    const failure = await decideCaseAgentAction(action, decision);
    setDecisionFailures((current) => {
      const next = { ...current };
      if (failure) next[action.id] = failure; else delete next[action.id];
      return next;
    });
  };
  // 正在执行的（可能是在智能体中心批准的）仍列在这里，按钮置灰。
  const waitingActions = (agentState?.pending_actions || []).filter((action) => action.status === "pending" || action.status === "executing");
  // 调度 11-05：在智能体中心处理掉的卡片，这里同步显示结果（执行失败也显示成结果行，不再留着可点的按钮）。
  const caseResultLine = (action: CaseAgentAction) => {
    const via = (action as { decided_via?: string }).decided_via === "agent_center" ? "（在智能体中心处理）" : "";
    if (action.status === "failed") return { text: `执行失败：${action.summary || "智能体操作"}${via}`, tone: "rejected" as const };
    const line = actionResultLine(action.status, action.summary);
    return line && { ...line, text: line.text + via };
  };
  const decidedActions = (agentState?.pending_actions || []).filter((action) => caseResultLine(action));
  // 501634：有新的待确认（没点过缩小的）就弹出浮动确认窗口；都处理完就关掉。
  const waitingKey = waitingActions.map((action) => action.id).join(",");
  useEffect(() => {
    if (!waitingActions.length) { setConfirmOpen(false); return; }
    const fresh = waitingActions.find((action) => !minimizedIds.includes(action.id));
    if (fresh && !confirmOpen) { setConfirmId(fresh.id); setConfirmOpen(true); }
  }, [waitingKey]); // eslint-disable-line react-hooks/exhaustive-deps
  const minimizeConfirm = () => { setMinimizedIds((current) => Array.from(new Set([...current, ...waitingActions.map((action) => action.id)]))); setConfirmOpen(false); };
  const openConfirm = () => { setConfirmId((current) => waitingActions.some((action) => action.id === current) ? current : waitingActions[0]?.id || null); setConfirmOpen(true); };
  const shownMessages = (agentHistoryExpanded ? agentState?.messages : agentState?.messages?.slice(-8)) || [];
  const firstShownAt = !agentHistoryExpanded && (agentState?.messages?.length || 0) > 8 ? shownMessages[0]?.created_at : undefined;
  const timeline = mergeByTime(shownMessages, decidedActions.filter((action) => !firstShownAt || !action.decided_at || Date.parse(action.decided_at) >= Date.parse(firstShownAt)),
    (item) => item.created_at, (action) => action.decided_at || action.requested_at);
  const actionDisabled = (action: CaseAgentAction) => Boolean(agentDecisionLoading) || Boolean((action as { preparing?: boolean }).preparing) || action.status === "executing" || (action.type !== "mcp.call" && !counselDetailCapabilities.can_write);
  const selectedSkill = (agentStatus?.skills || []).find((item) => item.id === agentSkillId);
  const quickPrompts = selectedSkill?.quick_prompts?.length
    ? selectedSkill.quick_prompts
    : ["概括案件现状", "检查最近期限风险", "汇总合同与费用", "列出尚未完成的任务"];
  return (
    // 501165：浮在案件页上的智能体窗口（右下角打开，可拖动、调大小、放大、收起），替代原来带遮罩的抽屉。
    <CaseAgentDock
      open={agentOpen}
      revealKey={agentRevealKey}
      idleTab={agentIdleTab}
      onExpandIdle={openIdleAgent}
      tabAlert={agentTabAlert}
      pendingCount={waitingActions.length}
      title={<span><AgentIcon size={20} /> 案件智能体：{agentCase?.serial_no || ""}</span>}
      onClose={closeCaseAgent}
    >
      <div className="case-agent-panel" data-testid="case-agent-panel">
        {/* 501170（tgn 08:30）：小窗口里头部只留一行小工具：文件夹、会话、新建会话、办公技能、案件材料；
            服务状态、模型、记忆和审批说明收进“ⓘ”，把高度留给对话。 */}
        <div className="case-agent-toolbar" role="toolbar" aria-label="案件智能体工具">
          <Tooltip title="案件智能体文件夹"><Button type="text" size="small" icon={<FolderOpenOutlined />} aria-label="案件智能体文件夹" onClick={openAgentFolder} /></Tooltip>
          {/* tgn 08:33：“新会话”和“新建会话”合成一个“会话”入口：点开新建或切换；新建不再弹名称输入框（钉钉里会被拦下，看着没反应）。 */}
          <Dropdown trigger={["click"]} menu={{
            selectable: true, selectedKeys: conversationId ? [String(conversationId)] : [],
            items: [{ key: "new", icon: <PlusOutlined />, label: "新建会话" }, ...(agentConversations.length ? [{ type: "divider" as const }] : []),
              ...agentConversations.map((item) => ({ key: String(item.id), label: item.title }))],
            onClick: ({ key }) => key === "new" ? void createCaseConversation(caseConversationTitle()) : switchCaseConversation(Number(key)),
          }}>
            <Button size="small" className="case-agent-conversation-trigger" icon={<MessageOutlined />} aria-label="会话">
              <span>{agentConversations.find((item) => item.id === conversationId)?.title || "会话"}</span><DownOutlined />
            </Button>
          </Dropdown>
          <Tooltip title={(agentStatus?.skills || []).find((item) => item.id === agentSkillId)?.description || "选择本轮对话使用的办公技能"}>
            <Select size="small" className="case-agent-toolbar-select" aria-label="办公技能" popupMatchSelectWidth={false} value={agentSkillId} allowClear onChange={value => setAgentSkillId(value ?? "")}
              options={[NO_AGENT_SKILL_OPTION, ...(agentStatus?.skills || []).map((item) => ({ value: item.id, label: `${item.name}${item.available ? "" : "（待配置）"}`, disabled: !item.available }))]} />
          </Tooltip>
          <Tooltip title="选择随本轮问题发送的案件材料"><Button type="text" size="small" className="case-agent-composer-material-trigger" icon={agentMaterialPickerOpen ? <FolderOpenOutlined /> : <FolderOutlined />} aria-label="案件材料" aria-expanded={agentMaterialPickerOpen} onClick={toggleAgentMaterialPicker}>{agentDocumentIds.length ? agentDocumentIds.length : null}</Button></Tooltip>
          <Popover trigger="click" placement="bottomRight" title="智能体状态" content={<div className="case-agent-status-popover">
            <Space size={[6, 6]} wrap>
              <Tag color={agentStatus?.ready ? "success" : "warning"}>{agentStatus?.ready ? "服务正常" : agentLoading && !agentStatus ? "正在检查服务" : "服务未就绪"}</Tag>
              <Tag>{agentStatus?.model || (agentLoading ? "正在读取配置" : "模型未配置")}</Tag>
              <Tag color={agentStatus?.checkpoint_backend === "postgresql" ? "blue" : "default"}>案件独立记忆</Tag>
              {agentStatus?.write_requires_approval && <Tag color="gold">人工审批</Tag>}
            </Space>
            <Button size="small" icon={<ReloadOutlined />} loading={agentLoading} onClick={() => agentCase && void loadCaseAgent(agentCase)}>刷新智能体状态</Button>
          </div>}>
            <Button type="text" size="small" icon={<InfoCircleOutlined />} aria-label="智能体状态" className={agentStatus && !agentStatus.ready ? "is-warning" : undefined} />
          </Popover>
        </div>
        {!agentLoading && !agentStatus?.ready && <Alert type="warning" showIcon title="案件智能体暂未就绪" description="请检查模型与 DPH 运行环境后重试。" />}
        {/* 501634：待确认的卡片不再夹在对话里，缩小后这里显示入口，点开浮动确认窗口。 */}
        {waitingActions.length && !confirmOpen ? <button type="button" className="case-agent-pending-pill" onClick={openConfirm}>
          <span className="agent-pending-tag">待确认 {waitingActions.length}</span>
          <span>有 {waitingActions.length} 项操作等你确认，点击处理</span>
        </button> : null}
        {confirmOpen && <CaseAgentConfirmFloat actions={[...waitingActions].reverse()} currentId={confirmId} target={agentCase?.serial_no}
          failures={decisionFailures} decisionLoading={agentDecisionLoading} disabled={actionDisabled}
          onSelect={setConfirmId} onDecide={(action, decision) => void decideAction(action, decision)} onMinimize={minimizeConfirm} />}
        <div className="case-agent-messages" aria-live="polite">
          {!agentLoading && !agentState?.messages?.length && <div className="case-agent-empty">
            <AgentMascot pose="wave" height={110} blink className="case-agent-empty-mascot" />
            <strong>可以开始分析这个案件</strong>
            <span>智能体仅使用你有权查看的案件空间数据。</span>
          </div>}
          {!agentHistoryExpanded && (agentState?.messages?.length || 0) > 8 && <Button className="case-agent-history-toggle" type="link" size="small" onClick={() => setAgentHistoryExpanded(true)}>查看更早记录</Button>}
          {timeline.map((row) => {
            if (row.kind === "action") {
              const action = row.item, line = caseResultLine(action)!;
              return <div key={`action-${action.id}`} className={`agent-action-result is-${line.tone}`} role="status">
                {line.tone === "done" ? <CheckOutlined /> : <CloseOutlined />}<span title={line.text}>{line.text}</span>
                {action.status === "approved" && action.type.endsWith(".delete") && <Button type="link" size="small" loading={agentDecisionLoading === action.id} onClick={() => void restoreCaseAgentAction(action)}>恢复</Button>}
              </div>;
            }
            const item = row.item, index = row.index;
            return <div className={`case-agent-message case-agent-message-${item.role}`} key={item.id || `${item.role}-${index}`}>
            <div className="case-agent-message-meta">{item.role === "user" ? "我" : "案件智能体"}{item.created_at ? ` · ${item.created_at.replace("T", " ").slice(0, 16)}` : ""}</div>
            <div className="case-agent-bubble">{item.attachments?.length ? <div className="case-agent-message-attachments">{item.attachments.map((attachment) => attachment.preview_url ? <figure key={attachment.id}><Image src={attachment.preview_url} alt={attachment.name} preview /><figcaption>{attachment.name}</figcaption></figure> : <Tag key={attachment.id}>{attachment.name}</Tag>)}</div> : null}{item.content}</div>
          </div>;
          })}
          {(agentLoading || agentSending) && <div className="case-agent-thinking"><AgentMascot pose="think" height={30} bob /> {agentSending ? (agentProgress || "正在理解您的问题…") : "正在载入会话..."}</div>}
          <AgentToolResult result={[agentState?.structured_results, ...(agentState?.pending_actions || []).filter((item) => item.status === "approved").map((item) => item.execution_result)]} />
          <div ref={agentMessagesEndRef} />
        </div>
        {!agentLoading && !agentState?.messages?.length && agentStatus?.ready && <div className="case-agent-suggestions">
          {quickPrompts.map((text) => <Button key={text} size="small" onClick={() => void sendOrGenerate(text)}>{text}</Button>)}
        </div>}
        <div className="case-agent-composer">
          {agentMaterialPickerOpen && <div className="case-agent-material-tree" aria-label="从案件文件夹选择本轮材料">
            <div className="case-agent-material-tree-header">
              <strong>从案件文件夹选择</strong>
              <Space size={2}>
                <Button type="link" size="small" onClick={() => { if (agentDocuments.length > AGENT_DOCUMENT_LIMIT) message.info(`已选择前 ${AGENT_DOCUMENT_LIMIT} 份材料`); setAgentDocumentIds(agentDocuments.slice(0, AGENT_DOCUMENT_LIMIT).map((item) => item.id)); }}>全选</Button>
                <Button type="link" size="small" disabled={!agentDocumentIds.length} onClick={() => setAgentDocumentIds([])}>清空</Button>
                <Button type="text" size="small" icon={<CloseOutlined />} title="收起材料选择" aria-label="收起材料选择" onClick={() => setAgentMaterialPickerOpen(false)} />
              </Space>
            </div>
            {agentDocumentsLoading ? <div className="case-agent-material-loading">正在加载案件材料...</div> : <Tree checkable selectable={false} defaultExpandAll checkedKeys={agentDocumentIds.map((id) => `document:${id}`)} treeData={buildAgentDocumentTree(agentDocuments)} onCheck={updateAgentDocumentSelection} />}
            <small>仅发送本轮勾选且当前账号有权查看的材料，最多 {AGENT_DOCUMENT_LIMIT} 份。</small>
          </div>}
          {!!agentDocumentIds.length && <div className="case-agent-composer-materials" aria-label="随本轮问题发送的案件材料">
            <div className="case-agent-composer-material-tags">
              {agentDocuments.filter((item) => agentDocumentIds.includes(item.id)).map((item) => <Tag key={item.id} closable title={item.original_name} onClose={(event) => { event.preventDefault(); setAgentDocumentIds((current) => current.filter((id) => id !== item.id)); }}>{item.original_name}</Tag>)}
            </div>
          </div>}
          {agentScreenshots.length ? <div className="case-agent-composer-attachments" aria-label="待发送截图">{agentScreenshots.map((item) => <div key={item.id}><Image src={item.preview_url} alt={item.name} preview /><span title={item.name}>{item.name}</span><Button type="text" icon={<CloseOutlined />} title="移除截图" onClick={() => removeAgentScreenshot(item)} /></div>)}</div> : null}
          <input ref={agentScreenshotInputRef} hidden type="file" accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp" onChange={(event) => void uploadCaseAgentScreenshot(event.target.files?.[0])} />
          <Button className="case-agent-composer-upload" type="text" icon={<PaperClipOutlined />} title="上传截图" loading={agentScreenshotUploading} disabled={agentLoading || !agentStatus?.ready || agentScreenshots.length >= 4} onClick={() => agentScreenshotInputRef.current?.click()} />
          <Button className="case-agent-composer-upload" type="text" icon={<FileWordOutlined />} title="按模板生成文书" aria-label="按模板生成文书"
            disabled={!agentCase} onClick={() => setWordTemplate({ open: true })} />
          <Input.TextArea
            value={agentInput}
            autoSize={{ minRows: 2, maxRows: 5 }}
            placeholder={agentSkillId === "screenshot-evidence" ? "可直接粘贴截图，并补充需要核验的问题" : "询问案件信息，也可直接粘贴截图"}
            disabled={agentLoading || !agentStatus?.ready}
            onChange={(event) => setAgentInput(event.target.value)}
            onPaste={pasteCaseAgentScreenshot}
            onPressEnter={(event) => {
              if (!event.shiftKey) {
                event.preventDefault();
                void sendOrGenerate();
              }
            }}
          />
          <Button type="primary" icon={agentSending && !agentInput.trim() && !agentScreenshots.length ? <StopOutlined /> : <SendOutlined />} disabled={agentLoading || !agentStatus?.ready || (!agentSending && !agentInput.trim() && !agentScreenshots.length)} title={agentSending && !agentInput.trim() && !agentScreenshots.length ? "停止生成" : agentSending ? "发送引导并打断当前生成" : "发送"} onClick={() => agentSending && !agentInput.trim() && !agentScreenshots.length ? stopCaseAgentResponse() : void sendOrGenerate()} />
        </div>
        <CaseWordTemplateModal caseId={agentCase?.id ?? null} open={wordTemplate.open} templateId={wordTemplate.id} canSave
          onClose={() => setWordTemplate({ open: false })} />
      </div>
    </CaseAgentDock>
  );
};
