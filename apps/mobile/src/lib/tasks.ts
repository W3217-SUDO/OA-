import type { SessionUser, TaskRow } from "./types";

// 与网页端 tp/constants.ts 的 receivedTabs / createdTabs / collaboratingTabs 一致。
export type TaskView = { key: string; label: string; relation?: "owned" | "initiated" | "collaborating"; unread?: boolean; statuses: string[] };

export const TASK_VIEWS: TaskView[] = [
  { key: "owned-pending", label: "待处理", relation: "owned", statuses: ["待接收", "待处理"] },
  { key: "owned-processing", label: "进行中", relation: "owned", statuses: ["处理中", "进行中", "已逾期"] },
  { key: "initiated-active", label: "我发起的", relation: "initiated", statuses: ["待接收", "待处理", "处理中", "进行中", "已逾期", "已完成", "待确认"] },
  { key: "collaborating", label: "我协作的", relation: "collaborating", statuses: ["待接收", "待处理", "处理中", "进行中", "已逾期"] },
  { key: "unread", label: "未读消息", unread: true, statuses: [] },
  { key: "owned-finished", label: "已完成", relation: "owned", statuses: ["已完成", "待确认", "已验收"] },
];

export const taskStatus = (task: TaskRow) => task.workflow_status || task.status;

/** 按钮显示规则沿用网页端 TaskDetail.tsx；最终权限以后端校验为准。 */
export function taskActions(task: TaskRow, user: SessionUser | null) {
  const status = taskStatus(task);
  const isOwner = !!user && task.owner === user.username;
  const isInitiator = !!user && task.initiator === user.username;
  return {
    accept: isOwner && ["待接收", "待处理"].includes(status),
    complete: isOwner && ["待接收", "待处理", "处理中", "进行中", "已逾期"].includes(status) && !task.phase_completion_required,
    confirm: isInitiator && ["已完成", "待确认"].includes(status),
    feedback: !!user && (user.role === "admin" || [task.owner, task.initiator, ...(task.collaborators || [])].includes(user.username)),
  };
}

export const ACTION_COMMENTS = {
  accept: "任务已接收",
  complete: "已提交完成，等待发起人确认",
  confirm: "任务已验收",
} as const;

export function deadlineText(task: TaskRow) {
  if (!task.deadline) return "无截止日期";
  const date = task.deadline.slice(0, 10);
  if (task.days_remaining === null || task.days_remaining === undefined) return `截止 ${date}`;
  if (task.days_remaining < 0) return `截止 ${date}（逾期 ${-task.days_remaining} 天）`;
  if (task.days_remaining === 0) return `截止 ${date}（今天）`;
  return `截止 ${date}（剩 ${task.days_remaining} 天）`;
}
