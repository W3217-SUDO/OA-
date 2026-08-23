import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { createRequire } from "node:module";
import ts from "typescript";

const page = fs.readFileSync("src/SealCenterPage.tsx", "utf8");
const policyPath = path.join(process.cwd(), "src", "sealWorkflowPolicy.ts");
const policySource = fs.readFileSync(policyPath, "utf8");
const backend = fs.readFileSync(path.resolve(process.cwd(), "..", "api-server", "app", "main.py"), "utf8");
const oldRoot = path.resolve(process.cwd(), "..", "..", "..", "旧系统归档源码", "SH.CRM.WEB");
const oldOfficialDocumentController = fs.readFileSync(
  path.join(oldRoot, "Areas", "AWS", "Controllers", "OfficialDocumentController.cs"),
  "utf8",
);
const oldOfficialDocumentFileController = fs.readFileSync(
  path.join(oldRoot, "Areas", "AWS", "Controllers", "OfficialDocumentFileController.cs"),
  "utf8",
);

function sourceHas(source, pattern) {
  return pattern.test(source);
}

function sliceBetween(source, startToken, endToken) {
  const start = source.indexOf(startToken);
  assert.notEqual(start, -1, "missing source anchor: " + startToken);
  const end = source.indexOf(endToken, start + startToken.length);
  assert.notEqual(end, -1, "missing source end anchor: " + endToken);
  return source.slice(start, end);
}

