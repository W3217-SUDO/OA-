import assert from "node:assert/strict";
import fs from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import vm from "node:vm";
import dayjs from "dayjs";
import ts from "typescript";

const require = createRequire(import.meta.url);
const sourceRoot = new URL("../../src/finance/", import.meta.url);
const Button = () => null;
const Select = () => null;
const Table = () => null;
const warnings = [];
const ui = {
  Button, Select, Table,
  Alert: () => null, DatePicker: () => null, Form: () => null,
  Input: () => null, Modal: () => null, Space: () => null,
  message: { warning: (text) => warnings.push(text) },
};

function loadFinanceModule(name, dependencies = {}) {
  const source = fs.readFileSync(new URL(name, sourceRoot), "utf8");
  const output = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
      jsx: ts.JsxEmit.ReactJSX,
      esModuleInterop: true,
    },
  }).outputText;
  const module = { exports: {} };
  const mocks = {
    antd: ui,
    "@ant-design/icons": { PlusOutlined: () => null, ReloadOutlined: () => null, UploadOutlined: () => null },
    "../components/ResizableTable": Table,
    "../financeRefundHelpers.mjs": { refundPageSizeOptions: [15, 30], refundStatusOptions: ["全部", "待审批"] },
    ...dependencies,
  };
  vm.runInNewContext(output, {
    module,
    exports: module.exports,
    require: (specifier) => specifier in mocks ? mocks[specifier] : require(specifier),
  }, { filename: name });
  return module.exports;
}

function nodes(element) {
  if (Array.isArray(element)) return element.flatMap(nodes);
  if (!element || typeof element !== "object" || !("props" in element)) return [];
  return [element, ...nodes(element.props.children)];
}

function button(element, text) {
  const found = nodes(element).find((node) => node.type === Button && node.props.children === text);
  assert.ok(found, `missing button ${text}`);
  return found;
}

test("original query values keep zero bounds and reject malformed date or text values", () => {
  const { dateQueryRange, amountQueryRange, queryArray, queryTextValue } = loadFinanceModule("originalQuery.ts");
  const range = [dayjs("2026-09-01"), dayjs("2026-09-30")];
  assert.equal(dateQueryRange(range)[0].format("YYYY-MM-DD"), "2026-09-01");
  assert.equal(dateQueryRange(range)[1].format("YYYY-MM-DD"), "2026-09-30");
  assert.equal(dateQueryRange(["2026-09-01", 123])[0], null);
  assert.equal(dateQueryRange({ 0: range[0] }), undefined);
  assert.equal(amountQueryRange([0, 250])[0], 0);
  assert.equal(amountQueryRange([0, 250])[1], 250);
  assert.equal(amountQueryRange(["bad", null])[0], null);
  assert.equal(queryArray([0, null])[0], 0);
  assert.equal(queryTextValue(0), 0);
  assert.equal(queryTextValue(false), undefined);
});

test("original query controls keep package refresh, upload, clear and route refresh actions", async () => {
  const { FinanceOriginalQueryView } = loadFinanceModule("FinanceOriginalQueryView.tsx");
  const calls = [];
  const file = { name: "statement.csv" };
  const base = {
    initialView: "finance-payment-package-manage", originalKind: "payment", title: "付款打包",
    sourceNotice: null, fields: null, routeConfig: { upload: true, clear: true },
    contractPaymentSource: { active: false }, bankUploadRef: { current: { click: () => calls.push("open-upload") } },
    onImportBankStatement: async (selected) => calls.push(["import", selected]),
    onSubmit: () => calls.push("query"), onClear: () => calls.push("clear"),
    onRefresh: async () => calls.push("refresh"), originalQuery: { routeField0: "CASE-1" },
    paymentPackageMeta: { page: 2, pageSize: 15 },
    onLoadPaymentPackages: async (...args) => calls.push(["package-refresh", ...args]),
    onOpenPaymentPackageEditor: () => calls.push("new-package"),
  };
  const view = FinanceOriginalQueryView(base);
  button(view, "查询").props.onClick();
  button(view, "刷新").props.onClick();
  button(view, "新增付款包").props.onClick();
  button(view, "上传").props.onClick();
  button(view, "清空").props.onClick();
  await nodes(view).find((node) => node.type === "input" && node.props.type === "file").props.onChange({ target: { files: [file] } });
  assert.equal(calls[0], "query");
  assert.equal(calls[1][0], "package-refresh");
  assert.equal(calls[1][1], base.originalQuery);
  assert.equal(calls[1][2], 2);
  assert.equal(calls[1][3], 15);
  assert.equal(calls[2], "new-package");
  assert.equal(calls[3], "open-upload");
  assert.equal(calls[4], "clear");
  assert.equal(calls[5][1], file);

  const audit = FinanceOriginalQueryView({ ...base, initialView: "finance-payment-audit", routeConfig: {} });
  button(audit, "刷新").props.onClick();
  assert.equal(calls.at(-1), "refresh");
  const blocked = FinanceOriginalQueryView({ ...base, contractPaymentSource: { active: true } });
  assert.equal(button(blocked, "查询").props.disabled, true);
});

