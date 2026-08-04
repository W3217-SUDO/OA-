import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

test("invoice detail contract number keeps a real contract navigation entry", () => {
  const start = source.indexOf("invoiceDetailData.contract_no || \"\"");
  const end = source.indexOf("                )}", start);
  assert.ok(start >= 0 && end > start, "normal invoice contract row should be extractable");
  const normalContractRow = source.slice(start, end);
  assert.match(normalContractRow, /openContractDetail\(invoiceDetailData\.contract_no\)/);
});
