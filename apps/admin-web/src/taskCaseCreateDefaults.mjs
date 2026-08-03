import dayjs from "dayjs"

export function getCaseTaskCreateDefaults(now = dayjs()) {
  return {
    priority: "重要",
    deadline: now.add(1, "day"),
  }
}
