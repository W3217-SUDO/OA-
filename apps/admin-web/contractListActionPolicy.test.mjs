import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { contractListActionPolicy } from "./src/contractWorkflowPolicy.mjs";

const contractSource = await readFile(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

test("contract list keeps legacy payment and invoice status gates", () => {
  assert.deepEqual(contractListActionPolicy("已通过"), { canPayment: true, canInvoice: true, canCreateCase: true });
  assert.deepEqual(contractListActionPolicy("审批中"), { canPayment: false, canInvoice: true, canCreateCase: true });
  assert.deepEqual(contractListActionPolicy("已归档"), { canPayment: false, canInvoice: false, canCreateCase: false });
});

test("contract list status policy accepts legacy A and local approved labels", () => {
  assert.equal(contractListActionPolicy("A").canPayment, true);
  assert.equal(contractListActionPolicy("Approved").canPayment, true);
  assert.equal(contractListActionPolicy("R").canPayment, false);
});

test("contract toolbar exposes guarded recycle deletion", () => {
  assert.match(contractSource, /deleteRecycledContract/);
  assert.match(contractSource, /selected\.status !== "已回收"/);
  assert.match(contractSource, /api\.post\("\/contracts\/delete", \{ contract_ids: \[contract\.id\] \}\)/);
});
