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

// 工作台的子区块由被测页面渲染，测试只记录收到哪些属性，便于断言权限与跳转是否透传。
function RecordingComponent(name) {
  const Recording = (props) => null;
  Recording.displayName = name;
  return Recording;
}

const MetricTilesStub = RecordingComponent("DashboardMetricTiles");
const HearingScheduleStub = RecordingComponent("DashboardHearingSchedule");
const RejectionReminderStub = RecordingComponent("DashboardRejectionReminder");
const AssistantPanelStub = RecordingComponent("AssistantPanel");
const OverviewStub = RecordingComponent("DashboardOverview");
const PersonalAiSpaceStub = RecordingComponent("PersonalAiSpace");

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

function dashboardDataHarness() {
  const slots = [];
  const requests = [];
  const deferredUpdates = [];
  let cursor = 0;
  let mounted = false;
  let effect;
  let cleanup;
  let deferData = false;
  const { useDashboardData } = loadComponent("../../src/dashboardData.ts", {
    react: {
      useState: (initial) => {
        const index = cursor++;
        if (!(index in slots)) slots[index] = initial;
        return [slots[index], (update) => {
          const apply = () => { slots[index] = typeof update === "function" ? update(slots[index]) : update; };
          if (index === 0 && deferData) deferredUpdates.push(apply);
          else apply();
        }];
      },
      useRef: (initial) => {
        const index = cursor++;
        if (!(index in slots)) slots[index] = { current: initial };
        return slots[index];
      },
      useEffect: (callback) => { if (!mounted) effect = callback; },
      useCallback: (callback) => callback,
    },
    "./api": { api: { get: (url, config) => new Promise((resolve, reject) => requests.push({ url, config, resolve, reject })) } },
  }, {
    AbortController,
    document: { hidden: false, addEventListener: () => {}, removeEventListener: () => {} },
    window: { setInterval: () => 1, clearInterval: () => {} },
  });
  const render = () => { cursor = 0; return useDashboardData(); };
  render();
  mounted = true;
  cleanup = effect();
  return {
    requests,
    get view() { return render(); },
    request: (section, round = 0) => requests.filter((request) => request.config.params.section === section)[round],
    pauseData: () => { deferData = true; },
    flushData: () => { deferData = false; deferredUpdates.splice(0).forEach((apply) => apply()); },
    cleanup,
  };
}

const financeMetricKeys = ["official-fee-unpaid", "refund-pending", "official-fee-unreceived"];
const caseMetricKeys = ["evidence-supplement", "opinion-supplement", "appeal-pending", "execution-pending", "urgent-cases"];
const metricResponse = (keys, value = "1件") => ({ data: { metrics: keys.map((key) => ({ key, label: key, value, tone: "green", route: `dashboard-queue-${key}` })) } });
const settleDashboard = () => new Promise((resolve) => setImmediate(resolve));

test("dashboard split metrics merge both arrival orders without cancelling cases", async () => {
  for (const first of ["metrics_finance", "metrics_cases"]) {
    const harness = dashboardDataHarness();
    try {
      assert.deepEqual(harness.requests.map((request) => request.config.params.section), ["metrics_cases", "metrics_finance", "todos", "cases", "rejections"]);
      const firstKeys = first === "metrics_finance" ? financeMetricKeys : caseMetricKeys;
      const second = first === "metrics_finance" ? "metrics_cases" : "metrics_finance";
      harness.request(first).resolve(metricResponse(firstKeys));
      await settleDashboard();
      assert.equal(harness.view.data.metrics.length, firstKeys.length);
      assert.equal(harness.view.loading.metrics, true);
      assert.equal(harness.request("metrics_cases").config.signal.aborted, false);
      assert.equal(harness.request("metrics_finance").config.signal.aborted, false);
      harness.view.retry("metrics");
      assert.equal(harness.requests.length, 5);
      harness.request(second).resolve(metricResponse(second === "metrics_cases" ? caseMetricKeys : financeMetricKeys));
      await settleDashboard();
      assert.deepEqual(Array.from(harness.view.data.metrics, (metric) => metric.key).sort(), [...financeMetricKeys, ...caseMetricKeys].sort());
      assert.equal(harness.view.loading.metrics, false);
      assert.equal(harness.view.caseMetricsError, undefined);
      assert.equal(harness.view.errors.metrics, undefined);
    } finally {
      harness.cleanup();
    }
  }
});

