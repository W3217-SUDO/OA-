import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const page = fs.readFileSync("src/SealCenterPage.tsx", "utf8");
const oldController = fs.readFileSync(
  path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    "../../../旧系统归档源码/SH.CRM.WEB/Areas/AWS/Controllers/OfficialDocumentController.cs",
  ),
  "utf8",
);

test("legacy contract creation copied every contract file when no explicit ids were supplied", () => {
  assert.match(
    oldController,
    /CreateByContract[\s\S]*?if \(!string\.IsNullOrEmpty\(contractFileIds\)\)[\s\S]*?else[\s\S]*?GetContractFileListByContractNo\(contractNo\)/,
  );
  assert.match(
    page,
    /选择全部来源附件/,
    "the source attachment picker should retain the legacy copy-all entry",
  );
});

test("copy-all source attachment entry loads every paged item and submits all ids", () => {
  assert.match(
    page,
    /const selectAllSourceAttachments = async[\s\S]*?page_size:[\s\S]*?setSourceAttachmentTotal[\s\S]*?source_attachment_ids/,
    "copy-all should consume paged attachments and bind all selected ids",
  );
  assert.match(
    page,
    /dropdownRender=\{\(menu\) => \([\s\S]*?selectAllSourceAttachments\(\)/,
    "the source picker should expose the copy-all action",
  );
});
