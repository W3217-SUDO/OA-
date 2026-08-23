import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";
import { createRequire } from "node:module";
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

function loadAppModule() {
  const appPath = fileURLToPath(new URL("./src/App.tsx", import.meta.url));
  const componentModule = { __esModule: true, default: () => null };
  const localModules = {
    "./api": { api: {}, AUTH_EXPIRED_EVENT: "auth-expired" },
    "./NotificationCenter": componentModule,
    "./GlobalSearch": componentModule,
    "./caseDetailNavigation": { rememberCaseDetailTarget() {} },
    "./customerDetailNavigation": { rememberCustomerDetailTarget() {} },
    "./contractDetailNavigation": {
      CONTRACT_DETAIL_TARGET_EVENT: "contract-detail-target",
      clearContractDetailTarget() {},
    },
    "./contractCreateContext": {
      clearContractCustomerContext() {},
      CONTRACT_CUSTOMER_ROUTE_SOURCE_KEY: "contract-customer-route-source",
    },
    "dingtalk-jsapi/entry/union": {},
    "dingtalk-jsapi/api/runtime/permission/requestAuthCode": {
      __esModule: true,
      default: async () => ({ code: "" }),
    },
    "dingtalk-jsapi/lib/env": { getENV: () => ({ platform: "notInDingTalk" }) },
  };
  return executeTsx(
    fs.readFileSync(appPath, "utf8"),
    appPath,
    (specifier) => localModules[specifier] ?? nativeRequire(specifier),
  );
}

test("system-parameters parent opens the overview only when entering from outside its section", () => {
  const app = loadAppModule();

  assert.equal(typeof app.routeForMenuOpenChange, "function");
  assert.equal(
    app.routeForMenuOpenChange(
      ["system", "system-parameters"],
      ["system"],
      "dashboard",
    ),
    "system-parameters",
  );
  assert.equal(
    app.routeForMenuOpenChange(
      ["system"],
      ["system", "system-parameters"],
      "dashboard",
    ),
    "system-parameters",
  );
  assert.equal(
    app.routeForMenuOpenChange(
      ["system"],
      ["system", "system-parameters"],
      "system-parameters-case-type",
    ),
    null,
  );
  assert.equal(
    app.routeForMenuOpenChange(
      ["system", "system-parameters"],
      ["system"],
      "system-parameters",
    ),
    null,
  );
  assert.equal(
    app.routeForMenuOpenChange(
      ["system"],
      ["system", "system-management"],
      "dashboard",
    ),
    null,
  );
});
