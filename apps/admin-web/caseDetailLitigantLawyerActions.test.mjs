import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("case detail exposes independent litigant and hearing-lawyer actions", () => {
  assert.match(source, /修改当事人/);
  assert.match(source, /修改开庭律师/);
  assert.match(source, /openCaseLitigants\(viewingCounselCase\)/);
  assert.match(source, /openCaseHearingLawyer\(viewingCounselCase\)/);
  assert.match(source, /\/cases\/\$\{editingCaseLitigants\.id\}\/litigants/);
  assert.match(source, /\/cases\/\$\{editingCaseHearingLawyer\.id\}\/hearing-lawyer/);
});

test("litigant and lawyer actions guard archived cases and preserve cancel paths", () => {
  assert.match(source, /归档中的案件不能修改当事人/);
  assert.match(source, /归档中的案件不能修改开庭律师/);
  assert.match(source, /onCancel=\{\(\)=>setEditingCaseLitigants\(null\)\}/);
  assert.match(source, /onCancel=\{\(\)=>setEditingCaseHearingLawyer\(null\)\}/);
});
