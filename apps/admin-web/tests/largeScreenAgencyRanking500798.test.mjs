// BUG 500798/500800/500801：报表大屏。员工业绩排行已移到员工业绩统计中心（500799）；大屏放经营总数据 4 块；
// 只在确实没有金额权限时提示；发布新版本后大屏自动重新加载。
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const read = file => readFileSync(new URL(`../src/${file}`, import.meta.url), 'utf8');

test('大屏放经营总数据 4 块，员工业绩排行已撤掉（BUG 500801）', () => {
  const page = read('ReportCenterPage.tsx');
  for (const title of ['年新增案件数', '年开庭数量', '新增调查线索·{group}', '年任务数量']) assert.ok(page.includes(title), title);
  assert.match(page, /\[\["by_investigator", "按调查员"\], \["by_brand", "按品牌"\]\]/);
  assert.match(page, /\{ key: "submitted", name: "提交线索数"/);
  assert.match(page, /\{ key: "approved", name: "审核通过数"/);
  // 19:12：线索两张图用分组柱状图，不用折线。
  assert.match(page, /<GroupedBarChart rows=\{overview\.clues\[key\]\} bars=\{clueLines\} \/>/);
  assert.match(page, /\{ key: "issued", name: "发出任务数"/);
  assert.match(page, /\{ key: "done", name: "完成任务数"/);
  assert.ok(!page.includes('员工业绩排行</strong>'), '员工业绩排行已移到员工业绩统计中心');
  assert.ok(!page.includes('案件类型分布'), '案件类型分布去掉');
});

test('大屏只在确实没有金额权限时提示；发布新版本后自动重新加载（BUG 500800）', () => {
  const page = read('ReportCenterPage.tsx');
  assert.match(page, /fetch\(`\/build-info\.json\?_=\$\{Date\.now\(\)\}`, \{ cache: "no-store" \}\)/);
  assert.match(page, /else if \(version !== loadedVersion\) window\.location\.reload\(\);/);
  assert.match(page, /data\.finance\.amount_visible \? \(data\.definitions\?\.income/);
});
