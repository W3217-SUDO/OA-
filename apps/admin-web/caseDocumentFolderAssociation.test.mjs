import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("case document parent folder includes every case-document category", () => {
  assert.match(source, /nonCaseDocumentCategories=\["客户文档","合同文档",\.\.\.counselDocCategoryGroups\.调查文档全部\]/);
  assert.match(source, /activeCounselDocCategory==="案件文档全部"\s*\?\s*!nonCaseDocumentCategories\.includes/);
});

test("investigation document parent folder includes every investigation category", () => {
  assert.match(source, /调查文档全部:\["调查文档","鉴别资料","取证文档"\]/);
});

test("folder selection matches imported categories exactly and keeps the visible label", () => {
  assert.match(source, /activeCounselDocCategories\.some\(category=>String\(row\.category\|\|""\)===category\)/);
  assert.match(source, /当前目录：\{activeCounselDocLabel\}/);
});

test("case detail loads the complete attachment set before folder filtering", () => {
  assert.match(source, /api\.get\("\/attachments", \{ params: \{ record_id: row\.id, page_size: 200 \} \}\)/);
});
