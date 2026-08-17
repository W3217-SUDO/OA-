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
  assert.match(page, /getCaseCapability\(row\)\.can_change_phase/);
  assert.match(page, /待归档审核.*已归档.*已合并/);
  assert.match(page, /请先选择案件/);
  assert.match(page, /await load\(\)/);
});

test("case detail keeps phase change separate from basic information, matching the legacy compact picker", () => {
  assert.match(page, /width=\{400\}/);
  assert.match(page, /title=\{`变更阶段：/);
  assert.match(page, /<Radio\.Group className="case-phase-change-options">/);
  assert.match(page, /<Radio key=\{option\.id\} value=\{option\.id\}>\{option\.name\}<\/Radio>/);
  assert.match(page, /<Form\.Item name="case_phase" hidden><Input \/><\/Form\.Item>/);
  assert.doesNotMatch(page, /阶段变更支持单行或批量案件/);
  assert.doesNotMatch(page, /<Form\.Item label="案件阶段" name="case_phase"/);
});
