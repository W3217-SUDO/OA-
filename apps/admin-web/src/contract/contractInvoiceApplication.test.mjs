import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import vm from "node:vm";
import ts from "typescript";
import { buildInvoiceApplicationPayload } from "../financeInvoiceHelpers.mjs";
import { buildContractInvoiceRoute, readContractInvoiceRoute, validateInvoiceContracts, customerInvoiceDefaults, selectedInvoiceAllocations, validateInvoiceAmounts, filterInvoiceSubjects } from "./contractInvoiceApplication.ts";

const contracts = [1, 2].map(id => ({ id, serial_no: `CODEX-CPI-A-C${id}`, title: `Contract ${id}`, customer: "CODEX-CPI-A", status: "草稿", data: { customer_id: 8, customer_no: "CODEX-CPI-A-CUSTOMER", contract_body: "律所" } }));
const subjects = contracts.map((contract, index) => ({ fee_id: index + 11, case_record_id: index + 21, case_no: `CODEX-CPI-A-CASE${index}`, contract_record_id: contract.id, contract_no: contract.serial_no, amount: 100, invoiceable_amount: 100, fee_type: "代理费", received_date: "2026-09-14", received_amount: 50, invoiced_amount: 0 }));
const values = { amount: 240, case_fee_ids: [11, 12], case_fee_allocations: [{ fee_id: 11, amount: 120 }, { fee_id: 12, amount: 120 }], service_items: [{ service_name: "Service", quantity: 2, unit_price: 120, amount: 240, tax_rate: 6, tax_amount: 7 }], invoice_title: "CODEX-CPI-A", taxpayer_id: "CODEX-CPI-A", remark: "" };

test("single and multiple contract URLs survive a new page without session storage", () => {
  for (const list of [contracts.slice(0, 1), contracts]) {
    const route = buildContractInvoiceRoute(list);
    const match = route.match(/^contract-invoice-apply-(\d+)-(.+)$/);
    assert.deepEqual(readContractInvoiceRoute(Number(match[1]), match[2]), list.map(({ id, serial_no }) => ({ id, serial_no })));
  }
  assert.throws(() => readContractInvoiceRoute(2, encodeURIComponent(JSON.stringify([{ id: 1, serial_no: "wrong" }]))));
  assert.throws(() => readContractInvoiceRoute(1, encodeURIComponent(JSON.stringify([{ id: 1, serial_no: "A" }, { id: 1, serial_no: "A" }]))));
});

test("same customer drafts are permitted; cross customer identity or accounting body is blocked", () => {
  assert.doesNotThrow(() => validateInvoiceContracts(contracts));
  assert.throws(() => validateInvoiceContracts([contracts[0], { ...contracts[1], customer: "Different" }]), /同一客户/);
  assert.throws(() => validateInvoiceContracts([contracts[0], { ...contracts[1], data: { ...contracts[1].data, customer_id: 9 } }]), /同一客户/);
  assert.throws(() => validateInvoiceContracts([contracts[0], { ...contracts[1], data: { ...contracts[1].data, contract_body: "平台" } }]), /不能合并/);
});

test("customer defaults use explicit invoicing fields then basic and registration fallbacks and clear missing fields", () => {
  const result = customerInvoiceDefaults({ title: "Customer", data: { credit_code: "TAX", contact_address: "Contact address", registered_address: "Registration", phone: "Phone", bank_name: "Bank", bank_account: "Account" } });
  assert.equal(result.invoice_title, "Customer"); assert.equal(result.taxpayer_id, "TAX"); assert.equal(result.invoice_address, "Contact address");
  assert.equal(result.invoice_phone, "Phone"); assert.equal(result.bank_name, "Bank"); assert.equal(result.bank_account, "Account");
  assert.equal(customerInvoiceDefaults({ data: { registered_address: "Registration" } }).invoice_address, "Registration");
  assert.equal(customerInvoiceDefaults({ data: {} }).bank_account, "");
});

test("filtering and paging do not change the selected allocation amounts", () => {
  const selected = selectedInvoiceAllocations([11, 12], values.case_fee_allocations, subjects);
  assert.deepEqual(selected, values.case_fee_allocations);
  assert.equal(filterInvoiceSubjects(subjects, { contract_no: contracts[1].serial_no }).length, 1);
  assert.equal(filterInvoiceSubjects(subjects, { received_from: "2026-09-15" }).length, 0);
  assert.deepEqual(selectedInvoiceAllocations([11, 12], selected, subjects), selected);
  assert.throws(() => selectedInvoiceAllocations([99], [], subjects), /不存在/);
});

test("partial invoices default to remaining balance and missing financial amounts cannot become zero", () => {
  assert.equal(selectedInvoiceAllocations([11], [], [{ ...subjects[0], invoiceable_amount: 40, invoiced_amount: 60 }])[0].amount, 40);
  assert.throws(() => selectedInvoiceAllocations([11], [], [{ ...subjects[0], amount: null, invoiceable_amount: null }]), /缺失/);
});

