import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const page = fs.readFileSync("src/HrCenterPage.tsx", "utf8");

test("customer accounts keep a visible account type and ordinary system role", () => {
  assert.match(page, /title:'账号类型'/);
  assert.match(page, /editingAccountType!==employeeAccountType/);
  assert.match(page, /setFieldValue\('system_role','user'\)/);
  assert.match(page, /normalizedAccountType===employeeAccountType\?selectedSystemRole:'user'/);
});
