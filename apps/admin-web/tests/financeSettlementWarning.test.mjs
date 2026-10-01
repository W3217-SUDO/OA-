import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';

const page = ts.createSourceFile('FinanceCenterPage.tsx', fs.readFileSync(new URL('../src/finance/FinanceCenterPage.tsx', import.meta.url), 'utf8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
const workspace = ts.createSourceFile('useSettlementWorkspaceState.ts', fs.readFileSync(new URL('../src/finance/hooks/useSettlementWorkspaceState.ts', import.meta.url), 'utf8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
const view = ts.createSourceFile('SettlementBatchModal.tsx', fs.readFileSync(new URL('../src/finance/SettlementBatchModal.tsx', import.meta.url), 'utf8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
function find(root, predicate) {
  if (predicate(root)) return root;
  return ts.forEachChild(root, child => find(child, predicate));
}
function compile(expression) {
  return ts.transpileModule(`const result = ${expression};`, { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText + '\nreturn result;';
}
const select = find(page, node => ts.isVariableDeclaration(node) && node.name.getText(page) === 'selectedSettlementCases');
const open = find(page, node => ts.isVariableDeclaration(node) && node.name.getText(page) === 'openSelectedSettlementBatch');
const openWorkspace = find(workspace, node => ts.isVariableDeclaration(node) && node.name.getText(workspace) === 'openSettlementBatch');
const selectedCaseCount = find(page, node => ts.isPropertyAssignment(node) && node.name.getText(page) === 'selectedCaseCount');
const title = find(view, node => ts.isJsxAttribute(node) && node.name.getText(view) === 'title' && node.initializer?.getText(view).includes('将修改已选费用关联的'));
assert.ok(select && open && openWorkspace && selectedCaseCount && title, 'test targets must be actual page and workspace functions and rendered title');
function setup(rows = [], cases = [], invoice = false) {
  const warnings = [], calls = [];
  const selectedSettlementCases = new Function('selectedSettlementRows', 'cases', 'isInvoiceUnissuedRoute', 'message', compile(select.initializer.getText(page)))(rows, cases, invoice, { warning: text => warnings.push(text) });
  const openWorkspaceBatch = new Function('settlementBatchForm', 'setSettlementBatchOpen', compile(openWorkspace.initializer.getText(workspace)))({ resetFields: () => calls.push('reset') }, state => calls.push(['open', state]));
  const openSettlementBatch = new Function('selectedSettlementCases', 'openSettlementBatch', compile(open.initializer.getText(page)))(selectedSettlementCases, openWorkspaceBatch);
  const countForModal = new Function('selectedSettlementCases', compile(selectedCaseCount.initializer.getText(page)));
  const renderTitle = new Function('selectedCaseCount', compile(title.initializer.expression.getText(view)));
  return { warnings, calls, selectedSettlementCases, openSettlementBatch, render: () => renderTitle(countForModal(selectedSettlementCases)) };
}
test('repeated render of empty selection never emits messages; real click emits once and stops', () => {
  const state = setup();
  for (let index = 0; index < 20; index++) assert.match(state.render(), /0 个案件/);
  assert.deepEqual(state.warnings, []);
  state.openSettlementBatch();
  assert.deepEqual(state.warnings, ['请先选择案件费用']);
  assert.deepEqual(state.calls, []);
});
test('valid selected fees render deduplicated count and click opens batch dialog', () => {
  const state = setup([{ data: { case_id: 1 } }, { data: { case_no: 'CODEX-WARN-A' } }], [{ id: 1, serial_no: 'CODEX-WARN-A' }]);
  assert.match(state.render(), /1 个案件/);
  state.openSettlementBatch();
  assert.deepEqual(state.warnings, []);
  assert.deepEqual(state.calls, ['reset', ['open', true]]);
  assert.deepEqual(state.selectedSettlementCases().map(row => row.id), [1]);
});
test('unlinked selected fees are silent in render but warn once on user action', () => {
  const state = setup([{ data: { case_id: 7 } }]);
  for (let index = 0; index < 20; index++) state.render();
  assert.deepEqual(state.warnings, []);
  state.openSettlementBatch();
  assert.deepEqual(state.warnings, ['部分费用未关联可操作的案件']);
  assert.deepEqual(state.calls, []);
});
test('invoice-specific click validation remains intact', () => {
  const state = setup([], [], true);
  state.render();
  state.openSettlementBatch();
  assert.deepEqual(state.warnings, ['请选择案件.']);
});
