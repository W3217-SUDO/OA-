import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import vm from 'node:vm';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const ts = require('typescript');
const sourceRoot = path.resolve(import.meta.dirname, '../src');
const element = (type, props) => ({ type, props: props || {} });
const childrenOf = (node) => Array.isArray(node) ? node.flatMap(childrenOf)
  : node && typeof node === 'object' ? [node, ...childrenOf(node.props?.children)] : [];

function loadPaymentDocument() {
  const file = path.join(sourceRoot, 'finance/PaymentDocument.tsx');
  const compiled = ts.transpileModule(fs.readFileSync(file, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const Table = () => null;
  const Button = () => null;
  const context = {
    exports: {},
    require: (name) => {
      if (name === 'antd') return { Button };
      if (name === 'react') return { Fragment: Symbol.for('react.fragment') };
      if (name === '../components/ResizableTable') return { default: Table };
      if (name === 'react/jsx-runtime') return { jsx: element, jsxs: element };
      throw new Error(`unexpected import: ${name}`);
    },
  };
  vm.runInNewContext(compiled, context, { filename: 'PaymentDocument.js' });
  return { render: context.exports.PaymentDocument, Table, Button };
}

test('普通付款明细的 8/12 列可调，案号动作与纸质打印分别保留', () => {
  const { render, Table, Button } = loadPaymentDocument();
  let openedCase = '';
  const ordinary = render({
    row: { id: 1, serial_no: 'PAY-1', status: '待审批', data: { items: [{ case_no: 'CASE-1', amount: 20, fee_type: '官费' }] } },
    printing: false,
    onCase: (no) => { openedCase = no; },
  });
  const ordinaryTable = childrenOf(ordinary).find((node) => node.type === Table);
  assert.ok(ordinaryTable, '正常付款详情应有可调列表');
  assert.equal(ordinaryTable.props.columns.length, 12);
  assert.equal(ordinaryTable.props.scroll.x, 'max-content');
  assert.equal(ordinaryTable.props.dataSource.length, 1);
  const caseButton = ordinaryTable.props.columns[4].render(null, ordinaryTable.props.dataSource[0]);
  assert.equal(caseButton.type, Button);
  caseButton.props.onClick();
  assert.equal(openedCase, 'CASE-1');

  const internal = render({
    row: { id: 2, serial_no: 'PAY-2', status: '待审批', data: { application_items: [{ id: 3, data: { payee: '收款人', amount: 50 } }] } },
    printing: false,
  });
  const internalTable = childrenOf(internal).find((node) => node.type === Table);
  assert.ok(internalTable);
  assert.equal(internalTable.props.columns.length, 8);
  assert.equal(internalTable.props.dataSource.length, 1);

  const printed = render({ row: { serial_no: 'PAY-3', data: { items: [{ case_no: 'CASE-1', amount: 20 }] } }, printing: true });
  assert.equal(childrenOf(printed).some((node) => node.type === Table), false);
  assert.equal(childrenOf(printed).some((node) => node.type === 'table' && node.props.className === 'payment-paper'), true);
});

test('用户缩窄列后横滚按列内容宽度计算，固定列和选择配置不丢失', () => {
  const file = path.join(sourceRoot, 'components/ResizableTable.tsx');
  const compiled = ts.transpileModule(fs.readFileSync(file, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const storage = new Map();
  const listeners = new Map();
  const state = [];
  let cursor = 0;
  const AntTable = Object.assign(() => null, { Column: {}, ColumnGroup: {}, Summary: {}, SELECTION_COLUMN: {}, EXPAND_COLUMN: {} });
  const hooks = {
    useEffect() {},
    useMemo: (run) => run(),
    useRef: (initial) => { const index = cursor++; return state[index] ||= { current: initial }; },
    useState: (initial) => {
      const index = cursor++;
      if (!(index in state)) state[index] = typeof initial === 'function' ? initial() : initial;
      return [state[index], (next) => { state[index] = typeof next === 'function' ? next(state[index]) : next; }];
    },
  };
  const context = {
    exports: {}, URLSearchParams,
    document: { body: { style: { cursor: '', userSelect: '' } } },
    sessionStorage: { getItem: (key) => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value) },
    window: {
      location: { search: '?page=case-counsel', pathname: '/' },
      addEventListener: (key, callback) => listeners.set(key, callback),
      removeEventListener: (key) => listeners.delete(key),
      setTimeout() {},
    },
    require: (name) => {
      if (name === 'react') return hooks;
      if (name === 'antd') return { Table: AntTable };
      if (name === 'react/jsx-runtime') return { jsx: element };
      if (name.endsWith('.css')) return {};
      throw new Error(`unexpected import: ${name}`);
    },
  };
  vm.runInNewContext(compiled, context, { filename: 'ResizableTable.js' });
  const columns = [{ key: 'name', title: '客户', width: 230 }, { key: 'actions', title: '操作', width: 150, fixed: 'right' }];
  const render = () => { cursor = 0; return context.exports.default({ columns, dataSource: [], rowSelection: { selectedRowKeys: [] }, scroll: { x: 420 } }); };
  const first = render();
  assert.equal(first.props.scroll.x, 420);
  const header = first.props.columns[0].onHeaderCell(columns[0]);
  header.onPointerDown({
    pointerType: 'mouse', button: 0, clientX: 228, defaultPrevented: false,
    currentTarget: { getBoundingClientRect: () => ({ right: 230, width: 230 }) },
    preventDefault() {}, stopPropagation() {},
  });
  listeners.get('pointermove')({ clientX: 78 });
  listeners.get('pointerup')();
  const resized = render();
  assert.equal(resized.props.columns[0].width, 80);
  assert.equal(resized.props.columns[1].fixed, 'right');
  assert.equal(resized.props.rowSelection.selectedRowKeys.length, 0);
  assert.equal(resized.props.scroll.x, 'max-content');
  const css = fs.readFileSync(path.join(sourceRoot, 'components/resizable-table.css'), 'utf8');
  const installedCellSource = fs.readFileSync(require.resolve('@rc-component/table/lib/Cell'), 'utf8');
  assert.ok(installedCellSource.includes('[`${cellPrefixCls}-fix`]: isFixStart || isFixEnd'), '固定列表头必须实际生成 ant-table-cell-fix 类');
  assert.match(css, /\.oa-resizable-header\.ant-table-cell-fix\s*\{\s*position:\s*sticky/s);
});
