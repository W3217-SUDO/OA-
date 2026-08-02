import test from "node:test";
import assert from "node:assert/strict";

let legacyEmployeeSelectOptions;
let legacyEmployeeBasicDefaults;
try {
  ({ legacyEmployeeSelectOptions, legacyEmployeeBasicDefaults } = await import("./src/employeeBasicSelectOptions.mjs"));
} catch {}

test("uses legacy fixed choices for employee status fields", () => {
  assert.deepEqual(legacyEmployeeSelectOptions, {
    political_status: ["党员", "团员", "学生", "其他"],
    marriage: ["已婚", "未婚"],
    childbearing: ["已生", "未生"],
    employment_status: ["在职", "离职"],
  });
});

test("uses legacy defaults for employee status fields", () => {
  assert.deepEqual(legacyEmployeeBasicDefaults, {
    political_status: "党员",
    marriage: "未婚",
    childbearing: "未生",
    employment_status: "在职",
  });
});
