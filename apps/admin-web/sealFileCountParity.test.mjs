import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

test("seal file-count column uses attachment count and opens file list", () => {
  const source = fs.readFileSync("src/SealCenterPage.tsx", "utf8");
  assert.match(source, /dataIndex: "file_count"/);
  assert.match(source, /openFileList\(r\)/);
  assert.match(source, /title="文件列表"/);
});
