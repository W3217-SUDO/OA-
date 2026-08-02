import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const source = fs.readFileSync(new URL('./src/CaseCenterPage.tsx', import.meta.url), 'utf8');

test('公司案件开庭排期详情把权限操作收纳到旧站单一操作入口且隔离其他路由', () => {
  const routeMatch = source.match(
    /export const shouldUseCompanyScheduleDetailOperationMenu = \(initialView: string, sourceRoute\?: string\) => ([^;]+);/,
  );
  assert.ok(routeMatch, 'CaseCenterPage 应把详情操作菜单限制到公司案件开庭排期精确路由');
  const shouldUseCompanyScheduleDetailOperationMenu = new Function(
    'initialView',
    'sourceRoute',
    `return (${routeMatch[1]});`,
  );

  assert.equal(shouldUseCompanyScheduleDetailOperationMenu('case-company-schedule'), true);
  assert.equal(shouldUseCompanyScheduleDetailOperationMenu('case-detail-1-SH001', 'case-company-schedule'), true);
  assert.equal(shouldUseCompanyScheduleDetailOperationMenu('case-detail-1-SH001', 'case-company-civil'), false);
  assert.equal(shouldUseCompanyScheduleDetailOperationMenu('case-schedule'), false);
  assert.equal(shouldUseCompanyScheduleDetailOperationMenu('case-dept-schedule'), false);
  assert.equal(shouldUseCompanyScheduleDetailOperationMenu('case-company-schedule-extra'), false);
  assert.equal(shouldUseCompanyScheduleDetailOperationMenu('case-company-execution'), false);

  assert.match(source, /const caseDetailActionButtons = viewingCounselCase \? <>/);
  assert.match(
    source,
    /shouldUseCompanyScheduleDetailOperationMenu\(initialView,caseListReturnContext\?\.route\)\?<Dropdown trigger=\{\["click"\]\} dropdownRender=\{\(\)=><Card size="small"><div style=\{\{display:"grid",gap:8\}\}>\{caseDetailActionButtons\}<\/div><\/Card>\}><Button>操作<\/Button><\/Dropdown>:caseDetailActionButtons/,
  );
});
