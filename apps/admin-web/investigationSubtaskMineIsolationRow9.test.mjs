import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
  new URL("./src/investigation/InvestigationCenterPage.tsx", import.meta.url),
  "utf8",
);
const constants = await readFile(
  new URL("./src/investigation/constants.ts", import.meta.url),
  "utf8",
);

test("我的调查任务向后端传递严格负责人视图", () => {
  assert.match(
    constants,
    /route === "investigation-task-unassigned" \|\|[\s\S]*?route === "investigation-task-sub-mine"[\s\S]*?return "assigned"/,
  );
  assert.match(
    source,
    /investigation_view: investigationListView\(initialTab\)/,
  );
});

test("前端按真实系统角色保留 owner 二次隔离", () => {
  assert.match(
    source,
    /const isActualAdmin = actualRoleIds\.includes\("admin"\)[\s\S]*?initialTab === "investigation-task-sub-mine"[\s\S]*?!isActualAdmin[\s\S]*?result = result\.filter\(\(row\) => names\.includes\(row\.owner\)\)/,
  );
});
