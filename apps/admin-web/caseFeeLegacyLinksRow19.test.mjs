import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const page = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const financePage = readFileSync(new URL("./src/FinanceCenterPage.tsx", import.meta.url), "utf8");

test("row 19 keeps the exact legacy fee columns", () => {
  const columns = page.match(/const externalCaseFeeColumns=\[([\s\S]*?)\n  \];/)?.[1] || "";
  const titles = [...columns.matchAll(/title:"([^"]+)"/g)].map((match) => match[1]);
  assert.deepEqual(titles, [
    "合同编号", "费用类型", "金额", "退费", "提交人", "提交日期",
    "回款日期", "回款金额", "开票日期", "发票号", "申请付款金额",
  ]);
  assert.doesNotMatch(columns, /title:"付款账号"/);
});

test("row 19 opens every blue legacy relation instead of styling inert text", () => {
  const columns = page.match(/const externalCaseFeeColumns=\[([\s\S]*?)\n  \];/)?.[1] || "";
  assert.match(columns, /title:"合同编号"[\s\S]*?openRelatedContract\(\{id:contractId,serial_no:contractNo\}\)/);
  assert.match(columns, /title:"回款金额"[\s\S]*?openRelatedIncomingPayment\(row\)/);
  assert.match(columns, /title:"发票号"[\s\S]*?openRelatedInvoice\(row\)/);
  assert.match(page, /setViewingFeeIncomingPayments\(payments\)/);
  assert.match(page, /title="费用回款记录"[\s\S]*?title:"回款单号"[\s\S]*?openIncomingPaymentDetail\(row.id\)/);
  assert.match(page, /rememberIncomingPaymentDetailTarget\(paymentId\)[\s\S]*?finance-incoming-company/);
  assert.match(page, /rememberBusinessRecordDetailTarget\(\{ id: invoiceId, module: "invoice" \}\)[\s\S]*?finance-invoice-company/);
  assert.match(financePage, /consumeIncomingPaymentDetailTarget\(\)[\s\S]*?\/finance\/incoming-payments\/\$\{paymentId\}/);
});
