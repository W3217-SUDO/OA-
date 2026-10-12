import assert from "node:assert/strict";
import test from "node:test";
import { build } from "esbuild";
import { fileURLToPath } from "node:url";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";

let moduleSequence = 0;
async function loadActualModule(relative) {
  const compiled = await build({ entryPoints: [fileURLToPath(new URL(relative, import.meta.url))],
    bundle: true, write: false, platform: "node", format: "esm", logLevel: "silent",
    plugins: [{ name: "isolated-adapters", setup(plugin) {
      // 仅转换 Vite 资产查询，读取真实文件，不替换业务模块或断言。
      plugin.onResolve({ filter: /\?(?:worker&url|url&inline)$/ }, (args) => ({
        path: createRequire(args.importer).resolve(args.path.split("?")[0]), namespace: "vite-asset",
      }));
      plugin.onLoad({ filter: /.*/, namespace: "vite-asset" }, (args) => ({ contents: readFileSync(args.path), loader: "dataurl" }));
      plugin.onResolve({ filter: /\.css$/ }, (args) => ({ path: args.path, namespace: "test-style" }));
      plugin.onLoad({ filter: /.*/, namespace: "test-style" }, () => ({ contents: "", loader: "js" }));
      plugin.onResolve({ filter: /^antd$|^(?:\.\.\/|\.\/)+api$/ }, (args) => ({ path: args.path, namespace: "test-adapter" }));
      plugin.onLoad({ filter: /.*/, namespace: "test-adapter" }, (args) => ({ contents: args.path === "antd"
        ? "export const message=globalThis.__paymentReworkMessages; export const Button=()=>null; export const Dropdown=()=>null; export const Modal={}; export const Table=()=>null; export const Space=()=>null;"
        : "export const api=globalThis.__paymentReworkApi;", loader: "js" }));
    } }] });
  return import(`data:text/javascript;base64,${Buffer.from(compiled.outputFiles[0].text).toString("base64")}#${++moduleSequence}`);
}

test("实际案件请款入口使用跨入口可申请余额，零余额不打开申请，驳回后可按释放余额重提", async () => {
  const warnings = [];
  let reads = 0;
  let opened;
  let values;
  globalThis.__paymentReworkMessages = { warning: (value) => warnings.push(value), error: (value) => { throw new Error(value); } };
  globalThis.__paymentReworkApi = { get: async () => { reads++; return { data: { items: [{ id: 1 }] } }; } };
  const { createCaseFinanceActions } = await loadActualModule("../src/legal/services/financeActions.tsx");
  const actions = createCaseFinanceActions({ counselDetailCapabilities: { can_create_finance: true },
    paymentRequestForm: { resetFields: () => {}, setFieldsValue: (value) => { values = value; } },
    setPaymentTypeSearch: () => {}, setPaymentRequestFee: (value) => { opened = value; },
    setCasePaymentTypesLoading: () => {}, setCasePaymentTypes: () => {}, setCasePaymentTypesError: () => {},
    casePaymentTypeRequestRef: { current: 0 }, casePaymentTypeFeeRef: { current: null } });
  const fee = { id: 1, status: "部分付款", data: { amount: 100, paid_amount: 30,
    payment_requested_amount: 90, payment_remaining_amount: 10, payment_type_id: 1 } };
  await actions.openPaymentRequest(fee);
  assert.equal(values.amount, 10);
  assert.equal(opened, fee);
  opened = null;
  await actions.openPaymentRequest({ ...fee, data: { ...fee.data, payment_remaining_amount: 0 } });
  assert.equal(reads, 1);
  assert.equal(opened, null);
  assert.match(warnings[0], /没有可申请付款的余额/);
  await actions.openPaymentRequest({ ...fee, status: "已驳回", data: { ...fee.data, payment_remaining_amount: 70 } });
  assert.equal(values.amount, 70);
  assert.equal(reads, 2);
  delete globalThis.__paymentReworkApi;
  delete globalThis.__paymentReworkMessages;
});

