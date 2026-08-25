import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url));
const helper = fs.readFileSync(path.join(root, "src", "caseSecondBatchParity.ts"), "utf8");
const page = fs.readFileSync(path.join(root, "src", "CaseCenterPage.tsx"), "utf8");
const { buildCasePhasePickerTree } = await import("./src/caseOrdinarySearchParity.mjs");

test("phase payload keeps legacy comma-separated case numbers and ID/name mapping", () => {
  assert.match(helper, /buildCasePhaseChangePayload/);
  assert.match(helper, /case_phase_id/);
  assert.match(helper, /case_phase_name/);
  assert.match(helper, /case_nos: list\(caseNos\)\.join\(","\)/);
});

test("phase editing uses a guarded dedicated endpoint", () => {
  assert.match(page, /const openPhaseChange = async \(rows: CaseRow\[\]\) => \{/);
  assert.match(page, /\[\.\.\.ARCHIVE_LOCKED_STATUSES, "已合并"\]\.includes\(row\.status\)/);
  assert.match(page, /api\.get\("\/cases\/phases"\)/);
  assert.match(page, /api\.post\("\/cases\/phase-change", buildCasePhaseChangePayload/);
  assert.match(page, /await load\(\)/);
});

test("phase picker remains separate from basic information", () => {
  const phaseModal = page.slice(page.indexOf("open={Boolean(phaseEditing)}"), page.indexOf("open={Boolean(progressEditing)}"));
  assert.match(page, /width=\{520\}/);
  assert.match(phaseModal, /open=\{Boolean\(phaseEditing\)\}/);
  assert.match(phaseModal, /<Radio\.Group className="case-phase-change-options">/);
  assert.match(phaseModal, /case-phase-change-tree/);
  assert.match(phaseModal, /phaseChangeTree\.groups\.map/);
  assert.match(phaseModal, /case-phase-change-group-label/);
  assert.match(phaseModal, /expandedPhaseChangeGroups/);
  assert.doesNotMatch(phaseModal, /name="case_phase"/);
  assert.match(page, /key === "batch-stage"\) void openPhaseChange\(selectedCases\)/);
  assert.match(page, /else if \(key\.startsWith\("batch-"\)\)/);
});

test("phase picker uses the same legacy grouped tree contract as the case stage sidebar", () => {
  const searchParity = fs.readFileSync(path.join(root, "src", "caseOrdinarySearchParity.mjs"), "utf8");
  assert.match(searchParity, /export const buildCasePhasePickerTree/);
  assert.match(searchParity, /LEGACY_CASE_PHASE_GROUPS\.map/);
  assert.match(searchParity, /legacyCasePhaseGroupFor\(phaseName\)/);
  assert.match(page, /buildCasePhasePickerTree\(phaseOptions, phaseDefinitions\)/);
});

test("phase picker groups every trial, enforcement, and archive option", () => {
  const tree = buildCasePhasePickerTree([
    { id: 1, name: "新案待分配", canonical_name: "新案待分配", sort_order: 1 },
    { id: 7, name: "新案待分配", canonical_name: "新案待分配", sort_order: 7 },
    { id: 8, name: "新案待分配", canonical_name: "历史新案待分配", sort_order: 8 },
    { id: 2, name: "一审准备开庭", canonical_name: "一审准备开庭", sort_order: 2 },
    { id: 3, name: "二审庭后待判", canonical_name: "二审庭后待判", sort_order: 3 },
    { id: 4, name: "再审立案受理", canonical_name: "再审立案受理", sort_order: 4 },
    { id: 5, name: "执行中", canonical_name: "执行中", sort_order: 5 },
    { id: 6, name: "归档审核", canonical_name: "归档审核", sort_order: 6 },
  ]);
  assert.deepEqual(tree.ungrouped.map((option) => option.id), [1]);
  assert.deepEqual(tree.groups.map((group) => group.label), ["一审阶段", "二审阶段", "再审阶段", "执行阶段", "归档阶段"]);
  assert.deepEqual(tree.groups.map((group) => group.options[0].id), [2, 3, 4, 5, 6]);
});

test("phase picker keeps the same root phases as the outside stage tree", () => {
  const tree = buildCasePhasePickerTree([
    { id: 1, name: "新案待分配", canonical_name: "新案待分配", sort_order: 1 },
    { id: 2, name: "准备材料", canonical_name: "准备材料", sort_order: 2 },
    { id: 3, name: "一审准备开庭", canonical_name: "一审准备开庭", sort_order: 3 },
  ], [
    { label: "待分配", value: "新案待分配" },
    { label: "一审阶段", value: "一审阶段" },
  ]);
  assert.deepEqual(tree.ungrouped.map((option) => option.id), [1]);
  assert.deepEqual(tree.groups[0].options.map((option) => option.id), [3]);
});
