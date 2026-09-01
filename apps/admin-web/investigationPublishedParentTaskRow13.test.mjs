import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/InvestigationCenterPage.tsx", import.meta.url), "utf8");

assert.match(source, /route === "investigation-task-mine"\) return "published"/);
assert.match(source, /const module = initialTab\.startsWith\("investigation-task-sub-"\)\s*\? "task"\s*:\s*initialTab\.startsWith\("investigation-task-"\)\s*\? "investigation"/s);

const mineButtons = source.match(/"investigation-task-mine": \[([\s\S]*?)\],/s)?.[1] || "";
const overdueButtons = source.match(/"investigation-task-overdue": \[([\s\S]*?)\],/s)?.[1] || "";
for (const buttons of [mineButtons, overdueButtons]) {
  for (const expected of ["查询", "刷新", "修改", "上传调查资料"]) assert.ok(buttons.includes(`"${expected}"`));
  for (const forbidden of ["新增线索", "关闭任务并生成报告"]) assert.ok(!buttons.includes(`"${forbidden}"`));
}

console.log("9.1 row 13 published parent investigation task contract passed");
