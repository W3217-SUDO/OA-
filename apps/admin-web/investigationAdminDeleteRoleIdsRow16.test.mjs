import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/InvestigationCenterPage.tsx", import.meta.url), "utf8");

assert.match(source, /"investigation-task-published": \[[\s\S]*?"删除",/);
assert.match(source, /"investigation-task-unassigned": \["查询", "刷新", "新增子任务", "删除"\]/);
assert.match(source, /const isAdminAccount = \[profile\.role, \.\.\.\(profile\.role_ids \|\| \[\]\)\]\.includes\("admin"\)/);
assert.match(source, /label !== "删除" \|\| initialTab !== "investigation-task-unassigned" \|\| isAdminAccount/);
assert.doesNotMatch(source, /仅管理员可以删除调查任务/);

assert.doesNotMatch(source, /investigationBootstrapPromise/);
assert.match(source, /const loadInvestigationBootstrap = \(\) =>\s*Promise\.all\(\[/);

console.log("9.1 row 16 admin orphaned investigation delete entry passed");
