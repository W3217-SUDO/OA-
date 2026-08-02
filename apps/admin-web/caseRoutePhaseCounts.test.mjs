import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const source = fs.readFileSync(new URL('./src/CaseCenterPage.tsx', import.meta.url), 'utf8');

test('行政案件阶段计数只使用当前案件类型的数据', () => {
  const match = source.match(
    /export const scopeCasesByListRoute = \(rows: CaseRow\[\], initialView: string\) => \{([\s\S]*?)\n\};/,
  );
  assert.ok(match, 'CaseCenterPage 应提供可复用的路由案件类型筛选');
  const scopeCasesByListRoute = new Function('rows', 'initialView', match[1]);

  const rows = [
    { id: 1, status: '等待公证书', data: { case_type: '行政案件及国家赔偿' } },
    { id: 2, status: '文书准备', data: { case_type: '民事案件' } },
    { id: 3, status: '等待公证书', data: { case_type: '刑事案件' } },
  ];

  assert.deepEqual(
    scopeCasesByListRoute(rows, 'case-mine-administrative').map((row) => row.id),
    [1],
  );
  assert.deepEqual(
    scopeCasesByListRoute(rows, 'case-mine').map((row) => row.id),
    [1, 2, 3],
  );

  const phaseMatch = source.match(
    /export const buildCasePhaseItems = \(rows: CaseRow\[\], initialView: string, items: \{label:string;value:string\}\[\]\) => \{([\s\S]*?)\n\};/,
  );
  assert.ok(phaseMatch, 'CaseCenterPage 应按当前案件类型生成阶段计数');
  const buildCasePhaseItems = new Function(
    'rows',
    'initialView',
    'items',
    'scopeCasesByListRoute',
    phaseMatch[1],
  );
  assert.deepEqual(
    buildCasePhaseItems(
      rows,
      'case-mine-administrative',
      [
        { label: '等待公证书', value: '等待公证书' },
        { label: '文书准备', value: '文书准备' },
      ],
      scopeCasesByListRoute,
    ),
    [
      { label: '等待公证书', value: '等待公证书', count: 1 },
      { label: '文书准备', value: '文书准备', count: 0 },
    ],
  );
});
