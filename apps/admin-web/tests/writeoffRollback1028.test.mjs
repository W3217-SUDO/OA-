// BUG20261028007：待核销列表右键有“查看”和“回滚”，回滚整个付款包退回待付款。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import { isPendingWriteoffPackage, isPendingWriteoffPayment } from "../src/finance/paymentLifecycle.mjs";

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");

test("只有已进付款包、未核销的待核销请款单可回滚", () => {
  assert.equal(isPendingWriteoffPackage({ status: "待核销", data: { payment_package_id: 9, writeoff_status: "待核销" } }), true);
  assert.equal(isPendingWriteoffPackage({ status: "待核销", data: { payment_package_id: 9, writeoff_status: "已核销" } }), false);
  assert.equal(isPendingWriteoffPackage({ status: "待核销", data: {} }), false);
  assert.equal(isPendingWriteoffPackage({ status: "已付款", data: { payment_package_id: 9 } }), false);
  assert.equal(isPendingWriteoffPackage(null), false);
});

test("右键菜单与提交走付款包回滚接口", () => {
  const columns = read("../src/finance/columns/paymentOriginalColumns.tsx");
  assert.match(columns, /\["已审批", "待付款"\]\.includes\(row\.status\) \|\| isPendingWriteoffPackage\(row\)/);
  const actions = read("../src/finance/services/paymentsActions.tsx");
  assert.match(actions, /isPendingWriteoffPackage\(paymentRollbackTarget\) \|\| isPendingWriteoffPayment\(paymentRollbackTarget\)\s*\?\s*`\/finance\/payment-packages\/\$\{paymentRollbackTarget\.data\.payment_package_id\}\/rollback`/);
});

test("内部费用 付款单查询、付款单-核销 也有右键查看和回滚（shenhe 11-02）", () => {
  const page = read("../src/finance/FinanceCenterPage.tsx");
  assert.match(page, /rowMenu: \["finance-internal-query", "finance-internal-writeoff"\]\.includes\(initialView\) \? internalRollbackMenu : undefined/);
  assert.match(page, /canRollbackPayment && isPendingWriteoffPackage\(row\)/);
  assert.match(page, /payment_package_id: row\.id/);
  const columns = read("../src/finance/columns/configuredColumns.tsx");
  assert.match(columns, /trigger=\{\["contextMenu"\]\} menu=\{\{ items \}\}/);
  const actions = read("../src/finance/services/paymentsActions.tsx");
  assert.match(actions, /initialView === "finance-internal-writeoff"\) \{\s*await loadPaymentPackages/);
});

test("501589：待核销列表的合同付款付款单也能回滚，操作栏有回滚按钮", () => {
  const contract = { module: "contract_payment", status: "待核销", data: { payment_package_id: 7, writeoff_status: "待核销" } };
  assert.equal(isPendingWriteoffPackage(contract), false);
  assert.equal(isPendingWriteoffPayment(contract), true);
  assert.equal(isPendingWriteoffPayment({ status: "待核销", data: { payment_package_id: 7, writeoff_status: "已核销" } }), false);
  assert.equal(isPendingWriteoffPayment({ status: "已付款", data: { payment_package_id: 7 } }), false);
  const page = fs.readFileSync(new URL("../src/finance/FinanceCenterPage.tsx", import.meta.url), "utf8");
  assert.match(page, /initialView === "finance-payment-writeoff" && isPendingWriteoffPayment\(row\)/);
});
