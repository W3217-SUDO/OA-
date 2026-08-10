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
    ["clue-company", "公司调查线索"],
    ["notary", "公证信息导入"],
    ["clue-my-draft", "待提交线索"],
    ["clue-my-pending", "待审核线索"],
    ["clue-my-customer", "待客户审核"],
    ["clue-my-collect", "待取证线索"],
    ["clue-my-collected", "已取证线索"],
    ["clue-my-refused", "已拒绝线索"],
    ["clue-my-no-fee", "未申请费用线索"],
    ["clue-my-fee", "已申请费用线索"],
    ["clue-audit-pending", "待审批线索"],
    ["clue-audit-customer", "待客户审核"],
    ["clue-audit-refused", "已拒绝线索"],
    ["clue-audit-collect", "待取证线索"],
    ["clue-audit-collected", "已取证线索"],
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

test("investigation task entries follow the legacy sibling hierarchy", () => {
  const publishedStart = source.indexOf('key: "investigation-task-published"');
  const clueStart = source.indexOf('key: "clue"', publishedStart);
  const taskSection = source.slice(publishedStart, clueStart);

  assert.ok(publishedStart >= 0, "the published investigation task group should exist");
  assert.doesNotMatch(source, /key: "investigation-tasks"/);
  const orderedKeys = [
    "investigation-task-published",
    "investigation-task-unassigned",
    "investigation-task-sub-published",
    "investigation-task-sub-mine",
  ];
  const positions = orderedKeys.map((key) => taskSection.indexOf(`key: "${key}"`));
  assert.ok(positions.every((position) => position >= 0));
  assert.deepEqual([...positions].sort((a, b) => a - b), positions);
  assert.match(taskSection, /label: "我发布的调查任务"/);
  assert.match(taskSection, /key: "investigation-task-mine"/);
  assert.match(taskSection, /key: "investigation-task-overdue"/);
});
