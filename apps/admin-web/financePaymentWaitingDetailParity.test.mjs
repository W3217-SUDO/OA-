import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

test("pending payment rows retain the legacy detail entry alongside paid print", () => {
  const start = source.indexOf('initialView === "finance-payment-waiting" ?');
  const end = source.indexOf("    ) : <Space size={0}>", start);
  assert.ok(start >= 0 && end > start, "waiting payment operation must have a stable branch");
  const branch = source.slice(start, end);

  assert.match(branch, /openPaymentDetail\(row\)/);
  assert.match(branch, /latestTransaction\(row\)[\s\S]*?printPayment\(row\)/);
});
