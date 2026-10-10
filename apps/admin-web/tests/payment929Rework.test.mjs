import assert from "node:assert/strict";
import test from "node:test";
import { build } from "esbuild";
import { fileURLToPath } from "node:url";

async function loadActualModule(relative) {
  const compiled = await build({ entryPoints: [fileURLToPath(new URL(relative, import.meta.url))],
    bundle: true, write: false, platform: "node", format: "esm", logLevel: "silent",
    plugins: [{ name: "isolated-adapters", setup(plugin) {
      plugin.onResolve({ filter: /\.css$/ }, (args) => ({ path: args.path, namespace: "test-style" }));
      plugin.onLoad({ filter: /.*/, namespace: "test-style" }, () => ({ contents: "", loader: "js" }));
      plugin.onResolve({ filter: /^antd$|^\.\.\/\.\.\/api$/ }, (args) => ({ path: args.path, namespace: "test-adapter" }));
      plugin.onLoad({ filter: /.*/, namespace: "test-adapter" }, (args) => ({ contents: args.path === "antd"
        ? "export const message=globalThis.__paymentReworkMessages; export const Button=()=>null; export const Dropdown=()=>null; export const Modal={}; export const Table=()=>null; export const Space=()=>null;"
        : "export const api=globalThis.__paymentReworkApi;", loader: "js" }));
    } }] });
  return import(`data:text/javascript;base64,${Buffer.from(compiled.outputFiles[0].text).toString("base64")}`);
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
