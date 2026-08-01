import test from "node:test";
import assert from "node:assert/strict";
import { employeeSubrecordCreateMessage } from "./src/employeeSubrecordGuard.mjs";

test("requires saving employee basic information before creating a leave record", () => {
  assert.equal(
    employeeSubrecordCreateMessage(undefined),
    "请先保存员工基本信息，再维护此页记录",
  );
});

test("allows creating a leave record after the employee exists", () => {
  assert.equal(employeeSubrecordCreateMessage(42), null);
});
