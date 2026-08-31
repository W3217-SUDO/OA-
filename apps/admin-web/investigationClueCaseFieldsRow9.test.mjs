import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./src/InvestigationCenterPage.tsx", import.meta.url), "utf8");

test("row 9 validates case fields before leaving the first conversion step", () => {
  const validation = source.indexOf('await batchForm.validateFields([');
  const advance = source.indexOf('setBatchStep(1);', validation);
  assert.ok(validation >= 0, "first-step validation is missing");
  assert.ok(advance > validation, "the modal advances before validation");
  for (const field of ["cause_or_charge", "handling_lawyer", "assistant"]) {
    assert.match(source.slice(validation, advance), new RegExp(`"${field}"`));
  }
  assert.match(source.slice(validation, advance), /setValidatedBatchCaseValues\(\{ \.\.\.batchForm\.getFieldsValue\(true\), \.\.\.values \}\)/);
});

test("row 9 requires both case-team people and submits stable usernames", () => {
  assert.match(source, /handling_lawyer: profile\.username \|\| ""/);
  assert.match(source, /label="经办律师"[\s\S]*?rules=\{\[\{ required: true,[\s\S]*?options=\{systemPersonOptions\}/);
  assert.match(source, /label="律师助理"[\s\S]*?rules=\{\[\{ required: true,[\s\S]*?options=\{systemPersonOptions\}/);
  assert.match(source, /\.\.\.validatedBatchCaseValues,[\s\S]*?clue_ids: selectedClues/);
});
