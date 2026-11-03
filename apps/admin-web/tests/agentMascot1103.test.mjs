// 智能体全身形象（陶威 11-03）：首页招手会眨眼、思考中用悬浮、空对话/空确认记录用抱平板；小头像不动。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");
const panel = read("../src/personal-agent/AssistantPanel.tsx");
const mascot = read("../src/personal-agent/AgentMascot.tsx");

test("全身形象接在首页、思考中和空状态，小头像不变", () => {
  assert.match(panel, /\{logoSrc && <AgentMascot pose="wave" height=\{128\} blink className="assistant-empty-mascot" \/>\}/);
  assert.match(panel, /<span className="assistant-thinking" role="status" title=\{progressText\}><AgentMascot pose="think" height=\{30\} bob \/>/);
  assert.match(panel, /\{logoSrc \? <img src=\{logoSrc\} alt="" width=\{32\} height=\{32\} \/> : <AgentAvatar size=\{32\} \/>\}/);
  assert.match(read("../src/personal-agent/ConversationManager.tsx"), /<Empty image=\{<AgentMascot pose="sleep" height=\{72\} \/>\} description="暂无对话" \/>/);
  assert.match(read("../src/personal-agent/ConversationManager.tsx"), /<AgentMascot pose="laptop" height=\{40\} bob \/><span>正在加载对话<\/span>/);
  assert.match(read("../src/personal-agent/CaseWorkspaceSelector.tsx"), /<AgentMascot pose="sorry" height=\{72\} \/>/);
  assert.match(read("../src/personal-agent/ConfirmationHistory.tsx"), /<Empty image=\{<AgentMascot pose="tablet" height=\{72\} \/>\}/);
  assert.match(mascot, /src=\{`\/assets\/agent\/agent-\$\{pose\}\.webp`\}/);
  for (const pose of ["wave", "float", "tablet", "thumbsup", "think", "celebrate", "laptop", "search", "guide", "sorry", "sleep", "deliver"]) {
    const size = fs.statSync(new URL(`../public/assets/agent/agent-${pose}.webp`, import.meta.url)).size;
    assert.ok(size < 100 * 1024, `${pose} ${size}`);
  }
});
