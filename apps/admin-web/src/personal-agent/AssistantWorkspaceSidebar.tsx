import { Button, Tooltip } from "antd";
import { message } from "antd";
import { ArrowLeftOutlined, ExperimentOutlined, FolderOpenOutlined, InboxOutlined, ReloadOutlined, RobotOutlined, SettingOutlined } from "@ant-design/icons";
import { ConfirmationHistory } from "./ConfirmationHistory";
import { ConversationManager } from "./ConversationManager";
import { ConversationWorkspaceNavigation } from "./ConversationWorkspaceNavigation";
import type { ConfirmationDetail } from "./types";
import type { CaseAgentConversationSummary } from "./types";
import type { usePersonalWorkspace } from "./usePersonalWorkspace";

type Props = {
  workspace: ReturnType<typeof usePersonalWorkspace>;
  name: string;
  logoSrc?: string;
  onOpenPersonalSpace: () => void;
  onOpenMemory: () => void;
  onImportSkills: () => void;
  onOpenAgentCenter?: () => void;
  onReopenConfirmation: (detail: ConfirmationDetail) => Promise<void>;
  onReturnWorkbench?: () => void;
  onOpenCaseAgentConversation?: (item: CaseAgentConversationSummary) => void;
};

export function AssistantWorkspaceSidebar({ workspace, name, logoSrc, onOpenPersonalSpace, onOpenMemory, onImportSkills, onOpenAgentCenter, onReopenConfirmation, onReturnWorkbench, onOpenCaseAgentConversation }: Props) {
  const busy = workspace.loading || workspace.stopping || workspace.uploading || !!workspace.decisionId || workspace.conversationBusy;
  return <aside className="assistant-workspace-sidebar" aria-label="AI 工作区导航">
    <div className="assistant-workspace-brand">
      {logoSrc && <img src={logoSrc} alt="" width={32} height={32} />}
      <span>{name}</span>
    </div>
    <ConversationManager
      presentation="sidebar"
      items={workspace.conversations}
      loading={workspace.loading}
      activeId={workspace.state.conversation_id}
      busy={workspace.loading || workspace.conversationBusy}
      runningIds={workspace.runningIds}
      onCreate={workspace.createConversation}
      onSelect={workspace.selectConversation}
      onDelete={workspace.deleteConversation}
      caseAgentConversations={workspace.caseAgentConversations}
      onSelectCaseAgentConversation={onOpenCaseAgentConversation}
      listClassName="assistant-conversation-list"
      rowClassName="assistant-conversation-row"
      selectClassName="assistant-conversation-select"
      navigation={<>
        <Button type="text" icon={<InboxOutlined />} aria-label="收文助手" disabled={busy || !workspace.courtIntakeAvailable} onClick={() => void workspace.startCourtIntake().catch((error: Error) => message.warning(error.message))}>收文助手</Button>
        <Button type="text" className="assistant-workspace-generated-entry" icon={<FolderOpenOutlined />} onClick={onOpenPersonalSpace}>AI生成文件夹</Button>
        <Button type="text" icon={<SettingOutlined />} aria-label="记忆管理" onClick={onOpenMemory}>记忆管理</Button>
        <ConfirmationHistory onReopen={onReopenConfirmation} busy={busy || !!workspace.dismissalId} />
        <Button type="text" icon={<ExperimentOutlined />} aria-label="导入技能" disabled={busy} onClick={onImportSkills}>导入技能</Button>
        {onOpenAgentCenter && <Button type="text" icon={<RobotOutlined />} onClick={onOpenAgentCenter}>智能体设置</Button>}
        <ConversationWorkspaceNavigation workspace={workspace} />
      </>}
    />
    <div className="assistant-workspace-footer">
      <Tooltip title="刷新智能体"><Button type="text" icon={<ReloadOutlined />} aria-label="刷新智能体" disabled={workspace.loading || !!workspace.runningIds.length} onClick={() => void workspace.load()}>刷新智能体</Button></Tooltip>
      {onReturnWorkbench && <Button type="text" icon={<ArrowLeftOutlined />} onClick={onReturnWorkbench}>返回工作台</Button>}
    </div>
  </aside>;
}
