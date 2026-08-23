import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

test("seal file-count column uses attachment count and opens file list", () => {
  const source = fs.readFileSync("src/SealCenterPage.tsx", "utf8");
  assert.match(source, /dataIndex: "file_count"/);
  assert.match(source, /openFileList\(r\)/);
  assert.match(source, /title="文件列表"/);
});

test("seal list exposes direct file-name preview entry beside file count", () => {
  const source = fs.readFileSync("src/SealCenterPage.tsx", "utf8");
  const fileCountColumn = source.slice(
    source.indexOf('title: "文件数"'),
    source.indexOf('title: "案号"'),
  );

  assert.match(source, /Popover/);
  assert.match(source, /function listSealRowFileNames|const listSealRowFileNames/);
  assert.match(source, /const previewListAttachmentByName = async/);
  assert.match(fileCountColumn, /listSealRowFileNames\(r\)/);
  assert.match(fileCountColumn, /sealAttachmentListLabel/);
  assert.match(fileCountColumn, /previewListAttachmentByName\(r, name\)/);
  assert.match(source, /previewAttachment\(target\)/);
  assert.match(source, /openFileList\(row\)/);
});
