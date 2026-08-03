import test from "node:test";
import assert from "node:assert/strict";
import {
  CONTRACT_ATTACHMENT_ACCEPT,
  normalizeContractActionResponse,
  validateContractAttachment,
} from "./src/contractWorkflowPolicy.mjs";

test("contract attachment inputs retain the legacy accepted file formats and validation", () => {
  for (const extension of [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".png", ".jpg", ".jpeg", ".zip", ".rar"]) {
    assert.ok(CONTRACT_ATTACHMENT_ACCEPT.split(",").includes(extension));
  }
  assert.equal(validateContractAttachment(null), "请选择合同附件");
  assert.equal(validateContractAttachment({ size: 0 }), "文件没有任何内容");
  assert.equal(validateContractAttachment({ size: 1024 }), null);
});

test("contract action feedback accepts current and legacy PostResponse success shapes", () => {
  assert.deepEqual(normalizeContractActionResponse({ data: { IsSuccess: true, Message: "上传成功！" } }, "上传失败"), { ok: true, message: "上传成功！" });
  assert.deepEqual(normalizeContractActionResponse({ data: { is_success: true, message: "审批成功！" } }, "审批失败"), { ok: true, message: "审批成功！" });
});

test("contract action feedback keeps server failure messages instead of hiding them behind HTTP fallbacks", () => {
  assert.deepEqual(normalizeContractActionResponse({ data: { IsSuccess: false, Message: "上传文件类型不正确,上传失败！" } }, "上传失败"), { ok: false, message: "上传文件类型不正确,上传失败！" });
  assert.deepEqual(normalizeContractActionResponse({ data: { is_success: false, message: "审核失败！" } }, "审批失败"), { ok: false, message: "审核失败！" });
});

test("contract action feedback treats ordinary local resource responses as successful", () => {
  assert.deepEqual(normalizeContractActionResponse({ data: { id: 42 } }, "操作失败"), { ok: true, message: "操作失败" });
});
