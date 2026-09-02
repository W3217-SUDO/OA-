import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const casePage = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const financePage = readFileSync(new URL("./src/FinanceCenterPage.tsx", import.meta.url), "utf8");
const navigation = readFileSync(new URL("./src/incomingPaymentDetailNavigation.ts", import.meta.url), "utf8");
const app = readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

test("row 30 keeps the legacy receipt list order and drill-down entry", () => {
  const receiptModal = casePage.match(/title="回款信息"[\s\S]*?columns=\{\[([\s\S]*?)\n\s*\]\}/)?.[1] || "";
  const titles = [...receiptModal.matchAll(/title:"([^"]+)"/g)].map((match) => match[1]);
  assert.deepEqual(titles.slice(0, 10), [
    "回款流水号", "合同编号", "客户名称", "回款单位", "回款日期",
    "回款金额", "回款官费", "回款代理费", "回款方式", "银行单据号",
  ]);
  assert.match(receiptModal, /openIncomingPaymentDetail\(row.id\)/);
});

test("row 30 renders a dedicated assigned-payment page with allocation details", () => {
  assert.match(financePage, /className="finance-original-panel finance-incoming-applied-page"/);
  assert.match(financePage, /<h2>已分配回款<\/h2>/);
  assert.match(financePage, />回款信息<\/div>/);
  assert.match(financePage, />费用分配明细<\/div>/);
  for (const label of [
    "回款单位", "到账日期", "银行单号", "回款方式", "合同号",
    "客户名称", "到账金额", "已分配额", "未分配额", "领款人", "备注",
  ]) assert.match(financePage, new RegExp(`label="${label}"`));
  for (const title of [
    "案件类型", "案件名称", "案号", "合同号", "费用类型", "总额", "已收", "待收", "本次回款",
  ]) assert.match(financePage, new RegExp(`title: "${title}"`));
  assert.doesNotMatch(financePage, /title=\{`回款详情：\$\{incomingDetailTarget/);
});

test("row 30 uses a refresh-safe payment detail route", () => {
  assert.match(casePage, /onNavigate\?\.\(incomingPaymentDetailRoute\(paymentId\)\)/);
  assert.match(navigation, /finance-incoming-payment-\$\{normalizedId\}/);
  assert.match(navigation, /\^finance-incoming-payment-\(\\d\+\)\$/);
  assert.match(financePage, /resolveIncomingPaymentDetailTarget\(initialView\)/);
  assert.match(financePage, /onNavigate\?\.\("finance-incoming-company"\)/);
  assert.match(app, /route\.startsWith\("finance-incoming-payment-"\)/);
});
