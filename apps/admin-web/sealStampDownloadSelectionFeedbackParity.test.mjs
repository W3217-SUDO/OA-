import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const page = fs.readFileSync("src/SealCenterPage.tsx", "utf8");
const oldScript = fs.readFileSync(
  path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    "../../../旧系统归档源码/SH.CRM.WEB/Scripts/AWS/OfficialDocument/AWS.OfficialDocument.js",
  ),
  "utf8",
);

test("legacy stamp and download entries report a missing selection", () => {
  assert.match(
    oldScript,
    /#btnOfficialDocumentPrint[\s\S]*?officialDocumentNos\.length == 0[\s\S]*?请选择用印文件/,
  );
  assert.match(
    oldScript,
    /#btnOfficialDocumentDownload[\s\S]*?officialDocumentNos\.length == 0[\s\S]*?请选择用印文件/,
  );
  assert.match(
    page,
    /const stampSelectedApplications = \(\) =>[\s\S]*?请选择用印文件[\s\S]*?canBatchStampSealRows/,
  );
  assert.match(
    page,
    /const downloadSelectedSealFiles = \(\) =>[\s\S]*?请选择用印文件[\s\S]*?packageDownload/,
  );
});

test("stamp keeps its selection handler while package download requires a selection", () => {
  assert.match(
    page,
    /<Button\s+onClick=\{\(\) => stampSelectedApplications\(\)\}\s*>\s*标记用印\s*<\/Button>/,
  );
  assert.match(
    page,
    /<Button\s+disabled=\{!selectedRows\.length\}\s+onClick=\{\(\) => downloadSelectedSealFiles\(\)\}\s*>\s*打包下载\s*<\/Button>/,
  );
  assert.doesNotMatch(
    page,
    /<Button[\s\S]*?disabled=\{\s*!canBatchStampSealRows\(selectedRows\)\s*\}[\s\S]*?标记用印\s*<\/Button>/,
  );
});
