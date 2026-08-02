import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

test("print preview keeps the legacy package and payment identity fields", () => {
  for (const field of ["packageNo", "serialNo", "paymentDate", "payee", "amount", "caseNo", "contractNo", "applicant", "payer", "remark"]) {
    assert.match(source, new RegExp(`paymentPrintPreview\\.${field}`));
  }
});

test("print preview is read-only until the explicit browser print action", () => {
  assert.match(source, /setPaymentPrintPreview\(preview\)/);
  assert.match(source, /window\.print\(\)/);
});

test("print keeps the old empty-selection wording", () => {
  assert.match(source, /paymentPackageEmptySelectionMessage[\s\S]*?请选择需要导出的请款单\./);
});

test("print status control keeps its legacy option matrix", () => {
  for (const status of ["请选择", "创建待提交", "待审批", "待付款", "待核销", "已付款", "已驳回", "已作废"]) {
    assert.match(source, new RegExp(`\\"${status}\\"`));
  }
});

test("writeoff list is status-locked to the legacy pending-writeoff value", () => {
  assert.match(source, /paymentWriteoffClearQuery[\s\S]*?status: "待核销"/);
  assert.match(source, /initialView === "finance-payment-writeoff"/);
});

test("writeoff uses the contract-payment endpoint for source applications", () => {
  assert.match(source, /contract-payment-applications\/\$\{contractPayment\.id\}\/writeoff/);
});

test("writeoff uses the finance-fee endpoint for ordinary payments", () => {
  assert.match(source, /api\.post\(`\/finance\/fees\/\$\{writeoffTarget\.id\}\/writeoff`/);
});

test("approval sends the legacy approved flag and audit comment", () => {
  assert.match(source, /review\`,\s*\{[\s\S]*?approved,[\s\S]*?comment: feeReviewComment/);
});

test("approval preserves a bounded batch endpoint for ordinary finance fees", () => {
  assert.match(source, /api\.post\("\/finance\/fees\/batch-review"/);
  assert.match(source, /fee_ids: feeReviewTargets\.map/);
});

test("contract-payment approvals use their dedicated status callback", () => {
  assert.match(source, /contract-payment-applications\/\$\{target\.id\}\/review/);
});

test("source navigation validates all contract-payment identity keys", () => {
  for (const key of ["payment_no", "contract_no", "customer", "amount", "source_id", "source_module", "return_page"]) {
    assert.match(source, new RegExp(`\\[\\s*\\"${key}\\"`));
  }
  assert.match(source, /matchesContractPaymentSource/);
});

test("invalid source and missing source records fail visibly", () => {
  assert.match(source, /合同付款来源参数重复/);
  assert.match(source, /合同付款来源缺少参数/);
  assert.match(source, /合同付款来源定位失败/);
});

test("source navigation returns through the contract detail route", () => {
  assert.match(source, /onNavigate\?\.\(contractPaymentSource\.returnPage\)/);
});

test("second-batch payment flows contain no unbounded record scan", () => {
  assert.doesNotMatch(source, /fetchAll|fetch-all|loadPaymentQueryRecords|paymentQueryRecordPagePlan/);
});

