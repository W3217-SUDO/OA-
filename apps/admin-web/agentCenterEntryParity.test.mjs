import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const appSource = readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");
const pageSource = readFileSync(new URL("./src/AgentCenterPage.tsx", import.meta.url), "utf8");
const styleSource = readFileSync(new URL("./src/agent-center.css", import.meta.url), "utf8");

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
