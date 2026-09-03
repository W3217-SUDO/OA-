import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/TaskCenterPage.tsx", import.meta.url), "utf8");

test("created-task completed and rejected detail actions match legacy workflow", () => {
  assert.match(source, /statusTab === "finished"[\s\S]*?>验收任务<\/Button>/);
  assert.match(source, /\["已完成", "待确认", "已拒绝"\]\.includes\(communication\.workflow_status \|\| communication\.status\)/);
  assert.match(source, />重启任务<\/Button>/);
  assert.match(source, />确认完成<\/Button>/);
  assert.doesNotMatch(source, /canManageInitiatedTask && <Button onClick=\{openCreateTask\}>新增任务/);
});

test("accepted-task pending and processing footers expose only valid lifecycle actions", () => {
  assert.match(source, /statusTab === "pending" && <Button onClick=\{acceptSelectedTask\}>接受任务<\/Button>/);
  assert.match(source, /statusTab === "pending"[\s\S]*?simpleAction\(row, "complete"\)[\s\S]*?openTaskHandoff/);
  assert.match(source, /statusTab === "processing"[\s\S]*?完成任务[\s\S]*?转交任务/);
  assert.doesNotMatch(source, /canManageAcceptedTask && <Button onClick=\{acceptSelectedTask\}>/);
  assert.match(source, /isInitiatedTaskContext &&[\s\S]*?row\.initiator === profile\.username/);
});

test("accepted-task details provide contextual actions without withdrawal", () => {
  assert.match(source, /isAcceptedTaskContext && \["待接收", "待处理"\]/);
  assert.match(source, /isAcceptedTaskContext && \["待接收", "待处理", "处理中", "进行中", "已逾期"\]/);
  assert.match(source, /isInitiatedTaskContext &&[\s\S]*?\["待接收", "待处理", "处理中", "进行中"\]/);
});
