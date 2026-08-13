import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

const source = readFileSync(resolve(import.meta.dirname, "src/CaseCenterPage.tsx"), "utf8");

test("row 22 exposes upload action in an empty case document list", () => {
  assert.match(source, /locale=\{\{emptyText:<Space direction="vertical"/);
  assert.match(source, /没有查到文档。/);
  assert.match(source, /counselDetailCapabilities\.can_upload_attachment&&<Button type="primary" onClick=\{\(\)=>counselDetailUploadRef\.current\?\.click\(\)\}>上传文件<\/Button>/);
});
