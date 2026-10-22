import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { createRequire } from "node:module";
import test from "node:test";
import React from "react";
import TestRenderer, { act } from "react-test-renderer";
import ts from "typescript";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const require = createRequire(import.meta.url);
const controls = Object.fromEntries(["Alert", "Button", "Descriptions", "Modal", "Pagination", "Spin"].map(name => [name, name]));
controls.Empty = Object.assign(props => React.createElement("Empty", props), { PRESENTED_IMAGE_SIMPLE: "simple" });
const requests = [];
const api = { get(path, options) {
  return new Promise((resolve, reject) => requests.push({ path, options, resolve, reject }));
} };
const filename = new URL("../src/legal/CaseDetail/CaseSystemLogsPanel.tsx", import.meta.url);
const output = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
}).outputText;
const module = { exports: {} };
vm.runInNewContext(output, {
  module, exports: module.exports, AbortController,
  require: name => name === "antd" ? controls : name === "../../api" ? { api } : name === "../../components/ResizableTable" ? { default: "Table", __esModule: true } : name.endsWith(".css") ? {} : require(name),
});
const Panel = module.exports.CaseSystemLogsPanel;
const personName = (account, name) => name || account;
const row = (id = "legacy:101") => ({ id, source: id.split(":")[0], source_id: Number(id.split(":")[1]), source_case_no: "CODEXDOCLOG", action: "历史系统操作", comment: "上传文件：材料.pdf", operator: "actor", operator_display_name: "人员", created_at: "2026-10-01T21:00:00+08:00" });
const page = (items, value = 1) => ({ items, total: 31, page: value, page_size: 15, pages: 3 });

test("系统日志分页、详情与后端失败保持真实状态", async () => {
  requests.length = 0;
  let view;
  await act(async () => { view = TestRenderer.create(React.createElement(Panel, { caseId: 1, casePersonDisplayName: personName })); });
  assert.equal(requests[0].path, "/cases/1/system-logs");
  assert.equal(requests[0].options.params.page, 1);
  await act(async () => { requests[0].resolve({ data: page([row()]) }); });
  let table = view.root.findByType("Table");
  assert.equal(table.props.rowKey, "id");
  assert.equal(table.props.dataSource[0].id, "legacy:101");
  await act(async () => { view.root.findByType("Pagination").props.onChange(2, 15); });
  assert.equal(requests[1].options.params.page, 2);
  await act(async () => { requests[1].resolve({ data: page([row("legacy:102")], 2) }); });
  table = view.root.findByType("Table");
  await act(async () => { table.props.columns.at(-1).render(null, table.props.dataSource[0]).props.onClick(); });
  assert.equal(requests[2].path, "/cases/1/system-logs/legacy/102");
  await act(async () => { requests[2].resolve({ data: row() }); });
  assert.equal(view.root.findByType("Descriptions").props.items.find(item => item.key === "operator").children, "人员");
  await act(async () => { view.update(React.createElement(Panel, { caseId: 1, refreshKey: 1, casePersonDisplayName: personName })); });
  await act(async () => { requests[3].reject({ response: { data: { detail: "无权访问" } } }); });
  assert.equal(view.root.findByType("Alert").props.title, "无权访问");
  assert.equal(view.root.findAllByType("Table").length, 0);
  await act(async () => { view.unmount(); });
});

test("换案取消旧列表请求，过期成功不覆盖新案", async () => {
  requests.length = 0;
  let view;
  await act(async () => { view = TestRenderer.create(React.createElement(Panel, { caseId: 1, casePersonDisplayName: personName })); });
  const old = requests[0];
  await act(async () => { view.update(React.createElement(Panel, { caseId: 2, casePersonDisplayName: personName })); });
  assert.equal(old.options.signal.aborted, true);
  assert.equal(view.root.findByType("Modal").props.open, false);
  assert.equal(requests[1].path, "/cases/2/system-logs");
  await act(async () => { requests[1].resolve({ data: page([row("current:200")]) }); });
  await act(async () => { old.resolve({ data: page([row("legacy:999")]) }); });
  assert.equal(view.root.findByType("Table").props.dataSource[0].id, "current:200");
  await act(async () => { view.unmount(); });
});

test("换案关闭旧详情、取消详情请求并保留真实空状态", async () => {
  requests.length = 0;
  let view;
  await act(async () => { view = TestRenderer.create(React.createElement(Panel, { caseId: 1, casePersonDisplayName: personName })); });
  await act(async () => { requests[0].resolve({ data: page([row()]) }); });
  const table = view.root.findByType("Table");
  await act(async () => { table.props.columns.at(-1).render(null, table.props.dataSource[0]).props.onClick(); });
  const detailRequest = requests[1];
  assert.equal(view.root.findByType("Modal").props.open, true);
  await act(async () => { view.update(React.createElement(Panel, { caseId: 2, casePersonDisplayName: personName })); });
  assert.equal(detailRequest.options.signal.aborted, true);
  assert.equal(view.root.findByType("Modal").props.open, false);
  await act(async () => { detailRequest.resolve({ data: row() }); requests[2].resolve({ data: { items: [], total: 0, page: 1, page_size: 15, pages: 1 } }); });
  assert.equal(view.root.findAllByType("Descriptions").length, 0);
  assert.equal(view.root.findByType("Empty").props.description, "暂无系统日志");
  await act(async () => { view.unmount(); });
});
