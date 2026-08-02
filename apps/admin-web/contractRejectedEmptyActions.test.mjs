import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

const source = fs.readFileSync(
  new URL("./src/ContractCenterPage.tsx", import.meta.url),
  "utf8",
);

const auditActions = source.match(
  /\{([^{}\n]+?)\s*&&\s*<div className="contract-bottom-actions"><Space><Button onClick=\{exportExcel\}>导出Excel/,
);

const actionsVisible = (initialView, isAuditView, rows) => {
  assert.ok(auditActions, "contract audit action bar condition must be discoverable");
  return vm.runInNewContext(`Boolean(${auditActions[1]})`, {
    initialView,
    isAuditView,
    rows,
  });
};

test("rejected approval hides its action bar only when the result set is empty", () => {
  assert.equal(actionsVisible("contract-audit-refused", true, []), false);
  assert.equal(actionsVisible("contract-audit-refused", true, [{ id: 1 }]), true);
  assert.equal(actionsVisible("contract-audit-pending", true, []), false);
  assert.equal(actionsVisible("contract-audit-approved", true, []), true);
});
