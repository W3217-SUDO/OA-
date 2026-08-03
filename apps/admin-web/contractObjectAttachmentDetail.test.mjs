import test from "node:test";
import assert from "node:assert/strict";
import {
  contractAttachmentActionPolicy,
  validateContractAttachment,
} from "./src/contractWorkflowPolicy.mjs";
import { contractObjectActionPolicy } from "./src/contractObjectPresentation.mjs";

test("contract detail keeps object writes and attachment writes locked by status", () => {
  assert.deepEqual(contractObjectActionPolicy("审批中"), { canEdit: false, canDelete: false, canLog: true });
  assert.deepEqual(contractObjectActionPolicy("草稿"), { canEdit: true, canDelete: true, canLog: true });
  assert.deepEqual(contractAttachmentActionPolicy("已归档"), { canUpload: false, canDelete: false, canDownload: true, canPreview: true });
  assert.deepEqual(contractAttachmentActionPolicy("草稿"), { canUpload: true, canDelete: true, canDownload: true, canPreview: true });
});

test("contract detail attachment validation rejects invalid files and accepts a valid file", () => {
  assert.equal(validateContractAttachment(null), "请选择合同附件");
  assert.equal(validateContractAttachment({ size: 0 }), "文件没有任何内容");
  assert.equal(validateContractAttachment({ size: 21 * 1024 * 1024 }), "单个文件不能超过 20MB");
  assert.equal(validateContractAttachment({ size: 1, name: "contract.pdf" }), null);
});
