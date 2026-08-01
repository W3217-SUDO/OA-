import test from 'node:test';
import assert from 'node:assert/strict';
import { sealViewMapping, sealViewSpec } from './src/sealViewMapping.ts';

test('every declared route maps to its exact API view and statuses', () => {
  const expected = {
    'seal-my': { view: 'my', statuses: [] },
    'seal-my-pending': { view: 'my', statuses: ['草稿', '待审批'] },
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
  assert.deepEqual(Object.keys(sealViewMapping).sort(), Object.keys(expected).sort());
  for (const [route, spec] of Object.entries(expected)) {
    assert.deepEqual(sealViewMapping[route], spec);
    assert.deepEqual(sealViewSpec(route), spec);
  }
  assert.deepEqual(sealViewSpec('seal-admin-query'), { view: 'all', statuses: [] });
  assert.deepEqual(sealViewSpec('seal-audit-extra'), { view: 'audit', statuses: [] });
  assert.deepEqual(sealViewSpec('unknown'), { view: 'my', statuses: [] });
});
