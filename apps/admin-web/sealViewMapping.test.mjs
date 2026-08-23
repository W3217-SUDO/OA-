import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { createRequire } from 'node:module';
import ts from 'typescript';

const mappingPath = path.join(process.cwd(), 'src', 'sealWorkflowPolicy.ts');
const javascript = ts.transpileModule(fs.readFileSync(mappingPath, 'utf8'), {
  fileName: mappingPath,
  compilerOptions: {
    esModuleInterop: true,
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2022,
  },
}).outputText;
const module = { exports: {} };
const wrapper = vm.runInThisContext(
  `(function (require, module, exports, __filename, __dirname) { ${javascript}\n})`,
  { filename: mappingPath },
);
wrapper(createRequire(import.meta.url), module, module.exports, mappingPath, path.dirname(mappingPath));
const { sealRouteMapping, sealRouteStatuses } = module.exports;

test('every declared route maps to its exact page statuses', () => {
  const expected = {
    'seal-my': { view: 'my', statuses: [] },
    'seal-my-pending': { view: 'my', statuses: ['待审批'] },
    'seal-my-stamping': { view: 'my', statuses: ['待用印'] },
    'seal-my-used': { view: 'my', statuses: ['已用印', '已归档'] },
    'seal-my-refused': { view: 'my', statuses: ['已拒绝'] },
    'seal-my-withdrawn': { view: 'my', statuses: ['已撤回'] },
    'seal-audit': { view: 'audit', statuses: [] },
    'seal-audit-pending': { view: 'audit', statuses: ['待审批'] },
    'seal-audit-stamping': { view: 'audit', statuses: ['待用印'] },
    'seal-audit-refused': { view: 'audit', statuses: ['已拒绝'] },
    'seal-admin': { view: 'all', statuses: [] },
    'seal-admin-pending': { view: 'all', statuses: ['待用印'] },
    'seal-admin-used': { view: 'all', statuses: ['已用印'] },
  };
  expected['seal-admin-query'] = { view: 'all', statuses: [] };
  assert.deepEqual(Object.keys(sealRouteMapping).sort(), Object.keys(expected).sort());
  for (const [route, spec] of Object.entries(expected)) {
    assert.deepEqual(sealRouteMapping[route], spec);
    assert.deepEqual(sealRouteStatuses(route), spec.statuses);
  }
  assert.deepEqual(sealRouteStatuses('seal-audit-extra'), []);
  assert.deepEqual(sealRouteStatuses('unknown'), []);
});
