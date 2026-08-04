import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const pageSource = fs.readFileSync(
  new URL("./src/SystemCenterPage.tsx", import.meta.url),
  "utf8",
);
const menuStart = pageSource.indexOf(
  '} else if (initialView === "system-management-menu")',
);
const menuEnd = pageSource.indexOf(
  '} else if (initialView === "system-management-config")',
  menuStart,
);
const menuBlock = pageSource.slice(menuStart, menuEnd);
const menuModalStart = pageSource.indexOf('open={menuOpen}');
const menuModalEnd = pageSource.indexOf('open={resettingUser}', menuModalStart);
const menuModalBlock = pageSource.slice(menuModalStart, menuModalEnd);
const apiSource = fs.readFileSync(
  new URL("../api-server/app/main.py", import.meta.url),
  "utf8",
);
const apiMenuBlock = apiSource.slice(
  apiSource.indexOf('@app.get(f"{settings.api_prefix}/system/menus")'),
  apiSource.indexOf('@app.get(f"{settings.api_prefix}/system/role-permissions")'),
);

test("legacy menu page keeps the list/action matrix and local extras", () => {
  assert.match(menuBlock, /title="菜单列表"/);
  assert.doesNotMatch(menuBlock, /新增菜单/);
  assert.match(menuBlock, /placeholder="菜单名称\/标识"/);
  assert.match(menuBlock, /setMenuSearch\(menuSearchInput\); setMenuPage\(1\)/);
  assert.match(menuBlock, /setMenuSearchInput\(""\); setMenuSearch\(""\); setMenuPage\(1\)/);
  assert.match(menuBlock, /title: "序号"/);
  assert.match(menuBlock, /dataIndex: "key"/);
  assert.match(menuBlock, /dataIndex: "parent_key"/);
  assert.match(menuBlock, /dataIndex: "label"/);
  assert.match(menuBlock, /dataIndex: "description"/);
  assert.match(menuBlock, /onClick=\{\(\) => editMenu\(row\)\}/);
  assert.match(menuBlock, /menuPageSize/);
  assert.match(menuBlock, /pageSizeOptions: \["10", "15", "20", "30", "50", "100", "200"\]/);
  assert.match(menuBlock, /showQuickJumper: true/);
  assert.match(menuBlock, /menuJumpPage/);
  assert.match(menuBlock, />GO<\/Button>/);
  assert.match(menuBlock, /showTotal: \(total\)/);
  assert.match(menuBlock, /没有查询到符合条件的菜单。/);
});

test("legacy menu modal keeps required fields and cancel semantics", () => {
  assert.match(menuModalBlock, /label="菜单名称"[\s\S]*name="label"[\s\S]*required: true/);
  assert.match(menuModalBlock, /label="菜单名称描述"[\s\S]*message: "请输入菜单名称描述\."/);
  assert.match(menuModalBlock, /okText="确定"/);
  assert.match(menuModalBlock, /cancelText="取消"/);
  assert.match(menuModalBlock, /onCancel=\{\(\) => setMenuOpen\(false\)\}/);
  assert.match(pageSource, /const saveMenu = async \(\) =>/);
  assert.match(pageSource, /message\.success\("保存成功\."\)/);
  assert.match(pageSource, /catch \(error: any\)[\s\S]*message\.error\(error\?\.response\?\.data\?\.detail \|\| "保存失败！"\)/);
});

test("menu API keeps login/admin guards, DTO constraints, and failure messages", () => {
  assert.match(apiMenuBlock, /@app\.get\(f"\{settings\.api_prefix\}\/system\/menus"\)/);
  assert.match(apiMenuBlock, /async def list_system_menus[\s\S]*_require_admin\(identity\)/);
  assert.match(apiMenuBlock, /@app\.post\(f"\{settings\.api_prefix\}\/system\/menus"/);
  assert.match(apiMenuBlock, /@app\.patch\(f"\{settings\.api_prefix\}\/system\/menus\/\{\{menu_id\}\}"\)/);
  assert.match(apiMenuBlock, /_require_admin\(identity\)/);
  assert.match(apiSource, /class SystemMenuInput\(BaseModel\)/);
  assert.match(apiSource, /label: str = Field\(min_length=1, max_length=128\)/);
  assert.match(apiSource, /description: str = Field\(default="", max_length=255\)/);
  assert.match(apiSource, /菜单标识不是已实现的系统路由，不能创建菜单入口/);
  assert.match(apiSource, /菜单标识已经存在/);
  assert.match(apiSource, /菜单不存在/);
});
