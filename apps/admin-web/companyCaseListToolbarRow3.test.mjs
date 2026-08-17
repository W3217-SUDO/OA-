import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const css = fs.readFileSync(new URL("./src/case-center.css", import.meta.url), "utf8");

test("公司案件各普通类型复用完整列表工具栏", () => {
  assert.match(source, /export const isCompanyCaseListRoute/);
  assert.match(source, /initialView === "case-company" \|\| initialView\.startsWith\("case-company-"\)/);
  assert.match(source, /isMyCaseListRoute\(initialView\) \|\| isCompanyCaseListRoute\(initialView\)/);
  assert.match(source, /case-company-list-actions/);
  assert.match(source, /aria-label="导出案件"/);
  assert.match(source, /上传案件文档/);
  assert.match(source, /aria-label="更多案件操作"/);
  assert.match(css, /\.case-company-list-actions \{ flex:0 0 auto/);
});

test("删除案件只在公司案件范围内并保留能力校验和确认流程", () => {
  assert.match(source, /if \(!isCompanyCaseListRoute\(initialView\) \|\| !getCaseCapability\(row\)\.can_delete_case\)/);
  assert.match(source, /canDeleteSelectedCompanyCase/);
  assert.match(source, /aria-label="删除案件"/);
  assert.match(source, /disabled=\{!canDeleteSelectedCompanyCase\}/);
  assert.match(source, /selectedCase&&void deleteCompanyCase\(selectedCase\)/);
  assert.match(source, /title: "删除案件"/);
  assert.match(source, /api\.delete\(`\/cases\/\$\{row\.id\}`\)/);
});

console.log("company case list toolbar row 3 contract passed");
