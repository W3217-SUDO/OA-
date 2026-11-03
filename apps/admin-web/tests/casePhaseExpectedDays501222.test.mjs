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

test('系统配置里有“旧系统迁来的案件也提醒”开关，保存到 case_stage_overdue（501222）', () => {
  const page = read('../src/system/SystemConfigList.tsx');
  assert.match(page, /row\.key === "case_stage_overdue"/);
  assert.match(page, /\/system\/configs\/case_stage_overdue", \{ value: \{ remind_legacy_cases: remindLegacyCases \} \}/);
});
