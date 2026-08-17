import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("legacy court submenu exposes the four original court levels", () => {
  const levelsMatch = source.match(
    /export const getCompanyScheduleCourtLevels = \(\) => (\[[\s\S]*?\]) as const;/,
  );
  assert.ok(levelsMatch, "court levels should be declared");
  const levels = new Function(`return (${levelsMatch[1]});`)();
  assert.deepEqual(levels, [
    ["first", "一审"],
    ["second", "二审"],
    ["execution", "执行"],
    ["retrial", "再审"],
  ]);

  const actions = source.slice(
    source.indexOf("const caseDetailPrimaryActionButtons"),
    source.indexOf("const companyScheduleCourtLevelLabel"),
  );
  assert.match(actions, /primaryOperationLabels\[5\]/);
  assert.match(actions, /openCompanyScheduleCourtInfo\(viewingCounselCase, key\)/);
  assert.match(actions, /data-testid="case-detail-court-submenu"/);
  assert.match(actions, /disabled=\{detailEditLocked\}/);
});

test("court information modal keeps its independent form and cancel behavior", () => {
  assert.match(source, /const \[companyScheduleCourtInfo, setCompanyScheduleCourtInfo\] = useState/);
  assert.match(source, /const \[companyScheduleCourtInfoForm\] = Form\.useForm\(\);/);
  assert.match(source, /const openCompanyScheduleCourtInfo = \(row: CaseRow, level: CompanyScheduleCourtLevel\) => \{/);
  assert.match(source, /const submitCompanyScheduleCourtInfo = async \(\) => \{/);
  assert.match(source, /open=\{Boolean\(companyScheduleCourtInfo\)\}/);
  assert.match(source, /onCancel=\{cancelCompanyScheduleCourtInfo\}/);
  for (const label of ["法院", "法庭", "法官", "书记员", "案号", "立案日期", "开庭日期", "判决日期"]) {
    assert.match(source, new RegExp(`Form\\.Item label="${label}"`));
  }
});

test("legacy case operation menu keeps the existing action handlers", () => {
  const actions = source.slice(
    source.indexOf("const caseDetailMoreActionButtons"),
    source.indexOf("const companyScheduleCourtLevelLabel"),
  );
  for (const handler of [
    "generateCaseDocument",
    "setMergingCase",
    "confirmLegacyDuplicateCase",
    "openLegacyBasicInfo",
    "openPhaseChange",
    "openLegacyNotaryInfo",
    "openCaseHearingLawyer",
    "openCaseLitigants",
    "openCompanyScheduleCourtInfo",
    "openLegacySettlementAmount",
    "openArchive",
  ]) {
    assert.match(actions, new RegExp(handler));
  }
});
