import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const source = fs.readFileSync(new URL('./src/CaseCenterPage.tsx', import.meta.url), 'utf8');

test('公司刑事列表只展示旧站九项查询字段', () => {
  const routeMatch = source.match(
    /export const shouldUseCompanyCriminalQueryFields = \(initialView: string\) => ([^;]+);/,
  );
  assert.ok(routeMatch, 'CaseCenterPage 应把公司刑事专属查询字段限制到精确路由');
  const shouldUseCompanyCriminalQueryFields = new Function(
    'initialView',
    `return (${routeMatch[1]});`,
  );

  assert.equal(shouldUseCompanyCriminalQueryFields('case-company-criminal'), true);
  assert.equal(shouldUseCompanyCriminalQueryFields('case-mine-criminal'), false);
  assert.equal(shouldUseCompanyCriminalQueryFields('case-dept-criminal'), false);
  assert.equal(shouldUseCompanyCriminalQueryFields('case-new-criminal'), false);

  const match = source.match(
    /export const getCompanyCriminalQueryFields = \(\) => (\[[\s\S]*?\n\]);/,
  );
  assert.ok(match, 'CaseCenterPage 应定义公司刑事列表专属查询字段');

  const getCompanyCriminalQueryFields = new Function(`return (${match[1]});`);
  assert.deepEqual(getCompanyCriminalQueryFields(), [
    ['prosecutor', '公诉机关', '公诉机关'],
    ['serial_no', '案号', '案号'],
    ['keyword', '关键字', '案号、法院号、案件名称、客户名称'],
    ['defendant', '被告', '被告'],
    ['notary_no', '公证书号', '公证书号'],
    ['status', '案件阶段', '案件阶段'],
    ['hearing_lawyer', '开庭律师', '开庭律师'],
    ['handling_lawyer', '经办律师', '经办律师'],
    ['court', '法院名称', '法院名称'],
  ]);

  assert.match(source, /shouldUseCompanyCriminalQueryFields\(initialView\) \? <>/);
  assert.doesNotMatch(source, /initialView\.endsWith\("criminal"\) \? <>/);
  assert.match(source, /getCompanyCriminalQueryFields\(\)\.map\(\(\[name,label,placeholder\]\)=>/);
});
