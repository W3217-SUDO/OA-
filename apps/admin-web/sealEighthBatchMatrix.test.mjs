import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const oldRoot = path.resolve(process.cwd(), "..", "..", "..", "旧系统归档源码", "SH.CRM.WEB");
const oldController = fs.readFileSync(
  path.join(oldRoot, "Areas", "AWS", "Controllers", "OfficialDocumentController.cs"),
  "utf8",
);
const oldFileController = fs.readFileSync(
  path.join(oldRoot, "Areas", "AWS", "Controllers", "OfficialDocumentFileController.cs"),
  "utf8",
);
const local = fs.readFileSync("src/SealCenterPage.tsx", "utf8");

test("old detail and file handlers keep authenticated read and explicit failure paths", () => {
  assert.match(oldController, /CheckUserLogin/);
  assert.match(oldController, /Preview\s*\(/);
  assert.match(oldController, /Edit\s*\(/);
  assert.match(oldController, /AuditList\s*\(/);
  assert.match(oldFileController, /catch \(ApplicationException ex\)/);
  assert.match(oldFileController, /OfficialDocumentFileDownload/);
});

test("seal query reset and status-aware detail loading are wired", () => {
  assert.match(local, /const clearQuery = \(\) =>/);
  assert.match(local, /queryForm\.resetFields\(\)/);
  assert.match(local, /sealQueryFailureMessage/);
  assert.match(local, /sealAttachmentListFailureMessage/);
  assert.match(local, /const \[historyResult, filesResult\] = await Promise\.allSettled/);
});

test("seal preview keeps legacy customer, type, print and remark fields", () => {
  assert.match(local, /key: "customer_no"/);
  assert.match(local, /key: "use_type"/);
  assert.match(local, /key: "print_quantity"/);
  assert.match(local, /key: "remark"/);
});

test("seal file lists expose legacy uploader, date, type and size metadata", () => {
  assert.match(local, /formatSealAttachmentSize/);
  assert.match(local, /getSealAttachmentExtension/);
  assert.match(local, /dataIndex: "size"/);
  assert.match(local, /dataIndex: "created_at"/);
});

test("seal asset audit detail consumes the paged backend contract behind an admin-manager gate", () => {
  assert.match(local, /canViewSealAssetAudit/);
  assert.match(local, /canReadAssetAudit && \(/);
  assert.match(local, /openAssetAudit\(r\)/);
  assert.match(local, /`\/seals\/assets\/\$\{assetId\}\/audit`/);
  assert.match(local, /page_size: nextPageSize/);
  assert.match(local, /date_from: filters\.date_from/);
  assert.match(local, /date_to: filters\.date_to/);
  assert.match(local, /sealAssetAuditPagination\.pageSizeOptions/);
  assert.match(local, /assetAuditTotal/);
  assert.match(local, /refreshAssetAudit/);
  assert.match(local, /shouldCloseSealAssetAuditAfterDelete/);
  assert.match(local, /setAssetAuditOpen\(false\)/);
  assert.match(local, /setAssetAuditRows\(\[\]\)/);
  assert.match(local, /assetAuditRequestTracker\.next\(\)/);
  assert.match(local, /assetAuditRequestTracker\.isCurrent\(requestId\)/);
  assert.match(local, /const latest = .*find\(.*target\.id/);
  assert.match(local, /setAssetAuditAsset\(latest\)/);
  assert.match(local, /mergeSealAssetSnapshot\(currentAssets, latest\)/);
  assert.doesNotMatch(local, /setAssets\(inventoryResult\.data\.items/);
  assert.match(local, /Promise\.all\(\[/);
  assert.match(local, /clearAssetAudit\(\)/);
});

test("single seal mutations reuse the in-flight action gate", () => {
  assert.match(local, /const createApplication = async[\s\S]*?actionGate\.tryEnter/);
  assert.match(local, /const submit = async[\s\S]*?actionGate\.tryEnter/);
  assert.match(local, /const withdraw = async[\s\S]*?actionGate\.tryEnter/);
  assert.match(local, /const saveAsset = async[\s\S]*?actionGate\.tryEnter/);
  assert.match(local, /const removeAsset = async[\s\S]*?actionGate\.tryEnter/);
  assert.match(local, /const removeSealFile = async[\s\S]*?actionGate\.tryEnter/);
});
