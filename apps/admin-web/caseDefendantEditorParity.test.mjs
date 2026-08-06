import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const source = await readFile(
  fileURLToPath(new URL("./src/CaseCenterPage.tsx", import.meta.url)),
  "utf8",
);

test("new case keeps defendants required and provides a separate right-side editor", () => {
  assert.match(source, /const \[createDefendantEditorOpen, setCreateDefendantEditorOpen\]/);
  assert.match(source, /const openCreateDefendantEditor = \(\) =>/);
  assert.match(source, /createForm\.setFieldValue\("defendants", values\.defendants\)/);
  assert.match(source, /<Button icon=\{<EditOutlined \/>} onClick=\{openCreateDefendantEditor\}>编辑被告<\/Button>/);
  assert.match(source, /label=\{litigantLabels\.defendant\} required=\{!isCounselCreate\}/);
  assert.match(source, /title="编辑被告"/);
  assert.match(source, /name="defendants" rules=\{\[\{ required: true, message: "请输入至少一名被告" \}\]\}/);
  assert.match(source, /请输入至少一名被告/);
});

test("defendant editor supports selecting customers and entering more than one defendant", () => {
  const editor = source.slice(source.indexOf('title="编辑被告"'));
  assert.match(editor, /mode="tags"/);
  assert.match(editor, /tokenSeparators=\{\[",", "，"\]\}/);
  assert.match(editor, /options=\{caseCustomers\.filter/);
});
