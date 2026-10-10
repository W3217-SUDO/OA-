import assert from "node:assert/strict";
import fs from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const require = createRequire(import.meta.url);
const Button = () => null;
const Card = () => null;
const Space = () => null;
const Table = () => null;

function loadComponent(path, dependencies, globals = {}) {
  const source = fs.readFileSync(new URL(path, import.meta.url), "utf8");
  const output = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
      jsx: ts.JsxEmit.ReactJSX,
      esModuleInterop: true,
    },
  }).outputText;
  const module = { exports: {} };
  vm.runInNewContext(output, {
    module,
    exports: module.exports,
    require: (name) => name in dependencies ? dependencies[name] : require(name),
    ...globals,
  }, { filename: path });
  return module.exports;
}

function nodes(element) {
  if (Array.isArray(element)) return element.flatMap(nodes);
  if (!element || typeof element !== "object" || !("props" in element)) return [];
  return [element, ...nodes(element.props.children)];
}

test("case clue context keeps file download, evidence selection and operation availability", () => {
  const { CaseClueContextPanel } = loadComponent("../../src/legal/CaseClueContextPanel.tsx", {
    antd: { Button, Space },
    "@ant-design/icons": { CloseOutlined: () => null },
    "../components/ResizableTable": Table,
    "./CaseDetail/CaseClueDetails": { CaseClueDetails: () => null },
  });
  const calls = [];
  const file = { id: 3, original_name: "证据.pdf" };
  const evidence = { id: 8, data: {}, files: [], can_delete: false, can_edit: true };
  const props = {
    workspace: { clue: { id: 1 }, clue_files: [file], evidence: [evidence] },
    loading: false,
    selectedEvidenceId: 8,
    onClose: () => calls.push("close"),
    onSelectEvidence: (id) => calls.push(["select", id]),
    onDownloadFile: (item) => calls.push(["download", item.id]),
    onDeleteEvidence: () => calls.push("delete"),
    onEditEvidence: () => calls.push("edit"),
  };
  assert.equal(CaseClueContextPanel({ ...props, workspace: null }), null);
  const rendered = nodes(CaseClueContextPanel(props));
  const tables = rendered.filter((node) => node.type === Table);
  assert.equal(tables.length, 2);
  assert.equal(tables[0].props.dataSource[0].id, 3);
  assert.equal(tables[1].props.rowSelection.selectedRowKeys[0], 8);
  tables[1].props.rowSelection.onChange([8]);
  tables[0].props.columns.at(-1).render(null, file).props.onClick();
  const buttons = rendered.filter((node) => node.type === Button);
  assert.equal(buttons.find((node) => node.props.children === "删除").props.disabled, true);
  const edit = buttons.find((node) => node.props.children === "修改");
  assert.equal(edit.props.disabled, false);
  edit.props.onClick();
  buttons.find((node) => node.props["aria-label"] === "关闭线索信息").props.onClick();
  assert.deepEqual(calls, [["select", 8], ["download", 3], "edit", "close"]);
});

