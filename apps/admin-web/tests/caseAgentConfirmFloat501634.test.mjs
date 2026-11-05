// 501634（tgn 11-05）：案件智能体写入确认改成浮动确认窗口；缩小不算处理，有“待确认 N”入口；逻辑不变。
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import Module, { createRequire } from "node:module";
import { build } from "esbuild";
import React from "react";
import { act, create } from "react-test-renderer";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");

async function loadFloat() {
  const output = await build({
    entryPoints: [fileURLToPath(new URL("../src/legal/CaseAgentConfirmFloat.tsx", import.meta.url))],
    bundle: true, write: false, platform: "node", format: "cjs", packages: "external", loader: { ".css": "empty" },
    plugins: [{ name: "stub-501634", setup(builder) {
      builder.onResolve({ filter: /^antd$|^@ant-design\/icons$|AgentOperationPreview$/ }, ({ path }) => ({ path, namespace: "stub" }));
      builder.onLoad({ filter: /.*/, namespace: "stub" }, ({ path }) => ({ resolveDir: fileURLToPath(new URL(".", import.meta.url)), contents:
        path === "antd" ? 'import React from "react"; export const Button=p=>React.createElement("button",p,p.children); export const Tag=p=>React.createElement("tag",p,p.children); export const Tooltip=p=>p.children; export const Alert=p=>React.createElement("alert",p);'
        : path === "@ant-design/icons" ? 'const I=()=>null; export const CheckOutlined=I,CloseOutlined=I,LeftOutlined=I,MinusOutlined=I,RightOutlined=I;'
        : 'import React from "react"; export const AgentChoice=()=>null; export const agentConfirmHeadline=(a,t)=>"修改案件 "+t; export const agentConfirmTable=a=>a.table; export const hasAgentOperationPreview=a=>!a.noPreview;' }));
    } }],
  });
  const target = new Module(fileURLToPath(import.meta.url));
  target.paths = Module._nodeModulePaths(fileURLToPath(new URL(".", import.meta.url)));
  target.require = createRequire(import.meta.url);
  target._compile(output.outputFiles[0].text, fileURLToPath(import.meta.url));
  return target.exports.CaseAgentConfirmFloat;
}

const textOf = (node) => node == null ? "" : typeof node === "string" ? node : Array.isArray(node) ? node.map(textOf).join("") : textOf(node.children);
const actions = [
  { id: "a1", summary: "案由改为离婚纠纷", status: "pending", type: "case.update", table: { mode: "change", rows: [{ field: "cause_or_charge", label: "案由", before: "侵害商标权纠纷", after: "离婚纠纷" }] } },
  { id: "a2", summary: "新增期限", status: "executing", type: "mcp.call", table: { mode: "create", rows: [{ field: "title", label: "期限名称", after: "举证期限" }] } },
];

test("浮动窗口直接批准/驳回；缩小只收起不处理；多项可翻页", async () => {
  const CaseAgentConfirmFloat = await loadFloat();
  const calls = [];
  let current = "a1";
  const props = () => ({ actions, currentId: current, target: "HZMS2650002", failures: {}, decisionLoading: "", disabled: (a) => a.status === "executing",
    onSelect: (id) => { current = id; calls.push(["select", id]); }, onDecide: (a, d) => calls.push(["decide", a.id, d]), onMinimize: () => calls.push(["minimize"]) });
  let renderer;
  await act(async () => { renderer = create(React.createElement(CaseAgentConfirmFloat, props())); });
  const button = (label) => renderer.root.findAllByType("button").find((b) => b.props.children === label || b.props["aria-label"] === label);
  const shown = textOf(renderer.toJSON());
  assert.match(shown, /修改案件 HZMS2650002/);
  assert.match(shown, /第 1\/2 项/);
  assert.match(shown, /字段现状改为案由侵害商标权纠纷离婚纠纷/, "修改：字段 / 现状 / 改为");
  assert.doesNotMatch(shown, /写入须人工确认|另有/, "不再有重复说明");
  await act(async () => button("缩小确认窗口").props.onClick());
  assert.deepEqual(calls, [["minimize"]], "缩小不能批准或驳回");
  await act(async () => button("批准并执行").props.onClick());
  await act(async () => button("驳回，不修改").props.onClick());
  assert.deepEqual(calls.slice(1), [["decide", "a1", "approved"], ["decide", "a1", "rejected"]]);
  await act(async () => button("下一项").props.onClick());
  await act(async () => renderer.update(React.createElement(CaseAgentConfirmFloat, props())));
  assert.equal(button("批准并执行").props.disabled, true, "正在执行的不能重复批准");
  assert.equal(button("驳回，不修改").props.disabled, true);
  assert.match(textOf(renderer.toJSON()), /正在执行/);
  assert.match(textOf(renderer.toJSON()), /字段内容期限名称举证期限/, "新增：字段 / 内容，没有现状列");
});

test("没有待确认时不渲染", async () => {
  const CaseAgentConfirmFloat = await loadFloat();
  let renderer;
  await act(async () => { renderer = create(React.createElement(CaseAgentConfirmFloat, { actions: [], currentId: null, failures: {}, decisionLoading: "", disabled: () => false, onSelect() {}, onDecide() {}, onMinimize() {} })); });
  assert.equal(renderer.toJSON(), null);
});

test("案件智能体：新的待确认自动弹出，缩小后有“待确认 N”入口，收起到侧边也显示", () => {
  const drawer = read("../src/legal/CaseAgentDrawer.tsx");
  const dock = read("../src/legal/CaseAgentDock.tsx");
  assert.match(drawer, /const fresh = waitingActions\.find\(\(action\) => !minimizedIds\.includes\(action\.id\)\);/);
  assert.match(drawer, /if \(fresh && !confirmOpen\) \{ setConfirmId\(fresh\.id\); setConfirmOpen\(true\); \}/);
  assert.match(drawer, /\{waitingActions\.length && !confirmOpen \? <button type="button" className="case-agent-pending-pill" onClick=\{openConfirm\}>/);
  assert.match(drawer, /pendingCount=\{waitingActions\.length\}/);
  assert.doesNotMatch(drawer, /<Modal open=\{Boolean\(activeAction\)\}/, "不再先点“查看并确认”再弹窗");
  assert.match(dock, /\{pendingCount > 0 && <b className="case-agent-dock-tab-pending">待确认 \{pendingCount\}<\/b>\}/);
});

test("浮动窗口层级压过智能体窗口，样式兼容钉钉 Chrome 100", () => {
  const css = read("../src/agentPending.css").replace(/\/\*[\s\S]*?\*\//g, "");
  assert.match(css, /\.case-agent-confirm-float \{[^}]*position: fixed;[^}]*z-index: 1650;/);
  assert.doesNotMatch(css, /color-mix\(|:has\(|@container|dvh/);
});
