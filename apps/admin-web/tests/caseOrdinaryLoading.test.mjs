import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';
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
for (const source of ['specialRows', 'originalArchiveRows']) test(`${source} table preserves its independent shared-loader behavior`, () => {
  const otherTable = tableForDataSource(source);
  const loading = otherTable.attributes.properties.find(attr => ts.isJsxAttribute(attr) && attr.name.getText(page) === 'loading');
  assert.ok(loading);
  assert.equal(runExpression(loading.initializer.expression, page, { loading: false, ordinaryLoading: true, counselListMode: false }), false);
  assert.equal(runExpression(loading.initializer.expression, page, { loading: true, ordinaryLoading: false, counselListMode: false }), true);
  const locale = otherTable.attributes.properties.find(attr => ts.isJsxAttribute(attr) && attr.name.getText(page) === 'locale');
  assert.equal(locale, undefined, 'ordinary-query empty/error text must not leak into other tables');
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
