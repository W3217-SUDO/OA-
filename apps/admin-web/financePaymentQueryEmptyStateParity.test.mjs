import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

test("payment query keeps the legacy empty-state punctuation", () => {
  assert.match(
    source,
    /emptyText:\s*isInternalDetailRoute\s*\|\|\s*isFeeQueryRoute\s*\|\|\s*initialView === "finance-payment-query"[\s\S]*?没有查询到符合条件的记录 。/,
    "payment query empty state should preserve the old site's visible text",
  );
});
