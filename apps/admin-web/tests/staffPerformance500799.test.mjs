// BUG 500799：员工业绩ROI统计改为“员工业绩统计中心”。
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const read = file => readFileSync(new URL(`../src/${file}`, import.meta.url), 'utf8');

test('菜单和页面改名为员工业绩统计中心，不再算 ROI', () => {
  assert.match(read('App.tsx'), /\{ key: "reports-staff-roi", label: "员工业绩统计中心" \}/);
  const page = read('ReportCenterPage.tsx');
  const staff = page.slice(page.indexOf('function StaffRoiReport'), page.indexOf('const largeScreenViews'));
  assert.match(staff, /api\.get<StaffPerformanceData>\("\/reports\/staff-performance"/);
  assert.ok(!staff.includes('ROI'), '员工业绩统计中心不再显示 ROI');
});

test('四类数、四种角色、姓名查个人；默认图，可切表格，大屏只放图', () => {
  const page = read('ReportCenterPage.tsx');
  for (const label of ['案源人', '调查员', '开庭律师', '律师助理']) assert.match(page, new RegExp(`label: "${label}"`));
  for (const key of ['agency_fee', 'new_cases', 'active_cases', 'hearings', 'archived_cases', 'loss_archived_cases']) assert.ok(page.includes(`dataIndex: "${key}"`), key);
  const staff = page.slice(page.indexOf('function StaffRoiReport'), page.indexOf('const largeScreenViews'));
  assert.match(staff, /useState<"chart" \| "table">\("chart"\)/);
  assert.match(staff, /onClick=\{pageBigScreen\.enter\}>大屏展示<\/Button>/);
  assert.match(staff, /display === "table" && !bigScreen/);
  const css = read('report-center.css').split('BUG 500799')[1];
  for (const feature of ['color-mix', ':has(', '@container', 'dvh']) assert.ok(!css.includes(feature), `钉钉旧内核不支持 ${feature}`);
});
