import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import vm from "node:vm";
import { createRequire } from "node:module";
import ts from "typescript";
import * as lifecycle from "./paymentLifecycle.mjs";
import * as invoiceHelpers from "../financeInvoiceHelpers.mjs";
import { fetchInvoiceRecord, invoiceEditValues, invoiceObjectFees, invoiceObjectRows, invoiceServiceRows } from "./invoiceDetails.mjs";

const require = createRequire(import.meta.url);
const plain = (value) => JSON.parse(JSON.stringify(value));
function loadTs(path, mocks = {}) {
  const source = fs.readFileSync(new URL(path, import.meta.url), "utf8");
  const output = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true } }).outputText;
  const module = { exports: {} };
  vm.runInNewContext(output, { module, exports: module.exports, require: (name) => name in mocks ? mocks[name] : require(name), console }, { filename: path });
  return module.exports;
}
const constants = loadTs("./constants.ts");
function actions(kind, api, context) {
  const notifications = [];
  const message = Object.fromEntries(["error", "warning", "info", "success"].map((key) => [key, (value) => notifications.push({ key, value })]));
  const exports = loadTs(`./services/${kind}Actions.tsx`, {
    "antd": { message, Modal: { warning() {}, info() {} } }, "../../api": { api },
    "../constants": constants, "../paymentLifecycle.mjs": lifecycle,
    "../../financeInvoiceHelpers.mjs": invoiceHelpers, "../../formSafety": { formatRequiredDate: (value) => value },
  });
  return { notifications, actions: exports[kind === "payments" ? "createFinancePaymentsActions" : "createFinanceInvoicesActions"](context) };
}
const fee = (id, caseNo, contractId, customer = "Synthetic customer") => ({ id, module: "finance", title: "Synthetic fee", customer, data: { case_no: caseNo, case_id: id + 100, contract_id: contractId, contract_no: `CON-${contractId}`, amount: 100 } });
const fees = [fee(1, "CASE-A", 10), fee(2, "CASE-B", 20), fee(3, "CASE-C", 20)];
const values = () => ({ customer: "Synthetic customer", amount: 420, extra_amount: 120, case_no: "STALE", case_record_id: 999, contract_record_id: 999,
  contract_no: "STALE", external_contract_no: "STALE", case_fee_ids: [1, 2, 3],
  service_items: [{ service_name: "Service A", quantity: 2, unit_price: 150, amount: 300, tax_rate: 6, tax_amount: 13 }, { service_name: "Service B", quantity: 1, unit_price: 120, amount: 120, tax_rate: 0, tax_amount: 0 }],
  case_fee_allocations: [{ fee_id: 1, amount: 180 }, { fee_id: 2, amount: 120 }, { fee_id: 3, amount: 120 }] });

