import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { buildCaseFeeContractOptions } from "./src/caseFeeContractOptions.mjs";

const page = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const sourceCase = { customer: "测试客户8.3", data: {} };
const contracts = [
  { id: 1, serial_no: "LF001", title: "律所合同", customer: "测试客户8.3", data: { contract_body: "律所" } },
  { id: 2, serial_no: "PT001", title: "平台合同", customer: "其他客户", data: { contract_body: "平台" } },
  { id: 3, serial_no: "LF002", title: "历史律所合同", customer: "测试客户8.3", data: {} },
];

test("row 6 filters selectable contracts by case customer and contract body", () => {
  assert.deepEqual(buildCaseFeeContractOptions(contracts, sourceCase, null, "律所").map((item) => item.value), [1, 3]);
  assert.deepEqual(buildCaseFeeContractOptions(contracts, sourceCase, null, "平台"), []);
});

test("row 6 blocks the fee drawer when the customer has no matching contract body", () => {
  assert.match(page, /当前案件客户名下没有\$\{expenseScope\}合同，无法新增\$\{expenseScope\}费用/);
  assert.match(page, /buildCaseFeeContractOptions\(availableContracts, row, null, expenseScope\)/);
  assert.match(page, /feeItems\[0\]\?\.expense_scope/);
  assert.match(page, /initialContractId = eligibleContracts\.some/);
});
