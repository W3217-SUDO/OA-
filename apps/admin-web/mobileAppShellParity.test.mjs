import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const appSource = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");
const styles = fs.readFileSync(new URL("./src/styles.css", import.meta.url), "utf8");
const dashboardStyles = fs.readFileSync(new URL("./src/dashboard.css", import.meta.url), "utf8");
const taskStyles = fs.readFileSync(new URL("./src/task-center.css", import.meta.url), "utf8");
const taskPageSource = fs.readFileSync(new URL("./src/TaskCenterPage.tsx", import.meta.url), "utf8");
const customerStyles = fs.readFileSync(new URL("./src/customer-center.css", import.meta.url), "utf8");
const contractStyles = fs.readFileSync(new URL("./src/contract-center.css", import.meta.url), "utf8");

test("mobile shell exposes app-style navigation and an overlay feature drawer", () => {
  assert.match(appSource, /mobile-bottom-nav/);
  assert.match(appSource, /移动端主导航/);
  assert.match(appSource, /mobile-sidebar-mask/);
  assert.match(appSource, /<span>首页<\/span>/);
  assert.match(appSource, /<span>功能<\/span>/);
  assert.match(appSource, /<span>待办<\/span>/);
  assert.match(appSource, /<span>消息<\/span>/);
  assert.match(appSource, /<span>我的<\/span>/);
  assert.match(styles, /position:\s*fixed !important;[\s\S]*top:\s*56px;[\s\S]*bottom:\s*64px;/);
});

test("mobile workspace removes desktop chrome and keeps touch targets usable", () => {
  assert.match(styles, /\.workspace-tabs\s*\{[\s\S]*display:\s*none;/);
  assert.match(styles, /\.page-head\s*\{[\s\S]*display:\s*none;/);
  assert.match(styles, /\.mobile-bottom-nav button[\s\S]*touch-action:\s*manipulation/);
  assert.match(styles, /width:\s*88px !important;[\s\S]*flex:\s*0 0 88px/);
  assert.match(styles, /\.ant-menu-submenu-popup\s*\{[\s\S]*display:\s*none !important/);
  assert.match(styles, /\.ant-input,[\s\S]*min-height:\s*40px/);
  assert.match(styles, /padding:\s*0 12px calc\(78px \+ env\(safe-area-inset-bottom\)\)/);
});

test("mobile dashboard uses compact two-column summary cards", () => {
  assert.match(dashboardStyles, /reference-metrics\{grid-template-columns:repeat\(2,minmax\(0,1fr\)\)/);
  assert.match(dashboardStyles, /reference-metrics \.metric\{height:96px/);
  assert.match(dashboardStyles, /\.todo-table\{display:none\}/);
  assert.match(dashboardStyles, /\.mobile-todo-list\{display:grid/);
  assert.match(appSource, /className="mobile-todo-list"/);
});

test("task center replaces its desktop grid and wide table on phones", () => {
  assert.match(taskStyles, /\.task-original-standard \.task-query\s*{[\s\S]*?grid-template-columns: minmax\(0, 1fr\)/);
  assert.match(taskStyles, /\.task-original-table\s*{\s*display: none;/);
  assert.match(taskStyles, /\.task-mobile-list\s*{\s*display: grid;/);
  assert.match(taskStyles, /\.task-original-standard \.task-query\.mobile-open\s*{\s*display: grid;/);
  assert.match(taskPageSource, /className="task-mobile-list"/);
  assert.match(taskPageSource, /className="task-mobile-card-body"/);
  assert.match(taskPageSource, /className="task-mobile-filter-toggle"/);
});

test("core customer and contract forms shed desktop fixed widths on phones", () => {
  assert.match(customerStyles, /\.customer-create-grid,[\s\S]*?grid-template-columns: minmax\(0, 1fr\)/);
  assert.match(customerStyles, /grid-template-columns: 96px minmax\(0, 1fr\)/);
  assert.match(contractStyles, /\.contract-query \{ grid-template-columns: minmax\(0, 1fr\)/);
  assert.match(contractStyles, /\.contract-page-form \.ant-form-item-row \{ display: block/);
  assert.match(contractStyles, /\.contract-query \.ant-form-item-control \{[\s\S]*?min-width: 0/);
  assert.match(contractStyles, /grid-template-columns: repeat\(4, minmax\(0, 1fr\)\)/);
  assert.match(styles, /\.finance-original-query-grid,[\s\S]*?grid-template-columns: minmax\(0, 1fr\) !important/);
});
