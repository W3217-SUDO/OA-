// 501294（陶国南 11-03）：案件详情里的线索号一个一个可点；线索信息页签打开详情时就查本案线索。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");
const load = () => {
  const output = ts.transpileModule(read("../src/legal/CaseDetail/caseClueLinks.ts"), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const module = { exports: {} };
  vm.runInNewContext(output, { module, exports: module.exports });
  return module.exports;
};

test("多个线索号拆开，按顺序配上线索编号（HZMS2500713 的真实数据）", () => {
  const { caseClueLinks } = load();
  const links = caseClueLinks({
    clue_no: "M25113326", clue_record_id: 121474, investigation_clue: "M25113326、M25113325、M25062865",
    investigation_clue_ids: [121474, 121473, 121015], investigation_clue_nos: ["M25113326", "M25113325", "M25062865"],
  });
  assert.deepEqual(JSON.parse(JSON.stringify(links)), [
    { serial_no: "M25113326", id: 121474 }, { serial_no: "M25113325", id: 121473 }, { serial_no: "M25062865", id: 121015 }]);
});

test("只有线索号字符串、编号对不上时不乱配，点开时按线索号去查", () => {
  const { caseClueLinks } = load();
  assert.deepEqual(JSON.parse(JSON.stringify(caseClueLinks({ investigation_clue: "A1、B2", clue_record_id: 9 }))), [{ serial_no: "A1" }, { serial_no: "B2" }]);
  assert.deepEqual(JSON.parse(JSON.stringify(caseClueLinks({ clue_no: "A1", clue_record_id: 9 }))), [{ serial_no: "A1", id: 9 }]);
  assert.deepEqual(JSON.parse(JSON.stringify(caseClueLinks({}))), []);
});

test("打开详情时线索页签单独查本案线索；按线索号兜底查编号", () => {
  const actions = read("../src/legal/services/workflowActions.tsx");
  assert.match(actions, /void context\.loadCounselDetailCluesPage\(row, 1, 10, ""\)/);
  assert.match(actions, /api\.get\(`\/cases\/\$\{viewingCounselCase\.id\}\/clues`, \{ params: \{ keyword: serialNo/);
  assert.match(actions, /Array\.isArray\(data\?\.items\) \? data\.items : \[\]/, "/clues 返回的是 items");
  assert.match(read("../src/legal/CaseDetail/CaseDetailHeader.tsx"), /caseClueLinks\(viewingCase\.data\)\.map\(\(clue, index\) =>/);
});

test("线索页签认 /cases/{id}/clues 的返回（items/total/page/page_size/pages），不再当成空（501294 第二次）", () => {
  const page = read("../src/legal/CaseCenterPage.tsx");
  assert.match(page, /Array\.isArray\(payload\?\.clues\) \? payload\.clues : Array\.isArray\(payload\?\.items\) \? payload\.items : \[\]/);
  assert.match(page, /Number\(payload\?\.clue_total \?\? payload\?\.total \?\? items\.length\)/);
  assert.match(page, /payload\?\.clue_pages \?\? payload\?\.pages/);
});
