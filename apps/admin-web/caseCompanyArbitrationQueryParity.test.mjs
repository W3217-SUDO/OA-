import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const source = fs.readFileSync(new URL('./src/CaseCenterPage.tsx', import.meta.url), 'utf8');

test('公司仲裁列表只展示旧站九项查询字段且不影响其他路由', () => {
  const routeMatch = source.match(
    /export const shouldUseCompanyArbitrationQueryFields = \(initialView: string\) => ([^;]+);/,
  );
  assert.ok(routeMatch, 'CaseCenterPage 应把公司仲裁专属查询字段限制到精确路由');
  const shouldUseCompanyArbitrationQueryFields = new Function(
    'initialView',
    `return (${routeMatch[1]});`,
  );

  assert.equal(shouldUseCompanyArbitrationQueryFields('case-company-arbitration'), true);
  assert.equal(shouldUseCompanyArbitrationQueryFields('case-mine-arbitration'), false);
  assert.equal(shouldUseCompanyArbitrationQueryFields('case-dept-arbitration'), false);
  assert.equal(shouldUseCompanyArbitrationQueryFields('case-new-arbitration'), false);
  assert.equal(shouldUseCompanyArbitrationQueryFields('case-company-arbitration-extra'), false);
  assert.equal(shouldUseCompanyArbitrationQueryFields('case-company-criminal'), false);

  const fieldsMatch = source.match(
    /export const getCompanyArbitrationQueryFields = \(\) => (\[[\s\S]*?\n\]);/,
  );
  assert.ok(fieldsMatch, 'CaseCenterPage 应定义公司仲裁列表专属查询字段');
  const getCompanyArbitrationQueryFields = new Function(`return (${fieldsMatch[1]});`);

  assert.deepEqual(getCompanyArbitrationQueryFields(), [
    ['plaintiff', '申请人', '申请人'],
    ['serial_no', '案号', '案号'],
    ['keyword', '关键字', '案号、法院号、案件名称、客户名称'],
    ['defendant', '被申请人', '被申请人'],
    ['notary_no', '公证书号', '公证书号'],
    ['status', '案件阶段', '案件阶段'],
    ['hearing_lawyer', '开庭律师', '开庭律师'],
    ['handling_lawyer', '经办律师', '经办律师'],
    ['court', '仲裁机构', '仲裁机构'],
  ]);

  assert.match(source, /shouldUseCompanyArbitrationQueryFields\(initialView\) \? <>/);
  assert.match(source, /getCompanyArbitrationQueryFields\(\)\.map\(\(\[name,label,placeholder\]\)=>/);
});