test("receipts actions select the exact payment and initialize registration", () => {
  const { FinanceReceiptsActions } = loadFinanceModule("FinanceReceiptsView.tsx");
  const calls = [];
  const payment = { id: 7, receipt_no: "REC-7" };
  const base = {
    incoming: [payment], shownIncoming: [payment], columns: [], selectedRows: [7],
    onSelectedRowsChange: () => {}, onOpenAllocation: (row) => calls.push(row),
    canManage: true, form: {
      resetFields: () => calls.push("reset"),
      setFieldsValue: (value) => calls.push(value),
    },
    onOpenRegistration: () => calls.push("open"), loading: false,
  };
  const view = FinanceReceiptsActions(base);
  button(view, "已分配记录").props.onClick();
  button(view, "登记银行到账").props.onClick();
  assert.equal(calls[0], payment);
  assert.equal(calls[1], "reset");
  assert.equal(dayjs.isDayjs(calls[2].received_date), true);
  assert.equal(calls[3], "open");
  warnings.length = 0;
  button(FinanceReceiptsActions({ ...base, selectedRows: [99] }), "已分配记录").props.onClick();
  assert.match(warnings[0], /请选择一笔回款记录/);
  assert.equal(nodes(FinanceReceiptsActions({ ...base, canManage: false })).some((node) => node.type === Button && node.props.children === "登记银行到账"), false);
});

test("refund filters, selection export and batch status preserve callbacks", () => {
  const { FinanceRefundsActions } = loadFinanceModule("FinanceRefundsView.tsx");
  const calls = [];
  const props = {
    initialView: "finance-refund", isNotRequiredRoute: false, activeStatus: "待审批", statusFilter: "待审批",
    onStatusFilterChange: (value) => calls.push(["status", value]), groupFilter: "lawfirm",
    onGroupFilterChange: (value) => calls.push(["group", value]), selectedRows: [3],
    onSelectedRowsChange: (value) => calls.push(["selection", value]), meta: { page: 2, pageSize: 15, total: 30 },
    rows: [], columns: [], loading: false, load: async (...args) => calls.push(["load", ...args]),
    exportRows: async (selected) => calls.push(["export", selected]),
    onBatchStatusChange: (value) => calls.push(["batch-status", value]),
    onOpenBatchStatus: () => calls.push("open-batch"), onOpenCreation: () => calls.push("new-refund"),
    statusForRoute: () => "待审批",
  };
  const view = FinanceRefundsActions(props);
  const selectors = nodes(view).filter((node) => node.type === Select);
  selectors.find((node) => node.props["aria-label"] === "退款业务组筛选").props.onChange("trad");
  selectors.find((node) => node.props["aria-label"] === "退款状态筛选").props.onChange("全部");
  button(view, "导出选中").props.onClick();
  button(view, "退费进度修改").props.onClick();
  button(view, "清空").props.onClick();
  assert.equal(calls[1][0], "load");
  assert.equal(calls[1][5], "trad");
  assert.equal(calls[3][3], "全部");
  assert.equal(calls[4][0], "export");
  assert.equal(calls[4][1], true);
  assert.equal(calls[5][1], "待审批");
  assert.equal(calls[6], "open-batch");
  assert.equal(calls.at(-1)[0], "load");
  assert.equal(calls.at(-1)[5], "");
});

