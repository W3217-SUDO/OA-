import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { createFinanceActionGate } from "./src/financeActionGate.mjs";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

const functionBody = (name, nextName) => {
  const start = source.indexOf(`const ${name}`);
  const end = source.indexOf(`const ${nextName}`, start);
  assert.ok(start >= 0 && end > start, `${name} should exist`);
  return source.slice(start, end);
};

test("finance action gate is synchronous and reusable after leave", () => {
  const gate = createFinanceActionGate();
  assert.equal(gate.tryEnter(), true);
  assert.equal(gate.tryEnter(), false);
  gate.leave();
  assert.equal(gate.tryEnter(), true);
  gate.leave();
});

test("finance component persists three independent action scopes", () => {
  assert.match(source, /useMemo\s*\(\s*\(\)\s*=>\s*\(\{[\s\S]*archiveSettlement: createFinanceActionGate\(\)[\s\S]*generalSettlement: createFinanceActionGate\(\)[\s\S]*paymentPackage: createFinanceActionGate\(\)/);
  assert.match(source, /from "\.\/financeActionGate\.mjs"/);
});

test("archive mutations use the synchronous gate and always leave", () => {
  for (const [name, next] of [
    ["exportPendingArchiveSettlements", "openArchiveSettlementReview"],
    ["submitArchiveSettlementReview", "openArchiveSettlementRollback"],
    ["submitArchiveSettlementRollback", "openArchiveSettlementReapply"],
    ["submitArchiveSettlementReapply", "applyGeneralSettlementRows"],
  ]) {
    const body = functionBody(name, next);
    assert.match(body, /financeActionGates\.archiveSettlement\.tryEnter\(\)/);
    assert.match(body, /finally[\s\S]*financeActionGates\.archiveSettlement\.leave\(\)/);
    assert.doesNotMatch(body, /if \(archiveSettlementBusy\) return/);
  }
});

test("general settlement mutations use the synchronous gate and always leave", () => {
  for (const [name, next] of [
    ["submitGeneralSettlementReview", "openGeneralSettlementPayment"],
    ["submitGeneralSettlementPayment", "openGeneralSettlementReapply"],
    ["submitGeneralSettlementReapply", "configuredRows"],
  ]) {
    const body = functionBody(name, next);
    assert.match(body, /financeActionGates\.generalSettlement\.tryEnter\(\)/);
    assert.match(body, /finally[\s\S]*financeActionGates\.generalSettlement\.leave\(\)/);
    assert.doesNotMatch(body, /if \(generalSettlementBusy\) return/);
  }
});

test("payment package mutations gate only after validation and always leave", () => {
  for (const [name, next] of [
    ["previewInternalPaymentPackage", "submitInternalPaymentPackage"],
    ["submitInternalPaymentPackage", "configuredDefaults"],
    ["writeoffPaymentPackage", "exportPendingArchiveSettlements"],
  ]) {
    const body = functionBody(name, next);
    assert.match(body, /financeActionGates\.paymentPackage\.tryEnter\(\)/);
    assert.match(body, /finally[\s\S]*financeActionGates\.paymentPackage\.leave\(\)/);
    assert.doesNotMatch(body, /if \(paymentPackageLoading\) return/);
  }
  const preview = functionBody("previewInternalPaymentPackage", "submitInternalPaymentPackage");
  assert.ok(preview.indexOf("payees.size") < preview.indexOf("tryEnter"));
  const writeoff = functionBody("writeoffPaymentPackage", "exportPendingArchiveSettlements");
  assert.ok(writeoff.indexOf("validateFields") < writeoff.indexOf("tryEnter"));
});
