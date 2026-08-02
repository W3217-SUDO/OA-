import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const source = fs.readFileSync(new URL('./src/CaseCenterPage.tsx', import.meta.url), 'utf8');

test('公司案件开庭排期空结果隐藏操作栏且不影响其他特殊案件路由', () => {
  const guardMatch = source.match(
    /export const shouldShowCompanyScheduleActions = \(initialView: string, rowCount: number\) => ([^;]+);/,
  );
  assert.ok(guardMatch, 'CaseCenterPage 应定义公司案件开庭排期空结果操作栏守卫');
  const shouldShowCompanyScheduleActions = new Function(
    'initialView',
    'rowCount',
    `return (${guardMatch[1]});`,
  );

  assert.equal(shouldShowCompanyScheduleActions('case-company-schedule', 0), false);
  assert.equal(shouldShowCompanyScheduleActions('case-company-schedule', 1), true);
  assert.equal(shouldShowCompanyScheduleActions('case-schedule', 0), true);
  assert.equal(shouldShowCompanyScheduleActions('case-dept-schedule', 0), true);
  assert.equal(shouldShowCompanyScheduleActions('case-company-execution', 0), true);
  assert.equal(shouldShowCompanyScheduleActions('case-company-arbitration', 0), true);

  assert.match(
    source,
    /specialMode!=="invoice"&&specialMode!=="stage"&&shouldShowCompanyScheduleActions\(initialView,specialRows\.length\)&&<div className="case-bottom-actions">/,
  );
});
