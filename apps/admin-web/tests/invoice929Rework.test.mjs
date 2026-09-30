import assert from "node:assert/strict";
import test from "node:test";
import { build } from "esbuild";
import { fileURLToPath } from "node:url";
import { invoiceCurrentSourceFields, invoiceEditValues } from "../src/finance/invoiceDetails.mjs";
import { buildInvoiceApplicationPayload } from "../src/financeInvoiceHelpers.mjs";

const fee = (id, external = "CURRENT", contract = 20) => ({ id, customer: "CODEX-929-RW09-客户", data: {
  contract_id: contract, contract_no: `SH-${contract}`, case_id: 30, case_no: "CASE-30", external_contract_no: external,
} });

test("旧草稿及页外所选费用取当前合同号码，保留金额分配和服务内容", () => {
  const old = invoiceEditValues({ customer: "CODEX-929-RW09-客户", data: {
    external_contract_no: "OLD", case_fee_ids: [81, 99], amount: 75, extra_amount: 5,
    case_fee_allocations: [{ fee_id: 81, amount: 25 }, { fee_id: 99, amount: 50 }],
    service_items: [{ service_name: "用户录入服务", quantity: 1, unit_price: 75, amount: 75, tax_rate: 0, tax_amount: 0 }],
    invoice_title: "用户抬头", email: "test@example.invalid", remark: "用户备注",
  } });
  const rows = [fee(99), fee(81)];
  const refreshed = { ...old, ...invoiceCurrentSourceFields(rows, [81, 99]) };
  assert.equal(refreshed.external_contract_no, "CURRENT");
  assert.deepEqual(Object.fromEntries(Object.entries(refreshed).filter(([key]) => key !== "external_contract_no")),
    Object.fromEntries(Object.entries(old).filter(([key]) => key !== "external_contract_no")));
  const result = buildInvoiceApplicationPayload({ values: refreshed, caseFees: rows, requireSource: true });
  assert.equal(result.ok, true);
  assert.equal(result.payload.amount, 75);
  assert.equal(result.payload.external_contract_no, "CURRENT");
  assert.deepEqual(result.payload.case_fee_allocations, old.case_fee_allocations);
  assert.deepEqual(result.payload.service_items, old.service_items);
});

test("合同号码清空后不可复活旧值，多合同单独显示明细且无错误汇总", () => {
  assert.deepEqual(invoiceCurrentSourceFields([fee(81, "")], [81]), { external_contract_no: "" });
  assert.deepEqual(invoiceCurrentSourceFields([fee(81), fee(99, "OTHER", 21)], [81, 99]), { external_contract_no: "" });
  assert.deepEqual(invoiceCurrentSourceFields([], []), { external_contract_no: "" });
});

test("缺失或无权所选费用明确失败，不使用陈旧来源", () => {
  assert.throws(() => invoiceCurrentSourceFields([fee(81)], [81, 99]), /不存在或无权访问/);
});

test("实际保存handler刷新失败不写入；过期响应不覆盖；成功提交使用当前所选来源并保留金额", async () => {
  const writes = [];
  const errors = [];
  let getResponse;
  globalThis.__invoiceReworkApi = {
    get: (...args) => getResponse(...args),
    post: async (url, body) => { writes.push({ url, body }); return { data: { id: 100, data: body } }; },
  };
  globalThis.__invoiceReworkMessages = { error: (value) => errors.push(value), success: () => {} };
  const compiled = await build({ entryPoints: [fileURLToPath(new URL("../src/finance/services/invoicesActions.tsx", import.meta.url))],
    bundle: true, write: false, platform: "node", format: "esm", logLevel: "silent", plugins: [{ name: "isolated-adapters", setup(plugin) {
      plugin.onResolve({ filter: /^antd$|^\.\.\/\.\.\/api$/ }, (args) => ({ path: args.path, namespace: "test-adapter" }));
      plugin.onLoad({ filter: /.*/, namespace: "test-adapter" }, (args) => ({ contents: args.path === "antd"
        ? "export const message = globalThis.__invoiceReworkMessages; export const Modal = {};"
        : "export const api = globalThis.__invoiceReworkApi;", loader: "js" }));
    } }] });
  const { createFinanceInvoicesActions } = await import(`data:text/javascript;base64,${Buffer.from(compiled.outputFiles[0].text).toString("base64")}`);
  let values = { customer: "CODEX-929-RW09-客户", case_fee_ids: [81], external_contract_no: "OLD", amount: 37,
    case_fee_allocations: [{ fee_id: 81, amount: 37 }],
    service_items: [{ service_name: "保留服务", quantity: 1, unit_price: 37, amount: 37, tax_rate: 0, tax_amount: 0 }] };
  let updates = 0;
  const form = { getFieldValue: (key) => values[key], setFieldsValue: (patch) => { values = { ...values, ...patch }; },
    validateFields: async () => ({ ...values }), resetFields: () => {} };
  const context = { invoiceForm: form, invoiceEditTarget: null, cases: [],
    setContracts: () => updates++, setCustomers: () => updates++, setInvoiceCandidateFees: () => updates++,
    setInvoiceEditTarget: () => {}, setInvoiceOpen: () => {}, load: async () => {} };
  const actions = createFinanceInvoicesActions(context);
  getResponse = async () => { throw { response: { data: { detail: "来源读取失败" } } }; };
  await actions.createInvoice(false);
  assert.equal(writes.length, 0);
  assert.deepEqual(errors, ["来源读取失败"]);
  assert.equal(values.amount, 37);
  const response = { data: { items: [], selected_items: [fee(81)], total: 0, page: 2, page_size: 1 } };
  getResponse = async () => response;
  await actions.loadInvoiceReferenceData({ isCurrent: () => false });
  assert.equal(updates, 0);
  assert.equal(values.external_contract_no, "OLD");
  await actions.createInvoice(false);
  assert.equal(writes.length, 1);
  assert.equal(writes[0].body.external_contract_no, "CURRENT");
  assert.equal(writes[0].body.amount, 37);
  assert.deepEqual(writes[0].body.case_fee_allocations, [{ fee_id: 81, amount: 37 }]);
  assert.equal(writes[0].body.service_items[0].service_name, "保留服务");
  delete globalThis.__invoiceReworkApi;
  delete globalThis.__invoiceReworkMessages;
});
