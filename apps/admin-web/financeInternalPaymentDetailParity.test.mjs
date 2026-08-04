import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

test("internal pending-payment rows expose the legacy detail action", () => {
  const routeStart = source.indexOf('"finance-internal-payment": {');
  const routeEnd = source.indexOf('...Object.fromEntries(', routeStart);
  assert.ok(routeStart >= 0 && routeEnd > routeStart, "internal payment route config should exist");
  assert.match(source.slice(routeStart, routeEnd), /"操作"/);

  const operationStart = source.indexOf("const originalOperation =");
  const operationEnd = source.indexOf("const openGeneralSettlementReview =", operationStart);
  assert.ok(operationStart >= 0 && operationEnd > operationStart, "finance operation renderer should exist");
  const operations = source.slice(operationStart, operationEnd);
  assert.match(
    operations,
    /initialView === "finance-internal-payment"[\s\S]*?openPaymentDetail\(row\)/,
  );
});
