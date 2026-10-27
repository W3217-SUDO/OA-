import type { FeedbackEvent } from "./types";

// 处理记录按聊天框显示（用户要求，2026-10-27）：提交人的消息靠右、蓝色气泡；
// 处理方（管理者、问题处理助手、被指派的处理人）靠左、白色气泡；状态变化是居中的小灰条。
export type FeedbackSpeaker = "reporter" | "admin" | "bot" | "assignee";

export const FEEDBACK_SPEAKER_LABEL: Record<FeedbackSpeaker, string> = {
  reporter: "提交人", admin: "管理者", bot: "问题处理助手", assignee: "处理人",
};

export function feedbackSpeaker(event: Pick<FeedbackEvent, "operator_role">): FeedbackSpeaker {
  const role = event.operator_role;
  return role === "reporter" || role === "bot" || role === "assignee" ? role : "admin";
}

/** 回复是消息；其余（提交反馈、确认修改、处理完成、验证通过、重新打开、指派处理人等）是状态变化。 */
export function isFeedbackStatusEvent(event: Pick<FeedbackEvent, "action">): boolean {
  return event.action !== "回复";
}

export function feedbackSpeakerName(event: Pick<FeedbackEvent, "operator" | "operator_display_name" | "operator_role">): string {
  const speaker = feedbackSpeaker(event);
  if (speaker === "bot") return FEEDBACK_SPEAKER_LABEL.bot;
  return event.operator_display_name || event.operator || FEEDBACK_SPEAKER_LABEL[speaker];
}

// 说明是系统生成的（如“未指派 → 陶国南”），直接写进灰条，不另起气泡。
const NOTE_IN_STATUS_ACTIONS = new Set(["指派处理人"]);

/** 居中灰条的文字，如“管理者 处理完成，请验证 → 待验证”“管理者 指派处理人：未指派 → 陶国南”。 */
export function feedbackStatusText(event: Pick<FeedbackEvent, "action" | "from_status" | "to_status" | "operator" | "operator_display_name" | "operator_role" | "comment">): string {
  const name = feedbackSpeakerName(event);
  if (NOTE_IN_STATUS_ACTIONS.has(event.action) && event.comment?.trim()) return `${name} ${event.action}：${event.comment.trim()}`;
  const action = event.action === "提交反馈" ? "提交了反馈" : event.action;
  return event.from_status !== event.to_status && event.to_status ? `${name} ${action} → ${event.to_status}` : `${name} ${action}`;
}

/** 状态变化带了说明或文件时，在灰条下面再显示一个对应的气泡。 */
export function feedbackEventHasMessage(event: Pick<FeedbackEvent, "action" | "comment" | "attachments" | "has_screenshot">): boolean {
  if (!isFeedbackStatusEvent(event)) return true;
  const note = NOTE_IN_STATUS_ACTIONS.has(event.action) ? "" : event.comment?.trim();
  return Boolean(note || event.attachments?.length || event.has_screenshot);
}
