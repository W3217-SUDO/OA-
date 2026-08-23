import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

assert.match(source, /className="case-detail-body-grid"/);
assert.match(source, /className="case-detail-side-panel"/);
assert.ok(source.indexOf('aria-label="法院信息"') < source.indexOf('aria-label="归档信息"'));
assert.ok(source.indexOf('aria-label="归档信息"') < source.indexOf('className="case-detail-body-grid"'));

const archiveSection = source.slice(
  source.indexOf('<section className="case-archive-summary"'),
  source.indexOf('<div className="case-detail-body-grid"'),
);
for (const field of [
  "archive_type",
  "archive_submitter",
  "archive_submitted_at",
  "archive_status",
  "archive_internal_reviewer",
  "archive_internal_reviewed_at",
  "archive_internal_review_comment",
  "archive_reviewer",
  "archive_reviewed_at",
  "archive_no",
]) {
  assert.match(archiveSection, new RegExp(field));
}
assert.equal([...archiveSection.matchAll(/<strong>([^<]+)<\/strong>/g)].length, 12);

console.log("case detail row 20 layout contract passed");
