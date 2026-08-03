import assert from "node:assert/strict";
import test from "node:test";
import { buildContractDetailRoute, sortContractObjectLogs } from "./src/contractDetailNavigation.ts";

test("contract detail navigation preserves legacy id routes and supports PreView contract numbers", () => {
  assert.equal(buildContractDetailRoute({ id: 42, serial_no: "HT/2026-0042" }), "contract-detail-42-HT%2F2026-0042");
  assert.equal(buildContractDetailRoute({ serial_no: "HT-ONLY-0042" }), "contract-preview-HT-ONLY-0042");
  assert.equal(buildContractDetailRoute({}), null);
});

test("contract object logs keep legacy newest-log-first order", () => {
  const rows = [
    { id: 2, created_at: "2026-08-01T10:00:00Z" },
    { id: 3, created_at: "2026-08-01T09:00:00Z" },
    { id: 3, created_at: "2026-08-01T11:00:00Z" },
  ];
  assert.deepEqual(sortContractObjectLogs(rows).map((row) => row.id), [3, 3, 2]);
  assert.equal(sortContractObjectLogs(rows)[0].created_at, "2026-08-01T11:00:00Z");
});
