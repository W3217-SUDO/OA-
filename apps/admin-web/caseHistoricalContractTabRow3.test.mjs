import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const caseSource = await readFile(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const contractSource = await readFile(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");
const customerSource = await readFile(new URL("./src/CustomerCenterPage.tsx", import.meta.url), "utf8");

test("case detail no longer exposes the historical contract tab", () => {
  assert.doesNotMatch(caseSource, /LegacyContractHistoryPanel/);
  assert.doesNotMatch(caseSource, /key:\s*["']legacy-contract-history["']/);
  assert.doesNotMatch(caseSource, /label:\s*["']历史合同["']/);
});

test("historical contract tools remain available in contract and customer details", () => {
  assert.match(contractSource, /LegacyContractHistoryPanel/);
  assert.match(contractSource, /key:\s*["']legacy-contract-history["']/);
  assert.match(customerSource, /LegacyContractHistoryPanel/);
  assert.match(customerSource, /key:\s*["']legacy-contract-history["']/);
});
