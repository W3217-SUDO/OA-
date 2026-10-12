import AssistantPanel from "./AssistantPanel";
import { usePersonalWorkspaceContext } from "./PersonalWorkspaceProvider";
import "./ai-chat-page.css";

type Props = {
  onReturnWorkbench: () => void;
  focusRequested: boolean;
  onFocusHandled: () => void;
};

export default function AiChatPage({ onReturnWorkbench, focusRequested, onFocusHandled }: Props) {
  const workspace = usePersonalWorkspaceContext();
  return (
    <div className="ai-chat-page" aria-label="Ai">
      <AssistantPanel
        name="Ai"
        logoSrc="/assets/ai-assistant-logo.png"
        returnLabel="返回工作台"
        onReturnOverview={onReturnWorkbench}
        workspace={workspace}
        suggestions={[]}
        focusRequested={focusRequested}
        onFocusHandled={onFocusHandled}
      />
    </div>
  );
}
