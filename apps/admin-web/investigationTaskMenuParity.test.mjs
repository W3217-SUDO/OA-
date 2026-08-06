import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

test("investigation hall exposes the published-task hierarchy", () => {
  for (const [key, label] of [
    ["investigation-task-published", "我发布的调查任务"],
    ["investigation-task-mine", "我的调查任务"],
    ["investigation-task-overdue", "过期调查任务"],
    ["investigation-task-unassigned", "待我分配的调查任务"],
    ["investigation-task-sub-published", "我发布的调查子任务"],
    ["investigation-task-sub-mine", "我的调查任务（子任务）"],
  ]) {
    assert.match(source, new RegExp(`key: "${key}"`));
    assert.match(source, new RegExp(`label: "${label}"`));
  }
  assert.match(source, /key: "investigation-task-published"[\s\S]*children:/);
});
