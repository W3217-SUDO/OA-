import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

import { selectContractCurrentApprovalStep } from "./src/contractApprovalCurrentStep.mjs";

const contractCenterSource = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

test("approval detail prefers the backend current_step over a stale pending item", () => {
  const selected = selectContractCurrentApprovalStep({
    current_step: { id: 3, step_order: 2, approver: "bob", status: "审批中" },
    items: [
      { id: 2, step_order: 1, approver: "alice", status: "审批中" },
      { id: 3, step_order: 2, approver: "bob", status: "审批中" },
    ],
  });

  assert.deepEqual(selected, { id: 3, step_order: 2, approver: "bob", status: "审批中" });
});

test("contract review consumes current_step when loading and refreshing approvals", () => {
  assert.match(contractCenterSource, /selectContractCurrentApprovalStep(?:<Step>)?\(data\)/);
  assert.match(contractCenterSource, /selectContractCurrentApprovalStep(?:<Step>)?\(data\)/);
});
