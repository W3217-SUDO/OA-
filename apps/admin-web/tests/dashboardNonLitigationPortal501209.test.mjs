// 501209（思法汇成 11-06）：新增非诉端和新格子，不开放个人自定义，只按角色统一配置。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");

test("工作台没有个人自定义入口", () => {
  assert.doesNotMatch(read("../src/Dashboard.tsx"), /自定义/);
  assert.doesNotMatch(read("../src/DashboardOverview.tsx"), /自定义/);
  assert.equal(fs.existsSync(new URL("../src/DashboardCustomize.tsx", import.meta.url)), false);
});

test("非诉期限预警有入口，有知识产权菜单就能进", () => {
  assert.match(read("../src/ipr/iprCaseTabs.ts"), /IPR_WARNINGS_ROUTE = "ipr-warnings"/);
  assert.match(read("../src/workspacePermissions.ts"), /route === "ipr-warnings"\) return hasFamily\("ipr"\)/);
  assert.match(read("../src/App.tsx"), /route === IPR_WARNINGS_ROUTE/);
  assert.match(read("../src/dashboardTodos.tsx"), /"ipr-warning": <AlertOutlined \/>/);
});
