import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const oldRoot = path.resolve(
  "C:/Users/13533/Desktop/OA\u7cfb\u7edf/\u65e7\u7cfb\u7edf\u5f52\u6863\u6e90\u7801/SH.CRM.WEB",
);
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
  assert.match(local, /const \[historyResult\] = await Promise\.all/);
});

test("single seal mutations reuse the in-flight action gate", () => {
  assert.match(local, /const createApplication = async[\s\S]*?actionGate\.tryEnter/);
  assert.match(local, /const submit = async[\s\S]*?actionGate\.tryEnter/);
  assert.match(local, /const withdraw = async[\s\S]*?actionGate\.tryEnter/);
  assert.match(local, /const saveAsset = async[\s\S]*?actionGate\.tryEnter/);
  assert.match(local, /const removeAsset = async[\s\S]*?actionGate\.tryEnter/);
  assert.match(local, /const removeSealFile = async[\s\S]*?actionGate\.tryEnter/);
});
