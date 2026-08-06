import test from "node:test";
import assert from "node:assert/strict";
import { buildCaseContractOptions, resolveCaseSourcePerson } from "./src/caseContractPrefill.ts";

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

test("prefers a contract person's display name over its login account for a new case", () => {
  assert.equal(resolveCaseSourcePerson({
    id: 1,
    serial_no: "SHHT2600001",
    customer: "客户",
    title: "合同",
    owner: "admin",
    owner_display_name: "管理员",
    data: { source_person: "admin", source_person_display_name: "管理员" },
  }), "管理员");
});
