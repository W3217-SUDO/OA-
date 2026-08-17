import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("all case detail routes use one legacy-compatible operation menu", () => {
  assert.match(source, /const caseDetailPrimaryActionButtons = viewingCounselCase/);
  assert.match(source, /dropdownRender=\{\(\) => caseDetailPrimaryActionButtons\}/);
  assert.doesNotMatch(source, /shouldUseCompanyScheduleDetailOperationMenu/);
  assert.doesNotMatch(source, /companyScheduleDetailActionButtons/);
});

test("primary and more actions keep their existing business handlers", () => {
  const actions = source.slice(
    source.indexOf("const caseDetailPrimaryActionButtons"),
    source.indexOf("const companyScheduleCourtLevelLabel"),
  );
  for (const handler of [
    "openLegacyBasicInfo",
    "openPhaseChange",
    "openLegacyNotaryInfo",
    "openCaseHearingLawyer",
    "openCaseLitigants",
    "openCompanyScheduleCourtInfo",
    "openLegacySettlementAmount",
    "openArchive",
    "caseDetailMoreActionButtons",
  ]) {
    assert.match(actions, new RegExp(handler));
  }
});
