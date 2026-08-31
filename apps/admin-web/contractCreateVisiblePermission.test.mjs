import assert from "node:assert/strict";
import test from "node:test";

import { contractWorkflowActionPolicy } from "./src/contractWorkflowPolicy.mjs";

test("visible contract workbenches do not require granular action grants", () => {
  const visibleCreator = {
    role: "user",
    username: "creator",
    menu_keys: ["contract-new"],
    action_keys: [],
  };

  assert.equal(contractWorkflowActionPolicy(visibleCreator).canCreate, true);
  assert.equal(contractWorkflowActionPolicy({ ...visibleCreator, menu_keys: ["contract-mine"] }, { status: "草稿" }).canEdit, true);
  assert.equal(contractWorkflowActionPolicy({ ...visibleCreator, menu_keys: ["contract-mine"] }, { status: "草稿" }).canSubmit, true);
  assert.equal(contractWorkflowActionPolicy({ ...visibleCreator, menu_keys: ["user-center"] }).canCreate, false);
  assert.equal(contractWorkflowActionPolicy({ role: "admin" }).canCreate, true);
});
