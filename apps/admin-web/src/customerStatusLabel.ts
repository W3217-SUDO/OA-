// 旧系统客户状态代码 T 显示“正常”（迁移客户的 status 原样保存为 T）。
const LEGACY_CUSTOMER_STATUS: Record<string, string> = { T: "正常" };

export function customerStatusLabel(status?: string): string {
  const value = status?.trim() || "";
  return LEGACY_CUSTOMER_STATUS[value] || value || "正常";
}
