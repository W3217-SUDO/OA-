import dayjs from "dayjs";

export function formatRequiredDate(
  value: unknown,
  label: string,
  format = "YYYY-MM-DD",
) {
  if (value === null || value === undefined || value === "") {
    throw new Error(`请重新选择${label}`);
  }
  const parsed = dayjs(value as any);
  if (!parsed.isValid()) {
    throw new Error(`${label}格式无效，请重新选择`);
  }
  return parsed.format(format);
}
