import { useState } from "react";
import { Button, Tooltip, message } from "antd";
import { FolderAddOutlined, FolderOpenOutlined, FolderOutlined } from "@ant-design/icons";
import { CaseWorkspaceSelector } from "./CaseWorkspaceSelector";
import { PERSONAL_CONVERSATION_WORKSPACE } from "./conversationWorkspace";
import { errorText, type ConversationWorkspace } from "./types";
import type { usePersonalWorkspace } from "./usePersonalWorkspace";

type Props = { workspace: ReturnType<typeof usePersonalWorkspace> };

export function ConversationWorkspaceNavigation({ workspace }: Props) {
  const [expanded, setExpanded] = useState(true);
  const [selectorOpen, setSelectorOpen] = useState(false);
  const busy = workspace.loading || workspace.conversationBusy || workspace.uploading || !!workspace.decisionId || !!workspace.dismissalId;
  const canUseCases = workspace.status?.commands.some((item) => item.id === "cases") === true;
  const current = workspace.currentWorkspace;
  const select = async (target: ConversationWorkspace) => {
    try { await workspace.selectWorkspace(target); }
    catch (failure) { message.error(errorText(failure, "空间未打开")); }
  };
  return <>
    <Button type="text" className="assistant-workspace-personal-entry" icon={<FolderOutlined />} aria-current={current?.kind === "personal" ? "page" : undefined} disabled={busy} onClick={() => void select(PERSONAL_CONVERSATION_WORKSPACE)}>个人空间</Button>
    <div className="assistant-workspace-projects">
      <div className="assistant-workspace-project-heading">
        <Button type="text" icon={<FolderOpenOutlined />} aria-expanded={expanded} onClick={() => setExpanded((value) => !value)}>案件空间</Button>
        <Tooltip title={workspace.loadError ? "工作区加载失败，请先重试" : canUseCases ? "选择案件空间" : "当前没有案件访问权限"}><Button type="text" icon={<FolderAddOutlined />} aria-label="选择案件空间" disabled={busy || !!workspace.loadError || !canUseCases} onClick={() => setSelectorOpen(true)} /></Tooltip>
      </div>
      {expanded && <div className="assistant-workspace-project-list" aria-label="案件项目">
        {workspace.workspaceProjects.filter((item) => item.kind === "case").map((item) => <Tooltip key={item.case_id} title={!item.available ? item.unavailable_reason : `${item.serial_no} · ${item.title}`}>
          <Button type="text" className="assistant-workspace-project" icon={<FolderOutlined />} aria-current={current?.kind === "case" && current.case_id === item.case_id ? "page" : undefined} disabled={busy || !!workspace.loadError || !canUseCases || !item.available} onClick={() => void select({ kind: "case", case_id: item.case_id! })}>
            <span className="assistant-workspace-project-label"><b>{item.serial_no}</b><span>{item.title}</span></span>
          </Button>
        </Tooltip>)}
      </div>}
    </div>
    <CaseWorkspaceSelector open={selectorOpen} blocked={!!workspace.loadError} onClose={() => setSelectorOpen(false)} onSelect={async (item) => { await workspace.selectWorkspace({ kind: "case", case_id: item.id }); setExpanded(true); }} />
  </>;
}
