import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { createRequire } from 'node:module';
import vm from 'node:vm';

const root = path.resolve(import.meta.dirname, '../src');
const require = createRequire(import.meta.url);
const ts = require('typescript');

function loadTable(storage) {
  const source = fs.readFileSync(path.join(root, 'components/ResizableTable.tsx'), 'utf8');
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const state = [];
  const listeners = new Map();
  const delayed = [];
  let cursor = 0;
  const hooks = {
    useEffect() {},
    useMemo: (callback) => callback(),
    useRef: (value) => {
      const index = cursor++;
      if (!state[index]) state[index] = { current: value };
      return state[index];
    },
    useState: (initial) => {
      const index = cursor++;
      if (!(index in state)) state[index] = typeof initial === 'function' ? initial() : initial;
      return [state[index], (next) => { state[index] = typeof next === 'function' ? next(state[index]) : next; }];
    },
  };
  const AntTable = Object.assign(() => null, {
    Column: {}, ColumnGroup: {}, Summary: {}, SELECTION_COLUMN: {}, EXPAND_COLUMN: {},
  });
  const context = {
    exports: {},
    URLSearchParams,
    document: { body: { style: { cursor: '', userSelect: '' } } },
    sessionStorage: {
      getItem: (key) => storage.get(key) ?? null,
      setItem: (key, value) => storage.set(key, value),
    },
    window: {
      location: { search: '?page=case-mine', pathname: '/' },
      addEventListener: (event, callback) => listeners.set(event, callback),
      removeEventListener: (event) => listeners.delete(event),
      setTimeout: (callback) => delayed.push(callback),
    },
    require: (name) => {
      if (name === 'react') return hooks;
      if (name === 'antd') return { Table: AntTable };
      if (name === 'react/jsx-runtime') return { jsx: (type, props) => ({ type, props }) };
      if (name.endsWith('.css')) return {};
      throw Error(`Unexpected import: ${name}`);
    },
  };
  vm.runInNewContext(compiled, context, { filename: 'ResizableTable.js' });
  return {
    render: (props) => { cursor = 0; return context.exports.default(props); },
    fire: (event, data) => listeners.get(event)?.(data),
    delayed,
    style: context.document.body.style,
  };
}

test('拖拽列边只修改该列并保留原表格属性，刷新后宽度仍生效', () => {
  const storage = new Map();
  const table = loadTable(storage);
  const columns = [
    { key: 'name', title: '名称', width: 120, sorter: true },
    { key: 'status', title: '状态', width: 90 },
  ];
  const first = table.render({ columns, rowKey: 'id', dataSource: [], scroll: { x: 600 } });
  assert.equal(first.props.scroll.x, 600);
  assert.equal(first.props.columns[0].sorter, true);
  const events = first.props.columns[0].onHeaderCell(columns[0]);
  let suppressed = false;
  events.onPointerDown({
    pointerType: 'mouse', button: 0, clientX: 118,
    currentTarget: { getBoundingClientRect: () => ({ right: 120, width: 120 }) },
    preventDefault() {}, stopPropagation() {}, defaultPrevented: false,
  });
  table.fire('pointermove', { clientX: 68 });
  assert.equal(table.style.cursor, 'col-resize');
  table.fire('pointerup');
  events.onClickCapture({ preventDefault() { suppressed = true; }, stopPropagation() {} });
  assert.equal(suppressed, true);
  assert.equal(table.style.cursor, '');
  const resized = table.render({ columns, rowKey: 'id', dataSource: [], scroll: { x: 600 } });
  assert.equal(resized.props.columns[0].width, 70);
  assert.equal(resized.props.columns[0].ellipsis, true);
  assert.equal(resized.props.columns[1].width, 90);
  const refreshed = loadTable(storage).render({ columns, rowKey: 'id', dataSource: [] });
  assert.equal(refreshed.props.columns[0].width, 70);
});

test('分组表头保留固定列、筛选及原有表头事件，列宽不低于最小值', () => {
  const table = loadTable(new Map());
  let originalPointerDown = 0;
  const columns = [{
    key: 'group', title: '分组', children: [
      { key: 'name', title: '名称', width: 100, filters: [{ text: '甲', value: 'a' }], onHeaderCell: () => ({ onPointerDown: () => { originalPointerDown += 1; } }) },
      { key: 'action', title: '操作', width: 80, fixed: 'right' },
    ],
  }];
  const first = table.render({ columns, dataSource: [], scroll: { x: 500 }, rowSelection: { selectedRowKeys: [] } });
  assert.equal(first.props.rowSelection.selectedRowKeys.length, 0);
  const events = first.props.columns[0].children[0].onHeaderCell(columns[0].children[0]);
  events.onPointerDown({
    pointerType: 'mouse', button: 0, clientX: 99,
    currentTarget: { getBoundingClientRect: () => ({ right: 100, width: 100 }) },
    preventDefault() {}, stopPropagation() {}, defaultPrevented: false,
  });
  table.fire('pointermove', { clientX: -100 });
  table.fire('pointerup');
  const resized = table.render({ columns, dataSource: [], scroll: { x: 500 } });
  assert.equal(originalPointerDown, 1);
  assert.equal(resized.props.columns[0].children[0].width, 48);
  assert.equal(resized.props.columns[0].children[0].filters[0].value, 'a');
  assert.equal(resized.props.columns[0].children[1].fixed, 'right');
});

test('现有 AntD 列表统一使用列宽组件', () => {
  const resizeStyle = fs.readFileSync(path.join(root, 'components/resizable-table.css'), 'utf8');
  assert.match(resizeStyle, /\.oa-resizable-table \.ant-table-content\s*\{[^}]*overflow-x:\s*auto/s);
  const pending = [root];
  let files = 0;
  while (pending.length) {
    for (const entry of fs.readdirSync(pending.pop(), { withFileTypes: true })) {
      const file = path.join(entry.parentPath, entry.name);
      if (entry.isDirectory()) { pending.push(file); continue; }
      if (!file.endsWith('.tsx') || file.endsWith('ResizableTable.tsx')) continue;
      const source = fs.readFileSync(file, 'utf8');
      const ast = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
      const tableImports = ast.statements.filter((node) => ts.isImportDeclaration(node)
        && node.moduleSpecifier.text === 'antd'
        && node.importClause?.namedBindings
        && ts.isNamedImports(node.importClause.namedBindings)
        && node.importClause.namedBindings.elements.some((item) => (item.propertyName?.text || item.name.text) === 'Table'));
      assert.equal(tableImports.length, 0, `${file} still imports AntD Table directly`);
      if (source.includes('<Table')) {
        assert.match(source, /import Table from ["'](?:\.{1,2}\/)+components\/ResizableTable["']|import Table from ["'](?:\.{1,2}\/)+ResizableTable["']/);
        files += 1;
      }
    }
  }
  assert.ok(files >= 90, `Only ${files} table consumers found`);
});
