import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const source = fs.readFileSync(new URL('./src/CaseCenterPage.tsx', import.meta.url), 'utf8');

test('普通案件列表遵循旧系统的六组字段顺序', () => {
  const schemaMatch = source.match(
    /export const getLegacyGroupedCaseColumnSchema = \(\) => (\[[\s\S]*?\n\]);/,
  );
  assert.ok(schemaMatch, 'CaseCenterPage 应定义旧系统案件列表列结构');
  const schema = new Function(`return (${schemaMatch[1]});`)();

  assert.deepEqual(
    schema.map(({ key, title }) => [key, title]),
    [
      ['base', '基本信息'],
      ['parties', '当事人信息'],
      ['court', '法院信息'],
      ['lawyer', '委托律师'],
      ['phase', '阶段信息'],
      ['task', '任务信息'],
    ],
  );
  assert.equal(source.includes('title:"法官信息",key:"judge"'), false);
  assert.equal(source.includes('title:"判决信息",key:"judgment"'), false);
  assert.match(source, /case "court":[\s\S]*?case-inline-cell-link[\s\S]*?openCounselDetail\(row\)/);
  assert.match(source, /case "task":[\s\S]*?case-task-cell-link[\s\S]*?openCaseTasks\(row\)/);
  assert.match(source, /const originalCaseTableScrollX=shouldUseCompanyArbitrationColumns\(initialView\)\?companyArbitrationCaseTableScrollX:1645;/);
});
