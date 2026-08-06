import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import {
  normalizeContractApprovalHistory,
  normalizeContractAttachment,
} from "./src/contractWorkflowPolicy.mjs";

const pageSource = await readFile(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

test("contract detail maps legacy attachment uploader and upload date fields", () => {
  assert.deepEqual(normalizeContractAttachment({ id: 1, FileName: "合同.pdf", UploadUserName: "alice", UploadTime: "2026-08-01" }), {
    id: 1,
    original_name: "合同.pdf",
    uploader: "alice",
    uploader_display_name: "",
    created_at: "2026-08-01",
  });
  assert.deepEqual(normalizeContractAttachment({ id: 2, original_name: "合同.docx", uploader: "bob", created_at: "2026-08-02" }), {
    id: 2,
    original_name: "合同.docx",
    uploader: "bob",
    uploader_display_name: "",
    created_at: "2026-08-02",
  });
});

test("contract detail maps legacy approval history fields into the local table contract", () => {
  assert.deepEqual(normalizeContractApprovalHistory([{ AuditId: 2, AuditorName: "alice", AuditDate: "2026-08-02", AuditStatus: "通过", AuditContent: "同意" }]), [{
    id: 2,
    approver: "alice",
    approver_display_name: "",
    acted_at: "2026-08-02",
    status: "通过",
    comment: "同意",
  }]);
  assert.deepEqual(normalizeContractApprovalHistory([{ id: 3, approver: "bob", acted_at: "2026-08-03", status: "待审批", comment: "" }]), [{
    id: 3,
    approver: "bob",
    approver_display_name: "",
    acted_at: "2026-08-03",
    status: "待审批",
    comment: "",
  }]);
});

test("contract detail keeps empty approval and attachment records safe", () => {
  assert.deepEqual(normalizeContractAttachment(null), { id: 0, original_name: "", uploader: "", uploader_display_name: "", created_at: "" });
  assert.deepEqual(normalizeContractApprovalHistory([]), []);
});

test("contract page no longer exposes the approver settings button in the contract workflow", () => {
  assert.doesNotMatch(pageSource, /设置审批人/);
});

test("contract creation wizard exposes the legacy four-step approval and seal flow", () => {
  assert.match(
    pageSource,
    /CONTRACT_CREATE_STEP_TITLES = \["合同基本信息", "提交审批", "合同审批", "合同用印"\]/,
  );
  assert.match(pageSource, /wizardStep === 2/);
  assert.match(pageSource, /wizardStep === 3/);
  assert.match(pageSource, /wizardStep < CONTRACT_CREATE_STEP_TITLES\.length/);
  assert.doesNotMatch(pageSource, /\["①", "②"\]\[index\]/);
});
