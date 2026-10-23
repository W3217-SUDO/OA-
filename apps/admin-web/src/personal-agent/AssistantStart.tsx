import type { ReactNode } from "react";
import { AuditOutlined, ExceptionOutlined, FolderOpenOutlined, InboxOutlined, ScheduleOutlined, ThunderboltOutlined } from "@ant-design/icons";

// 由工作台当天的数据生成的建议：点击后把具体内容交给智能体处理。
export type AssistantSuggestion = {
  kind: "hearing" | "rejection";
  label: string;
  hint: string;
  count: number;
  prompt: string;
};

type Shortcut = { label: string; hint: string; prompt: string; icon: ReactNode };

// 常用问题：点击后直接发给智能体，和手动输入走同一条对话。
export const shortcuts: Shortcut[] = [
  { label: "今日优先事项", hint: "今天要先处理的审批和任务", prompt: "列出我今天优先处理的审批和任务", icon: <ThunderboltOutlined /> },
  { label: "我的合同审批", hint: "当前等我审批的合同", prompt: "查询我当前待审批的合同", icon: <AuditOutlined /> },
  { label: "我的案件", hint: "我负责的案件和所处阶段", prompt: "列出我负责的案件和当前阶段", icon: <FolderOpenOutlined /> },
];

const suggestionIcons: Record<AssistantSuggestion["kind"], ReactNode> = {
  hearing: <ScheduleOutlined />,
  rejection: <ExceptionOutlined />,
};

type Props = {
  suggestions: AssistantSuggestion[];
  disabled: boolean;
  onPick: (prompt: string) => void;
  onStartIntake?: () => void;
};

// 还没有对话时占满面板中间：先给出今天最值得问的几件事。
export default function AssistantStart({ suggestions, disabled, onPick, onStartIntake }: Props) {
  return (
    <div className="assistant-start">
      {!!suggestions.length && (
        <div className="assistant-cards is-context">
          {suggestions.map((item) => (
            <button key={item.kind} type="button" className={`assistant-card is-${item.kind}`} disabled={disabled} onClick={() => onPick(item.prompt)}>
              <span className="assistant-card-icon">{suggestionIcons[item.kind]}</span>
              <span className="assistant-card-body">
                <b>{item.label}</b>
                <span>{item.hint}</span>
              </span>
              <em>{item.count}</em>
            </button>
          ))}
        </div>
      )}
      <div className="assistant-cards is-shortcut">
        {onStartIntake && (
          <button type="button" className="assistant-card" disabled={disabled} onClick={onStartIntake}>
            <span className="assistant-card-icon"><InboxOutlined /></span>
            <span className="assistant-card-body">
              <b>收文助手</b>
              <span>粘贴法院送达短信，自动收文入库</span>
            </span>
          </button>
        )}
        {shortcuts.map((item) => (
          <button key={item.label} type="button" className="assistant-card" disabled={disabled} onClick={() => onPick(item.prompt)}>
            <span className="assistant-card-icon">{item.icon}</span>
            <span className="assistant-card-body">
              <b>{item.label}</b>
              <span>{item.hint}</span>
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
