import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("case detail exposes document generation only for writable, non-archived cases", () => {
  assert.match(source, /生成案件文书/);
  assert.match(source, /<Dropdown trigger=\{\["click"\]\} menu=\{\{ items: caseDocumentTypes/);
  assert.match(source, /counselDetailCapabilities\.can_write/);
  assert.match(source, /\["待归档审核","已归档","已合并"\]\.includes\(viewingCounselCase\.status\)/);
  assert.match(source, /\/cases\/\$\{viewingCounselCase\.id\}\/documents\/\$\{documentType\}/);
});

test("document generation refreshes attachment detail and reports failures", () => {
  assert.match(source, /setAttachments\(\(current\) => \[data, \.\.\.current\.filter\(\(item\) => item\.id !== data\.id\)\]\)/);
  assert.match(source, /await openCounselDetail\(viewingCounselCase\)/);
  assert.match(source, /案件文书生成失败/);
});
