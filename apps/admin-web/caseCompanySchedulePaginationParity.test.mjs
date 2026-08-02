import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const source = fs.readFileSync(new URL('./src/CaseCenterPage.tsx', import.meta.url), 'utf8');

test('公司案件开庭排期显示旧站页长选项与GO且不影响其他特殊案件路由', () => {
  const routeMatch = source.match(
    /export const shouldUseCompanySchedulePagination = \(initialView: string\) => ([^;]+);/,
  );
  assert.ok(routeMatch, 'CaseCenterPage 应把公司排期分页控件限制到精确路由');
  const shouldUseCompanySchedulePagination = new Function(
    'initialView',
    `return (${routeMatch[1]});`,
  );

  assert.equal(shouldUseCompanySchedulePagination('case-company-schedule'), true);
  assert.equal(shouldUseCompanySchedulePagination('case-schedule'), false);
  assert.equal(shouldUseCompanySchedulePagination('case-dept-schedule'), false);
  assert.equal(shouldUseCompanySchedulePagination('case-company-schedule-extra'), false);
  assert.equal(shouldUseCompanySchedulePagination('case-company-execution'), false);

  const sizesMatch = source.match(
    /export const getCompanySchedulePageSizeOptions = \(\) => (\[[^;]+\]);/,
  );
  assert.ok(sizesMatch, 'CaseCenterPage 应定义旧站排期页长选项');
  const getCompanySchedulePageSizeOptions = new Function(`return (${sizesMatch[1]});`);
  assert.deepEqual(getCompanySchedulePageSizeOptions(), ['10', '15', '20', '50', '100', '200']);

  const singlePageJumperMatch = source.match(
    /export const shouldShowCompanyScheduleSinglePageJumper = \(initialView: string, rowCount: number, pageSize: number\) => ([^;]+);/,
  );
  assert.ok(singlePageJumperMatch, 'CaseCenterPage should keep GO visible for the single-page company schedule baseline');
  const shouldShowCompanyScheduleSinglePageJumper = new Function(
    'initialView',
    'rowCount',
    'pageSize',
    `return (${singlePageJumperMatch[1]});`,
  );
  assert.equal(shouldShowCompanyScheduleSinglePageJumper('case-company-schedule', 2, 20), true);
  assert.equal(shouldShowCompanyScheduleSinglePageJumper('case-company-schedule', 20, 20), true);
  assert.equal(shouldShowCompanyScheduleSinglePageJumper('case-company-schedule', 0, 20), false);
  assert.equal(shouldShowCompanyScheduleSinglePageJumper('case-company-schedule', 21, 20), false);
  assert.equal(shouldShowCompanyScheduleSinglePageJumper('case-dept-schedule', 2, 20), false);
  assert.equal(shouldShowCompanyScheduleSinglePageJumper('case-company-execution', 2, 20), false);

  assert.match(
    source,
    /shouldUseCompanySchedulePagination\(initialView\)\?\{defaultPageSize:20,showSizeChanger:true,pageSizeOptions:getCompanySchedulePageSizeOptions\(\),showQuickJumper:\{goButton:<Button size="small">GO<\/Button>\}\}:\{pageSize:20\}/,
  );
  assert.match(
    source,
    /shouldShowCompanyScheduleSinglePageJumper\(initialView,specialRows\.length,companySchedulePageSize\)&&<Space[^>]*><InputNumber[^>]*aria-label="页码"[^>]*\/><Button size="small" onClick=\{\(\)=>setCompanySchedulePage\(1\)\}>GO<\/Button><\/Space>/,
  );
});