test("explicit high invoices and independent tax amounts are accepted without clipping", () => {
  assert.deepEqual(validateInvoiceAmounts(values, subjects, [11, 12]), values.case_fee_allocations);
  const result = buildInvoiceApplicationPayload({ values: { ...values, customer: contracts[0].customer }, contracts,
    cases: subjects.map(row => ({ id: row.case_record_id, serial_no: row.case_no })),
    caseFees: subjects.map(row => ({ id: row.fee_id, customer: contracts[0].customer, data: row })), requireSource: true });
  assert.equal(result.ok, true);
  assert.equal(result.payload.contract_record_id, null); assert.equal(result.payload.case_no, "");
  assert.deepEqual(result.payload.case_fee_allocations, values.case_fee_allocations);
  assert.equal(result.payload.service_items[0].tax_amount, 7);
});

test("negative, missing, mismatched and duplicate allocations and inconsistent service products are rejected", () => {
  assert.throws(() => validateInvoiceAmounts({ ...values, amount: 200 }, subjects, [11, 12]), /逐费分配/);
  assert.throws(() => validateInvoiceAmounts({ ...values, case_fee_allocations: [{ fee_id: 11, amount: -1 }, { fee_id: 12, amount: 241 }] }, subjects, [11, 12]), /大于0/);
  assert.throws(() => validateInvoiceAmounts({ ...values, case_fee_allocations: [{ fee_id: 11, amount: 120 }, { fee_id: 11, amount: 120 }] }, subjects, [11, 12]), /不一致/);
  assert.throws(() => validateInvoiceAmounts({ ...values, service_items: [{ ...values.service_items[0], unit_price: 1 }] }, subjects, [11, 12]), /数量乘以单价/);
  assert.throws(() => validateInvoiceAmounts({ ...values, service_items: [{ ...values.service_items[0], tax_rate: 101 }] }, subjects, [11, 12]), /完整填写/);
});

function makeActions({ submitFails = false, forbidden = false } = {}) {
  const posts = [], notifications = [], navigations = [], clear = [];
  const source = fs.readFileSync(new URL("./services/financeActions.tsx", import.meta.url), "utf8");
  const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const module = { exports: {} };
  const api = { post: async (url, body) => { posts.push({ url, body }); if (submitFails && url.endsWith("/submit")) throw new Error("CODEX isolated submit failure"); return { data: { id: 90, serial_no: "CODEX-CPI-A-INVOICE" } }; } };
  const require = id => {
    if (id === "antd") return { message: Object.fromEntries(["error", "warning", "success"].map(key => [key, value => notifications.push([key, value])])) };
    if (id.endsWith("/api")) return { api };
    if (id.endsWith("financeInvoiceHelpers.mjs")) return { buildInvoiceApplicationPayload };
    if (id.endsWith("contractInvoiceApplication")) return { validateInvoiceAmounts, validateInvoiceContracts };
    if (id.endsWith("contractWorkflowPolicy.mjs")) return { extractContractErrorMessage: error => error.message, normalizeContractActionResponse: () => ({ ok: true }) };
    return {};
  };
  vm.runInNewContext(js, { require, exports: module.exports });
  let busy = false;
  const gate = { tryEnter: () => { if (busy) return false; busy = true; return true; }, leave: () => { busy = false; } };
  const context = { invoiceTarget: contracts[0], invoiceContracts: contracts, invoiceSubjects: subjects, selectedInvoiceObjectKeys: [11, 12],
    invoiceForm: { validateFields: async () => structuredClone(values), resetFields: () => clear.push(true) },
    contractMutationGates: { current: { invoice: gate } }, contractCapabilities: contract => ({ canInvoice: !(forbidden && contract.id === 2) }),
    denyContractAction: () => notifications.push(["denied"]), setInvoiceSaving: () => {}, setInvoiceTarget: () => {}, onNavigate: key => navigations.push(key) };
  return { actions: module.exports.createContractFinanceActions(context), posts, notifications, navigations, clear };
}

test("actual create handler posts both contracts/cases and exact amounts then submits once", async () => {
  const flow = makeActions();
  await flow.actions.createContractInvoice();
  assert.equal(flow.posts.length, 2);
  assert.equal(flow.posts[0].url, "/finance/invoices");
  assert.deepEqual(flow.posts[0].body.case_fee_ids, [11, 12]);
  assert.deepEqual(flow.posts[0].body.case_fee_allocations, values.case_fee_allocations);
  assert.equal(flow.posts[0].body.contract_record_id, null);
  assert.equal(flow.posts[1].url, "/finance/invoices/90/submit");
  assert.deepEqual(flow.navigations, ["finance-invoice-mine"]);
});

