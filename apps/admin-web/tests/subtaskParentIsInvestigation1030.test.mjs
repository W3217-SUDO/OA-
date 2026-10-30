// BUG20261030013：待我分配的调查任务里新增子任务，父任务固定为当前调查任务，不再默认挂到已有子任务下。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const page = fs.readFileSync(new URL("../src/investigation/InvestigationCenterPage.tsx", import.meta.url), "utf8");
const drawer = fs.readFileSync(new URL("../src/investigation/TaskDetailDrawer.tsx", import.meta.url), "utf8");

test("新增子任务不再把已有子任务预填为父任务", () => {
  assert.ok(!page.includes("existingTasks.find((task) => !task.parent_task_id)"));
  assert.ok(page.includes('taskForm.setFieldValue("parent_task_id", undefined);'));
});

test("新增子任务表单没有“父调查任务”下拉框，始终提示当前调查任务", () => {
  assert.ok(!drawer.includes('label="父调查任务"'));
  assert.ok(!drawer.includes("onParentTaskChange"));
  assert.match(drawer, /\{creatingSubtask && \(\s*<Alert[\s\S]*?父调查任务：\$\{taskTarget\?\.serial_no/);
});
