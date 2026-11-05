// 陶国南 11-05 09:14：录费用有两份及以上合同时，确认卡片上列出合同让用户选，选了才能批准；五个批准入口都带上选择。
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");

test("卡片显示选择项，没选不能批准", () => {
  const preview = source("AgentOperationPreview.tsx");
  assert.match(preview, /<AgentChoice action=\{action\} \/>/);
  assert.match(preview, /请先在卡片上选择/);
  assert.match(preview, /export const agentChoiceBody/);
});

test("案件窗口、智能体中心、确认请求页、个人智能体批准时都带上选择", () => {
  for (const path of ["legal/services/assistantActions.tsx", "AgentCenterPage.tsx", "AgentToolRequests.tsx", "personal-agent/usePersonalWorkspace.ts"]) {
    const text = source(path);
    assert.match(text, /agentChoiceMissing\(/, path);
    assert.match(text, /agentChoiceBody\(/, path);
  }
});
