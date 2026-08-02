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
  const javascript = ts.transpileModule(source, { fileName: filename, compilerOptions: { esModuleInterop: true, jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const module = { exports: {} };
  vm.runInThisContext(`(function (require, module, exports, __filename, __dirname) { ${javascript}\n})`, { filename })(localRequire, module, module.exports, filename, path.dirname(filename));
  return module.exports;
}

function render(initialView, rows) {
  let stateCalls = 0;
  const react = { ...React, useState(initialValue) { stateCalls += 1; return React.useState(stateCalls === 2 ? rows : initialValue); } };
  const sourceDir = path.join(process.cwd(), "src");
  const mappingPath = path.join(sourceDir, "sealViewMapping.ts");
  const mapping = executeTsx(fs.readFileSync(mappingPath, "utf8"), mappingPath, nativeRequire);
  const pagePath = path.join(sourceDir, "SealCenterPage.tsx");
  const page = executeTsx(fs.readFileSync(pagePath, "utf8"), pagePath, (specifier) => ({
    react, "./sealViewMapping": mapping, "./api": { api: {} }, "./caseDetailNavigation": { rememberCaseDetailTarget() {} }, "./contractDetailNavigation": { rememberContractDetailTarget() {} }, "./customerDetailNavigation": { rememberCustomerDetailTarget() {} }, "./detailRelationResolver": { resolveDetailRelation() {} }, "./businessRecordDetailNavigation": { consumeBusinessRecordDetailTarget() {} }, "./formSafety": { formatRequiredDate() {} }, "./RecordImportButton": { __esModule: true, default: () => null }, "./seal-center.css": {},
  })[specifier] ?? nativeRequire(specifier));
  return renderToStaticMarkup(React.createElement(page.default, { initialView }));
}

function rows(status) {
  return Array.from({ length: 16 }, (_, index) => ({ id: index + 1, serial_no: `CODEX-G4-${index}`, title: "fixture", customer: "fixture", status, owner: "fixture", description: "", data: {}, created_at: "2026-08-02T00:00:00Z", updated_at: "2026-08-02T00:00:00Z" }));
}

test("administrative query alone retains the legacy 15-row pagination controls", () => {
  assert.match(render("seal-admin-query", rows("待审批")), /ant-pagination-options-size-changer/);
  assert.match(render("seal-admin-query", rows("待审批")), /ant-pagination-options-quick-jumper/);
  assert.doesNotMatch(render("seal-my-used", rows("已用印")), /ant-pagination-options-size-changer/);
});
