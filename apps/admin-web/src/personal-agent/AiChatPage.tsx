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
};

export default function AiChatPage({ onReturnWorkbench, focusRequested, onFocusHandled, name = "Ai", desktop = false, onOpenAgentCenter }: Props) {
  const workspace = usePersonalWorkspaceContext();
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
        suggestions={[]}
        focusRequested={focusRequested}
        onFocusHandled={onFocusHandled}
      />
    </div>
  );
}
