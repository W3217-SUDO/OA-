import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  CONTRACT_ATTACHMENT_ACCEPT,
  extractContractErrorMessage,
  normalizeContractActionResponse,
  validateContractAttachment,
} from "./src/contractWorkflowPolicy.mjs";

const contractCenterSource = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

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

test("mutation handlers preserve legacy server messages and keep validation UX", () => {
  assert.equal(extractContractErrorMessage(new Error("旧 PostResponse Message"), "固定失败文案"), "旧 PostResponse Message");
  for (const handler of ["submit", "createContractPayment", "createContractInvoice", "approve"]) {
    const start = contractCenterSource.indexOf(`const ${handler} =`);
    assert.ok(start >= 0, `${handler} handler is wired`);
    const end = contractCenterSource.indexOf("\n  };", start);
    const source = contractCenterSource.slice(start, end < 0 ? undefined : end);
    assert.match(source, /normalizeContractActionResponse\(/);
    assert.match(source, /extractContractErrorMessage\(error/);
  }
  assert.match(contractCenterSource, /if \(error\?\.errorFields\) return;/);
});

const contractObjectHandlerSource = (name) => {
  const start = contractCenterSource.indexOf("const " + name + " =");
  assert.ok(start >= 0, name + " handler is wired");
  const next = contractCenterSource.indexOf("\n  const ", start + 1);
  return contractCenterSource.slice(start, next < 0 ? undefined : next);
};

const topLevelHandlerSource = (name, nextName) => {
  const start = contractCenterSource.indexOf("const " + name + " =");
  assert.ok(start >= 0, name + " handler is wired");
  const next = contractCenterSource.indexOf("\n  const " + nextName + " =", start + 1);
  assert.ok(next > start, nextName + " handler follows " + name);
  return contractCenterSource.slice(start, next);
};

test("contract object save and delete consume legacy PostResponse failures before success UI", () => {
  const saveSource = contractObjectHandlerSource("saveContractObject");
  const deleteSource = contractObjectHandlerSource("deleteContractObject");

  for (const source of [saveSource, deleteSource]) {
    assert.match(source, /normalizeContractActionResponse\(/);
    assert.match(source, /if \(!feedback\.ok\) throw new Error\(feedback\.message\)/);
    assert.ok(
      source.indexOf("normalizeContractActionResponse(") < source.indexOf("message.success("),
      "legacy envelope must be checked before success message",
    );
  }
});

test("contract draft save and archive consume legacy PostResponse failures before success UI", () => {
  const saveSource = topLevelHandlerSource("save", "submitWizard");
  const archiveSource = topLevelHandlerSource("archive", "openInvestigation");

  for (const source of [saveSource, archiveSource]) {
    assert.match(source, /normalizeContractActionResponse\(response,/);
    assert.match(source, /if \(!feedback\.ok\) throw new Error\(feedback\.message\)/);
    assert.ok(
      source.indexOf("normalizeContractActionResponse(response,") < source.indexOf("message.success("),
      "legacy envelope must be checked before success message",
    );
    assert.match(source, /extractContractErrorMessage\(error/);
  }
});

test("contract secondary mutations consume legacy PostResponse failures before success UI", () => {
  const handlers = [
    topLevelHandlerSource("saveChange", "reviewChange"),
    topLevelHandlerSource("revokeDraft", "archive"),
    topLevelHandlerSource("uploadDraftContractAttachment", "uploadViewingAttachment"),
    topLevelHandlerSource("saveApproverSettings", "contractApproverLabel"),
  ];

  for (const source of handlers) {
    assert.match(source, /normalizeContractActionResponse\(response,/);
    assert.match(source, /if \(!feedback\.ok\) throw new Error\(feedback\.message\)/);
    assert.ok(
      source.indexOf("normalizeContractActionResponse(response,") < source.indexOf("message.success("),
      "legacy envelope must be checked before success message",
    );
    assert.match(source, /extractContractErrorMessage\(error/);
  }
});
