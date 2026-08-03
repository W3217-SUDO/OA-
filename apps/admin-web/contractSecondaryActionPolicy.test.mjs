import test from "node:test";
import assert from "node:assert/strict";
import { contractSecondaryActionPolicy } from "./src/contractWorkflowPolicy.mjs";

test("legacy contract secondary actions reject archived records", () => {
  assert.deepEqual(contractSecondaryActionPolicy("已归档"), {
    canEdit: false,
    canInvestigation: false,
    canArchive: false,
  });
  assert.deepEqual(contractSecondaryActionPolicy("Archived"), {
    canEdit: false,
    canInvestigation: false,
    canArchive: false,
  });
});

test("legacy contract secondary actions remain available before archive", () => {
  assert.deepEqual(contractSecondaryActionPolicy("审批中"), {
    canEdit: true,
    canInvestigation: true,
    canArchive: true,
  });
});
