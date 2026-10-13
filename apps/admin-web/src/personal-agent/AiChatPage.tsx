import type { ComponentProps } from "react";
import { Alert, Button } from "antd";
import dayjs from "dayjs";
import { useDashboardData } from "../dashboardData";
import { rejectionsPrompt, todayHearingsPrompt } from "../dashboardPrompts";
import AssistantPanel, { type AssistantSuggestion } from "./AssistantPanel";
import { usePersonalWorkspaceContext } from "./PersonalWorkspaceProvider";
import "./ai-chat-page.css";

type Props = {
  onReturnWorkbench: () => void;
  focusRequested: boolean;
  onFocusHandled: () => void;
  name?: string;
  desktop?: boolean;
};

const desktopSuggestionSections = ["cases", "rejections"] as const;

// 仅桌面入口挂载提醒数据，手机保持原有空建议和请求范围。
function DesktopAssistantPanel(props: ComponentProps<typeof AssistantPanel>) {
  const { data, errors, retry } = useDashboardData(desktopSuggestionSections);
  const today = dayjs().format("YYYY-MM-DD");
  const todayHearings = (data.hearings || []).filter((item) => item.date === today);
  const rejections = data.rejections || [];
  const rejectionTotal = data.rejection_total || 0;
  const suggestions: AssistantSuggestion[] = [];
  if (todayHearings.length) {
    const first = todayHearings[0];
    suggestions.push({ kind: "hearing", label: "准备今天的开庭", hint: `最早 ${first.time} ${first.court || "法院待定"}`, count: todayHearings.length, prompt: todayHearingsPrompt(todayHearings) });
  }
  if (rejections.length) {
    suggestions.push({ kind: "rejection", label: "处理被驳回的审批", hint: `最近一条：${rejections[0].title}`, count: rejectionTotal, prompt: rejectionsPrompt(rejections, rejectionTotal) });
  }
  return (
    <>
      {desktopSuggestionSections.map((section) => errors[section] && (
        <Alert
          key={section}
          className="assistant-alert ai-chat-suggestions-error"
          type="error"
          showIcon
          title={`${section === "cases" ? "开庭" : "驳回审批"}建议加载失败：${errors[section]}`}
          action={<Button size="small" onClick={() => retry(section)}>重试</Button>}
        />
      ))}
      <AssistantPanel {...props} suggestions={suggestions} />
    </>
  );
}

export default function AiChatPage({ onReturnWorkbench, focusRequested, onFocusHandled, name = "Ai", desktop = false }: Props) {
  const workspace = usePersonalWorkspaceContext();
  const Panel = desktop ? DesktopAssistantPanel : AssistantPanel;
  return (
    <div className="ai-chat-page" aria-label={name}>
      <Panel
        name={name}
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
