import test from "node:test"
import assert from "node:assert/strict"
import dayjs from "dayjs"
import { getCaseTaskCreateDefaults } from "./src/taskCaseCreateDefaults.mjs"

test("案件任务默认使用旧 Top1 优先级、当天开始和次日截止", () => {
  const now = dayjs("2026-08-03T15:42:19")
  const defaults = getCaseTaskCreateDefaults(now)

  assert.equal(defaults.priority, "重要")
  assert.equal(defaults.deadline.format("YYYY-MM-DD"), "2026-08-04")
  assert.equal(defaults.deadline.format("HH:mm:ss"), "15:42:19")
  assert.equal("startAt" in defaults, false)
})

test("案件任务截止时间在当天最后时刻加一天后仍保留时刻", () => {
  const defaults = getCaseTaskCreateDefaults(dayjs("2026-08-03T23:59:59"))

  assert.equal(defaults.deadline.format("YYYY-MM-DD HH:mm:ss"), "2026-08-04 23:59:59")
})
