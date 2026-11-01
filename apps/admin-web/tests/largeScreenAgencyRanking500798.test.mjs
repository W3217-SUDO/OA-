// BUG 500798：报表大屏员工业绩排行加代理费到账（按案源人、按开庭律师），默认今年，可按日期重新筛选。
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const read = file => readFileSync(new URL(`../src/${file}`, import.meta.url), 'utf8');

test('大屏排行三图并排，日期默认今年，查询后按新区间取数', () => {
  const page = read('ReportCenterPage.tsx');
  assert.match(page, /const defaultRankingRange = \(\): \[Dayjs, Dayjs\] => \[dayjs\(\)\.startOf\("year"\), dayjs\(\)\];/);
  assert.match(page, /params: \{ ranking_from: range\[0\]\.format\("YYYY-MM-DD"\), ranking_to: range\[1\]\.format\("YYYY-MM-DD"\) \}/);
  assert.match(page, /\[\["by_source_person", "按案源人"\], \["by_hearing_lawyer", "按开庭律师"\]\]/);
  assert.match(page, /\{group\}·新建案件数/);
  assert.match(page, /\{group\}·代理费到账/);
  assert.ok(!page.includes('按案件负责人'), '18:14：不要按案件负责人');
  assert.match(page, /无财务金额查看权限/);
  const css = read('report-center.css').split('BUG 500798')[1];
  assert.match(css, /grid-template-columns: repeat\(2, minmax\(0, 1fr\)\)/);
  assert.ok(!/color-mix|:has\(|@container|dvh/.test(css), '要兼容钉钉 Chrome 100 内核');
});
