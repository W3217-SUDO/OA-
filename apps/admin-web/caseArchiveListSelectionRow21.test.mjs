import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("archive review actions resolve selection from the archive table rows", () => {
  assert.match(
    source,
    /const selectedArchiveCase = originalArchiveRows\.find\(\(row\) => selectedCaseKeySet\.has\(String\(row\.id\)\)\)/,
  );
  assert.match(source, /if \(key === "review"\)[\s\S]*?openArchiveReview\(selectedArchiveCase\)/);
  assert.match(source, /<Button onClick=\{\(\) => \{[\s\S]*?openArchiveReview\(selectedArchiveCase\);[\s\S]*?\}\}>归档审核<\/Button>/);
  assert.doesNotMatch(
    source,
    /originalArchiveMode[\s\S]*?<Table[\s\S]*?setReviewing\(\{ row: selectedCase,/,
  );
});

test("archive table selection and all archive list actions share one source", () => {
  assert.match(
    source,
    /dataSource=\{originalArchiveRows\} rowSelection=\{\{selectedRowKeys:selectedCaseKeys,onChange:setSelectedCaseKeys\}\}/,
  );
  assert.match(source, /selectedArchiveCaseCapability = getCaseCapability\(selectedArchiveCase\)/);
  assert.match(source, /openCaseTasks\(selectedArchiveCase\)/);
  assert.match(source, /openArchive\(selectedArchiveCase\)/);
  assert.match(source, /requestUnarchive\(selectedArchiveCase\)/);
});
