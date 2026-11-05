// 501602（高勤兰 11-05）：从消息通知打开问题时，目标只留给重新打开的问题反馈页读取，
// 不通知已打开的旧页面（否则旧页面先取走目标，新页面只剩空白填写页）。
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

const { consumeFeedbackTarget, rememberFeedbackTarget } = await import("../src/feedback/navigation.ts");

test("从通知跳转：不发事件，目标留给新打开的页面", () => {
  rememberFeedbackTarget(501602, false);
  assert.deepEqual(events, []);
  assert.equal(consumeFeedbackTarget(), 501602);
  assert.equal(consumeFeedbackTarget(), null);
});

test("页面内打开（默认）：照常通知已打开的页面", () => {
  rememberFeedbackTarget(7);
  assert.deepEqual(events, ["sunhold:feedback-target"]);
  assert.equal(consumeFeedbackTarget(), 7);
});
