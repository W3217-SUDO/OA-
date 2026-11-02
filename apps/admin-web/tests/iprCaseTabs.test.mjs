import test from 'node:test';
import assert from 'node:assert/strict';
import { iprCaseDetailRoute, iprCaseTabLabel, parseIprCaseDetailRoute } from '../src/ipr/iprCaseTabs.ts';

// BUG20261102003（高勤兰 11-02）：列表点案号另开“专利 案号”/“商标 案号”标签，同一案件一个标签。
test('patent and trademark cases get their own stable tab route and label', () => {
  const patent = iprCaseDetailRoute({ id: 12, serial_no: 'SHPI1810979', data: { case_kind: '专利' } });
  const trademark = iprCaseDetailRoute({ id: 34, serial_no: 'SHTM/01', data: { case_kind: '商标' } });
  assert.equal(patent, 'ipr-case-detail-12-p-SHPI1810979');
  assert.equal(iprCaseDetailRoute({ id: 12, serial_no: 'SHPI1810979', data: { case_kind: '专利' } }), patent);
  assert.equal(iprCaseTabLabel(patent), '专利 SHPI1810979');
  assert.deepEqual(parseIprCaseDetailRoute(trademark), { id: 34, kind: '商标', serialNo: 'SHTM/01' });
  assert.equal(iprCaseTabLabel('ipr-patent'), null);
});
