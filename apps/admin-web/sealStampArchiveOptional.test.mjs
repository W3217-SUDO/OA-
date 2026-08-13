import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const page = fs.readFileSync("src/SealCenterPage.tsx", "utf8");

test("actual seal registration does not require an archive number", () => {
  const single = page.match(/name="archive_no"[\s\S]{0,180}?<Input placeholder=/g) || [];
  assert.equal(single.length, 2, "single and batch stamp forms must both expose archive_no");
  for (const field of single) assert.doesNotMatch(field, /required:\s*true/);
});
