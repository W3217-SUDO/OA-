import type { ReactNode } from "react";
import { Button, Tooltip } from "antd";
import { ArrowLeftOutlined, FolderOpenOutlined, InboxOutlined, ReloadOutlined, ScheduleOutlined, SolutionOutlined } from "@ant-design/icons";
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
  onReopenConfirmation: (detail: ConfirmationDetail) => Promise<void>;
  onReturnWorkbench?: () => void;
  onOpenCaseAgentConversation?: (item: CaseAgentConversationSummary) => void;
  onStartIntake: () => void;
  onOpenIntake: (id: string) => void;
  onStartTask?: (skillId: string) => void;
};

const TASK_ICONS: Record<string, ReactNode> = { tasks: <ScheduleOutlined />, intake: <InboxOutlined />, customer: <SolutionOutlined /> };

export function AssistantWorkspaceSidebar({ workspace, name, logoSrc, onOpenPersonalSpace, onReopenConfirmation, onReturnWorkbench, onOpenCaseAgentConversation, onStartIntake, onOpenIntake, onStartTask }: Props) {
  // 501147：历史会话标题写明属于哪个空间。
  const current = workspace.currentWorkspace;
  const caseProject = current?.kind === "case" ? workspace.workspaceProjects.find((item) => item.kind === "case" && item.case_id === current.case_id) : undefined;
  const historyTitle = current?.kind === "case" ? `${caseProject?.serial_no || "案件空间"} · 最近会话` : "个人空间 · 最近会话";
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
      onRename={workspace.renameConversation}
      caseAgentConversations={workspace.caseAgentConversations}
      onSelectCaseAgentConversation={onOpenCaseAgentConversation}
      listClassName="assistant-conversation-list"
      rowClassName="assistant-conversation-row"
      selectClassName="assistant-conversation-select"
      historyTitle={historyTitle}
      navigation={(history) => <>
        {/* 501141：固定任务入口，点开新建对话并带好技能和开场提示。 */}
        <div className="assistant-task-entries" role="group" aria-label="固定任务">
          {(workspace.taskEntries || []).map((entry) => <Button key={entry.key} type="text" icon={TASK_ICONS[entry.key]} title={entry.hint} disabled={busy}
            onClick={() => onStartTask ? onStartTask(entry.skillId) : onStartIntake()}>{entry.label}</Button>)}
        </div>
        {!!workspace.courtIntakeConversations?.length && <div className="assistant-intake-history" aria-label="收文历史">
          {workspace.courtIntakeConversations.slice(0, 8).map((item) => <Button key={item.id} type="text" size="small" disabled={busy}
            className={item.id === workspace.state.conversation_id ? "is-active" : undefined}
            title={item.title} onClick={() => onOpenIntake(item.id)}>{item.title}</Button>)}
        </div>}
        <Button type="text" className="assistant-workspace-generated-entry" icon={<FolderOpenOutlined />} onClick={onOpenPersonalSpace}>AI生成文件夹</Button>
        <ConfirmationHistory onReopen={onReopenConfirmation} busy={busy || !!workspace.dismissalId} />
        <ConversationWorkspaceNavigation workspace={workspace} history={history} />
      </>}
    />
    <div className="assistant-workspace-footer">
      <Tooltip title="刷新智能体"><Button type="text" icon={<ReloadOutlined />} aria-label="刷新智能体" disabled={workspace.loading || !!workspace.runningIds.length} onClick={() => void workspace.load()}>刷新智能体</Button></Tooltip>
      {onReturnWorkbench && <Button type="text" icon={<ArrowLeftOutlined />} onClick={onReturnWorkbench}>返回工作台</Button>}
    </div>
  </aside>;
}
