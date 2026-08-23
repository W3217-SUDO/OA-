import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("document generation is available only to writable, non-locked case details", () => {
  const actions = source.slice(source.indexOf("const caseDetailMoreActionButtons"), source.indexOf("const caseDetailPrimaryActionButtons"));
  assert.match(actions, /counselDetailCapabilities\.can_write && !detailEditLocked/);
  assert.match(actions, /generateCaseDocument\("authorization-letter"\)/);
  assert.match(actions, /generateCaseDocument\("identity-certificate"\)/);
  assert.match(source, /const detailEditLocked = Boolean\(viewingCounselCase && \[\.\.\.ARCHIVE_LOCKED_STATUSES, "已合并"\]\.includes\(viewingCounselCase\.status\)\);/);
  assert.match(source, /\/cases\/\$\{viewingCounselCase\.id\}\/documents\/\$\{documentType\}/);
});

test("document generation refreshes attachment detail and reports failures", () => {
  assert.match(source, /setAttachments\(\(current\) => \[data, \.\.\.current\.filter\(\(item\) => item\.id !== data\.id\)\]\)/);
  assert.match(source, /await openCounselDetail\(viewingCounselCase\)/);
  assert.match(source, /message\.error\(error\?\.response\?\.data\?\.detail \|\|/);
});
