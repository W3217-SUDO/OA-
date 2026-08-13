import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const source = fs.readFileSync(path.join(import.meta.dirname, "src", "CaseCenterPage.tsx"), "utf8");
const feeSection = source.slice(source.indexOf('{key:"firm-fees"'), source.indexOf('{key:"reminders"'));
const dateColumns = [...feeSection.matchAll(/title:\"提交(?:日期|时间)\"[\s\S]*?render:\(_:unknown,row:CaseRow\)=>String\(([^)]*)\)/g)].map((match) => match[1]);

assert.equal(dateColumns.length, 2, "案件费用的律所费用和内部结算都应有提交日期列");
for (const expression of dateColumns) {
  assert.match(expression, /row\.data\.submitted_at/);
  assert.match(expression, /row\.created_at/);
  assert.match(expression, /row\.data\.created_at/);
}

const archiveColumn = source.slice(source.indexOf('{title:"归档信息",key:"archive"'), source.indexOf('{title:"案件编号",dataIndex:"serial_no"'));
assert.match(archiveColumn, /onClick=\{\(\)=>void openCounselDetail\(row\)\}/);
assert.doesNotMatch(archiveColumn, /openCaseTasks\(row\)/);

const backend = fs.readFileSync(path.join(import.meta.dirname, "..", "api-server", "app", "main.py"), "utf8");
assert.match(backend, /submitted_at = datetime\.now\(\)\.isoformat\(timespec=\"seconds\"\)/);
assert.match(backend, /item\.data = \{\*\*data, \"submitted_at\": submitted_at, \"submitted_by\": identity\[\"username\"\]\}/);

console.log("case fee submitted date row 25: PASS");
