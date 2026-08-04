import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const source = fs.readFileSync(
  path.join(path.dirname(fileURLToPath(import.meta.url)), "src", "FinanceCenterPage.tsx"),
  "utf8",
);

const sliceBetween = (start, end) => {
  const startAt = source.indexOf(start);
  assert.notEqual(startAt, -1, `missing source anchor: ${start}`);
  const endAt = end ? source.indexOf(end, startAt + start.length) : source.length;
  assert.notEqual(endAt, -1, `missing source anchor: ${end}`);
  return source.slice(startAt, endAt);
};

test("invoice detail actions load the canonical invoice record", () => {
  const loader = sliceBetween(
    "const openInvoiceDetail = async (row: FinanceFlow)",
    "const openRefundDetail = async",
  );
  assert.match(loader, /api\.get\(`\/records\/\$\{row\.id\}`\)/);
  assert.match(loader, /data\.module !== "invoice"/);
  assert.match(loader, /String\(data\.id\) !== String\(row\.id\)/);
  assert.match(loader, /setInvoiceDetail\(data\)/);

  for (const operation of [
    "invoiceMineOperation",
    "invoicePendingOperation",
    "invoiceCompanyOperation",
  ]) {
    const block = sliceBetween(`const ${operation} =`, "const ");
    assert.match(block, /openInvoiceDetail\(row\)/, `${operation} must use canonical detail loader`);
  }
});
