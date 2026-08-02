import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

test("seal third batch wires selection guards and permission-aware failure semantics", () => {
  const source = fs.readFileSync("src/SealCenterPage.tsx", "utf8");
  assert.match(source, /function sealAttachmentDeleteFailureMessage/);
  assert.match(source, /function sealPackageDownloadFailureMessage/);
  assert.match(source, /请选择用印文件/);
  assert.match(source, /setSelectedKeys\(\[\]\)/);
  assert.match(source, /sealAttachmentDeleteFailureMessage\(/);
  assert.match(source, /sealPackageDownloadFailureMessage\(/);
  assert.match(source, /initialView === "seal-admin-pending"/);
  assert.match(source, /type: "stamp"/);
});
