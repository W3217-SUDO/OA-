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
const parameterBlock = pageSource.slice(
  pageSource.indexOf("if (category) {"),
  pageSource.indexOf('} else if (initialView === "system-parameters-company")'),
);

test("legacy case-type/cause parameter list keeps the shared field matrix", () => {
  assert.match(pageSource, /"system-parameters-case-type": "case_type"/);
  assert.match(pageSource, /"system-parameters-cause": "cause"/);
  assert.match(parameterBlock, /const title = `\$\{categoryTitle\[category\]\}列表`/);
  assert.match(parameterBlock, /onPressEnter=\{\(\) => loadParameters\(\)\}/);
  assert.match(parameterBlock, /<Button type="primary" onClick=\{\(\) => loadParameters\(\)\}>/);
  assert.match(parameterBlock, /startParameter\(\)/);
  assert.match(parameterBlock, /defaultPageSize: 15/);
  assert.match(parameterBlock, /pageSizeOptions: \["10", "15", "20", "50", "100", "200"\]/);
  assert.match(parameterBlock, /showTotal: \(total\) => `共 \$\{total\} 条`/);
  assert.match(pageSource, /没有查询到符合条件的记录，可以去/);
});

test("legacy cause and case-type fields keep parent-code and validation behavior", () => {
  assert.match(pageSource, /cause: \[\{ key: "parent_code", label: "上级案由Id" \}\]/);
  assert.match(pageSource, /const numericParent = item\.key === "parent_code"/);
  assert.match(pageSource, /inputMode=\{numericParent \? "numeric" : undefined\}/);
  assert.match(pageSource, /numericParent \? cleanCompanyDigitsInputEvent : undefined/);
  assert.match(pageSource, /name="code"[\s\S]*required: true/);
  assert.match(pageSource, /name="name"[\s\S]*required: true/);
  assert.match(pageSource, /name="sort_order"[\s\S]*required: true/);
  assert.match(pageSource, /name="is_active" valuePropName="checked"/);
  assert.match(pageSource, /onCancel=\{\(\) => setParameterOpen\(false\)\}/);
});

test("legacy role permissions keeps tree fields, admin lock, and feedback", () => {
  assert.match(pageSource, /title="系统角色权限"/);
  assert.match(pageSource, /权限设定/);
  assert.match(pageSource, /title=\{`角色维护：/);
  assert.match(pageSource, /name="data_scope"/);
  assert.match(pageSource, /name="menu_keys"/);
  assert.match(pageSource, /treeCheckable/);
  assert.match(pageSource, /disabled=\{editingRole\?\.role === "admin"\}/);
  assert.match(pageSource, /message\.success\("保存成功！"\)/);
  assert.match(pageSource, /message\.error\(error\?\.response\?\.data\?\.detail \|\| "保存失败！"\)/);
});

test("parameter and role APIs keep admin guards and legacy failure paths", () => {
  const parameterApi = apiSource.slice(
    apiSource.indexOf('@app.get(f"{settings.api_prefix}/system/parameters")'),
    apiSource.indexOf('@app.get(f"{settings.api_prefix}/system/caches")'),
  );
  assert.match(parameterApi, /_require_admin\(identity\)/);
  assert.match(apiSource, /class SystemParameterInput/);
  assert.match(parameterApi, /参数分类无效/);
  assert.match(parameterApi, /同一分类下参数代码或名称已存在/);
  assert.match(parameterApi, /参数“\{item\.name\}”已被业务记录引用/);
  assert.match(apiSource, /@app\.get\(f"\{settings\.api_prefix\}\/system\/role-permissions"\)/);
  assert.match(apiSource, /@app\.patch\(f"\{settings\.api_prefix\}\/system\/role-permissions\/\{\{role\}\}"\)/);
  assert.match(apiSource, /数据范围无效/);
  assert.match(apiSource, /用户中心为基础权限，不能移除/);
});
