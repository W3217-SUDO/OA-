import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("case document seal shortcut is limited to a Word file owned by the current case", () => {
  const guard = source.slice(
    source.indexOf("const canApplySealToCounselAttachment"),
    source.indexOf("const handleCounselDocumentMoreAction"),
  );
  assert.match(guard, /item\.record_id === viewingCounselCase\?\.id/);
  assert.match(guard, /\\\.docx\?\$\/i\.test\(item\.original_name\)/);
  assert.match(source, /canApplySealToCounselAttachment\(row\).*?>申请用印<\/Button>/);
  assert.match(source, /canApplySealToSelectedCounselDocument\?\[\{key:"seal",label:"申请用印"\}\]:\[\]/);
  assert.match(source, /仅案件中的 Word 文件可以申请用印/);
});

test("case document seal shortcut reuses the seal application and submit endpoints", () => {
  const submit = source.slice(
    source.indexOf("const submitCounselAttachmentSeal"),
    source.indexOf("const uploadCounselDetailAttachment"),
  );
  assert.match(submit, /api\.post\("\/seals\/applications"/);
  assert.match(submit, /source_attachment_ids: \[sealingCounselAttachment\.id\]/);
  assert.match(submit, /case_no: viewingCounselCase\.serial_no/);
  assert.match(submit, /`\/seals\/applications\/\$\{response\.data\.id\}\/submit`/);
});
