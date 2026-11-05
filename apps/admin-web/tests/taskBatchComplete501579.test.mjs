// 501579：“我接受的任务”勾选多条直接“批量完成（N）”，不符合的跳过并列出原因。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");
const list = read("../src/tp/TaskList.tsx");
const page = read("../src/tp/TaskCenterPage.tsx");
const modals = read("../src/tp/TaskActionModals.tsx");

test("勾选多条出现批量完成按钮，下拉里不再整体禁用", () => {
  assert.match(list, /onOpenTaskBatchLifecycle\("complete"\)\}>\{`批量完成（\$\{selectedRows\.length\}）`\}/);
  assert.match(list, /\{ key: "complete", label: "批量完成" \}/);
});

test("完成说明选填，跳过的任务弹窗列出原因", () => {
  assert.match(modals, /完成说明（选填）/);
  assert.match(page, /已完成 \$\{data\.updated\} 条，跳过 \$\{skipped\.length\} 条/);
});

test("501580：公司接受的任务只有能代办的人显示操作按钮", () => {
  assert.match(page, /\(initialView === "task-company-accepted" && roleActionAllowed\("task\.batch\.update"\)\)/);
});
