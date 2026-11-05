import test from "node:test";
import assert from "node:assert/strict";
import { withPageLoadTimeout } from "../src/pageLoadTimeout.ts";

test("页面加载一直不返回时按超时失败，交给自动刷新处理", async () => {
  await assert.rejects(withPageLoadTimeout(new Promise(() => undefined), 20), /页面资源加载超时/);
});

test("正常加载完成的照常返回", async () => {
  assert.equal(await withPageLoadTimeout(Promise.resolve("ok"), 1000), "ok");
  await assert.rejects(withPageLoadTimeout(Promise.reject(new Error("chunk 404")), 1000), /chunk 404/);
});
