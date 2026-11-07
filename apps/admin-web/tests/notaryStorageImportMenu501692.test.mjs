// 501692/501694（范文玲 11-06）：公证信息导入下只留一个“公证书号仓库信息导入”，收 Excel/CSV；
// 原“取证信息文件导入”菜单去掉，原“公证信息导入”的“用 CSV 新建公证记录”放在同一页面下面。
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const app = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
const page = readFileSync(new URL("../src/investigation/InvestigationCenterPage.tsx", import.meta.url), "utf8");
const block = readFileSync(new URL("../src/investigation/NotaryCreateCsvImport.tsx", import.meta.url), "utf8");

test("菜单只留公证书号仓库信息导入，没有取证信息文件导入和公证信息导入子项", () => {
  assert.equal(app.match(/\{ key: "notary-import-storage", label: "公证书号仓库信息导入" \}/g)?.length, 2);
  assert.doesNotMatch(app, /取证信息文件导入/);
  assert.doesNotMatch(app, /key: "notary-import-info"/);
});

test("旧地址进合并后的页面，页面收 Excel 和 CSV", () => {
  assert.match(page, /requestedTab === "notary-import-info" \? "notary-import-storage"/);
  assert.match(page, /\.xlsx,\.xls,\.csv/);
  assert.match(page, /<NotaryCreateCsvImport /);
});

test("用 CSV 新建公证记录保留，接口不变", () => {
  assert.match(block, /\/investigations\/notaries\/import"/);
  assert.match(block, /\/investigations\/notaries\/import-template/);
  assert.match(block, /accept="\.csv,text\/csv"/);
});
