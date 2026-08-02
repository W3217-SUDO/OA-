import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

import {
  contractAuditActionPolicy,
  contractAuditViewConfig,
  normalizeContractDetailReturnView,
} from "./src/contractWorkflowPolicy.mjs";

const pageSource = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

test("audit action policy keeps approval operations on pending views only", () => {
  assert.deepEqual(contractAuditActionPolicy("contract-audit"), { canReview: true, canReviewChange: true, canExport: true });
  assert.deepEqual(contractAuditActionPolicy("contract-audit-pending"), { canReview: true, canReviewChange: true, canExport: true });
  assert.deepEqual(contractAuditActionPolicy("contract-audit-refused"), { canReview: false, canReviewChange: false, canExport: true });
  assert.deepEqual(contractAuditActionPolicy("contract-audit-approved"), { canReview: false, canReviewChange: false, canExport: true });
});

test("detail return context accepts only known contract list routes", () => {
  assert.equal(normalizeContractDetailReturnView("contract-mine"), "contract-mine");
  assert.equal(normalizeContractDetailReturnView("contract-audit-pending"), "contract-audit-pending");
  assert.equal(normalizeContractDetailReturnView("contract-detail-7-HT7"), "contract-mine");
  assert.equal(normalizeContractDetailReturnView("contract-unknown"), "contract-mine");
  assert.equal(normalizeContractDetailReturnView(""), "contract-mine");
});

test("contract center uses the policy for audit actions and detail return", () => {
  assert.match(pageSource, /contractAuditActionPolicy\(initialView\)/);
  assert.match(pageSource, /contractAuditViewConfig\(initialView\)/);
  assert.match(pageSource, /auditViewConfig\.statuses\.includes\(x\.status\)/);
  assert.match(pageSource, /auditActionPolicy\.canReview/);
  assert.match(pageSource, /auditActionPolicy\.canReviewChange/);
  assert.match(pageSource, /normalizeContractDetailReturnView\(view\)/);
});

test("audit view config preserves the legacy status matrix", () => {
  assert.deepEqual(contractAuditViewConfig("contract-audit-pending").statuses, ["审批中"]);
  assert.deepEqual(contractAuditViewConfig("contract-audit-refused").statuses, ["已拒绝", "已驳回"]);
  assert.deepEqual(contractAuditViewConfig("contract-audit-approved").statuses, ["已通过", "履行中", "已完成", "已归档"]);
  assert.deepEqual(contractAuditViewConfig("contract-audit").statuses, []);
});
