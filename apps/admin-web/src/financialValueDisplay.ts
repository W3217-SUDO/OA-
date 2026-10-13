export function displayFinancialValue<T>(value: T): T | "—" {
  return typeof value === "string" && /^[\\/]+$/.test(value.trim()) ? "—" : value;
}
