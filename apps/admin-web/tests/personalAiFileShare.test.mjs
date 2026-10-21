import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';
import * as React from 'react';
import { act, create } from 'react-test-renderer';
import * as XLSX from 'xlsx';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const source = fs.readFileSync(new URL('../src/personal-agent/PersonalAiFileShare.tsx', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source.replace(/^import .*;\r?\n/gm, ''), {
  compilerOptions: { target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.React, module: ts.ModuleKind.CommonJS },
}).outputText;

async function setup(t, { unsupported = false, failure, rejectShare, canShare = true, markdown = false } = {}) {
  const requests = [], shares = [];
  const file = { id: 'CODEX1021FILES', name: '中文费用.xls', status: 'available', download_url: '/controlled', content_type: 'application/vnd.ms-excel' };
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet([['名称', '金额'], ['CODEX1021FILES', 307]]), '费用');
  const bytes = XLSX.write(workbook, { type: 'buffer', bookType: 'biff8' });
  if (markdown) Object.assign(file, { name: 'IDENTITY.md', content_type: 'text/markdown', source_kind: 'personal_identity' });
  const blob = new Blob([markdown ? '# CODEX1021FILES\n中文身份文件\n' : bytes], { type: file.content_type });
  const navigator = unsupported ? {} : { canShare: () => canShare, share: value => { shares.push(value); return rejectShare ? Promise.reject(rejectShare) : Promise.resolve(); } };
  const api = { get: async url => { requests.push(url); if (failure) throw failure; return { data: url.endsWith('/download') ? blob : file }; } };
  const exports = {};
  const Modal = props => React.createElement('Modal', props, props.children, props.footer);
  const Component = new Function('exports', 'React', 'useEffect', 'useRef', 'useState', 'Alert', 'Button', 'Modal', 'Spin', 'ShareAltOutlined', 'api', 'navigator', 'errorText', compiled + '\nreturn exports.PersonalAiFileShare;')(
    exports, React, React.useEffect, React.useRef, React.useState, 'Alert', 'Button', Modal, 'Spin', 'Icon', api, navigator, error => error.message,
  );
  let renderer;
  await act(async () => { renderer = create(React.createElement(Component, { file })); });
  t.after(async () => { await act(async () => renderer.unmount()); });
  const button = label => renderer.root.findAllByType('Button').find(node => node.props.children === label);
  const click = async label => { await act(async () => { await button(label).props.onClick(); }); };
  const errors = () => renderer.root.findAllByType('Alert').map(node => node.props.description);
  return { renderer, button, click, errors, requests, shares, bytes };
}

test('controlled XLS bytes are prepared before a separate user click opens file sharing', async t => {
  const view = await setup(t);
  await view.click('分享文件');
  assert.deepEqual(view.requests, ['/personal-agent/ai-space/files/CODEX1021FILES', '/personal-agent/ai-space/files/CODEX1021FILES/download']);
  assert.equal(view.shares.length, 0);
  assert.equal(view.button('打开系统分享面板').props.disabled, false);
  await view.click('打开系统分享面板');
  assert.equal(view.shares.length, 1);
  assert.deepEqual(Object.keys(view.shares[0]), ['files']);
  const shared = view.shares[0].files[0];
  assert.equal(shared.name, '中文费用.xls');
  const workbook = XLSX.read(await shared.arrayBuffer(), { type: 'array' });
  assert.deepEqual(XLSX.utils.sheet_to_json(workbook.Sheets['费用'], { header: 1 })[1], ['CODEX1021FILES', 307]);
});

test('unsupported browser explains download route and never requests private file bytes', async t => {
  const view = await setup(t, { unsupported: true });
  await view.click('分享文件');
  assert.equal(view.requests.length, 0);
  assert.match(view.errors()[0], /不支持文件分享.*下载/);
  assert.equal(view.button('打开系统分享面板').props.disabled, true);
});

test('Markdown identity bytes are unchanged and never shared without an explicit second click', async t => {
  const view = await setup(t, { markdown: true });
  assert.equal(view.requests.length, 0);
  await view.click('分享文件');
  assert.equal(view.shares.length, 0);
  assert.ok(view.renderer.root.findAllByType('Alert').some(node => node.props.title.includes('个人身份文件')));
  await view.click('打开系统分享面板');
  assert.equal(view.shares[0].files[0].name, 'IDENTITY.md');
  assert.equal(await view.shares[0].files[0].text(), '# CODEX1021FILES\n中文身份文件\n');
});

test('authorization failures are visible and cannot share bytes', async t => {
  const view = await setup(t, { failure: new Error('403 无权访问文件') });
  await view.click('分享文件');
  assert.deepEqual(view.errors(), ['403 无权访问文件']);
  assert.equal(view.requests.length, 1);
  assert.equal(view.button('打开系统分享面板').props.disabled, true);
});

test('device format rejection stays explicit and does not call share', async t => {
  const view = await setup(t, { canShare: false });
  await view.click('分享文件');
  assert.match(view.errors()[0], /无法分享此文件格式或大小/);
  assert.equal(view.shares.length, 0);
});

test('canceling the system picker is normal and does not claim sent or error', async t => {
  const view = await setup(t, { rejectShare: new DOMException('取消', 'AbortError') });
  await view.click('分享文件');
  await view.click('打开系统分享面板');
  assert.deepEqual(view.errors(), []);
  assert.equal(view.renderer.root.findByType('Modal').props.open, true);
});

test('a denied system picker reports its real error', async t => {
  const view = await setup(t, { rejectShare: new DOMException('分享权限被拒绝', 'NotAllowedError') });
  await view.click('分享文件');
  await view.click('打开系统分享面板');
  assert.deepEqual(view.errors(), ['分享权限被拒绝']);
});
