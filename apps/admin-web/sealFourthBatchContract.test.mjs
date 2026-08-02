import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

test("seal fourth batch gives download and preview permission-aware failures", () => {
  const source = fs.readFileSync("src/SealCenterPage.tsx", "utf8");
  assert.match(source, /function sealAttachmentDownloadFailureMessage/);
  assert.match(source, /function sealAttachmentPreviewFailureMessage/);
  assert.match(source, /sealAttachmentDownloadFailureMessage\(/);
  assert.match(source, /sealAttachmentPreviewFailureMessage\(/);
  assert.match(source, /label:\s*["`]行政用印/);
  assert.match(source, /label:\s*["`]用印审批/);
  assert.match(source, /setSelectedKeys\(\[\]\)/);
});
