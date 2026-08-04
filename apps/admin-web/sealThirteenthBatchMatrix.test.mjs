import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import path from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";
import ts from "typescript";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);

const page = fs.readFileSync(new URL("./src/SealCenterPage.tsx", import.meta.url), "utf8");
const oldController = fs.readFileSync(new URL("../../../旧系统归档源码/SH.CRM.WEB/Areas/AWS/Controllers/OfficialDocumentController.cs", import.meta.url), "utf8");
const oldFileController = fs.readFileSync(new URL("../../../旧系统归档源码/SH.CRM.WEB/Areas/AWS/Controllers/OfficialDocumentFileController.cs", import.meta.url), "utf8");
const policyPath = fileURLToPath(new URL("./src/sealWorkflowPolicy.ts", import.meta.url));
const javascript = ts.transpileModule(fs.readFileSync(policyPath, "utf8"), {
  fileName: policyPath,
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
const policyModule = { exports: {} };
vm.runInThisContext(`(function (require, module, exports) { ${javascript}\n})`)(require, policyModule, policyModule.exports);
const { sealErrorMessage, sealResponseIsFailure, toSealAuditRows } = policyModule.exports;

test("legacy PostResponse and HTTP detail matrix is runnable", () => {
  assert.equal(sealResponseIsFailure({ IsSuccess: false, Message: "失败" }), true);
  assert.equal(sealResponseIsFailure({ is_success: false, message: "失败" }), true);
  assert.equal(sealResponseIsFailure({ items: [] }), false);
  assert.equal(sealErrorMessage({ response: { status: 409, data: { detail: "冲突" } } }, "fallback"), "冲突");
  assert.equal(sealErrorMessage({ IsSuccess: false, Message: "旧失败" }, "fallback"), "旧失败");
  assert.equal(toSealAuditRows([{ id: 1, action: "驳回", current_step: "审批驳回" }])[0].current_step, "审批驳回");
});

test("old controller/file routes and page handlers preserve response semantics", () => {
  assert.match(oldController, /CreateUpdate/);
  assert.match(oldController, /Preview/);
  assert.match(oldController, /AuditList/);
  assert.match(oldController, /Print\(List<string> officialDocumentNos\)/);
  assert.match(oldController, /Download\(List<string> officialDocumentNos\)/);
  assert.match(oldController, /Rollback\(List<string> officialDocumentNos\)/);
  assert.match(oldFileController, /OfficialDocumentFileUpload/);
  assert.match(oldFileController, /Delete\(List<long>/);
  assert.match(page, /sealResponseIsFailure/);
  assert.match(page, /sealErrorMessage/);
  assert.match(page, /ensureSealSuccess/);
  for (const name of [
    "createApplication", "submit", "withdraw", "batchWithdraw", "removeDraft",
    "runAction", "runBatchStamp", "uploadSealFile", "removeSealFile", "removeSealFiles",
    "packageDownload", "saveAsset", "removeAsset",
  ]) {
    assert.match(page, new RegExp(`const ${name} = [\\s\\S]*?postSeal|const ${name} = [\\s\\S]*?patchSeal|const ${name} = [\\s\\S]*?deleteSeal`));
  }
  for (const name of ["downloadAttachment", "previewAttachment", "openFileList"]) {
    assert.match(page, new RegExp(`const ${name} = [\\s\\S]*?sealErrorMessage`));
  }
  assert.match(page, /dataIndex: "current_step"/);
  assert.match(page, /response\.data instanceof Blob[\s\S]*?sealResponseIsFailure/);
});

test("batch delete keeps selection on atomic server failure", () => {
  assert.match(page, /removeSealFiles[\s\S]*?catch[\s\S]*?setAttachmentSelectedKeys\(\[\]\)/);
});
