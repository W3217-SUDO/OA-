import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const source = fs.readFileSync(new URL('./src/CaseCenterPage.tsx', import.meta.url), 'utf8');

test('公司仲裁列表使用旧站六阶段且不影响其他仲裁路由', () => {
  const match = source.match(
    /export const getCasePhaseDefinitions = \(initialView: string, defaultItems: \{label:string;value:string\}\[\], criminalItems: \{label:string;value:string\}\[\]\) => \{([\s\S]*?)\n\};/,
  );
  assert.ok(match, 'CaseCenterPage 应按精确列表路由选择案件阶段目录');

  const getCasePhaseDefinitions = new Function(
    'initialView',
    'defaultItems',
    'criminalItems',
    match[1],
  );
  const defaultItems = [{ label: '默认阶段', value: '默认阶段' }];
  const criminalItems = [{ label: '刑事阶段', value: '刑事阶段' }];

  assert.deepEqual(
    getCasePhaseDefinitions('case-company-arbitration', defaultItems, criminalItems),
    [
      { label: '待分配', value: '新案待分配' },
      { label: '文书准备', value: '文书准备' },
      { label: '仲裁阶段', value: '仲裁阶段' },
      { label: '申诉阶段', value: '申诉阶段' },
      { label: '执行立案', value: '执行立案' },
      { label: '归档阶段', value: '归档阶段' },
    ],
  );

  for (const route of [
    'case-mine-arbitration',
    'case-dept-arbitration',
    'case-new-arbitration',
    'case-company-arbitration-extra',
  ]) {
    assert.equal(
      getCasePhaseDefinitions(route, defaultItems, criminalItems),
      defaultItems,
      `${route} 不应命中公司仲裁专属阶段`,
    );
  }
});
