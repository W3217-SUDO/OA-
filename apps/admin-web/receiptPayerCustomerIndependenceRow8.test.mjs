import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/PlatformFinancePage.tsx", import.meta.url), "utf8");
const start = source.indexOf('label="回款单位" name="payerName"');
const end = source.indexOf('label="回款时间"', start);
const form = source.slice(start, end);

assert.ok(start >= 0 && end > start, "新增回款表单必须包含独立的回款单位与客户名称字段");
assert.doesNotMatch(form, /onSelect=\{\(customer\) => form\.setFieldValue\("customer", customer\)\}/);
assert.doesNotMatch(form, /form\.setFieldValue\("payerName", customer\)/);
assert.match(form, /label="客户名称" name="customer"/);
assert.match(form, /allowClear/);

console.log("receipt payer/customer independence row 8 frontend contract passed");
