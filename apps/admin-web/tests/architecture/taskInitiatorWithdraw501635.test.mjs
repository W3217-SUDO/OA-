import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const read = (name) => fs.readFileSync(new URL(`../../src/tp/${name}.tsx`, import.meta.url), "utf8");

test("501635: own tasks hide 申请取消任务 and offer direct withdraw everywhere", () => {
  const page = read("TaskCenterPage");
  assert.match(page, /row && row\.initiator !== profile\.username && \(profile\.role === "admin"/, "申请取消任务 not for own tasks");
  const withdraw = page.slice(page.indexOf("const canWithdrawTask"), page.indexOf("const canReviewTaskException"));
  assert.doesNotMatch(withdraw, /isInitiatedTaskContext &&/, "withdraw not limited to 我发起的 tab");
  assert.match(withdraw, /row\.initiator === profile\.username/);
  assert.match(read("TaskList"), /canWithdrawTask\(selected\) && \(\s*roleActionAllowed\("task\.withdraw"\)/);
  assert.match(read("TaskDetail"), /props\.canWithdrawTask\(communication\)[\s\S]{0,200}props\.onWithdraw\(communication\)/);
});
