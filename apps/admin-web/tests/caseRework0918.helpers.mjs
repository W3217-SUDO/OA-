import assert from 'node:assert/strict';
import { build } from 'esbuild';
import Module, { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

export async function load(entry, api, messages = []) {
  const result = await build({ entryPoints: [fileURLToPath(new URL(entry, import.meta.url))], bundle: true, write: false, platform: 'node', format: 'cjs', packages: 'external', plugins: [{
    name: 'isolated-api', setup(builder) {
      builder.onResolve({ filter: /\/api$/ }, () => ({ path: 'api', namespace: 'test' }));
      builder.onResolve({ filter: /^antd$/ }, () => ({ path: 'antd', namespace: 'test' }));
      builder.onLoad({ filter: /.*/, namespace: 'test' }, ({ path }) => ({ contents: path === 'api' ? 'export const api=globalThis.__reworkApi;' : 'export const message=globalThis.__reworkMessage; export const Modal={}; export const Checkbox=()=>null; export const Space=()=>null; export const Select="select-probe";' }));
    },
  }] });
  const target = new Module(fileURLToPath(import.meta.url));
  target.paths = Module._nodeModulePaths(fileURLToPath(new URL('.', import.meta.url)));
  target.require = createRequire(import.meta.url);
  globalThis.__reworkApi = api;
  globalThis.__reworkMessage = { success: value => messages.push(value), warning: value => messages.push(value), error: value => messages.push(value) };
  try { target._compile(result.outputFiles[0].text, fileURLToPath(import.meta.url)); return target.exports; }
  finally { delete globalThis.__reworkApi; delete globalThis.__reworkMessage; }
}

export async function courtPayloads() {
  const requests = [], messages = [];
  const { createCaseWorkflowActions } = await load('../src/legal/services/workflowActions.tsx', {
    put: async (path, body) => { requests.push(body); return { data: { id: 1, serial_no: 'CODEX-0918-REWORK' } }; },
  }, messages);
  globalThis.sessionStorage = { setItem() {} };
  globalThis.document = { querySelector() { return null; } };
  for (const level of ['first', 'second', 'execution', 'retrial']) {
    const actions = createCaseWorkflowActions({
      companyScheduleCourtInfo: { level, row: { id: 1, data: { first_instance_court: '历史法院', second_instance_court: '' } } },
      companyScheduleCourtInfoForm: { validateFields: async () => ({ court: `${level}法院`, case_no: `${level}案号`, courtroom: '法庭', judge: '法官', clerk: '书记员', filing_date: { format: () => '2026-09-20' }, hearing_date: { format: () => '2026-09-25 10:00:00' } }) },
      cancelCompanyScheduleCourtInfo() {}, load: async () => {},
    });
    await actions.submitCompanyScheduleCourtInfo();
    const payload = requests.at(-1);
    assert.equal(payload[`${level}_court_name`], `${level}法院`);
    for (const other of ['first', 'second', 'execution', 'retrial'].filter(item => item !== level)) {
      assert(!Object.keys(payload).some(key => key.startsWith(`${other}_`)), `${level}不应提交${other}`);
    }
  }
  assert.equal(messages.length, 4);
  assert(messages.every(text => text.endsWith('法院信息已更新')));
  delete globalThis.sessionStorage; delete globalThis.document;
  return requests;
}
if (process.argv.includes('--payloads')) console.log(JSON.stringify(await courtPayloads()));

