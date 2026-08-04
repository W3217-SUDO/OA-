import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

test("my payment and internal-fee lists retain direct legacy page navigation", () => {
  assert.match(
    source,
    /const paymentQueryQuickJumper = \(initialView: string\) =>\s*\[\s*"finance-payment-query",\s*"finance-payment-mine",\s*"finance-internal-mine",?\s*\]\.includes\(initialView\)[\s\S]*?\?\s*\{\s*goButton: "GO"\s*\}\s*:\s*undefined/,
  );
  assert.match(
    source,
    /showQuickJumper: paymentQueryQuickJumper\(initialView\)/,
  );
  assert.match(
    source,
    /\[\s*"finance-payment-mine",\s*"finance-internal-mine",[\s\S]*?\]\.includes\(initialView\)\s*\? 15/,
  );
});
