// 首页管理端（2026-10-27）：点“问题反馈 / 问题处理中心”进入问题处理中心时带上状态筛选，只用一次。
import assert from "node:assert/strict";
import test from "node:test";

const store = new Map();
globalThis.sessionStorage = {
  getItem: (key) => store.get(key) ?? null,
  setItem: (key, value) => store.set(key, String(value)),
  removeItem: (key) => store.delete(key),
};
const events = [];
globalThis.window = { dispatchEvent: (event) => events.push(event.type) };

const { consumeFeedbackStatusFilter, rememberFeedbackStatusFilter } = await import("../src/feedback/navigation.ts");

test("状态筛选只消费一次，并通知已打开的问题处理中心", () => {
  assert.equal(consumeFeedbackStatusFilter(), null);
  rememberFeedbackStatusFilter("待验证");
  assert.deepEqual(events, ["sunhold:feedback-status-filter"]);
  assert.equal(consumeFeedbackStatusFilter(), "待验证");
  assert.equal(consumeFeedbackStatusFilter(), null);
});
