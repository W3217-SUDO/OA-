// 501289（陶国南 11-03）：待确认卡片醒目；按钮淡色底块加文字，不靠红绿区分，兼容钉钉 Chrome 100。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");

test("待确认卡片有边框、左侧色条、浅色底和“待确认”标签", () => {
  const css = read("../src/agentPending.css");
  assert.match(css, /\.agent-pending-card \{[^}]*border-left: 5px solid #d46b08;[^}]*background: #fff7e6;/);
  const drawer = read("../src/legal/CaseAgentDrawer.tsx");
  assert.match(drawer, /<Tag className="agent-pending-tag">待确认<\/Tag>/);
  assert.match(read("../src/personal-agent/AssistantPanel.tsx"), /<Tag className="agent-pending-tag">待确认<\/Tag>/);
});

test("确认按钮淡色底块加文字和图标，主次靠底色深浅，不用红色 danger", () => {
  const drawer = read("../src/legal/CaseAgentDrawer.tsx");
  assert.match(drawer, /className="agent-btn-cancel" icon=\{<CloseOutlined \/>\}[^\n]*>驳回，不修改</);
  assert.match(drawer, /className="agent-btn-confirm" icon=\{<CheckOutlined \/>\}/);
  assert.doesNotMatch(drawer, /key="reject" danger/);
  const confirmation = read("../src/personal-agent/ActionConfirmation.tsx");
  assert.match(confirmation, /className="agent-btn-cancel"[^\n]*>取消操作</);
  assert.match(confirmation, /className="agent-btn-confirm"/);
  const css = read("../src/agentPending.css").replace(/\/\*[\s\S]*?\*\//g, "");
  assert.doesNotMatch(css, /color-mix\(|:has\(|@container|dvh/);
  assert.match(css, /:root\[data-theme="dark"\] \.ant-btn\.agent-btn-confirm/);
});
