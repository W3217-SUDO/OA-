import assert from "node:assert/strict";
import fs from "node:fs";

const center = fs.readFileSync(new URL("./src/FinanceCenterPage.tsx", import.meta.url), "utf8");
const start = center.indexOf("const originalOperation =");
const mineStart = center.indexOf("].includes(initialView) ? (", start);
const mineEnd = center.indexOf(") : initialView === \"finance-payment-waiting\"", mineStart);
const operations = center.slice(mineStart, mineEnd);

assert.ok(start >= 0 && mineStart > start && mineEnd > mineStart, "finance payment mine operations should remain a stable source boundary");
assert.match(
  operations,
  /initialView === "finance-payment-mine"[\s\S]*?\["待审批", "已审批", "待付款"\][\s\S]*?\["admin", "manager", "auditor"\][\s\S]*?openPaymentRollback\(row\)[\s\S]*?回滚请款/,
  "authorized users should get the legacy rollback action on my-payment rows",
);

console.log("finance payment mine rollback parity: PASS");
