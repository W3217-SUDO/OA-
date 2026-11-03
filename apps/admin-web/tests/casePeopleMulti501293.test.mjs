// 501293：案件基本信息人员多选；迁移的多人串（"sugq,sugq,sugq"）拆开回显，调查员按关联线索带出。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import ts from "typescript";

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");
const loadModule = (path) => {
  const compiled = ts.transpileModule(read(path), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true },
  }).outputText;
  const module = { exports: {} };
  new Function("exports", "require", "module", compiled)(module.exports, () => ({}), module);
  return module.exports;
};
const parity = loadModule("../src/caseSecondBatchParity.ts");
const page = read("../src/legal/CaseCenterPage.tsx");

test("拆开迁移的多人串并去重", () => {
  assert.deepEqual(parity.splitCasePeople("sugq,sugq,sugq"), ["sugq"]);
  assert.deepEqual(parity.splitCasePeople(["杨亮", "王长红、杨亮"], "范应根；虞向东"), ["杨亮", "王长红", "范应根", "虞向东"]);
});

test("账号都对得上系统人员时按账号回显，否则按姓名回显", () => {
  const options = new Set(["sugq", "shenjf"]);
  const resolve = (values) => values.map((value) => (value === "苏贵全" ? "sugq" : value));
  assert.deepEqual(parity.resolveStoredCasePeople(resolve, (v) => options.has(v), ["sugq"], ["苏贵全"]), ["sugq"]);
  assert.deepEqual(parity.resolveStoredCasePeople(resolve, (v) => options.has(v), ["sugq", "gone"], ["苏贵全", "离职员工"]), ["sugq", "离职员工"]);
});

test("迁移数据：线索号与“苏贵全,苏贵全,苏贵全”逐条对上，不去重", () => {
  assert.deepEqual(parity.storedClueInvestigators({ investigation_clue_nos: ["M1", "M2", "M3"], investigator: "苏贵全,苏贵全,苏贵全" }),
    [{ clue_no: "M1", name: "苏贵全" }, { clue_no: "M2", name: "苏贵全" }, { clue_no: "M3", name: "苏贵全" }]);
  const saved = [{ clue_no: "M1", username: "sugq", name: "苏贵全" }];
  assert.deepEqual(parity.storedClueInvestigators({ investigator_clues: saved }), saved);
});

test("线索调查员：有 investigator_usernames 用它，否则用线索负责人", () => {
  const name = (value) => ({ sugq: "苏贵全", yuxd: "虞向东" }[value] || value);
  assert.deepEqual(parity.clueInvestigatorRows({ id: 1, serial_no: "M1", owner: "sugq", data: {} }, name), [{ clue_id: 1, clue_no: "M1", username: "sugq", name: "苏贵全" }]);
  assert.deepEqual(parity.clueInvestigatorRows({ id: 2, serial_no: "M2", owner: "sugq", data: { investigator_usernames: ["yuxd"] } }, name).map((row) => row.name), ["虞向东"]);
});

test("另加调查员：不来自线索的行单独回显，线索列表不含它们", () => {
  const data = { investigator_clues: [{ clue_no: "M1", username: "sugq", name: "苏贵全" }, { clue_no: "", username: "wengjie", name: "翁洁", extra: true }] };
  assert.deepEqual(parity.storedClueInvestigators(data).map((row) => row.clue_no), ["M1"]);
  assert.deepEqual(parity.storedExtraInvestigators(data), ["wengjie"]);
  assert.deepEqual(parity.normalizeCaseEditPayload({ handling_lawyers: ["a"], extra_investigators: ["wengjie"] }, "normal").extra_investigators, ["wengjie"]);
});

test("提成审批：调查提成超 5% 标红并提示个案审核", () => {
  const drawer = read("../src/finance/FeeReviewDrawer.tsx");
  assert.match(drawer, /row\?\.over_limit/);
  assert.match(drawer, /金额超标，请进行个案审核/);
  assert.match(read("../src/finance/FinanceCenterPage.tsx"), /over_limit: Boolean\(fee\.data\?\.investigation_over_limit\)/);
});

test("修改窗口：调查员按线索只读显示，可另加调查员，案源人单选，开庭律师多选", () => {
  assert.match(page, /label="调查员（来自线索）" name="investigator_clues"[\s\S]*?<CaseClueInvestigatorList \/>/);
  assert.match(page, /label="另加调查员" name="extra_investigators"[^>]*><KeywordPersonSelect mode="multiple"/);
  assert.match(page, /label="案源人" name="business_owner"><KeywordPersonSelect allowClear/);
  assert.match(page, /label="开庭律师" name="hearing_lawyers"[^>]*>\s*<KeywordPersonSelect mode="multiple"/);
  assert.match(page, /CaseClueSelect caseId=\{editingNormalCase\?\.id\} onPickRows=/);
});
