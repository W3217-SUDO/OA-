import assert from "node:assert/strict";
import fs from "node:fs";

const platformSource = fs.readFileSync(
  new URL("./src/PlatformFinancePage.tsx", import.meta.url),
  "utf8",
);
const financeSource = fs.readFileSync(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

for (const source of [platformSource, financeSource]) {
  assert.match(source, /AutoComplete/);
  assert.match(source, /输入回款单位，或从系统客户中选择/);
  assert.match(source, /filterOption=\{\(inputValue, option\) =>/);
}
assert.match(platformSource, /options=\{customers\.map\(\(value\) => \(\{ value, label: value \}\)\)\}/);
assert.match(financeSource, /value: customer\.title/);

console.log("finance payer autocomplete row 13 contract passed");
