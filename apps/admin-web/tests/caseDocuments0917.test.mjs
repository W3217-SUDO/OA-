import assert from 'node:assert/strict';
import { test } from 'node:test';
import { build } from 'esbuild';
import Module, { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { readFileSync } from 'node:fs';

async function load(entry, api, messages = []) {
  const result = await build({ entryPoints: [fileURLToPath(new URL(entry, import.meta.url))], bundle: true, write: false, platform: 'node', format: 'cjs', packages: 'external', plugins: [{
    name: 'isolated-api', setup(builder) {
      builder.onResolve({ filter: /\/api$/ }, () => ({ path: 'api', namespace: 'test' }));
      builder.onResolve({ filter: /^antd$/ }, () => ({ path: 'antd', namespace: 'test' }));
      builder.onLoad({ filter: /.*/, namespace: 'test' }, ({ path }) => ({ contents: path === 'api' ? 'export const api=globalThis.__caseTestApi;' : 'export const message=globalThis.__caseTestMessage; export const Modal={}; export const Checkbox=()=>null; export const Space=()=>null; export const Descriptions=()=>null;' }));
    },
  }] });
  const target = new Module(fileURLToPath(import.meta.url));
  target.paths = Module._nodeModulePaths(fileURLToPath(new URL('.', import.meta.url)));
  target.require = createRequire(import.meta.url);
  globalThis.__caseTestApi = api;
  globalThis.__caseTestMessage = { warning: value => messages.push(value), error: value => messages.push(value) };
  try { target._compile(result.outputFiles[0].text, fileURLToPath(import.meta.url)); return target.exports; }
  finally { delete globalThis.__caseTestApi; delete globalThis.__caseTestMessage; }
}

test('案件线索动作加载右侧工作区，拒绝和不存在明确提示，不跳转调查大厅', async () => {
  const notices = [], loading = [], results = [];
  let response = { data: { clue: { id: 12 }, clue_files: [{ id: 1 }], evidence: [{ id: 2 }] } };
  const { createCaseWorkflowActions } = await load('../src/legal/services/workflowActions.tsx', {
    get: async path => { assert.equal(path, '/investigations/clues/12/workspace'); if (response instanceof Error) throw response; return response; },
  }, notices);
  const actions = createCaseWorkflowActions({ setCaseClueLoading: value => loading.push(value), setViewingCaseClue: value => results.push(value), setSelectedCaseClueEvidenceId: value => assert.equal(value, null), get onNavigate() { throw new Error('不允许离开案件'); } });
  await actions.openCaseClueWorkspace({ id: 12 });
  assert.equal(results[0].clue_files.length, 1);assert.equal(results[0].evidence.length, 1);
  for (const status of [403, 404]) { response = Object.assign(new Error('拒绝'), { response: { status } }); await actions.openCaseClueWorkspace({ id: 12 }); }
  assert.equal(results.length, 1);assert.equal(notices.length, 2);assert.equal(loading.at(-1), false);
  const source=readFileSync(new URL('../src/legal/CaseCenterPage.tsx',import.meta.url),'utf8');
  assert.match(source,/openRelatedClue=\{openCaseClueWorkspace\}/);
  assert.match(source,/onOpenClue=\{openCaseClueWorkspace\}/);
});

test('文档分页完整加载，第二页失败不得伪装成功', async () => {
  let fail = false;
  const { loadCaseDocuments } = await load('../src/legal/services/caseDocuments.ts', { get: async (path, { params }) => {
    assert.equal(path, '/cases/9/documents');
    if (fail && params.page === 2) throw new Error('第二页失败');
    return { data: { items: Array.from({ length: params.page === 1 ? 200 : 5 }, (_, i) => ({ id: (params.page - 1) * 200 + i })), pages: 2 } };
  } });
  assert.equal((await loadCaseDocuments(9)).data.items.length, 205);
  fail = true;await assert.rejects(loadCaseDocuments(9), /第二页失败/);
});



test('线索详情映射原始店铺链接、产品及多主体字段', async () => {
  const { CaseClueDetails } = await load('../src/legal/CaseDetail/CaseClueDetails.tsx', {});
  const tree=CaseClueDetails({clue:{id:1,serial_no:'CODEX-0917',data:{store_url:'https://example.test/store',product:'商品',product_url:'https://example.test/product',sale_num:'2万',producers:[{name:'厂商',address:'生产地址'}],indictees:[{name:'主体甲',identity_no:'TEST-A'},{name:'主体乙',identity_no:'TEST-B'}]}}});
  const fields=Object.fromEntries(tree.props.items.map(item=>[item.key,item.children]));
  assert.equal(fields['shop-link'].props.href,'https://example.test/store');
  assert.equal(fields.product,'商品');assert.equal(fields.scale,'2万');
  assert.equal(fields.subjects.length,2);
  assert.match(fields.subjects[1].props.children,/主体乙/);
  assert.match(fields.producers[0].props.children,/生产地址/);
});
