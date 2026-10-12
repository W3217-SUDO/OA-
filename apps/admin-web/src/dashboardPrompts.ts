import type { DashboardRejection } from "./dashboardData";

type Hearing = Record<string, string>;

// 工作台里“交给智能体”发出的提问：把当前提醒的关键信息写进问题，智能体不需要再追问。
const hearingLine = (item: Hearing) =>
  `${item.time} ${item.court || "法院待定"}，案件 ${item.case_no}${item.client ? `，客户 ${item.client}` : ""}`;

const rejectionLine = (item: DashboardRejection) =>
  `${item.type} ${item.serial_no}「${item.title}」，驳回原因：${item.reason || "未填写"}`;

export const hearingPrompt = (item: Hearing) =>
  `帮我准备开庭：案件 ${item.case_no}${item.client ? `，客户 ${item.client}` : ""}，${item.date} ${item.time} 在${item.court || "法院待定"}开庭。请列出需要准备的材料、庭前待办和注意事项。`;

export const todayHearingsPrompt = (items: Hearing[]) =>
  `帮我准备今天的开庭：\n${items.map(hearingLine).join("\n")}\n请按场次列出需要准备的材料、庭前待办和注意事项。`;

export const rejectionPrompt = (item: DashboardRejection) =>
  `帮我处理被驳回的${item.type} ${item.serial_no}「${item.title}」。驳回原因：${item.reason || "未填写"}。请说明应该怎么修改，才能重新提交。`;

export const rejectionsPrompt = (items: DashboardRejection[], total: number) =>
  `我有 ${total} 条被驳回的审批${total > items.length ? `，下面是最新的 ${items.length} 条` : ""}：\n${items.map(rejectionLine).join("\n")}\n请逐条说明应该怎么修改，才能重新提交。`;
