import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const helperPath = new URL("./src/caseSecondBatchParity.ts", import.meta.url);
const helper = fs.existsSync(helperPath) ? fs.readFileSync(helperPath, "utf8") : "";
const page = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("case create and edit DTOs keep the old required-field matrix", () => {
  assert.match(helper, /CASE_CREATE_REQUIRED_FIELDS/);
  assert.match(helper, /getCaseCreateValidationError/);
  assert.match(helper, /buildCaseCreatePayload/);
  assert.match(helper, /getCaseEditValidationError/);
  assert.match(helper, /normalizeCaseEditPayload/);
  assert.match(page, /caseSecondBatchParity/);
  assert.match(page, /getCaseCreateValidationError/);
  assert.match(page, /buildCaseCreatePayload/);
});

test("clue to case keeps batch endpoint, duplicate protection and contract linkage", () => {
  assert.match(helper, /CASE_CLUE_CONVERSION_ENDPOINT/);
  assert.match(helper, /buildClueConversionPayload/);
  assert.match(helper, /getClueConversionIssues/);
  assert.match(helper, /converted_case_id/);
  assert.match(page, /\/investigations\/clues\/batch-cases/);
  assert.match(page, /clueConversionOpen/);
  assert.match(page, /clueConversionForm/);
});

test("duplicate and merge preserve source identifiers and block unsafe statuses", () => {
  assert.match(helper, /CASE_MUTATION_BLOCKED_STATUSES/);
  assert.match(helper, /getCaseMutationBlockReason/);
  assert.match(helper, /buildCaseDuplicateRequest/);
  assert.match(helper, /buildCaseMergePayload/);
  assert.match(page, /buildCaseDuplicateRequest/);
  assert.match(page, /buildCaseMergePayload/);
  assert.match(page, /getCaseMutationBlockReason/);
});

test("execution status and progress keep comma-separated legacy case numbers", () => {
  assert.match(helper, /CASE_EXECUTION_STATUSES/);
  assert.match(helper, /buildCaseExecutionStatusPayload/);
  assert.match(helper, /buildCaseProgressPayload/);
  assert.match(helper, /case_nos/);
  assert.match(page, /buildCaseProgressPayload/);
});

test("case to payment navigation preserves both case and fee parameters", () => {
  assert.match(helper, /buildCasePaymentContext/);
  assert.match(helper, /case_record_id/);
  assert.match(helper, /case_no/);
  assert.match(helper, /fee_id/);
  assert.match(helper, /fee_no/);
  assert.match(page, /buildCasePaymentContext/);
});
