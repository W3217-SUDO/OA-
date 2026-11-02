import type { ReactNode } from "react";
import { FileSearchOutlined, InboxOutlined, ScheduleOutlined, SolutionOutlined } from "@ant-design/icons";
import type { AgentTaskEntry } from "../agentSkillRouting";

const taskIcons: Record<string, ReactNode> = { tasks: <ScheduleOutlined />, intake: <InboxOutlined />, customer: <SolutionOutlined /> };

/** 固定任务卡片（501141）：任务处理、收文处理、客户与合同；点开新建对话并带好技能和开场提示。 */
export function TaskEntryCards({ entries, disabled, onStart, commands = [], onCommand }: {
  entries: AgentTaskEntry[]; disabled: boolean; onStart: (skillId: string) => void;
  /** 常规指令（tgn 11-02 22:50：“查询我的今日收文”和固定任务一样做成卡片，点了直接发）。 */
  commands?: { label: string; hint: string; prompt: string }[]; onCommand?: (prompt: string) => void;
}) {
  if (!entries.length && !commands.length) return null;
  return <div className="assistant-cards is-shortcut is-task-entries" role="group" aria-label="固定任务">
    {entries.map((entry) => <button key={entry.key} type="button" className="assistant-card is-task" disabled={disabled} onClick={() => onStart(entry.skillId)}>
      <span className="assistant-card-icon">{taskIcons[entry.key]}</span>
      <span className="assistant-card-body"><b>{entry.label}</b><span>{entry.hint}</span></span>
    </button>)}
    {onCommand && commands.map((command) => <button key={command.label} type="button" className="assistant-card is-task is-command" disabled={disabled} onClick={() => onCommand(command.prompt)}>
      <span className="assistant-card-icon"><FileSearchOutlined /></span>
      <span className="assistant-card-body"><b>{command.label}</b><span>{command.hint}</span></span>
    </button>)}
  </div>;
}
