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

test("保存时带上多选的调查员、案源人", () => {
  const payload = parity.normalizeCaseEditPayload({ customer_record_id: 1, handling_lawyers: ["shenjf"], investigators: ["sugq", "yuxd"], business_owners: ["wengjie"] }, "normal");
  assert.deepEqual(payload.investigators, ["sugq", "yuxd"]);
  assert.deepEqual(payload.business_owners, ["wengjie"]);
});

test("修改窗口：调查员、案源人多选，改线索带出线索调查员", () => {
  assert.match(page, /label="调查员" name="investigators"[^>]*><KeywordPersonSelect mode="multiple"/);
  assert.match(page, /label="案源人" name="business_owners"><KeywordPersonSelect mode="multiple"/);
  assert.match(page, /CaseClueSelect caseId=\{editingNormalCase\?\.id\} onPickRows=/);
});