test("dashboard split errors survive the other group's success and retry merges independently", async () => {
  for (const failed of ["metrics_cases", "metrics_finance"]) {
    const harness = dashboardDataHarness();
    try {
      const successful = failed === "metrics_cases" ? "metrics_finance" : "metrics_cases";
      harness.request(failed).reject({ response: { data: { detail: "真实分区错误" } } });
      await settleDashboard();
      assert.equal(harness.view.loading.metrics, true);
      harness.request(successful).resolve(metricResponse(successful === "metrics_finance" ? financeMetricKeys : caseMetricKeys));
      await settleDashboard();
      assert.equal(harness.view.loading.metrics, false);
      assert.equal(harness.view.caseMetricsError, failed === "metrics_cases" ? "案件统计加载失败：真实分区错误" : undefined);
      assert.equal(harness.view.errors.metrics, failed === "metrics_finance" ? "真实分区错误" : undefined);
      assert.equal(harness.requests.length, 5);
      harness.view.retry("metrics");
      assert.equal(harness.requests.length, 7);
      assert.equal(harness.view.caseMetricsError, undefined);
      assert.equal(harness.view.errors.metrics, undefined);
      harness.request("metrics_finance", 1).resolve(metricResponse(financeMetricKeys, "2件"));
      await settleDashboard();
      assert.equal(harness.view.loading.metrics, true);
      assert.equal(harness.request("metrics_cases", 1).config.signal.aborted, false);
      harness.request("metrics_cases", 1).resolve(metricResponse(caseMetricKeys, "2件"));
      await settleDashboard();
      assert.equal(harness.view.data.metrics.length, 8);
      assert.equal(harness.view.data.metrics.every((metric) => metric.value === "2件"), true);
      assert.equal(harness.view.loading.metrics, false);
    } finally {
      harness.cleanup();
    }
  }
});

