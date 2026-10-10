import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import Module, { createRequire } from 'node:module';
import { build } from 'esbuild';
import ts from 'typescript';
import React from 'react';
import { act, create } from 'react-test-renderer';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const read = path => fs.readFileSync(new URL(path, import.meta.url), 'utf8');
const source = path => ts.createSourceFile(path, read(path), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
function find(root, predicate) {
  if (predicate(root)) return root;
  return ts.forEachChild(root, child => find(child, predicate));
}
function expression(text, bindings = {}) {
  const code = ts.transpileModule(`const value = ${text};`, { compilerOptions: { target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.React } }).outputText;
  return new Function(...Object.keys(bindings), code + '\nreturn value;')(...Object.values(bindings));
}
async function load(path, api = {}, messages = []) {
  const output = await build({ entryPoints: [fileURLToPath(new URL(path, import.meta.url))], bundle: true, write: false, platform: 'node', format: 'cjs', packages: 'external', plugins: [{
    name: 'isolated-clue-ui', setup(builder) {
      builder.onResolve({ filter: /\/api$/ }, () => ({ path: 'api', namespace: 'verification' }));
      builder.onResolve({ filter: /^antd$/ }, () => ({ path: 'antd', namespace: 'verification' }));
      builder.onLoad({ filter: /.*/, namespace: 'verification' }, ({ path }) => ({ contents: path === 'api' ? 'export const api=globalThis.__clueApi;' : 'export const message=globalThis.__clueMessages; export const Button="button"; export const Modal="modal"; export const Select="select"; export const Alert="alert"; export const Spin="spin"; export const Descriptions="descriptions"; export const Tag="tag";' }));
    },
  }] });
  const target = new Module(fileURLToPath(import.meta.url));
  target.paths = Module._nodeModulePaths(fileURLToPath(new URL('.', import.meta.url)));
  target.require = createRequire(import.meta.url);
  globalThis.__clueApi = api;
  globalThis.__clueMessages = { success: text => messages.push(text), warning: text => messages.push(text), error: text => messages.push(text) };
  try { target._compile(output.outputFiles[0].text, fileURLToPath(import.meta.url)); return target.exports; }
  finally { delete globalThis.__clueApi; delete globalThis.__clueMessages; }
}

test('R13 配置窗口读取、清空保存，失败留窗并明确报错', async () => {
  const calls = [], messages = [];
  let fail = false;
  const { default: Setting } = await load('../src/InvestigationSupervisorSetting.tsx', {
    get: async () => ({ data: { items: [{ key: 'investigation_assignment', value: { supervisor_username: 'CODEX-929-supervisor' } }], investigation_supervisor_options: [{ username: 'CODEX-929-supervisor', display_name: '调查主管' }] } }),
    patch: async (...args) => { calls.push(args); if (fail) throw { response: { data: { detail: '保存失败' } } }; },
  }, messages);
  let renderer;
  await act(async () => { renderer = create(React.createElement(Setting)); });
  await act(async () => { renderer.root.findByType('button').props.onClick(); });
  assert.equal(renderer.root.findByType('select').props.value, 'CODEX-929-supervisor');
  assert.equal(renderer.root.findByType('select').props.allowClear, true);
  await act(async () => { renderer.root.findByType('select').props.onChange(undefined); });
  await act(async () => { renderer.root.findByType('modal').props.onOk(); });
  assert.deepEqual(calls[0], ['/system/configs/investigation_assignment', { value: { supervisor_username: '' } }]);
  assert.equal(renderer.root.findByType('modal').props.open, false);
  await act(async () => { renderer.root.findByType('button').props.onClick(); });
  fail = true;
  await act(async () => { renderer.root.findByType('modal').props.onOk(); });
  assert.equal(renderer.root.findByType('modal').props.open, true);
  assert.equal(messages.at(-1), '保存失败');
  await act(async () => renderer.unmount());
});

test('R13 关闭窗口取消请求，旧响应不会重新填入已关闭窗口', async () => {
  let resolve, signal;
  const { default: Setting } = await load('../src/InvestigationSupervisorSetting.tsx', {
    get: (_url, options) => { signal = options.signal; return new Promise(done => { resolve = done; }); },
  });
  let renderer;
  await act(async () => { renderer = create(React.createElement(Setting)); });
  await act(async () => { renderer.root.findByType('button').props.onClick(); });
  await act(async () => { renderer.root.findByType('modal').props.onCancel(); });
  assert.equal(signal.aborted, true);
  await act(async () => resolve({ data: { items: [{ key: 'investigation_assignment', value: { supervisor_username: 'stale' } }], investigation_supervisor_options: [] } }));
  assert.equal(renderer.root.findByType('modal').props.open, false);
  assert.equal(renderer.root.findByType('select').props.value, undefined);
  await act(async () => renderer.unmount());
});

test('R20 新增渠道与原渠道一起用于新建、修改共享选项', async () => {
  const { CLUE_SALES_CHANNEL_OPTIONS: channels } = await load('../src/investigation/constants.ts');
  for (const value of ['淘宝', '天猫', '京东', '阿里巴巴', '苏宁', '1号店', '其他']) assert.ok(channels.includes(value));
  assert.equal(new Set(channels).size, channels.length);
});

test('R22 关联案件按钮跳转带真实案号的详情，不依赖公司案件菜单', async () => {
  const page = source('../src/investigation/InvestigationCenterPage.tsx');
  const node = find(page, item => ts.isVariableDeclaration(item) && item.name.getText(page) === 'openLinkedCase');
  const routes = [], warnings = [], errors = [], requests = [];
  let items = [{ id: 12, serial_no: 'CODEX-929-案号/1' }];
  const open = expression(node.initializer.getText(page), { api: { get: async (...args) => { requests.push(args); return { data: { items } }; } }, message: { warning: value => warnings.push(value), error: value => errors.push(value) }, onNavigate: value => routes.push(value), setLinkedCase: () => assert.fail('路由存在时不应开另一个入口') });
  await open(' CODEX-929-案号/1 ');
  assert.deepEqual(routes, ['case-detail-12-CODEX-929-%E6%A1%88%E5%8F%B7%2F1']);
  assert.equal(requests[0][1].params.module, 'case');
  items = [];
  await open('CODEX-929-无权限');
  assert.equal(routes.length, 1);
  assert.equal(warnings.length, 1);
  await open('');
  assert.equal(requests.length, 2);
  assert.equal(errors.length, 0);
});

test('R24 详情表保留完整字段和关联事件，标签使用专用固定宽度不换行', async () => {
  const { default: Header } = await load('../src/investigation/ClueDetail/ClueDetailHeader.tsx');
  const cases = [], longName = 'CODEX-929-很长的客户名称'.repeat(8);
  const view = Header({ investigationDetail: { module: 'clue', serial_no: 'CODEX-929-线索', status: '待审批', customer: longName, title: '调查事项', data: { case_no: 'CODEX-929-CASE', sales_channel: '阿里巴巴' } }, projectedPersonDisplayName: () => '调查员', onOpenLinkedCase: no => cases.push(no) });
  assert.equal(view.props.className, 'investigation-clue-summary');
  assert.equal(view.props.column, 2);
  assert.equal(view.props.items.find(item => item.key === 'customer').children.props.children, longName);
  view.props.items.find(item => item.key === 'case').children.props.onClick();
  assert.deepEqual(cases, ['CODEX-929-CASE']);
  const css = read('../src/investigation-center.css');
  assert.match(css, /\.investigation-clue-summary \.ant-descriptions-item-label\s*\{[^}]*width:\s*112px;[^}]*white-space:\s*nowrap;/);
  assert.match(css, /\.investigation-clue-summary \.ant-descriptions-view\s*\{[^}]*overflow-x:\s*auto;/);
});

