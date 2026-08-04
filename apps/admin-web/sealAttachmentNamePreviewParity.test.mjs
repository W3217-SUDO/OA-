import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync("src/SealCenterPage.tsx", "utf8");

test("seal detail file names keep the legacy direct-preview entry", () => {
  const attachmentTableStart = source.indexOf("dataSource={attachments}");
  assert.notEqual(attachmentTableStart, -1, "seal attachment table should exist");

  const nameColumnStart = source.indexOf('dataIndex: "original_name"', attachmentTableStart);
  assert.notEqual(nameColumnStart, -1, "attachment name column should exist");
  const nameColumn = source.slice(nameColumnStart, nameColumnStart + 650);

  assert.match(
    nameColumn,
    /render:\s*\(value:\s*string,\s*item:\s*AttachmentRow\)\s*=>\s*\([\s\S]*?<Button\s+type="link"\s+onClick=\{\(\)\s*=>\s*void previewAttachment\(item\)\}/,
    "legacy file-name preview should remain available directly from the attachment name",
  );
  assert.match(nameColumn, /\{value\}/, "the direct preview button should preserve the real file name");
});
