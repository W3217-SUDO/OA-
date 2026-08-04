import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

test("legacy invoice controllers use a twenty-row default", () => {
  assert.match(source, /const invoiceLegacyDefaultPageSize = \(initialView: string\)/);
  assert.match(source, /initialView\.startsWith\("finance-invoice"\) \? 20 : 15/);
  assert.match(source, /pageSize: invoiceLegacyDefaultPageSize\(initialView\)/);
});

test("all invoice loaders send the legacy page size by default", () => {
  for (const name of ["invoiceMineParams", "invoicePendingParams", "invoiceCompanyParams", "invoiceUnissuedParams"]) {
    const start = source.indexOf(`const ${name}`);
    const end = source.indexOf("\n  };", start);
    assert.notEqual(start, -1);
    assert.match(source.slice(start, end), /pageSize = invoiceLegacyDefaultPageSize\(initialView\)/);
  }
});

test("invoice clear starts a fresh page-one request for every invoice list", () => {
  for (const name of ["loadInvoiceMine", "loadInvoicePending", "loadInvoiceCompany"]) {
    assert.match(source, new RegExp(`${name}\\(\\{\\}, 1,`));
  }
  assert.match(source, /loadInvoiceUnissued\(next, 1,/);
  assert.match(source, /const clearConfiguredQuery = \(\) =>/);
});

test("invoice clear clears selected rows and draft filters", () => {
  assert.match(source, /setOriginalQueryDraft\(\{\}\);[\s\S]*?setOriginalQuery\(\{\}\);[\s\S]*?setSelectedOriginalRows\(\[\]\);/);
});

test("invoice pending status remains explicit in the request matrix", () => {
  assert.match(source, /invoice_status: query\.routeField5 \|\| ""/);
  assert.match(source, /scope: "pending"/);
});

test("invoice failures preserve the legacy query error fallback", () => {
  assert.match(source, /const invoiceLegacyErrorMessage = "查询出错\."/);
});

test("invoice pagination remains server bounded", () => {
  assert.match(source, /api\.get\("\/finance\/invoices"/);
  assert.match(source, /page,\s*page_size: pageSize/);
  assert.doesNotMatch(source, /loadInvoiceAll|invoiceFetchAll/);
});

test("invoice detail and export controls remain available alongside the new default", () => {
  assert.match(source, /openInvoiceDetail\(row\)/);
  assert.match(source, /api\.get\("\/finance\/invoices\/export"/);
  assert.match(source, /selectedOnly && !selectedOriginalRows\.length/);
});

test("invoice approval flow exposes explicit approve and reject actions", () => {
  assert.match(source, /reviewFlow\("invoices", r, true\)/);
  assert.match(source, /reviewFlow\("invoices", r, false\)/);
});

test("invoice issue flow requires both invoice number and issue date", () => {
  assert.match(source, /if \(invoiceProcess && !String\(issueForm\.getFieldValue\("invoice_no"\)/);
  assert.match(source, /formatRequiredDate\(v\.invoice_date, "开票日期"\)/);
});

test("invoice issue failure and rejection stay on the bounded pending page", () => {
  assert.match(source, /loadInvoicePending\(originalQuery, 1, invoicePendingMeta\.pageSize\)/);
  assert.match(source, /reject-issue/);
});

test("invoice export supports current-filter and selected-id modes", () => {
  assert.match(source, /selectedOnly \? selectedOriginalRows\.join\(","\)/);
  assert.match(source, /\/finance\/invoices\/export/);
});

test("invoice empty export selection is rejected before any request", () => {
  assert.match(source, /selectedOnly && !selectedOriginalRows\.length/);
  assert.match(source, /请选择需要导出的发票/);
});

test("invoice detail remains read-only and can be opened from mine rows", () => {
  assert.match(source, /const invoiceMineOperation/);
  assert.match(source, /openInvoiceDetail\(row\)/);
});
