import assert from "node:assert/strict";
import fs from "node:fs";

const center = fs.readFileSync(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");

assert.match(
  center,
  /const openMainListCustomerCases = \(record: IprRecord\) => \{[\s\S]*?const customerKeyword = String\(record\.data\.customer_no \|\| record\.customer \|\| ""\)\.trim\(\);[\s\S]*?setKeyword\(customerKeyword\);[\s\S]*?setPage\(1\);[\s\S]*?void load\(1, pageSize, customerKeyword\)/,
  "IPR main-list customer navigation should filter from page one using the customer number or name.",
);

assert.match(
  center,
  /dataIndex: "customer",[\s\S]*?render: \(_, row\) => \([\s\S]*?<Button type="link"[^>]*onClick=\{\(\) => openMainListCustomerCases\(row\)\}/,
  "IPR main-list customer cells should be an explicit customer-case-list navigation entry.",
);

console.log("ipr main-list customer navigation parity: PASS");
