import test from "node:test";
import assert from "node:assert/strict";
import { createContractListRequestGuard } from "./src/contractWorkflowPolicy.mjs";

test("contract list ignores responses from an older query request", () => {
  const guard = createContractListRequestGuard();
  const filteredRequest = guard.begin();
  const clearedRequest = guard.begin();

  assert.equal(guard.isLatest(filteredRequest), false);
  assert.equal(guard.isLatest(clearedRequest), true);
});
