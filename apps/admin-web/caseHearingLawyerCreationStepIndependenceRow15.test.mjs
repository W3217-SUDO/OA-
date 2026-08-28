import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const handler = source.match(/const saveCaseHearingLawyer = async \(\) => \{[\s\S]*?\n  \};/);
const opener = source.match(/const openCaseHearingLawyer = \(row: CaseRow\) => \{[\s\S]*?\n  \};/);

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
assert.ok(opener, "应保留修改开庭律师弹窗入口");
assert.match(opener[0], /can_edit_hearing_lawyer/, "可见案件应使用独立的开庭律师修改能力");
assert.doesNotMatch(opener[0], /can_assign_team/, "修改开庭律师不得再依赖案件人员分配权限");
assert.match(source, /counselDetailCapabilities\.can_edit_hearing_lawyer[\s\S]{0,180}openCaseHearingLawyer/, "详情菜单应按专用能力展示修改开庭律师");

console.log("CASE_HEARING_LAWYER_ROW15_OK");
