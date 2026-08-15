import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

assert.match(source, /aria-label="法院信息"/);
assert.match(source, /aria-label="归档信息"/);
assert.match(source, /title="案件信息"/);
assert.match(source, /className="case-detail-body-grid"/);
assert.ok(source.indexOf('aria-label="法院信息"') < source.indexOf('aria-label="归档信息"'));
assert.ok(source.indexOf('aria-label="归档信息"') < source.indexOf('className="case-detail-body-grid"'));
for (const field of ["archive_status", "archive_no", "archive_submitter", "archive_submitted_at", "archive_reviewer", "archive_reviewed_at"]) {
  assert.match(source, new RegExp(field));
}
assert.doesNotMatch(source, /archive_status\s*\|\|\s*viewingCounselCase\.status/);
assert.doesNotMatch(source, /archive_submitter\s*\|\|\s*viewingCounselCase\.owner/);
assert.doesNotMatch(source, /archive_status\s*\|\|\s*row\.status/);
assert.match(source, /archive_submitter\s*\?\s*casePersonDisplayName/);
assert.match(source, /archive_reviewer\s*\?\s*casePersonDisplayName/);

console.log("case detail row 20 layout contract passed");