test('R25 退款长文本保留全文提示、原链接动作及操作列，其他财务列不受影响', async () => {
  const { createConfiguredColumns } = await load('../src/finance/columns/configuredColumns.tsx');
  const clicked = [], longText = 'CODEX-929-长名称'.repeat(20);
  const context = { activeRouteConfig: { headers: ['操作', '原告', '客户'] }, initialView: 'finance-refund', isRefundCaseFeeRoute: true, cellValue: (_row, header) => header === '客户' ? 'CODEX-929-客户' : longText, refundCaseFeeOperation: () => React.createElement('button', { onClick: () => clicked.push('操作') }, '操作'), openFinanceCustomerDetail: () => clicked.push('客户') };
  const columns = createConfiguredColumns(context);
  const text = columns[1].render(null, {});
  assert.equal(text.props.title, longText);
  assert.equal(text.props.children, longText);
  const link = columns[2].render(null, {});
  assert.equal(link.props.children.type, 'button');
  link.props.children.props.onClick();
  columns[0].render(null, {}).props.onClick();
  assert.deepEqual(clicked, ['客户', '操作']);
  const nodeValue = React.createElement('span', null, '节点');
  const nodeColumn = createConfiguredColumns({ ...context, cellValue: () => nodeValue })[1];
  assert.equal(nodeColumn.render(null, {}).props.title, undefined);
  const ordinary = createConfiguredColumns({ ...context, isRefundCaseFeeRoute: false });
  assert.equal(ordinary[1].render(null, {}), longText);
});

test('R26 已授权开庭排期标题实际点击跳到我的案件开庭排期，未授权不显示跳转入口', async () => {
  const page = source('../src/Dashboard.tsx');
  const title = find(page, item => ts.isJsxAttribute(item) && item.name.getText(page) === 'title' && item.initializer?.getText(page).includes('case-mine-schedule'));
  assert.ok(title);
  const routes = [];
  const { isWorkspaceRouteGranted } = await load('../src/workspacePermissions.ts');
  const renderTitle = granted => expression(title.initializer.expression.getText(page), {
    React, Button: 'button', onNavigate: route => routes.push(route),
    canNavigate: route => isWorkspaceRouteGranted(route, granted),
  });
  const button = renderTitle(new Set(['case-mine-schedule']));
  assert.equal(button.props.children, '开庭排期');
  button.props.onClick();
  assert.deepEqual(routes, ['case-mine-schedule']);
  assert.equal(renderTitle(new Set()), '开庭排期');
  assert.equal(renderTitle(new Set(['case-mine-civil'])), '开庭排期');
  assert.deepEqual(routes, ['case-mine-schedule']);
});
