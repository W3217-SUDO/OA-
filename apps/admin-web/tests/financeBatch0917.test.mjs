import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { incomingTotals } from '../src/finance/incomingTotals.mjs';
import { selectableFeeTypes } from '../src/feeTypeHierarchy.mjs';

test('六列汇总使用完整筛选集并按分累加，空集为零，无金额权限不显示金额', () => {
  const rows = Array.from({length: 35}, () => ({amount: 0.3, allocated_amount: 0.1, remaining_amount: 0.2, assigned_official_fee: 0.05, assigned_agency_fee: 0.03, assigned_other_fee: 0.02}));
  assert.deepEqual(incomingTotals(rows), {回款金额:10.5,已分金额:3.5,未分金额:7,已分官费:1.75,已分代理费:1.05,已分其他费用:0.7});
  assert.equal(incomingTotals(rows.slice(0, 2)).回款金额, 0.6);
  assert.deepEqual(Object.values(incomingTotals([])), [0,0,0,0,0,0]);
  assert.deepEqual(Object.values(incomingTotals([{amount:null}])), [null,null,null,null,null,null]);
});

test('9.17 原目录证据：官费九项、平台其他费用四项，排除错误分组', () => {
  const source = JSON.parse(readFileSync(process.env.OA_FEE_CATALOG_EVIDENCE, 'utf8'));
  const catalog = source.selectable_fees.map(row => ({...row, fee_group:row.group, base_fee_type:row.base, expense_scopes:row.scopes, selectable:true, is_active:true}));
  const official = selectableFeeTypes(catalog, '律所', 'official').map(row=>row.name);
  assert.deepEqual(official.sort(), ['一审诉讼费','二审诉讼费','再审诉讼费','公证费','调解金额','判决金额','保全费','执行费','核定成本'].sort());
  assert.deepEqual(selectableFeeTypes(catalog,'平台','other').map(row=>row.name).sort(), ['案源介绍费','权利人分成','投资人分成','其他费用'].sort());
});
