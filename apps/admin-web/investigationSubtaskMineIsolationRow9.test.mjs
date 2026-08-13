import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
  new URL("./src/InvestigationCenterPage.tsx", import.meta.url),
  "utf8",
);

test("我的调查任务向后端传递严格负责人视图", () => {
  assert.match(
    source,
    /route === "investigation-task-unassigned" \|\|[\s\S]*?route === "investigation-task-sub-mine"[\s\S]*?return "assigned"/,
  );
  assert.match(
    source,
    /investigation_view: investigationListView\(initialTab\)/,
  );
});

test("前端仍保留非管理员 owner 二次隔离", () => {
  assert.match(
    source,
    /initialTab === "investigation-task-sub-mine"[\s\S]*?profile\.role !== "admin"[\s\S]*?result = result\.filter\(\(row\) => names\.includes\(row\.owner\)\)/,
  );
});
