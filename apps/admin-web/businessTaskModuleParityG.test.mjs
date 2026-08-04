import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./src/BusinessPage.tsx", import.meta.url), "utf8");

test("事项记录G: 任务模块明确引导专用事务中心并阻断通用写操作", () => {
  assert.match(source, /module === "task"/);
  assert.match(source, /事务中心/);
  assert.match(source, /我的任务/);
  assert.match(source, /专用入口/);
  assert.match(source, /Alert/);
  assert.match(source, /禁止使用通用记录接口新建或流转任务/);
});
