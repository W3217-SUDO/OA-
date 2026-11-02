// 501165（tgn 11-03 07:36）：案件智能体停靠右侧、默认 2/9 宽、不遮挡案件信息；可调宽、放大、收起、浮动；记住布局；手机全屏。
import assert from "node:assert/strict";
import fs from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import { fileURLToPath } from "node:url";
import vm from "node:vm";
import React from "react";
import { act, create } from "react-test-renderer";
import ts from "typescript";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const entry = fileURLToPath(new URL("../src/legal/CaseAgentDock.tsx", import.meta.url));

function environment({ width = 1800, height = 1000, mobile = false } = {}) {
  const store = new Map([["user", JSON.stringify({ username: "tgn" })]]);
  const listeners = {};
  const classes = new Set(), styleVars = {};
  const window = {
    innerWidth: width, innerHeight: height,
    matchMedia: () => ({ matches: mobile }),
    addEventListener: (type, fn) => { (listeners[type] ||= []).push(fn); },
    removeEventListener: (type, fn) => { listeners[type] = (listeners[type] || []).filter(item => item !== fn); },
  };
  const document = { body: { classList: { add: c => classes.add(c), remove: c => classes.delete(c) }, style: { setProperty: (k, v) => { styleVars[k] = v; }, removeProperty: k => { delete styleVars[k]; } } } };
  const localStorage = { getItem: k => store.has(k) ? store.get(k) : null, setItem: (k, v) => store.set(k, String(v)) };
  const fire = (type, event) => (listeners[type] || []).slice().forEach(fn => fn(event));
  return { window, document, localStorage, store, classes, styleVars, fire };
}

function load(env) {
  const compilerOptions = { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true };
  const output = ts.transpileModule(fs.readFileSync(entry, "utf8"), { compilerOptions, fileName: entry }).outputText;
  const module = { exports: {} };
  const component = name => ({ children, ...props }) => React.createElement(name, props, children);
  const deps = { antd: { Button: component("button"), Tooltip: ({ children }) => children }, "@ant-design/icons": new Proxy({}, { get: () => "icon" }) };
  vm.runInNewContext(output, { module, exports: module.exports, require: s => deps[s] ?? createRequire(entry)(s), JSON, Math, Number, ...env }, { filename: entry });
  return module.exports;
}

const pointer = (x, y) => ({ button: 0, clientX: x, clientY: y, preventDefault() {}, target: { closest: () => null } });
const plain = value => JSON.parse(JSON.stringify(value));

test("默认停靠右侧 2/9 宽，左侧页面让出宽度；拖左边缘调宽并记住", async () => {
  const env = environment();
  const { CaseAgentDock } = load(env);
  let renderer;
  await act(async () => { renderer = create(React.createElement(CaseAgentDock, { open: true, title: "案件智能体：HZMS2600441", onClose() {} }, React.createElement("panel"))); });
  const dock = () => renderer.root.findByProps({ "aria-label": "案件智能体" });
  assert.equal(dock().props.className, "case-agent-dock is-docked");
  assert.equal(dock().props.style.width, 400, "1800 宽屏幕的 2/9");
  assert.equal(dock().props.style.right, 0);
  assert.equal(dock().props.style.bottom, 0, "tgn 07:52：默认放在右下角");
  assert.equal(dock().props.style.height, 665, "高度约为可视区（去掉顶栏）的 70%");
  const top = renderer.root.findByProps({ "aria-label": "拖动调整智能体高度" });
  await act(async () => { top.props.onPointerDown(pointer(1600, 385)); env.fire("pointermove", { clientX: 1600, clientY: 285 }); env.fire("pointerup", {}); });
  assert.equal(dock().props.style.height, 765, "拖上边缘调高");
  assert.ok(env.classes.has("case-agent-docked"));
  assert.equal(env.styleVars["--case-agent-dock-width"], "400px", "案件信息区右边让出同样宽度");
  const handle = renderer.root.findByProps({ "aria-label": "拖动调整智能体宽度" });
  await act(async () => { handle.props.onPointerDown(pointer(1400, 500)); env.fire("pointermove", { clientX: 1100, clientY: 500 }); env.fire("pointerup", {}); });
  assert.equal(dock().props.style.width, 700);
  assert.equal(plain(JSON.parse(env.store.get("oa.caseAgentDock.v2.tgn"))).mode, "docked");
  await act(async () => { handle.props.onPointerDown(pointer(1100, 500)); env.fire("pointermove", { clientX: 0, clientY: 500 }); env.fire("pointerup", {}); });
  assert.equal(dock().props.style.width, 1260, "最大 70%，左侧始终留出案件信息");
  await act(async () => { renderer.unmount(); });
  assert.equal(env.classes.has("case-agent-docked"), false, "关闭后页面恢复全宽");
});

