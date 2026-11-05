import assert from "node:assert/strict";
import test from "node:test";
import { dropPartialParentMenus, menuTreeCheckState } from "../src/rolePermissionTreeState.ts";

// 客户管理 › 我的客户（带功能）、公海客户；用印中心 › 我的用印 › 待用印、已用印
const tree = [
  { key: "menu:customer", children: [
    { key: "menu:customer-mine", children: [{ key: "action:crm.customer.update" }] },
    { key: "menu:customer-public" },
  ] },
  { key: "menu:seal", children: [
    { key: "menu:seal-my", children: [{ key: "menu:seal-my-pending" }, { key: "menu:seal-my-used" }] },
  ] },
];

test("501310：下面页面勾着时大类显示勾上或半勾，不再显示为空", () => {
  const state = menuTreeCheckState(tree, ["menu:customer-mine", "menu:customer-public", "menu:seal-my-pending"]);
  assert.ok(state.checked.includes("menu:customer"), "下面全勾，大类显示勾上");
  assert.ok(state.halfChecked.includes("menu:seal") && state.halfChecked.includes("menu:seal-my"), "下面部分勾，大类半勾");
  assert.ok(!state.checked.includes("menu:seal"));
});

test("501310：勾了大类又取消下面页面，大类显示半勾，保存时不带大类", () => {
  const selected = ["menu:customer", "menu:customer-mine", "action:crm.customer.update"];
  const state = menuTreeCheckState(tree, selected);
  assert.ok(!state.checked.includes("menu:customer") && state.halfChecked.includes("menu:customer"));
  assert.deepEqual(dropPartialParentMenus(tree, selected), ["menu:customer-mine", "action:crm.customer.update"]);
});

test("501310：功能没勾不影响大类；下面页面全勾时大类照样保存", () => {
  const selected = ["menu:customer", "menu:customer-mine", "menu:customer-public"];
  assert.deepEqual(dropPartialParentMenus(tree, selected), selected);
  assert.ok(menuTreeCheckState(tree, selected).checked.includes("menu:customer"));
});

test("新菜单不随大类继承：没勾它，大类仍算全勾，保存时不去掉大类", () => {
  const ipr = [{ key: "menu:ipr", children: [{ key: "menu:ipr-patent-annual-fee" }, { key: "menu:ipr-my-cases", parent_grant_excluded: true }] }];
  const selected = ["menu:ipr", "menu:ipr-patent-annual-fee"];
  assert.ok(menuTreeCheckState(ipr, selected).checked.includes("menu:ipr"));
  assert.deepEqual(dropPartialParentMenus(ipr, selected), selected);
});
