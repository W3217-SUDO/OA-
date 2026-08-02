import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("公司排期法院信息使用四审级独立入口且不复用案件阶段弹窗", () => {
  const levelsMatch = source.match(
    /export const getCompanyScheduleCourtLevels = \(\) => (\[[\s\S]*?\]) as const;/,
  );
  assert.ok(levelsMatch, "应声明公司排期专用的一审、二审、执行、再审入口");
  const getCompanyScheduleCourtLevels = new Function(`return (${levelsMatch[1]});`);
  assert.deepEqual(getCompanyScheduleCourtLevels(), [
    ["first", "一审"],
    ["second", "二审"],
    ["execution", "执行"],
    ["retrial", "再审"],
  ]);

  assert.match(
    source,
    /const \[companyScheduleCourtInfo, setCompanyScheduleCourtInfo\] = useState<\{ row: CaseRow; level: CompanyScheduleCourtLevel \} \| null>\(null\);/,
  );
  assert.match(source, /const \[companyScheduleCourtInfoForm\] = Form\.useForm\(\);/);
  assert.match(source, /const openCompanyScheduleCourtInfo = \(row: CaseRow, level: CompanyScheduleCourtLevel\) => \{/);

  const actions = source.slice(
    source.indexOf("const companyScheduleDetailActionButtons"),
    source.indexOf("return (", source.indexOf("const companyScheduleDetailActionButtons")),
  );
  assert.match(actions, /companyScheduleDetailOperationLabels\[5\]/);
  assert.match(actions, /openCompanyScheduleCourtInfo\(viewingCounselCase,key as CompanyScheduleCourtLevel\)/);
  assert.doesNotMatch(
    actions,
    /openProgress\(viewingCounselCase\)[^\n]*companyScheduleDetailOperationLabels\[5\]/,
  );
  assert.match(actions, /counselDetailCapabilities\.can_edit_basic/);
  assert.match(actions, /\["待归档审核","已归档","已合并"\]\.includes\(viewingCounselCase\.status\)/);
});

test("公司排期法院信息弹窗字段独立且取消不触发保存", () => {
  assert.match(source, /const submitCompanyScheduleCourtInfo = async \(\) => \{/);
  assert.match(source, /open=\{Boolean\(companyScheduleCourtInfo\)\}/);
  assert.match(source, /title=\{`修改法院信息 · \$\{companyScheduleCourtLevelLabel\}`\}/);
  for (const label of ["法院", "法庭", "法官", "书记员", "案号", "立案日期", "开庭日期", "判决日期"]) {
    assert.match(source, new RegExp(`Form\\.Item label="${label}"`));
  }

  const cancelMatch = source.match(
    /const cancelCompanyScheduleCourtInfo = \(\) => \{([\s\S]*?)\n  \};/,
  );
  assert.ok(cancelMatch, "应提供独立取消处理器");
  assert.match(cancelMatch[1], /setCompanyScheduleCourtInfo\(null\)/);
  assert.match(cancelMatch[1], /companyScheduleCourtInfoForm\.resetFields\(\)/);
  assert.doesNotMatch(cancelMatch[1], /api\.|submitCompanyScheduleCourtInfo|saveProgress|load\(/);
  assert.match(source, /onCancel=\{cancelCompanyScheduleCourtInfo\}/);
  assert.match(
    source,
    /okButtonProps=\{\{disabled:Boolean\(companyScheduleCourtInfo && !\["first", "second"\]\.includes\(companyScheduleCourtInfo\.level\)\)\}\}/,
  );
});

test("公司排期其余八项操作保持各自处理器", () => {
  const actions = source.slice(
    source.indexOf("const companyScheduleDetailActionButtons"),
    source.indexOf("return (", source.indexOf("const companyScheduleDetailActionButtons")),
  );
  for (const handler of [
    "openNormalCaseEdit",
    "openProgress",
    "setNotaryInfoCase",
    "openCaseHearingLawyer",
    "openCaseLitigants",
    "setSettlementAmountCase",
    "openArchive",
    "generateCaseDocument",
  ]) {
    assert.match(actions, new RegExp(handler));
  }
});
