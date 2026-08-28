import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { buildCaseFeeContractOptions } from "./src/caseFeeContractOptions.mjs";

const page = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const sourceCase = { id: 14, customer: "\u6d4b\u8bd5\u5ba2\u62378.3", data: { contract_record_id: 5 } };
const contracts = [
  ...Array.from({ length: 8 }, (_, index) => ({ id: index + 1, serial_no: `LAW-${index + 1}`, title: `law-${index + 1}`, customer: sourceCase.customer, data: { contract_body: "\u5f8b\u6240" } })),
  ...Array.from({ length: 3 }, (_, index) => ({ id: index + 101, serial_no: `PLATFORM-${index + 1}`, title: `platform-${index + 1}`, customer: sourceCase.customer, data: { contract_body: "\u5e73\u53f0" } })),
  { id: 999, serial_no: "OTHER-CUSTOMER", title: "other", customer: "\u5176\u4ed6\u5ba2\u6237", data: { contract_body: "\u5f8b\u6240" } },
];

test("row 14 keeps every customer contract for each fee scope", () => {
  assert.equal(buildCaseFeeContractOptions(contracts, sourceCase, null, "\u5f8b\u6240").length, 8);
  assert.equal(buildCaseFeeContractOptions(contracts, sourceCase, null, "\u5e73\u53f0").length, 3);
});

test("row 14 loads fee contracts per visible case and keeps the linked contract as default", () => {
  assert.match(page, /api\.get\(`\/cases\/\$\{row\.id\}\/fee-contracts`/);
  assert.match(page, /params: \{ expense_scope: expenseScope \}/);
  assert.match(page, /eligibleContracts\.some\(\(option\) => option\.value === linkedContractId\)[\s\S]*?linkedContractId/);
});
