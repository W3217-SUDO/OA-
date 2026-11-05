// 501629（tgn 11-05）：已完成任务的剩余天数显示“逾期完成 X 天”/“按期完成”，灰色；未完成照旧。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import ts from "typescript";

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");
const constants = read("../src/tp/constants.ts");
const page = read("../src/tp/TaskCenterPage.tsx");
const css = read("../src/task-center.css");

const helperSource = constants.slice(
  constants.indexOf("const FINISHED_TASK_STATUSES"),
  constants.indexOf("\n};", constants.indexOf("export const taskDaysDisplay")) + 3,
).replace("export const", "const");
const { outputText } = ts.transpileModule(`${helperSource}\nexport { taskDaysDisplay };`, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2019 },
});
const { taskDaysDisplay } = await import(`data:text/javascript,${encodeURIComponent(outputText)}`);

test("已完成且逾期：逾期完成 X 天，灰色", () => {
  assert.deepEqual(taskDaysDisplay("已完成", -116), { text: "逾期完成 116 天", className: "task-days-finished" });
  assert.deepEqual(taskDaysDisplay("已验收", -3), { text: "逾期完成 3 天", className: "task-days-finished" });
  assert.deepEqual(taskDaysDisplay("待确认", -1), { text: "逾期完成 1 天", className: "task-days-finished" });
});

test("已完成且按期：按期完成", () => {
  assert.deepEqual(taskDaysDisplay("已完成", 9), { text: "按期完成", className: "task-days-finished" });
  assert.deepEqual(taskDaysDisplay("已完成", 0), { text: "按期完成", className: "task-days-finished" });
});

test("未完成照旧：X/天，逾期红、3 天内橙；无截止日为空", () => {
  assert.deepEqual(taskDaysDisplay("已逾期", -5), { text: "-5/天", className: "task-days-overdue" });
  assert.deepEqual(taskDaysDisplay("进行中", 2), { text: "2/天", className: "task-days-soon" });
  assert.deepEqual(taskDaysDisplay("待处理", 10), { text: "10/天", className: "" });
  assert.deepEqual(taskDaysDisplay("已完成", null), { text: "", className: "" });
});

test("列表用 taskDaysDisplay，灰色样式不用新 CSS 特性（钉钉 Chrome 100）", () => {
  assert.match(page, /taskDaysDisplay\(row\.workflow_status \|\| row\.status, value\)/);
  assert.match(css, /\.task-days-finished \{ color: #8c8c8c; \}/);
});
