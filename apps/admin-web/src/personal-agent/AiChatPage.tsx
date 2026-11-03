import { useEffect } from "react";
import AssistantPanel from "./AssistantPanel";
import { usePersonalWorkspaceContext } from "./PersonalWorkspaceProvider";
import { AGENT_HEAD_SRC } from "./AgentAvatar";
import "./ai-chat-page.css";

type Props = {
  onReturnWorkbench: () => void;
  focusRequested: boolean;
  onFocusHandled: () => void;
  name?: string;
  desktop?: boolean;
  onOpenAgentCenter?: () => void;
  onOpenCaseAgent?: (caseId: number, serialNo: string) => void;
};

export default function AiChatPage({ onReturnWorkbench, focusRequested, onFocusHandled, name = "Ai", desktop = false, onOpenAgentCenter, onOpenCaseAgent }: Props) {
  const workspace = usePersonalWorkspaceContext();
  useEffect(() => {
    if (!desktop) return;
    // 501147（tgn 22:27）：每次进入智能体默认打开新对话框，不进上次的会话。
    void workspace.setProjectMode(true).then(() => workspace.startBlank?.());
    return () => { void workspace.setProjectMode(false); };
  }, [desktop]);
  return (
    <div className={`ai-chat-page${desktop ? " is-desktop-workspace" : ""}`} aria-label={name}>
      <AssistantPanel
        name={name}
        logoSrc={AGENT_HEAD_SRC}
        returnLabel="返回工作台"
        onReturnOverview={onReturnWorkbench}
        workspace={workspace}
        desktopWorkspace={desktop}
        onOpenAgentCenter={onOpenAgentCenter}
        onOpenCaseAgent={onOpenCaseAgent}
        suggestions={[]}
        focusRequested={focusRequested}
        onFocusHandled={onFocusHandled}
      />
    </div>
  );
}
