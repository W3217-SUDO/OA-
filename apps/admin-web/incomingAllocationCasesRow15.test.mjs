import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

assert.match(source, /allocation-candidates/);
assert.match(source, /案件费用明细/);
assert.match(source, /title: "本次回款"/);
assert.match(source, /title: "全部回款"/);
assert.match(source, /selectedAllocationKeys/);
assert.doesNotMatch(source, /description="本次可分配到一个合同应收计划及其案件/);

console.log("incoming allocation cases row 15 contract passed");
