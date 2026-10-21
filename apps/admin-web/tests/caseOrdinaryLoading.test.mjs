import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';
import * as React from 'react';
import { act, create } from 'react-test-renderer';
import { buildCaseOrdinarySearchPayload, parseOrdinarySearchResult, createLatestRequestGuard } from '../src/caseOrdinarySearchParity.mjs';

const parse = relative => ts.createSourceFile(relative, fs.readFileSync(new URL(relative, import.meta.url), 'utf8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
const page = parse('../src/legal/CaseCenterPage.tsx');
const service = parse('../src/legal/services/queriesActions.tsx');
function find(node, predicate) {
  if (predicate(node)) return node;
  return ts.forEachChild(node, child => find(child, predicate));
}
const variable = (root, name) => find(root, node => ts.isVariableDeclaration(node) && node.name.getText(root) === name);
function runExpression(node, root, bindings) {
  const js = ts.transpileModule(`const result = ${node.getText(root)};`, { compilerOptions: { target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.React } }).outputText;
  return new Function('React', ...Object.keys(bindings), js + '\nreturn result;')(React, ...Object.values(bindings));
}
function initialValue(name) {
  const node = find(page, node => ts.isVariableDeclaration(node) && ts.isArrayBindingPattern(node.name) && node.name.elements[0].name?.getText(page) === name);
  return runExpression(node.initializer, page, { useState: initial => typeof initial === 'function' ? initial() : initial });
}
function tableForDataSource(expression) {
  const found = find(page, node => (ts.isJsxSelfClosingElement(node) || ts.isJsxOpeningElement(node)) && node.tagName.getText(page) === 'Table' && node.attributes.properties.some(attr => ts.isJsxAttribute(attr) && attr.name.getText(page) === 'dataSource' && attr.initializer?.expression?.getText(page) === expression));
  assert.ok(found, `actual table for ${expression} must exist`);
  return found;
}
const table = tableForDataSource('counselListMode?counselCases:originalCases');
function tableValue(name, state) {
  const attribute = table.attributes.properties.find(node => ts.isJsxAttribute(node) && node.name.getText(page) === name);
  return runExpression(attribute.initializer.expression, page, { counselListMode: false, ...state });
}
function deferred() { let resolve, reject; const promise = new Promise((a,b) => { resolve = a; reject = b; }); return { promise, resolve, reject }; }
const result = (items = [], total = items.length) => ({ data: { items, total, page: 1, page_size: 15, phase_counts: {} } });
function setup() {
  const state = { loading: false, ordinaryLoading: initialValue('ordinaryLoading'), ordinaryLoadError: initialValue('ordinaryLoadError'), ordinaryCases: [] };
  const requests = [], messages = [], side = deferred();
  const setters = new Proxy({}, { get: (_target, name) => name.startsWith('set') ? value => { const field = name[3].toLowerCase() + name.slice(4); state[field] = value; } : undefined });
  const context = new Proxy({ ordinaryRequestGuard: createLatestRequestGuard(), originalPageSize: 15, caseQuery: {}, ordinaryScope: 'company', ordinaryCaseTypes: ['民事案件'], initialView: 'case-company-civil', isCreateView: false, isCaseDetailView: false }, { get: (target, name) => name in target ? target[name] : setters[name] });
  const api = { post: (_url, payload) => { const request = deferred(); requests.push({ ...request, payload }); return request.promise; }, get: (url, config) => url === '/records' && config?.params?.module === 'case' ? side.promise : Promise.resolve({ data: { items: [] } }) };
  const bindings = { context, api, message: { error: value => messages.push(value), warning: value => messages.push(value) }, buildCaseOrdinarySearchPayload, parseOrdinarySearchResult, loadCaseCapabilities: () => {}, loadCaseRelations: () => {}, consumeCaseDetailTarget: () => null };
  const ordinary = runExpression(variable(service, 'loadOrdinaryCases').initializer, service, bindings);
  const load = runExpression(variable(service, 'load').initializer, service, bindings);
  return { state, requests, messages, side, ordinary, load };
}
test('initial ordinary table renders loading feedback before effects, never empty-result text', () => {
  const { state } = setup();
  assert.equal(tableValue('loading', state), true);
  assert.equal(tableValue('locale', state).emptyText, '案件加载中…');
});

test('batch execution and receipt pagination accepts 200 and resets changed size to page one', async () => {
  const requests = [], selected = [];
  const bindings = {
    pendingExecutionPage: 6, pendingExecutionPageSize: 20, pendingExecutionTotal: 201,
    loadPendingExecutionCases: (...args) => requests.push(args),
    setSelectedCaseKeys: value => selected.push(value),
    receiptList: { page: 6, pageSize: 20, total: 201, search: (...args) => requests.push(args) },
    specialCaseList: { active: false, page: 6, pageSize: 20, total: 201, search: (...args) => requests.push(args) },
  };
  for (const mode of ['execution', 'receipt', 'unclaimed', 'refund']) {
    const value = runExpression(variable(page, 'specialPagination').initializer, page, { ...bindings, specialMode: mode,
      specialCaseList: { ...bindings.specialCaseList, active: ['unclaimed', 'refund'].includes(mode) } });
    assert.ok(value.pageSizeOptions.includes(200));
    value.onChange(6, 200);
    assert.deepEqual(requests.at(-1), mode === 'execution' ? [1, 200] : [undefined, 1, 200]);
    assert.deepEqual(selected.at(-1), []);
    value.onChange(2, 20);
    assert.deepEqual(requests.at(-1), mode === 'execution' ? [2, 20] : [undefined, 2, 20]);
  }
});
test('special table isolates receipt and stage loading from unrelated feeds', () => {
  const otherTable = tableForDataSource('specialRows');
  const loading = otherTable.attributes.properties.find(attr => ts.isJsxAttribute(attr) && attr.name.getText(page) === 'loading');
  assert.ok(loading);
  const evaluate = (specialMode, sharedLoading, receiptLoading, stageLoading, invoiceLoading = false) => runExpression(loading.initializer.expression, page, { specialMode, loading: sharedLoading, specialCaseList: { active: false }, receiptList: { loading: receiptLoading }, stageStatistics: { loading: stageLoading }, invoiceBatch: { loading: invoiceLoading } });
  assert.equal(evaluate('receipt', false, true, false), true);
  assert.equal(evaluate('receipt', true, false, true), false);
  assert.equal(evaluate('receipt', true, true, true), true);
  assert.equal(evaluate('receipt', false, false, false), false);
  assert.equal(evaluate('stage', false, false, true), true);
  assert.equal(evaluate('stage', true, true, false), false);
  assert.equal(evaluate('stage', true, false, true), true);
  assert.equal(evaluate('stage', false, true, false), false);
  assert.equal(evaluate('invoice', true, true, true, false), false);
  assert.equal(evaluate('invoice', false, false, false, true), true);
  for (const mode of ['schedule', 'execution', 'unclaimed', 'refund']) {
    assert.equal(evaluate(mode, false, true, true), false);
    assert.equal(evaluate(mode, true, false, false), true);
  }
  const locale = otherTable.attributes.properties.find(attr => ts.isJsxAttribute(attr) && attr.name.getText(page) === 'locale');
  assert.equal(locale, undefined, 'ordinary-query empty/error text must not leak into other tables');
});

async function specialCaseSetup(t, route) {
  const requests = [];
  const compiled = ts.transpileModule(fs.readFileSync(new URL('../src/legal/hooks/useSpecialCaseRecords.ts', import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const loaded = { exports: {} };
  const api = { get: (url, options) => {
    assert.equal(url, '/cases/special-records');
    const pending = deferred();
    requests.push({ params: options.params, ...pending });
    return pending.promise;
  } };
  new Function('require', 'module', 'exports', compiled)(name => {
    if (name === 'react') return React;
    assert.equal(name, '../../api');
    return { api };
  }, loaded, loaded.exports);
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  let current, renderer;
  function Host({ route }) { current = loaded.exports.useSpecialCaseRecords(route); return null; }
  await act(async () => { renderer = create(React.createElement(Host, { route })); });
  t.after(async () => { await act(async () => renderer.unmount()); delete globalThis.IS_REACT_ACT_ENVIRONMENT; });
  return { requests, get current() { return current; }, changeRoute: async route => {
    await act(async () => renderer.update(React.createElement(Host, { route })));
  } };
}

test('hearing export reports busy immediately, blocks duplicate requests and releases after failure', async t => {
  const env = await specialCaseSetup(t, 'case-company-schedule');
  let search;
  await act(async () => { search = env.current.search({ customer: 'CODEX1021UI客户' }); });
  await act(async () => { env.requests[0].resolve({ data: { items: [], total: 201 } }); await search; });
  let pending;
  await act(async () => { pending = env.current.exportFile(); });
  assert.equal(env.current.exporting, true);
  await assert.rejects(env.current.exportFile(), /导出正在进行/);
  assert.equal(env.requests.length, 2);
  assert.equal(env.requests[1].params.customer, 'CODEX1021UI客户');
  assert.equal(env.requests[1].params.export_format, 'xls');
  const failure = assert.rejects(pending, /导出故障/);
  await act(async () => { env.requests[1].reject(new Error('导出故障')); await failure; });
  assert.equal(env.current.exporting, false);
  await act(async () => { pending = env.current.exportFile(); });
  const file = new Blob(['CODEX1021UI导出']);
  await act(async () => { env.requests[2].resolve({ data: file }); assert.equal((await pending).data, file); });
  assert.equal(env.current.exporting, false);
});

test('person selector hides an unsearched directory while retaining selected labels, values and role options', async t => {
  const source = ts.transpileModule(fs.readFileSync(new URL('../src/components/KeywordPersonSelect.tsx', import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  const loaded = { exports: {} };
  new Function('require', 'module', 'exports', source)(name => {
    if (name === 'react') return React;
    if (name === 'react/jsx-runtime') return { jsx: React.createElement, jsxs: React.createElement };
    if (name === 'antd') return { Select: 'PersonnelSelect' };
    assert.equal(name, './keyword-person-select.css');
    return {};
  }, loaded, loaded.exports);
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  const options = [{ value: 'CODEX1021UI-lawyer', label: '中文律师（诉讼部）' }, { value: 'CODEX1021UI-assistant', label: '中文助理（调查部）', disabled: true }];
  let renderer;
  await act(async () => { renderer = create(React.createElement(loaded.exports.KeywordPersonSelect, { options, value: ['CODEX1021UI-lawyer'], mode: 'multiple', allowClear: true })); });
  t.after(async () => { await act(async () => renderer.unmount()); delete globalThis.IS_REACT_ACT_ENVIRONMENT; });
  const control = () => renderer.root.findByType('PersonnelSelect').props;
  assert.deepEqual(control().options, []);
  assert.equal(control().labelRender({ value: 'CODEX1021UI-lawyer' }), options[0].label);
  await act(async () => control().onSearch('诉讼'));
  assert.deepEqual(control().options, options);
  assert.equal(control().filterOption('诉讼', options[0]), true);
  assert.equal(control().filterOption('CODEX1021UI-lawyer', options[0]), true);
  assert.equal(control().filterOption('诉讼', options[1]), false);
  assert.equal(control().options[1].disabled, true);
  await act(async () => control().onSelect(options[0].value, options[0]));
  assert.deepEqual(control().options, []);
  assert.deepEqual(control().value, ['CODEX1021UI-lawyer']);
  await act(async () => control().onSearch('  '));
  assert.deepEqual(control().options, []);
});

test('case table measurement reserves live header and pagination sizes when available space shrinks', async t => {
  const source = ts.transpileModule(fs.readFileSync(new URL('../src/legal/hooks/useArchiveTableScroll.ts', import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const loaded = { exports: {} };
  new Function('require', 'module', 'exports', source)(() => React, loaded, loaded.exports);
  const original = { ResizeObserver: globalThis.ResizeObserver, requestAnimationFrame: globalThis.requestAnimationFrame, cancelAnimationFrame: globalThis.cancelAnimationFrame };
  let observerCallback, frame, current, bodyHeight = 1, reserved = 96;
  const container = { clientHeight: 500, querySelector: selector => selector === '.ant-table-body'
    ? { getBoundingClientRect: () => ({ height: bodyHeight }) }
    : { getBoundingClientRect: () => ({ height: bodyHeight + reserved }) } };
  globalThis.ResizeObserver = class { constructor(callback) { observerCallback = callback; } observe() {} disconnect() {} };
  globalThis.requestAnimationFrame = callback => { frame = callback; return 1; };
  globalThis.cancelAnimationFrame = () => {};
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  function Host() { current = loaded.exports.useArchiveTableScroll(true, 'case-company-civil'); bodyHeight = current.scrollY; return React.createElement('div', { ref: current.containerRef }); }
  let renderer;
  await act(async () => { renderer = create(React.createElement(Host), { createNodeMock: () => container }); });
  t.after(async () => { await act(async () => renderer.unmount()); Object.assign(globalThis, original); delete globalThis.IS_REACT_ACT_ENVIRONMENT; });
  assert.equal(current.scrollY, 404);
  container.clientHeight = 310;
  await act(async () => { observerCallback(); frame(); });
  assert.equal(current.scrollY, 214);
  reserved = 132;
  await act(async () => { observerCallback(); frame(); });
  assert.equal(current.scrollY, 178);
  assert.equal(current.minHeight, 133);
});

test('special case query forwards filters and page size, retries exact query, ignores stale results', async t => {
  const env = await specialCaseSetup(t, 'case-company-no-refund');
  let first, second;
  const day = value => ({ format: pattern => { assert.equal(pattern, 'YYYY-MM-DD'); return value; } });
  await act(async () => { first = env.current.search({ serial_no: 'CODEX-201', refund_amount: 0,
    payment_range: [day('2026-01-01'), day('2026-01-31')] }, 1, 200); });
  assert.deepEqual(env.requests[0].params, { kind: 'refund', scope: 'company', serial_no: 'CODEX-201',
    refund_amount: 0, paid_from: '2026-01-01', paid_to: '2026-01-31', page: 1, page_size: 200 });
  await act(async () => { second = env.current.search(undefined, 2, 200); });
  await act(async () => { env.requests[1].resolve({ data: { items: [{ id: 201 }], total: 201 } }); await second; });
  await act(async () => { env.requests[0].resolve({ data: { items: [{ id: 1 }], total: 201 } }); await first; });
  assert.equal(env.current.page, 2);
  assert.deepEqual(env.current.rows, [{ id: 201 }]);
  let failed, retry;
  await act(async () => { failed = env.current.search(undefined, 1, 50); });
  await act(async () => { env.requests[2].reject({ response: { data: { detail: 'CODEX查询失败' } } }); await failed; });
  assert.equal(env.current.error, 'CODEX查询失败');
  assert.deepEqual(env.current.rows, []);
  await act(async () => { retry = env.current.reload(); });
  assert.deepEqual(env.requests[3].params, env.requests[2].params);
  await act(async () => { env.requests[3].resolve({ data: { items: [], total: 0 } }); await retry; });
  assert.equal(env.current.error, '');
  let leaving;
  await act(async () => { leaving = env.current.search({}, 1, 200); });
  await env.changeRoute('case-mine-unclaimed');
  await act(async () => { env.requests[4].resolve({ data: { items: [{ id: 99 }], total: 1 } }); await leaving; });
  assert.deepEqual(env.current.rows, []);
  let mine;
  await act(async () => { mine = env.current.reload(); });
  assert.deepEqual(env.requests[5].params, { kind: 'unclaimed', scope: 'mine', page: 1, page_size: 20 });
  await act(async () => { env.requests[5].resolve({ data: { items: [], total: 0 } }); await mine; });
});

test('special list initial load does not request a 100-row side feed or locally re-filter server rows', async () => {
  const calls = [];
  const rows = [{ id: 201, data: { commission_applied: false } }];
  const specialCaseList = { active: true, rows, reload: async () => { calls.push('special'); return true; } };
  const context = { specialCaseList, initialView: 'case-mine-unclaimed', setLoading: () => {}, setProfile: () => {},
    setSelectedCaseKeys: keys => assert.deepEqual(keys, []) };
  const load = runExpression(variable(service, 'load').initializer, service, { context,
    api: { get: async url => { calls.push(url); assert.equal(url, '/auth/me'); return { data: {} }; } }, message: { error: text => assert.fail(text) } });
  await load();
  assert.deepEqual(calls, ['/auth/me', 'special']);
  assert.equal(runExpression(variable(page, 'specialRows').initializer, page, { specialCaseList }), rows);
});

test('special query submit and reset clear selected rows and start filtered server page one', () => {
  const calls = [], selected = [];
  const bindings = { setCaseQuery: query => calls.push(['query', query]), setSelectedCaseKeys: keys => selected.push(keys),
    setCompanySchedulePage: value => calls.push(['local-page', value]), specialCaseList: { active: true, pageSize: 200,
      search: (...args) => calls.push(['search', ...args]) }, caseQueryForm: { resetFields: () => calls.push(['reset']) } };
  const bar = find(page, node => ts.isJsxOpeningElement(node) && node.tagName.getText(page) === 'ListFilterBar'
    && node.attributes.properties.some(attr => ts.isJsxAttribute(attr) && attr.name.getText(page) === 'className' && attr.initializer?.text === 'case-special-query'));
  const finish = bar.attributes.properties.find(attr => attr.name?.getText(page) === 'onFinish').initializer.expression;
  runExpression(finish, page, bindings)({ customer: 'CODEX' });
  assert.deepEqual(calls.at(-1), ['search', { customer: 'CODEX' }, 1, 200]);
  const reset = find(page, node => ts.isJsxAttribute(node) && node.name.getText(page) === 'onClick'
    && node.initializer?.expression?.getText(page).startsWith('()=>{caseQueryForm.resetFields();setCaseQuery({});'));
  runExpression(reset.initializer.expression, page, bindings)();
  assert.deepEqual(calls.at(-1), ['search', {}, 1, 200]);
  assert.deepEqual(selected, [[], []]);
});

const documentsService = parse('../src/legal/services/documentsActions.tsx');
const financeService = parse('../src/legal/services/financeActions.tsx');
const hookPath = '../src/legal/hooks/useCaseInvoiceBatch.ts';
const hookSource = ts.transpileModule(fs.readFileSync(new URL(hookPath, import.meta.url), 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
const hookModule = { exports: {} };
new Function('require', 'module', 'exports', hookSource)(name => {
  assert.equal(name, 'react');
  return React;
}, hookModule, hookModule.exports);

async function invoiceSetup(t) {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  let batch, renderer;
  function Host({ active }) { batch = hookModule.exports.useCaseInvoiceBatch(active); return null; }
  await act(async () => { renderer = create(React.createElement(Host, { active: true })); });
  t.after(async () => {
    await act(async () => renderer.unmount());
    delete globalThis.IS_REACT_ACT_ENVIRONMENT;
  });
  const requests = [], messages = [];
  let nextId = 1, readFailure, uploadFailure, importFailure, uploadWait, readWait;
  let importData = { processed: 1, matched: 1, unmatched: 0, result_attachment_ids: [1] };
  const linked = new Set(), failed = new Set();
  const api = {
    get: async (url, options) => {
      assert.equal(url, '/cases/invoice-files');
      assert.ok(options.params instanceof URLSearchParams);
      const ids = options.params.getAll('attachment_ids').map(Number);
      assert.ok(ids.length > 0 && ids.length <= 200);
      assert.equal(options.params.get('page'), '1');
      assert.equal(options.params.get('page_size'), '200');
      requests.push({ method: 'get', ids });
      const failure = typeof readFailure === 'function' ? readFailure(ids) : readFailure;
      if (failure) throw new Error(failure);
      if (readWait) return readWait.promise;
      return { data: { pages: 1, items: ids.map(id => ({ id, record_id: linked.has(id) ? 100 : null,
        original_name: 'CODEX-invoice.pdf', category: '案件发票文件', match_status: failed.has(id) ? '导入失败：未匹配' : linked.has(id) ? '已关联费用' : '待导入' })) } };
    },
    post: async (url, body) => {
      requests.push({ method: 'post', url, body });
      if (url === '/attachments') {
        if (uploadFailure) throw new Error(uploadFailure);
        if (uploadWait) return uploadWait.promise;
        return { data: { id: nextId++ } };
      }
      assert.equal(url, '/cases/invoice-files/import');
      if (importFailure) throw typeof importFailure === 'string' ? new Error(importFailure) : importFailure;
      importData.result_attachment_ids.forEach(id => { if (!failed.has(id)) linked.add(id); });
      return { data: importData };
    },
  };
  const context = { get invoiceBatch() { return batch; }, caseUploadRef: { current: { value: 'selected' } } };
  const message = Object.fromEntries(['success', 'warning', 'error'].map(kind => [kind, text => messages.push({ kind, text })]));
  const read = runExpression(variable(service, 'loadCaseInvoiceBatch').initializer, service, { context, api, message });
  context.loadCaseInvoiceBatch = read;
  const upload = runExpression(variable(documentsService, 'uploadCaseInvoiceFile').initializer, documentsService, { context, api, message });
  const startImport = runExpression(variable(financeService, 'startCaseInvoiceImport').initializer, financeService, { context, api, message });
  return { get batch() { return batch; }, requests, messages, read, startImport, linked, failed,
    upload: () => upload(new File(['CODEX'], 'CODEX.pdf', { type: 'application/pdf' })),
    setReadFailure: value => { readFailure = value; }, setUploadFailure: value => { uploadFailure = value; },
    setImportFailure: value => { importFailure = value; }, setImportData: value => { importData = value; },
    setUploadWait: value => { uploadWait = value; },
    setReadWait: value => { readWait = value; },
    activate: async active => { await act(async () => renderer.update(React.createElement(Host, { active }))); },
  };
}

test('发票工作台 idle 不查询历史，上传只采用新源 ID，旧源不混入或恢复', async t => {
  const run = await invoiceSetup(t);
  await act(async () => run.read());
  assert.deepEqual(run.requests, []);
  assert.equal(run.batch.canImport, false);
  await act(async () => run.upload());
  assert.deepEqual(run.batch.sourceAttachmentIds, [1]);
  assert.equal(run.batch.canImport, true);
  await act(async () => run.upload());
  assert.deepEqual(run.batch.sourceAttachmentIds, [2]);
  assert.deepEqual(run.batch.rows.map(row => row.id), [2]);
  assert.deepEqual(run.requests.filter(row => row.method === 'get').map(row => row.ids), [[1], [2]]);
  await run.activate(false);
  await run.activate(true);
  await act(async () => run.read());
  assert.deepEqual(run.batch.attachmentIds, []);
  assert.deepEqual(run.batch.rows, []);
  assert.equal(run.requests.length, 4);
  assert.doesNotMatch(variable(service, 'load').initializer.getText(service), /\/cases\/invoice-files|setAttachments/);
});

test('失败新上传不能展示旧成功，查询失败保留源范围且仅只读重试', async t => {
  const run = await invoiceSetup(t);
  await act(async () => run.upload());
  await act(async () => run.startImport());
  assert.equal(run.batch.rows[0].record_id, 100);
  assert.equal(run.batch.canImport, false);
  run.setUploadFailure('CODEX 上传失败');
  await act(async () => run.upload());
  assert.deepEqual(run.batch.rows, []);
  assert.deepEqual(run.batch.sourceAttachmentIds, []);
  assert.equal(run.batch.error, 'CODEX 上传失败');
  run.setUploadFailure(undefined);
  run.setReadFailure('CODEX 查询失败');
  await act(async () => run.upload());
  assert.deepEqual(run.batch.attachmentIds, [2]);
  assert.equal(run.batch.error, 'CODEX 查询失败');
  assert.equal(run.batch.canImport, false);
  const writes = run.requests.filter(row => row.method === 'post').length;
  run.setReadFailure(undefined);
  await act(async () => run.read());
  assert.equal(run.batch.canImport, true);
  assert.equal(run.requests.filter(row => row.method === 'post').length, writes);
});

test('ZIP 多费全部结果按 200 ID 分块保留，结果查询失败不清空或自动重提', async t => {
  const run = await invoiceSetup(t);
  await act(async () => run.upload());
  const ids = Array.from({ length: 451 }, (_, i) => i + 1);
  run.setImportData({ processed: 1, matched: 1, unmatched: 0, result_attachment_ids: ids });
  run.setReadFailure(ids => ids[0] === 201 ? 'CODEX 结果失败' : undefined);
  await act(async () => { const first = run.startImport(); await run.startImport(); await first; });
  assert.deepEqual(run.requests.find(row => row.url === '/cases/invoice-files/import').body, { attachment_ids: [1] });
  assert.deepEqual(run.batch.attachmentIds, ids);
  assert.equal(run.batch.resultUnconfirmed, false);
  assert.equal(run.batch.rows.length, 1);
  assert.equal(run.batch.canImport, false);
  run.setReadFailure(undefined);
  const before = run.requests.length;
  await act(async () => run.read());
  assert.deepEqual(run.requests.slice(before).map(row => row.ids.length), [200, 200, 51]);
  assert.deepEqual(run.batch.rows.map(row => row.id), ids);
  assert.ok(run.batch.rows.every(row => row.record_id === 100));
  assert.equal(run.batch.canImport, false);
  assert.equal(run.requests.filter(row => row.url === '/cases/invoice-files/import').length, 1);
});

test('批次分块查询的旧响应在离开重开后不能覆盖新上传结果', async t => {
  const run = await invoiceSetup(t);
  const pending = deferred();
  run.setReadWait(pending);
  let oldUpload;
  await act(async () => { oldUpload = run.upload(); });
  assert.deepEqual(run.batch.attachmentIds, [1]);
  await run.activate(false);
  await run.activate(true);
  run.setReadWait(undefined);
  await act(async () => run.upload());
  await act(async () => {
    pending.resolve({ data: { pages: 1, items: [{ id: 1, record_id: null }] } });
    await oldUpload;
  });
  assert.deepEqual(run.batch.sourceAttachmentIds, [2]);
  assert.deepEqual(run.batch.rows.map(row => row.id), [2]);
  assert.equal(run.batch.loading, false);
});

test('真实未匹配源保留失败状态可重试，网络失败不能自动再次导入', async t => {
  const run = await invoiceSetup(t);
  await act(async () => run.upload());
  run.failed.add(1);
  run.setImportData({ processed: 1, matched: 0, unmatched: 1, result_attachment_ids: [1] });
  await act(async () => run.startImport());
  assert.match(run.batch.rows[0].match_status, /导入失败/);
  assert.equal(run.batch.canImport, true);
  run.setImportFailure('CODEX 网络失败');
  await act(async () => run.startImport());
  assert.match(run.batch.error, /网络失败/);
  assert.equal(run.batch.rows.length, 1);
  assert.equal(run.batch.canImport, false);
  const writes = run.requests.filter(row => row.method === 'post').length;
  await act(async () => run.read());
  assert.equal(run.requests.filter(row => row.method === 'post').length, writes);
  assert.equal(run.batch.canImport, false);
  assert.equal(run.batch.resultUnconfirmed, true);
  assert.match(run.batch.error, /导入结果未确认/);
});

test('POST 已写入但回执丢失或无效，源查询成功不能冒充恢复全部 ZIP 输出', async t => {
  const run = await invoiceSetup(t);
  await act(async () => run.upload());
  run.linked.add(1);
  run.linked.add(2);
  run.setImportData({ processed: 1, matched: 1, unmatched: 0, result_attachment_ids: [] });
  await act(async () => run.startImport());
  assert.equal(run.batch.resultUnconfirmed, true);
  await act(async () => run.read());
  assert.deepEqual(run.batch.rows.map(row => row.id), [1]);
  assert.match(run.batch.error, /完整结果清单未恢复/);
  assert.equal(run.batch.canImport, false);
  await act(async () => run.startImport());
  assert.equal(run.requests.filter(row => row.url === '/cases/invoice-files/import').length, 1);
});

test('确定的 422 前置拒绝是失败，查询恢复后可由用户重新提交', async t => {
  const run = await invoiceSetup(t);
  await act(async () => run.upload());
  run.setImportFailure({ response: { status: 422, data: { detail: 'CODEX 参数不合法' } } });
  await act(async () => run.startImport());
  assert.equal(run.batch.resultUnconfirmed, false);
  assert.equal(run.batch.error, 'CODEX 参数不合法');
  await act(async () => run.read());
  assert.equal(run.batch.canImport, true);
  assert.equal(run.requests.filter(row => row.url === '/cases/invoice-files/import').length, 1);
});

for (const staleFailure of [false, true]) test(`同步锁阻止重复上传，重开后的旧上传${staleFailure ? '失败' : '成功'}不得覆盖新批次`, async t => {
  const run = await invoiceSetup(t);
  const pending = deferred();
  run.setUploadWait(pending);
  let first;
  await act(async () => { first = run.upload(); void run.upload(); });
  assert.equal(run.requests.length, 1);
  assert.equal(run.batch.loading, true);
  await run.activate(false);
  await run.activate(true);
  run.setUploadWait(undefined);
  await act(async () => run.upload());
  const messages = run.messages.length;
  await act(async () => {
    if (staleFailure) pending.reject(new Error('CODEX 旧上传失败'));
    else pending.resolve({ data: { id: 999 } });
    await first;
  });
  assert.deepEqual(run.batch.sourceAttachmentIds, [1]);
  assert.deepEqual(run.batch.rows.map(row => row.id), [1]);
  assert.equal(run.batch.loading, false);
  assert.equal(run.messages.length, messages);
});
test('archive table owns its loading and error feedback independently', () => {
  const archiveTable = tableForDataSource('originalArchiveRows');
  const attribute = name => archiveTable.attributes.properties.find(attr => ts.isJsxAttribute(attr) && attr.name.getText(page) === name).initializer.expression;
  const evaluate = (name, archiveList) => runExpression(attribute(name), page, { loading: true, ordinaryLoading: true, archiveList });
  assert.equal(evaluate('loading', { loading: false, error: '' }), false);
  assert.equal(evaluate('loading', { loading: true, error: '' }), true);
  assert.equal(evaluate('locale', { loading: true, error: '' }).emptyText, '归档案件加载中…');
  assert.equal(evaluate('locale', { loading: false, error: '归档查询失败' }).emptyText, '归档查询失败');
  assert.equal(evaluate('locale', { loading: false, error: '' }).emptyText, '暂无符合条件的案件');
});
test('early completion of side feeds cannot clear a pending ordinary search spinner', async () => {
  const run = setup();
  const search = run.ordinary();
  const sideLoad = run.load();
  run.side.resolve(result());
  await sideLoad;
  assert.deepEqual(run.messages, []);
  assert.equal(run.state.loading, false);
  assert.equal(tableValue('loading', run.state), true);
  run.requests[0].resolve(result([{ id: 9 }], 4904));
  await search;
  assert.equal(tableValue('loading', run.state), false);
  assert.equal(run.state.ordinaryTotal, 4904);
  assert.deepEqual(run.state.ordinaryCases, [{ id: 9 }]);
});
test('completed search shows records without waiting for slower unrelated feeds', async () => {
  const run = setup();
  const sideLoad = run.load(), search = run.ordinary();
  run.requests[0].resolve(result([{ id: 8 }]));
  await search;
  assert.equal(run.state.loading, true);
  assert.equal(tableValue('loading', run.state), false);
  run.side.resolve(result());
  await sideLoad;
  assert.deepEqual(run.messages, []);
});
test('current failed search persists error instead of no-data; retry clears it while pending', async () => {
  const run = setup();
  const first = run.ordinary();
  run.requests[0].reject({ response: { data: { detail: 'CODEX query failed' } } });
  await first;
  assert.equal(tableValue('loading', run.state), false);
  assert.equal(tableValue('locale', run.state).emptyText, 'CODEX query failed');
  assert.deepEqual(run.messages, ['CODEX query failed']);
  const retry = run.ordinary();
  assert.equal(run.state.ordinaryLoadError, '');
  assert.equal(tableValue('locale', run.state).emptyText, '案件加载中…');
  run.requests[1].resolve(result());
  await retry;
  assert.equal(tableValue('locale', run.state).emptyText, '暂无案件');
});
for (const staleFailure of [false, true]) test(`stale ${staleFailure ? 'failure' : 'success'} cannot clear newer loading, error or rows`, async () => {
  const run = setup();
  const first = run.ordinary(), latest = run.ordinary({ keyword: 'CODEX' });
  if (staleFailure) run.requests[0].reject(new Error('stale'));
  else run.requests[0].resolve(result([{ id: 1 }]));
  await first;
  assert.equal(run.state.ordinaryLoading, true);
  assert.equal(run.state.ordinaryLoadError, '');
  assert.deepEqual(run.state.ordinaryCases, []);
  assert.deepEqual(run.messages, []);
  run.requests[1].resolve(result([{ id: 2 }]));
  await latest;
  assert.deepEqual(run.state.ordinaryCases, [{ id: 2 }]);
  assert.equal(run.state.ordinaryLoading, false);
});
