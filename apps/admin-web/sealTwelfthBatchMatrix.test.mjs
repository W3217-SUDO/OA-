import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { test } from "node:test";

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

test("old detail, audit and file handlers remain independent authenticated reads", () => {
  assert.match(oldController, /\[CheckUserLogin\][\s\S]*?ActionResult Preview\(/);
  assert.match(oldController, /\[CheckUserLogin\][\s\S]*?ActionResult AuditList\(/);
  assert.match(oldFileController, /OfficialDocumentFiles\(string officialDocumentGuid, int\? pageNo, int\? pageSize\)/);
  assert.match(oldFileController, /\[CheckUserLogin\][\s\S]*?OfficialDocumentFileDownload\(/);
});

test("detail reads isolate stale responses and attachment failures", () => {
  assert.match(local, /createSealDetailRequestTracker/);
  assert.match(local, /const requestId = detailRequestTracker\.next\(\)/);
  assert.match(local, /detailRequestTracker\.isCurrent\(requestId\)/);
  assert.match(local, /Promise\.allSettled\(\[/);
  assert.match(local, /setHistory\(\[\]\)/);
  assert.match(local, /detailRequestTracker\.invalidate\(\)/);
});

test("file list and preview failures clear stale modal state", () => {
  assert.match(local, /createSealFileListRequestTracker/);
  assert.match(local, /fileListRequestTracker\.next\(\)/);
  assert.match(local, /fileListRequestTracker\.isCurrent\(requestId\)/);
  assert.match(local, /fileListRequestTracker\.invalidate\(\)/);
  assert.match(local, /createSealPreviewRequestTracker/);
  assert.match(local, /previewRequestTracker\.next\(\)/);
  assert.match(local, /previewRequestTracker\.isCurrent\(requestId\)/);
  assert.match(local, /previewRequestTracker\.invalidate\(\)/);
  assert.match(local, /URL\.revokeObjectURL\(url\)/);
  assert.match(local, /const openFileList = async[\s\S]*?setFileListAttachments\(\[\]\)[\s\S]*?setFileListOpen\(false\)/);
  assert.match(local, /const previewAttachment = async[\s\S]*?setPreviewOpen\(false\)/);
  assert.match(local, /setPreviewName\(""\)/);
  assert.match(local, /setPreviewDetail\(""\)/);
});
