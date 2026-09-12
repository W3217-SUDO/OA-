import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const center = fs.readFileSync(new URL("./src/tp/TaskCenterPage.tsx", import.meta.url), "utf8");
const list = fs.readFileSync(new URL("./src/tp/TaskList.tsx", import.meta.url), "utf8");
const detail = fs.readFileSync(new URL("./src/tp/TaskDetail.tsx", import.meta.url), "utf8");
const source = `${center}\n${list}\n${detail}`;

test("created-task completed and rejected detail actions match legacy workflow", () => {
  assert.match(list, /canManageInitiatedTask && statusTab === "finished" && \([\s\S]*?onConfirmTask\(selected\)[\s\S]*?验收任务/);
  assert.match(list, /\(canManageInitiatedTask \|\| canManageCompanyCreatedTask\) &&[\s\S]*?selected\?\.status === "已拒绝"[\s\S]*?onResendTask\(selected\)/);
  assert.match(list, /\["已完成", "待确认"\]\.includes\([\s\S]*?!selected\?\.auto_completed[\s\S]*?onRestartTask\(selected\)/);
  assert.match(center, /onConfirmTask=\{\(row\) => void simpleAction\(row, "confirm"\)\}[\s\S]*?onRestartTask=\{\(row\) => void simpleAction\(row, "restart"\)\}/);
  assert.match(detail, /isInitiatedTaskContext && \["已完成", "待确认", "已拒绝"\]\.includes\(communication\.workflow_status \|\| communication\.status\)[\s\S]*?onSimpleAction\(communication, "restart"\)[\s\S]*?onSimpleAction\(communication, "confirm"\)/);
  assert.doesNotMatch(source, /canManageInitiatedTask && <Button onClick=\{openCreateTask\}>新增任务/);
});

test("accepted-task pending and processing footers expose only valid lifecycle actions", () => {
  assert.match(list, /canManageAcceptedTask && statusTab === "pending" && \([\s\S]*?onAcceptSelected[\s\S]*?接受任务/);
  assert.match(list, /canManageAcceptedTask && statusTab === "pending" && \([\s\S]*?onCompleteSelected[\s\S]*?onOpenHandoff\(selected\)/);
  assert.match(list, /canManageAcceptedTask && statusTab === "processing" && \([\s\S]*?onCompleteOne\(selected\)[\s\S]*?onOpenHandoff\(selected\)/);
  assert.match(center, /onAcceptSelected=\{acceptSelectedTask\}[\s\S]*?onCompleteSelected=\{\(\) => requireOne\(\(row\) => void simpleAction\(row, "complete"\)\)\}[\s\S]*?onCompleteOne=\{\(row\) => void simpleAction\(row, "complete"\)\}[\s\S]*?onOpenHandoff=\{openTaskHandoff\}/);
  assert.match(source, /isInitiatedTaskContext &&[\s\S]*?row\.initiator === profile\.username/);
});

test("accepted-task details provide contextual actions without withdrawal", () => {
  assert.match(source, /isAcceptedTaskContext && \["待接收", "待处理"\]/);
  assert.match(source, /isAcceptedTaskContext && \["待接收", "待处理", "处理中", "进行中", "已逾期"\]/);
  assert.match(source, /isInitiatedTaskContext &&[\s\S]*?\["待接收", "待处理", "处理中", "进行中"\]/);
});
