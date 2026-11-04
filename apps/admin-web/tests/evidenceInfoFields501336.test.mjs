// 501336（fwl 11-04）：案件和调查大厅的“修改取证信息”都能选公证处并按模板填公证书号，证物存放处列出仓库库位。
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");

test("两处修改取证信息都用同一套字段", () => {
  assert.match(read("legal/CaseCenterPage.tsx"), /<EvidenceInfoFields form=\{caseClueEvidenceForm\} open=\{Boolean\(editingCaseClueEvidence\)\} \/>/);
  assert.match(read("investigation/EvidenceEditorModal.tsx"), /<EvidenceInfoFields form=\{evidenceEditForm\} open=\{open\} \/>/);
});

test("公证处按模板填、未补编号不能保存；证物存放处列仓库库位", () => {
  const fields = read("investigation/EvidenceInfoFields.tsx");
  assert.match(fields, /if \(!current \|\| current === autoFilled\.current\)/);
  assert.match(fields, /请把公证书号里的 xxxxx 换成实际编号/);
  assert.match(fields, /\$\{warehouse\.name\} \/ \$\{location\.name\}/);
  assert.match(fields, /\/investigations\/evidence-storage-options/);
  assert.match(fields, /<AutoComplete options=\{storageOptions\}/);
});
