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

const parameterForm = pageSource.slice(
  pageSource.indexOf('<Modal\n        open={parameterOpen}'),
  pageSource.indexOf('<Modal\n        open={menuOpen}'),
);
const parameterSave = pageSource.slice(
  pageSource.indexOf("const saveParameter = async"),
  pageSource.indexOf("const removeParameter = async"),
);
const parameterSaveCatch = parameterSave.slice(parameterSave.indexOf("} catch"));
const roleSave = pageSource.slice(
  pageSource.indexOf("const saveRole = async"),
  pageSource.indexOf("const saveSecurity = async"),
);
const auditApi = apiSource.slice(
  apiSource.indexOf('@app.get(f"{settings.api_prefix}/audit/events")'),
  apiSource.indexOf('@app.get(f"{settings.api_prefix}/audit/events")') + 700,
);

test("case type and cause write validation keeps legacy field-specific messages", () => {
  assert.match(parameterForm, /category === "case_type"/);
  assert.match(parameterForm, /请输入类型名称\./);
  assert.match(parameterForm, /请输入类型字母名称\./);
  assert.match(parameterForm, /category === "cause"/);
  assert.match(parameterForm, /请输入案由名称\./);
});

test("parameter writes keep legacy success and failure feedback", () => {
  assert.match(parameterSave, /message\.success\("保存成功！"\)/);
  assert.match(parameterSave, /message\.error\(error\?\.response\?\.data\?\.detail \|\| "保存失败！"\)/);
  assert.match(parameterSave, /validateFields\(\)/);
});

test("parameter duplicate and reference failures remain visible and preserve the form", () => {
  assert.match(parameterSave, /error\?\.response\?\.data\?\.detail/);
  assert.doesNotMatch(parameterSaveCatch, /setParameterOpen\(false\)/);
  assert.match(apiSource, /同一分类下参数代码或名称已存在/);
  assert.match(apiSource, /不能删除；请停用以保留历史数据/);
});

test("parameter deletion keeps an explicit confirmation boundary", () => {
  assert.match(pageSource, /Popconfirm title="确认删除/);
  assert.match(pageSource, /onConfirm=\{\(\) => removeParameter\(row\)\}/);
  assert.match(pageSource, /api\.delete\(`\/system\/parameters\/\$\{row\.id\}`\)/);
});

test("role permission writes keep legacy success and failure feedback", () => {
  assert.match(roleSave, /message\.success\("保存成功！"\)/);
  assert.match(roleSave, /message\.error\(error\?\.response\?\.data\?\.detail \|\| "保存失败！"\)/);
  assert.match(roleSave, /api\.patch\(`\/system\/role-permissions\/\$\{editingRole\.role\}`/);
});

test("role admin boundary is enforced before a permission save", () => {
  assert.match(roleSave, /editingRole\.role === "admin"/);
  assert.match(roleSave, /权限不可修改/);
  assert.match(pageSource, /okButtonProps=\{\{ disabled: editingRole\?\.role === "admin" \}\}/);
  assert.match(pageSource, /disabled=\{editingRole\?\.role === "admin"\}/);
});

test("role permission form keeps required scope, menu tree, and fields", () => {
  const roleForm = pageSource.slice(
    pageSource.indexOf('<Form\n            form={roleForm}'),
    pageSource.indexOf('</Form>\n        </Modal>', pageSource.indexOf('<Form\n            form={roleForm}')),
  );
  assert.match(roleForm, /name="data_scope"[\s\S]*required: true/);
  assert.match(roleForm, /name="menu_keys"[\s\S]*required: true/);
  assert.match(roleForm, /name="field_keys"[\s\S]*required: true/);
  assert.match(roleForm, /treeCheckable/);
});

test("system write APIs keep administrator guards and protected-role branches", () => {
  const parameterApi = apiSource.slice(
    apiSource.indexOf('@app.post(f"{settings.api_prefix}/system/parameters", status_code=status.HTTP_201_CREATED)'),
    apiSource.indexOf('@app.get(f"{settings.api_prefix}/system/configs")'),
  );
  const roleApi = apiSource.slice(
    apiSource.indexOf('@app.patch(f"{settings.api_prefix}/system/role-permissions/{{role}}")'),
    apiSource.indexOf('@app.get(f"{settings.api_prefix}/audit/events")'),
  );
  assert.ok((parameterApi.match(/_require_admin\(identity\)/g) || []).length >= 3);
  assert.match(roleApi, /_require_admin\(identity\)/);
  assert.match(roleApi, /系统管理员必须保留全部菜单权限/);
  assert.match(roleApi, /系统管理员必须保留全部字段权限/);
  assert.match(roleApi, /数据范围无效/);
});

test("role permission cancel closes without a write action", () => {
  assert.match(pageSource, /onCancel=\{\(\) => setRoleOpen\(false\)\}/);
  assert.match(pageSource, /cancelText="取消"/);
});

test("system audit endpoint remains administrator-only with paging and filters", () => {
  assert.match(auditApi, /module: str = ""/);
  assert.match(auditApi, /keyword: str = ""/);
  assert.match(auditApi, /page_size: int = Query\(50, ge=1, le=200\)/);
  assert.match(auditApi, /仅管理员可以查看全所操作日志/);
});

test("system parameter rows expose create/update audit metadata", () => {
  assert.match(pageSource, /const auditColumns = \[/);
  assert.match(pageSource, /dataIndex: "created_by"/);
  assert.match(pageSource, /dataIndex: "created_at"/);
  assert.match(pageSource, /dataIndex: "updated_by"/);
  assert.match(pageSource, /dataIndex: "updated_at"/);
});
