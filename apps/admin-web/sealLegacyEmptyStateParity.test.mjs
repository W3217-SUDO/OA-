import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

test("seal audit and file-list modals keep the legacy empty table body", () => {
  const source = fs.readFileSync("src/SealCenterPage.tsx", "utf8");
  const auditStart = source.indexOf('<Modal\n        open={auditListOpen}');
  const fileStart = source.indexOf('<Modal\n        open={fileListOpen}');
  assert.ok(auditStart >= 0 && fileStart > auditStart);
  const audit = source.slice(auditStart, fileStart);
  const fileEnd = source.indexOf('<Modal\n        open={previewOpen}', fileStart);
  const file = source.slice(fileStart, fileEnd);
  assert.match(audit, /locale=\{\{\s*emptyText: ""/);
  assert.match(file, /locale=\{\{\s*emptyText: ""/);
});
