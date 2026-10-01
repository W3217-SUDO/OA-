import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { selectableFeeTypes } from '../../src/feeTypeHierarchy.mjs';

test('9.17 原目录外部证据：官费九项、平台其他费用四项', () => {
  assert.ok(process.env.OA_FEE_CATALOG_EVIDENCE, '历史证据核验必须显式提供 OA_FEE_CATALOG_EVIDENCE');
  const source = JSON.parse(readFileSync(process.env.OA_FEE_CATALOG_EVIDENCE, 'utf8'));
  const catalog = source.selectable_fees.map(row => ({...row, fee_group:row.group, base_fee_type:row.base, expense_scopes:row.scopes, selectable:true, is_active:true}));
  assert.deepEqual(selectableFeeTypes(catalog, '律所', 'official').map(row => row.name).sort(), ['一审诉讼费','二审诉讼费','再审诉讼费','公证费','调解金额','判决金额','保全费','执行费','核定成本'].sort());
  assert.deepEqual(selectableFeeTypes(catalog, '平台', 'other').map(row => row.name).sort(), ['案源介绍费','权利人分成','投资人分成','其他费用'].sort());
});
