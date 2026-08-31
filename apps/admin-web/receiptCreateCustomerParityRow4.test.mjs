import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const page = fs.readFileSync(new URL("./src/PlatformFinancePage.tsx", import.meta.url), "utf8");

test("row 4 searches system customers for both receipt customer fields", () => {
  assert.match(page, /api\.get\("\/finance\/customer-options", \{ params: \{ keyword \} \}\)/);
  assert.match(page, /onSelect=\{\(customer\) => form\.setFieldValue\("customer", customer\)\}/);
  assert.match(page, /if \(customer\) form\.setFieldValue\("payerName", customer\)/);
  assert.doesNotMatch(page, /get\("\/records\?module=customer&page_size=100"\)/);
});

test("row 4 generates a legacy-style bank reference from the bank field", () => {
  assert.match(page, /return `\$\{dayjs\(\)\.format\("YYMMDD"\)\}-\$\{suffix\}`/);
  assert.match(page, /placeholder="点击输入框自动生成"/);
  assert.match(page, /onFocus=\{\(\) => \{/);
  assert.match(page, />生成<\/Button>/);
});
