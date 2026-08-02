import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const source = fs.readFileSync(new URL('./src/CaseCenterPage.tsx', import.meta.url), 'utf8');

test('公司刑事列表使用旧站平铺专属表头且不影响其他案件路由', () => {
  const match = source.match(
    /export const getCompanyCriminalColumnSchema = \(\) => (\[[\s\S]*?\n\]);/,
  );
  assert.ok(match, 'CaseCenterPage 应定义公司刑事专属列结构');
  const getCompanyCriminalColumnSchema = new Function(`return (${match[1]});`);
  const schema = getCompanyCriminalColumnSchema();

  assert.deepEqual(
    schema.map(({ key, title }) => [key, title]),
    [
      ['serial_no', '案件编号'],
      ['charge', '罪名'],
      ['prosecutor', '公诉机关'],
      ['defendant', '被告人/犯罪嫌疑人'],
      ['status', '案件阶段'],
      ['court', '法院名称'],
      ['hearing_at', '开庭时间'],
      ['handling_lawyer', '经办律师'],
      ['assistant', '律师助理'],
      ['source_person', '案源人'],
      ['remaining_days', '剩余时间'],
      ['spacer', ''],
    ],
  );
  assert.equal(schema.every((column) => column.children === undefined), true);

  assert.match(
    source,
    /columns=\{counselListMode\?counselCaseColumns:shouldUseCompanyCriminalQueryFields\(initialView\)\?companyCriminalCaseColumns:originalCaseColumns\}/,
  );
  assert.match(
    source,
    /case "serial_no": return <Button type="link" className="case-cell-link" onClick=\{\(\)=>void openCounselDetail\(row\)\}>\{row\.serial_no\}<\/Button>;/,
  );
});
