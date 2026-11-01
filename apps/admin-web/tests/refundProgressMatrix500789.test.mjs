// BUG 500789：退费进度案件统计改成按律师助理的表格，大屏同一张表。
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const read = file => readFileSync(new URL(`../src/${file}`, import.meta.url), 'utf8');

test('退费进度页改用按人统计的进度表，并进入大屏轮播', () => {
  const page = read('ReportCenterPage.tsx');
  assert.match(page, /initialView === "reports-refund"\) return <ProgressMatrixReport title="退费进度案件统计" endpoint="\/reports\/refund-progress"/);
  assert.match(page, /initialView=\{largeScreenViews\[legacyIndex\]\} bigScreen \/>/);
  assert.match(page, /PAGE_OWN_LOADERS = new Set\(\[[^\]]*"reports-refund"/);
});

test('表格：合计行、点数字看清单、大屏自动刷新和翻页', () => {
  const matrix = read('ProgressMatrixReport.tsx');
  assert.match(matrix, /Table\.Summary\.Row className="progress-matrix-total-row"/);
  assert.match(matrix, /api\.get<\{ items: ProgressCase\[\] \}>\(`\$\{endpoint\}\/cases`, \{ params: \{ person, stage \} \}\)/);
  assert.match(matrix, /BIG_SCREEN_REFRESH_MS = 5 \* 60_000/);
  assert.match(matrix, /setPage\(current => current % pages \+ 1\)/);
  assert.ok(!read('report-center.css').split('BUG 500789')[1].includes('color-mix'), '大屏样式要兼容钉钉旧内核');
});
