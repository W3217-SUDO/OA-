import assert from "node:assert/strict";
import test from "node:test";

test("pending approval shows only contracts assigned to the current approver", async () => {
  let filterPendingContractApprovals;
  try {
    ({ filterPendingContractApprovals } = await import("./src/contractAuditScope.ts"));
  } catch {
    // RED until the production scope rule exists.
  }

  assert.equal(typeof filterPendingContractApprovals, "function");

  const contracts = [
    {
      id: 1,
      status: "审批中",
      data: {},
    },
    {
      id: 2,
      status: "审批中",
      data: { current_approver: "admin" },
    },
    {
      id: 3,
      status: "审批中",
      data: { current_approver: "other" },
    },
    {
      id: 4,
      status: "已通过",
      data: { current_approver: "admin" },
    },
  ];

  assert.deepEqual(
    filterPendingContractApprovals(contracts, "admin").map((item) => item.id),
    [2],
  );
});
