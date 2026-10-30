// BUG20261030005：商标案件页按原系统商标页，和专利区分开。
import test from 'node:test';
import assert from 'node:assert/strict';
import {iprCaseEditValues, iprCaseFlags, iprCaseInfoItems} from '../src/ipr/IprCaseDetail/iprCaseInfo.ts';

const trademark = {serial_no: 'SHTM1811222', customer: '山西六建', status: '受理', data: {
  case_kind: '商标', case_name: '极九井及图', trademark_ids: '35', trade_type_id: 1, first_instance_date: '2016-12-13T00:00:00',
  trade_product_service: '商业管理咨询; 市场分析', has_priority: 'F', has_foreign: 'T', has_trade_color_protected: 'T',
  has_trade_voice_protected: 'F', has_trade3_d_protected: 'T', card_no: 'X', inventor: '9', cost_slow_rate: '1.00',
}};

test('商标案件不显示专利专用字段，显示商标类别等', () => {
  const items = iprCaseInfoItems(trademark);
  const labels = items.map(item => item.label);
  for (const hidden of ['证件号码', '发明人', '首年年费年度', '费用减缓比例']) assert.ok(!labels.includes(hidden), hidden);
  const value = label => items.find(item => item.label === label)?.value;
  assert.equal(value('商标名称'), '极九井及图');
  assert.equal(value('商标类别'), '35');
  assert.equal(value('商品服务'), '商业管理咨询; 市场分析');
  assert.equal(value('初审公告'), '2016-12-13');
  assert.equal(value('商标类型'), '一般商标');
  assert.equal(iprCaseEditValues(trademark)['trade-type'], '一般商标');
});

test('商标案件勾选项是优先权、涉外、颜色、声音、三维', () => {
  assert.deepEqual(iprCaseFlags(trademark).map(flag => [flag.label, flag.checked]), [
    ['优先权', false], ['涉外案件', true], ['颜色保护', true], ['声音标志', false], ['三维标志', true],
  ]);
});

test('专利案件不变', () => {
  const patent = {serial_no: 'SHPU1', data: {case_kind: '专利', inventor: '张三'}};
  const labels = iprCaseInfoItems(patent).map(item => item.label);
  assert.ok(labels.includes('发明人') && labels.includes('费用减缓比例') && !labels.includes('商标类别'));
  assert.deepEqual(iprCaseFlags(patent).map(flag => flag.label), ['优先权', '涉外案件', '费用减缓', '不公发明人', '一发一实']);
});
