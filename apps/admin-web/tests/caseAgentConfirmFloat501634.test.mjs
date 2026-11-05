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
        : 'import React from "react"; export const AgentChoice=()=>null; export const agentConfirmHeadline=(a)=>"修改/编辑确认：修改案件基本信息"; export const agentOperationName=a=>"修改案件"; export const agentConfirmTable=a=>a.table; export const hasAgentOperationPreview=a=>!a.noPreview;' }));
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

test("一项时直接批准/驳回；缩小只收起不处理", async () => {
  const CaseAgentConfirmFloat = await loadFloat();
  const calls = [];
  let renderer;
  const props = { actions: [actions[0]], failures: {}, decisionLoading: "", disabled: (a) => a.status === "executing",
    onDecide: async (a, d) => { calls.push(["decide", a.id, d]); return ""; }, onMinimize: () => calls.push(["minimize"]) };
  await act(async () => { renderer = create(React.createElement(CaseAgentConfirmFloat, props)); });
  const button = (label) => renderer.root.findAllByType("button").find((b) => b.props.children === label || b.props["aria-label"] === label);
  const shown = textOf(renderer.toJSON());
  assert.match(shown, /^待确认修改\/编辑确认：修改案件基本信息/, "tgn 11-05 07:22：标题只写动了哪块");
  assert.doesNotMatch(shown, /案号|第 1\/|驳回此项/, "不写案号、不翻页；只有一项时没有“驳回此项”");
  assert.match(shown, /字段现状改为案由侵害商标权纠纷离婚纠纷/, "修改：字段 / 现状 / 改为");
  await act(async () => button("缩小确认窗口").props.onClick());
  assert.deepEqual(calls, [["minimize"]], "缩小不能批准或驳回");
  await act(async () => button("批准并执行").props.onClick());
  await act(async () => button("驳回，不修改").props.onClick());
  assert.deepEqual(calls.slice(1), [["decide", "a1", "approved"], ["decide", "a1", "rejected"]]);
});

test("一句话拆成几项（tgn 11-05 07:47）：一个窗口全部列出，全部批准逐项办，失败就停；每项可单独驳回", async () => {
  const CaseAgentConfirmFloat = await loadFloat();
  const items = [actions[0], { ...actions[0], id: "a3", table: { mode: "change", rows: [{ field: "handling_lawyers", label: "经办律师", before: "曹志刚", after: "曹志刚、沈建锋" }] } }, actions[1]];
  const calls = [];
  let fail = "";
  let renderer;
  const props = () => ({ actions: items, failures: {}, decisionLoading: "", disabled: (a) => a.status === "executing",
    onDecide: async (a, d) => { calls.push([a.id, d]); return a.id === fail ? "原因" : ""; }, onMinimize() {} });
  await act(async () => { renderer = create(React.createElement(CaseAgentConfirmFloat, props())); });
  const buttons = () => renderer.root.findAllByType("button");
  const button = (label) => buttons().find((b) => b.props.children === label);
  const shown = textOf(renderer.toJSON());
  assert.match(shown, /共 3 项修改，请一起确认/);
  assert.match(shown, /案由侵害商标权纠纷离婚纠纷/);
  assert.match(shown, /经办律师曹志刚曹志刚、沈建锋/, "第二项也直接显示，不用翻页");
  assert.match(shown, /正在执行/);
  assert.equal(buttons().filter((b) => b.props.children === "驳回此项").length, 3);
  await act(async () => button("全部批准并执行").props.onClick());
  assert.deepEqual(calls, [["a1", "approved"], ["a3", "approved"]], "正在执行的那项跳过，按顺序逐项批准");
  calls.length = 0; fail = "a1";
  await act(async () => button("全部批准并执行").props.onClick());
  assert.deepEqual(calls, [["a1", "approved"]], "有一项没执行成功就停下");
  calls.length = 0;
  await act(async () => buttons().filter((b) => b.props.children === "驳回此项")[1].props.onClick());
  assert.deepEqual(calls, [["a3", "rejected"]]);
});

test("没有待确认时不渲染", async () => {
  const CaseAgentConfirmFloat = await loadFloat();
  let renderer;
  await act(async () => { renderer = create(React.createElement(CaseAgentConfirmFloat, { actions: [], failures: {}, decisionLoading: "", disabled: () => false, onDecide() {}, onMinimize() {} })); });
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
