import assert from "node:assert/strict";
import test from "node:test";

import { buildContractPaymentNavigation } from "./src/contractPaymentNavigation.ts";

test("contract payment detail emits the complete exact finance target", () => {
  const target = buildContractPaymentNavigation({
    pathname: "/workspace",
    hash: "#contract-detail",
    payment: {
      id: 806,
      serial_no: "FK20260802001",
      customer: "CODEX-H2客户",
      data: {
        contract_no: "SHHT2510026",
        amount: 1250.5,
        pending_amount: 800,
      },
    },
    contract: {
      id: 595,
      serial_no: "SHHT2510026",
      customer: "CODEX-H2客户",
    },
  });

  assert.equal(target.ok, true);
  if (!target.ok) return;
  const url = new URL(target.url, "http://127.0.0.1:5173");
  assert.equal(url.pathname, "/workspace");
  assert.equal(url.hash, "#contract-detail");
  assert.deepEqual(Object.fromEntries(url.searchParams), {
    page: "finance-payment-mine",
    payment_no: "FK20260802001",
    contract_no: "SHHT2510026",
    customer: "CODEX-H2客户",
    amount: "1250.5",
    source_id: "806",
    source_module: "contract_payment",
    return_page: "contract-detail-595-SHHT2510026",
  });
});

test("contract payment detail refuses an unresolvable finance target", () => {
  assert.deepEqual(
    buildContractPaymentNavigation({
      pathname: "/workspace",
      payment: { id: 0, serial_no: "", data: {} },
      contract: { id: 595, serial_no: "SHHT2510026", customer: "test" },
    }),
    { ok: false, message: "当前付款记录缺少申请单号" },
  );

  assert.deepEqual(
    buildContractPaymentNavigation({
      pathname: "/workspace",
      payment: { id: 0, serial_no: "FK20260802001", data: {} },
      contract: { id: 595, serial_no: "SHHT2510026", customer: "test" },
    }),
    { ok: false, message: "当前付款记录缺少来源ID" },
  );

  assert.deepEqual(
    buildContractPaymentNavigation({
      pathname: "/workspace",
      payment: { id: 806, serial_no: "FK20260802001", data: { amount: 0 } },
      contract: { id: 595, serial_no: "SHHT2510026", customer: "test" },
    }),
    { ok: false, message: "当前付款记录缺少有效金额" },
  );
});
