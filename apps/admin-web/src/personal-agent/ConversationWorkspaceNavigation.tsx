import { useState, type ReactNode } from "react";
import { Button, Tooltip, message } from "antd";
import { CaretDownOutlined, CaretRightOutlined, FolderAddOutlined } from "@ant-design/icons";
import { CaseWorkspaceSelector } from "./CaseWorkspaceSelector";
import { PERSONAL_CONVERSATION_WORKSPACE } from "./conversationWorkspace";
import { errorText, type ConversationWorkspace } from "./types";
import type { usePersonalWorkspace } from "./usePersonalWorkspace";

type Props = { workspace: ReturnType<typeof usePersonalWorkspace>; history?: ReactNode;
  /** 501185（陶国南 11-03 09:36）：点案件空间里的案件，跳到该案件详情并在右下角弹出案件智能体浮窗。 */
  onOpenCaseAgent?: (caseId: number, serialNo: string) => void };

// 501147：每个空间的收起/展开记在本机，下次打开保持（读写失败时按默认展开）。
const COLLAPSE_STORAGE_KEY = "oa-agent-space-collapsed-v1";
const readCollapsed = (): Record<string, boolean> => {
  try { const value = JSON.parse(window.localStorage.getItem(COLLAPSE_STORAGE_KEY) || "{}"); return value && typeof value === "object" ? value : {}; }
  catch { return {}; }
};

/** 空间导航；history 紧贴放在所选空间下面（501147：历史会话属于所在空间，点空间标题收起/展开）。 */
export function ConversationWorkspaceNavigation({ workspace, history, onOpenCaseAgent }: Props) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>(readCollapsed);
  const setSpaceCollapsed = (key: string, value: boolean) => setCollapsed((previous) => {
    const next = { ...previous, [key]: value };
    try { window.localStorage.setItem(COLLAPSE_STORAGE_KEY, JSON.stringify(next)); } catch { /* 本机存不了就只在本次有效 */ }
    return next;
  });
  const expanded = !collapsed.cases;
  const setExpanded = (value: boolean | ((previous: boolean) => boolean)) => setSpaceCollapsed("cases", !(typeof value === "function" ? value(expanded) : value));
  const caret = (open: boolean) => open ? <CaretDownOutlined /> : <CaretRightOutlined />;
  const [selectorOpen, setSelectorOpen] = useState(false);
  const busy = workspace.loading || workspace.conversationBusy || workspace.uploading || !!workspace.decisionId || !!workspace.dismissalId;
  const canUseCases = workspace.status?.commands.some((item) => item.id === "cases") === true;
  const current = workspace.currentWorkspace;
  const select = async (target: ConversationWorkspace) => {
    try { await workspace.selectWorkspace(target); }
    catch (failure) { message.error(errorText(failure, "空间未打开")); }
  };
  // 点当前空间：收起/展开它的最近会话；点别的空间：打开它并展开。
  const openSpace = (key: string, active: boolean, target: ConversationWorkspace) => {
    if (active) { setSpaceCollapsed(key, !collapsed[key]); return; }
    setSpaceCollapsed(key, false);
    void select(target);
  };
  const personalActive = current?.kind === "personal";
  return <>
    <Button type="text" className="assistant-workspace-personal-entry" icon={caret(personalActive && !collapsed.personal)} aria-current={personalActive ? "page" : undefined} aria-expanded={personalActive ? !collapsed.personal : false} disabled={busy} onClick={() => openSpace("personal", personalActive, PERSONAL_CONVERSATION_WORKSPACE)}>个人空间</Button>
    {personalActive && !collapsed.personal && history}
    <div className={`assistant-workspace-projects${expanded ? " is-expanded" : ""}`}>
      <div className="assistant-workspace-project-heading">
        <Button type="text" icon={caret(expanded)} aria-expanded={expanded} onClick={() => setExpanded((value) => !value)}>案件空间</Button>
        <Tooltip title={workspace.loadError ? "工作区加载失败，请先重试" : canUseCases ? "选择案件空间" : "当前没有案件访问权限"}><Button type="text" icon={<FolderAddOutlined />} aria-label="选择案件空间" disabled={busy || !!workspace.loadError || !canUseCases} onClick={() => setSelectorOpen(true)} /></Tooltip>
      </div>
      {expanded && <div className="assistant-workspace-project-list" aria-label="案件项目">
        {workspace.workspaceProjects.filter((item) => item.kind === "case").map((item) => {
          const active = current?.kind === "case" && current.case_id === item.case_id;
          const key = `case:${item.case_id}`;
          return <div key={item.case_id}>
            <Tooltip title={!item.available ? item.unavailable_reason : `${item.serial_no} · ${item.title}`}>
              <Button type="text" className="assistant-workspace-project" icon={caret(active && !collapsed[key])} aria-current={active ? "page" : undefined} aria-expanded={active ? !collapsed[key] : false} disabled={busy || !!workspace.loadError || !canUseCases || !item.available} onClick={() => onOpenCaseAgent ? onOpenCaseAgent(item.case_id!, item.serial_no || "") : openSpace(key, active, { kind: "case", case_id: item.case_id! })}>
                <span className="assistant-workspace-project-label"><b>{item.serial_no}</b><span>{item.title}</span></span>
              </Button>
            </Tooltip>
            {active && !collapsed[key] && history}
          </div>;
        })}
      </div>}
    </div>
    <CaseWorkspaceSelector open={selectorOpen} blocked={!!workspace.loadError} onClose={() => setSelectorOpen(false)} onSelect={async (item) => {
      if (onOpenCaseAgent) { setSelectorOpen(false); onOpenCaseAgent(item.id, item.serial_no); return; }
      await workspace.selectWorkspace({ kind: "case", case_id: item.id }); setExpanded(true);
    }} />
  </>;
}
