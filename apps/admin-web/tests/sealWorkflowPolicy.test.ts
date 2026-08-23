import assert from "node:assert/strict";
import test from "node:test";
import {
  canSealAction,
  sealAttachmentTotal,
} from "../src/sealWorkflowPolicy.ts";

test("approval controls only honor backend capabilities", () => {
  assert.equal(canSealAction("approve", { status: "待审批" }), false);
  assert.equal(canSealAction("approve", { status: "草稿", capabilities: { approve: true } }), true);
  assert.equal(canSealAction("reject", { status: "待审批", action_keys: ["reject"] }), true);
  assert.equal(canSealAction("approve", { status: "待审批", action_keys: ["reject"] }), false);
});

test("stamp and archive controls also require backend capabilities", () => {
  assert.equal(canSealAction("stamp", { status: "待用印" }), false);
  assert.equal(canSealAction("stamp", { status: "待用印", capabilities: { stamp: true } }), true);
  assert.equal(canSealAction("archive", { status: "已用印", action_keys: ["archive"] }), true);
});

test("attachment totals prefer the new split-count contract", () => {
  assert.equal(sealAttachmentTotal({ file_count: 1, application_file_count: 2, stamped_file_count: 3 }), 5);
  assert.equal(sealAttachmentTotal({ file_count: 4 }), 4);
  assert.equal(sealAttachmentTotal({ application_file_count: 2 }), 2);
});
