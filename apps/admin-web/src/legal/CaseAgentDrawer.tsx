import {
CloseOutlined,
FolderOpenOutlined,
FolderOutlined,
PaperClipOutlined,
ReloadOutlined,
RobotOutlined,
SendOutlined,
StopOutlined,
} from "@ant-design/icons";
import { Alert,Button,Drawer,Image,Input,message,Select,Space,Tag,Tree } from "antd";
import type { ClipboardEvent,Key,PointerEvent as ReactPointerEvent } from "react";
import {
AGENT_DOCUMENT_LIMIT,
buildAgentDocumentTree,
} from "./constants";
import type {
CaseAgentAction,
CaseAgentAttachment,
CaseAgentDocument,
CaseAgentState,
CaseAgentStatus,
CaseDetailCapabilities,
CaseRow
} from "./types";

interface CaseAgentDrawerProps {
  agentOpen: boolean;
  setAgentOpen: (open: boolean) => void;
  agentCase: CaseRow | null;
  agentDrawerWidth: number;
  startAgentDrawerResize: (event: ReactPointerEvent<HTMLDivElement>) => void;
  agentStatus: CaseAgentStatus | null;
  agentLoading: boolean;
  agentSending: boolean;
  agentSkillId: string;
  setAgentSkillId: (id: string) => void;
  loadCaseAgent: (row: CaseRow, resetMaterials?: boolean) => Promise<unknown>;
  agentState: CaseAgentState | null;
  agentDecisionLoading: string;
  decideCaseAgentAction: (action: CaseAgentAction, decision: "approved" | "rejected") => Promise<unknown>;
  counselDetailCapabilities: CaseDetailCapabilities;
  agentHistoryExpanded: boolean;
  setAgentHistoryExpanded: (expanded: boolean) => void;
  sendCaseAgentMessage: (preset?: string) => Promise<unknown>;
  agentMaterialPickerOpen: boolean;
  setAgentMaterialPickerOpen: (open: boolean | ((current: boolean) => boolean)) => void;
  agentDocuments: CaseAgentDocument[];
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
  setAgentOpen,
  agentCase,
  agentDrawerWidth,
  startAgentDrawerResize,
  agentStatus,
  agentLoading,
  agentSending,
  agentSkillId,
  setAgentSkillId,
  loadCaseAgent,
  agentState,
  agentDecisionLoading,
  decideCaseAgentAction,
  counselDetailCapabilities,
  agentHistoryExpanded,
  setAgentHistoryExpanded,
  sendCaseAgentMessage,
  agentMaterialPickerOpen,
  setAgentMaterialPickerOpen,
  agentDocuments,
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
  return (
    <Drawer
      className="case-agent-drawer"
      width={agentDrawerWidth}
      open={agentOpen}
      title={<span><RobotOutlined /> 案件智能体：{agentCase?.serial_no || ""}</span>}
      onClose={() => setAgentOpen(false)}
      destroyOnHidden
    >
      <div className="case-agent-resize-handle" role="separator" aria-label="拖动调整智能体宽度" onPointerDown={startAgentDrawerResize} />
      <div className="case-agent-panel" data-testid="case-agent-panel">
        <div className="case-agent-status">
          <Space size={[6, 6]} wrap>
            <Tag color={agentStatus?.ready ? "success" : "warning"}>{agentStatus?.ready ? "服务正常" : "服务未就绪"}</Tag>
            <Tag>{agentStatus?.model || "模型未配置"}</Tag>
            <Tag color={agentStatus?.checkpoint_backend === "postgresql" ? "blue" : "default"}>案件独立记忆</Tag>
            {agentStatus?.write_requires_approval && <Tag color="gold">人工审批</Tag>}
          </Space>
          <Button type="text" size="small" icon={<ReloadOutlined />} loading={agentLoading} title="刷新智能体状态" onClick={() => agentCase && void loadCaseAgent(agentCase)} />
        </div>
        <div className="case-agent-skill-select">
          <span>办公技能</span>
          <Select
            value={agentSkillId}
            onChange={setAgentSkillId}
            options={(agentStatus?.skills || []).map((item) => ({ value: item.id, label: `${item.name}${item.available ? "" : "（待配置）"}`, disabled: !item.available }))}
          />
          <small>{(agentStatus?.skills || []).find((item) => item.id === agentSkillId)?.description || "选择本轮对话使用的办公技能"}</small>
        </div>
        {!agentLoading && !agentStatus?.ready && <Alert type="warning" showIcon title="案件智能体暂未就绪" description="请检查模型与 LangGraph 服务配置后重试。" />}
        {agentState?.pending_actions?.length ? <section className="case-agent-actions">
          <div className="case-agent-section-title">待审批操作</div>
          <Alert type="info" showIcon title="批准只记录人工审批决定，当前不会自动改写案件业务数据。" />
          {[...agentState.pending_actions].reverse().map((action) => <div className="case-agent-action" key={action.id}>
            <div>
              <strong>{action.summary}</strong>
              <span>{action.type}</span>
            </div>
            {action.status === "pending" ? <Space>
              <Button size="small" type="primary" disabled={!counselDetailCapabilities.can_write} loading={agentDecisionLoading === action.id} onClick={() => void decideCaseAgentAction(action, "approved")}>批准</Button>
              <Button size="small" danger icon={<CloseOutlined />} disabled={!counselDetailCapabilities.can_write} onClick={() => void decideCaseAgentAction(action, "rejected")}>驳回</Button>
            </Space> : <Tag color={action.status === "approved" ? "success" : "error"}>{action.status === "approved" ? "已批准" : "已驳回"}</Tag>}
          </div>)}
        </section> : null}
        <div className="case-agent-messages" aria-live="polite">
          {!agentLoading && !agentState?.messages?.length && <div className="case-agent-empty">
            <RobotOutlined />
            <strong>可以开始分析这个案件</strong>
            <span>智能体仅使用你有权查看的案件空间数据。</span>
          </div>}
          {!agentHistoryExpanded && (agentState?.messages?.length || 0) > 8 && <Button className="case-agent-history-toggle" type="link" size="small" onClick={() => setAgentHistoryExpanded(true)}>查看更早记录</Button>}
          {(agentHistoryExpanded ? agentState?.messages : agentState?.messages?.slice(-8))?.map((item, index) => <div className={`case-agent-message case-agent-message-${item.role}`} key={item.id || `${item.role}-${index}`}>
            <div className="case-agent-message-meta">{item.role === "user" ? "我" : "案件智能体"}{item.created_at ? ` · ${item.created_at.replace("T", " ").slice(0, 16)}` : ""}</div>
            <div className="case-agent-bubble">{item.attachments?.length ? <div className="case-agent-message-attachments">{item.attachments.map((attachment) => attachment.preview_url ? <figure key={attachment.id}><Image src={attachment.preview_url} alt={attachment.name} preview /><figcaption>{attachment.name}</figcaption></figure> : <Tag key={attachment.id}>{attachment.name}</Tag>)}</div> : null}{item.content}</div>
          </div>)}
          {(agentLoading || agentSending) && <div className="case-agent-thinking"><RobotOutlined /> {agentSending ? "正在分析案件空间..." : "正在载入会话..."}</div>}
          <div ref={agentMessagesEndRef} />
        </div>
        {!agentState?.messages?.length && agentStatus?.ready && <div className="case-agent-suggestions">
          {["概括案件现状", "检查最近期限风险", "汇总合同与费用", "列出尚未完成的任务"].map((text) => <Button key={text} size="small" onClick={() => void sendCaseAgentMessage(text)}>{text}</Button>)}
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
            <Tree checkable selectable={false} defaultExpandAll checkedKeys={agentDocumentIds.map((id) => `document:${id}`)} treeData={buildAgentDocumentTree(agentDocuments)} onCheck={updateAgentDocumentSelection} />
            <small>仅发送本轮勾选且当前账号有权查看的材料，最多 {AGENT_DOCUMENT_LIMIT} 份。</small>
          </div>}
          <div className="case-agent-composer-materials" aria-label="随本轮问题发送的案件材料">
            <Button type="text" size="small" className="case-agent-composer-material-trigger" icon={agentMaterialPickerOpen ? <FolderOpenOutlined /> : <FolderOutlined />} aria-expanded={agentMaterialPickerOpen} onClick={() => setAgentMaterialPickerOpen((current) => !current)}>案件材料</Button>
            <div className="case-agent-composer-material-tags">
              {agentDocuments.filter((item) => agentDocumentIds.includes(item.id)).map((item) => <Tag key={item.id} closable title={item.original_name} onClose={(event) => { event.preventDefault(); setAgentDocumentIds((current) => current.filter((id) => id !== item.id)); }}>{item.original_name}</Tag>)}
              {!agentDocumentIds.length && <span>选择后随本轮问题一起发送</span>}
            </div>
          </div>
          {agentScreenshots.length ? <div className="case-agent-composer-attachments" aria-label="待发送截图">{agentScreenshots.map((item) => <div key={item.id}><Image src={item.preview_url} alt={item.name} preview /><span title={item.name}>{item.name}</span><Button type="text" icon={<CloseOutlined />} title="移除截图" onClick={() => removeAgentScreenshot(item)} /></div>)}</div> : null}
          <input ref={agentScreenshotInputRef} hidden type="file" accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp" onChange={(event) => void uploadCaseAgentScreenshot(event.target.files?.[0])} />
          <Button className="case-agent-composer-upload" type="text" icon={<PaperClipOutlined />} title="上传截图" loading={agentScreenshotUploading} disabled={!agentStatus?.ready || agentScreenshots.length >= 4} onClick={() => agentScreenshotInputRef.current?.click()} />
          <Input.TextArea
            value={agentInput}
            autoSize={{ minRows: 2, maxRows: 5 }}
            placeholder={agentSkillId === "screenshot-evidence" ? "可直接粘贴截图，并补充需要核验的问题" : "询问案件信息，也可直接粘贴截图"}
            disabled={!agentStatus?.ready}
            onChange={(event) => setAgentInput(event.target.value)}
            onPaste={pasteCaseAgentScreenshot}
            onPressEnter={(event) => {
              if (!event.shiftKey) {
                event.preventDefault();
                void sendCaseAgentMessage();
              }
            }}
          />
          <Button type="primary" icon={agentSending && !agentInput.trim() && !agentScreenshots.length ? <StopOutlined /> : <SendOutlined />} disabled={!agentStatus?.ready || (!agentSending && !agentInput.trim() && !agentScreenshots.length)} title={agentSending && !agentInput.trim() && !agentScreenshots.length ? "停止生成" : agentSending ? "发送引导并打断当前生成" : "发送"} onClick={() => agentSending && !agentInput.trim() && !agentScreenshots.length ? stopCaseAgentResponse() : void sendCaseAgentMessage()} />
        </div>
      </div>
    </Drawer>
  );
};
