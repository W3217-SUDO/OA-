import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const source = fs.readFileSync(path.join(here, "src", "OrganizationCenterPage.tsx"), "utf8");
const apiSource = fs.readFileSync(path.join(here, "..", "api-server", "app", "main.py"), "utf8");

test("organization matrix covers legacy department and role fields", () => {
  for (const field of ["name", "code", "parent_department_id", "parent_department_name", "manager", "overdue_deduction", "sort_order", "is_active"]) {
    assert.match(source, new RegExp(field));
  }
  for (const field of ["name", "code", "permissions", "description", "sort_order", "is_active"]) {
    assert.match(source, new RegExp(field));
  }
});

test("organization lists retain legacy fifteen-row paging plus boundary controls", () => {
  assert.equal((source.match(/pageSize:\s*15/g) || []).length, 2);
  assert.match(source, /showSizeChanger:\s*true/);
  assert.match(source, /pageSizeOptions:\s*\[[^\]]*15/);
  assert.match(source, /showQuickJumper:\s*true/);
  assert.match(source, /showTotal:\s*\(total\)/);
});

test("empty state uses the current view add action", () => {
  assert.match(source, /const emptyContent/);
  assert.match(source, /\{button\}/);
  assert.doesNotMatch(source, /emptyContent[\s\S]*?新增角色[\s\S]*?\n\s*<\/Button>/);
});

test("department form preserves legacy required validation and parent selector", () => {
  assert.match(source, /label="部门名称"[\s\S]*?message:\s*"请输入部门名称\."/);
  assert.match(source, /label="部门代码"[\s\S]*?message:\s*"请输入部门代码\."/);
  assert.match(source, /label="上级部门"/);
  assert.match(source, /请选择（顶级部门）/);
});

test("role form exposes legacy required validation and local role fields", () => {
  assert.match(source, /label="角色名称"[\s\S]*?message:\s*"请输入角色名称\."/);
  assert.match(source, /label="角色代码"[\s\S]*?message:\s*"请输入角色代码\."/);
  assert.match(source, /label="说明"[\s\S]*?message:\s*"请输入角色名称描述\."/);
  assert.match(source, /SYSTEM-ADMIN/);
});

test("save/cancel flows retain API error detail and legacy feedback", () => {
  assert.match(source, /api\.post\("\/hr\/departments"/);
  assert.match(source, /api\.patch\(`\/hr\/departments\//);
  assert.match(source, /api\.post\("\/hr\/job-roles"/);
  assert.match(source, /api\.patch\(`\/hr\/job-roles\//);
  assert.match(source, /message\.success\("保存成功\."\)/);
  assert.match(source, /error\?\.response\?\.data\?\.detail \|\| "保存失败\."/);
  assert.match(source, /onCancel=\{\(\) => setOpen\(false\)\}/);
});

test("organization tree is rendered from department parent relationships", () => {
  assert.match(source, /useMemo/);
  assert.match(source, /departmentTreeData/);
  assert.match(source, /parent_department_id/);
  assert.match(source, /<Tree[\s\S]*treeData=\{departmentTreeData\}/);
});

test("delete flows confirm and protect children, references and system administrator", () => {
  assert.match(source, /Popconfirm[\s\S]*确认删除该部门/);
  assert.match(source, /下级部门/);
  assert.match(source, /SYSTEM-ADMIN.*不可删除|系统管理员角色不可删除/);
  assert.match(source, /api\.delete\(`\/hr\/departments\//);
  assert.match(source, /api\.delete\(`\/hr\/job-roles\//);
  assert.match(source, /error\?\.response\?\.data\?\.detail \|\| "删除失败\."/);
});

test("permissions tree supports cancel/save and cannot downgrade SYSTEM-ADMIN", () => {
  assert.match(source, /checkable/);
  assert.match(source, /selectedRolePermissions/);
  assert.match(source, /onCancel=\{\(\) => setPermissionRole\(null\)\}/);
  assert.match(source, /api\.patch\(`\/hr\/job-roles\//);
  assert.match(source, /disabled=\{permissionRole\?\.code === "SYSTEM-ADMIN"\}/);
  assert.match(source, /系统管理员权限由系统强制保持完整/);
});

test("admin boundary is enforced for every organization mutation", () => {
  assert.match(source, /organizationActionAccess\(accessRole\)\.canManageOrganization/);
  assert.ok((source.match(/if \(!canManageOrganization\)/g) || []).length >= 5);
  assert.match(source, /canDeleteOrganizationRole\(row\.code\)/);
});

test("API organization endpoints expose duplicate, reference, hierarchy and admin guards", () => {
  assert.match(apiSource, /create_department[\s\S]*_require_admin\(identity\)/);
  assert.match(apiSource, /Department\.code == code, Department\.name == name/);
  assert.match(apiSource, /child_count/);
  assert.match(apiSource, /BusinessRecord\.department == item\.name/);
  assert.match(apiSource, /create_job_role[\s\S]*_require_admin\(identity\)/);
  assert.match(apiSource, /item\.code == "SYSTEM-ADMIN"/);
  assert.match(apiSource, /BusinessRecord\.module == "hr"/);
});

test("audit fields remain available from organization API and are represented by the UI contract", () => {
  assert.match(apiSource, /created_by/);
  assert.match(apiSource, /updated_by/);
  assert.match(source, /created_by|updated_by/);
});