test("submit failure preserves one server draft and routes to mine without a second creation", async () => {
  const flow = makeActions({ submitFails: true }); await flow.actions.createContractInvoice();
  assert.equal(flow.posts.length, 2); assert.equal(flow.posts.filter(row => row.url === "/finance/invoices").length, 1);
  assert.match(flow.notifications.find(row => row[0] === "error")[1], /草稿/);
  assert.deepEqual(flow.navigations, ["finance-invoice-mine"]);
});

test("second-contract permission failure prevents any create or submit", async () => {
  const flow = makeActions({ forbidden: true }); await flow.actions.createContractInvoice();
  assert.equal(flow.posts.length, 0); assert.equal(flow.notifications[0][0], "denied");
});

function loadDataModule(get) {
  const source = fs.readFileSync(new URL("./contractInvoiceData.ts", import.meta.url), "utf8");
  const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const exports = {};
  vm.runInNewContext(js, { exports, require: id => id.endsWith("/api") ? { api: { get } } : { customerInvoiceDefaults, validateInvoiceContracts } });
  return exports;
}

test("candidate loader calls every authorized contract and preserves missing money rather than inventing zero", async () => {
  const calls = [];
  const module = loadDataModule(async url => {
    calls.push(url);
    if (url === "/records/8") return { data: { id: 8, module: "customer", title: contracts[0].customer, serial_no: contracts[0].data.customer_no, data: { credit_code: "CODEX-TAX" } } };
    const id = Number(url.split("/")[2]);
    return { data: { items: [{ ...subjects[id - 1], received_amount: undefined }] } };
  });
  const result = await module.loadContractInvoiceData(contracts);
  assert.equal(result.subjects.length, 2); assert.equal(result.subjects[0].received_amount, undefined);
  assert.deepEqual(calls, ["/contracts/1/invoice-candidates", "/contracts/2/invoice-candidates", "/records/8"]);
  assert.equal(result.defaults.taxpayer_id, "CODEX-TAX");
});

test("candidate failure aborts the whole multi-contract load rather than returning first contract only", async () => {
  const module = loadDataModule(async url => {
    if (url.includes("/2/")) throw new Error("Forbidden");
    return { data: { items: [subjects[0]] } };
  });
  await assert.rejects(() => module.loadContractInvoiceData(contracts), /Forbidden/);
});

test("conflicting fee ownership and ambiguous customer records fail closed", async () => {
  const module = loadDataModule(async () => ({ data: { items: [subjects[0]] } }));
  await assert.rejects(() => module.loadContractInvoiceData(contracts), /冲突/);
  const ambiguous = loadDataModule(async url => ({ data: { items: url === "/records" ? [1, 2].map(id => ({ id, module: "customer", title: contracts[0].customer })) : [] } }));
  await assert.rejects(() => ambiguous.loadContractInvoiceData([{ ...contracts[0], data: {} }]), /多份档案/);
});

test("actual shared service control keeps amount read-only and recalculates product without changing tax or extension fields", () => {
  const source = fs.readFileSync(new URL("./InvoiceServiceItemsTable.tsx", import.meta.url), "utf8");
  const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX } }).outputText;
  const data = { service_items: [{ service_name: "CODEX-Service", quantity: 2, unit_price: 120, amount: 240, tax_amount: 7, tax_rate: 6, legacy_id: 88 }] };
  const form = { getFieldValue: path => path.reduce((item, key) => item[key], data), setFieldValue: (path, value) => { path.slice(0, -1).reduce((item, key) => item[key], data)[path.at(-1)] = value; } };
  const exports = {};
  const jsx = (type, props) => ({ type, props });
  vm.runInNewContext(js, { exports, require: id => {
    if (id === "react/jsx-runtime") return { jsx, jsxs: jsx, Fragment: "fragment" };
    if (id === "antd") return { Form: { List: "list", Item: "item", useWatch: () => data.service_items }, Table: { Summary: {} }, Button: "button", Input: "input", InputNumber: "number", Tooltip: "tooltip" };
    if (id.includes("icons")) return {};
    return { invoiceMoney: value => Math.round((Number(value) + Number.EPSILON) * 100) / 100, invoiceTotal: rows => rows.reduce((sum, row) => sum + Number(row.amount || 0), 0) };
  } });
  const list = exports.InvoiceServiceItemsTable({ form });
  assert.equal(list.props.name, "service_items");
  const table = list.props.children([{ key: 0, name: 0 }], { add() {}, remove() {} }).props.children[0];
  const columns = table.props.columns;
  const amount = columns.find(col => col.title === "金额").render(null, { name: 0 }).props.children;
  assert.equal(amount.props.readOnly, true);
  const price = columns.find(col => col.title === "单价").render(null, { name: 0 }).props.children;
  price.props.onChange(125);
  assert.equal(data.service_items[0].amount, 250);
  assert.equal(data.service_items[0].tax_amount, 7);
  assert.equal(data.service_items[0].legacy_id, 88);
});
