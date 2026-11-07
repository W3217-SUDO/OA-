// 陶威 11-07：缓存管理、菜单管理、安全策略的修改按钮只给真实系统管理员显示（actual_role_ids），页面授权的人只能查看。
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import Module, { createRequire } from "node:module";
import { build } from "esbuild";
import React from "react";
import { act, create } from "react-test-renderer";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
if (!globalThis.window) globalThis.window = globalThis;
if (!globalThis.matchMedia) globalThis.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} });

async function load(entry) {
  const output = await build({
    entryPoints: [fileURLToPath(new URL(entry, import.meta.url))],
    bundle: true, write: false, platform: "node", format: "cjs", packages: "external", loader: { ".css": "empty" },
    plugins: [{ name: "stub-antd-1107", setup(builder) {
      builder.onResolve({ filter: /^antd$|^@ant-design\/icons$|ResizableTable$/ }, ({ path }) => ({ path, namespace: "stub" }));
      builder.onLoad({ filter: /.*/, namespace: "stub" }, ({ path }) => ({ resolveDir: fileURLToPath(new URL(".", import.meta.url)), contents: path.endsWith("ResizableTable") ? 'export { Table as default } from "antd";' : path !== "antd"
        ? 'export const ClearOutlined=()=>null,ReloadOutlined=()=>null,EditOutlined=()=>null,PlusOutlined=()=>null,DeleteOutlined=()=>null,SearchOutlined=()=>null;'
        : `import React from "react";
const C=n=>p=>React.createElement(n,{"data-disabled":p.disabled?"yes":undefined},p.children);
const Table=p=>React.createElement("table",null,
  p.title?p.title():null,
  p.rowSelection?React.createElement("select-col"):null,
  (p.columns||[]).map(c=>React.createElement("col",{key:c.key||c.dataIndex},c.title)),
  (p.dataSource||[]).map((row,i)=>React.createElement("tr",{key:i},(p.columns||[]).map(c=>React.createElement("td",{key:c.key||c.dataIndex},c.render?c.render(row[c.dataIndex],row,i):String(row[c.dataIndex]??""))))));
const Form=Object.assign(p=>React.createElement("form",{"data-disabled":p.disabled?"yes":undefined},p.children),{Item:C("form-item"),useForm:()=>[{setFieldsValue(){},validateFields:async()=>({})}]});
export {Table,Form}; export const Button=C("button"),Popconfirm=C("popconfirm"),Space=C("space"),Card=p=>React.createElement("card",null,p.extra,p.children),Alert=p=>React.createElement("alert",null,p.message,p.description,p.children),Input=Object.assign(C("input"),{Search:C("input")}),InputNumber=C("input"),Switch=C("switch"),Modal=C("modal"),Tree=C("tree"),Select=C("select"),Pagination=C("pagination"),Tag=C("tag"),Statistic=C("statistic"),Row=C("row"),Col=C("col"),Empty=C("empty"),Tooltip=C("tooltip"),Typography={Text:C("text"),Paragraph:C("p")},Descriptions=Object.assign(C("dl"),{Item:C("dd")});
export const message={success(){},error(){}};` }));
    } }],
  });
  const target = new Module(fileURLToPath(import.meta.url));
  target.paths = Module._nodeModulePaths(fileURLToPath(new URL(".", import.meta.url)));
  target.require = createRequire(import.meta.url);
  target._compile(output.outputFiles[0].text, fileURLToPath(import.meta.url));
  return target.exports;
}
const textOf = (node) => node == null ? "" : typeof node === "string" ? node : Array.isArray(node) ? node.map(textOf).join("") : textOf(node.children);
async function render(element) {
  let renderer;
  await act(async () => { renderer = create(element); });
  return renderer;
}
const noop = () => {};

test("缓存管理：非真实管理员直接提示只有系统管理员可用，不转圈、不显示清除按钮", async () => {
  const { SystemCacheManagement } = await load("../src/system/SystemCacheManagement.tsx");
  const props = { caches: [{ key: "k1", name: "参数缓存", clearable: true }], cacheSummary: null, cacheActionPending: false, cacheTotal: 1, cachePage: 1, cachePageSize: 15,
    cacheJumpPage: "", selectedCacheKeys: [], onSelectedCacheKeysChange: noop, onCacheJumpPageChange: noop, onLoadCaches: noop, onClearCache: noop,
    onClearSelectedCaches: noop, onClearAllCaches: noop, onJumpToCachePage: noop };
  const admin = textOf((await render(React.createElement(SystemCacheManagement, { ...props, actualAdmin: true }))).toJSON());
  for (const word of ["清除选中缓存", "清除全部缓存", "清空"]) assert.ok(admin.includes(word), word);
  const viewer = await render(React.createElement(SystemCacheManagement, { ...props, actualAdmin: false }));
  const text = textOf(viewer.toJSON());
  for (const word of ["清除选中缓存", "清除全部缓存", "清空", "正在读取"]) assert.ok(!text.includes(word), word);
  assert.ok(text.includes("缓存管理只有系统管理员可以使用"));
  assert.equal(viewer.root.findAll((node) => node.type === "table").length, 0);
  const page = fs.readFileSync(new URL("../src/system/SystemCenterPage.tsx", import.meta.url), "utf8");
  assert.match(page, /if \(initialView === "system-management-cache" && actualAdmin\) void loadCaches\(\);\n  \}, \[initialView, actualAdmin\]\);/, "非真实管理员不请求缓存列表");
});

