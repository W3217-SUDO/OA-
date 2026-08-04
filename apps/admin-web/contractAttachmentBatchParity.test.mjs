import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

import {
  buildContractAttachmentDeletePlan,
  summarizeContractAttachmentDeleteResults,
} from "./src/contractAttachmentBatch.mjs";

const contractCenterSource = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

test("attachment batch delete deduplicates valid ids without inventing targets", () => {
  assert.deepEqual(buildContractAttachmentDeletePlan([8, "8", 0, -1, "bad", 3]), [8, 3]);
});

test("attachment batch delete keeps per-item server failure messages", () => {
  assert.deepEqual(
    summarizeContractAttachmentDeleteResults([
      { id: 8, status: "fulfilled" },
      { id: 3, status: "rejected", reason: new Error("闄勪欢宸茶閿佸畾") },
      { id: 4, status: "rejected", reason: { response: { data: { detail: "鏃犳潈鍒犻櫎闄勪欢" } } } },
    ]),
    { deleted: 1, failed: [{ id: 3, message: "闄勪欢宸茶閿佸畾" }, { id: 4, message: "鏃犳潈鍒犻櫎闄勪欢" }] },
  );
});

test("contract detail wires real attachment delete calls, refresh, and saving gates", () => {
  assert.match(contractCenterSource, /buildContractAttachmentDeletePlan\(selectedAttachmentKeys\)/);
  assert.match(contractCenterSource, /api\.post\(`\/contracts\/\$\{target\.id\}\/attachments\/delete`, \{ fileIds: deletePlan \}\)/);
  assert.doesNotMatch(contractCenterSource, /Promise\.allSettled\(deletePlan\.map/);
  assert.match(contractCenterSource, /await reloadViewingAttachments\(target\)/);
  assert.match(contractCenterSource, /attachmentBatchSaving/);
  assert.match(contractCenterSource, /rowSelection=\{\{\s*selectedRowKeys:\s*selectedAttachmentKeys/);
});

