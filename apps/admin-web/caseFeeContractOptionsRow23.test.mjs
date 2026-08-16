import assert from "node:assert/strict";
import test from "node:test";

import { buildCaseFeeContractOptions } from "./src/caseFeeContractOptions.mjs";

test("row 23 keeps the case-linked historical contract visible by contract number", () => {
  const options = buildCaseFeeContractOptions(
    [{ id: 12, serial_no: "SHHT2600012", title: "其他合同", customer: "其他客户" }],
    {
      customer: "目标客户",
      data: {
        contract_record_id: 111,
        contract_no: "SHHT2610053",
        contract_title: "目标客户委托合同",
      },
    },
    null,
  );

  assert.deepEqual(options, [
    { value: 111, label: "SHHT2610053｜目标客户委托合同" },
  ]);
});

test("row 23 keeps all selectable customer contracts without duplicating the linked one", () => {
  const contracts = [
    { id: 111, serial_no: "SHHT2610053", title: "关联合同", customer: "目标客户" },
    { id: 112, serial_no: "SHHT2610054", title: "延伸合同", customer: "目标客户" },
  ];
  const options = buildCaseFeeContractOptions(
    contracts,
    { customer: "目标客户", data: { contract_record_id: 111, contract_no: "SHHT2610053" } },
    null,
  );

  assert.deepEqual(options, [
    { value: 111, label: "SHHT2610053｜关联合同" },
    { value: 112, label: "SHHT2610054｜延伸合同" },
  ]);
});