test("菜单管理：非真实管理员看不到新增、修改、删除、保存显示配置，查询照常", async () => {
  const { SystemMenuManagement } = await load("../src/system/SystemMenuManagement.tsx");
  const menus = [{ id: 1, key: "case", parent_key: "", label: "案件", description: "", is_visible: true, is_active: true, sort_order: 1, route: "case", is_system: true },
                 { id: 2, key: "old-x", parent_key: "", label: "历史", description: "", is_visible: false, is_active: false, sort_order: 2, is_system: false }];
  const props = { menus, menuPage: 1, menuPageSize: 15, menuJumpPage: "", menuSearchInput: "", menuSearch: "", menuOpen: false, editingMenu: null, loading: false,
    menuForm: { setFieldsValue() {}, resetFields() {} }, onMenuSearchInputChange: noop, onMenuSearch: noop, onMenuPageChange: noop, onMenuJumpPageChange: noop,
    onJumpToMenuPage: noop, onEditMenu: noop, onSaveMenu: noop, onRemoveMenu: noop, onMenuOpenChange: noop, onNewMenu: noop, onResetMenuSearch: noop, onSaveVisibility: noop };
  const admin = textOf((await render(React.createElement(SystemMenuManagement, { ...props, actualAdmin: true }))).toJSON());
  for (const word of ["新增菜单", "修改", "删除", "保存显示配置"]) assert.ok(admin.includes(word), word);
  const viewer = await render(React.createElement(SystemMenuManagement, { ...props, actualAdmin: false }));
  const text = textOf(viewer.toJSON());
  for (const word of ["新增菜单", "修改", "删除", "保存显示配置"]) assert.ok(!text.includes(word), word);
  assert.ok(text.includes("查询"));
  assert.ok(viewer.root.findAll((node) => node.type === "tree").every((node) => node.props["data-disabled"] === "yes"), "显示配置只读");
});

test("安全策略：非真实管理员没有保存按钮，表单只读", async () => {
  const { SystemSecurityPolicy } = await load("../src/system/SystemSecurityPolicy.tsx");
  const props = { securityPolicy: { min_password_length: 8, updated_by: "admin", updated_at: "" }, loading: false, securityForm: { setFieldsValue() {} }, onSaveSecurity: noop };
  assert.ok(textOf((await render(React.createElement(SystemSecurityPolicy, { ...props, actualAdmin: true }))).toJSON()).includes("保存安全策略"));
  const viewer = await render(React.createElement(SystemSecurityPolicy, { ...props, actualAdmin: false }));
  assert.ok(!textOf(viewer.toJSON()).includes("保存安全策略"));
  assert.equal(viewer.root.findByType("form").props["data-disabled"], "yes");
});

test("系统中心按登录信息的真实角色传入，不按页面授权", () => {
  const app = fs.readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
  assert.match(app, /<SystemCenterPage initialView=\{route\} actualAdmin=\{permissionAdministrator\} \/>/);
  assert.match(app, /const permissionAdministrator = sessionUser\?\.actual_role_ids\?\.includes\("admin"\) === true;/);
  // role / role_ids 对页面授权的人也是 admin，不能兜底。
  assert.match(app, /actual_role_ids: Array\.isArray\(data\.actual_role_ids\) \? data\.actual_role_ids : \[\],/);
  assert.doesNotMatch(app, /actual_role_ids: data\.actual_role_ids \|\| data\.role_ids/);
  assert.doesNotMatch(app, /sessionUser\?\.actual_role \|\| sessionUser\?\.role/);
  const page = fs.readFileSync(new URL("../src/system/SystemCenterPage.tsx", import.meta.url), "utf8");
  assert.equal(page.match(/actualAdmin=\{actualAdmin\}/g)?.length, 3);
  // 系统配置列表里“系统配置”（维护模式、系统名称）只显示值，没有修改入口。
  const configList = fs.readFileSync(new URL("../src/system/SystemConfigList.tsx", import.meta.url), "utf8");
  assert.doesNotMatch(configList, /application_settings/);
  assert.match(configList, /if \(row\.key !== "conflict_auto_review"\) return JSON\.stringify\(value\);/);
});
