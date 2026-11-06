// 501294：案件“线索信息”的公证书、仓库等取证物。501675：同一条线索只显示一行，多个证物的值用“、”连起来，明细在右侧“取证信息”里。
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

test("一条线索一行：多个证物的值合并，相同的只写一次；没有证物的线索也有一行", () => {
  const rows = module.exports.clueEvidenceRows([
    { id: 1, serial_no: "P24111956", data: {}, evidences: [
      { id: 11, certificate_no: "645645", evidence_status: "未入库" },
      { id: 12, certificate_no: "47654", evidence_status: "未入库" },
      { id: 13, certificate_no: "435", evidence_status: "未入库", warehouse_name: "上海二仓" },
    ] },
    { id: 2, serial_no: "M2", data: {} },
  ]);
  assert.deepEqual(rows.map((row) => row.row_key), ["1", "2"]);
  assert.equal(rows[0].evidence.certificate_no, "645645、47654、435");
  assert.equal(rows[0].evidence.evidence_status, "未入库");
  assert.equal(rows[0].evidence.warehouse_name, "上海二仓");
  assert.equal(rows[0].evidence_count, 3);
  assert.equal(rows[1].evidence, undefined);
  assert.match(source, /共 \{evidence_count\} 个证物，点“查看”看明细/);
});

test("公证书号、仓库等先取证物；店铺地址没有时显示店铺链接", () => {
  assert.match(source, /evidence\?\.certificate_no\|\|/);
  assert.match(source, /evidence\?\.warehouse_location\|\|/);
  assert.match(source, /clue\.data\.store_url\|\|clue\.data\.legacy_record\?\.StoreUrl/);
});
