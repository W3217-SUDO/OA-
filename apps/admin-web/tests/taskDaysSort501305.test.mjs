// 501305：“我接受的任务”默认按剩余天数从少到多，逾期红、3 天内橙。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");
const page = read("../src/tp/TaskCenterPage.tsx");
const css = read("../src/task-center.css");
const constants = read("../src/tp/constants.ts");

test("我接受的任务默认按剩余天数升序，重置后也恢复", () => {
  assert.match(page, /initialView\.endsWith\("-accepted"\) \? \{ field: "days_remaining", order: "ascend" \}/);
  assert.match(page, /setTaskSort\(defaultTaskSort\);\s*void load\(\{\}, firstTab, 1, 15, defaultTaskSort\)/);
  assert.match(page, /setTaskSort\(defaultTaskSort\);\s*setSelectedKeys\(\[\]\);\s*void load\(\{\}, statusTab, 1, taskMeta\.pageSize, defaultTaskSort\)/);
});

test("剩余天数表头只在升降序间切换，逾期红、3 天内橙", () => {
  assert.match(page, /sortDirections: \["ascend", "descend", "ascend"\]/);
  assert.match(constants, /value < 0 \? "task-days-overdue" : value <= 3 \? "task-days-soon"/);
  assert.match(css, /\.task-days-overdue \{ color: #cf1322/);
  assert.match(css, /\.task-days-soon \{ color: #d46b08/);
});
