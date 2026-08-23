import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const normalArchive = "\u6b63\u5e38\u5f52\u6863";
const deficitArchive = "\u4e8f\u635f\u5f52\u6863";

test("case detail splits normal and deficit archive into real guarded actions", () => {
  assert.match(source, /counselDetailCapabilities\.can_archive/);
  assert.match(source, /data-testid="case-detail-archive-submenu"/);
  assert.match(source, /ARCHIVE_LOCKED_STATUSES\.includes\(viewingCounselCase\.status\)/);
  assert.match(source, /openArchive\(viewingCounselCase, "normal"\)/);
  assert.match(source, /openArchive\(viewingCounselCase, "deficit"\)/);
  assert.ok(source.includes(`>${normalArchive}</Button>`));
  assert.ok(source.includes(`>${deficitArchive}</Button>`));
});

test("archive form and submit payload preserve the selected archive type", () => {
  assert.match(source, /archive_type: archiveType, submit/);
  assert.ok(source.includes(`archiveType === "deficit" ? "${deficitArchive}\u7533\u8bf7" : "${normalArchive}\u7533\u8bf7"`));
  assert.match(source, /archiveType === "deficit".*required: true/);
});
