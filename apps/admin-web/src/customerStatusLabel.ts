export function customerStatusLabel(status?: string): string {
  return status?.trim() || "正常";
}
