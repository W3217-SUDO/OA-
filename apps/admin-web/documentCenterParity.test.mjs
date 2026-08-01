import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/DocumentCenterPage.tsx", import.meta.url), "utf8");

test("document list keeps query, pagination, upload/download and detail navigation contracts", () => {
  assert.match(source, /api\.get\("\/records"/);
  assert.match(source, /pagination=\{\{[\s\S]*?pageSize: 15/);
  assert.match(source, /onClick=\{\(\) => openDocument\(r\)\}/);
  assert.match(source, /openUpload\(r,/);
  assert.match(source, /api\.get\(`\/attachments\/\$\{row\.id\}\/download`/);
  assert.match(source, /resetOfficialOutgoingSearch/);
  assert.match(source, /searchOfficialOutgoing/);
  assert.match(source, /openAttachmentRecord/);
});
