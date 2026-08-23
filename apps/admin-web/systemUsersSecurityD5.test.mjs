import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const pageSource = fs.readFileSync(
  new URL("./src/SystemCenterPage.tsx", import.meta.url),
  "utf8",
);
const apiSource = fs.readFileSync(
  new URL("../api-server/app/main.py", import.meta.url),
  "utf8",
);
const appSource = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");
const usersStart = pageSource.indexOf('} else if (initialView === "system-users")');
const usersEnd = pageSource.indexOf('} else if (initialView === "system-roles")', usersStart);
const usersBlock = pageSource.slice(usersStart, usersEnd);
const securityStart = pageSource.indexOf('} else if (initialView === "system-security")');
const securityEnd = pageSource.indexOf("} else {", securityStart);
const securityBlock = pageSource.slice(securityStart, securityEnd);

test("system user list keeps the legacy fields and local status/action extras", () => {
  for (const field of ["username", "display_name", "email", "mobile", "office_phone", "department"]) {
    assert.match(usersBlock, new RegExp(`dataIndex: "${field}"`));
  }
  for (const field of ["role", "contract_approval_enabled", "is_active", "failed_login_attempts", "locked_until", "last_login_at"]) {
    assert.match(usersBlock, new RegExp(`dataIndex: "${field}"`));
  }
});

test("system user list restores the legacy 15-row pagination contract", () => {
  assert.match(usersBlock, /defaultPageSize: 15/);
  assert.match(usersBlock, /showSizeChanger: true/);
  assert.match(usersBlock, /pageSizeOptions: \["10", "15", "20", "50", "100", "200"\]/);
  assert.match(usersBlock, /showQuickJumper: \{ goButton: "GO" \}/);
  assert.match(usersBlock, /showTotal:/);
});

test("system user empty state keeps the actionable create entry", () => {
  assert.match(usersBlock, /没有查询到符合条件的记录，可以去/);
  assert.match(usersBlock, /新增用户/);
  assert.match(usersBlock, /onClick=\{\(\) => editUser\(\)\}/);
});

test("system user query keeps Enter and create actions", () => {
  assert.match(usersBlock, /onPressEnter=\{\(\) => loadUsers\(keyword\)\}/);
  assert.match(usersBlock, /onClick=\{\(\) => loadUsers\(keyword\)\}/);
  assert.match(usersBlock, /onClick=\{\(\) => editUser\(\)\}/);
});

test("system user modal keeps required fields and cancel semantics", () => {
  assert.match(usersBlock, /onCancel=\{\(\) => setUserOpen\(false\)\}/);
  assert.match(pageSource, /name="display_name"[\s\S]*required: true/);
  assert.match(pageSource, /name="department"[\s\S]*required: true/);
  assert.match(pageSource, /name="role"[\s\S]*required: true/);
  assert.match(pageSource, /name="password"[\s\S]*min: 8/);
});

test("system user personnel-name display never falls back to username", () => {
  assert.match(pageSource, /PERSON_NAME_PLACEHOLDER = "姓名待维护"/);
  assert.match(pageSource, /const personDisplayName = /);
  assert.match(pageSource, /String\(row\?\.display_name \|\| ""\)\.trim\(\) \|\| PERSON_NAME_PLACEHOLDER/);
  assert.match(usersBlock, /renderPersonDisplayName\(_value, row\)/);
  assert.match(usersBlock, /title=\{`重置密码：\$\{personDisplayName\(resettingUser \|\| undefined\)\}`\}/);
  assert.doesNotMatch(pageSource, /hasChineseName/);
  assert.doesNotMatch(pageSource, /label: item\.display_name \|\| item\.username/);
  assert.doesNotMatch(usersBlock, /display_name\s*\|\|\s*row\.username/);
});

test("system user destructive helpers protect deletion but permit password reset for the current administrator", () => {
  const helpers = pageSource.slice(
    pageSource.indexOf("const removeUser = async"),
    pageSource.indexOf("const editRole =", pageSource.indexOf("const removeUser = async")),
  );
  assert.match(helpers, /row\.role === "admin"/);
  assert.match(helpers, /系统管理员账号不可删除/);
  assert.doesNotMatch(helpers, /resettingUser\.username === currentUsername/);
  assert.match(helpers, /\/reset-password/);
});

