import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("row 24 case-file seal action uses the shared seal application workflow in-place", () => {
  const submit = source.slice(source.indexOf("const submitCounselAttachmentSeal"), source.indexOf("const uploadCounselDetailAttachment"));
  assert.match(submit, /api\.post\("\/seals\/applications"/);
  assert.match(submit, /use_type: "案件用印"/);
  assert.match(submit, /source_attachment_ids: \[sealingCounselAttachment\.id\]/);
  assert.match(submit, /`\/seals\/applications\/\$\{response\.data\.id\}\/submit`/);
  assert.doesNotMatch(submit, /official-outgoing/);
  assert.match(source, /title="用印申请"/);
  for (const label of ["案件号", "合同号", "客户名称", "选择印章", "计划用印日期", "用印份数", "办理方式", "是否电子印章", "是否打印盖章", "用印事由", "用印备注", "附件"]) {
    assert.match(source, new RegExp(`label="${label}"`));
  }
});
