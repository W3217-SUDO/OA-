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
  assert.doesNotMatch(page.slice(page.indexOf("const openPhaseChange"), page.indexOf("const openExecutionStatus")), /getCaseCapability/);
  assert.match(page, /\[\.\.\.ARCHIVE_LOCKED_STATUSES, "已合并"\]\.includes\(row\.status\)/);
  assert.match(page, /api\.get\("\/cases\/phases"\)/);
  assert.match(page, /api\.post\("\/cases\/phase-change", buildCasePhaseChangePayload/);
  assert.match(page, /await load\(\)/);
});

test("phase picker remains separate from basic information", () => {
  const phaseModal = page.slice(page.indexOf("open={Boolean(phaseEditing)}"), page.indexOf("open={Boolean(progressEditing)}"));
  assert.match(page, /width=\{520\}/);
  assert.match(phaseModal, /open=\{Boolean\(phaseEditing\)\}/);
  assert.match(phaseModal, /<CasePhasePickerTree options=\{phaseOptions\} \/>/);
  assert.doesNotMatch(phaseModal, /<Radio\.Group/);
  assert.match(page, /case-phase-tree case-phase-change-tree/);
  assert.match(page, /buildLegacyCasePhaseTree\([\s\S]*?CASE_PHASE_ROOT_LABELS\.map/);
  assert.match(page, /\.filter\(\(child\) => child\.option\)/);
  assert.match(page, /\.filter\(\(node\) => node\.option \|\| node\.children\.length\)/);
  assert.match(page, /depth > 0 \? "case-phase-child" : "case-phase-filter"/);
  assert.match(page, /case-phase-selected/);
  assert.match(page, /aria-pressed=\{Number\(value\) === node\.option\?\.id\}/);
  assert.match(page, /aria-label=\{\(expanded \? "收起" : "展开"\) \+ node\.label\}/);
  assert.match(page, /!LEGACY_PHASE_GROUPS\.has\(node\.label\)/);
  assert.doesNotMatch(page, /"一审": "一审立案受理"/);
  assert.doesNotMatch(phaseModal, /name="case_phase"/);
});

test("ordinary-case batch phase menu opens the constrained phase picker", () => {
  assert.match(page, /if \(key === "batch-stage"\) void openPhaseChange\(selectedCases\);/);
  assert.match(page, /else if \(key\.startsWith\("batch-"\)\)/);
});