test("放大、收起成右侧小按钮、拖出成浮动窗口，下次按上次位置打开", async () => {
  const env = environment();
  const { CaseAgentDock } = load(env);
  let renderer;
  const props = { open: true, title: "案件智能体", onClose() {} };
  await act(async () => { renderer = create(React.createElement(CaseAgentDock, props, "内容")); });
  const button = label => renderer.root.findByProps({ "aria-label": label });
  await act(async () => { button("放大").props.onClick(); });
  assert.equal(renderer.root.findByProps({ "aria-label": "案件智能体" }).props.className, "case-agent-dock is-maximized");
  await act(async () => { button("还原").props.onClick(); button("收起").props.onClick(); });
  assert.equal(renderer.root.findAllByProps({ "aria-label": "案件智能体" }).length, 0);
  assert.equal(env.classes.has("case-agent-docked"), false, "收起后案件信息占满宽度");
  await act(async () => { button("展开案件智能体").props.onClick(); });
  const header = () => renderer.root.findByType("header");
  await act(async () => { header().props.onPointerDown(pointer(1500, 70)); env.fire("pointermove", { clientX: 900, clientY: 300 }); env.fire("pointerup", {}); });
  const dock = renderer.root.findByProps({ "aria-label": "案件智能体" });
  assert.equal(dock.props.className, "case-agent-dock is-floating");
  assert.equal(env.classes.has("case-agent-docked"), false, "浮动时不占页面宽度");
  const saved = JSON.parse(env.store.get("oa.caseAgentDock.v2.tgn"));
  assert.equal(saved.mode, "floating");
  assert.deepEqual(plain(saved.float), plain({ x: dock.props.style.left, y: dock.props.style.top, w: dock.props.style.width, h: dock.props.style.height }));
  await act(async () => { renderer.unmount(); });
  let again;
  await act(async () => { again = create(React.createElement(load(env).CaseAgentDock, props, "内容")); });
  assert.equal(again.root.findByProps({ "aria-label": "案件智能体" }).props.style.left, saved.float.x, "按上次浮动位置打开");
  await act(async () => { again.root.findByProps({ "aria-label": "停靠到右侧" }).props.onClick(); });
  assert.equal(again.root.findByProps({ "aria-label": "案件智能体" }).props.className, "case-agent-dock is-docked");
  await act(async () => { again.unmount(); });
});

test("手机全屏，不停靠也不占页面宽度", async () => {
  const env = environment({ width: 390, height: 800, mobile: true });
  const { CaseAgentDock } = load(env);
  let renderer;
  await act(async () => { renderer = create(React.createElement(CaseAgentDock, { open: true, title: "案件智能体", onClose() {} }, "内容")); });
  const dock = renderer.root.findByProps({ "aria-label": "案件智能体" });
  assert.equal(dock.props.className, "case-agent-dock is-mobile");
  assert.equal(dock.props.style, undefined);
  assert.equal(renderer.root.findAllByProps({ "aria-label": "收起" }).length, 0);
  assert.equal(env.classes.has("case-agent-docked"), false);
  await act(async () => { renderer.unmount(); });
});
