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
  assert.match(matrix, /`\$\{endpoint\}\/cases`, \{ params: \{ person, stage \} \}/);
  assert.match(matrix, /BIG_SCREEN_REFRESH_MS = 5 \* 60_000/);
  assert.match(matrix, /setPage\(current => current % pages \+ 1\)/);
  assert.ok(!read('report-center.css').split('BUG 500789')[1].includes('color-mix'), '大屏样式要兼容钉钉旧内核');
});

test('执行进度三张表合并成一张按律师助理的表（BUG 500788）', () => {
  const page = read('ReportCenterPage.tsx');
  assert.match(page, /initialView\.startsWith\("reports-execution-"\)\) return <ProgressMatrixReport title="执行进度案件统计" endpoint="\/reports\/execution-progress"/);
  assert.match(page, /const largeScreenViews = \["reports-refund", "reports-execution-1"\];/);
  assert.ok(!page.includes('一审待执行案件数量'));
  const app = read('App.tsx');
  assert.match(app, /\{ key: "reports-execution-1", label: "执行进度案件统计" \}/);
  assert.ok(!app.includes('"reports-execution-2"') && !app.includes('"reports-execution-3"'));
  assert.match(read('ProgressMatrixReport.tsx'), /setDrillColumns\(result\.columns \|\| \[\]\)/);
});

test('“大屏展示”全屏显示本页，不再跳经营数据大屏（BUG 500789 15:39）', () => {
  for (const file of ['ReportCenterPage.tsx', 'ProgressMatrixReport.tsx']) {
    const source = read(file);
    assert.ok(!source.includes('onClick={() => onNavigate("reports-large-screen")}>大屏展示'), file);
    assert.match(source, /onClick=\{pageBigScreen\.enter\}>大屏展示<\/Button>/, file);
    assert.match(source, /onClick=\{pageBigScreen\.exit\}>退出大屏<\/Button>/, file);
  }
  assert.match(read('reportBigScreen.ts'), /requestFullscreen\(\)/);
  assert.match(read('report-center.css'), /\.report-page\.report-page-big-screen \{ position: fixed;/);
});

test('每个进度一个柱状图，横轴律师助理、纵轴案件数，大屏收起说明（BUG 500792）', async () => {
  const matrix = read('ProgressMatrixReport.tsx');
  assert.match(matrix, /data\.stages\.map\(stage => \(\s*<StageChart/);
  assert.match(matrix, /<span>\{stage\}案件数量<\/span>/);
  assert.match(matrix, /▸ 展开说明/);
  const css = read('report-center.css').split('BUG 500792')[1];
  assert.match(css, /grid-template-columns: repeat\(3, minmax\(0, 1fr\)\)/);
  assert.ok(!/color-mix|:has\(|@container|dvh/.test(css), '要兼容钉钉 Chrome 100 内核');
});
