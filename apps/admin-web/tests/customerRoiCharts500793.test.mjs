// BUG 500793：客户ROI 加图，默认显示图，右上角“图 / 表格”切换，大屏只放图。
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const read = file => readFileSync(new URL(`../src/${file}`, import.meta.url), 'utf8');

test('客户ROI：收入成本对比柱叠 ROI 折线（前 15 名）和 ROI 排行横条（正绿负红）', () => {
  const page = read('ReportCenterPage.tsx');
  assert.match(page, /const ROI_TOP_INCOME = 15;/);
  assert.match(page, /<Bar yAxisId="amount" dataKey="income" name="收入"/);
  assert.match(page, /<Bar yAxisId="amount" dataKey="cost" name="成本"/);
  assert.match(page, /<Line yAxisId="roi" dataKey="roi" name="ROI"/);
  assert.match(page, /layout="vertical"/);
  assert.match(page, /Number\(row\.roi\) < 0 \? "#ef6d85" : "#2cc47c"/);
  assert.match(page, /Number\(row\.cost \|\| 0\) !== 0/, '成本为 0 的不进 ROI 排行');
});

test('客户ROI：默认显示图，可切表格；大屏只放图并隐藏筛选和表格', () => {
  const page = read('ReportCenterPage.tsx');
  const roi = page.slice(page.indexOf('function CustomerRoiReport'), page.indexOf('function StaffRoiReport'));
  assert.match(roi, /useState<"chart" \| "table">\("chart"\)/);
  assert.match(roi, /options=\{\[\{ label: "图", value: "chart" \}, \{ label: "表格", value: "table" \}\]\}/);
  assert.match(roi, /onClick=\{pageBigScreen\.enter\}>大屏展示<\/Button>/);
  assert.match(roi, /\{!bigScreen && <Form form=\{form\}/);
  assert.match(roi, /display === "table" && !bigScreen && <div className="report-roi-table-panel">/);
  const css = read('report-center.css').split('BUG 500793')[1];
  for (const feature of ['color-mix', ':has(', '@container', 'dvh']) assert.ok(!css.includes(feature), `钉钉旧内核不支持 ${feature}`);
});
