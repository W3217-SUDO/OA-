// 501302：“我接受的任务”勾选多条可批量转交；接收人从员工目录选；不符合的跳过并列出原因。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");
const list = read("../src/tp/TaskList.tsx");
const modals = read("../src/tp/TaskActionModals.tsx");
const page = read("../src/tp/TaskCenterPage.tsx");

test("勾选多条后出现“批量转交”按钮，下拉里也叫批量转交任务", () => {
  assert.match(list, /selectedRows\.length > 1[\s\S]{0,200}onOpenTaskBatchLifecycle\("handoff"\)\}>批量转交<\/Button>/);
  assert.match(list, /label: "批量转交任务"/);
});

test("批量转交的接收人从员工目录选择，不再手输", () => {
  const batch = modals.slice(modals.indexOf("export function TaskBatchModal"));
  assert.match(batch, /name="recipient"[\s\S]{0,200}<KeywordPersonSelect/);
  assert.match(page, /handoffDirectory=\{handoffDirectory\}/);
});

test("转完列出跳过的任务和原因", () => {
  assert.match(page, /data\.skipped/);
  assert.match(page, /跳过 \$\{skipped\.length\} 条/);
});

test("维护任务可勾选多条一起改负责人、截止日期，不符合的跳过并列出原因", () => {
  assert.match(list, /批量维护任务（\$\{selectedRows\.length\}）/);
  assert.match(page, /task_ids: ids, owner: values\.owner/);
  assert.match(page, /已修改 \$\{data\.updated\} 条，跳过 \$\{skipped\.length\} 条/);
  assert.match(modals, /批量维护任务（已选 \$\{count\} 条）/);
});
