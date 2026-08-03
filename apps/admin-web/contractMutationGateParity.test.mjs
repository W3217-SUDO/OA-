import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

import { createContractMutationGate } from "./src/contractMutationGate.mjs";

const contractCenterSource = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

test("shared mutation gate rejects synchronous duplicates and releases after finally", () => {
  const gate = createContractMutationGate();
  assert.equal(gate.tryEnter(), true);
  assert.equal(gate.tryEnter(), false);
  gate.leave();
  assert.equal(gate.tryEnter(), true);
});

test("approval, payment, and invoice handlers share the gate before validation and release in finally", () => {
  assert.match(contractCenterSource, /contractMutationGates\.current\.submit\.tryEnter\(\)/);
  assert.match(contractCenterSource, /contractMutationGates\.current\.payment\.tryEnter\(\)/);
  assert.match(contractCenterSource, /contractMutationGates\.current\.invoice\.tryEnter\(\)/);
  assert.match(contractCenterSource, /contractMutationGates\.current\.submit\.leave\(\)/);
  assert.match(contractCenterSource, /contractMutationGates\.current\.payment\.leave\(\)/);
  assert.match(contractCenterSource, /contractMutationGates\.current\.invoice\.leave\(\)/);
});

test("approval, payment, and invoice modals lock cancel and confirm while saving", () => {
  assert.match(contractCenterSource, /submitSaving/);
  assert.match(contractCenterSource, /paymentSaving/);
  assert.match(contractCenterSource, /invoiceSaving/);
  assert.match(contractCenterSource, /confirmLoading=\{submitSaving\}/);
  assert.match(contractCenterSource, /confirmLoading=\{paymentSaving\}/);
  assert.match(contractCenterSource, /confirmLoading=\{invoiceSaving\}/);
  assert.match(contractCenterSource, /closable=\{!submitSaving\}/);
  assert.match(contractCenterSource, /closable=\{!paymentSaving\}/);
  assert.match(contractCenterSource, /closable=\{!invoiceSaving\}/);
});
