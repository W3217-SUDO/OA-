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

test("agent center routes skills internally without a standalone office skill module", () => {
  assert.doesNotMatch(pageSource, /办公技能/);
  assert.doesNotMatch(pageSource, /agent-skill-bar/);
  assert.match(pageSource, /status\?\.skills/);
  assert.match(pageSource, /encodeAgentSkillMessage\(skillId, content\)/);
  assert.match(skillSource, /\[\[skill:\$\{normalized\}\]\]/);
  assert.doesNotMatch(styleSource, /\.agent-skill-bar/);
});

test("manual-driven workflow uses a compact top phase strip without a standalone workbench", () => {
  assert.doesNotMatch(pageSource, /data-testid="case-standard-workflow"/);
  assert.doesNotMatch(pageSource, /案件标准化工作台/);
  assert.doesNotMatch(styleSource, /\.agent-standard-workflow/);
  assert.match(pageSource, /data-testid="case-phase-strip"/);
  assert.match(pageSource, /\/case-spaces\/\$\{record\.id\}\/workflow-guide/);
  assert.match(pageSource, /className="agent-workspace-status"[\s\S]*?data-testid="case-phase-strip"[\s\S]*?<Space wrap>/);
  assert.match(styleSource, /\.agent-workspace-status\{[^}]*grid-template-columns:minmax\(190px,250px\) minmax\(420px,1fr\) auto/);
  assert.match(styleSource, /\.agent-phase-strip\{[^}]*height:38px/);
  assert.match(styleSource, /\.agent-phase-strip\{[^}]*overflow:hidden/);
  assert.match(styleSource, /\.agent-phase-strip-item\{[^}]*flex:1 1 0/);
  assert.doesNotMatch(styleSource, /\.agent-phase-strip\{[^}]*overflow-x:auto/);
  assert.match(pageSource, /PHASE_SHORT_NAMES/);
  for (const label of ["文书", "盖章", "待立案", "补取证", "提立案", "一审", "二审", "再审", "执行", "归档"]) {
    assert.ok(pageSource.includes(`"${label}"`), `missing compact phase label ${label}`);
  }
});

test("screenshot evidence skill uploads case-scoped images and submits attachment ids", () => {
  assert.match(pageSource, /skillId === "screenshot-evidence"/);
  assert.match(pageSource, /form\.append\("record_id", String\(selected\.id\)\)/);
  assert.match(pageSource, /form\.append\("category", "智能体截图证据"\)/);
  assert.match(pageSource, /attachment_ids: outgoingScreenshots\.map/);
  assert.doesNotMatch(pageSource, />上传截图<\/Button>/);
  assert.doesNotMatch(styleSource, /\.agent-screenshot-bar/);
  assert.match(pageSource, /className="agent-composer-upload"/);
  assert.match(pageSource, /PaperClipOutlined/);
  assert.match(pageSource, /preview_url: previewUrl/);
  assert.match(pageSource, /aria-label="待发送截图"/);
  assert.match(pageSource, /clipboardData\.items[\s\S]*?getAsFile\(\)/);
  assert.match(pageSource, /if \(skillId !== "screenshot-evidence"\) setSkillId\("screenshot-evidence"\)/);
  assert.match(pageSource, /onPaste=\{pasteScreenshot\}/);
  assert.match(pageSource, /可直接粘贴截图/);
  assert.match(pageSource, /<Image src=\{attachment\.preview_url\}[\s\S]*?preview/);
  assert.match(styleSource, /\.agent-composer-attachments/);
  assert.match(pageSource, /new AbortController\(\)/);
  assert.match(pageSource, /signal: controller\.signal/);
  assert.match(pageSource, /stopAgentResponse/);
  assert.match(pageSource, /发送引导并打断当前生成/);
  assert.match(pageSource, /messages: \[\.\.\.\(current\.messages \|\| \[\]\), \{ id: optimisticId/);
});
