// 智能体全身形象（陶威 11-03）：首页招手会眨眼、思考中用悬浮、空对话/空确认记录用抱平板；小头像不动。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");
const panel = read("../src/personal-agent/AssistantPanel.tsx");
const mascot = read("../src/personal-agent/AgentMascot.tsx");

test("全身形象接在首页、思考中和空状态，小头像不变", () => {
  // 桌面端：招手机器人在左，问候语是它说的话（对话气泡）。
  assert.match(panel, /<div className="assistant-greeting-hero"><AgentMascot pose="wave" height=\{120\} blink className="assistant-greeting-mascot" \/><h1 className="assistant-greeting-bubble">\{title\}<\/h1><\/div>/);
  assert.match(panel, /desktopWorkspace \? <div className="assistant-workspace-greeting">\{greetingHero\("今天想处理什么？"\)\}/);
  assert.match(panel, /<span className="assistant-thinking" role="status" title=\{progressText\}><AgentMascot pose="think" height=\{30\} bob \/>/);
  assert.match(panel, /\{logoSrc \? <img src=\{logoSrc\} alt="" width=\{32\} height=\{32\} \/> : <AgentAvatar size=\{32\} \/>\}/);
  // 陶威 11-03：头像、菜单、案件智能体等所有地方统一换成新形象的头部。
  assert.match(read("../src/personal-agent/AgentAvatar.tsx"), /export const AGENT_HEAD_SRC = "\/assets\/agent\/agent-head\.webp";/);
  assert.match(read("../src/personal-agent/AiChatPage.tsx"), /logoSrc=\{AGENT_HEAD_SRC\}/);
  assert.match(read("../src/legal/CaseAgentDrawer.tsx"), /<AgentMascot pose="wave" height=\{110\} blink className="case-agent-empty-mascot" \/>/);
  assert.match(read("../src/legal/CaseAgentDock.tsx"), /<AgentIcon size=\{26\} \/>\{alert &&/);
  assert.match(read("../src/App.tsx"), /\{ key: "ai-chat", icon: <AgentIcon size=\{16\} \/>, label: "智能体中心" \}/);
  assert.match(read("../src/personal-agent/ConversationManager.tsx"), /<Empty image=\{<AgentMascot pose="sleep" height=\{72\} \/>\} description="暂无对话" \/>/);
  assert.match(read("../src/personal-agent/ConversationManager.tsx"), /<AgentMascot pose="laptop" height=\{40\} bob \/><span>正在加载对话<\/span>/);
  assert.match(read("../src/personal-agent/CaseWorkspaceSelector.tsx"), /<AgentMascot pose="sorry" height=\{72\} \/>/);
  assert.match(read("../src/personal-agent/ConfirmationHistory.tsx"), /<Empty image=\{<AgentMascot pose="tablet" height=\{72\} \/>\}/);
  assert.match(mascot, /src=\{`\/assets\/agent\/agent-\$\{pose\}\.webp`\}/);
  for (const pose of ["head", "wave", "float", "tablet", "thumbsup", "think", "celebrate", "laptop", "search", "guide", "sorry", "sleep", "deliver"]) {
    const size = fs.statSync(new URL(`../public/assets/agent/agent-${pose}.webp`, import.meta.url)).size;
    assert.ok(size < 100 * 1024, `${pose} ${size}`);
  }
});
