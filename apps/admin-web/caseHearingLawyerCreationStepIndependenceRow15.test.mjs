import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const handler = source.match(/const saveCaseHearingLawyer = async \(\) => \{[\s\S]*?\n  \};/);

assert.ok(handler, "应保留修改开庭律师的真实保存处理器");
assert.match(
  handler[0],
  /api\.put\(`\/cases\/\$\{editingCaseHearingLawyer\.id\}\/hearing-lawyer`,\s*\{[\s\S]*?hearing_lawyer:[\s\S]*?comment:/,
  "修改开庭律师必须调用独立持久化接口",
);
assert.doesNotMatch(
  handler[0],
  /\/assign|handling_lawyers|assistant|customer_manager/,
  "修改开庭律师不得复用整组案件人员分配或覆盖其他人员",
);
assert.match(handler[0], /setViewingCounselCase\(data\)[\s\S]*?await load\(\)/, "保存后应立即回读详情并刷新列表");

console.log("CASE_HEARING_LAWYER_ROW15_OK");
