import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./src/TaskCenterPage.tsx", import.meta.url), "utf8");

test("row 11 initiated-task footer exposes withdrawal instead of task creation", () => {
  const footer = source.slice(source.indexOf('<div className="task-bottom-actions">'), source.indexOf("title=\"新增任务\""));
  assert.match(footer, /canManageInitiatedTask[\s\S]*撤回任务/);
  assert.match(footer, /disabled=\{!canWithdrawTask\(selected\)\}/);
  assert.doesNotMatch(footer, /canManageInitiatedTask && <Button onClick=\{openCreateTask\}>新增任务/);
});
