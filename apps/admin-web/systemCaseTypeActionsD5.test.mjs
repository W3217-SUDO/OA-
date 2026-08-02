import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
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

function renderCaseTypeActions() {
  const realAntd = nativeRequire("antd");
  const icons = Object.fromEntries(
    ["clear", "delete", "edit", "plus"].map((name) => [
      `${name[0].toUpperCase()}${name.slice(1)}Outlined`,
      () => React.createElement("i", { "data-icon": name }),
    ]),
  );
  const row = {
    id: 110,
    category: "case_type",
    code: "110",
    name: "民事争议",
    extra: { letter_code: "MS" },
    sort_order: 1,
    is_active: true,
    created_by: "system",
    updated_by: "system",
    created_at: "2026-08-01T10:16:52",
    updated_at: "2026-08-01T10:16:52",
  };
  const TableProbe = ({ columns }) => {
    const actionColumn = columns.at(-1);
    return React.createElement(
      "output",
      { "data-case-type-actions": true },
      actionColumn.render(undefined, row),
    );
  };
  const pagePath = fileURLToPath(
    new URL("./src/SystemCenterPage.tsx", import.meta.url),
  );
  const page = executeTsx(
    fs.readFileSync(pagePath, "utf8"),
    pagePath,
    (specifier) => {
      if (specifier === "antd") return { ...realAntd, Table: TableProbe };
      if (specifier === "@ant-design/icons") return icons;
      if (specifier === "./api") return { api: {} };
      if (specifier === "./system-center.css") return {};
      return nativeRequire(specifier);
    },
  );
  return renderToStaticMarkup(
    React.createElement(page.default, {
      initialView: "system-parameters-case-type",
    }),
  );
}

test("case-type rows expose legacy edit action without a delete action", () => {
  const html = renderCaseTypeActions();

  assert.match(html, /修改/);
  assert.doesNotMatch(html, /data-icon="delete"/);
});
