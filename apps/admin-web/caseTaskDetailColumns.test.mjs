import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

assert.match(source, /type TaskRow = \{[\s\S]*?priority: string;/, "case detail task rows must retain priority");
assert.equal(
  (source.match(/dataIndex:\s*\"priority\"/g) || []).length,
  3,
  "case task tab, customer task tab, and task drawer must all render priority",
);
assert.match(source, /api\.get\(`\/cases\/\$\{row\.id\}\/tasks`\)/, "case detail must load linked tasks");
assert.match(source, /rememberTaskDetailTarget\(\{ id: task\.id, serial_no: task\.serial_no \}\)/, "task links must preserve detail navigation");

console.log("case task detail column parity: PASS");
