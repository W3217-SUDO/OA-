import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(
  new URL("./src/OrganizationCenterPage.tsx", import.meta.url),
  "utf8",
);

test("department list keeps the legacy 15-row page boundary", () => {
  const departmentTable = source.match(
    /dataSource=\{departments\}[\s\S]*?pagination=\{\{([\s\S]*?)\}\}\s*\/>/,
  );

  assert.ok(departmentTable, "department table configuration should exist");
  assert.match(departmentTable[1], /pageSize:\s*15\b/);
});

test("department management keeps permissions in role management and exposes overdue deduction", () => {
  const departmentColumns = source.match(
    /const departmentColumns:[\s\S]*?=\s*\[([\s\S]*?)\];\s*const roleColumns/,
  );
  const departmentForm = source.match(
    /\) : \(\s*<Form form=\{departmentForm\}[\s\S]*?<\/Form>\s*\)\}\s*<\/Modal>/,
  );

  assert.ok(departmentColumns, "department columns should exist");
  assert.ok(departmentForm, "department form should exist");
  assert.match(departmentColumns[1], /title:\s*"是否逾期扣款"/);
  assert.match(departmentColumns[1], /dataIndex:\s*"overdue_deduction"/);
  assert.match(departmentForm[0], /title="部门只维护组织和数据归属"/);
  assert.match(departmentForm[0], /角色管理/);
  assert.match(departmentForm[0], /name="overdue_deduction"/);
  assert.doesNotMatch(departmentForm[0], /permissionTreeData|权限来源部门/);
});
