import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const page = fs.readFileSync("src/HrCenterPage.tsx", "utf8");

test("customer accounts keep a visible account type and ordinary system role", () => {
  assert.match(page, /title:'账号类型'/);
  assert.match(page, /normalizedAccountType==='客户账号'\?'客户联系人':permissionRole/);
  assert.match(page, /normalizedAccountType===employeeAccountType\?selectedSystemRole:'user'/);
  assert.match(page, /account_type:'客户账号',data:\{\.\.\.editableData,staff_role:'客户联系人',position:'客户联系人'/);
});
