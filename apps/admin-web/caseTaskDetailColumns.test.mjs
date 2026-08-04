import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const taskEndpoint =
  "api.get(" + String.fromCharCode(96) + "/cases/" + "$" + "{row.id}" + "/tasks" + String.fromCharCode(96) + ", {";

assert.match(source, /type TaskRow = \{[\s\S]*?priority: string;/, "case detail task rows must retain priority");
assert.equal(
  (source.match(/dataIndex:\s*\"priority\"/g) || []).length,
  3,
  "case task tab, customer task tab, and task drawer must all render priority",
);
assert.ok(source.includes(taskEndpoint), "case detail must load linked tasks with request config");
assert.match(
  source,
  /params:\s*\{\s*page:\s*CASE_TASK_DEFAULT_PAGE,\s*page_size:\s*CASE_TASK_DEFAULT_PAGE_SIZE\s*\}/,
  "case detail task load must request the first server page",
);
assert.match(source, /rememberTaskDetailTarget\(\{ id: task\.id, serial_no: task\.serial_no \}\)/, "task links must preserve detail navigation");

console.log("case task detail column parity: PASS");
