import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

test("my payment rows always expose the legacy read-only detail entry", () => {
  const operation = source.match(
    /const originalOperation = \([\s\S]*?\n  const openGeneralSettlementReview/,
  );

  assert.ok(operation, "payment row operation should exist");
  assert.match(
    operation[0],
    /\[\s*"finance-payment-mine",\s*"finance-payment-query",\s*"finance-internal-mine",?\s*\]\.includes\(initialView\)[\s\S]*?(?:setFeeDetail\(row\)|void openPaymentDetail\(row\))[\s\S]*?查看/,
  );
});

test("my payment list keeps the legacy fifteen-row page size", () => {
  const pagination = source.match(
    /pagination=\{\{[\s\S]*?showSizeChanger:\s*true/,
  );

  assert.ok(pagination, "payment pagination should exist");
  assert.match(
    pagination[0],
    /pageSize:[\s\S]*?\[\s*"finance-payment-mine",[\s\S]*?\]\.includes\(initialView\)\s*\?\s*15/,
  );
});

test("my payment list offers the legacy page-size choices", () => {
  const pagination = source.match(
    /pagination=\{\{[\s\S]*?showSizeChanger:\s*true/,
  );

  assert.ok(pagination, "payment pagination should exist");
  assert.match(
    pagination[0],
    /pageSizeOptions:[\s\S]*?\[\s*"finance-payment-mine",[\s\S]*?\]\.includes\(initialView\)\s*\?\s*\[10,\s*15,\s*20,\s*50,\s*100,\s*200\]/,
  );
});