test("invoice application opens only after reference data loads", async () => {
  const { FinanceInvoicesActions } = loadFinanceModule("FinanceInvoicesView.tsx");
  const calls = [];
  const props = {
    rows: [], columns: [], loading: false,
    form: { resetFields: () => calls.push("reset"), setFieldsValue: (value) => calls.push(["defaults", value]) },
    loadReference: async () => calls.push("load"),
    onEditTargetChange: (value) => calls.push(["edit", value]),
    onSourceFeeChange: (value) => calls.push(["source", value]),
    onSelectedFeeIdsChange: (value) => calls.push(["selected", value]),
    onFeeAmountsChange: (value) => calls.push(["amounts", value]),
    onOpen: () => calls.push("open"),
  };
  FinanceInvoicesActions(props).props.onClick();
  await new Promise(setImmediate);
  assert.equal(calls[0], "load");
  assert.equal(calls.at(-1), "open");
  assert.equal(calls.find((item) => item[0] === "defaults")[1].invoice_type, "增值税普通发票");
  calls.length = 0;
  FinanceInvoicesActions({ ...props, loadReference: async () => { throw new Error("offline"); } }).props.onClick();
  await new Promise(setImmediate);
  assert.equal(calls.length, 0);
});

test("settlement context modal keeps action footer and linked-case task data", () => {
  const { SettlementContextModal } = loadFinanceModule("SettlementContextModal.tsx");
  const calls = [];
  const context = { mode: "task-create", caseRecords: [{ id: 3, serial_no: "CASE-3", data: {} }] };
  const props = {
    context, onClose: () => calls.push("close"), actionLoading: false,
    onSubmitLog: async () => calls.push("log"), onSubmitTask: async () => calls.push("task"),
    logContent: "", onLogContentChange: () => {},
    taskForm: { title: "Follow up", owner: "user", deadline: dayjs("2026-10-15"), priority: "普通" },
    onTaskFormChange: () => {}, financePeople: [], rows: [], displayPersonName: (value) => value,
  };
  const modal = SettlementContextModal(props);
  assert.match(modal.props.title, /新增案件任务（1 个案件）/);
  button(modal.props.footer, "创建任务").props.onClick();
  assert.equal(calls[0], "task");
  modal.props.onCancel();
  assert.equal(calls[1], "close");
  const logs = SettlementContextModal({ ...props, context: { ...context, mode: "log-create" } });
  button(logs.props.footer, "保存日志").props.onClick();
  assert.equal(calls[2], "log");
});

test("settlement allocation row actions retain task and export targets", () => {
  const { GeneralSettlementExpandedRow } = loadFinanceModule("GeneralSettlementExpandedRow.tsx");
  const calls = [];
  const detail = { detail_id: "D-1", case_no: "CASE-1", customer: "Acme", customer_no: "C-1" };
  const row = { id: 8, status: "待付款", data: { allocation_details: [detail] } };
  const view = GeneralSettlementExpandedRow({
    row, isPaymentRoute: true, isPaidRoute: false, isRejectedRoute: false, isAuditRoute: false,
    detailsExpanded: true, displayPersonName: (value) => value || "—", displayPersonNames: () => "—",
    openTask: (source) => calls.push(["task", source]), exportSettlement: async (...args) => calls.push(["export", ...args]),
    openCase: (value) => calls.push(["case", value]), openCustomer: () => {}, openContract: () => {},
  });
  const table = nodes(view).find((node) => node.type === Table);
  assert.ok(table);
  assert.equal(table.props.dataSource[0], detail);
  const operation = table.props.columns[1];
  assert.equal(typeof operation.render, "function");
  const buttons = nodes(operation.render(null, detail));
  buttons.find((node) => node.props.title === "新建案件任务").props.onClick();
  buttons.find((node) => node.props.title === "导出结算清单").props.onClick();
  buttons.find((node) => node.props.title === "导出结算列表").props.onClick();
  assert.equal(calls[0][1], detail);
  assert.equal(calls[1][1], "settlement");
  assert.equal(calls[1][2][0], 8);
  assert.equal(calls[2][1], "case");
});
