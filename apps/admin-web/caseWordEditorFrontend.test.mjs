import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("case document operations expose a guarded Word editor for original .docx attachments", () => {
  assert.match(source, /row\.record_id===viewingCounselCase\.id&&\/\\\.docx\?\$\/i/);
  assert.match(source, />在线编辑<\/Button>/);
  assert.match(source, /旧版 \.doc 文件暂不支持在线编辑/);
});

test("Word editor protects concurrent edits and preserves unsaved content after a failed save", () => {
  assert.match(source, /word-editor\/content/);
  assert.match(source, /word-editor\/lock\/renew/);
  assert.match(source, /word-editor\/lock/);
  assert.match(source, /lock_token: wordEditor\.lockToken/);
  assert.match(source, /version: wordEditor\.version/);
  assert.match(source, /blocks: blocksSnapshot/);
  assert.match(source, /const nextLockToken = String\(data\.lock_token \|\| wordEditor\.lockToken\)/);
  assert.match(source, /lockToken: nextLockToken/);
  assert.match(source, /if \(wordEditorSavingRef\.current\) return/);
  assert.match(source, /尚有未保存的 Word 修改/);
  assert.match(source, /当前编辑内容仍保留，可稍后重试/);
  assert.match(source, /editable: block\.editable !== false/);
  assert.match(source, /readOnlyReason: block\.read_only_reason/);
});
