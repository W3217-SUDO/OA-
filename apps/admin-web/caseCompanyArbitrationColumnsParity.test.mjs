import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const source = fs.readFileSync(new URL('./src/CaseCenterPage.tsx', import.meta.url), 'utf8');

test('公司仲裁列表使用旧站平铺专属表头且不影响其他案件路由', () => {
  const routeMatch = source.match(
    /export const shouldUseCompanyArbitrationColumns = \(initialView: string\) => ([^;]+);/,
  );
  assert.ok(routeMatch, 'CaseCenterPage 应把公司仲裁专属表头限制到精确路由');
  const shouldUseCompanyArbitrationColumns = new Function(
    'initialView',
    `return (${routeMatch[1]});`,
  );

  assert.equal(shouldUseCompanyArbitrationColumns('case-company-arbitration'), true);
  assert.equal(shouldUseCompanyArbitrationColumns('case-mine-arbitration'), false);
  assert.equal(shouldUseCompanyArbitrationColumns('case-dept-arbitration'), false);
  assert.equal(shouldUseCompanyArbitrationColumns('case-new-arbitration'), false);
  assert.equal(shouldUseCompanyArbitrationColumns('case-company-arbitration-extra'), false);
  assert.equal(shouldUseCompanyArbitrationColumns('case-company-criminal'), false);

  const schemaMatch = source.match(
    /export const getCompanyArbitrationColumnSchema = \(\) => (\[[\s\S]*?\n\]);/,
  );
  assert.ok(schemaMatch, 'CaseCenterPage 应定义公司仲裁专属列结构');
  const getCompanyArbitrationColumnSchema = new Function(`return (${schemaMatch[1]});`);
  const schema = getCompanyArbitrationColumnSchema();

  assert.deepEqual(
    schema.map(({ key, title }) => [key, title]),
    [
      ['serial_no', '案件编号'],
      ['charge', '案由'],
      ['plaintiff', '申请人'],
      ['defendant', '被申请人'],
      ['status', '案件阶段'],
      ['court', '仲裁机构'],
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
    /const originalCaseColumns=shouldUseCompanyArbitrationColumns\(initialView\)\?companyArbitrationCaseColumns:groupedOriginalCaseColumns;/,
  );
  assert.match(
    source,
    /columns=\{counselListMode\?counselCaseColumns:shouldUseCompanyCriminalQueryFields\(initialView\)\?companyCriminalCaseColumns:originalCaseColumns\}/,
  );
  assert.match(
    source,
    /case "serial_no": return <Button type="link" className="case-cell-link" onClick=\{\(\)=>void openCounselDetail\(row\)\}>\{row\.serial_no\}<\/Button>;/,
  );
});
