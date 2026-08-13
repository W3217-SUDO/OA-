import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const casePage = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const financePage = fs.readFileSync(new URL("./src/FinanceCenterPage.tsx", import.meta.url), "utf8");
const navigation = fs.readFileSync(new URL("./src/businessRecordDetailNavigation.ts", import.meta.url), "utf8");

test("律所付款使用普通费用审批而不是内部付款包", () => {
  assert.match(casePage, /const submitCaseFeePayment = async/);
  assert.match(casePage, /api\.post\(`\/finance\/fees\/\$\{row\.id\}\/submit`/);
  assert.match(casePage, /if\(key===\"payment\"\)return void submitCaseFeePayment\(selectedFirmFee!\)/);
  assert.doesNotMatch(casePage, /if\(key===\"payment\"\)return void previewInternalPayment\(selectedFirmFee!\)/);
});

test("案件费用退费和开票携带动作并打开预填表单", () => {
  assert.match(navigation, /"create_invoice" \| "create_refund"/);
  assert.match(casePage, /action:key===\"invoice\"\?\"create_invoice\":\"create_refund\"/);
  assert.match(casePage, /key===\"invoice\"\?\"finance-invoice-mine\":\"finance-refund\"/);
  assert.match(financePage, /target\.action === \"create_invoice\"/);
  assert.match(financePage, /case_fee_ids: \[data\.id\]/);
  assert.match(financePage, /setInvoiceOpen\(true\)/);
  assert.match(financePage, /target\.action === \"create_refund\"/);
  assert.match(financePage, /fee_record_id: data\.id/);
  assert.match(financePage, /<Form\.Item name="fee_record_id" hidden>/);
  assert.match(financePage, /applicant: profile\.data\?\.display_name \|\| data\.owner_display_name \|\| "姓名待维护"/);
  assert.doesNotMatch(financePage, /applicant: profile\.data\?\.display_name \|\| profile\.data\?\.username/);
  assert.match(financePage, /setRefundOpen\(true\)/);
  assert.match(financePage, /initialView\.startsWith\("finance-refund"\)[\s\S]*?\? "refunds"/);
});

test("案件任务和内部结算显示关键状态字段", () => {
  assert.equal((casePage.match(/dataIndex:\s*\"priority\"/g) || []).length, 3);
  assert.match(casePage, /key:\"internal-fees\"[\s\S]*?title:\"状态\",dataIndex:\"status\"/);
  assert.match(casePage, /row\.data\.payment_requested_amount/);
  assert.match(casePage, /row\.data\.paid_amount/);
});
