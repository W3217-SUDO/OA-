import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";
import { createRequire } from "node:module";
import ts from "typescript";

const nativeRequire = createRequire(import.meta.url);
const pagePath = fileURLToPath(
  new URL("./src/SystemCenterPage.tsx", import.meta.url),
);
const source = fs.readFileSync(pagePath, "utf8");

function loadPageModule() {
  const javascript = ts.transpileModule(source, {
    fileName: pagePath,
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
    { filename: pagePath },
  );
  wrapper(
    (specifier) => {
      if (specifier === "./api") return { api: {} };
      if (specifier === "./system-center.css") return {};
      return nativeRequire(specifier);
    },
    module,
    module.exports,
    pagePath,
    path.dirname(pagePath),
  );
  return module.exports;
}

test("customer share days remove non-digit characters while typing", () => {
  const page = loadPageModule();

  assert.equal(typeof page.sanitizeShareDaysInput, "function");
  assert.equal(page.sanitizeShareDaysInput("abc"), "");
  assert.equal(page.sanitizeShareDaysInput("12abc3"), "123");
  assert.equal(page.sanitizeShareDaysInput("-5.8"), "58");
  assert.equal(page.sanitizeShareDaysInput(undefined), "");
  const input = { value: "100abc" };
  assert.equal(
    page.cleanShareDaysInputEvent({ currentTarget: input }),
    "100",
  );
  assert.equal(input.value, "100");

  assert.equal(page.isShareDaysValueValid("1"), true);
  assert.equal(page.isShareDaysValueValid(3650), true);
  assert.equal(page.isShareDaysValueValid("0"), false);
  assert.equal(page.isShareDaysValueValid(3651), false);
  assert.equal(page.isShareDaysValueValid("abc"), false);
});

test("every customer share input uses the shared digit sanitizer", () => {
  const shareStart = source.indexOf('title="客户共享时间设置"');
  const shareEnd = source.indexOf("</Card>", shareStart);
  const shareBlock = source.slice(shareStart, shareEnd);

  assert.match(shareBlock, /normalize=\{sanitizeShareDaysInput\}/);
  assert.match(shareBlock, /onInput=\{cleanShareDaysInputEvent\}/);
  assert.match(shareBlock, /isShareDaysValueValid\(value\)/);
});
