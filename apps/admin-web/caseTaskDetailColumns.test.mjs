import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

assert.match(source, /type TaskRow = \{[\s\S]*?priority: string;/);
assert.equal((source.match(/dataIndex:\s*"priority"/g) || []).length, 3);
assert.match(source, /api\.get\(`\/cases\/\$\{row\.id\}\/tasks`, \{/);
assert.match(source, /params: \{ page: CASE_TASK_DEFAULT_PAGE, page_size: CASE_TASK_DEFAULT_PAGE_SIZE, scope: "case" \}/);
assert.match(source, /params: \{ page: CASE_TASK_DEFAULT_PAGE, page_size: CASE_TASK_DEFAULT_PAGE_SIZE, scope: "customer" \}/);
assert.match(source, /rememberTaskDetailTarget\(\{ id: task\.id, serial_no: task\.serial_no \}\)/);

console.log("case task detail column parity: PASS");