test("system user action buttons retain lock and delete confirmation guards", () => {
  assert.doesNotMatch(usersBlock, /disabled=\{row\.username === currentUsername\}/);
  assert.match(usersBlock, /disabled=\{!row\.failed_login_attempts && !row\.locked_until\}/);
  assert.match(usersBlock, /row\.role !== "admin"/);
  assert.match(usersBlock, /Popconfirm/);
  assert.match(usersBlock, /onConfirm=\{\(\) => removeUser\(row\)\}/);
});

test("security policy keeps legacy bounded numeric fields and save feedback", () => {
  assert.match(securityBlock, /name="min_password_length"[\s\S]*min=\{8\}[\s\S]*max=\{128\}/);
  assert.match(securityBlock, /name="max_failed_attempts"[\s\S]*min=\{1\}[\s\S]*max=\{20\}/);
  assert.match(securityBlock, /name="lock_minutes"[\s\S]*min=\{1\}[\s\S]*max=\{1440\}/);
  assert.match(securityBlock, /name="token_minutes"[\s\S]*min=\{5\}[\s\S]*max=\{10080\}/);
  assert.match(pageSource, /message\.success\("安全策略已保存"\)/);
  assert.match(pageSource, /message\.error\(error\?\.response\?\.data\?\.detail \|\| "安全策略保存失败"\)/);
});

test("security policy cancel-safe read path retains updated-by metadata", () => {
  assert.match(securityBlock, /securityPolicy\.updated_by/);
  assert.match(securityBlock, /securityPolicy\.updated_at/);
  assert.match(securityBlock, /onClick=\{saveSecurity\}/);
  assert.doesNotMatch(securityBlock, /onClick=\{\(\) => removeUser/);
});

test("system user and security APIs retain administrator guards", () => {
  const userApi = apiSource.slice(
    apiSource.indexOf('@app.get(f"{settings.api_prefix}/system/users")'),
    apiSource.indexOf('@app.get(f"{settings.api_prefix}/system/role-permissions")'),
  );
  const securityApi = apiSource.slice(
    apiSource.indexOf('@app.get(f"{settings.api_prefix}/system/security-policy")'),
    apiSource.indexOf('@app.get(f"{settings.api_prefix}/system/parameters")'),
  );
  assert.match(userApi, /_require_admin\(identity\)/);
  assert.match(securityApi, /_require_admin\(identity\)/);
  assert.match(userApi, /不能删除系统管理员账号/);
  assert.match(securityApi, /_security_policy_dict/);
});

test("standalone system user management route is hidden from the visible workspace", () => {
  const configuredMenuItems = appSource.slice(
    appSource.indexOf("function configuredMenuItems"),
    appSource.indexOf("function flattenMenu"),
  );
  assert.match(appSource, /"system-users": "hr-all"/);
  assert.match(configuredMenuItems, /item\.key !== "system-users"/);
});

test("organization and audit routes remain explicit integration boundaries", () => {
  assert.match(apiSource, /@app\.get\(f"\{settings\.api_prefix\}\/audit\/events"\)/);
  assert.match(apiSource, /仅管理员可以查看全所操作日志/);
  assert.match(pageSource, /initialView === "system-users"/);
});

test("system configuration remains a read-only projection instead of an unrelated assignment editor", () => {
  assert.match(pageSource, /initialView === "system-management-config"/);
  assert.match(pageSource, /dataSource=\{configs\}/);
  assert.match(pageSource, /render: \(value\) => JSON\.stringify\(value\)/);
  assert.doesNotMatch(pageSource, /loadInvestigationSupervisorOptions/);
  assert.doesNotMatch(pageSource, /onOpenChange=\{\(open\) => \{[\s\S]*loadInvestigationSupervisorOptions/);
  assert.match(apiSource, /"investigation_supervisor_options": supervisor_options/);
  assert.match(apiSource, /select\(User\)\.where\(User\.is_active\.is_\(True\)\)/);
});
