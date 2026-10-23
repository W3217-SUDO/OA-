// 10.22 第7行：需要填写人员的地方，未输入关键词时不列出人员候选。
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

async function load(path, api = {}) {
  const output = await build({ entryPoints: [fileURLToPath(new URL(path, import.meta.url))], bundle: true, write: false, platform: 'node', format: 'cjs', packages: 'external', loader: { '.css': 'empty' }, plugins: [{
    name: 'isolated-1022-row7', setup(builder) {
      builder.onResolve({ filter: /\/api$/ }, () => ({ path: 'api', namespace: 'row7' }));
      builder.onResolve({ filter: /^antd$/ }, () => ({ path: 'antd', namespace: 'row7' }));
      builder.onLoad({ filter: /.*/, namespace: 'row7' }, ({ path }) => ({ resolveDir: fileURLToPath(new URL('.', import.meta.url)), contents: path === 'api'
        ? 'export const api=globalThis.__row7Api;'
        : 'import React from "react"; const Item=props=>React.createElement("form-item",props); export const Form=Object.assign(props=>React.createElement("form",props),{Item}); export const message={success(){},error(){}}; export const Button="button"; export const Modal="modal"; export const Select="select"; export const Input=Object.assign(props=>React.createElement("input",props),{TextArea:"textarea"}); export const Alert="alert"; export const Spin="spin";' }));
    },
  }] });
  const target = new Module(fileURLToPath(import.meta.url));
  target.paths = Module._nodeModulePaths(fileURLToPath(new URL('.', import.meta.url)));
  target.require = createRequire(import.meta.url);
  globalThis.__row7Api = api;
  try { target._compile(output.outputFiles[0].text, fileURLToPath(import.meta.url)); return target.exports; }
  finally { delete globalThis.__row7Api; }
}

async function assertHiddenUntilKeyword(control, expectedOptions, keyword) {
  assert.deepEqual(control().options, [], '未输入关键词时不应列出人员');
  assert.equal(control().notFoundContent, '请输入姓名、账号或部门关键词');
  await act(async () => control().onSearch('   '));
  assert.deepEqual(control().options, [], '空格关键词也不应列出人员');
  await act(async () => control().onSearch(keyword));
  assert.deepEqual(control().options, expectedOptions);
  await act(async () => control().onOpenChange(false));
  assert.deepEqual(control().options, []);
}

test('线索转审目标审核人：未输入关键词不列出审核人，已选审核人名称仍可回显', async () => {
  const { default: TurnOnAuditModal } = await load('../src/investigation/TurnOnAuditModal.tsx');
  const reviewers = [{ value: 'CODEX-1022-7-reviewer', label: '审核人甲（调查部）' }];
  let renderer;
  await act(async () => { renderer = create(React.createElement(TurnOnAuditModal, { open: true, turnOnAuditTarget: { serial_no: 'CODEX-1022-7-线索' }, turnOnAuditForm: {}, reviewerCandidatesLoading: false, reviewerCandidates: reviewers, onOk() {}, onCancel() {} })); });
  const control = () => renderer.root.findByType('select').props;
  assert.equal(control().labelRender({ value: 'CODEX-1022-7-reviewer' }), '审核人甲（调查部）');
  await assertHiddenUntilKeyword(control, reviewers, '审核');
  await act(async () => control().onSearch('不存在'));
  assert.equal(control().notFoundContent, '没有可用审核人');
  await act(async () => renderer.unmount());
});

test('调查任务分配人员配置：未输入关键词不列出人员，已配置人员仍显示且可清除', async () => {
  const { default: Setting } = await load('../src/InvestigationSupervisorSetting.tsx', {
    get: async () => ({ data: { items: [{ key: 'investigation_assignment', value: { supervisor_username: 'CODEX-1022-7-supervisor' } }], investigation_supervisor_options: [{ username: 'CODEX-1022-7-supervisor', display_name: '调查主管' }] } }),
  });
  let renderer;
  await act(async () => { renderer = create(React.createElement(Setting)); });
  await act(async () => { renderer.root.findByType('button').props.onClick(); });
  const control = () => renderer.root.findByType('select').props;
  assert.equal(control().value, 'CODEX-1022-7-supervisor');
  assert.equal(control().allowClear, true);
  assert.equal(control().labelRender({ value: 'CODEX-1022-7-supervisor' }), '调查主管（CODEX-1022-7-supervisor）');
  await assertHiddenUntilKeyword(control, [{ value: 'CODEX-1022-7-supervisor', label: '调查主管（CODEX-1022-7-supervisor）' }], '主管');
  await act(async () => renderer.unmount());
});

function personFieldTags(path) {
  const file = ts.createSourceFile(path, read(path), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const result = {};
  const visit = node => {
    if (ts.isJsxElement(node)) {
      const opening = node.openingElement;
      const label = opening.attributes.properties.find(attr => ts.isJsxAttribute(attr) && attr.name.getText(file) === 'label');
      const text = label?.initializer && ts.isStringLiteral(label.initializer) ? label.initializer.text : '';
      if (opening.tagName.getText(file) === 'Form.Item' && ['客户来源', '客户管理人', '客户联系人账号'].includes(text)) {
        const child = node.children.find(item => ts.isJsxElement(item) || ts.isJsxSelfClosingElement(item));
        result[text] = (ts.isJsxElement(child) ? child.openingElement : child).tagName.getText(file);
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(file);
  return result;
}

test('新建客户页与客户新增/编辑弹窗的三个人员字段都改为输入关键词后才列出', () => {
  for (const path of ['../src/crm/CustomerCreatePage.tsx', '../src/crm/CustomerCreateEditModal.tsx']) {
    assert.deepEqual(personFieldTags(path), { 客户来源: 'KeywordPersonSelect', 客户管理人: 'KeywordPersonSelect', 客户联系人账号: 'KeywordPersonSelect' }, path);
  }
});

test('全前端不再用原生下拉直接挂人员目录候选', () => {
  const root = new URL('../src/', import.meta.url);
  const offenders = [];
  const walk = dir => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = new URL(entry.name + (entry.isDirectory() ? '/' : ''), dir);
      if (entry.isDirectory()) walk(full);
      else if (entry.name.endsWith('.tsx')) {
        const text = fs.readFileSync(full, 'utf8');
        for (const match of text.matchAll(/<Select\b[^>]*options=\{(directoryOptions|customerContactOptions|reviewerCandidates)\}/g)) offenders.push(`${fileURLToPath(full)}: ${match[1]}`);
      }
    }
  };
  walk(root);
  assert.deepEqual(offenders, []);
});