test("实际请款列表显示本轮申请金额，保留合同请款及隐藏金额行为", async () => {
  const { createPaymentOriginalColumns } = await loadActualModule("../src/finance/columns/paymentOriginalColumns.tsx");
  const column = createPaymentOriginalColumns({}).find((item) => item.title === "申请金额");
  const render = (data) => column.render(undefined, { data });
  assert.equal(render({ amount: 100, payment_request_amount: 30 }), render({ amount: 30 }));
  assert.equal(render({ amount: 60 }), render({ amount: 100, payment_request_amount: 60 }));
  assert.equal(render({ payment_request_amount: 30 }), "—");
});

test("实际审批入口先服务端筛选，完整读取超过200条待办并分离普通费用与合同单", async () => {
  const calls = [];
  const contracts = Array.from({ length: 205 }, (_, id) => ({ id: id + 1, module: "contract_payment", status: "待审批", data: { applicant: "同一申请人", amount: 50, lines: [{ fee_type: "官方费用", case_no: "独立测试案件" }] } }));
  const direct = { id: 206, module: "finance", status: "待审批", data: { applicant: "同一申请人", amount: 30 } };
  const rows = [...contracts, direct];
  globalThis.__paymentReworkMessages = { error: (value) => { throw new Error(value); } };
  globalThis.__paymentReworkApi = { get: async (path, options) => {
    calls.push([path, options?.params]);
    if (path === "/finance/payment-applications/query") {
      assert.equal(options.params.scope, "audit");
      const start = (options.params.page - 1) * options.params.page_size;
      return { data: { items: rows.slice(start, start + options.params.page_size), total: rows.length } };
    }
    if (path === "/auth/me") return { data: { username: "审批人", display_name: "审批人", role: "admin" } };
    return { data: { items: [] } };
  } };
  const { createFinanceQueriesActions } = await loadActualModule("../src/finance/services/queriesActions.tsx");
  let fees, payments, ready;
  const context = {
    initialView: "finance-payment-audit", contractPaymentSource: { active: false },
    financeTransactionMeta: { pageSize: 100 }, setFinanceDataReady: value => { ready = value; },
    setFees: value => { fees = value; }, setContractPayments: value => { payments = value; },
    setLoading() {}, setFinanceFeeListMeta() {}, setTransactions() {}, setFinanceTransactionMeta() {},
    setRole() {}, setCurrentUser() {}, setFinancePeople() {}, setCases() {},
  };
  await createFinanceQueriesActions(context).loadForTab("fees");
  assert.equal(payments.length, 205);
  assert.deepEqual(fees, [direct]);
  assert.equal(new Set(payments.map(row => row.id)).size, 205);
  assert.equal(payments[204].data.amount, 50);
  assert.equal(ready, true);
  assert.equal(calls.filter(([path]) => path === "/finance/payment-applications/query").length, 2);
  assert.ok(!calls.some(([path, params]) => path === "/records" && ["finance", "contract_payment"].includes(params?.module)));
  delete globalThis.__paymentReworkApi;
  delete globalThis.__paymentReworkMessages;
});

test("实际审批分页缺失不能静默显示不完整待办", async () => {
  const errors = [];
  let replaced = false, ready;
  globalThis.__paymentReworkMessages = { error: value => errors.push(value) };
  globalThis.__paymentReworkApi = { get: async () => ({ data: { items: [], total: 1 } }) };
  const { createFinanceQueriesActions } = await loadActualModule("../src/finance/services/queriesActions.tsx");
  await createFinanceQueriesActions({ initialView: "finance-payment-audit", contractPaymentSource: { active: false },
    setLoading() {}, setFinanceDataReady: value => { ready = value; }, setFees: () => { replaced = true; },
  }).loadForTab("fees");
  assert.equal(replaced, false);
  assert.equal(ready, true);
  assert.equal(errors.length, 1);
  assert.match(errors[0], /数据未完整返回/);
  delete globalThis.__paymentReworkApi;
  delete globalThis.__paymentReworkMessages;
});
