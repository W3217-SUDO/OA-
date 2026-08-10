import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const appSource = readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");
const pageSource = readFileSync(new URL("./src/AgentCenterPage.tsx", import.meta.url), "utf8");
const styleSource = readFileSync(new URL("./src/agent-center.css", import.meta.url), "utf8");
const skillSource = readFileSync(new URL("./src/agentSkillRouting.ts", import.meta.url), "utf8");

test("global agent center is a first-level routed workspace", () => {
  assert.match(appSource, /lazyWithVersionRecovery\("agent-center"/);
  assert.match(appSource, /key:\s*"agent-center"[\s\S]*?label:\s*"智能体中心"/);
  assert.match(appSource, /route === "agent-center"[\s\S]*?<AgentCenterPage/);
  assert.match(appSource, /name === "robot"[\s\S]*?<RobotOutlined/);
});

test("chat composer stays inside the visible application workspace", () => {
  assert.match(styleSource, /\.agent-center-page\{[^}]*height:calc\(100dvh - 154px\)/);
  assert.match(styleSource, /\.agent-center-page\{[^}]*overflow:hidden/);
  assert.match(styleSource, /\.agent-global-composer\{[^}]*grid-template-columns/);
  assert.doesNotMatch(styleSource, /@media\(max-width:850px\)\{\.agent-center-page\{height:auto/);
});

test("agent center resumes authorized case spaces and all linked business areas", () => {
  assert.match(pageSource, /data-testid="agent-center-page"/);
  assert.match(pageSource, /module:\s*"case"/);
  assert.match(pageSource, /\/case-spaces\/\$\{record\.id\}\/agent\/status/);
  assert.match(pageSource, /\/case-spaces\/\$\{selected\.id\}\/agent\/messages/);
  assert.match(pageSource, /\/actions\/\$\{action\.id\}\/decision/);
  for (const label of ["客户", "合同", "案件", "线索", "调查", "财务"]) {
    assert.ok(pageSource.includes(`<Tag>${label}</Tag>`), `missing ${label} relation label`);
  }
});

test("agent center routes each conversation through the selected office skill", () => {
  assert.match(pageSource, /办公技能/);
  assert.match(pageSource, /status\?\.skills/);
  assert.match(pageSource, /encodeAgentSkillMessage\(skillId, content\)/);
  assert.match(pageSource, /disabled: !item\.available/);
  assert.match(skillSource, /\[\[skill:\$\{normalized\}\]\]/);
  assert.match(styleSource, /\.agent-skill-bar/);
});

test("screenshot evidence skill uploads case-scoped images and submits attachment ids", () => {
  assert.match(pageSource, /skillId === "screenshot-evidence"/);
  assert.match(pageSource, /form\.append\("record_id", String\(selected\.id\)\)/);
  assert.match(pageSource, /form\.append\("category", "智能体截图证据"\)/);
  assert.match(pageSource, /attachment_ids: screenshots\.map/);
  assert.match(pageSource, /accept="\.png,\.jpg,\.jpeg,\.webp/);
  assert.match(styleSource, /\.agent-screenshot-bar/);
  assert.match(pageSource, /preview_url: previewUrl/);
  assert.match(pageSource, /aria-label="待发送截图"/);
  assert.match(pageSource, /clipboardData\.items[\s\S]*?getAsFile\(\)/);
  assert.match(pageSource, /if \(skillId !== "screenshot-evidence"\) setSkillId\("screenshot-evidence"\)/);
  assert.match(pageSource, /onPaste=\{pasteScreenshot\}/);
  assert.match(pageSource, /可上传或直接粘贴截图/);
  assert.match(pageSource, /agent-message-attachments[\s\S]*?<img src=\{attachment\.preview_url\}/);
  assert.match(styleSource, /\.agent-composer-attachments/);
});
