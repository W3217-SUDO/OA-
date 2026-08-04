import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

test("contract list keeps a guarded legacy delete entry for draft contracts", () => {
  const actionsStart = source.indexOf('{!isAuditView && <div className="contract-bottom-actions">');
  const auditActionsStart = source.indexOf('{isAuditView', actionsStart + 1);
  assert.ok(actionsStart >= 0 && auditActionsStart > actionsStart);

  const actions = source.slice(actionsStart, auditActionsStart);
  assert.match(actions, />撤销草稿<\/Button>/);
  assert.match(actions, /disabled=\{!selected \|\| selected\.status !== "草稿"\}/);
  assert.match(actions, /onClick=\{\(\)=>needSelected\(\(\)=>revokeDraft\(selected!\)\)\}/);
});
