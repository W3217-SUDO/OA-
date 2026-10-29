// BUG20261028007：待核销列表右键有“查看”和“回滚”，回滚整个付款包退回待付款。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import { isPendingWriteoffPackage } from "../src/finance/paymentLifecycle.mjs";

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
  assert.match(actions, /isPendingWriteoffPackage\(paymentRollbackTarget\)\s*\?\s*`\/finance\/payment-packages\/\$\{paymentRollbackTarget\.data\.payment_package_id\}\/rollback`/);
});
