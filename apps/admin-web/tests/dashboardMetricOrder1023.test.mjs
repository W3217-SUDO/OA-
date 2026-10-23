// 10.23 第4行：工作台八个提醒指标位置与颜色固定，不随案件/财务两组接口的返回先后变化。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import ts from "typescript";

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");
const jsx = (type, props, key) => ({ type, key, props: props || {} });
const loadModule = (path, stubs = {}) => {
  const compiled = ts.transpileModule(read(path), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
  }).outputText;
  const module = { exports: {} };
  const fakeRequire = (name) => stubs[name] ?? new Proxy({}, { get: (_target, key) => (key === "__esModule" ? true : () => null) });
  new Function("exports", "require", "module", compiled)(module.exports, fakeRequire, module);
  return module.exports;
};

const dashboardData = loadModule("../src/dashboardData.ts", { react: { useCallback: (fn) => fn, useEffect: () => {}, useRef: () => ({}), useState: (value) => [value, () => {}] }, "./api": { api: {} } });
const metric = (key, label, value = "1件") => ({ key, label, value, tone: "", route: `dashboard-queue-${key}` });
const CASES = [metric("evidence-supplement", "补充证据"), metric("opinion-supplement", "补充意见"), metric("appeal-pending", "待上诉"), metric("execution-pending", "待执行"), metric("urgent-cases", "紧急案件", "2件")];
const FINANCE = [metric("official-fee-unpaid", "待缴官费"), metric("refund-pending", "待退费"), metric("official-fee-unreceived", "未到官费金额", "1.00元")];
const EXPECTED = ["待缴官费", "待退费", "补充证据", "补充意见", "待上诉", "待执行", "紧急案件", "未到官费金额"];

test("第4行：无论案件组还是财务组先返回，排序结果都是原八卡固定顺序", () => {
  const caseFirst = dashboardData.orderDashboardMetrics([...CASES, ...FINANCE]).map((item) => item.label);
  const financeFirst = dashboardData.orderDashboardMetrics([...FINANCE, ...CASES]).map((item) => item.label);
  assert.deepEqual(caseFirst, EXPECTED);
  assert.deepEqual(financeFirst, EXPECTED);
  assert.deepEqual(dashboardData.DASHBOARD_METRIC_ORDER.map((item) => item.label), EXPECTED);
});

test("第4行：合并逻辑在写入状态时排序", () => {
  assert.match(read("../src/dashboardData.ts"), /metrics: orderDashboardMetrics\(Array\.from\(metrics\.values\(\)\)\)/);
});

const { default: Tiles } = loadModule("../src/DashboardMetricTiles.tsx", {
  "react/jsx-runtime": { jsx, jsxs: jsx, Fragment: "Fragment" },
  react: { useEffect: () => {}, useState: (init) => [typeof init === "function" ? false : init, () => {}] },
  antd: { Button: "Button" },
  "./dashboardData": dashboardData,
});
const findButtons = (node, output = []) => {
  if (!node || typeof node !== "object") return output;
  if (Array.isArray(node)) { node.forEach((child) => findButtons(child, output)); return output; }
  if (node.type === "button") output.push(node);
  findButtons(node.props?.children, output);
  return output;
};
const render = (metrics) => {
  globalThis.window = { localStorage: { getItem: () => "0", setItem: () => {} }, innerWidth: 1600 };
  return findButtons(Tiles({ metrics, status: null, onOpen: () => {} })).map((button) => ({
    key: button.key, className: button.props.className, disabled: Boolean(button.props.disabled),
  }));
};

test("第4行：只返回一组时另一组先占位，位置和颜色不随返回先后改变", () => {
  const onlyCases = render(CASES);
  const onlyFinance = render(FINANCE);
  const all = render([...FINANCE, ...CASES]);
  const keys = dashboardData.DASHBOARD_METRIC_ORDER.map((item) => item.key);
  for (const tiles of [onlyCases, onlyFinance, all]) assert.deepEqual(tiles.map((tile) => tile.key), keys);
  assert.deepEqual(onlyCases.filter((tile) => tile.disabled).map((tile) => tile.key), ["official-fee-unpaid", "refund-pending", "official-fee-unreceived"]);
  assert.deepEqual(onlyFinance.filter((tile) => tile.disabled).map((tile) => tile.key), CASES.map((item) => item.key));
  const tone = (tiles) => tiles.map((tile) => tile.className.match(/tone-\d+/)[0]);
  assert.deepEqual(tone(onlyCases), tone(all));
  assert.deepEqual(tone(onlyFinance), tone(all));
  assert.ok(all.find((tile) => tile.key === "urgent-cases").className.includes("is-urgent"));
});
