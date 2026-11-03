import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), 'utf8');

test('案件阶段参数有“预期停留天数”，表单、保存、列表三处都带上（501222）', () => {
  // 保存时按 extraFieldsLocal 重建 extra，漏掉这里会在改阶段时把预期天数清掉。
  const field = /\{ key: "expected_days", label: "预期停留天数" \}/;
  assert.match(read('../src/system/constants.ts'), field);
  assert.match(read('../src/system/SystemCenterPage.tsx'), field);
  assert.match(read('../src/system/SystemParameterManagement.tsx'), /title: "预期停留天数"/);
});
