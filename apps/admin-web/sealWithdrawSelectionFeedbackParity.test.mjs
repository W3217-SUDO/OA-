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

test("legacy rollback selection reports a missing selection", () => {
  assert.match(
    oldScript,
    /Rollback: function[\s\S]*?officialDocumentNos\.length == 0[\s\S]*?请选择需要撤回的用印申请/,
  );
  assert.match(
    page,
    /const withdrawSelectedApplications = \(\) =>[\s\S]*?请选择需要撤回的用印申请[\s\S]*?canBatchWithdrawSealRows/,
    "the React withdraw entry should preserve the legacy missing-selection feedback",
  );
});

test("withdraw action uses the guarded selection handler instead of a silent disabled button", () => {
  assert.match(
    page,
    /<Button\s+onClick=\{\(\) => withdrawSelectedApplications\(\)\}\s*>\s*撤回\s*<\/Button>/,
  );
  assert.doesNotMatch(
    page,
    /<Button[\s\S]*?disabled=\{\s*!canBatchWithdrawSealRows\(selectedRows\)\s*\}[\s\S]*?撤回\s*<\/Button>/,
  );
});
