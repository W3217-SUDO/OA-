import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("case attachments show the resolved person name", () => {
  assert.match(source, /type AttachmentRow = \{[^}]*uploader_display_name\?:string/);
  assert.match(source, /row\.uploader_display_name\s*\|\|\s*row\.uploader\s*\|\|\s*"—"/);
});

test("case attachments format the preserved upload timestamp", () => {
  assert.match(source, /title:"上传时间",dataIndex:"created_at"/);
  assert.match(source, /dayjs\(value\)\.format\("YYYY-MM-DD HH:mm:ss"\)/);
});
