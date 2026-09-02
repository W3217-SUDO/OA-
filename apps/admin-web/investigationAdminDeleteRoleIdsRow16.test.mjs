import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/InvestigationCenterPage.tsx", import.meta.url), "utf8");

assert.match(source, /"investigation-task-published": \[[\s\S]*?"删除",/);
assert.match(source, /"investigation-task-unassigned": \["查询", "刷新", "新增子任务"\]/);
assert.doesNotMatch(source, /"investigation-task-unassigned": \[[^\]]*"删除"/);
assert.doesNotMatch(source, /仅管理员可以删除调查任务/);

console.log("9.1 row 16 legacy investigation delete entry parity passed");
