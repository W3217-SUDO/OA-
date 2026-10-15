import { useEffect } from "react";
import AssistantPanel from "./AssistantPanel";
import { usePersonalWorkspaceContext } from "./PersonalWorkspaceProvider";
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
    void workspace.setProjectMode(true);
    return () => { void workspace.setProjectMode(false); };
  }, [desktop]);
  return (
    <div className={`ai-chat-page${desktop ? " is-desktop-workspace" : ""}`} aria-label={name}>
      <AssistantPanel
        name={name}
        logoSrc="/assets/ai-assistant-logo.png"
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
