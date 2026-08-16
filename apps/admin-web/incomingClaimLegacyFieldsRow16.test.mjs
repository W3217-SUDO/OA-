import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

for (const label of [
  "回款流水号",
  "回款单位",
  "客户名称",
  "回款时间",
  "回款金额",
  "回款方式",
  "银行单号",
  "合同编号",
  "登记备注",
  "领取备注",
]) {
  assert.match(source, new RegExp(`label="${label}"`));
}
assert.match(source, /claimTarget\?\.bank_source/);
assert.match(source, /name="customer"/);
assert.match(source, /name="comment"/);

console.log("incoming claim legacy fields row 16 contract passed");
