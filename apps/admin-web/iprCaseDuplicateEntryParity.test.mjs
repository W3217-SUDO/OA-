import assert from "node:assert/strict";
import fs from "node:fs";

const page = fs.readFileSync(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");

assert.match(
  page,
  /const\s+openCopy\s*=\s*\(record:\s*IprRecord\)\s*=>\s*\{[\s\S]*?setEditing\(null\);[\s\S]*?setCreateOpen\(true\);/,
  "IPR detail should expose a copy action that opens a fresh create form.",
);
assert.match(
  page,
  /onClick=\{\(\)\s*=>\s*openCopy\(detail\)\}[\s\S]*?\u590d\u5236\u6848\u4ef6/,
  "IPR detail actions should include the legacy copy-case entry.",
);
assert.match(
  page,
  /await api\.post\("\/ipr\/cases", payload\)/,
  "The copy entry should reuse the existing IPR create API after editing the new draft.",
);

console.log("ipr case duplicate entry parity: PASS");