function loadPolicy() {
  const javascript = ts.transpileModule(policySource, {
    fileName: policyPath,
    compilerOptions: {
      esModuleInterop: true,
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText;
  const module = { exports: {} };
  const wrapper = vm.runInThisContext(
    "(function (require, module, exports, __filename, __dirname) { " + javascript + "\n})",
    { filename: policyPath },
  );
  wrapper(createRequire(import.meta.url), module, module.exports, policyPath, path.dirname(policyPath));
  return module.exports;
}

test("legacy print, rollback, stamp-upload and download contracts are present", () => {
  assert.ok(
    sourceHas(oldOfficialDocumentController, /public JsonResult Print\(List<string> officialDocumentNos\)[\s\S]*?OfficialDocumentService\.Instance\.Print\(officialDocumentNos\)[\s\S]*?用印成功/),
    "legacy Print accepted officialDocumentNos and returned success text",
  );
  assert.ok(
    sourceHas(oldOfficialDocumentController, /public JsonResult Rollback\(List<string> officialDocumentNos\)[\s\S]*?OfficialDocumentService\.Instance\.Rollback\(officialDocumentNos\)[\s\S]*?用印撤回成功/),
    "legacy Rollback accepted officialDocumentNos and returned success text",
  );
  assert.ok(
    sourceHas(oldOfficialDocumentController, /StampFileUpload\(string officialDocumentNos\)[\s\S]*?Request\.Files\[0\][\s\S]*?OfficialDocumentFileService\.Instance\.CreateUpdate\(officialDocumentFile, bytes\)[\s\S]*?OfficialDocumentService\.Instance\.Print\(officialDocumentNos\.Split\(','\)\.ToList\(\)\)/),
    "legacy StampFileUpload persisted the uploaded stamp file before printing",
  );
  assert.ok(
    sourceHas(oldOfficialDocumentController, /public JsonResult Download\(List<string> officialDocumentNos\)[\s\S]*?OfficialDocumentService\.Instance\.Download\(officialDocumentNos\)[\s\S]*?FileName = fileName[\s\S]*?下载成功/),
    "legacy Download returned a PostResponse payload with the generated file name",
  );
});

test("waiting-stamp action exposes a stamp attachment upload or selection before stamping", () => {
  const actionModal = sliceBetween(page, "open={Boolean(action)}", "</Modal>");
  assert.ok(
    sourceHas(actionModal, /action\?\.type === "stamp"[\s\S]*?(Upload|盖章附件|stamp_attachment|stamp_file|stamp_file_id|stamp_attachment_id|attachmentSelectedKeys)/),
    "the waiting-stamp modal must let admins select or upload the stamped file before confirming actual seal use",
  );
  assert.ok(
    sourceHas(actionModal, /(盖章附件|上传盖章文件|已盖章文件|stamp attachment|stamped file)/i),
    "the stamp action UI should distinguish stamped attachments from the draft-stage source seal files",
  );
});

test("stamp attachment selector consumes paged seal files instead of hard-capping the first page", () => {
  assert.ok(
    sourceHas(
      oldOfficialDocumentFileController,
      /OfficialDocumentFiles\(string officialDocumentGuid, int\? pageNo, int\? pageSize\)[\s\S]*?result\.PageNo = pageNo > 0 \? pageNo\.Value : 1;[\s\S]*?result\.PageSize = pageSize > 0 \? pageSize\.Value : 15;/,
    ),
    "legacy official document file list defaulted to server-side 15-row paging",
  );

  const stampAttachmentLoader = sliceBetween(
    page,
    "const resetStampAttachmentState = () =>",
    "const runAction = async",
  );
  const actionModal = sliceBetween(page, "open={Boolean(action)}", "</Modal>");

  assert.ok(
    sourceHas(stampAttachmentLoader, /stampAttachmentPage/),
    "stamp attachment selector must track the current attachment page",
  );
  assert.ok(
    sourceHas(stampAttachmentLoader, /stampAttachmentPageSize/),
    "stamp attachment selector must track page_size for attachment requests",
  );
  assert.ok(
    sourceHas(stampAttachmentLoader, /stampAttachmentTotal/),
    "stamp attachment selector must preserve response.total",
  );
  assert.ok(
    sourceHas(stampAttachmentLoader, /api\.get\("\/attachments"[\s\S]*?page:\s*nextPage[\s\S]*?page_size:\s*nextPageSize/),
    "stamp attachment loader must request /attachments with explicit page and page_size",
  );
  assert.ok(
    !sourceHas(stampAttachmentLoader, /page_size:\s*200/),
    "stamp attachment selector must not hard-cap choices at the first 200 rows",
  );
  assert.ok(
    sourceHas(actionModal, /(loadMoreStampAttachments|stampAttachmentTotal|stampAttachmentPage)/),
    "stamp action modal must expose a way to consume additional stamp attachment pages",
  );
});

test("stamp submission is gated on successful stamp attachment upload", () => {
  const runAction = sliceBetween(page, "const runAction = async", "const runBatchStamp = async");
  assert.ok(
    sourceHas(runAction, /(stampAttachment|stampFile|stampedFile|uploadedStamp|stamp_file_id|stamp_attachment_id)/),
    "runAction must track the stamped-file upload result before calling /stamp",
  );
  assert.ok(
    sourceHas(runAction, /if\s*\([^)]*(stampAttachment|stampFile|stampedFile|uploadedStamp|stamp_file_id|stamp_attachment_id)[^)]*\)[\s\S]*?postSeal\([^)]*\/stamp/),
    "the /stamp request must only execute after a stamped attachment has been uploaded or selected",
  );
});

test("stamp upload failure path must not call the stamp endpoint", () => {
  const runAction = sliceBetween(page, "const runAction = async", "const runBatchStamp = async");
  const uploadStampAttachment = sliceBetween(page, "const uploadStampAttachments = async", "const runAction = async");
  assert.ok(
    sourceHas(uploadStampAttachment, /catch\s*\([^)]*\)[\s\S]*?setStampAttachmentUploadFailed\(true\)[\s\S]*?return \[\]/),
    "a stamped-file upload failure must be recorded before any stamp attempt",
  );
  assert.ok(
    sourceHas(runAction, /if \(stampAttachmentUploadFailed\)[\s\S]*?return[\s\S]*?stamp_attachment_id/),
    "runAction must return without /stamp when the stamped-file upload failed",
  );
  assert.ok(
    !sourceHas(runAction, /catch\s*\([^)]*\)[\s\S]*?postSeal\([^)]*\/stamp/),
    "the failure path must not fall through to /stamp",
  );
});

test("withdraw gates remain limited to pending approval and waiting-stamp statuses", () => {
  const { canBatchWithdrawSealRows, canSealWithdraw } = loadPolicy();

  assert.equal(canSealWithdraw({ status: "待审批" }), true);
  assert.equal(canSealWithdraw({ status: "待用印" }), true);
  assert.equal(canSealWithdraw({ status: "草稿" }), false);
  assert.equal(canSealWithdraw({ status: "已用印" }), false);
  assert.equal(canSealWithdraw({ status: "已归档" }), false);
  assert.equal(canBatchWithdrawSealRows([{ status: "待审批" }, { status: "待用印" }]), true);
  assert.equal(canBatchWithdrawSealRows([{ status: "待审批" }, { status: "已用印" }]), false);
});

test.todo("backend batch package download filters category == 用印文件 after main.py serial window");
