import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const app = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
const page = readFileSync(new URL("../src/investigation/InvestigationCenterPage.tsx", import.meta.url), "utf8");

test("501692/501694 公证信息导入下只留“公证书号仓库信息导入”，没有“取证信息文件导入”和“公证信息导入”子项", () => {
  assert.equal(app.match(/\{ key: "notary-import-storage", label: "公证书号仓库信息导入" \}/g)?.length, 2);
  assert.match(app, /"notary-import-storage": "公证书号仓库信息导入"/);
  assert.doesNotMatch(app, /label: "取证信息文件导入"|: "取证信息文件导入"/);
  assert.doesNotMatch(app, /key: "notary-import-info"/);
});

test("501694 旧地址进合并后的页面；“用 CSV 新建公证记录”保留在页面下面，接口不变", () => {
  const block = readFileSync(new URL("../src/investigation/NotaryCreateCsvImport.tsx", import.meta.url), "utf8");
  assert.match(page, /requestedTab === "notary-import-info" \? "notary-import-storage"/);
  assert.match(page, /<NotaryCreateCsvImport /);
  assert.match(block, /\/investigations\/notaries\/import"/);
  assert.match(block, /\/investigations\/notaries\/import-template/);
  assert.match(block, /accept="\.csv,text\/csv"/);
});

test("501692 公证书号仓库信息导入收 Excel 和 CSV", () => {
  assert.match(page, /initialTab === "notary-import-storage"\n\s*\? "\.xlsx,\.xls,\.csv/);
  assert.match(page, /支持 Excel（\.xlsx \/ \.xls）或 UTF-8 CSV/);
});
