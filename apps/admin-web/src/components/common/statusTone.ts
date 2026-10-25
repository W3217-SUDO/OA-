/**
 * 全站状态标签的唯一配色来源：每个状态只对应一种含义，每种含义只对应一种颜色。
 * 新状态加到下面的 STATUS_TONE 里，不要在模块里另建“状态→颜色”表。
 * 诉讼阶段（一审、二审、执行等）不是状态，用 StageTag 统一浅色显示。
 */
export type StatusTone = "pending" | "processing" | "waiting" | "success" | "danger" | "neutral";

/** 每种含义对应的 antd 预设色，深色模式由 antd 自动适配。 */
export const STATUS_TONE_COLOR: Record<StatusTone, string> = {
  /** 待我处理 */
  pending: "orange",
  /** 进行中 */
  processing: "blue",
  /** 等别人（客户、对方、机构） */
  waiting: "purple",
  /** 已完成 */
  success: "green",
  /** 失败或驳回 */
  danger: "red",
  /** 已终止、草稿 */
  neutral: "default",
};

/** 按含义分组的状态清单；同一状态只能出现在一个分组里（有测试保证）。 */
export const STATUS_GROUPS: Readonly<Record<StatusTone, readonly string[]>> = {
  pending: [
    "待接收", "待处理", "待审批", "待审核", "待分配", "新案待分配", "待开票", "待用印", "待办理", "待校验", "待转发", "待取证", "待认领", "未入库",
    "审批中", "待立案审批", "待立案审核", "归档审核", "待归档审核", "亏损内审", "亏损审核",
  ],
  processing: [
    "进行中", "处理中", "在办", "归档中", "已转发", "调查中", "已审批", "已确认", "部分付款", "部分分配", "退款办理中", "已取证", "已出库",
  ],
  waiting: [
    "待确认", "待验证", "待客户审核", "等待材料", "等待公证书", "等待审核公证书", "待公证", "维修",
  ],
  success: [
    "已完成", "已办结", "已解决", "已验收", "已用印", "已归档", "已付款", "已办理", "已分配", "已开票", "已退款", "已入账", "已入卷", "已转案件", "已结案",
    "审核通过", "审批通过", "已通过", "亏损归档", "已签收", "已入库", "已重新入库", "可用", "正常",
  ],
  danger: [
    "已逾期", "已过期", "已拒绝", "已驳回", "已退回", "审核驳回", "归档拒绝", "亏损归档拒绝", "亏损拒绝", "遗失",
  ],
  neutral: [
    "草稿", "已撤回", "已作废", "已停止", "已暂停", "已取消", "已合并", "停用", "已销毁",
  ],
};

export const STATUS_TONE: Readonly<Record<string, StatusTone>> = Object.freeze(Object.fromEntries(
  (Object.entries(STATUS_GROUPS) as [StatusTone, readonly string[]][])
    .flatMap(([value, statuses]) => statuses.map((status) => [status, value])),
));

/** 表里没有的状态返回 undefined，由调用方决定按“已终止”还是按阶段显示。 */
export function statusToneOf(status: unknown): StatusTone | undefined {
  return STATUS_TONE[String(status ?? "").trim()];
}
