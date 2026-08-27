import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const source = fs.readFileSync(new URL('./src/CaseCenterPage.tsx', import.meta.url), 'utf8');

test('控制台待执行入口读取统一的服务端待执行列表与总数', () => {
  assert.match(source, /api\.get\("\/cases\/pending-execution", \{ params: \{ page, page_size: pageSize \} \}\)/);
  assert.match(source, /initialView === "case-company-execution"[\s\S]*?loadPendingExecutionCases\(1, pendingExecutionPageSize\)/);
  assert.match(source, /specialMode==="execution"\?pendingExecutionCases:scopedCases/);
  assert.match(source, /specialMode==="execution"\?specialCases:/);
  assert.doesNotMatch(source, /specialMode==="execution"\?specialCases\.filter\(row=>row\.status==="执行"\)/);
  assert.match(source, /specialMode==="execution"\?\{current:pendingExecutionPage,pageSize:pendingExecutionPageSize,total:pendingExecutionTotal/);
});
