import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const page = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("row 2 removes the broken batch ZIP action and keeps per-file download", () => {
  const documentTabStart = page.indexOf('{key:"documents",label:"文档信息"');
  const nextTabStart = page.indexOf('{key:"firm-fees"', documentTabStart);
  const documentTab = page.slice(documentTabStart, nextTabStart);

  assert.ok(documentTabStart >= 0 && nextTabStart > documentTabStart);
  assert.doesNotMatch(documentTab, /下载选中（ZIP）|downloadCounselAttachments/);
  assert.match(
    documentTab,
    /onClick=\{\(\)=>void downloadCounselDetailAttachment\(row\)\}>下载<\/Button>/,
  );
  assert.match(page, /api\.get\(`\/attachments\/\$\{item\.id\}\/download`/);
});
