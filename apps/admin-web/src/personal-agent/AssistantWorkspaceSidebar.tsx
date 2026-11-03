import { useState, type ReactNode } from "react";
import { Button, Tooltip } from "antd";
import { ArrowLeftOutlined, DownOutlined, FolderOpenOutlined, RightOutlined, InboxOutlined, ReloadOutlined, ScheduleOutlined, SolutionOutlined } from "@ant-design/icons";
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
  onOpenIntake?: (id: string) => void;
  onStartTask?: (skillId: string) => void;
  onOpenTaskConversation?: (id: string, skillId: string) => void;
  onOpenCaseAgent?: (caseId: number, serialNo: string) => void;
};

const TASK_ICONS: Record<string, ReactNode> = { tasks: <ScheduleOutlined />, intake: <InboxOutlined />, customer: <SolutionOutlined /> };

const updatedAt = (value?: string) => { const time = value ? Date.parse(value) : NaN; return Number.isNaN(time) ? 0 : time; };
const shortTime = (value?: string) => {
  const time = updatedAt(value);
  if (!time) return "";
  const date = new Date(time);
  return `${date.getMonth() + 1}-${String(date.getDate()).padStart(2, "0")} ${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
};

export function AssistantWorkspaceSidebar({ workspace, name, logoSrc, onOpenPersonalSpace, onReopenConfirmation, onReturnWorkbench, onOpenCaseAgentConversation, onOpenTaskConversation, onOpenCaseAgent }: Props) {
  const [expanded, setExpanded] = useState<string[]>([]);
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
        {/* 501147（tgn 11-03 00:04）：左侧三个固定任务是会话归集，点开只展开这一类的历史会话（最新在上），不下任何指令；
            要下指令点对话框上方的便捷指令卡片。 */}
        <div className="assistant-task-entries" role="group" aria-label="会话归集">
          {(workspace.taskEntries || []).map((entry) => {
            const open = expanded.includes(entry.key);
            const items = (workspace.conversations || []).filter((item) => item.skill_id === entry.skillId)
              .sort((left, right) => updatedAt(right.updated_at) - updatedAt(left.updated_at));
            return <div key={entry.key} className="assistant-task-group">
              <Button type="text" icon={TASK_ICONS[entry.key]} title={`${entry.label}的历史会话`} aria-expanded={open}
                onClick={() => setExpanded((current) => open ? current.filter((key) => key !== entry.key) : [...current, entry.key])}>
                <span className="assistant-task-group-label">{entry.label}</span>
                {!!items.length && <span className="assistant-task-group-count">{items.length}</span>}
                {open ? <DownOutlined className="assistant-task-group-arrow" /> : <RightOutlined className="assistant-task-group-arrow" />}
              </Button>
              {open && <ul className="assistant-task-group-list" aria-label={`${entry.label}会话`}>
                {items.map((item) => <li key={item.id}>
                  <button type="button" className={item.id === workspace.state.conversation_id ? "is-active" : undefined} disabled={busy}
                    aria-current={item.id === workspace.state.conversation_id ? "true" : undefined}
                    onClick={() => onOpenTaskConversation?.(item.id, entry.skillId)}>
                    <span>{item.title || entry.label}</span>{shortTime(item.updated_at) && <time>{shortTime(item.updated_at)}</time>}
                  </button>
                </li>)}
                {!items.length && <li className="assistant-task-group-empty">暂无会话，点对话框上方的“{entry.label}”开始</li>}
              </ul>}
            </div>;
          })}
        </div>
        {/* 501147（tgn 22:50）：收文已是固定会话，左侧不再另列收文历史，避免出现两个“收文助手”。 */}
        <Button type="text" className="assistant-workspace-generated-entry" icon={<FolderOpenOutlined />} onClick={onOpenPersonalSpace}>AI生成文件夹</Button>
        <ConfirmationHistory onReopen={onReopenConfirmation} busy={busy || !!workspace.dismissalId} />
        <ConversationWorkspaceNavigation workspace={workspace} history={history} onOpenCaseAgent={onOpenCaseAgent} />
      </>}
    />
    <div className="assistant-workspace-footer">
      <Tooltip title="刷新智能体"><Button type="text" icon={<ReloadOutlined />} aria-label="刷新智能体" disabled={workspace.loading || !!workspace.runningIds.length} onClick={() => void workspace.load()}>刷新智能体</Button></Tooltip>
      {onReturnWorkbench && <Button type="text" icon={<ArrowLeftOutlined />} onClick={onReturnWorkbench}>返回工作台</Button>}
    </div>
  </aside>;
}
