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

test("确认表格（tgn 11-06）：修改只列要改的“字段/现状/改为”，新增是“字段/内容”，顶部一行操作对象", async () => {
  const { agentConfirmTable, agentConfirmHeadline } = await loadPreview();
  const preview = {
    operation_name: "修改案件", method: "PUT", path: "/cases/501332/normal-basic", requires_confirmation: true, target: "HZMS2650002 10.30测试客户",
    params: { path: { case_id: 501332 }, query: {}, body: {} },
    changes: [
      { field: "customer_record_id", before: 280154, before_read: true, after: 280154 },
      { field: "title", before: "10.30测试客户", before_read: true, after: "10.30测试客户" },
      { field: "case_phase", before: null, before_read: true, after: "新案待分配" },
      { field: "cause_or_charge", before: "侵害商标权纠纷", before_read: true, after: "离婚纠纷" },
      { field: "handling_lawyers", before: ["System"], before_read: true, after: ["System"] },
      { field: "investigation_clue_ids", before: [280197], before_read: true, after: [280197] },
      { field: "unknown_code", before: "a", before_read: true, after: "b" },
    ],
    field_labels: { customer_record_id: "客户", title: "名称", case_phase: "案件阶段", cause_or_charge: "案由", handling_lawyers: "经办律师", investigation_clue_ids: "关联线索", unknown_code: "其他信息" },
    value_labels: { customer_record_id: { "280154": "10.30测试客户" }, handling_lawyers: { System: "系统" }, investigation_clue_ids: { "280197": "M26103970-R" } },
  };
  const action = { id: "m1", type: "mcp.call", status: "pending", summary: "长摘要", payload: { request_id: "m1" }, preview };
  assert.deepEqual(agentConfirmTable(action), { mode: "change", rows: [
    { field: "case_phase", label: "案件阶段", before: "（空）", after: "新案待分配" },
    { field: "cause_or_charge", label: "案由", before: "侵害商标权纠纷", after: "离婚纠纷" },
  ] });
  // tgn 11-05 07:47：人员显示姓名；同一批人原来存姓名、这次写账号的算没变。
  const people = { ...action, preview: { ...preview, changes: [
    { field: "handling_lawyers", before: ["曹志刚"], before_read: true, after: ["caozg", "shenjf"] },
    { field: "assistant", before: "郝蕴,鲍宇琳", before_read: true, after: "haoyun,baoyulin" },
  ], field_labels: { handling_lawyers: "经办律师", assistant: "律师助理" },
    value_labels: { handling_lawyers: { caozg: "曹志刚", shenjf: "沈建锋" }, assistant: { "haoyun,baoyulin": "郝蕴、鲍宇琳" } } } };
  const peopleRows = agentConfirmTable(people).rows;
  assert.equal(peopleRows.length, 1, "律师助理没变，不列");
  assert.equal(peopleRows[0].label, "经办律师");
  assert.match(peopleRows[0].after, /曹志刚.*沈建锋/);
  assert.doesNotMatch(peopleRows[0].after, /caozg|shenjf/);
  // tgn 11-05 07:22：不写案号，只写动了哪一块。
  assert.equal(agentConfirmHeadline({ ...action, preview: { ...preview, sections: ["案件基本信息"] } }), "修改/编辑确认：修改案件基本信息");
  assert.equal(agentConfirmHeadline({ ...action, preview: { ...preview, sections: ["诉讼标的"] } }), "修改/编辑确认：修改诉讼标的");
  assert.equal(agentConfirmHeadline({ ...action, preview: { ...preview, sections: ["案件基本信息", "经办律师信息"] } }), "修改/编辑确认：修改案件基本信息、经办律师信息");
  assert.equal(agentConfirmHeadline({ ...action, preview: { ...preview, operation_name: "修改法院信息" } }), "修改/编辑确认：修改法院信息", "老卡片没有区块时用操作名");
  assert.doesNotMatch(agentConfirmHeadline(action), /案号|HZMS/);
  const create = { ...action, preview: { ...preview, changes: undefined, create: { title: "举证期限", deadline: "2026-11-20", note_code: "x1" },
    field_labels: { title: "名称", deadline: "截止日期", note_code: "其他信息" } } };
  assert.deepEqual(agentConfirmTable(create), { mode: "create", rows: [
    { field: "title", label: "名称", after: "举证期限" }, { field: "deadline", label: "截止日期", after: "2026-11-20" },
  ] });
  assert.equal(agentConfirmHeadline({ ...create, preview: { ...create.preview, operation_name: "新增案件期限" } }), "新增确认：新增案件期限");
});
