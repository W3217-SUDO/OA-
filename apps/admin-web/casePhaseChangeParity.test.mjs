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
  assert.match(helper, /case_nos: list\(caseNos\)\.join\(","\)/);
});

test("phase editing uses a guarded dedicated endpoint", () => {
  assert.match(page, /const openPhaseChange = async \(rows: CaseRow\[\]\) => \{/);
  assert.match(page, /getCaseCapability\(row\)\.can_change_phase/);
  assert.match(page, /\[\.\.\.ARCHIVE_LOCKED_STATUSES, "已合并"\]\.includes\(row\.status\)/);
  assert.match(page, /api\.get\("\/cases\/phases"\)/);
  assert.match(page, /api\.post\("\/cases\/phase-change", buildCasePhaseChangePayload/);
  assert.match(page, /await load\(\)/);
});

test("phase picker remains separate from basic information", () => {
  const phaseModal = page.slice(page.indexOf("open={Boolean(phaseEditing)}"), page.indexOf("open={Boolean(progressEditing)}"));
  assert.match(page, /width=\{400\}/);
  assert.match(phaseModal, /open=\{Boolean\(phaseEditing\)\}/);
  assert.match(phaseModal, /<Radio\.Group className="case-phase-change-options">/);
  assert.match(phaseModal, /\{renderCasePhaseTree\(phaseOptions\)\}/);
  assert.doesNotMatch(phaseModal, /name="case_phase"/);
});
