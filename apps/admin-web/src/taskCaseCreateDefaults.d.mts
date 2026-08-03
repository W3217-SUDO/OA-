import type { Dayjs } from "dayjs"

export declare function getCaseTaskCreateDefaults(now?: Dayjs): {
  priority: "重要"
  deadline: Dayjs
}
