import test from "node:test";
import assert from "node:assert/strict";
import { buildCaseContractOptions } from "./src/caseContractPrefill.ts";

test("keeps a contract-originated case on its contract serial number before contracts finish loading", () => {
  const options = buildCaseContractOptions([], {
    id: 99,
    serial_no: "SHHT-2026-0099",
    customer: "测试客户1",
    title: "测试客户合同",
  });

  assert.deepEqual(options, [{
    value: 99,
    label: "SHHT-2026-0099｜测试客户1｜测试客户合同",
  }]);
});

test("uses the loaded contract label instead of a duplicate prefill option", () => {
  const options = buildCaseContractOptions([{
    id: 99,
    serial_no: "SHHT-2026-0099",
    customer: "测试客户1",
    title: "测试客户合同",
  }], {
    id: 99,
    serial_no: "SHHT-2026-0099",
    customer: "测试客户1",
    title: "测试客户合同",
  });

  assert.deepEqual(options, [{
    value: 99,
    label: "SHHT-2026-0099｜测试客户1｜测试客户合同",
  }]);
});
