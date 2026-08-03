import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

test("refund mutation refreshes preserve the active status and business-group filters", () => {
  for (const name of ["updateRefundAmount", "updateRefundBatchStatus"]) {
    const start = source.indexOf(`const ${name}`);
    const end = source.indexOf("\n  };", start);
    assert.ok(start >= 0 && end > start, `${name} should exist`);
    const block = source.slice(start, end);
    assert.match(block, /loadRefunds\(/);
    assert.match(block, /refundStatusFilter/);
    assert.match(block, /refundGroupFilter/);
  }
});

test("refund create and completion refresh only the bounded refund list", () => {
  for (const name of ["createRefund", "completeRefund"]) {
    const start = source.indexOf(`const ${name}`);
    const end = source.indexOf("\n  };", start);
    assert.ok(start >= 0 && end > start, `${name} should exist`);
    const block = source.slice(start, end);
    assert.match(block, /refreshRefundList\(/);
    assert.doesNotMatch(block, /\bload\(\)/);
  }
});

test("refund submit and review reload through the bounded refund endpoint", () => {
  const submitStart = source.indexOf("const submitFlow");
  const submitEnd = source.indexOf("\n  const reviewFlow", submitStart);
  const submitBlock = source.slice(submitStart, submitEnd);
  assert.match(submitBlock, /kind === "refunds"/);
  assert.match(submitBlock, /refreshRefundList\(/);

  const reviewStart = source.indexOf("const reviewFlow");
  const reviewEnd = source.indexOf("\n  const issueInvoice", reviewStart);
  const reviewBlock = source.slice(reviewStart, reviewEnd);
  assert.match(reviewBlock, /kind === "refunds"/);
  assert.match(reviewBlock, /refreshRefundList\(/);
});

test("refund refresh plan stays server-bounded and keeps the current coordinates", () => {
  assert.match(source, /const refreshRefundList = async \(/);
  assert.match(source, /refreshRefundList\(\)/);
  assert.match(source, /refundMeta\.pageSize,[\s\S]*refundStatusFilter,[\s\S]*refundGroupFilter/);
});
