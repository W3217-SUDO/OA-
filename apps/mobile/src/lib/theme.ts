// 沿用网页端沪知主题色（public/huzhi.webmanifest theme_color）。
export const colors = {
  primary: "#183c36",
  primarySoft: "#e8efed",
  accent: "#2f7d6b",
  background: "#f4f6f5",
  surface: "#ffffff",
  text: "#1c2421",
  textSecondary: "#5d6b66",
  textMuted: "#8a9691",
  border: "#e2e7e5",
  danger: "#c4382f",
  warning: "#c47a12",
  success: "#2f7d4f",
};

export const statusTone: Record<string, string> = {
  待接收: colors.warning,
  待处理: colors.warning,
  处理中: colors.accent,
  进行中: colors.accent,
  已逾期: colors.danger,
  待确认: colors.primary,
  已完成: colors.success,
  已验收: colors.success,
  已拒绝: colors.danger,
  已停止: colors.textMuted,
  已撤回: colors.textMuted,
};
