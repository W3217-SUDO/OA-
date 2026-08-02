import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const source = fs.readFileSync(new URL('./src/CaseCenterPage.tsx', import.meta.url), 'utf8');

test('我的案件查询支持重置并恢复第一页数据', () => {
  assert.match(source, /caseQueryForm\.resetFields\(\);setCaseQuery\(\{\}\);if\(counselListMode\)void loadCounselCases\(\{\},1,counselPageSize\)/);
  assert.match(source, /pageSizeOptions:\[10,15,20,50,100,200\]/);
  assert.match(source, /initialView\.startsWith\("case-mine"\)/);
});

test('我的案件列表保留详情入口与导出/批量操作', () => {
  assert.match(source, /onClick=\{\(\)=>void openCounselDetail\(row\)\}/);
  assert.match(source, /导出选中（Excel）/);
  assert.match(source, /更多操作 ▾/);
});
