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
  assert.match(source, /"finance-settlement-pending",[\s\S]*?"finance-settlement-audit",[\s\S]*?"finance-settlement-payment"/);
  assert.match(source, /clearConfiguredQuery/);
});

test("contract payment applications are loaded and reviewed through contract API", () => {
  assert.match(source, /module:\s*"contract_payment"/);
  assert.match(source, /_source_module:\s*"contract_payment"/);
  assert.match(source, /contract-payment-applications\/\$\{target\.id\}\/review/);
  assert.match(source, /contract-payment-applications\/\$\{contractPayment\.id\}\/writeoff/);
});
