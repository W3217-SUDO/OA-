import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const source = fs.readFileSync(new URL('./src/CaseCenterPage.tsx', import.meta.url), 'utf8');

test('我的案件查询支持重置并恢复第一页数据', () => {
  assert.match(source, /caseQueryForm\.resetFields\(\);setCaseQuery\(\{\}\);setOriginalPage\(1\);if\(counselListMode\)void loadCounselCases\(\{\},1,counselPageSize\)/);
  assert.match(source, /pageSizeOptions:\[10,15,20,50,100,200\]/);
  assert.match(source, /const \[originalPage, setOriginalPage\] = useState\(caseListReturnContext\?\.page \|\| 1\)/);
  assert.match(source, /const \[originalPageSize, setOriginalPageSize\] = useState\(caseListReturnContext\?\.pageSize \|\| 10\)/);
  assert.match(source, /current:originalPage,pageSize:originalPageSize/);
  assert.match(source, /setOriginalPage\(nextPage\);setOriginalPageSize\(nextPageSize\);sessionStorage\.setItem\("sunhold:case-list-return"/);
  assert.match(source, /if \(!isCreateView && !isCaseDetailView && caseListReturnContext\?\.query\)/);
  assert.match(source, /setOriginalPage\(page\);\s*setOriginalPageSize\(pageSize\);\s*onNavigate\?\.\(route\);/);
  assert.match(source, /initialView\.startsWith\("case-mine"\)/);
  assert.match(source, /const exportCases = async \(\) => \{\s*if \(!originalCases\.length\) return message\.warning\("当前查询没有可导出的案件"\);/);
});

test('我的案件列表保留详情入口与导出/批量操作', () => {
  assert.match(source, /onClick=\{\(\)=>void openCounselDetail\(row\)\}/);
  assert.match(source, /导出选中（Excel）/);
  assert.match(source, /更多操作 ▾/);
});
