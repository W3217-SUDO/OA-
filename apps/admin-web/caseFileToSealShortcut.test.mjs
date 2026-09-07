import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const pageSource = await readFile(new URL("./src/legal/CaseCenterPage.tsx", import.meta.url), "utf8");
const panelSource = await readFile(new URL("./src/legal/CaseDetail/CaseDocumentsPanel.tsx", import.meta.url), "utf8");
const actionsSource = await readFile(new URL("./src/legal/services/documentsActions.tsx", import.meta.url), "utf8");

test("case document seal shortcut supports Word files in the related document chain", () => {
  const guard = pageSource.slice(
    pageSource.indexOf("const relatedCounselDocumentAttachmentIds"),
    pageSource.indexOf("const handleCounselDocumentMoreAction"),
  );
  assert.match(guard, /counselDetailCustomerAttachments/);
  assert.match(guard, /counselDetailContractAttachments/);
  assert.match(guard, /relatedCounselDocumentAttachmentIds\.has\(item\.id\)/);
  assert.match(guard, /\\\.docx\?\$\/i\.test\(item\.original_name\)/);
  assert.match(panelSource, /canApplySealToCounselAttachment\(row\).*?>申请用印<\/Button>/);
  assert.match(panelSource, /canApplySealToSelectedCounselDocument\?\[\{key:"seal",label:"申请用印"\}\]:\[\]/);
  assert.match(pageSource, /仅当前案件关联文档中的 Word 文件可以申请用印/);
});

test("case document seal shortcut reuses the seal application and submit endpoints", () => {
  const submit = actionsSource.slice(
    actionsSource.indexOf("const submitCounselAttachmentSeal"),
    actionsSource.indexOf("const uploadCounselDetailAttachment"),
  );
  assert.match(submit, /api\.post\("\/seals\/applications"/);
  assert.match(submit, /source_attachment_ids: \[sealingCounselAttachment\.id\]/);
  assert.match(submit, /case_no: viewingCounselCase\.serial_no/);
  assert.match(submit, /`\/seals\/applications\/\$\{response\.data\.id\}\/submit`/);
});
