import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const oldRoot = path.resolve(process.cwd(), "..", "..", "..", "旧系统归档源码", "SH.CRM.WEB");
const oldFiles = fs.readFileSync(path.join(oldRoot, "Areas", "AWS", "Controllers", "OfficialDocumentFileController.cs"), "utf8");
const oldController = fs.readFileSync(path.join(oldRoot, "Areas", "AWS", "Controllers", "OfficialDocumentController.cs"), "utf8");
const oldAudit = fs.readFileSync(path.join(oldRoot, "Areas", "AWS", "Controllers", "OfficialDocumentAuditController.cs"), "utf8");
const oldScript = fs.readFileSync(path.join(oldRoot, "Scripts", "AWS", "OfficialDocument", "AWS.OfficialDocument.js"), "utf8");
const localPage = fs.readFileSync("src/SealCenterPage.tsx", "utf8");
const localApi = fs.readFileSync(path.resolve(process.cwd(), "..", "api-server", "app", "main.py"), "utf8");

test("seal second batch maps upload, permissions, package download and workflow failures", () => {
  // 01–04: legacy file upload/delete/download contracts and local guarded actions.
  assert.match(oldFiles, /\[HttpPost\][\s\S]*Delete\(List<long> fileIds\)/);
  assert.match(oldFiles, /删除成功！/);
  assert.match(oldFiles, /删除失败！/);
  assert.match(oldFiles, /OfficialDocumentFileUpload\(OfficialDocumentModel model\)/);
  assert.match(oldFiles, /Request\.Files\.Count/);
  assert.match(oldFiles, /上传成功！/);
  assert.match(oldFiles, /\[CheckUserLogin\][\s\S]*OfficialDocumentFileDownload/);
  assert.match(localPage, /validateSealUploadFile/);
  assert.match(localApi, /async def upload_seal_application_files/);
  assert.match(localApi, /files: list\[UploadFile\]/);
  assert.match(localPage, /\/seals\/applications\/\$\{detail\.id\}\/files/);
  assert.match(localPage, /body\.append\("files", file\)/);
  assert.match(localPage, /detail\.status === "草稿"/);
  assert.match(localPage, /deleteSeal\(`\/attachments\/\$\{item\.id\}`\)/);

  // 05–08: package download selection, protected API and failure details.
  assert.match(oldController, /public JsonResult Download\(List<string> officialDocumentNos\)/);
  assert.match(oldController, /下载成功！/);
  assert.match(oldScript, /请选择用印文件/);
  assert.match(localPage, /\/seals\/applications\/package-download/);
  assert.match(localPage, /const downloadSelectedSealFiles = \(\) =>[\s\S]*?请选择用印文件/);
  assert.match(localApi, /async def package_download_seal_files/);
  assert.match(localApi, /所选用印申请暂无可下载附件/);

  // 09–12: administrative status flow and approval failure handling.
  assert.match(oldController, /public JsonResult Print\(List<string> officialDocumentNos\)/);
  assert.match(oldController, /public JsonResult Rollback\(List<string> officialDocumentNos\)/);
  assert.match(oldAudit, /AuditStatus\.A/);
  assert.match(oldAudit, /AuditStatus\.R/);
  assert.match(localPage, /type: "approve" \| "reject" \| "stamp" \| "archive"/);
  assert.match(localPage, /sealActionFailureMessage\(action\.type\)/);
  assert.match(localApi, /item\.status = "待用印" if body\.approved else "已拒绝"/);
});
