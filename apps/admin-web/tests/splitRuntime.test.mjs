import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { build } from 'esbuild';

// Bundle actual extracted modules together so all operations share the same API mock.
fs.mkdirSync('.split-evidence', { recursive: true });
const output = path.resolve('.split-evidence/runtime-services.mjs');
await build({ stdin: { contents: `export { api } from './src/api'; export { message } from 'antd'; export { createFinancePaymentsActions } from './src/finance/services/paymentsActions'; export { createCaseQueriesActions } from './src/legal/services/queriesActions'; export { createContractDocumentsActions } from './src/contract/services/documentsActions'; export { CaseEventsPanel } from './src/legal/CaseDetail/CaseEventsPanel'; export { IncomingAllocationModal } from './src/finance/IncomingAllocationModal';`, resolveDir: process.cwd(), loader: 'ts' }, outfile: output, bundle: true, platform: 'node', format: 'esm', packages: 'external', logLevel: 'silent' });
const { api, message, createFinancePaymentsActions, createCaseQueriesActions, createContractDocumentsActions, CaseEventsPanel, IncomingAllocationModal } = await import(pathToFileURL(output).href);
const original = { get: api.get, post: api.post, success: message.success, error: message.error, warning: message.warning };
const feedback = [];
for (const key of ['success', 'error', 'warning']) message[key] = (text) => feedback.push([key, text]);
test.after(() => { Object.assign(api, { get: original.get, post: original.post }); for (const key of ['success', 'error', 'warning']) message[key] = original[key]; fs.unlinkSync(output); });

test('finance query reads default pagination at invocation and applies response metadata', async () => {
  let pageSize = 15; const calls = [], rows = [], meta = [];
  const actions = createFinancePaymentsActions({ get feeQueryMeta() { return { pageSize }; }, isRefundCaseFeeRoute: false, feeQueryParams: (query, page, size) => ({ ...query, page, page_size: size }), setFeeQueryRows: value => rows.push(value), setFeeQueryMeta: value => meta.push(value) });
  api.get = async (url, options) => { calls.push([url, options.params]); return { data: { items: [{ id: 7 }], total: 1 } }; };
  pageSize = 30;
  await actions.loadFeeQuery({ customer: 'CODEX-SPLIT' }, 2);
  assert.deepEqual(calls, [['/finance/fees/query', { customer: 'CODEX-SPLIT', page: 2, page_size: 30 }]]);
  assert.deepEqual(rows, [[{ id: 7 }]]);
  assert.deepEqual(meta, [{ total: 1, page: 2, pageSize: 30, totals: {} }]);
  api.get = async () => { throw new Error('request rejected'); };
  await assert.rejects(actions.loadFeeQuery({}), /request rejected/);
  assert.equal(rows.length, 1);
});

test('case clue request guard ignores stale responses and clears loading only for latest request', async () => {
  const pending = [], loading = [], applied = [], requestRef = { current: 0 };
  api.get = (url, options) => new Promise(resolve => pending.push({ url, options, resolve }));
  const actions = createCaseQueriesActions({ counselDetailCluePage: 3, counselDetailCluePageSize: 15, counselDetailClueKeyword: 'CODEX-SPLIT', counselDetailClueRequestRef: requestRef, setCounselDetailClueLoading: value => loading.push(value), viewingCounselCase: { id: 4 }, applyCounselDetailCluePageState: (data, page, size) => { applied.push([data, page, size]); return data; } });
  const first = actions.loadCounselDetailCluesPage({ id: 4 });
  const second = actions.loadCounselDetailCluesPage({ id: 4 }, 2, 30, 'new');
  pending[0].resolve({ data: { marker: 'stale' } });
  assert.equal(await first, null);
  assert.deepEqual(loading, [true, true]);
  pending[1].resolve({ data: { marker: 'latest' } });
  await second;
  assert.deepEqual(applied, [[{ marker: 'latest' }, 2, 30]]);
  assert.deepEqual(loading, [true, true, false]);
});

test('contract upload keeps rejected file and skips refresh, then clears only after success', async () => {
  const file = new File(['test'], 'CODEX-SPLIT.pdf', { type: 'application/pdf' });
  const sequence = [], context = { viewing: { id: 9, status: '草稿' }, contractFile: file, setContractFile: value => sequence.push(['file', value]), openViewing: async row => sequence.push(['refresh', row.id]) };
  const actions = createContractDocumentsActions(context);
  api.post = async () => { throw new Error('upload rejected'); };
  await actions.uploadViewingAttachment();
  assert.deepEqual(sequence, []);
  assert.equal(feedback.at(-1)[0], 'error');
  api.post = async (url, data) => { assert.equal(url, '/attachments'); assert.equal(data.get('record_id'), '9'); assert.equal(data.get('file').name, file.name); return { data: { id: 8 } }; };
  await actions.uploadViewingAttachment();
  assert.deepEqual(sequence, [['file', null], ['refresh', 9]]);
  assert.equal(feedback.at(-1)[0], 'success');
});


function findElement(node, predicate) {
  if (!node || typeof node !== 'object') return;
  if (Array.isArray(node)) return node.map(item => findElement(item, predicate)).find(Boolean);
  if (predicate(node)) return node;
  return findElement(node.props?.children, predicate) || findElement(node.props?.action, predicate);
}

test('case event retry passes no click event and creator uses the established person formatter', () => {
  const calls = [];
  const view = CaseEventsPanel({ events: [], selectedKeys: [], capabilities: {}, submitting: false, error: 'retry', onRefresh: (...args) => calls.push(args), casePersonDisplayName: (source, display) => display + ':' + source });
  const retry = findElement(view, element => element.props?.children === '重试');
  retry.props.onClick({ type: 'click' });
  assert.deepEqual(calls, [[]]);
  const table = findElement(view, element => Array.isArray(element.props?.columns));
  assert.equal(table.props.columns.find(column => column.title === '创建人').render(null, { creator: 'user', creator_display_name: 'Display' }), 'Display:user');
});

test('allocation selection retains functional updates and normalizes table keys', () => {
  let keys = ['initial'];
  const view = IncomingAllocationModal({ allocateTarget: null, allocationCandidates: [], filteredAllocationCandidates: [], selectedAllocationKeys: ['initial'], allocationAmounts: {}, onSelectedKeysChange: next => { keys = typeof next === 'function' ? next(keys) : next; }, onAmountChange: () => {} });
  const table = findElement(view, element => Array.isArray(element.props?.columns));
  const amountColumn = table.props.columns.find(column => column.key === 'allocation_amount');
  amountColumn.render(null, { key: 'a', remaining_amount: 10 }).props.onChange(2);
  amountColumn.render(null, { key: 'b', remaining_amount: 10 }).props.onChange(3);
  assert.deepEqual(keys, ['initial', 'a', 'b']);
  table.props.rowSelection.onChange([1, 'b']);
  assert.deepEqual(keys, ['1', 'b']);
});
