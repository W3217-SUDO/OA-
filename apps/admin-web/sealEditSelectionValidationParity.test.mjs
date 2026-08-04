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

test("legacy edit selection reports missing and multiple selections", () => {
  assert.match(oldScript, /officialDocumentIds\.length == 0[\s\S]*?请选择用印申请/);
  assert.match(oldScript, /officialDocumentIds\.length > 1[\s\S]*?只能选择一个用印申请进行修改/);
  assert.match(
    page,
    /const editSelectedApplication = \(\) =>[\s\S]*?请选择用印申请[\s\S]*?只能选择一个用印申请进行修改/,
    "the React edit entry should preserve the legacy selection feedback",
  );
});

test("edit action uses the guarded selection handler instead of a silent disabled button", () => {
  assert.match(page, /onClick=\{\(\) => editSelectedApplication\(\)\}/);
  assert.doesNotMatch(
    page,
    /<Button[\s\S]*?disabled=\{\s*!selectedRow \|\| selectedRow\.status !== "草稿"\s*\}[\s\S]*?修改\s*<\/Button>/,
  );
});
