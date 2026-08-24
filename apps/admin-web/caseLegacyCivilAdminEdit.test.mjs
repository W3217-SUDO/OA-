import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("legacy civil case names share the full basic-information editor", () => {
  assert.match(source, /isCivilCaseType = \(caseType: unknown\) => \["民事案件", "民事争议", "民事"\]/);
  assert.match(source, /isNormalEditableCase = \(row: CaseRow\) => isNormalCaseBasicType\(row\.data\.case_type\)/);
  assert.match(source, /isCivilCaseType\(viewingCounselCase\.data\.case_type\)[\s\S]*?openLegacyNotaryInfo/);
  assert.match(source, /isNormalCaseBasicType\(viewingCounselCase\.data\.case_type\)[\s\S]*?openLegacySettlementAmount/);
  assert.match(source, /isCivilCaseType\(editingNormalCase\?\.data\.case_type\)[\s\S]*?label="案源人"/);
});

test("a visible basic-information action is not denied by a second client-side permission check", () => {
  assert.doesNotMatch(source, /if \(!getCaseCapability\(row\)\.can_edit_basic\) return message\.warning/);
  assert.match(source, /counselDetailCapabilities\.can_edit_basic && <Button[\s\S]*?onClick=\{openLegacyBasicInfo\}/);
});

test("phase-change dialog trusts the server-filtered phase catalog", () => {
  const phaseChangeSource = source.slice(source.indexOf("const openPhaseChange"), source.indexOf("const openExecutionStatus"));
  assert.match(phaseChangeSource, /api\.get\("\/cases\/phases"/);
  assert.doesNotMatch(phaseChangeSource, /phaseOptionsForCaseType/);
  assert.doesNotMatch(phaseChangeSource, /getCaseCapability/);
});
