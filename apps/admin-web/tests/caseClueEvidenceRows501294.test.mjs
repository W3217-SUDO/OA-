// 501294：案件“线索信息”与旧系统一致按证物逐行显示，公证书、仓库等取证物。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import ts from "typescript";

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");
const source = read("../src/legal/CaseDetail/CaseCluesPanel.tsx");
const helper = source.slice(source.indexOf("type ClueEvidence ="), source.indexOf("export const CaseCluesPanel"));
const compiled = ts.transpileModule(helper, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
const module = { exports: {} };
new Function("exports", "module", compiled)(module.exports, module);

test("一个证物一行，没有证物的线索也有一行", () => {
  const rows = module.exports.clueEvidenceRows([
    { id: 1, serial_no: "M1", data: {}, evidences: [{ id: 11, certificate_no: "A" }, { id: 12, certificate_no: "B" }] },
    { id: 2, serial_no: "M2", data: {} },
  ]);
  assert.deepEqual(rows.map((row) => row.row_key), ["1-11", "1-12", "2"]);
  assert.equal(rows[1].evidence.certificate_no, "B");
});

test("公证书号、仓库等先取证物；店铺地址没有时显示店铺链接", () => {
  assert.match(source, /evidence\?\.certificate_no\|\|/);
  assert.match(source, /evidence\?\.warehouse_location\|\|/);
  assert.match(source, /clue\.data\.store_url\|\|clue\.data\.legacy_record\?\.StoreUrl/);
});