test("CPI08 multi-contract multi-case same-customer payload clears stale single-source summaries and allows per-fee over-invoicing", () => {
  const input = values();
  const result = invoiceHelpers.buildInvoiceApplicationPayload({ values: input, caseFees: fees, requireSource: true });
  assert.equal(result.ok, true);
  assert.equal(result.payload.case_no, ""); assert.equal(result.payload.case_record_id, null);
  assert.equal(result.payload.contract_record_id, null); assert.equal(result.payload.contract_no, ""); assert.equal(result.payload.external_contract_no, "");
  assert.deepEqual(result.payload.case_fee_allocations, input.case_fee_allocations);
  assert.deepEqual(result.payload.service_items, input.service_items);
  assert.equal(input.contract_no, "STALE");
});
test("CPI08 cross-customer, missing and forbidden source fees remain blocked", () => {
  for (const caseFees of [fees.slice(0, 2), [fees[0], fee(2, "CASE-B", 20, "Other customer"), fees[2]], fees.map((row) => ({ ...row, data: { ...row.data, missing_or_forbidden: true } }))]) {
    assert.equal(invoiceHelpers.buildInvoiceApplicationPayload({ values: values(), caseFees }).ok, false);
  }
});
test("CPI08 monetary, service and allocation invariants reject inconsistent edits", () => {
  const invalid = [
    (v) => { v.amount = NaN; }, (v) => { v.extra_amount = -1; },
    (v) => { v.service_items[0].quantity = 0; }, (v) => { v.service_items[0].unit_price = Infinity; },
    (v) => { v.service_items[0].amount = 301; }, (v) => { v.service_items[0].tax_rate = 101; },
    (v) => { v.service_items[0].tax_amount = -1; }, (v) => { v.case_fee_allocations[1].fee_id = 1; },
    (v) => { v.case_fee_allocations.pop(); }, (v) => { v.case_fee_allocations[0].amount = 179; },
    (v) => { v.service_items[0].service_name = " "; }, (v) => { v.case_fee_allocations[0].amount = null; },
  ];
  for (const modify of invalid) { const v = values(); modify(v); assert.equal(invoiceHelpers.buildInvoiceApplicationPayload({ values: v, caseFees: fees }).ok, false); }
});
test("CPI06 detail uses every service and per-fee allocation, never invoice total as source fee amount", () => {
  const record = { id: 70, module: "invoice", customer: "Synthetic customer", data: { ...values(), invoice_objects: [
    { fee_id: 1, fee_amount: 100, issued_amount: 45, received_amount: 80, contract_no: "CON-10", case_no: "CASE-A", allocation_amount: 180 },
    { fee_id: 2, fee_amount: 100, issued_amount: 25, received_amount: 20, contract_no: "CON-20", case_no: "CASE-B", allocation_amount: 120 },
    { fee_id: 3, fee_amount: null, issued_amount: null, received_amount: null, allocation_amount: null, missing_or_forbidden: true },
  ] } };
  assert.equal(invoiceServiceRows(record).length, 2);
  const rows = invoiceObjectRows(record);
  assert.equal(rows.length, 3); assert.equal(rows[0].fee_amount, 100); assert.equal(rows[0].allocation_amount, 180);
  assert.equal(rows[2].allocation_amount, null); assert.equal(rows[2].fee_amount, null); assert.equal(rows[2].received_amount, null);
  assert.deepEqual(invoiceEditValues(record).case_fee_ids, [1, 2, 3]);
  assert.equal(invoiceObjectFees(record)[0].data.invoiced_amount, 45);
  assert.equal(invoiceServiceRows({ data: { amount: 500 } }).length, 0);
  assert.equal(invoiceObjectRows({ data: { amount: 500, case_fee_ids: [1, 2] } }).length, 0);
});
test("CPI06 hydrated fetch rejects wrong identity and uses dedicated endpoint", async () => {
  const urls = [];
  const record = { id: 7, module: "invoice", data: {} };
  assert.equal(await fetchInvoiceRecord({ get: async (url) => { urls.push(url); return { data: record }; } }, 7), record);
  assert.deepEqual(urls, ["/finance/invoices/7"]);
  await assert.rejects(fetchInvoiceRecord({ get: async () => ({ data: { ...record, id: 8 } }) }, 7));
});
test("CPI05 cancel and rollback actions dispatch both record sources to their own APIs and refresh", async () => {
  for (const module of ["finance", "contract_payment"]) for (const action of ["cancel", "rollback"]) {
    const calls = [], target = { id: 12, module, status: "待审批", data: {} };
    let reloaded = 0;
    const context = { paymentCancelTarget: target, paymentCancelReason: "synthetic cancellation", setPaymentCancelTarget() {}, setPaymentCancelReason() {},
      paymentRollbackTarget: target, paymentRollbackComment: "synthetic rollback", setPaymentRollbackTarget() {}, setPaymentRollbackComment() {},
      financeFeeListMeta: { page: 1, pageSize: 15 }, originalQuery: {}, financeFeeRefreshGuard: { begin: () => 1, isLatest: () => true },
      setFees() {}, setFinanceFeeListMeta() {}, load: async () => { reloaded++; } };
    const client = { post: async (...args) => { calls.push(args); }, get: async (...args) => { calls.push(args); return { data: { items: [] } }; } };
    const { actions: run } = actions("payments", client, context);
    await run[action === "cancel" ? "submitPaymentCancel" : "submitPaymentRollback"]();
    assert.equal(calls[0][0], `/${module === "finance" ? "finance/fees" : "contract-payment-applications"}/12/${action}`);
    assert.equal(module === "contract_payment" ? reloaded : calls.length - 1, 1);
  }
});
test("CPI07 contract submit/review never calls ordinary readiness or fee mutation", async () => {
  const calls = [];
  const { actions: run } = actions("payments", { post: async (...args) => calls.push(args) }, { load: async () => {} });
  const row = { id: 12, module: "contract_payment", data: { fee_type: "官方费用" } };
  await run.feeAction(row, "submit"); await run.feeAction(row, "approve");
  assert.equal(calls[0][0], "/contract-payment-applications/12/submit");
  assert.equal(calls[1][0], "/contract-payment-applications/12/review"); assert.equal(calls[1][1].approved, true);
});
test("CPI07 rejected original payment editor preserves source types, rounds money, blocks terminal state and invalid balances", () => {
  assert.equal(lifecycle.canEditContractPayment({ module: "contract_payment", status: "已驳回", data: {} }), true);
  for (const status of ["待审批", "待付款", "已付款", "已核销", "已撤销"]) assert.equal(lifecycle.canEditContractPayment({ module: "contract_payment", status, data: {} }), false);
  const candidates = [{ case_fee_id: 5, remaining_amount: 80 }, { contract_object_id: 5, remaining_amount: 25 }];
  const v = { payment_type_id: 3, application_date: "2026-09-14", serial_no: "DO-NOT-CHANGE" };
  const result = lifecycle.contractPaymentEditPayload(v, ["fee:5", "object:5"], candidates, { "fee:5": 60.126, "object:5": 25 });
  assert.deepEqual(result.lines.map((row) => row.amount), [60.13, 25]); assert.equal("serial_no" in result, false);
  for (const amounts of [{ "fee:5": 81 }, { "fee:5": NaN }, { "fee:5": 0 }, { "fee:5": Infinity }]) assert.throws(() => lifecycle.contractPaymentEditPayload(v, ["fee:5"], candidates, amounts));
  assert.throws(() => lifecycle.contractPaymentEditPayload(v, ["fee:404"], candidates, { "fee:404": 2 }));
});
test("CPI09 unified query sends one filtered page and preserves backend order/total without merging or truncation", async () => {
  const records = Array.from({ length: 30 }, (_, index) => ({ id: index + 1, module: index % 2 ? "contract_payment" : "finance" }));
  const calls = [];
  const response = { data: { items: records, total: 237, page: 2, page_size: 30 } };
  const { actions: run } = actions("payments", { get: async (...args) => { calls.push(args); return response; } }, { paymentQueryPageSize: 30 });
  const result = await run.loadPaymentQueryPage({ paymentNo: "KEY", customer: "Synthetic customer", status: "已驳回" }, 2, 30);
  assert.equal(result, response); assert.equal(calls.length, 1);
  assert.equal(calls[0][0], "/finance/payment-applications/query");
  assert.equal(calls[0][1].params.module, undefined); assert.equal(calls[0][1].params.page_size, 30);
  assert.equal(calls[0][1].params.keyword, "KEY"); assert.equal(calls[0][1].params.customer, "Synthetic customer");
  assert.equal(lifecycle.unifiedPaymentQueryParams({ page: 2, page_size: 500 }).page_size, 500);
});
test("CPI08 scoped context keeps selected fees beyond first candidate page and uses invoice_id", async () => {
  const calls = [];
  let candidates = [fees[0]], contractRows = [], customerRows = [];
  const context = { invoiceEditTarget: { id: 99 }, invoiceForm: { getFieldValue: (name) => name === "case_fee_ids" ? [1, 3] : "Synthetic customer" },
    setInvoiceCandidateFees: (fn) => { candidates = fn(candidates); }, setContracts: (fn) => { contractRows = fn(contractRows); }, setCustomers: (fn) => { customerRows = fn(customerRows); } };
  const { actions: run } = actions("invoices", { get: async (...args) => { calls.push(args); return { data: { items: [fees[1]], selected_items: [fees[2]], total: 112, page: 2, page_size: 50, customer_record: { id: 80 } } }; } }, context);
  const result = await run.loadInvoiceReferenceData({ page: 2 });
  assert.equal(calls.length, 1); assert.equal(calls[0][0], "/finance/invoice-context"); assert.equal(calls[0][1].params.invoice_id, 99);
  assert.deepEqual(plain(candidates.map((row) => row.id)), [1, 2, 3]); assert.equal(result.total, 112);
  assert.equal(result.selectedRows[0].id, 3);
});
test("CPI08 saved draft survives submit failure and retry patches original ID with all services/allocations", async () => {
  const calls = [];
  const originalValues = values();
  const context = { invoiceForm: { validateFields: async () => originalValues, resetFields() {} }, invoiceFeeOptions: fees,
    cases: [], contracts: [], invoiceCandidateFees: [], fees: [], invoiceEditTarget: null,
    setInvoiceEditTarget: (row) => { context.invoiceEditTarget = row; }, setInvoiceOpen() {}, load: async () => {} };
  let failSubmit = true;
  const api = {
    post: async (url, payload) => { calls.push([url, payload]); if (url.endsWith("/submit") && failSubmit) { failSubmit = false; throw new Error("mock submit failure"); } return { data: { id: 90, module: "invoice", serial_no: "KEEP-90", status: "草稿", customer: originalValues.customer, data: payload } }; },
    patch: async (url, payload) => { calls.push([url, payload]); return { data: { id: 90, data: payload } }; },
  };
  const { actions: run } = actions("invoices", api, context);
  await run.createInvoice(true);
  assert.equal(context.invoiceEditTarget.id, 90);
  await run.createInvoice(true);
  assert.deepEqual(calls.map((row) => row[0]), ["/finance/invoices", "/finance/invoices/90/submit", "/finance/invoices/90", "/finance/invoices/90/submit"]);
  assert.deepEqual(plain(calls[2][1].service_items), originalValues.service_items);
  assert.deepEqual(plain(calls[2][1].case_fee_allocations), originalValues.case_fee_allocations);
});

