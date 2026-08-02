import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

test("pending payment list keeps the legacy selectable checkbox column", () => {
  const rowSelection = source.match(
    /rowSelection=\{[\s\S]*?\n                \}/,
  );

  assert.ok(rowSelection, "finance table row selection should exist");
  assert.match(
    rowSelection[0],
    /initialView\s*===\s*"finance-payment-waiting"/,
  );
  assert.match(
    rowSelection[0],
    /getTitleCheckboxProps:[\s\S]*?initialView\s*===\s*"finance-payment-waiting"[\s\S]*?disabled:\s*false/,
  );
});
