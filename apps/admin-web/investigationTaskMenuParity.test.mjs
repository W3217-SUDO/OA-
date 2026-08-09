import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

test("investigation hall matches the legacy investigation directory hierarchy", () => {
  for (const [key, label] of [
    ["investigation-task-published", "我发布的调查任务"],
    ["investigation-task-mine", "我的调查任务"],
    ["investigation-task-overdue", "过期调查任务"],
    ["investigation-task-unassigned", "待我分配的调查任务"],
    ["investigation-task-sub-published", "我发布的调查子任务"],
    ["investigation-task-sub-mine", "我的调查任务"],
    ["clue", "我的调查线索"],
    ["clue-audit", "调查线索审核"],
    ["notary", "公证信息导入"],
  ]) {
    assert.match(source, new RegExp(`key: "${key}"`));
    assert.match(source, new RegExp(`label: "${label}"`));
  }
  const publishedStart = source.indexOf('key: "investigation-task-published"');
  const publishedEnd = source.indexOf('{ key: "investigation-task-unassigned"', publishedStart);
  const publishedBranch = source.slice(publishedStart, publishedEnd);
  assert.match(publishedBranch, /key: "investigation-task-mine"/);
  assert.match(publishedBranch, /key: "investigation-task-overdue"/);
  assert.doesNotMatch(publishedBranch, /key: "investigation-task-unassigned"/);
  assert.match(source, /route\.startsWith\("clue-"\)/);
  assert.match(source, /route\.startsWith\("notary-"\)/);
});
