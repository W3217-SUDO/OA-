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
        ? "export const message=globalThis.__paymentReworkMessages; export const Button=()=>null; export const Dropdown=()=>null; export const Modal=globalThis.__paymentReworkModal || {}; export const Table=()=>null; export const Space=()=>null;"
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

test("案件费用只在发票列显示真实开票，票据和核销仍保留独立入口", async () => {
  const { createExternalCaseFeeColumns } = await loadActualModule("../src/legal/columns/externalCaseFeeColumns.tsx");
  const opened = [];
  const columns = createExternalCaseFeeColumns({
    openRelatedInvoice: row => opened.push(["invoice", row.id]),
    openCaseReceiptFiles: row => opened.push(["voucher", row.id]),
  });
  const cell = (name, row) => columns.find(column => column.title === name).render(undefined, row);
  const row = { id: 3, title: "一审诉讼费", data: { paid_date: "2026-10-12",
    writeoff_voucher_record_id: 9,
    receipt_files: [{ attachment_id: 7, bill_no: "公告费", bill_date: "2026-10-11" }] } };
  assert.equal(cell("开票日期", row), "—");
  assert.equal(cell("发票号", row), "—");
  assert.equal(cell("核销日期", row), "2026-10-12");
  cell("缴费凭证", row).props.onClick();
  const invoiced = { ...row, data: { ...row.data, invoice_no: "FP-REAL", invoice_date: "2026-10-10", invoice_record_id: 10 } };
  assert.equal(cell("开票日期", invoiced), "2026-10-10");
  assert.equal(cell("发票号", invoiced).props.children, "FP-REAL");
  cell("发票号", invoiced).props.onClick();
  assert.deepEqual(opened, [["voucher", 3], ["invoice", 3]]);
  assert.equal(cell("缴费凭证", { ...row, data: { writeoff_voucher_record_id: 9 } }).props.children, "查看凭证");
});

test("五类第三方回款日期和金额为斜杠，官费代理费未到账为零并保留真实回款链接", async () => {
  const { createExternalCaseFeeColumns } = await loadActualModule("../src/legal/columns/externalCaseFeeColumns.tsx");
  let opened;
  const columns = createExternalCaseFeeColumns({ openRelatedIncomingPayment: row => { opened = row.id; } });
  const cell = (name, row) => columns.find(column => column.title === name).render(undefined, row);
  for (const name of ["公告费", "公证服务费", "担保费", "鉴定费", "检索费"]) {
    for (const key of ["expense_subtype", "fee_type_name", "case_fee_type_name", "fee_type"]) {
      const row = { title: "独立测试费用", data: { [key]: name, received_amount: 0, received_at: "2026-10-12" } };
      assert.equal(cell("回款金额", row), "/");
      assert.equal(cell("回款日期", row), "/");
    }
  }
  assert.equal(cell("回款金额", { data: { receipt_allocation_applicable: false, received_amount: 8 } }), "/");
  for (const name of ["一审诉讼费", "二审诉讼费", "保全费", "公证费", "代理费", "律师代理费"]) {
    for (const received_amount of [undefined, null, "", "/", "\\", 0]) {
      const row = { title: name, data: { expense_subtype: name, received_amount } };
      assert.equal(cell("回款金额", row), 0);
      assert.equal(cell("回款日期", row), "—");
    }
  }
  const row = { id: 12, data: { receipt_allocation_applicable: true, expense_subtype: "律师代理费", received_amount: 20, received_at: "2026-10-12" } };
  assert.equal(cell("回款金额", row).props.children, 20);
  cell("回款金额", row).props.onClick();
  assert.equal(opened, 12);
  assert.equal(cell("回款日期", row), "2026-10-12");
});

test("凭证弹窗读取专属核销关联并保留同时存在的真实发票附件及操作", async () => {
  let dialog;
  const requested = [];
  globalThis.__paymentReworkModal = { info: value => { dialog = value; } };
  globalThis.__paymentReworkMessages = { warning: assert.fail, error: assert.fail };
  globalThis.__paymentReworkApi = { get: async (url, options) => {
    requested.push([url, options?.params]);
    const recordId = options?.params?.record_id;
    const items = url === "/attachments" && recordId === 9
      ? [{ id: 90, category: "付款凭证", original_name: "CODEX-proof.pdf" }]
      : url === "/attachments" && recordId === 10
        ? [{ id: 100, category: "案件发票文件", original_name: "CODEX-invoice.pdf" }] : [];
    return { data: { items } };
  } };
  const { createCaseFinanceActions } = await loadActualModule("../src/legal/services/financeActions.tsx");
  const actions = createCaseFinanceActions({});
  await actions.openCaseReceiptFiles({ id: 3, serial_no: "CODEX-FEE", data: { writeoff_voucher_record_id: 9, invoice_record_id: 10 } });
  assert.deepEqual(requested.filter(([url, params]) => url === "/attachments" && !params.category).map(([, params]) => params.record_id), [9, 10]);
  assert.deepEqual(dialog.content.props.dataSource.map(row => [row.attachmentId, row.source, row.path]),
    [[90, "缴费凭证", "/attachments/90/download"], [100, "发票文件", "/attachments/100/download"]]);
  const operation = dialog.content.props.columns.find(column => column.title === "操作");
  assert.deepEqual(operation.render(undefined, dialog.content.props.dataSource[0]).props.children.map(button => button.props.children), ["查看", "下载"]);
  requested.length = 0;
  await actions.openCaseReceiptFiles({ id: 3, serial_no: "CODEX-FEE", data: { writeoff_voucher_record_id: 9 } });
  assert.equal(dialog.content.props.dataSource[0].source, "缴费凭证");
  await actions.openCaseReceiptFiles({ id: 3, serial_no: "CODEX-FEE", data: { invoice_record_id: 9 } });
  assert.equal(dialog.content.props.dataSource[0].attachmentId, 90);
  delete globalThis.__paymentReworkModal;
  delete globalThis.__paymentReworkMessages;
  delete globalThis.__paymentReworkApi;
});

test("付款单显示核销单据号，不以并存的真实发票号替代，旧付款字段仍可读", async () => {
  const { PaymentDocument } = await loadActualModule("../src/finance/PaymentDocument.tsx");
  const find = node => {
    if (!node || typeof node !== "object") return undefined;
    if (node.key === "单据号") return node.props.children[1];
    for (const child of [node.props?.children].flat(Infinity)) {
      const result = find(child);
      if (result !== undefined) return result;
    }
  };
  assert.equal(find(PaymentDocument({ row: { data: { invoice_no: "FP-REAL", writeoff_voucher_no: "PAYMENT-ONLY" } }, printing: false })), "PAYMENT-ONLY");
  assert.equal(find(PaymentDocument({ row: { data: { invoice_no: "OLD-PAYMENT" } }, printing: false })), "OLD-PAYMENT");
});
