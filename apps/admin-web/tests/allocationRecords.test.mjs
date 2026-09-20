import test from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { create, act } from 'react-test-renderer';
import { build } from 'esbuild';
import Module, { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

test('分配记录整页查询、按选中项取消及错误提示', async () => {
  const calls = [];
  const original = { payment: { receipt_no: 'test', amount: 100, allocated_amount: 100, remaining_amount: 0 }, revision: 'v1', can_cancel: true, items: [
    { index: 0, case_no: 'A', contract_no: 'C', fee_type: '一审诉讼费', case_stage: '新案待分配', amount: 30 },
    { index: 1, case_no: 'B', contract_no: 'D', fee_type: '律师代理费', case_stage: '已立案', amount: 70 },
  ] };
  let failure = false;
  globalThis.__allocationApi = {
    get: async () => ({ data: original }),
    post: async (path, body) => {
      calls.push({ path, body });
      if (failure) throw { response: { data: { detail: '已有有效结算' } } };
      return { data: { ...original, revision: 'v2', items: [original.items[1]], payment: { ...original.payment, allocated_amount: 70, remaining_amount: 30 } } };
    },
  };
  const result = await build({ entryPoints: [fileURLToPath(new URL('../src/finance/IncomingAllocationRecordsPage.tsx', import.meta.url))], bundle: true, write: false, platform: 'node', format: 'cjs', packages: 'external', plugins: [{ name: 'isolated-ui', setup(builder) {
    builder.onResolve({ filter: /\/api$/ }, () => ({ path: 'api', namespace: 'test' }));
    builder.onResolve({ filter: /^antd$/ }, () => ({ path: 'antd', namespace: 'test' }));
    builder.onLoad({ filter: /.*/, namespace: 'test' }, ({ path }) => ({ contents: path === 'api' ? 'export const api=globalThis.__allocationApi;' : 'export const Alert="Alert",Button="Button",Card="Card",Descriptions="Descriptions",Input="Input",InputNumber="InputNumber",Select="Select",Space="Space",Table="Table";export const message={success(){}};' }));
  } }] });
  const target = new Module(fileURLToPath(import.meta.url));
  target.paths = Module._nodeModulePaths(fileURLToPath(new URL('.', import.meta.url)));
  target.require = createRequire(import.meta.url);
  target._compile(result.outputFiles[0].text, fileURLToPath(import.meta.url));
  delete globalThis.__allocationApi;
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  let rendered;
  try {
    await act(async () => { rendered = create(React.createElement(target.exports.IncomingAllocationRecordsPage, { paymentId: 1, onChange: async () => {}, onClose() {}, onCase() {}, onContract() {} })); });
    const table = () => rendered.root.findByType('Table');
    const button = name => rendered.root.findAllByType('Button').find(node => node.props.children === name);
    assert.equal(rendered.root.findAllByType('Card').length, 1);
    assert.equal(table().props.dataSource.length, 2);
    await act(async () => rendered.root.findByType('Input').props.onChange({ target: { value: 'A' } }));
    await act(async () => button('查询').props.onClick());
    assert.deepEqual(table().props.dataSource.map(row => row.index), [0]);
    await act(async () => table().props.rowSelection.onChange([0]));
    await act(async () => rendered.root.findAllByType('Button').find(node => node.props.danger).props.onClick());
    assert.deepEqual(calls[0].body, { revision: 'v1', indexes: [0] });
    await act(async () => button('清空').props.onClick());
    assert.deepEqual(table().props.dataSource.map(row => row.index), [1]);
    assert.deepEqual(table().props.rowSelection.selectedRowKeys, []);
    failure = true;
    await act(async () => table().props.rowSelection.onChange([1]));
    await act(async () => rendered.root.findAllByType('Button').find(node => node.props.danger).props.onClick());
    assert.equal(rendered.root.findByType('Alert').props.title, '已有有效结算');
    assert.equal(table().props.dataSource.length, 1);
  } finally {
    if (rendered) await act(async () => rendered.unmount());
    delete globalThis.IS_REACT_ACT_ENVIRONMENT;
  }
});
