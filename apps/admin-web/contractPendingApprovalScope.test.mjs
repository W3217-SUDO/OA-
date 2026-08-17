import assert from "node:assert/strict";
import test from "node:test";
import { buildContractListRequestParams } from "./src/contractWorkflowPolicy.mjs";

test("pending approval requests server-side current-approver filtering", () => {
  const params = buildContractListRequestParams(
    "contract-audit-pending",
    { current: 1, pageSize: 15 },
  );

  assert.equal(params.scope, "audit");
  assert.equal(params.statuses, "审批中");
  assert.equal(params.pending_approver_only, true);
});
