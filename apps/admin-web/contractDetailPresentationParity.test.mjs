import test from "node:test";
import assert from "node:assert/strict";
import {
  normalizeContractApprovalHistory,
  normalizeContractAttachment,
} from "./src/contractWorkflowPolicy.mjs";

test("contract detail maps legacy attachment uploader and upload date fields", () => {
  assert.deepEqual(normalizeContractAttachment({ id: 1, FileName: "合同.pdf", UploadUserName: "alice", UploadTime: "2026-08-01" }), {
    id: 1,
    original_name: "合同.pdf",
    uploader: "alice",
    created_at: "2026-08-01",
  });
  assert.deepEqual(normalizeContractAttachment({ id: 2, original_name: "合同.docx", uploader: "bob", created_at: "2026-08-02" }), {
    id: 2,
    original_name: "合同.docx",
    uploader: "bob",
    created_at: "2026-08-02",
  });
});

test("contract detail maps legacy approval history fields into the local table contract", () => {
  assert.deepEqual(normalizeContractApprovalHistory([{ AuditId: 2, AuditorName: "alice", AuditDate: "2026-08-02", AuditStatus: "通过", AuditContent: "同意" }]), [{
    id: 2,
    approver: "alice",
    acted_at: "2026-08-02",
    status: "通过",
    comment: "同意",
  }]);
  assert.deepEqual(normalizeContractApprovalHistory([{ id: 3, approver: "bob", acted_at: "2026-08-03", status: "待审批", comment: "" }]), [{
    id: 3,
    approver: "bob",
    acted_at: "2026-08-03",
    status: "待审批",
    comment: "",
  }]);
});

test("contract detail keeps empty approval and attachment records safe", () => {
  assert.deepEqual(normalizeContractAttachment(null), { id: 0, original_name: "", uploader: "", created_at: "" });
  assert.deepEqual(normalizeContractApprovalHistory([]), []);
});
