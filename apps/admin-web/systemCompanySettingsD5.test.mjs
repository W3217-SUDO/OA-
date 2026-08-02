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
const companyStart = source.indexOf(
  '} else if (initialView === "system-parameters-company")',
);
const companyEnd = source.indexOf(
  '} else if (initialView === "system-management-cache")',
  companyStart,
);
const companyBlock = source.slice(companyStart, companyEnd);
const saveConfigStart = source.indexOf("const saveConfig = async");
const saveConfigEnd = source.indexOf("const startParameter", saveConfigStart);
const saveConfigBlock = source.slice(saveConfigStart, saveConfigEnd);

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

test("company settings expose the legacy guidance and eleven fields", () => {
  assert.match(
    companyBlock,
    /请完善以下信息,方便我们更好的为您服务/,
  );
  for (const name of [
    "name",
    "code",
    "short_code",
    "address",
    "phone",
    "fax",
    "email",
    "postal_code",
    "bank_name",
    "bank_account",
    "bank_address",
  ]) {
    assert.match(companyBlock, new RegExp(`name: "${name}"`));
  }
});

test("company postal code and bank account clean visible non-digit input", () => {
  const page = loadPageModule();
  const postalInput = { value: "12312abc" };
  const accountInput = { value: "12121212121x-y" };

  assert.equal(page.cleanCompanyDigitsInputEvent({ currentTarget: postalInput }), "12312");
  assert.equal(postalInput.value, "12312");
  assert.equal(page.cleanCompanyDigitsInputEvent({ currentTarget: accountInput }), "12121212121");
  assert.equal(accountInput.value, "12121212121");
  assert.match(
    companyBlock,
    /name: "postal_code"[\s\S]*normalize: sanitizeCompanyDigitsInput/,
  );
  assert.match(
    companyBlock,
    /name: "bank_account"[\s\S]*normalize: sanitizeCompanyDigitsInput/,
  );
});

test("company email and required failures are validated before PATCH", () => {
  assert.match(companyBlock, /name: "email"[\s\S]*type: "email"/);
  assert.match(companyBlock, /请填写正确联系邮箱！/);
  assert.match(companyBlock, /请输入红星\*必填项\./);
  assert.ok(
    saveConfigBlock.indexOf("validateFields()") <
      saveConfigBlock.indexOf("api.patch"),
  );
});

test("company settings keep one save action and no cancel action", () => {
  assert.equal((companyBlock.match(/>\s*保存\s*</g) || []).length, 1);
  assert.doesNotMatch(companyBlock, />\s*取消\s*</);
});
