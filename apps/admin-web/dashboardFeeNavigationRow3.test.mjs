import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

import {
  clearDashboardFeeQuery,
  consumeDashboardFeeQuery,
  preserveDashboardFeeQueryContext,
  rememberDashboardFeeQuery,
} from "./src/dashboardFeeNavigation.mjs";

function storage() {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) ?? null,
    removeItem: (key) => values.delete(key),
    setItem: (key, value) => values.set(key, value),
  };
}

test("dashboard unpaid official fee navigation keeps the legacy hidden query", () => {
  const session = storage();
  rememberDashboardFeeQuery({ scope: "mine", unpaid_official: true }, session);
  const query = consumeDashboardFeeQuery("finance-fee-query", session);
  assert.deepEqual(query, {
    dashboardScope: "mine",
    dashboardUnpaidOfficial: true,
  });
  assert.deepEqual(preserveDashboardFeeQueryContext(query), query);
  assert.deepEqual(consumeDashboardFeeQuery("finance-fee-query", session), query);
  clearDashboardFeeQuery(session);
  assert.deepEqual(consumeDashboardFeeQuery("finance-fee-query", session), {});
});

test("fee query renders missing people as a dash, never as a fabricated name", () => {
  const source = fs.readFileSync(new URL("./src/FinanceCenterPage.tsx", import.meta.url), "utf8");
  assert.match(
    source,
    /isFeeQueryRoute\s*\?\s*dashboardFeeQuerySeed\s*:\s*\{\}/,
    "the fee query initialization must retain the dashboard seed so Clear cannot drop the hidden scope",
  );
  assert.match(source, /if \(!key\) return "—"/);
  assert.doesNotMatch(source.slice(source.indexOf("const financePersonDisplayName"), source.indexOf("const [originalQueryDraft")), /姓名待维护/);
});
