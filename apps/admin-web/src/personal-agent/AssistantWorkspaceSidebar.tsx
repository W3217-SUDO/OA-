import { Button, Tooltip } from "antd";
import { ArrowLeftOutlined, ExperimentOutlined, FileOutlined, FolderOpenOutlined, ReloadOutlined, RobotOutlined } from "@ant-design/icons";
import { ConfirmationHistory } from "./ConfirmationHistory";
import { ConversationManager } from "./ConversationManager";
import type { ConfirmationDetail } from "./types";
import type { usePersonalWorkspace } from "./usePersonalWorkspace";

type Props = {
  workspace: ReturnType<typeof usePersonalWorkspace>;
  name: string;
  logoSrc?: string;
  onOpenPersonalSpace: () => void;
  onOpenCases: () => void;
  onOpenCaseMaterials: () => void;
  onImportSkills: () => void;
  onOpenAgentCenter?: () => void;
  onReopenConfirmation: (detail: ConfirmationDetail) => Promise<void>;
  onReturnWorkbench?: () => void;
};

export function AssistantWorkspaceSidebar({ workspace, name, logoSrc, onOpenPersonalSpace, onOpenCases, onOpenCaseMaterials, onImportSkills, onOpenAgentCenter, onReopenConfirmation, onReturnWorkbench }: Props) {
  const busy = workspace.loading || workspace.stopping || workspace.uploading || !!workspace.decisionId || workspace.conversationBusy;
  const canUseCases = workspace.status?.commands.some((item) => item.id === "cases") === true;
  const caseAccessHint = workspace.loading ? "正在加载案件访问权限" : workspace.loadError ? "工作区加载失败，请先重试" : canUseCases ? "选择可访问的案件" : "当前没有案件访问权限";
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
      listClassName="assistant-conversation-list"
      rowClassName="assistant-conversation-row"
      selectClassName="assistant-conversation-select"
      navigation={<>
        <Button type="text" className="assistant-workspace-personal-entry" icon={<FolderOpenOutlined />} onClick={onOpenPersonalSpace}>个人空间</Button>
        <Tooltip title={caseAccessHint}>
          <Button type="text" className="assistant-workspace-case-entry" icon={<FolderOpenOutlined />} disabled={busy || !!workspace.loadError || !canUseCases} onClick={onOpenCases}>案件空间</Button>
        </Tooltip>
        {canUseCases && workspace.selectedCase && <Tooltip title={`${workspace.selectedCase.serial_no} · ${workspace.selectedCase.title}`}>
          <Button type="text" className="assistant-workspace-case-materials" icon={<FileOutlined />} disabled={busy || !!workspace.loadError} onClick={onOpenCaseMaterials} aria-label={`选择案件材料：${workspace.selectedCase.serial_no}`}>
            <span>{workspace.selectedCase.serial_no}</span>
          </Button>
        </Tooltip>}
        <ConfirmationHistory onReopen={onReopenConfirmation} busy={busy || !!workspace.dismissalId} />
        <Button type="text" icon={<ExperimentOutlined />} aria-label="导入技能" disabled={busy} onClick={onImportSkills}>导入技能</Button>
        {onOpenAgentCenter && <Button type="text" icon={<RobotOutlined />} onClick={onOpenAgentCenter}>智能体中心</Button>}
      </>}
    />
    <div className="assistant-workspace-footer">
      <Tooltip title="刷新智能体"><Button type="text" icon={<ReloadOutlined />} aria-label="刷新智能体" disabled={workspace.loading || !!workspace.runningIds.length} onClick={() => void workspace.load()}>刷新智能体</Button></Tooltip>
      {onReturnWorkbench && <Button type="text" icon={<ArrowLeftOutlined />} onClick={onReturnWorkbench}>返回工作台</Button>}
    </div>
  </aside>;
}
