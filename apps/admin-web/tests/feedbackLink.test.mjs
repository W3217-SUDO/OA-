// 问题链接（2026-10-27）：?page=feedback&id=<反馈 ID> 直达问题详情，地址栏随详情同步。
import assert from "node:assert/strict";
import test from "node:test";

const replaced = [];
globalThis.window = {
  location: { origin: "https://huzhilawfirm.com", pathname: "/", search: "?page=feedback", hash: "" },
  history: { state: null, replaceState: (_state, _title, url) => { replaced.push(url); const q = url.indexOf("?"); window.location.search = q >= 0 ? url.slice(q) : ""; } },
};

const { feedbackLink, readFeedbackIdFromUrl, syncFeedbackIdToUrl } = await import("../src/feedback/navigation.ts");

test("生成和读取问题链接", () => {
  assert.equal(feedbackLink(279936), "https://huzhilawfirm.com/?page=feedback&id=279936");
  assert.equal(readFeedbackIdFromUrl("?page=feedback&id=279936"), 279936);
  assert.equal(readFeedbackIdFromUrl("?page=feedback-center&id=12"), 12);
  assert.equal(readFeedbackIdFromUrl("?page=case-mine&id=12"), null);
  assert.equal(readFeedbackIdFromUrl("?page=feedback&id=abc"), null);
  assert.equal(readFeedbackIdFromUrl("?page=feedback"), null);
});

test("打开和关闭详情时同步地址栏 id，其他页面不动", () => {
  syncFeedbackIdToUrl(279936);
  assert.equal(window.location.search, "?page=feedback&id=279936");
  syncFeedbackIdToUrl(null);
  assert.equal(window.location.search, "?page=feedback");
  window.location.search = "?page=case-mine";
  const before = replaced.length;
  syncFeedbackIdToUrl(5);
  assert.equal(replaced.length, before);
});
