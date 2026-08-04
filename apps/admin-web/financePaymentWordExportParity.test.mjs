import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

test("payment print keeps the legacy Word export contract in addition to browser print", () => {
  const printStart = source.indexOf("const printPayment");
  const previewStart = source.indexOf("paymentPrintPreviewPage");
  assert.notEqual(printStart, -1, "single payment print handler should exist");
  assert.notEqual(previewStart, -1, "payment print preview page should exist");
  const printArea = source.slice(printStart, source.indexOf("const loadInvoiceReferenceData", printStart));
  const previewArea = source.slice(previewStart, source.indexOf("paymentPrintPreviewPage", previewStart + 1));

  assert.match(
    source,
    /\/finance\/(payment-packages|fees|payments)[^"'\`]*(word|docx|print-to-word|print-word)/i,
    "frontend should call a finance payment Word/DOCX export endpoint instead of relying only on window.print",
  );
  assert.match(
    source,
    /responseType:\s*["']blob["']/,
    "Word export must download a server-generated binary file",
  );
  assert.match(
    previewArea,
    /导出\s*Word|下载\s*Word|DOCX|Word/,
    "print preview should expose a visible Word export/download action",
  );
  assert.match(printArea, /window\.print|setPaymentPrintPreview\(preview\)/);
});