test("dashboard old-generation queued state and unmounted responses cannot write back", async () => {
  const harness = dashboardDataHarness();
  try {
    harness.pauseData();
    harness.request("metrics_finance").resolve(metricResponse(financeMetricKeys, "旧轮"));
    harness.request("metrics_cases").resolve(metricResponse(caseMetricKeys, "旧轮"));
    await settleDashboard();
    harness.view.retry("metrics");
    harness.flushData();
    assert.equal(harness.view.data.metrics, undefined);
    harness.request("metrics_finance", 1).resolve(metricResponse(financeMetricKeys, "新轮"));
    harness.request("metrics_cases", 1).resolve(metricResponse(caseMetricKeys, "新轮"));
    await settleDashboard();
    assert.equal(harness.view.data.metrics.length, 8);
    assert.equal(harness.view.data.metrics.every((metric) => metric.value === "新轮"), true);
    harness.view.retry("metrics");
    harness.cleanup();
    assert.equal(harness.request("metrics_cases", 2).config.signal.aborted, true);
    assert.equal(harness.request("metrics_finance", 2).config.signal.aborted, true);
    harness.request("metrics_cases", 2).resolve(metricResponse(caseMetricKeys, "卸载后"));
    harness.request("metrics_finance", 2).resolve(metricResponse(financeMetricKeys, "卸载后"));
    await settleDashboard();
    assert.equal(harness.view.data.metrics.every((metric) => metric.value === "新轮"), true);
  } finally {
    harness.cleanup();
  }
});

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
  let conversationVisible = false;
  let relatedRecords = [{ id: 17, serial_no: "CASE-1", title: "案件" }];
  const data = {
    metrics: [{ key: "official-fee-unpaid", label: "待收费用", value: "2", route: "finance-fee-query", query: { scope: "mine" }, detail_context: { contract_no: "HT-1", return_view: "dashboard" } }],
    hearings: [{ case_no: "CASE-1", client: "客户", time: "09:00", date: "2026-10-12", weekday: "星期一" }],
    rejections: [{ id: 5, type: "task", serial_no: "RW-1", title: "被驳回的任务", reason: "材料不全", rejected_by: "管理员", rejected_at: "2026-10-11", route: "task-my-created" }],
    rejection_total: 1,
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
  // 工作台沿用智能体中心那套会话工作区：桩只要暴露面板读取的字段并记录发问。
  const workspace = {
    status: { ready: true },
    state: { messages: [], pending_actions: [], dismissed_action_ids: [] },
    loading: false,
    sending: false,
    send: (prompt) => calls.push(["agent", prompt]),
    selectConversation: async (id) => calls.push(["conversation", id]),
  };
  const Dashboard = loadComponent("../../src/Dashboard.tsx", {
    react: {
      useMemo: (factory) => factory(),
      useCallback: (callback) => callback,
      useRef: (value) => ({ current: value }),
      useEffect: (effect) => { const cleanup = effect(); if (typeof cleanup === "function") cleanups.push(cleanup); },
    },
    antd: { Button, Card, message: { warning: (value) => warnings.push(value), error: (value) => errors.push(value) } },
    "./components/ResizableTable": Table,
    "./DashboardPersonCell": () => null,
    "./DashboardGreeting": () => null,
    "./DashboardHearingSchedule": HearingScheduleStub,
    "./DashboardMetricTiles": MetricTilesStub,
    "./DashboardRejectionReminder": RejectionReminderStub,
    "./DashboardOverview": OverviewStub,
    "./dashboardPrompts": { hearingPrompt: (item) => `开庭 ${item.case_no}`, rejectionsPrompt: () => "驳回", todayHearingsPrompt: () => "今日开庭" },
    dayjs: () => ({ format: () => "2026-10-12", day: () => 1, hour: () => 14 }),
    "./dashboardData": { useDashboardData: () => ({ data, loading: { metrics: false, todos: false, cases: false, rejections: false }, errors: {}, retry: (section) => calls.push(["retry", section]) }) },
    "./dashboardFeeNavigation.mjs": { rememberDashboardFeeQuery: (query) => calls.push(["fee-query", query.scope]) },
    "./caseDetailNavigation": { rememberCaseDetailTarget: (target) => calls.push(["case", target.serial_no]) },
    "./customerDetailNavigation": { rememberCustomerDetailTarget: (target) => calls.push(["customer", target.title]) },
    "./personal-agent/AssistantPanel": AssistantPanelStub,
    "./personal-agent/PersonalAiSpace": { PersonalAiSpace: PersonalAiSpaceStub },
    "./personal-agent/PersonalWorkspaceProvider": { usePersonalWorkspaceContext: () => workspace },
    "./detailRelationResolver": detailResolver,
    "./workspacePermissions": permissions,
  }, { AbortController, sessionStorage: { setItem: (key, value) => storage.set(key, value) } }).default;
  const props = {
    get view() { return conversationVisible ? "conversation" : "overview"; },
    isNarrowViewport: true,
    assistantFocusRequested: false,
    onAssistantFocusHandled: () => {},
    onViewChange: (view) => { conversationVisible = view === "conversation"; },
    onNavigate: (route) => calls.push(["route", route]),
    grantedMenuKeys: new Set(["finance-fee-query", "task-my-accepted", "case-mine-civil"]),
    permissionAdministrator: false,
  };
  const rendered = nodes(Dashboard(props));
  const metrics = rendered.find((node) => node.type === MetricTilesStub);
  const schedule = rendered.find((node) => node.type === HearingScheduleStub);
  const reminders = rendered.find((node) => node.type === RejectionReminderStub);
  const overview = rendered.find((node) => node.type === OverviewStub);
  assert.ok(metrics && schedule && reminders && overview);
  assert.equal(rendered.some((node) => node.type === AssistantPanelStub), false);
  assert.equal(conversationVisible, false);

  // 已授权时指标可点，并且带上请款上下文。
  metrics.props.onOpen(data.metrics[0]);
  assert.equal(JSON.parse(storage.get("sunhold:receivable-detail-context")).contract_no, "HT-1");
  assert.equal(schedule.props.canOpenCase, true);
  const caseLink = schedule.props.onOpenCase("CASE-1");
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(requests[0][0], "/records");
  assert.equal(requests[0][1].params.module, "case");
  assert.equal(requests[0][1].params.keyword, "CASE-1");
  assert.equal(requests[0][1].signal.aborted, false);
  assert.deepEqual(calls, [
    ["fee-query", "mine"], ["route", "finance-fee-query"],
    ["case", "CASE-1"], ["route", "case-detail-17-CASE-1"],
  ]);
  assert.equal(caseLink, undefined);

  // 提醒里的“交给智能体”与输入框共用同一条对话。
  schedule.props.onAsk("开庭 CASE-1");
  assert.equal(conversationVisible, true);
  const desktopConversation = nodes(Dashboard({ ...props, isNarrowViewport: false }));
  assert.equal(desktopConversation.some((node) => node.type === AssistantPanelStub), false, "PC工作台不内嵌独立AI助手");
  assert.ok(desktopConversation.some((node) => node.type === OverviewStub));
  const mobileConversation = nodes(Dashboard(props));
  assert.ok(mobileConversation.some((node) => node.type === AssistantPanelStub), "手机对话保留内嵌助手");
  const overviewButton = mobileConversation.find((node) => node.type === "button" && node.props.children === "工作概况");
  overviewButton.props.onClick();
  assert.equal(conversationVisible, false);
  const mobileOverview = nodes(Dashboard(props));
  assert.ok(mobileOverview.some((node) => node.type === OverviewStub));
  assert.equal(mobileOverview.some((node) => node.type === AssistantPanelStub), false);
  assert.equal(calls.at(-1)[0], "agent");
  assert.equal(calls.at(-1)[1], "开庭 CASE-1");
  assert.equal(mobileOverview.some((node) => node.type === "button" && node.props.children === "AI 空间"), false);
  assert.equal(mobileOverview.some((node) => node.type === PersonalAiSpaceStub), false);
  const viewSwitch = mobileOverview.find((node) => node.props.className === "wb-view-switch");
  assert.equal(viewSwitch.props.children.length, 2, "手机工作台保留工作概况与助手对话两按钮");
  assert.equal(desktopConversation.some((node) => node.props.className === "wb-view-switch"), false, "桌面删除入口后不留下空切换容器");
  assert.equal(desktopConversation.some((node) => node.type === "button" && node.props.children === "AI 空间"), false);
  assert.equal(desktopConversation.some((node) => node.type === PersonalAiSpaceStub), false);

  const successfulCallCount = calls.length;
  relatedRecords = [];
  schedule.props.onOpenCase("CASE-1");
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(requests[0][1].signal.aborted, true);
  assert.equal(calls.length, successfulCallCount);
  assert.equal(warnings.at(-1), "未找到关联案件或当前账号无权查看");
  assert.equal(errors.length, 0);

  // 未授权时不再出现可点的入口，链接降级为纯文本。
  const denied = nodes(Dashboard({ ...props, grantedMenuKeys: new Set() }));
  const deniedSchedule = denied.find((node) => node.type === HearingScheduleStub);
  assert.equal(deniedSchedule.props.canOpenSchedule, false);
  assert.equal(deniedSchedule.props.canOpenCase, false);
  assert.equal(deniedSchedule.props.canOpenCustomer, false);
  assert.equal(calls.length, successfulCallCount);
  cleanups.forEach((cleanup) => cleanup());
  assert.equal(requests.at(-1)[1].signal.aborted, true);
});
