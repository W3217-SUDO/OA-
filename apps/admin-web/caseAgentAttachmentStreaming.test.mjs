import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

const page = await readFile(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const styles = await readFile(new URL("./src/case-center.css", import.meta.url), "utf8");

test("case agent lets the user select authorized case materials", () => {
  assert.match(page, /className="case-agent-material-tree"/);
  assert.match(page, /buildAgentDocumentTree\(agentDocuments\)/);
  assert.match(page, /AGENT_INVESTIGATION_DOCUMENT_FOLDERS\.includes\(category\)/);
  assert.match(page, /=== "调查资料" \? "调查文档"/);
  assert.match(page, /从案件文件夹选择本轮材料/);
  assert.match(page, /document_ids: outgoingDocumentIds/);
  assert.match(page, /api\.get\(`\/case-spaces\/\$\{row\.id\}\/context`\)/);
  const composerIndex = page.indexOf('className="case-agent-composer"');
  const materialsIndex = page.indexOf('className="case-agent-composer-materials"', composerIndex);
  assert.ok(composerIndex >= 0 && materialsIndex > composerIndex, "selected case materials should render inside the composer");
  assert.match(page, /document_ids: outgoingDocumentIds/);
  assert.match(page, /setAgentDocumentIds\(\[\]\)/);
  assert.match(page, /aria-label="收起材料选择"[\s\S]*setAgentMaterialPickerOpen\(false\)/);
});

test("case agent streams the response and keeps the latest message visible", () => {
  assert.match(page, /response\.body\.getReader\(\)/);
  assert.match(page, /event\.type === "delta"/);
  assert.match(page, /scrollIntoView\(\{ behavior: "auto", block: "end" \}\)/);
  assert.match(page, /messages\?\.slice\(-8\)/);
  assert.match(page, /查看更早记录/);
});

test("case agent drawer has a left-edge resize handle", () => {
  assert.match(page, /case-agent-resize-handle/);
  assert.match(styles, /cursor:ew-resize/);
});
