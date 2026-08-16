import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url));
const helper = fs.readFileSync(path.join(root, "src", "caseSecondBatchParity.ts"), "utf8");
const page = fs.readFileSync(path.join(root, "src", "CaseCenterPage.tsx"), "utf8");

test("phase payload keeps legacy comma-separated case numbers and ID/name mapping", () => {
  assert.match(helper, /buildCasePhaseChangePayload/);
  assert.match(helper, /case_phase_id/);
  assert.match(helper, /case_phase_name/);
  assert.match(helper, /case_nos: list\(caseNos\)\.join\(\",\"\)/);
});

test("case page opens a guarded phase editor and submits the dedicated endpoint", () => {
  assert.match(page, /phaseEditing/);
  assert.match(page, /phaseForm/);
  assert.match(page, /\/cases\/phases/);
  assert.match(page, /\/cases\/phase-change/);
  assert.match(page, /buildCasePhaseChangePayload/);
  assert.match(page, /修改案件阶段/);
  assert.match(page, /修改成功！/);
  assert.match(page, /修改失败！/);
});

test("phase editing preserves permission and archive/merge guards", () => {
  assert.match(page, /can_change_phase/);
  assert.match(page, /selectedCaseCapability\.can_change_phase/);
  assert.match(page, /getCaseCapability\(row\)\.can_change_phase/);
  assert.match(page, /待归档审核.*已归档.*已合并/);
  assert.match(page, /请先选择案件/);
  assert.match(page, /await load\(\)/);
});
