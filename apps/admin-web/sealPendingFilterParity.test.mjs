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

function renderSealCenterPage(initialView, rows = []) {
  let stateCallCount = 0;
  const pageReact = {
    ...React,
    useState(initialValue) {
      stateCallCount += 1;
      return React.useState(stateCallCount === 2 ? rows : initialValue);
    },
  };
  const sourceDir = path.join(process.cwd(), "src");
  const mappingPath = path.join(sourceDir, "sealViewMapping.ts");
  const mapping = executeTsx(
    fs.readFileSync(mappingPath, "utf8"),
    mappingPath,
    nativeRequire,
  );
  const policyPath = path.join(sourceDir, "sealWorkflowPolicy.ts");
  const policy = executeTsx(
    fs.readFileSync(policyPath, "utf8"),
    policyPath,
    nativeRequire,
  );
  const pagePath = path.join(sourceDir, "SealCenterPage.tsx");
  const localModules = {
    react: pageReact,
    "./sealViewMapping": mapping,
    "./sealWorkflowPolicy": policy,
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

function createSealRows(count, status) {
  return Array.from({ length: count }, (_, index) => ({
    id: index + 1,
    serial_no: `CODEX-SEAL-PAGINATION-${index + 1}`,
    title: "pagination fixture",
    customer: "pagination customer",
    status,
    owner: "pagination owner",
    description: "",
    data: { use_type: "合同用印", seal_names: "合同章", file_count: 1 },
    created_at: "2026-08-02T00:00:00Z",
    updated_at: "2026-08-02T00:00:00Z",
  }));
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

test("my used route shows the legacy locked status as 已用印", () => {
  const html = renderSealCenterPage("seal-my-used");
  const statusStart = html.indexOf("用印状态");

  assert.notEqual(statusStart, -1, "the rendered query form should contain 用印状态");
  assert.match(
    html.slice(statusStart, statusStart + 2500),
    /已用印/,
    "the disabled status filter should show the legacy 已用印 label",
  );
});

test("my withdrawn route keeps the legacy locked status unselected", () => {
  const html = renderSealCenterPage("seal-my-withdrawn");
  const statusStart = html.indexOf("用印状态");
  const statusEnd = html.indexOf("用印类型", statusStart);
  const statusMarkup = html.slice(statusStart, statusEnd);

  assert.notEqual(statusStart, -1, "the rendered query form should contain 用印状态");
  assert.notEqual(statusEnd, -1, "the rendered query form should contain 用印类型");
  assert.match(
    statusMarkup,
    /请选择/,
    "the disabled status filter should preserve the legacy placeholder",
  );
  assert.doesNotMatch(
    statusMarkup,
    /已撤回/,
    "the legacy withdrawn page should not show a selected status label",
  );
});

test("audit pagination shows the legacy page controls", () => {
  const html = renderSealCenterPage(
    "seal-audit-pending",
    createSealRows(16, "待审批"),
  );
  const paginationStart = html.indexOf("ant-pagination");
  const paginationMarkup = html.slice(paginationStart, paginationStart + 5000);

  assert.notEqual(
    paginationStart,
    -1,
    "the rendered table should contain pagination",
  );
  assert.match(
    paginationMarkup,
    /ant-pagination-options-size-changer[\s\S]*title="15 \/ page"/,
    "pagination should expose the legacy page size",
  );
  assert.match(
    paginationMarkup,
    /共 16 条记录/,
    "pagination should retain the record total",
  );
  assert.match(
    paginationMarkup,
    /ant-pagination-options-quick-jumper/,
    "pagination should expose the legacy quick-jump control",
  );
});

test("unverified seal routes retain the original 20-row pagination", () => {
  for (const [route, status] of [
    ["seal-my-used", "已用印"],
    ["seal-my-refused", "已拒绝"],
  ]) {
    const html = renderSealCenterPage(route, createSealRows(20, status));
    const paginationStart = html.indexOf("ant-pagination");
    const paginationMarkup = html.slice(paginationStart, paginationStart + 5000);

    assert.notEqual(paginationStart, -1, `${route} should render pagination`);
    assert.match(paginationMarkup, /共 20 条记录/, `${route} should retain its total`);
    assert.doesNotMatch(
      paginationMarkup,
      /ant-pagination-item-2/,
      `${route} should keep all 20 rows on its original first page`,
    );
    assert.doesNotMatch(
      paginationMarkup,
      /ant-pagination-options-size-changer/,
      `${route} should retain its original controls`,
    );
    assert.doesNotMatch(
      paginationMarkup,
      /ant-pagination-options-quick-jumper/,
      `${route} should retain its original controls`,
    );
  }
});
