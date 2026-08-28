import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const app = fs.readFileSync(new URL("./App.tsx", import.meta.url), "utf8");
const tasks = fs.readFileSync(new URL("./TaskCenterPage.tsx", import.meta.url), "utf8");
const contracts = fs.readFileSync(new URL("./contractWorkflowPolicy.mjs", import.meta.url), "utf8");

test("dashboard todo numbers navigate to distinct pending and rejected queues", () => {
  assert.match(app, /待处理任务: \{ primary: "task-my-accepted", secondary: "task-my-created" \}/);
  assert.match(app, /待审批线索: \{ primary: "clue-audit-pending", secondary: "clue-audit-refused" \}/);
  assert.match(app, /待审批合同: \{ primary: "contract-audit-pending", secondary: "contract-audit-refused" \}/);
  assert.match(app, /待审批用印: \{ primary: "seal-audit-pending", secondary: "seal-my-refused" \}/);
  assert.match(app, /待审核归档: \{ primary: "case-archive-pending", secondary: "case-archive-refused" \}/);
  assert.match(app, /kind === "secondary" \? "rejected" : "pending"/);
  assert.match(tasks, /sessionStorage\.getItem\("sunhold:dashboard-task-tab"\)/);
});

test("clue dashboard queues use server-side pending and rejected filters", () => {
  const investigations = fs.readFileSync(
    new URL("./InvestigationCenterPage.tsx", import.meta.url),
    "utf8",
  );
  assert.match(investigations, /"clue-audit-pending": \["待审批"\]/);
  assert.match(investigations, /"clue-audit-refused": \["已驳回", "已拒绝"\]/);
  assert.match(investigations, /statuses: \(clueStatusesByRoute\[initialTab\] \|\| \[\]\)\.join\(","\)/);
});

test("rejected contract queue keeps the legacy current-owner scope", () => {
  assert.match(
    contracts,
    /key: "contract-audit-refused", label: "已驳回合同", scope: "mine"/,
  );
});
