import dayjs from "dayjs";

// 反馈时间一律按北京时间显示，不随电脑所在时区变化（中国无夏令时，固定 UTC+8）。
export function beijingTime(value: string | null | undefined, format: string): string {
  const time = dayjs(value);
  if (!value || !time.isValid()) return "";
  return time.add(480 + time.toDate().getTimezoneOffset(), "minute").format(format);
}
