export function displayFinancialValue<T>(value: T): T | "—" {
  return typeof value === "string" && /^[\\/]+$/.test(value.trim()) ? "—" : value;
}

/** 费用字段的空值统一留白；实际的零金额仍按零金额展示。 */
export function displayFeeValue<T>(value: T): T | "" {
  if (value === null || value === undefined) return "";
  if (typeof value === "string" && (!value.trim() || /^[\\/]+$/.test(value.trim()))) return "";
  return value;
}
