import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const local = fs.readFileSync("src/SealCenterPage.tsx", "utf8");
const oldRoot = path.resolve(process.cwd(), "..", "..", "..", "旧系统归档源码", "SH.CRM.WEB");
const oldFileController = fs.readFileSync(
  path.join(oldRoot, "Areas", "AWS", "Controllers", "OfficialDocumentFileController.cs"),
  "utf8",
);
const oldController = fs.readFileSync(
  path.join(oldRoot, "Areas", "AWS", "Controllers", "OfficialDocumentController.cs"),
  "utf8",
);
const oldAuditController = fs.readFileSync(
  path.join(oldRoot, "Areas", "AWS", "Controllers", "OfficialDocumentAuditController.cs"),
  "utf8",
);
const oldListView = fs.readFileSync(
  path.join(oldRoot, "Areas", "AWS", "Views", "OfficialDocumentFile", "PartialView", "FileList.cshtml"),
  "utf8",
);
const oldScript = fs.readFileSync(
  path.join(oldRoot, "Scripts", "AWS", "OfficialDocument", "AWS.OfficialDocument.js"),
  "utf8",
);

test("old file list is authenticated and paged at fifteen", () => {
  assert.match(oldFileController, /CheckUserLogin/);
  assert.match(oldFileController, /OfficialDocumentFiles/);
  assert.match(oldFileController, /PageSize\s*=\s*15/);
  assert.match(oldListView, /FileId|FileName|OriginalName/);
});

test("local file list exposes read-only preview and download handlers", () => {
  assert.match(local, /const previewAttachment = async/);
  assert.match(local, /const downloadAttachment = async/);
  assert.match(local, /\/attachments\/\$\{item\.id\}\/preview/);
  assert.match(local, /\/attachments\/\$\{item\.id\}\/download/);
});

test("old controller supports delete and upload outcomes", () => {
  assert.match(oldFileController, /Delete\s*\(/);
  assert.match(oldFileController, /Request\.Files/);
  assert.match(oldFileController, /上传成功|删除成功/);
});

test("local attachment deletion remains guarded by draft and permission failures", () => {
  assert.match(local, /const removeSealFile = async/);
  assert.match(local, /sealAttachmentDeleteFailureMessage/);
  assert.match(local, /detail\.status === "草稿"/);
});

test("old print/download/stamp handlers are represented", () => {
  assert.match(oldController, /Print\s*\(/);
  assert.match(oldController, /Download\s*\(/);
  assert.match(oldController, /StampFileUpload/);
  assert.match(oldController, /用印失败/);
});

test("local admin actions map approval, stamping, and archive endpoints", () => {
  assert.match(local, /\/seals\/applications\/\$\{action\.row\.id\}\/approve/);
  assert.match(local, /\/seals\/applications\/\$\{action\.row\.id\}\/stamp/);
  assert.match(local, /\/seals\/applications\/\$\{action\.row\.id\}\/archive/);
  assert.match(local, /sealActionFailureMessage/);
});

test("old audit controller exposes pending/approved/rejected flows", () => {
  assert.match(oldAuditController, /PendingList/);
  assert.match(oldAuditController, /ApprovedList/);
  assert.match(oldAuditController, /RejectedList/);
  assert.match(oldAuditController, /AuditList/);
});

test("local approval tab and audit dialog are wired", () => {
  assert.match(local, /label:\s*["`]用印审批/);
  assert.match(local, /setAuditListOpen\(true\)/);
  assert.match(local, /title="审批流程"/);
});

test("official and administrative menus remain visible", () => {
  assert.match(local, /label:\s*["`]我的申请/);
  assert.match(local, /label:\s*["`]行政用印/);
  assert.match(local, /tabFromView/);
});

test("withdraw is available as a state transition", () => {
  assert.match(oldScript, /Rollback|Withdraw/);
  assert.match(local, /const withdraw = async/);
  assert.match(local, /\/seals\/applications\/\$\{row\.id\}\/withdraw/);
});

test("batch selection clears across view/query changes and guards empty downloads", () => {
  assert.match(local, /setSelectedKeys\(\[\]\)/);
  assert.match(local, /const packageDownload = async/);
  assert.match(local, /if \(!selected\.length\)/);
  assert.match(local, /请选择用印文件/);
});

test("attachment failure matrix distinguishes 403/404/409", () => {
  assert.match(local, /function sealAttachmentDownloadFailureMessage/);
  assert.match(local, /function sealAttachmentPreviewFailureMessage/);
  assert.match(local, /status === 403/);
  assert.match(local, /status === 404/);
  assert.match(local, /status === 409/);
});

test("package download keeps explicit 403/404 semantics", () => {
  assert.match(local, /function sealPackageDownloadFailureMessage/);
  assert.match(local, /所选用印申请暂无可下载附件/);
  assert.match(local, /当前账号无权下载所选用印附件/);
});
