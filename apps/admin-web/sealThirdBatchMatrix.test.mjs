import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const oldRoot = path.resolve(process.cwd(), "..", "..", "..", "旧系统归档源码", "SH.CRM.WEB");
const oldController = fs.readFileSync(path.join(oldRoot, "Areas", "AWS", "Controllers", "OfficialDocumentController.cs"), "utf8");
const oldFiles = fs.readFileSync(path.join(oldRoot, "Areas", "AWS", "Controllers", "OfficialDocumentFileController.cs"), "utf8");
const oldScript = fs.readFileSync(path.join(oldRoot, "Scripts", "AWS", "OfficialDocument", "AWS.OfficialDocument.js"), "utf8");
const localPage = fs.readFileSync("src/SealCenterPage.tsx", "utf8");
const localApi = fs.readFileSync(path.resolve(process.cwd(), "..", "api-server", "app", "main.py"), "utf8");

test("seal third batch keeps legacy selection semantics while wiring protected actions", () => {
  // 01–04: old selection guards and action payloads.
  assert.match(oldScript, /请选择用印文件/);
  assert.match(oldScript, /officialDocumentNos/);
  assert.match(oldScript, /checkbox\.vals\("chkOfficialDocumentId"\)/);
  assert.match(oldController, /Download\(List<string> officialDocumentNos\)/);
  assert.match(oldController, /Print\(List<string> officialDocumentNos\)/);
  assert.match(oldController, /Rollback\(List<string> officialDocumentNos\)/);

  // 05–08: delete/download permissions and failure paths.
  assert.match(oldFiles, /Delete\(List<long> fileIds\)/);
  assert.match(oldFiles, /OfficialDocumentFileDownload/);
  assert.match(oldFiles, /catch \(ApplicationException ex\)/);
  assert.match(localPage, /sealAttachmentDeleteFailureMessage/);
  assert.match(localPage, /sealPackageDownloadFailureMessage/);
  assert.match(localPage, /setSelectedKeys\(\[\]\)/);
  assert.match(localPage, /if \(!selected\.length\)/);

  // 09–12: administrative stamping/approval UI is connected to real endpoints.
  assert.match(localPage, /initialView === "seal-admin-pending"/);
  assert.match(localPage, /setAction\(\{ type: "stamp", row: selectedRow \}\)/);
  assert.match(localPage, /\/seals\/applications\/package-download/);
  assert.match(localPage, /\/seals\/applications\/\$\{action\.row\.id\}\/approve/);
  assert.match(localApi, /async def package_download_seal_files/);
  assert.match(localApi, /async def approve_seal_application/);
});
