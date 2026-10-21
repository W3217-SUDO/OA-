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

function loadFinanceModule(name, dependencies = {}, globals = {}) {
  const sourceUrl = new URL(name, sourceRoot);
  const source = fs.readFileSync(sourceUrl, "utf8");
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
    require: (specifier) => {
      if (specifier in mocks) return mocks[specifier];
      if (specifier === "../components/KeywordPersonSelect") return loadFinanceModule("../components/KeywordPersonSelect.tsx", dependencies);
      if (specifier === "./keyword-person-select.css") return {};
      if (["../financialValueDisplay", "../../financialValueDisplay"].includes(specifier)) {
        return loadFinanceModule(new URL(`${specifier}.ts`, sourceUrl).href);
      }
      if (specifier === "./settlementIdentity") return loadFinanceModule("settlementIdentity.ts");
      return require(specifier);
    },
    ...globals,
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

test("finance source labels distinguish historical snapshots local activity and unknown allocation", () => {
  const Tag = () => null;
  const { createConfiguredColumns } = loadFinanceModule("columns/configuredColumns.tsx", {
    antd: { ...ui, Tag }, "../moneyColumns": { moneyColumnStyle: () => ({}) },
  });
  for (const source of ["generalSettlements", "archiveSettlements", "incoming"]) {
    const columns = createConfiguredColumns({
      activeRouteConfig: { source, headers: ["操作", "回款日期"] },
      initialView: "finance-receipts-manage", cellValue: () => "2026-10-16",
    });
    const render = row => nodes(columns[1].render(null, row)).filter(node => node.type === Tag).map(node => node.props.children);
    if (source === "incoming") {
      assert.deepEqual(render({ allocation_status_label: "现行分配待核", has_local_allocation_activity: false }), ["现行分配待核"]);
      assert.deepEqual(render({ has_local_allocation_activity: true }), ["已发生本地分配操作"]);
    } else {
      const row = { amount_basis: "legacy_snapshot", source_label: "原始历史结算快照（只读，不代表现行分配）", has_local_allocation_activity: true };
      assert.deepEqual(render(row), ["原始快照", "已发生本地分配操作"]);
      const snapshot = nodes(columns[1].render(null, row)).find(node => node.type === Tag);
      assert.equal(snapshot.props.title, row.source_label);
      assert.equal(snapshot.props.style.whiteSpace, "normal");
    }
    assert.deepEqual(render({}), []);
  }
  const Descriptions = () => null;
  Descriptions.Item = () => null;
  const { LegacyFinanceDetailDrawer } = loadFinanceModule("LegacyHistoryPanel.tsx", {
    antd: { Drawer: () => null, Descriptions, Tabs: () => null, Tag, Alert: () => null },
    "./constants": loadFinanceModule("constants.ts"),
  });
  const view = LegacyFinanceDetailDrawer({
    detail: { id: 41, record_kind: "ar_payment", amount_basis: "legacy_snapshot", source_label: "只读，不代表现行分配", has_local_allocation_activity: true },
    amountVisible: true, detailLoading: false, onCloseDetail: () => {},
  });
  assert.ok(nodes(view).some(node => node.type === Tag && node.props.children === "原始快照"));
  assert.ok(nodes(view).some(node => node.props.children === "已发生本地分配操作"));
});

test("incoming classified totals show unknown sources without replacing real zero", () => {
  const { IncomingTotalsBody } = loadFinanceModule("IncomingTotalsBody.tsx");
  const body = IncomingTotalsBody({
    headers: ["已分官费", "已分代理费", "已分其他费", "回款金额", "操作"],
    totals: { 已分官费: 0, 已分代理费: 25.5, 已分其他费: null, 回款金额: null },
  });
  const cells = nodes(body).filter(node => node.type === "td");
  assert.deepEqual(cells.slice(1).map(node => node.props.children), ["0.00", "25.50", "未知", null, "合计"]);
  const missing = IncomingTotalsBody({ headers: ["已分官费", "已分代理费", "已分其他费"], totals: {} });
  assert.deepEqual(nodes(missing).filter(node => node.type === "td").slice(1).map(node => node.props.children), ["未知", "未知", "未知"]);
});

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

test("all settlement states retain readable allocation columns, amounts and linked targets", () => {
  const { GeneralSettlementExpandedRow } = loadFinanceModule("GeneralSettlementExpandedRow.tsx");
  const states = ["pending", "audit", "payment", "paid", "refused"];
  for (const state of states) {
    const calls = [];
    const detail = { detail_id: "CODEX-layout-detail", case_no: "CODEX-CASE", customer: "CODEX 客户",
      customer_no: "CODEX-CUSTOMER", contract_no: "CODEX-CONTRACT" };
    const row = { id: 8, data: { allocation_details: [detail] } };
    const view = GeneralSettlementExpandedRow({ row, detailsExpanded: true,
      isAuditRoute: state === "audit", isPaymentRoute: state === "payment",
      isPaidRoute: state === "paid", isRejectedRoute: state === "refused",
      displayPersonName: (value) => value || "—", displayPersonNames: () => "CODEX 律师",
      openTask: (value) => calls.push(["task", value]), exportSettlement: () => Promise.resolve(),
      openCase: (value) => calls.push(["case", value]),
      openCustomer: (...args) => calls.push(["customer", ...args]),
      openContract: (value) => calls.push(["contract", value]),
    });
    const table = nodes(view).find((node) => node.type === Table);
    assert.equal(table.props.columns.length, 15, state);
    assert.equal(table.props.tableLayout, "fixed", state);
    assert.equal(table.props.scroll.x, table.props.columns.reduce((sum, column) => sum + column.width, 0));
    assert.ok(table.props.scroll.x <= 1541, state);
    assert.equal(table.props.dataSource[0], detail);
    const byField = (name) => table.props.columns.find((column) => column.dataIndex === name);
    for (const field of ["fee_total_amount", "fee_allocated_amount", "current_amount", "settlement_amount", "archive_fee"]) {
      const column = byField(field);
      assert.equal(column.render(43166062.63), "43166062.63", field);
      assert.equal(column.render(0), "0.00", field);
      assert.equal(column.render(null), "", field);
      assert.equal(column.align, "right");
      assert.equal(column.className, "finance-money-column");
      assert.ok(column.width >= 96, field);
    }
    nodes(byField("case_no").render(detail.case_no, detail)).find((node) => node.type === Button).props.onClick();
    nodes(byField("customer").render(detail.customer, detail)).find((node) => node.type === Button).props.onClick();
    nodes(byField("contract_no").render(detail.contract_no, detail)).find((node) => node.type === Button).props.onClick();
    assert.deepEqual(calls, [["case", detail.case_no], ["customer", detail.customer, detail.customer_no], ["contract", detail.contract_no]]);
  }
});

test("internal server pagination changes size to 200, resets page, and clears selection", async () => {
  const noView = () => null;
  const calls = [];
  const { FinanceOriginalRoutesView } = loadFinanceModule("FinanceOriginalRoutesView.tsx", {
    "./constants": loadFinanceModule("constants.ts"), "./financeErrors": { financeErrorDetail: String },
    "./IncomingTotalsBody": { IncomingTotalsBody: noView },
    "./FinanceOriginalQueryView": { FinanceOriginalQueryView: noView },
    "./GeneralSettlementExpandedRow": { GeneralSettlementExpandedRow: noView },
    "./FinanceOriginalTotals": {}, "./FinanceFeeQueryActions": { FinanceFeeQueryActions: noView },
    "./RefundCaseFeeActions": { RefundCaseFeeOperationMenu: noView, RefundCaseFeeMarkButton: noView },
  });
  const base = {
    initialView: "finance-internal-audit", originalQueryView: {}, activeRouteConfig: { source: "fees", selectable: true, headers: [] },
    isInternalQueueRoute: true, originalColumns: [], configuredRows: [], originalQuery: { routeField5: "CODEX-CASE" },
    selectedOriginalRows: [1], setSelectedOriginalRows: (keys) => calls.push(["selected", ...keys]),
    internalQueueMeta: { page: 8, pageSize: 15, total: 201, amountVisible: true, totalAmount: 100 },
    loadInternalQueue: async (...args) => calls.push(["load", ...args]),
  };
  const table = nodes(FinanceOriginalRoutesView(base)).find((node) => node.type === Table);
  table.props.pagination.onChange(8, 200);
  assert.equal(table.props.pagination.total, 201);
  assert.equal(table.props.pagination.pageSizeOptions.includes(200), true);
  assert.equal(calls[1][2], 1);
  assert.equal(calls[1][3], 200);
  assert.deepEqual(calls[0], ["selected"]);
  assert.equal(calls[1][1].routeField5, "CODEX-CASE");
  const after = nodes(FinanceOriginalRoutesView({ ...base, internalQueueMeta: { page: 1, pageSize: 200, total: 201, amountVisible: true, totalAmount: 100 } })).find((node) => node.type === Table);
  assert.equal(after.props.pagination.pageSize, 200);
  after.props.pagination.onChange(2, 200);
  assert.equal(calls[3][2], 2);
  assert.equal(after.props.rowSelection.getCheckboxProps({ data: { read_only: true } }).disabled, true);
});

test("all seven internal queue footers show filtered grand totals instead of the current page", () => {
  const noView = () => null;
  const SummaryRow = () => null;
  const SummaryCell = () => null;
  const totals = loadFinanceModule("FinanceOriginalTotals.tsx", {
    "../components/ResizableTable": { Summary: { Row: SummaryRow, Cell: SummaryCell } },
    "./constants": loadFinanceModule("constants.ts"),
  });
  const { FinanceOriginalRoutesView } = loadFinanceModule("FinanceOriginalRoutesView.tsx", {
    "./constants": loadFinanceModule("constants.ts"), "./financeErrors": { financeErrorDetail: String },
    "./IncomingTotalsBody": { IncomingTotalsBody: noView },
    "./FinanceOriginalQueryView": { FinanceOriginalQueryView: noView },
    "./GeneralSettlementExpandedRow": { GeneralSettlementExpandedRow: noView },
    "./FinanceOriginalTotals": totals, "./FinanceFeeQueryActions": { FinanceFeeQueryActions: noView },
    "./RefundCaseFeeActions": { RefundCaseFeeOperationMenu: noView, RefundCaseFeeMarkButton: noView },
  });
  for (const route of ["settle", "archive", "refused", "payment", "audit", "fee-audit", "refund-audit"]) {
    const header = route === "payment" ? "实际提成" : route === "settle" ? "金额" : "申请金额";
    const headers = route === "settle" ? ["操作", header, "到账金额"] : ["操作", header];
    const props = {
      initialView: `finance-internal-${route}`, originalQueryView: {}, originalHeaders: headers,
      activeRouteConfig: { source: "fees", selectable: route !== "refused", headers },
      isInternalQueueRoute: true, originalColumns: [], configuredRows: [], originalQuery: {}, selectedOriginalRows: [],
      internalQueueMeta: { page: 1, pageSize: 1, total: 2, amountVisible: true, totalAmount: 100, totalActualCommission: 90, totalCashedAmount: 70 },
      loadInternalQueue: async () => {},
    };
    for (const [index, amount] of [10, 90].entries()) {
      const table = nodes(FinanceOriginalRoutesView({ ...props, internalQueueMeta: { ...props.internalQueueMeta, page: index + 1 } })).find((node) => node.type === Table);
      const summary = table.props.summary([{ id: index + 1, data: { amount, actual_commission: index === 0 ? 0 : 90, cashed_amount: index === 0 ? 10 : 60 } }]);
      const cells = nodes(summary.type(summary.props)).filter((node) => node.type === SummaryCell);
      const amountIndex = route === "refused" ? 1 : 2;
      assert.equal(cells[amountIndex].props.children, route === "payment" ? "90.00" : "100.00");
      assert.equal(cells[amountIndex].props.index, amountIndex);
      if (route === "settle") assert.equal(cells[3].props.children, "70.00");
    }
    const hidden = nodes(FinanceOriginalRoutesView({ ...props, internalQueueMeta: { ...props.internalQueueMeta, amountVisible: false, totalAmount: null, totalActualCommission: null, totalCashedAmount: null } })).find((node) => node.type === Table).props.summary([]);
    assert.equal(nodes(hidden.type(hidden.props)).filter((node) => node.type === SummaryCell).at(-1).props.children, "无权限");
    const failed = nodes(FinanceOriginalRoutesView({ ...props, internalQueueError: "查询失败" })).find((node) => node.type === Table);
    assert.equal(failed.props.summary([]), null);
  }
});

test("internal case columns and review payees consume exact server names, including inactive employees", () => {
  const { createInternalOriginalColumns } = loadFinanceModule("columns/internalOriginalColumns.tsx", {
    "../moneyColumns": loadFinanceModule("moneyColumns.ts"), "../constants": loadFinanceModule("constants.ts"),
  });
  const columns = createInternalOriginalColumns({ internalMineOperation: () => null });
  assert.equal(columns.find((column) => column.title === "案件名称").render(null, {
    title: "CODEX-费用标题", data: { case_name: "CODEX-关联案件" },
  }), "CODEX-关联案件");
  const source = fs.readFileSync(new URL("FinanceCenterPage.tsx", sourceRoot), "utf8");
  const tree = ts.createSourceFile("FinanceCenterPage.tsx", source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  let initializer;
  const visit = (node) => {
    if (ts.isVariableDeclaration(node) && node.name.getText(tree) === "feeReviewRows") initializer = node.initializer.getText(tree);
    ts.forEachChild(node, visit);
  };
  visit(tree);
  assert.ok(initializer);
  const code = ts.transpileModule(`const rows = ${initializer}; result(rows);`, {
    compilerOptions: { target: ts.ScriptTarget.ES2022 },
  }).outputText;
  let result;
  vm.runInNewContext(code, {
    useMemo: (read) => read(), financePersonNameMap: new Map(),
    financePersonDisplayName: (identity, name) => name || `未解析:${identity}`,
    feeReviewTargets: [{ data: { application_items: [
      { id: 1, owner: "parent", data: { payee: "disabled-user", payee_display_name: "历史员工", commission_details: [
        { payee: "child-a", payee_display_name: "子项甲" },
        { payment_target: "child-b", payment_target_display_name: "子项乙" },
        {},
      ] } },
    ] } }], result: (value) => { result = value; },
  });
  assert.equal(result.map((row) => row.payee).join(","), "子项甲,子项乙,历史员工");
});

test("main receipt cells read top-level allocations and real payment method without changing settlement cells", () => {
  const source = fs.readFileSync(new URL("FinanceCenterPage.tsx", sourceRoot), "utf8");
  const tree = ts.createSourceFile("FinanceCenterPage.tsx", source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const headers = ["已分官费", "已分代理费", "已分其他费用", "回款方式"];
  const expressions = new Map();
  let cellExpression;
  const visit = (node) => {
    if (ts.isVariableDeclaration(node) && node.name.getText(tree) === "cellValue") cellExpression = node.initializer.getText(tree);
    if (ts.isVariableDeclaration(node) && node.name.getText(tree) === "values" && ts.isObjectLiteralExpression(node.initializer)) {
      for (const property of node.initializer.properties) {
        if (ts.isPropertyAssignment(property) && headers.includes(property.name.getText(tree))) expressions.set(property.name.getText(tree), property.initializer.getText(tree));
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(tree);
  assert.equal(expressions.size, headers.length);
  assert.ok(cellExpression);
  const code = ts.transpileModule(`const rawCellValue = (row, header) => { const data = row.data || {}; return ({${headers.map(header => `${JSON.stringify(header)}: ${expressions.get(header)}`).join(",")}})[header]; }; result(${cellExpression});`, {
    compilerOptions: { target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const constants = loadFinanceModule("constants.ts");
  for (const center of ["firm", "platform"]) {
    const route = { source: "incoming" };
    let cell;
    vm.runInNewContext(code, {
      activeRouteConfig: route, initialView: "finance-receipts-manage",
      displayFinancialValue: loadFinanceModule("../financialValueDisplay.ts").displayFinancialValue,
      money: constants.money, isArchiveSettlementActiveRoute: false, isInternalDetailRoute: false,
      isInvoiceMineRoute: false, isInvoicePendingRoute: false, isInvoiceCompanyRoute: false,
      isInvoiceUnissuedRoute: false, isFeeQueryRoute: false, isGeneralSettlementRoute: false,
      result: value => { cell = value; },
    });
    const row = { finance_scope: center, assigned_official_fee: 0, assigned_agency_fee: 25.5, assigned_other_fee: null,
      payment_method: "实际回款方式", bank_source: "实际到账银行", data: { assigned_official_fee: 99, assigned_agency_fee: 99, assigned_other_fee: 99, payment_method: "结算回款方式" } };
    assert.equal(cell(row, headers[0]), constants.money(0));
    assert.equal(cell(row, headers[1]), constants.money(25.5));
    assert.equal(cell(row, headers[2]), "—");
    assert.equal(cell(row, headers[3]), "实际回款方式");
    assert.equal(cell({ bank_source: "实际到账银行", data: row.data }, headers[0]), "—");
    assert.equal(cell({ bank_source: "实际到账银行", data: row.data }, headers[3]), "—");
    route.source = "generalSettlements";
    assert.equal(cell(row, headers[0]), constants.money(99));
    assert.equal(cell(row, headers[3]), "结算回款方式");
  }
});

test("historical settlement actions open real legacy heads and never expose modern writes", async () => {
  const source = fs.readFileSync(new URL("FinanceCenterPage.tsx", sourceRoot), "utf8");
  const tree = ts.createSourceFile("FinanceCenterPage.tsx", source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const names = ["openHistoricalSettlement", "historicalSettlementOperation", "generalSettlementOperation", "archiveSettlementPendingOperation"];
  const expressions = new Map();
  const visit = node => {
    if (ts.isVariableDeclaration(node) && names.includes(node.name.getText(tree))) expressions.set(node.name.getText(tree), node.initializer.getText(tree));
    ts.forEachChild(node, visit);
  };
  visit(tree);
  assert.equal(expressions.size, names.length);
  const reads = [], exports = [], errors = [];
  let actions;
  const code = ts.transpileModule(`${names.map(name => `const ${name} = ${expressions.get(name)};`).join("\n")} result({generalSettlementOperation,archiveSettlementPendingOperation});`, {
    compilerOptions: { target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.CommonJS },
  }).outputText;
  vm.runInNewContext(code, {
    require, exports: {}, Button, Space: ui.Space, DownloadOutlined: () => null, isHistoricalSettlement: loadFinanceModule("settlementIdentity.ts").isHistoricalSettlement,
    openLegacyFinanceDetail: async id => { reads.push(id); },
    exportGeneralSettlement: async (kind, ids) => { exports.push({ kind, ids }); },
    exportPendingArchiveSettlements: async ids => { exports.push({ kind: "archive", ids }); },
    message: { error: value => errors.push(value) }, result: value => { actions = value; },
  });
  for (const [name, id] of [["generalSettlementOperation", "legacy-normal:41"], ["archiveSettlementPendingOperation", "legacy-archive:71"]]) {
    const row = { id, source: "legacy", read_only: true, legacy_record_id: 41, source_status: "30", data: {} };
    const view = actions[name](null, row);
    const buttons = nodes(view).filter(node => node.type === Button);
    assert.deepEqual(buttons.map(node => node.props.children || node.props["aria-label"]), ["历史只读", "导出"]);
    await buttons[0].props.onClick();
    await buttons[1].props.onClick();
    assert.equal(reads.at(-1), 41);
    assert.equal(exports.at(-1).ids[0], id);
  }
  assert.deepEqual(errors, []);
  actions.generalSettlementOperation(null, { id: "legacy-normal:999", source: "legacy", read_only: true, data: {} }).props.children[0].props.onClick();
  assert.equal(reads.length, 2);
  assert.match(errors[0], /缺少有效的来源头记录/);
});

test("settlement tables disable historical selection and keep query export reachable", () => {
  const noView = () => null;
  const { FinanceOriginalRoutesView } = loadFinanceModule("FinanceOriginalRoutesView.tsx", {
    "./constants": loadFinanceModule("constants.ts"), "./financeErrors": {},
    "./IncomingTotalsBody": { IncomingTotalsBody: noView }, "./FinanceOriginalQueryView": { FinanceOriginalQueryView: noView },
    "./GeneralSettlementExpandedRow": { GeneralSettlementExpandedRow: noView }, "./FinanceOriginalTotals": {},
    "./FinanceFeeQueryActions": { FinanceFeeQueryActions: noView }, "./RefundCaseFeeActions": {},
  });
  const historical = { id: "legacy-normal:41", source: "legacy", read_only: true, data: {} };
  const modern = { id: 8, data: {} };
  let selected;
  for (const archive of [false, true]) {
    const view = FinanceOriginalRoutesView({
      initialView: archive ? "finance-archive-fee-paid" : "finance-settlement-paid",
      activeRouteConfig: { source: archive ? "archiveSettlements" : "generalSettlements", selectable: true, headers: [] },
      configuredRows: [modern, historical], originalColumns: [], originalHeaders: [], originalQueryView: {},
      isGeneralSettlementRoute: !archive, isGeneralSettlementPaidRoute: !archive,
      isArchiveSettlementActiveRoute: archive, isArchiveSettlementPaidRoute: archive,
      generalSettlementMeta: { total: 2, page: 1, pageSize: 15, totals: {} },
      archiveSettlementMeta: { total: 2, page: 1, pageSize: 15, totals: {} },
      generalSettlementDetails: [], selectedOriginalRows: [], setSelectedOriginalRows: keys => { selected = keys; },
    });
    const table = nodes(view).find(node => node.type === Table);
    assert.equal(table.props.rowSelection.getCheckboxProps(historical).disabled, true);
    assert.equal(table.props.rowSelection.getCheckboxProps(modern).disabled, false);
    table.props.rowSelection.onChange([8, historical.id]);
    assert.deepEqual(Array.from(selected), [8]);
    if (archive) assert.ok(nodes(view).some(node => node.type === Button && node.props.children === "导出查询结果"));
  }
});

test("legacy detail drawer is reusable from status pages and preserves unknown and zero amounts", () => {
  const Drawer = () => null;
  const Descriptions = () => null;
  Descriptions.Item = () => null;
  const Tabs = () => null;
  const { LegacyFinanceDetailDrawer } = loadFinanceModule("LegacyHistoryPanel.tsx", {
    antd: { Drawer, Descriptions, Tabs, Tag: () => null, Alert: () => null },
    "./constants": loadFinanceModule("constants.ts"),
  });
  let closed = false;
  const view = LegacyFinanceDetailDrawer({
    detail: { id: 41, source_table: "FAM_AR_Payment", legacy_id: "source-head-41", record_kind: "ar_payment", legacy_statuses: { SettlementStatus: "30" }, allocations: [], primary_amount: null },
    detailLoading: false, amountVisible: true, onCloseDetail: () => { closed = true; },
  });
  assert.equal(view.type, Drawer);
  assert.equal(view.props.open, true);
  view.props.onClose();
  assert.equal(closed, true);
  const tabs = nodes(view).find(node => node.type === Tabs);
  const allocations = tabs.props.items.find(item => item.key === "allocations").children;
  const amount = allocations.props.columns.find(column => column.dataIndex === "amount");
  assert.equal(amount.render(null), "—");
  assert.equal(amount.render(0), loadFinanceModule("constants.ts").money(0));
  const statuses = tabs.props.items.find(item => item.key === "legacy-fields").children;
  assert.ok(nodes(statuses).some(node => node.props.children === "30"));
});

test("settlement parent layout uses its full column budget for five states only", () => {
  const constants = loadFinanceModule("constants.ts");
  const { createConfiguredColumns } = loadFinanceModule("columns/configuredColumns.tsx", {
    "../moneyColumns": loadFinanceModule("moneyColumns.ts"),
  });
  const noView = () => null;
  const { FinanceOriginalRoutesView } = loadFinanceModule("FinanceOriginalRoutesView.tsx", {
    "./constants": constants, "./financeErrors": { financeErrorDetail: String },
    "./IncomingTotalsBody": { IncomingTotalsBody: noView },
    "./FinanceOriginalQueryView": { FinanceOriginalQueryView: noView },
    "./GeneralSettlementExpandedRow": { GeneralSettlementExpandedRow: noView },
    "./FinanceOriginalTotals": {}, "./FinanceFeeQueryActions": { FinanceFeeQueryActions: noView },
    "./RefundCaseFeeActions": { RefundCaseFeeOperationMenu: noView, RefundCaseFeeMarkButton: noView },
  });
  const source = fs.readFileSync(new URL("FinanceCenterPage.tsx", sourceRoot), "utf8");
  const tree = ts.createSourceFile("FinanceCenterPage.tsx", source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  let widths;
  const visit = (node) => {
    if (ts.isVariableDeclaration(node) && node.name.getText(tree) === "generalSettlementColumnWidths") {
      assert.ok(ts.isArrayLiteralExpression(node.initializer));
      widths = node.initializer.elements.map((item) => Number(item.getText(tree)));
    }
    ts.forEachChild(node, visit);
  };
  visit(tree);
  const headers = ["操作", "客户名称", "客户管理人", "回款单位", "回款日期", "回款金额", "已分金额", "未分金额",
    "已分官费", "已分代理费", "已分其他费用", "代理费结算金额", "扣归档费", "实际结算金额", ""];
  const config = { source: "generalSettlements", selectable: true, headers };
  const columnsContext = { activeRouteConfig: config, isGeneralSettlementRoute: true,
    generalSettlementColumnWidths: widths, cellValue: () => "CODEX-value", generalSettlementOperation: noView };
  for (const state of ["pending", "audit", "payment", "paid", "refused"]) {
    const initialView = "finance-settlement-" + state;
    const originalColumns = createConfiguredColumns({ ...columnsContext, initialView });
    assert.equal(originalColumns.length, headers.length);
    assert.ok(originalColumns.every((column) => column.fixed === undefined));
    const view = FinanceOriginalRoutesView({ initialView, activeRouteConfig: config, originalColumns,
      configuredRows: [], originalQueryView: {}, isGeneralSettlementRoute: true,
      isGeneralSettlementPaidRoute: state === "paid", isGeneralSettlementRejectedRoute: state === "refused",
      isGeneralSettlementAuditRoute: state === "audit", isGeneralSettlementPaymentRoute: state === "payment",
      generalSettlementMeta: { page: 1, pageSize: 15, total: 0, totals: {} },
      generalSettlementDetails: [], selectedOriginalRows: [], setSelectedOriginalRows: noView,
    });
    const panel = nodes(view).find((node) => node.type === "section");
    const table = nodes(view).find((node) => node.type === Table);
    assert.match(panel.props.className, /finance-general-settlement/);
    assert.equal(table.props.tableLayout, "fixed");
    assert.equal(table.props.rowSelection.columnWidth, 36);
    assert.equal(table.props.scroll.x, 36 + widths.reduce((sum, width) => sum + width, 0));
    assert.ok(table.props.scroll.x <= 1600);
    assert.equal(table.props.columns, originalColumns);
  }
  const unrelated = FinanceOriginalRoutesView({ initialView: "finance-archive-fee-pending",
    activeRouteConfig: { source: "archiveSettlements", headers: [] }, originalColumns: [], configuredRows: [],
    originalQueryView: {}, isArchiveSettlementActiveRoute: true,
    archiveSettlementMeta: { page: 1, pageSize: 15, total: 0 },
  });
  assert.doesNotMatch(nodes(unrelated).find((node) => node.type === "section").props.className, /finance-general-settlement/);
  assert.equal(nodes(unrelated).find((node) => node.type === Table).props.scroll.x, 1904);
});

test("saved allocation widths retain their existing route keys and override defaults honestly", async () => {
  const React = require("react");
  const { create, act } = require("react-test-renderer");
  const { GeneralSettlementExpandedRow } = loadFinanceModule("GeneralSettlementExpandedRow.tsx");
  const columns = nodes(GeneralSettlementExpandedRow({ row: { id: 8, data: {} }, detailsExpanded: true,
    displayPersonName: String, displayPersonNames: String,
  })).find((node) => node.type === Table).props.columns;
  const signature = "0:|1:|2:case_no|3:case_stage|4:fee_type|5:fee_total_amount|6:fee_allocated_amount|7:current_amount|8:allocated_at|9:settlement_amount|10:archive_fee|11:customer|12:handling_lawyer|13:assistant|14:contract_no";
  const previousActEnvironment = globalThis.IS_REACT_ACT_ENVIRONMENT;
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  try {
  for (const state of ["pending", "audit", "payment", "paid", "refused"]) {
    const route = "finance-settlement-" + state;
    const key = "sunhold:table-widths:" + route + ":finance-settlement-detail-table:" + signature;
    const reads = [];
    const { default: ResizableTable } = loadFinanceModule("../components/ResizableTable.tsx", {
      "./resizable-table.css": {},
    }, { URLSearchParams, window: { location: { search: "?page=" + route, pathname: "/" } },
      sessionStorage: { getItem: (value) => { reads.push(value); return value === key ? '{"2":220}' : null; } },
    });
    let rendered;
    await act(async () => { rendered = create(React.createElement(ResizableTable, {
      columns, className: "finance-settlement-detail-table", scroll: { x: 1504 }, tableLayout: "fixed",
    })); });
    const table = rendered.root.findByType(Table);
    assert.deepEqual(reads, [key]);
    assert.equal(table.props.columns[2].width, 220);
    assert.equal(table.props.scroll.x, "max-content");
    await act(async () => rendered.unmount());
  }
  } finally {
    globalThis.IS_REACT_ACT_ENVIRONMENT = previousActEnvironment;
  }
});

test("settlement CSS preserves numeric readability and honest narrow-screen scrolling", () => {
  const postcss = require("postcss");
  const source = fs.readFileSync(new URL("../../src/finance-center.css", import.meta.url), "utf8");
  const root = postcss.parse(source);
  const declarations = (selector) => {
    const matches = [];
    root.walkRules((rule) => {
      if (rule.selectors.includes(selector)) matches.push(rule);
    });
    assert.equal(matches.length, 1, selector);
    return Object.fromEntries(matches[0].nodes.filter((node) => node.type === "decl").map((node) => [node.prop, node.value]));
  };
  const numeric = declarations(".finance-general-settlement .ant-table-tbody > tr > td.finance-money-column");
  assert.equal(numeric["white-space"], "nowrap");
  assert.equal(numeric["overflow-wrap"], "normal");
  assert.equal(numeric["font-variant-numeric"], "tabular-nums");
  assert.equal(declarations(".finance-general-settlement .ant-table-content")["overflow-x"], "auto");
  assert.equal(declarations(".finance-general-settlement .ant-table-tbody .ant-btn-link")["white-space"], "normal");
  assert.equal(declarations(".finance-general-settlement .finance-settlement-detail-table .ant-table")["min-width"], "0");
  for (const name of ["context", "audit-context", "payment-context", "rejected-context"]) {
    const grid = declarations(".finance-general-settlement .finance-settlement-" + name);
    assert.equal(grid.display, "grid");
    assert.ok(grid["grid-template-columns"].includes("minmax(0,"));
  }
  root.walkRules((rule) => {
    if (!rule.selector.includes("finance-general-settlement")) return;
    rule.walkDecls((declaration) => {
      assert.ok(!(declaration.prop.startsWith("overflow") && declaration.value === "hidden"));
      assert.ok(!(declaration.prop === "font-size" && declaration.value.includes("vw")));
    });
  });
});
