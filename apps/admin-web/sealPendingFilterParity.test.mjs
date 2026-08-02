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
    compilerOptions: {
      esModuleInterop: true,
      jsx: ts.JsxEmit.ReactJSX,
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText;
  const module = { exports: {} };
  const wrapper = vm.runInThisContext(
    `(function (require, module, exports, __filename, __dirname) { ${javascript}\n})`,
    { filename },
  );
  wrapper(localRequire, module, module.exports, filename, path.dirname(filename));
  return module.exports;
}

function renderSealCenterPage(initialView) {
  const sourceDir = path.join(process.cwd(), "src");
  const mappingPath = path.join(sourceDir, "sealViewMapping.ts");
  const mapping = executeTsx(
    fs.readFileSync(mappingPath, "utf8"),
    mappingPath,
    nativeRequire,
  );
  const pagePath = path.join(sourceDir, "SealCenterPage.tsx");
  const localModules = {
    "./sealViewMapping": mapping,
    "./api": { api: {} },
    "./caseDetailNavigation": { rememberCaseDetailTarget() {} },
    "./contractDetailNavigation": { rememberContractDetailTarget() {} },
    "./customerDetailNavigation": { rememberCustomerDetailTarget() {} },
    "./detailRelationResolver": { resolveDetailRelation() {} },
    "./businessRecordDetailNavigation": { consumeBusinessRecordDetailTarget() {} },
    "./formSafety": { formatRequiredDate() {} },
    "./RecordImportButton": { __esModule: true, default: () => null },
    "./seal-center.css": {},
  };
  const page = executeTsx(
    fs.readFileSync(pagePath, "utf8"),
    pagePath,
    (specifier) => localModules[specifier] ?? nativeRequire(specifier),
  );
  const html = renderToStaticMarkup(
    React.createElement(page.default, { initialView }),
  );
  return html;
}

test("my pending route shows the legacy locked status as 待审核", () => {
  const html = renderSealCenterPage("seal-my-pending");
  const statusStart = html.indexOf("用印状态");

  assert.notEqual(statusStart, -1, "the rendered query form should contain 用印状态");
  assert.match(
    html.slice(statusStart, statusStart + 2500),
    /待审核/,
    "the disabled status filter should show the legacy 待审核 label",
  );
});

test("my stamping empty state ends with the legacy full stop", () => {
  const html = renderSealCenterPage("seal-my-stamping");

  assert.match(
    html,
    /没有查询到符合条件的记录。/,
    "the empty state should preserve the legacy sentence punctuation",
  );
});
