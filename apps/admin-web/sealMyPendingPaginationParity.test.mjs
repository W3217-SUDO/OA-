import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { createRequire } from "node:module";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";

const nativeRequire = createRequire(import.meta.url);

function executeTsx(source, filename, localRequire) {
  const javascript = ts.transpileModule(source, {
    fileName: filename,
    compilerOptions: { esModuleInterop: true, jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const module = { exports: {} };
  vm.runInThisContext(`(function (require, module, exports, __filename, __dirname) { ${javascript}\n})`, { filename })(localRequire, module, module.exports, filename, path.dirname(filename));
  return module.exports;
}

function renderPaginationProbe() {
  const sourceDir = path.join(process.cwd(), "src");
  const mappingPath = path.join(sourceDir, "sealViewMapping.ts");
  const mapping = executeTsx(fs.readFileSync(mappingPath, "utf8"), mappingPath, nativeRequire);
  const TableProbe = ({ pagination }) => React.createElement("output", { "data-page-size": pagination?.defaultPageSize ?? pagination?.pageSize, "data-page-options": (pagination?.pageSizeOptions ?? []).join(","), "data-size-changer": String(Boolean(pagination?.showSizeChanger)), "data-quick-jumper-go": String(pagination?.showQuickJumper?.goButton ?? "") });
  const pagePath = path.join(sourceDir, "SealCenterPage.tsx");
  const page = executeTsx(fs.readFileSync(pagePath, "utf8"), pagePath, (specifier) => ({
    antd: { ...nativeRequire("antd"), Table: TableProbe }, "./sealViewMapping": mapping, "./api": { api: {} }, "./caseDetailNavigation": { rememberCaseDetailTarget() {} }, "./contractDetailNavigation": { rememberContractDetailTarget() {} }, "./customerDetailNavigation": { rememberCustomerDetailTarget() {} }, "./detailRelationResolver": { resolveDetailRelation() {} }, "./businessRecordDetailNavigation": { consumeBusinessRecordDetailTarget() {} }, "./formSafety": { formatRequiredDate() {} }, "./RecordImportButton": { __esModule: true, default: () => null }, "./seal-center.css": {},
  })[specifier] ?? nativeRequire(specifier));
  return renderToStaticMarkup(React.createElement(page.default, { initialView: "seal-my-pending" }));
}

test("my pending seal route exposes the legacy pagination controls", () => {
  const html = renderPaginationProbe();
  assert.match(html, /data-page-size="15"/);
  assert.match(html, /data-page-options="10,15,20,50,100,200"/);
  assert.match(html, /data-size-changer="true"/);
  assert.match(html, /data-quick-jumper-go="GO"/);
});
