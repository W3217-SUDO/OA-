import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./src/FinanceCenterPage.tsx", import.meta.url), "utf8");

test("payment approval route exposes row selection and approval action", () => {
  assert.match(source, /const internalApprovalRoutes = \[[\s\S]*?"finance-payment-audit"[\s\S]*?\];/);
  assert.match(source, /activeRouteConfig\?\.selectable\s*\|\|\s*initialView\s*===\s*"finance-payment-audit"/);
  assert.match(source, /initialView\s*===\s*"finance-payment-audit"\s*\?\s*"付款审批"\s*:\s*"提成审批"/);
  assert.match(source, /initialView\s*===\s*"finance-payment-audit"\s*\?\s*\[/);
  for (const field of ["案号", "原告", "金额", "费用类型", "付款备注"]) {
    assert.match(source, new RegExp(`title:\\s*"${field}"`));
  }
  assert.match(source, /取消/);
  assert.match(source, /if \(!targets\.length\)/);
  assert.match(source, /message\.warning\(/);
});

test("payment print empty state keeps selectable export controls", () => {
  assert.match(source, /"finance-payment-print":\s*\{[\s\S]*?selectable:\s*true[\s\S]*?export:\s*true/);
  assert.match(source, /initialView\s*===\s*"finance-payment-print"\s*\?\s*\(/);
  assert.match(source, /合并打印/);
  assert.match(source, /if \(!targets\.length\)\s*\{\s*Modal\.info/);
});

test("payment print rows expose only print action by status", () => {
  assert.match(
    source,
    /initialView\s*===\s*"finance-payment-print"\s*\?\s*\([\s\S]*?row\.status[\s\S]*?printPayment\(row\)/,
  );
  assert.doesNotMatch(
    source,
    /initialView\s*===\s*"finance-payment-print"\s*&&[\s\S]*?printPayment\(row\)/,
  );
  assert.match(source, /canApprove\s*&&\s*row\.status/);
});

test("payment writeoff exposes clear and selectable checkbox controls", () => {
  assert.match(
    source,
    /activeRouteConfig\?\.clear[\s\S]*?initialView\s*===\s*"finance-payment-writeoff"/,
  );
  assert.match(
    source,
    /initialView\s*===\s*"finance-payment-audit"[\s\S]*?initialView\s*===\s*"finance-payment-writeoff"/,
  );
});

test("non-print payment routes retain generic actions", () => {
  assert.match(source, /canApprove\s*&&\s*row\.status/);
  assert.match(source, /transactionForm\.setFieldsValue\(\{/);
  assert.match(source, /openRecordFiles\(row/);
});

test("payment query keeps date clear and read-only detail action", () => {
  assert.match(source, /DatePicker\.RangePicker[\s\S]*?allowClear/);
  assert.match(source, /\["finance-payment-query",\s*"finance-internal-mine"\]\.includes\(initialView\)[\s\S]*?setOriginalField\(key, undefined\)[\s\S]*?清空/);
  assert.match(
    source,
    /\["finance-payment-query",\s*"finance-internal-mine"\]\.includes\(initialView\)\s*\?\s*\([\s\S]*?setFeeDetail\(row\)[\s\S]*?查看/,
  );
});

test("internal expense mine keeps query controls and read-only rows", () => {
  assert.match(source, /\["finance-payment-query",\s*"finance-internal-mine"\]\.includes\(initialView\)/);
  assert.match(source, /queryField\("审核日期",\s*"auditRange",\s*"date"\)/);
  assert.match(source, /queryField\("费用类型",\s*"feeType"\)/);
});

test("invoice mine gates empty-state exports", () => {
  assert.match(source, /isInvoiceMineRoute\s*\|\|\s*isInvoicePendingRoute\s*\|\|\s*isInvoiceCompanyRoute/);
  assert.match(source, /disabled=\{!configuredRows\.length\}[\s\S]*?exportInvoiceList\(false\)/);
  assert.match(source, /disabled=\{!configuredRows\.length\}[\s\S]*?exportInvoiceList\(true\)/);
  assert.match(source, /if \(selectedOnly && !selectedOriginalRows\.length\)[\s\S]*?请选择需要导出的发票/);
});

test("unissued invoice empty-state export and more actions are gated", () => {
  assert.match(source, /isInvoiceUnissuedRoute\s*\?\s*\(\s*<Space/);
  assert.match(source, /exportInvoiceUnissued\(key === "selected"\)/);
  assert.match(source, /disabled=\{!configuredRows\.length\}/);
  assert.match(source, /loading=\{settlementActionLoading\}/);
});

test("pending settlement exposes query clear control", () => {
  assert.match(source, /"finance-settlement-pending",[\s\S]*?"finance-settlement-audit",[\s\S]*?"finance-settlement-payment",[\s\S]*?"finance-settlement-refused"/);
  assert.match(source, /clearConfiguredQuery/);
});

test("paid settlement exposes clear and export controls", () => {
  const route = source.match(/"finance-settlement-paid": \{([\s\S]*?)\n    \},\n    "finance-settlement-refused"/);
  assert.ok(route, "paid settlement route config should exist");
  assert.match(route[1], /clear: true/);
  assert.match(route[1], /export: true/);
  assert.match(source, /isGeneralSettlementPaidRoute/);
});

test("paid settlement rows keep view/export/rollback actions without pay action", () => {
  const operation = source.match(/const generalSettlementOperation = \([\s\S]*?\n  const archiveSettlementPendingOperation/);
  assert.ok(operation, "general settlement row operation should exist");
  assert.match(operation[0], /isGeneralSettlementPaidRoute/);
  assert.match(operation[0], /exportGeneralSettlement\("settlement", \[row\.id\]\)/);
  assert.match(operation[0], /openGeneralSettlementPayment\(\[row\], "rollback"\)/);
  assert.match(operation[0], /\{isGeneralSettlementPaymentRoute && \(/);
  assert.match(source, /exportGeneralSettlement\("receipt"\)/);
  assert.match(source, /exportGeneralSettlement\("case"\)/);
});

test("refused settlement exposes clear/export and reapply-only row flow", () => {
  const route = source.match(/"finance-settlement-refused": \{([\s\S]*?)\n    \},\n    \.\.\.Object\.fromEntries/);
  assert.ok(route, "refused settlement route config should exist");
  assert.match(route[1], /clear: true/);
  assert.match(route[1], /export: true/);
  const operation = source.match(/const generalSettlementOperation = \([\s\S]*?\n  const archiveSettlementPendingOperation/);
  assert.match(operation[0], /isGeneralSettlementRejectedRoute/);
  assert.match(operation[0], /openGeneralSettlementReapply\(\[row\]\)/);
});

test("archive settlement pending exposes clear/export controls", () => {
  const expr = source.indexOf('clear: [', source.indexOf("const routeConfigs"));
  assert.ok(expr >= 0, "archive pending route expression should exist");
  const block = source.slice(expr - 500, expr + 500);
  assert.match(block, /"finance-archive-fee-pending",[\s\S]*?"finance-archive-fee-payment"/);
  assert.match(block, /"finance-archive-fee-paid"/);
  assert.match(block, /clear: \[[\s\S]*?\]\.includes\(route\)/);
  assert.match(block, /export: \[[\s\S]*?\]\.includes\(route\)/);
  assert.doesNotMatch(block, /clear: true/);
  assert.doesNotMatch(block, /export: true/);
  assert.match(source, /exportPendingArchiveSettlements/);
});

test("archive settlement routes expose scoped clear/export capability", () => {
  const expr = source.slice(source.indexOf('clear: [', source.indexOf("const routeConfigs")), source.indexOf('headers:', source.indexOf('clear: [', source.indexOf("const routeConfigs"))));
  assert.match(expr, /finance-archive-fee-pending/);
  assert.match(expr, /finance-archive-fee-payment/);
  assert.match(expr, /finance-archive-fee-paid/);
  assert.match(expr, /finance-archive-fee-refused/);
});

test("contract payment applications are loaded and reviewed through contract API", () => {
  assert.match(source, /module:\s*"contract_payment"/);
  assert.match(source, /_source_module:\s*"contract_payment"/);
  assert.match(source, /contract-payment-applications\/\$\{target\.id\}\/review/);
  assert.match(source, /contract-payment-applications\/\$\{contractPayment\.id\}\/writeoff/);
});
