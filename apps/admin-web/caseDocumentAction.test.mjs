import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("document generation follows its dedicated capability on non-locked case details", () => {
  const actions = source.slice(source.indexOf("const caseDetailMoreActionButtons"), source.indexOf("const caseDetailPrimaryActionButtons"));
  assert.match(actions, /counselDetailCapabilities\.can_generate_document && !detailEditLocked/);
  assert.match(actions, /generateCaseDocument\("authorization-letter"\)/);
  assert.match(actions, /generateCaseDocument\("identity-certificate"\)/);
  assert.match(source, /const detailEditLocked = Boolean\(viewingCounselCase && \[\.\.\.ARCHIVE_LOCKED_STATUSES, "已合并"\]\.includes\(viewingCounselCase\.status\)\);/);
  assert.match(source, /\/cases\/\$\{viewingCounselCase\.id\}\/documents\/\$\{documentType\}/);
});

test("document generation refreshes attachment detail and reports failures", () => {
  assert.match(source, /setCounselDetailAttachments\(\(current\) => \[data, \.\.\.current\.filter\(\(item\) => item\.id !== data\.id\)\]\)/);
  assert.match(source, /await refreshCounselDetailAttachments\(viewingCounselCase\.id\)/);
  assert.match(source, /setActiveCounselDocCategory\(targetCategory\)/);
  assert.doesNotMatch(source.slice(source.indexOf("const generateCaseDocument"), source.indexOf("const openCounselAttachmentSeal")), /openCounselDetail/);
  assert.match(source, /const detail = error\?\.response\?\.data\?\.detail \|\|/);
  assert.match(source, /message\.error\(detail\)/);
  assert.match(source, /setCaseDocumentGenerationError\(detail\)/);
  assert.match(source, /caseDocumentGenerationError && <Alert[\s\S]*message=\{caseDocumentGenerationError\}/);
});

test("document generation prevents duplicate clicks and exposes progress", () => {
  assert.match(source, /if \(!viewingCounselCase \|\| generatingCaseDocumentType\) return/);
  assert.match(source, /setGeneratingCaseDocumentType\(documentType\)/);
  assert.match(source, /loading=\{Boolean\(generatingCaseDocumentType\)\}[\s\S]*aria-haspopup="menu"[\s\S]*>生成操作<\/Button>/);
  assert.match(source, /finally \{\s*setGeneratingCaseDocumentType\(""\)/);
});

test("document menu closes deliberately without leaking clicks into detail tabs", () => {
  assert.match(source, /<Dropdown[\s\S]*open=\{caseDocumentGenerationMenuOpen\}[\s\S]*onOpenChange=\{setCaseDocumentGenerationMenuOpen\}/);
  assert.match(source, /onClick: \(event\) => dispatchCaseDocumentGenerationMenuClick\(event, \(key\) => \{\s*setCaseDocumentGenerationMenuOpen\(false\);\s*void generateCaseDocument\(key\)/);
  assert.doesNotMatch(source, /case-document-generation-menu-panel/);
});
