import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const helperPath = new URL("./src/caseFileFrontendParity.mjs", import.meta.url);
const helper = await import(helperPath);
const page = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("case file pagination uses the legacy ten-row default", () => {
  const pagination = helper.getCaseFilePagination();
  assert.equal(pagination.defaultPageSize, 10);
  assert.deepEqual(pagination.pageSizeOptions, [10, 20, 50, 100]);
  assert.equal(pagination.showSizeChanger, true);
  assert.equal(pagination.showTotal(12), "共 12 项");
  assert.match(page, /getCaseFilePagination/);
});

test("case file upload rejects absent and empty files before the API", () => {
  assert.equal(helper.getCaseAttachmentUploadValidationError(undefined), "请选择文件进行上传");
  assert.equal(helper.getCaseAttachmentUploadValidationError({ name: "empty.pdf", size: 0 }), "文件没有任何内容");
  assert.equal(helper.getCaseAttachmentUploadValidationError({ name: "ok.pdf", size: 3 }), "");
  assert.match(page, /getCaseAttachmentUploadValidationError/);
});

test("case file rename preserves the legacy empty-name guard without inventing extension locking", () => {
  assert.equal(helper.getCaseFileRenameValidationError("", "old.pdf"), "文件名不能为空且不能包含路径");
  assert.equal(helper.getCaseFileRenameValidationError(".pdf", "old.pdf"), "文件名不能为空且不能包含路径");
  assert.equal(helper.getCaseFileRenameValidationError("folder/new.pdf", "old.pdf"), "文件名不能为空且不能包含路径");
  assert.equal(helper.getCaseFileRenameValidationError("new.docx", "old.pdf"), "");
  assert.equal(helper.getCaseFileRenameValidationError("new.pdf", "old.pdf"), "");
  assert.equal(helper.getCaseFileRenameValidationError("renamed", "legacy"), "");
  assert.equal(helper.getCaseFileRenameValidationError("renamed", "legacy.pdf"), "");
  assert.match(page, /getCaseFileRenameValidationError/);
});

test("case attachment actions require selection and recognize nested categories", () => {
  assert.equal(helper.getCaseAttachmentSelectionValidationError([], "下载"), "请选择需要下载的案件文件");
  assert.equal(helper.getCaseAttachmentSelectionValidationError([8], "下载"), "");
  assert.equal(helper.getCaseAttachmentSelectionValidationError([], "删除"), "请选择需要删除的案件文件");
  const tree = [{ value: "ROOT", label: "Root", code: "ROOT", options: [{ value: "CHILD", label: "Child", code: "CHILD", parent_code: "ROOT" }] }];
  assert.equal(helper.hasCaseFileTypeOption("CHILD", tree), true);
  assert.equal(helper.hasCaseFileTypeOption("MISSING", tree), false);
  assert.match(page, /getCaseAttachmentSelectionValidationError/);
  assert.match(page, /hasCaseFileTypeOption/);
});
