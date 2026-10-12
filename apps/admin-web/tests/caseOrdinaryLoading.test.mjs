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
  const js = ts.transpileModule(`const result = ${node.getText(root)};`, { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText;
  return new Function(...Object.keys(bindings), js + '\nreturn result;')(...Object.values(bindings));
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
test('special table isolates receipt and stage loading from unrelated feeds', () => {
  const otherTable = tableForDataSource('specialRows');
  const loading = otherTable.attributes.properties.find(attr => ts.isJsxAttribute(attr) && attr.name.getText(page) === 'loading');
  assert.ok(loading);
  const evaluate = (specialMode, sharedLoading, receiptLoading, stageLoading, invoiceLoading = false) => runExpression(loading.initializer.expression, page, { specialMode, loading: sharedLoading, receiptList: { loading: receiptLoading }, stageStatistics: { loading: stageLoading }, invoiceBatch: { loading: invoiceLoading } });
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
