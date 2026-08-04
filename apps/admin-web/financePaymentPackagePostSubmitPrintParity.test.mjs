import assert from "node:assert/strict";
import fs from "node:fs";

const center = fs.readFileSync(new URL("./src/FinanceCenterPage.tsx", import.meta.url), "utf8");
const start = center.indexOf("const paymentPackagePrintPage =");
const end = center.indexOf("if (initialView === \"finance-receipts-new\")", start);
const packagePrintPage = center.slice(start, end);

assert.ok(start >= 0 && end > start, "payment package print page should remain a stable source boundary");
assert.match(
  packagePrintPage,
  /\{\(!paymentPackagePreview \|\| paymentPackagePreview\.submitted\) && \([\s\S]*?downloadPaymentPrintWord\(paymentPackagePrintData\.package_no\)[\s\S]*?下载 Word/,
  "a newly submitted payment package should retain the supported Word-download action",
);
assert.match(
  packagePrintPage,
  /\{\(!paymentPackagePreview \|\| paymentPackagePreview\.submitted\) && \([\s\S]*?window\.print\(\)[\s\S]*?打印/,
  "a newly submitted payment package should retain a repeat browser-print action",
);

console.log("finance payment package post-submit print parity: PASS");
