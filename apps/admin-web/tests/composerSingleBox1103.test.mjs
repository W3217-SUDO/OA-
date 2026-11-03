// 陶威 11-03：输入区只要一个框；文字框不带自己的边框，工具和发送排一排；兼容钉钉 Chrome 100。
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");

test("智能体中心和案件智能体浮窗都引入单框样式", () => {
  assert.match(read("personal-agent/AssistantPanel.tsx"), /import "\.\.\/composerSingleBox\.css"/);
  assert.match(read("legal/CaseAgentDrawer.tsx"), /import "\.\.\/composerSingleBox\.css"/);
});

test("内层文字框去掉边框，外框焦点变主题色，发送和工具同一行", () => {
  const css = read("composerSingleBox.css").replace(/\/\*[\s\S]*?\*\//g, "");
  assert.match(css, /\.assistant-composer \.assistant-composer-input,\s*\.assistant-composer \.assistant-composer-input:focus-within \{\s*border: 0;/);
  assert.match(css, /\.assistant-composer \.assistant-composer-input \{ display: contents; \}/);
  assert.match(css, /\.assistant-composer-actions \{ order: 3; flex: none; margin-left: auto; \}/);
  assert.match(css, /\.case-agent-panel \.case-agent-composer:focus-within \{\s*border-color: var\(--oa-primary\);/);
  assert.match(css, /\.case-agent-panel \.case-agent-composer textarea:focus \{[^}]*border: 0;/);
  assert.doesNotMatch(css, /:has\(|color-mix|@container|dvh/);
});