test("CPI08 rapid customer switch rejects late scope response before any shared state write", async () => {
  let token = 1, candidates = [], contracts = [], customers = [];
  const pending = new Map();
  const context = { invoiceForm: { getFieldValue: (name) => name === "case_fee_ids" ? [] : "" }, invoiceEditTarget: null,
    setInvoiceCandidateFees: (fn) => { candidates = fn(candidates); }, setContracts: (fn) => { contracts = fn(contracts); }, setCustomers: (fn) => { customers = fn(customers); } };
  const { actions: run } = actions("invoices", { get: async (_url, { params }) => {
    assert.equal("isCurrent" in params, false);
    return new Promise((resolve) => pending.set(params.customer, resolve));
  } }, context);
  const first = run.loadInvoiceReferenceData({ customer: "First", isCurrent: () => token === 1 });
  token = 2;
  const second = run.loadInvoiceReferenceData({ customer: "Second", isCurrent: () => token === 2 });
  pending.get("Second")({ data: { items: [fee(22, "CASE-SECOND", 222, "Second")], customer_record: { id: 2222 }, page: 1, total: 1 } });
  await second;
  pending.get("First")({ data: { items: [fee(11, "CASE-FIRST", 111, "First")], customer_record: { id: 1111 }, page: 1, total: 1 } });
  await first;
  assert.deepEqual(plain(candidates.map((row) => row.id)), [22]);
  assert.deepEqual(plain(contracts.map((row) => row.id)), [222]);
  assert.deepEqual(plain(customers.map((row) => row.id)), [2222]);
});
