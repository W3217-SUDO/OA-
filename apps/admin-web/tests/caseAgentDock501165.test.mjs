// 501165（tgn 11-03 08:06）：案件智能体是浮在案件页上的窗口，右下角打开、宽 2/9 高约 70%；拖动始终在可视区内；再点按钮拉回；手机全屏。
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
  const deps = { antd: { Button: component("button"), Tooltip: ({ children }) => children, ConfigProvider: ({ children }) => children }, "@ant-design/icons": new Proxy({}, { get: () => "icon" }), "react-dom": { createPortal: node => node } };
  vm.runInNewContext(output, { module, exports: module.exports, require: s => deps[s] ?? createRequire(entry)(s), JSON, Math, Number, ...env }, { filename: entry });
  return module.exports;
}

const pointer = (x, y) => ({ button: 0, clientX: x, clientY: y, preventDefault() {}, target: { closest: () => null } });
const KEY = "oa.caseAgentWindow.v4.tgn";
const style = renderer => renderer.root.findByProps({ "aria-label": "案件智能体" }).props.style;
const render = async (Dock, props) => { let renderer; await act(async () => { renderer = create(React.createElement(Dock, { open: true, title: "案件智能体", onClose() {}, ...props }, "内容")); }); return renderer; };

test("打开时浮在右下角，宽 2/9、高约 85%，不压缩案件页", async () => {
  const env = environment();
  const { CaseAgentDock } = load(env);
  const renderer = await render(CaseAgentDock);
  assert.equal(renderer.root.findByProps({ "aria-label": "案件智能体" }).props.className, "case-agent-dock is-floating");
  assert.deepEqual({ ...style(renderer) }, { left: 1384, top: 176, width: 400, height: 808 }, "1800×1000：宽 400（2/9），高 808（去掉顶栏的 85%），右下各留 16");
  assert.equal(env.classes.size, 0, "不给案件页加任何让位样式");
  await act(async () => { renderer.unmount(); });
});

test("拖动、调大小始终留在可视区内，不会掉到页面底下", async () => {
  const env = environment();
  const { CaseAgentDock } = load(env);
  const renderer = await render(CaseAgentDock);
  const header = () => renderer.root.findByType("header");
  // 往右下猛拖：窗口贴住右下边，不出屏幕。
  await act(async () => { header().props.onPointerDown(pointer(1500, 340)); env.fire("pointermove", { clientX: 3000, clientY: 3000 }); env.fire("pointerup", {}); });
  assert.deepEqual({ ...style(renderer) }, { left: 1400, top: 192, width: 400, height: 808 });
  // 往左上猛拖：不盖住顶栏，不出左边。
  await act(async () => { header().props.onPointerDown(pointer(1500, 340)); env.fire("pointermove", { clientX: -3000, clientY: -3000 }); env.fire("pointerup", {}); });
  assert.deepEqual({ ...style(renderer) }, { left: 0, top: 50, width: 400, height: 808 });
  assert.deepEqual(JSON.parse(env.store.get(KEY)), { x: 0, y: 50, w: 400, h: 808 }, "松手后记住位置");
  // 右下角拉大：不超过可视区。
  const corner = renderer.root.findByProps({ "aria-label": "拖动调整智能体大小" });
  await act(async () => { corner.props.onPointerDown(pointer(400, 858)); env.fire("pointermove", { clientX: 5000, clientY: 5000 }); env.fire("pointerup", {}); });
  assert.deepEqual({ ...style(renderer) }, { left: 0, top: 50, width: 1800, height: 950 });
  // 浏览器窗口变小：窗口一起收进可视区。
  env.window.innerWidth = 1200; env.window.innerHeight = 700;
  await act(async () => { env.fire("resize", {}); });
  assert.deepEqual({ ...style(renderer) }, { left: 0, top: 50, width: 1200, height: 650 });
  await act(async () => { renderer.unmount(); });
});

test("记住的位置在屏幕外就回到右下角；再点“案件智能体”拉回并显示", async () => {
  const env = environment();
  env.store.set(KEY, JSON.stringify({ x: 100, y: 2400, w: 500, h: 600 }));
  const { CaseAgentDock } = load(env);
  const renderer = await render(CaseAgentDock, { revealKey: 1 });
  assert.deepEqual({ ...style(renderer) }, { left: 1384, top: 176, width: 400, height: 808 }, "旧位置在屏幕外，重置到右下角");
  env.store.set(KEY, JSON.stringify({ x: 200, y: 100, w: 500, h: 600 }));
  await act(async () => { renderer.update(React.createElement(CaseAgentDock, { open: true, title: "案件智能体", onClose() {}, revealKey: 2 }, "内容")); });
  assert.deepEqual({ ...style(renderer) }, { left: 200, top: 100, width: 500, height: 600 }, "在屏幕内的旧位置照用");
  await act(async () => { renderer.root.findByProps({ "aria-label": "收起" }).props.onClick(); });
  assert.equal(renderer.root.findAllByProps({ "aria-label": "案件智能体" }).length, 0);
  await act(async () => { renderer.update(React.createElement(CaseAgentDock, { open: true, title: "案件智能体", onClose() {}, revealKey: 3 }, "内容")); });
  assert.equal(renderer.root.findAllByProps({ "aria-label": "案件智能体" }).length, 1, "收起后再点“案件智能体”重新弹出");
  await act(async () => { renderer.root.findByProps({ "aria-label": "放大" }).props.onClick(); });
  assert.equal(renderer.root.findByProps({ "aria-label": "案件智能体" }).props.className, "case-agent-dock is-maximized");
  await act(async () => { renderer.unmount(); });
});

test("手机全屏", async () => {
  const env = environment({ width: 390, height: 800, mobile: true });
  const { CaseAgentDock } = load(env);
  const renderer = await render(CaseAgentDock);
  const dock = renderer.root.findByProps({ "aria-label": "案件智能体" });
  assert.equal(dock.props.className, "case-agent-dock is-mobile");
  assert.equal(dock.props.style, undefined);
  assert.equal(renderer.root.findAllByProps({ "aria-label": "收起" }).length, 0);
  await act(async () => { renderer.unmount(); });
});

test("501170：所在案件详情页退到后台（回列表、切页签）时窗口跟着藏起来，回来再出现", async () => {
  const env = environment();
  const classes = new Set(["workspace-page"]);
  let notify = null;
  const page = { classList: { contains: c => classes.has(c) } };
  class FakeObserver { constructor(cb) { notify = cb; } observe() {} disconnect() {} }
  const { CaseAgentDock } = load({ ...env, MutationObserver: FakeObserver });
  let renderer;
  await act(async () => {
    renderer = create(React.createElement(CaseAgentDock, { open: true, title: "案件智能体", onClose() {} }, "内容"),
      { createNodeMock: element => element.type === "span" ? { closest: selector => selector === ".workspace-page" ? page : null } : null });
  });
  const visible = () => renderer.root.findAllByProps({ "aria-label": "案件智能体" }).length === 1;
  assert.equal(visible(), true, "详情页在前台时显示");
  classes.add("is-cached");
  await act(async () => { notify(); });
  assert.equal(visible(), false, "回到列表后，详情页的智能体窗口不留在列表上");
  classes.delete("is-cached");
  await act(async () => { notify(); });
  assert.equal(visible(), true, "回到这个案件详情页，窗口原样出现");
  await act(async () => { renderer.unmount(); });
});
