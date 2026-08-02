import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const oldRoot = path.resolve(process.cwd(), "..", "..", "..", "旧系统归档源码", "SH.CRM.WEB");
const oldController = fs.readFileSync(path.join(oldRoot, "Areas", "AWS", "Controllers", "OfficialDocumentController.cs"), "utf8");
const oldFiles = fs.readFileSync(path.join(oldRoot, "Areas", "AWS", "Controllers", "OfficialDocumentFileController.cs"), "utf8");
const oldFileView = fs.readFileSync(path.join(oldRoot, "Areas", "AWS", "Views", "OfficialDocumentFile", "PartialView", "FileList.cshtml"), "utf8");
const oldListView = fs.readFileSync(path.join(oldRoot, "Areas", "AWS", "Views", "OfficialDocument", "List.cshtml"), "utf8");
const oldPreview = fs.readFileSync(path.join(oldRoot, "Areas", "AWS", "Views", "OfficialDocument", "PartialView", "Preview.cshtml"), "utf8");
const oldAuditView = fs.readFileSync(path.join(oldRoot, "Areas", "AWS", "Views", "OfficialDocumentAudit", "PartialView", "AuditList.cshtml"), "utf8");
const oldScript = fs.readFileSync(path.join(oldRoot, "Scripts", "AWS", "OfficialDocument", "AWS.OfficialDocument.js"), "utf8");
const localPage = fs.readFileSync("src/SealCenterPage.tsx", "utf8");
const localViewMap = fs.readFileSync("src/sealViewMapping.ts", "utf8");
const localApi = fs.readFileSync(path.resolve(process.cwd(), "..", "api-server", "app", "main.py"), "utf8");

test("seal source capability matrix records the first implementation batch", () => {
  // 01–04: list defaults, paging and status routing.
  assert.match(oldController, /PageSize\s*=\s*15/);
  assert.match(localPage, /defaultPageSize:\s*15/);
  assert.match(oldFiles, /pageSize > 0 \? pageSize\.Value : 15/);
  assert.match(localPage, /pageSizeOptions:\s*\[10, 15, 20, 50, 100, 200\]/);
  assert.match(oldController, /OfficialDocumentStatus\.P/);
  assert.match(oldController, /OfficialDocumentStatus\.E/);
  assert.match(oldController, /OfficialDocumentStatus\.N/);
  assert.match(oldController, /OfficialDocumentStatus\.R/);
  assert.match(oldController, /OfficialDocumentStatus\.W/);
  assert.match(localViewMap, /seal-my-pending/);

  // 05–08: query, file list, preview and upload entry points.
  assert.match(oldListView, /btnOfficialDocumentSearch/);
  assert.match(oldFileView, /FileList/);
  assert.match(oldFileView, /Files\.File\.View/);
  assert.match(oldFileView, /Files\.File\.Download/);
  assert.match(oldPreview, /用印类型/);
  assert.match(oldPreview, /用印文件/);
  assert.match(oldScript, /fileUploadForm/);
  assert.match(localPage, /new FormData\(\)/);

  // 09–12: authenticated download, protected preview and attachment writes.
  assert.match(oldFiles, /OfficialDocumentFileDownload/);
  assert.match(oldFiles, /CheckUserLogin/);
  assert.match(localApi, /async def download_attachment\(/);
  assert.match(localApi, /identity: dict = Depends\(current_identity\)/);
  assert.match(localApi, /async def preview_attachment\(/);
  assert.match(localPage, /\/attachments\/\$\{item\.id\}\/preview/);
  assert.match(localPage, /api\.delete\(`\/attachments\/\$\{item\.id\}`\)/);

  // 13–15: audit modal schema, close action and legacy empty-body behavior.
  assert.match(oldAuditView, /auditListModal/);
  assert.match(oldAuditView, /审批轮次/);
  assert.match(oldAuditView, /value="关闭"/);
  assert.match(localPage, /title="审批流程"/);
  assert.match(localPage, /locale=\{\{ emptyText: "" \}\}/);
});