test("dashboard approved entries keep their destinations and unapproved entries remain read-only", async () => {
  const calls = [];
  const storage = new Map();
  const requests = [];
  const warnings = [];
  const errors = [];
  const cleanups = [];
  let relatedRecords = [{ id: 17, serial_no: "CASE-1", title: "案件" }];
  const data = {
    metrics: [{ key: "m", label: "待收费用", value: "2", route: "finance-fee-query", query: { scope: "mine" }, detail_context: { contract_no: "HT-1", return_view: "dashboard" } }],
    todos: [["待处理任务", 2, 1, "待审批用印", 3, 0]],
    hearings: [{ case_no: "CASE-1", time: "09:00" }],
    latest_cases: [{ case_no: "CASE-2" }],
    case_trend: [{ date: "10-01", value: 2 }],
    civil_distribution: [{ label: "民事", value: 1, color: "blue" }],
  };
  const permissions = loadComponent("../../src/workspacePermissions.ts", {
    "./dashboardWorkspace": loadComponent("../../src/dashboardWorkspace.ts", {}),
    "./feedback/navigation": loadComponent("../../src/feedback/navigation.ts", {}),
  });
  const detailResolver = loadComponent("../../src/detailRelationResolver.ts", {
    "./api": { api: { get: async (url, options) => {
      requests.push([url, options]);
      return { data: { items: relatedRecords } };
    } } },
  });
  const Dashboard = loadComponent("../../src/Dashboard.tsx", {
    react: {
      useMemo: (factory) => factory(),
      useCallback: (callback) => callback,
      useRef: (value) => ({ current: value }),
      useEffect: (effect) => cleanups.push(effect()),
    },
    antd: { Button, Card, message: { warning: (value) => warnings.push(value), error: (value) => errors.push(value) } },
    "./components/ResizableTable": Table,
    "./DashboardPersonCell": () => null,
    "./dashboardData": { useDashboardData: () => ({ data, loading: { metrics: false, todos: false, cases: false }, errors: {}, retry: (section) => calls.push(["retry", section]) }) },
    "./dashboardFeeNavigation.mjs": { rememberDashboardFeeQuery: (query) => calls.push(["fee-query", query.scope]) },
    "./caseDetailNavigation": { rememberCaseDetailTarget: (target) => calls.push(["case", target.serial_no]) },
    "./customerDetailNavigation": { rememberCustomerDetailTarget: (target) => calls.push(["customer", target.title]) },
    "./detailRelationResolver": detailResolver,
    "./workspacePermissions": permissions,
  }, { AbortController, sessionStorage: { setItem: (key, value) => storage.set(key, value) } }).default;
  const props = {
    onNavigate: (route) => calls.push(["route", route]),
    grantedMenuKeys: new Set(["finance-fee-query", "task-my-accepted", "case-mine-civil"]),
    permissionAdministrator: false,
  };
  const rendered = nodes(Dashboard(props));
  rendered.find((node) => node.props.className === "metric target-0").props.onClick();
  assert.equal(JSON.parse(storage.get("sunhold:receivable-detail-context")).contract_no, "HT-1");
  rendered.find((node) => node.type === "button" && node.props.children === 2).props.onClick();
  assert.equal(storage.get("sunhold:dashboard-task-tab"), "pending");
  const tables = rendered.filter((node) => node.type === Table);
  const caseLink = tables[0].props.columns.find((column) => column.dataIndex === "case_no").render("CASE-1");
  caseLink.props.onClick();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(requests[0][0], "/records");
  assert.equal(requests[0][1].params.module, "case");
  assert.equal(requests[0][1].params.keyword, "CASE-1");
  assert.equal(requests[0][1].signal.aborted, false);
  assert.deepEqual(calls, [
    ["fee-query", "mine"], ["route", "finance-fee-query"],
    ["route", "task-my-accepted"], ["case", "CASE-1"], ["route", "case-detail-17-CASE-1"],
  ]);
  const successfulCallCount = calls.length;
  relatedRecords = [];
  caseLink.props.onClick();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(requests[0][1].signal.aborted, true);
  assert.equal(calls.length, successfulCallCount);
  assert.equal(warnings.at(-1), "未找到关联案件或当前账号无权查看");
  assert.equal(errors.length, 0);

  const denied = nodes(Dashboard({ ...props, grantedMenuKeys: new Set() }));
  const deniedMetric = denied.find((node) => node.props.className === "metric target-0");
  assert.equal(deniedMetric.props.role, undefined);
  assert.equal(deniedMetric.props.tabIndex, undefined);
  assert.equal(deniedMetric.props.onClick, undefined);
  assert.equal(deniedMetric.props.onKeyDown, undefined);
  assert.ok(denied.some((node) => node.type === "span" && node.props.className === "todo-link" && node.props.children === 2));
  assert.equal(denied.some((node) => node.type === "button" && node.props.children === 2), false);
  const deniedTables = denied.filter((node) => node.type === Table);
  assert.equal(deniedTables[0].props.columns.find((column) => column.dataIndex === "case_no").render("CASE-1"), "CASE-1");
  assert.equal(deniedTables[1].props.columns.find((column) => column.dataIndex === "case_no").render("CASE-2"), "CASE-2");
  assert.equal(deniedTables[0].props.columns.find((column) => column.dataIndex === "client").render("客户"), "客户");
  assert.ok(denied.some((node) => node.type === Card && node.props.title === "开庭排期"));
  assert.equal(calls.length, successfulCallCount);
  cleanups.forEach((cleanup) => cleanup());
  assert.equal(requests.at(-1)[1].signal.aborted, true);
});
