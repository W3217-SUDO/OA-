import { POPUP_WIDTH } from "../components/common/popupSize";
import { CaseAgentDock } from "./CaseAgentDock";
import { StatusTag } from "../components/common/StatusTag";
import {
CloseOutlined,
DownOutlined,
FolderOpenOutlined,
FolderOutlined,
InfoCircleOutlined,
MessageOutlined,
PaperClipOutlined,
PlusOutlined,
ReloadOutlined,
RobotOutlined,
SendOutlined,
StopOutlined,
} from "@ant-design/icons";
import { Alert,Button,Dropdown,Image,Input,message,Modal,Popover,Select,Space,Tag,Tooltip,Tree } from "antd";
import { useEffect, useState } from "react";
import { AgentOperationPreview, agentOperationName, hasAgentOperationPreview } from "../AgentOperationPreview";
import { AgentToolResult } from "../AgentToolResult";
import { NO_AGENT_SKILL_OPTION } from "../agentSkillRouting";
import type { ClipboardEvent,Key,PointerEvent as ReactPointerEvent } from "react";
import {
AGENT_DOCUMENT_LIMIT,
buildAgentDocumentTree,
} from "./constants";
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
  closeCaseAgent: () => void;
  agentCase: CaseRow | null;
  agentDrawerWidth: number;
  startAgentDrawerResize: (event: ReactPointerEvent<HTMLDivElement>) => void;
  agentStatus: CaseAgentStatus | null;
  agentLoading: boolean;
  agentSending: boolean;
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
  decideCaseAgentAction: (action: CaseAgentAction, decision: "approved" | "rejected") => Promise<unknown>;
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
  closeCaseAgent,
  agentCase,
  agentStatus,
  agentLoading,
  agentSending,
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
  const [activeAction, setActiveAction] = useState<CaseAgentAction | null>(null);
  useEffect(() => { setActiveAction(null); }, [agentCase?.id, agentOpen]);
  const decideActiveAction = async (decision: "approved" | "rejected") => {
    if (!activeAction || agentDecisionLoading) return;
    await decideCaseAgentAction(activeAction, decision);
    setActiveAction(null);
  };
  const actionDisabled = (action: CaseAgentAction) => Boolean(agentDecisionLoading) || (action.type !== "mcp.call" && !counselDetailCapabilities.can_write);
  const selectedSkill = (agentStatus?.skills || []).find((item) => item.id === agentSkillId);
  const quickPrompts = selectedSkill?.quick_prompts?.length
    ? selectedSkill.quick_prompts
    : ["概括案件现状", "检查最近期限风险", "汇总合同与费用", "列出尚未完成的任务"];
  return (
    // 501165：浮在案件页上的智能体窗口（右下角打开，可拖动、调大小、放大、收起），替代原来带遮罩的抽屉。
    <CaseAgentDock
      open={agentOpen}
      revealKey={agentRevealKey}
      title={<span><RobotOutlined /> 案件智能体：{agentCase?.serial_no || ""}</span>}
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
        {agentState?.pending_actions?.length ? <section className="case-agent-actions">
          <div className="case-agent-section-title">待审批操作</div>
          <Alert type="info" showIcon title="写入须人工确认后执行，原业务权限与审批规则不变。" />
          {[...agentState.pending_actions].reverse().map((action) => <div className="case-agent-action" key={action.id}>
            <div>
              <strong>{action.summary}</strong>
              <span>{agentOperationName(action)}</span>
            </div>
            {action.status === "pending" ? <Space>
              <Button size="small" type="primary" disabled={actionDisabled(action)} loading={agentDecisionLoading === action.id} onClick={() => setActiveAction(action)}>查看并确认</Button>
            </Space> : <Space>
              <StatusTag status={action.status} tone={action.status === "approved" ? "success" : action.status === "restored" ? "processing" : "danger"} label={action.status === "approved" ? "已批准" : action.status === "restored" ? "已恢复" : "已驳回"} />
              {action.status === "approved" && action.type.endsWith(".delete") && <Button size="small" loading={agentDecisionLoading === action.id} onClick={() => void restoreCaseAgentAction(action)}>恢复</Button>}
            </Space>}
          </div>)}
        </section> : null}
        <Modal open={Boolean(activeAction)} title="案件智能体操作确认" width={POPUP_WIDTH.md} maskClosable={!agentDecisionLoading} onCancel={() => { if (!agentDecisionLoading) setActiveAction(null); }} footer={activeAction ? [
          <Button key="reject" danger icon={<CloseOutlined />} disabled={actionDisabled(activeAction)} onClick={() => void decideActiveAction("rejected")}>驳回，不修改</Button>,
          <Button key="approve" type="primary" disabled={actionDisabled(activeAction) || !hasAgentOperationPreview(activeAction)} loading={agentDecisionLoading === activeAction.id} onClick={() => void decideActiveAction("approved")}>批准并执行</Button>,
        ] : null}>
          {activeAction && <div style={{ maxHeight: "60dvh", overflowY: "auto" }}><AgentOperationPreview action={activeAction} target={agentCase?.serial_no} /></div>}
        </Modal>
        <div className="case-agent-messages" aria-live="polite">
          {!agentLoading && !agentState?.messages?.length && <div className="case-agent-empty">
            <div className="case-agent-empty-icon"><RobotOutlined /></div>
            <strong>可以开始分析这个案件</strong>
            <span>智能体仅使用你有权查看的案件空间数据。</span>
          </div>}
          {!agentHistoryExpanded && (agentState?.messages?.length || 0) > 8 && <Button className="case-agent-history-toggle" type="link" size="small" onClick={() => setAgentHistoryExpanded(true)}>查看更早记录</Button>}
          {(agentHistoryExpanded ? agentState?.messages : agentState?.messages?.slice(-8))?.map((item, index) => <div className={`case-agent-message case-agent-message-${item.role}`} key={item.id || `${item.role}-${index}`}>
            <div className="case-agent-message-meta">{item.role === "user" ? "我" : "案件智能体"}{item.created_at ? ` · ${item.created_at.replace("T", " ").slice(0, 16)}` : ""}</div>
            <div className="case-agent-bubble">{item.attachments?.length ? <div className="case-agent-message-attachments">{item.attachments.map((attachment) => attachment.preview_url ? <figure key={attachment.id}><Image src={attachment.preview_url} alt={attachment.name} preview /><figcaption>{attachment.name}</figcaption></figure> : <Tag key={attachment.id}>{attachment.name}</Tag>)}</div> : null}{item.content}</div>
          </div>)}
          {(agentLoading || agentSending) && <div className="case-agent-thinking"><RobotOutlined /> {agentSending ? "正在分析案件空间..." : "正在载入会话..."}</div>}
          <AgentToolResult result={[agentState?.structured_results, ...(agentState?.pending_actions || []).filter((item) => item.status === "approved").map((item) => item.execution_result)]} />
          <div ref={agentMessagesEndRef} />
        </div>
        {!agentLoading && !agentState?.messages?.length && agentStatus?.ready && <div className="case-agent-suggestions">
          {quickPrompts.map((text) => <Button key={text} size="small" onClick={() => void sendCaseAgentMessage(text)}>{text}</Button>)}
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
                void sendCaseAgentMessage();
              }
            }}
          />
          <Button type="primary" icon={agentSending && !agentInput.trim() && !agentScreenshots.length ? <StopOutlined /> : <SendOutlined />} disabled={agentLoading || !agentStatus?.ready || (!agentSending && !agentInput.trim() && !agentScreenshots.length)} title={agentSending && !agentInput.trim() && !agentScreenshots.length ? "停止生成" : agentSending ? "发送引导并打断当前生成" : "发送"} onClick={() => agentSending && !agentInput.trim() && !agentScreenshots.length ? stopCaseAgentResponse() : void sendCaseAgentMessage()} />
        </div>
      </div>
    </CaseAgentDock>
  );
};
