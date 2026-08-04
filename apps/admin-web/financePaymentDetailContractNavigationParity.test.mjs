import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

const generalPaymentDetail = () => {
  const start = source.indexOf('open={Boolean(feeDetail) && !isInternalHistoryList}');
  const end = source.indexOf('open={Boolean(refundDetail)}', start);
  assert.ok(start >= 0 && end > start, "general payment detail modal should be extractable");
  return source.slice(start, end);
};

test("general payment detail keeps the legacy contract entry and navigation", () => {
  const detail = generalPaymentDetail();
  assert.match(detail, /feeDetail\.data\.contract_no/);
  assert.match(detail, /openContractDetail\(feeDetail\.data\.contract_no\)/);
});
