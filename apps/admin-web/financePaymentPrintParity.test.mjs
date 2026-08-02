import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

test("payment print list reuses the paid-only finance rows", () => {
  const configuredRows = source.match(
    /const configuredRows = useMemo\(\(\) => \{[\s\S]*?\n  \}, \[/,
  );

  assert.ok(configuredRows, "configured finance rows should exist");
  assert.match(
    configuredRows[0],
    /initialView\s*===\s*"finance-payment-print"\s*\?\s*\[\.\.\.originalFinanceRows\]/,
  );
});
