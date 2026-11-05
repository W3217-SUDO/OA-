// 501298（陶国南 11-04 07:31）：确认执行或驳回后卡片收起，对话里只留一行结果；失败的留在卡片里。
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import ts from "typescript";

const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
const helper = ts.transpileModule(source("agentActionResult.ts"), { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
const { actionResultLine, mergeByTime } = await import(`data:text/javascript,${encodeURIComponent(helper)}`);

test("处理完的操作给一行结果，待确认、执行中、失败的不给", () => {
  assert.deepEqual(actionResultLine("approved", "案由改为侵害商标权纠纷"), { text: "已执行：案由改为侵害商标权纠纷", tone: "done" });
  assert.equal(actionResultLine("succeeded", "改阶段").text, "已执行：改阶段");
  assert.equal(actionResultLine("rejected", "改阶段").text, "已驳回：改阶段");
  for (const status of ["pending", "executing", "failed"]) assert.equal(actionResultLine(status, "x"), null);
});

test("结果行按处理时间插进对话", () => {
  const messages = [{ id: 1, at: "2026-11-04T07:00:00Z" }, { id: 2, at: "2026-11-04T07:10:00Z" }, { id: 3 }];
  const rows = mergeByTime(messages, [{ id: "a", at: "2026-11-04T07:05:00Z" }, { id: "b" }], (m) => m.at, (a) => a.at);
  assert.deepEqual(rows.map((row) => row.kind === "message" ? row.item.id : row.item.id), [1, "a", 2, 3, "b"]);
});

test("案件智能体浮窗只把待确认的放进卡片，失败写原因，处理完的在对话里一行", () => {
  const drawer = source("legal/CaseAgentDrawer.tsx");
  assert.match(drawer, /const waitingActions = \(agentState\?\.pending_actions \|\| \[\]\)\.filter\(\(action\) => action\.status === "pending" \|\| action\.status === "executing"\)/);
  // 调度 11-05：在智能体中心处理掉的卡片同步显示结果；执行失败显示成结果行。
  assert.match(drawer, /执行失败：/);
  assert.match(drawer, /在智能体中心处理/);
  // 501634：待确认的放进浮动确认窗口（CaseAgentConfirmFloat），对话里只留缩小后的入口。
  assert.match(drawer, /<CaseAgentConfirmFloat actions=\{\[\.\.\.waitingActions\]\.reverse\(\)\}/);
  assert.match(source("legal/CaseAgentConfirmFloat.tsx"), /未执行：\{failure\}/);
  assert.match(drawer, /className=\{`agent-action-result is-\$\{line\.tone\}`\}/);
  assert.match(source("legal/services/assistantActions.tsx"), /return reason;/);
});

test("智能体中心卡片不再放处理完的操作", () => {
  const panel = source("personal-agent/AssistantPanel.tsx");
  assert.match(panel, /const ordinaryActions = allOrdinaryActions\.filter\(\(item\) => !!workspace\.decisionFailures\[item\.id\] \|\| !actionResultLine/);
  assert.match(panel, /finishedActions\.map/);
  assert.doesNotMatch(source("agentPending.css").replace(/\/\*[\s\S]*?\*\//g, ""), /:has\(|color-mix/);
});
