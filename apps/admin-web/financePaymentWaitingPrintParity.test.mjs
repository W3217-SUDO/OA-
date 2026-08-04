import assert from "node:assert/strict";
import fs from "node:fs";

const center = fs.readFileSync(new URL("./src/FinanceCenterPage.tsx", import.meta.url), "utf8");
const start = center.indexOf("const originalOperation =");
const end = center.indexOf("const paymentPackageOperation =", start);
const operations = center.slice(start, end);

assert.ok(start >= 0 && end > start, "finance payment operations should remain a stable source boundary");
assert.match(
  operations,
  /initialView === "finance-payment-waiting"[\s\S]*?latestTransaction\(row\)[\s\S]*?printPayment\(row\)[\s\S]*?打印/,
  "waiting payment rows with a real payment transaction should expose the legacy print action",
);

console.log("finance payment waiting print parity: PASS");
