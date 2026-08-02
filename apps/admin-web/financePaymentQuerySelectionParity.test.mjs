import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

test("payment query exposes legacy header and row selection", () => {
  const start = source.indexOf("rowSelection={");
  const end = source.indexOf("selectedRowKeys:", start);
  assert.notEqual(start, -1, "finance table row selection should be configured");
  assert.notEqual(end, -1, "finance table selection state should be wired");

  const selectionGate = source.slice(start, end);
  assert.match(
    selectionGate,
    /initialView === "finance-payment-query"/,
    "payment query must opt into the same checkbox column as the legacy list",
  );
});

test("payment query selection keeps selected row keys and clears them on page-size changes", () => {
  assert.match(
    source,
    /selectedRowKeys:\s*selectedOriginalRows[\s\S]*?onChange:\s*\(keys\) =>[\s\S]*?setSelectedOriginalRows\(/,
    "payment query checkboxes should use the shared selected-row state",
  );
  assert.match(
    source,
    /initialView === "finance-payment-query"[\s\S]*?onShowSizeChange:[\s\S]*?setSelectedOriginalRows\(\[\]\)/,
    "changing the payment query page size should clear stale selections",
  );
});
