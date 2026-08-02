import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const source = fs.readFileSync(new URL('./src/CaseCenterPage.tsx', import.meta.url), 'utf8');

test('法律顾问列表使用旧站五阶段并把待分配映射到新案状态', () => {
  const match = source.match(
    /export const getCasePhaseDefinitions = \(initialView: string, defaultItems: \{label:string;value:string\}\[\], criminalItems: \{label:string;value:string\}\[\]\) => \{([\s\S]*?)\n\};/,
  );
  assert.ok(match, 'CaseCenterPage 应按列表类型选择案件阶段目录');
  const getCasePhaseDefinitions = new Function(
    'initialView',
    'defaultItems',
    'criminalItems',
    match[1],
  );

  assert.deepEqual(
    getCasePhaseDefinitions(
      'case-company-counsel',
      [{ label: '民事阶段', value: '民事阶段' }],
      [{ label: '刑事阶段', value: '刑事阶段' }],
    ),
    [
      { label: '待分配', value: '新案待分配' },
      { label: '服务中', value: '服务中' },
      { label: '续费中', value: '续费中' },
      { label: '已过期', value: '已过期' },
      { label: '归档阶段', value: '归档阶段' },
    ],
  );
});
