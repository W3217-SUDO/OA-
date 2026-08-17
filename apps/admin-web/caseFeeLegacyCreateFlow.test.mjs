import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

for (const label of ["新增官费", "新增第三方费用", "新增代理费", "新增其他费用", "新建提成(选择代理费)"]) {
  assert.match(source, new RegExp(label.replace(/[()]/g, "\\$&")));
}
assert.match(source, /className="case-fee-create-drawer"/);
assert.match(source, /items=\{\[\{ title: "新增费用" \}, \{ title: "申请付款" \}\]\}/);
for (const field of ["案号", "合同号", "费用类型", "金额", "备注", "截止日期", "操作"]) {
  assert.match(source, new RegExp(`<span>${field}<\\/span>`));
}
assert.match(source, /caseFeeCreateStep === 0 \? "下一步" : "申请付款"/);
assert.match(source, /\/finance\/fees\/\$\{row\.id\}\/submit/);

console.log("legacy case fee create flow contract passed");
