import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const page = fs.readFileSync("src/SealCenterPage.tsx", "utf8");
const oldEdit = fs.readFileSync(
  path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    "../../../旧系统归档源码/SH.CRM.WEB/Areas/AWS/Views/OfficialDocument/PartialView/Edit.cshtml",
  ),
  "utf8",
);

test("legacy edit modal exposes direct submit-to-audit and React keeps that entry", () => {
  assert.match(oldEdit, /id="btnOfficialDocumentToAudit"[\s\S]*?value="提交"/);
  assert.match(
    page,
    /保存并提交审批/,
    "the edit modal should submit the saved application without returning to the list",
  );
});

test("direct edit submission reuses the existing seal submit endpoint after save", () => {
  assert.match(
    page,
    /createApplication\s*=|const createApplication/,
  );
  assert.match(
    page,
    /保存并提交审批[\s\S]*?createSubmitModeRef\.current = true[\s\S]*?createApplication\(\)/,
    "the direct-submit button should opt into the save-then-submit flow",
  );
  assert.match(
    page,
    /createApplication[\s\S]*?\/seals\/applications\/\$\{savedApplication\.id\}\/submit/,
    "the flow should call the existing application submit endpoint after saving",
  );
});
