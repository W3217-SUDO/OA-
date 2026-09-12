import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = (await Promise.all([
  "./src/legal/CaseCenterPage.tsx",
  "./src/legal/types.ts",
  "./src/legal/CaseDetail/CaseTasksPanel.tsx",
  "./src/legal/services/queriesActions.tsx",
].map((path) => readFile(new URL(path, import.meta.url), "utf8")))).join("\n");

assert.match(source, /type TaskRow = \{[\s\S]*?priority: string;/);
assert.equal((source.match(/dataIndex:\s*"priority"/g) || []).length, 3);
assert.match(source, /api\.get\(`\/cases\/\$\{row\.id\}\/tasks`, \{/);
assert.match(source, /const loadCounselDetailTasksPage = async \(row: CaseRow, nextPage = context\.counselDetailTaskPage, nextPageSize = context\.counselDetailTaskPageSize, nextVipFilter = context\.counselDetailTaskVipFilter\)[\s\S]*?params: \{ page: nextPage, page_size: nextPageSize, scope: "case", is_vip: nextVipFilter === "all" \? undefined : nextVipFilter === "vip" \}/);
assert.match(source, /const loadCounselDetailCustomerTasksPage = async \(row: CaseRow, nextPage = context\.counselDetailCustomerTaskPage, nextPageSize = context\.counselDetailCustomerTaskPageSize, nextVipFilter = context\.counselDetailCustomerTaskVipFilter\)[\s\S]*?params: \{ page: nextPage, page_size: nextPageSize, scope: "customer", is_vip: nextVipFilter === "all" \? undefined : nextVipFilter === "vip" \}/);
assert.match(source, /onClick=\{\(\)=>onOpenTask\(row\)\}/);
assert.match(source, /onOpenTask=\{openRelatedTask\}/);
assert.match(source, /const openRelatedTask = \(task: TaskRow\) => \{\s*if \(!task\.id\) return message\.warning[\s\S]*?void loadCaseTaskDetail\(task\);/);
assert.match(source, /api\.get\(`\/records\/\$\{task\.id\}`\)/);
assert.match(source, /任务编号：<\/b>\{viewingCaseTask\?\.serial_no \|\| "—"\}/);

console.log("case task detail column parity: PASS");
