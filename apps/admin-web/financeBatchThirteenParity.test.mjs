import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import {
  createLatestRequestGuard,
  refundFallbackPage,
  refreshRefundListWithFallback,
} from "./src/financeRefundHelpers.mjs";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

test("latest refund request guard lets fast B win over slow A", () => {
  const guard = createLatestRequestGuard();
  const slowA = guard.begin();
  const fastB = guard.begin();
  assert.equal(guard.isLatest(fastB), true);
  assert.equal(guard.isLatest(slowA), false);
});

test("refund fallback page targets the last legal server page after migration", () => {
  assert.equal(
    refundFallbackPage({ requestedPage: 4, pageSize: 15, total: 31, items: [] }),
    3,
  );
  assert.equal(
    refundFallbackPage({ requestedPage: 3, pageSize: 15, total: 31, items: [] }),
    3,
  );
  assert.equal(
    refundFallbackPage({ requestedPage: 2, pageSize: 15, total: 31, items: [{ id: 1 }] }),
    null,
  );
});

test("refund pagination and page-size changes retain status and business group", () => {
  assert.match(source, /loadRefunds\(\s*1,\s*size,\s*refundStatusFilter,\s*true,\s*refundGroupFilter/);
  assert.match(source, /loadRefunds\(\s*page,\s*size,\s*refundStatusFilter,\s*true,\s*refundGroupFilter/);
});

test("refund loader ignores stale responses and refresh retries one bounded fallback page", () => {
  assert.match(source, /const refundRequestGuard = useMemo\(\(\) => createLatestRequestGuard\(\), \[\]\)/);
  assert.match(source, /const requestToken = refundRequestGuard\.begin\(\)/);
  assert.match(source, /if \(!refundRequestGuard\.isLatest\(requestToken\)\)/);
  assert.match(source, /return \{ applied: false, response: null \};/);
  assert.match(source, /return refreshRefundListWithFallback\(\{/);
});

test("stale refresh results do not schedule a fallback request", async () => {
  const calls = [];
  const result = await refreshRefundListWithFallback({
    load: async (...args) => {
      calls.push(args);
      return { applied: false, response: { data: { total: 31, items: [] } } };
    },
    page: 4,
    pageSize: 15,
    status: "pending",
    group: "Lawfirm",
  });
  assert.equal(result.applied, false);
  assert.equal(calls.length, 1);
});

test("fast B refresh remains final while slow A cannot trigger a retry", async () => {
  const guard = createLatestRequestGuard();
  const calls = [];
  let resolveA;
  let resolveB;
  const aGate = new Promise((resolve) => { resolveA = resolve; });
  const bGate = new Promise((resolve) => { resolveB = resolve; });
  const load = async (...args) => {
    calls.push(args);
    const token = guard.begin();
    const response = args[0] === 4
      ? await aGate
      : await bGate;
    return {
      applied: guard.isLatest(token),
      response,
    };
  };
  const slowA = refreshRefundListWithFallback({
    load,
    page: 4,
    pageSize: 15,
    status: "pending",
    group: "Lawfirm",
  });
  const fastB = refreshRefundListWithFallback({
    load,
    page: 2,
    pageSize: 15,
    status: "paid",
    group: "Trad",
  });
  resolveB({ data: { total: 16, items: [{ id: 2 }] } });
  const finalB = await fastB;
  resolveA({ data: { total: 31, items: [] } });
  const staleA = await slowA;
  assert.equal(finalB.applied, true);
  assert.equal(staleA.applied, false);
  assert.equal(calls.length, 2);
});
