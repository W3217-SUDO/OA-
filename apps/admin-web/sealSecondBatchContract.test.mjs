import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

test("seal second batch exposes upload validation and audit failure fallbacks", () => {
  const source = fs.readFileSync("src/SealCenterPage.tsx", "utf8");
  assert.match(source, /function validateSealUploadFile/);
  assert.match(source, /validateSealUploadFile\(file/);
  assert.match(source, /function sealActionFailureMessage/);
  assert.match(source, /sealActionFailureMessage\(action\.type\)/);
});
