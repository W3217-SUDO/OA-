// 501634（tgn 11-05）：确认窗口里的信息跟页面一致：案号代替案件ID，不出现“其他信息”编号、英文代码。
import test from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import Module, { createRequire } from "node:module";
import { build } from "esbuild";
import React from "react";
import { act, create } from "react-test-renderer";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
async function loadPreview() {
  const output = await build({
    entryPoints: [fileURLToPath(new URL("../src/AgentOperationPreview.tsx", import.meta.url))],
    bundle: true, write: false, platform: "node", format: "cjs", packages: "external", loader: { ".css": "empty" },
    plugins: [{ name: "stub-antd-501634", setup(builder) {
      builder.onResolve({ filter: /^antd$|ResizableTable$/ }, ({ path }) => ({ path, namespace: "stub" }));
      builder.onLoad({ filter: /.*/, namespace: "stub" }, ({ path }) => ({ resolveDir: fileURLToPath(new URL(".", import.meta.url)), contents: path !== "antd" ? 'import React from "react"; export default p=>React.createElement("table",p);' :
        'import React from "react"; const C=n=>p=>React.createElement(n,p,p.children); export const Tag=C("tag"),Alert=C("alert"),Radio=Object.assign(C("radio"),{Group:C("radio-group")}),Space=C("space"),Button=C("button"),Collapse=C("collapse"),Typography={Text:C("text")}; export const Descriptions=Object.assign(C("descriptions"),{Item:C("descriptions-item")});' }));
    } }],
  });
  const target = new Module(fileURLToPath(import.meta.url));
  target.paths = Module._nodeModulePaths(fileURLToPath(new URL(".", import.meta.url)));
  target.require = createRequire(import.meta.url);
  target._compile(output.outputFiles[0].text, fileURLToPath(import.meta.url));
  return target.exports;
}
const textOf = (node) => node == null ? "" : typeof node === "string" ? node : Array.isArray(node) ? node.map(textOf).join("") : textOf(node.children);

test("老卡片摘要：案件ID 换成案号，去掉“其他信息：编号”", async () => {
  const { readableAgentSummary } = await loadPreview();
  const old = "修改案件（案件ID：501332；其他信息：280154；其他信息：280197）：名称：10.30测试客户，案由：离婚纠纷";
  assert.equal(readableAgentSummary(old, "HZMS2650002"), "修改案件（案号：HZMS2650002）：名称：10.30测试客户，案由：离婚纠纷");
});

test("确认信息：编号显示成案号、名称；换不了的编号、内部代码不显示", async () => {
  const { AgentOperationPreview } = await loadPreview();
  const action = { id: "r1", type: "mcp.call", status: "pending", summary: "修改案件（案号：HZMS2650002）", payload: { request_id: "r1" }, preview: {
    operation_name: "修改案件", method: "PUT", path: "/cases/501332/normal-basic", requires_confirmation: true,
    params: { path: { case_id: 501332 }, query: {}, body: { customer_record_id: 280154, case_phase: "新案待分配", cause_or_charge: "离婚纠纷", unknown_code: "abc123", investigation_clue_ids: [999], handling_lawyers: ["System"] } },
    field_labels: { case_id: "案号", customer_record_id: "客户", case_phase: "案件阶段", cause_or_charge: "案由", unknown_code: "其他信息", investigation_clue_ids: "关联线索", handling_lawyers: "经办律师" },
    value_labels: { case_id: { "501332": "HZMS2650002" }, customer_record_id: { "280154": "10.30测试客户" } },
  } };
  let renderer;
  await act(async () => { renderer = create(React.createElement(AgentOperationPreview, { action, target: "HZMS2650002" })); });
  const text = textOf(renderer.toJSON());
  assert.match(text, /案号HZMS2650002/);
  assert.match(text, /客户10\.30测试客户/);
  assert.match(text, /案件阶段新案待分配/);
  assert.match(text, /经办律师系统/);
  assert.doesNotMatch(text, /System/);
  assert.doesNotMatch(text, /501332|280154|abc123|999|其他信息/);
  assert.match(text, /另有 2 项系统内部参数未显示/);
});

test("逐字段“原值 → 新值”：只列改了的，原来没有写（空），没变的只说几项", async () => {
  const { AgentOperationPreview } = await loadPreview();
  const action = { id: "r2", type: "mcp.call", status: "pending", summary: "修改案件（案号：HZMS2650002）", payload: { request_id: "r2" }, preview: {
    operation_name: "修改案件", method: "PUT", path: "/cases/501332/normal-basic", requires_confirmation: true,
    params: { path: { case_id: 501332 }, query: {}, body: { cause_or_charge: "离婚纠纷", case_phase: "新案待分配", title: "10.30测试客户", handling_lawyers: ["System"] } },
    changes: [
      { field: "cause_or_charge", before: "侵害商标权纠纷", before_read: true, after: "离婚纠纷" },
      { field: "case_phase", before: null, before_read: true, after: "新案待分配" },
      { field: "title", before: "10.30测试客户", before_read: true, after: "10.30测试客户" },
      { field: "handling_lawyers", before: ["System"], before_read: true, after: ["System"] },
    ],
    field_labels: { case_id: "案号", cause_or_charge: "案由", case_phase: "案件阶段", title: "名称", handling_lawyers: "经办律师" },
    value_labels: { case_id: { "501332": "HZMS2650002" }, handling_lawyers: { System: "系统" } },
  } };
  let renderer;
  await act(async () => { renderer = create(React.createElement(AgentOperationPreview, { action, target: "HZMS2650002" })); });
  const text = textOf(renderer.toJSON());
  assert.match(text, /案由：侵害商标权纠纷 → 离婚纠纷/);
  assert.match(text, /案件阶段：（空） → 新案待分配/);
  assert.match(text, /其余 2 项保持不变/);
  assert.doesNotMatch(text, /名称：10\.30测试客户 →/);
  assert.equal((text.match(/离婚纠纷/g) || []).length, 1, "提交字段不再重复列一遍");
});
