import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

test("payment query filters always reload from page one with server metadata", () => {
  assert.match(
    source,
    /if \(initialView === "finance-payment-query"\) \{[\s\S]*?loadPaymentQueryPage\(next, 1, paymentQueryPageSize\)/,
    "submitting a payment query should reset the server page before filtering",
  );
});

test("clearing payment query filters restores page one and total", () => {
  assert.match(
    source,
    /if \(initialView === "finance-payment-query"\) \{[\s\S]*?loadPaymentQueryPage\(\{\}, 1, paymentQueryPageSize\)/,
    "clearing a payment query should reload the first server page",
  );
});
