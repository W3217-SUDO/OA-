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

test("legacy rollback confirms the batch before calling the API", () => {
  assert.match(
    oldScript,
    /Rollback: function \(\)[\s\S]*?officialDocumentNos\.length == 0[\s\S]*?showModalConfirmDialog\("确定撤回用印申请？"[\s\S]*?RollbackCallBack[\s\S]*?officialDocumentNos/,
  );
  assert.match(
    page,
    /const batchWithdraw = async \(selected: SealRow\[\]\) =>[\s\S]*?Modal\.confirm\([\s\S]*?(确定撤回|撤回用印申请)[\s\S]*?postSeal\("\/seals\/applications\/batch\/withdraw"/,
    "batch withdraw must confirm before calling the batch API",
  );
});

test("legacy stamp upload modal is opened for every selected application", () => {
  assert.match(
    oldScript,
    /#btnOfficialDocumentPrint[\s\S]*?Stamp\.UploadFile\(officialDocumentNos\)/,
  );
  assert.match(
    oldScript,
    /UploadFile\s*:\s*function \(officialDocumentNos\)[\s\S]*?fileUploadForm[\s\S]*?officialDocumentNos/,
  );
});

test.todo("backend batch-stamp accepts and persists stamp_attachment_id after main.py serial window");
