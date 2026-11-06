// 11-06 陶威：打开就显示、自己操作后尽快更新、页面写明更新时间。
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");

test("写操作成功后广播，搜索和读取类 POST 不算", () => {
  const api = read("../src/api.ts");
  assert.match(api, /DATA_CHANGED_EVENT/);
  assert.match(api, /method !== 'get' && method !== 'head'/);
  assert.match(api, /\\\/search\$/);
});

test("工作台：允许先显示计算中，提交后带 refresh 重取，连续提交只刷新一次", () => {
  const hook = read("../src/dashboardData.ts");
  assert.match(hook, /allow_pending: true/);
  assert.match(hook, /refresh: true/);
  assert.match(hook, /addEventListener\(DATA_CHANGED_EVENT/);
  assert.match(hook, /window\.clearTimeout\(changedTimer\)/);
  assert.match(hook, /if \(result\.pending\) \{/);
});

test("页面写明更新时间，手动刷新走优先通道；样式不用旧内核不支持的写法", () => {
  const page = read("../src/Dashboard.tsx");
  assert.match(page, /更新于 \$\{minutes\} 分钟前/);
  assert.match(page, /const refreshAll = refreshDashboard/);
  assert.match(page, /正在计算，算好后自动显示/);
  const line = read("../src/dashboard.css").split("\n").find((item) => item.startsWith(".wb-hero-updated"));
  assert.ok(line);
  assert.doesNotMatch(line, /color-mix\(|:has\(|@container|dvh/);
});
