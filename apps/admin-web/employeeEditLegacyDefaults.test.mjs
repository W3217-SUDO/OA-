import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { normalizeEmployeeDataLevel, resolveEmployeeSystemRole } from "./src/employeeEditLegacyDefaults.mjs";

test("legacy employee data receives a least-privilege data level", () => {
  assert.equal(normalizeEmployeeDataLevel(""), "本人");
  assert.equal(normalizeEmployeeDataLevel(undefined), "本人");
  assert.equal(normalizeEmployeeDataLevel("部门"), "部门");
});

test("legacy business roles become valid role-select values", () => {
  assert.equal(resolveEmployeeSystemRole({ accountRole: "user", staffRole: "律师助理" }), "user");
  assert.equal(resolveEmployeeSystemRole({ accountRole: "律师助理", staffRole: "律师助理" }), "business:律师助理");
  assert.equal(resolveEmployeeSystemRole({ permissionRole: "品管审核", accountRole: "user" }), "business:品管审核");
  assert.equal(resolveEmployeeSystemRole({}), "user");
});

test("employee edit values are applied after the conditional form is mounted", () => {
  const source = readFileSync(new URL("./src/HrCenterPage.tsx", import.meta.url), "utf8");
  assert.match(source, /useEffect\(\(\)=>\{if\(!editingEmployee\|\|!employeeEditInitialValues\)return;employeeEditForm\.setFieldsValue\(employeeEditInitialValues\)\}/);
  assert.doesNotMatch(source, /setEmployeeLoginEnabled\(loginEnabled\);employeeEditForm\.setFieldsValue\(/);
  assert.match(source, /name="system_role"[^>]+extra="业务角色来自角色管理及旧系统角色目录/);
  assert.doesNotMatch(source, /name="system_role"[^>]*><Select[^>]*\/><div/);
});
