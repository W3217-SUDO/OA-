// BUG20261029001：请款单申请日期取实际点“申请付款”的日期，而不是费用新建日期。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import { paymentApplicationDate } from "../src/finance/paymentLifecycle.mjs";

test("申请日期优先取申请付款时间", () => {
  const row = { created_at: "2026-10-15T14:13:31", data: { payment_applied_at: "2026-10-29T11:06:01", application_date: null } };
  assert.equal(paymentApplicationDate(row), "2026-10-29");
  assert.equal(paymentApplicationDate({ created_at: "2026-10-15T14:13:31", data: { application_date: "2026-10-20" } }), "2026-10-20");
  assert.equal(paymentApplicationDate({ created_at: "2026-10-15T14:13:31", data: {} }), "2026-10-15T14:13:31");
  assert.equal(paymentApplicationDate(null), "");
});

test("我的请款单、请款单审批、请款单详情都用同一个申请日期", () => {
  for (const path of ["../src/finance/columns/paymentOriginalColumns.tsx", "../src/finance/columns/paymentAuditOriginalColumns.tsx", "../src/finance/PaymentDocument.tsx"]) {
    const source = fs.readFileSync(new URL(path, import.meta.url), "utf8");
    assert.match(source, /paymentApplicationDate\(row\)/, path);
    assert.ok(!source.includes("application_date || row.created_at"), path);
  }
});
