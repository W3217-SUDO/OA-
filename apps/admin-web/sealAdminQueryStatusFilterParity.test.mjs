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

function render(initialView) {
  const sourceDir = path.join(process.cwd(), "src");
  const mappingPath = path.join(sourceDir, "sealViewMapping.ts");
  const mapping = executeTsx(fs.readFileSync(mappingPath, "utf8"), mappingPath, nativeRequire);
  const policyPath = path.join(sourceDir, "sealWorkflowPolicy.ts");
  const policy = executeTsx(fs.readFileSync(policyPath, "utf8"), policyPath, nativeRequire);
  const pagePath = path.join(sourceDir, "SealCenterPage.tsx");
  const page = executeTsx(fs.readFileSync(pagePath, "utf8"), pagePath, (specifier) => ({
    "./sealViewMapping": mapping, "./sealWorkflowPolicy": policy, "./api": { api: {} }, "./caseDetailNavigation": { rememberCaseDetailTarget() {} }, "./contractDetailNavigation": { rememberContractDetailTarget() {} }, "./customerDetailNavigation": { rememberCustomerDetailTarget() {} }, "./detailRelationResolver": { resolveDetailRelation() {} }, "./businessRecordDetailNavigation": { consumeBusinessRecordDetailTarget() {} }, "./formSafety": { formatRequiredDate() {} }, "./RecordImportButton": { __esModule: true, default: () => null }, "./seal-center.css": {},
  })[specifier] ?? nativeRequire(specifier));
  return renderToStaticMarkup(React.createElement(page.default, { initialView }));
}

function statusMarkup(initialView) {
  const html = render(initialView);
  const start = html.indexOf('title="用印状态"');
  const end = html.indexOf('title="用印类型"', start);
  return html.slice(start, end);
}

test("administrative query alone unlocks its status filter", () => {
  assert.doesNotMatch(statusMarkup("seal-admin-query"), /disabled=""/);
  assert.match(statusMarkup("seal-admin-pending"), /disabled=""/);
  assert.match(statusMarkup("seal-admin-pending"), /已审待用印/);
});
