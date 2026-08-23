import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("case actions accept equivalent numeric and string table keys", () => {
  assert.match(source, /new Set\(selectedCaseKeys\.map\(\(key\) => String\(key\)\)\)/);
  assert.match(source, /selectedArchiveCase = originalArchiveRows\.find\(\(row\) => selectedCaseKeySet\.has\(String\(row\.id\)\)\)/);
  assert.doesNotMatch(source, /selectedCaseKeys\.includes\(row\.id\)/);
});
