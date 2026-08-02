import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const source = fs.readFileSync(new URL('./src/CaseCenterPage.tsx', import.meta.url), 'utf8');

test('公司案件开庭排期使用旧站查询占位与开庭日期默认值且不影响其他路由', () => {
  const routeMatch = source.match(
    /export const shouldUseCompanyScheduleQueryFields = \(initialView: string\) => ([^;]+);/,
  );
  assert.ok(routeMatch, 'CaseCenterPage 应把公司案件开庭排期查询配置限制到精确路由');
  const shouldUseCompanyScheduleQueryFields = new Function(
    'initialView',
    `return (${routeMatch[1]});`,
  );

  assert.equal(shouldUseCompanyScheduleQueryFields('case-company-schedule'), true);
  assert.equal(shouldUseCompanyScheduleQueryFields('case-schedule'), false);
  assert.equal(shouldUseCompanyScheduleQueryFields('case-dept-schedule'), false);
  assert.equal(shouldUseCompanyScheduleQueryFields('case-company-schedule-extra'), false);
  assert.equal(shouldUseCompanyScheduleQueryFields('case-company-arbitration'), false);

  const fieldsMatch = source.match(
    /export const getCompanyScheduleQueryFields = \(\): \[string,string,string\?,string\?\]\[\] => (\[[\s\S]*?\n\]);/,
  );
  assert.ok(fieldsMatch, 'CaseCenterPage 应定义公司案件开庭排期专属查询字段');
  const getCompanyScheduleQueryFields = new Function(`return (${fieldsMatch[1]});`);

  assert.deepEqual(getCompanyScheduleQueryFields(), [
    ['plaintiff', '原告/申请人/公诉机关', 'text', '原告'],
    ['serial_no', '案号', 'text', '案号'],
    ['handling_lawyer', '经办律师', 'text', '经办律师'],
    ['keyword', '关键字', 'text', '案号、法院号、案件名称、客户名称'],
    ['defendant', '被告/被申请人', 'text', '被告'],
    ['notary_no', '公证书号', 'text', '公证书号'],
    ['hearing_lawyer', '开庭律师', 'text', '开庭律师'],
    ['court', '法院/机构', 'text', '法院名称'],
    ['third_party', '第三人/受害人', 'text', '第三人'],
    ['investigator', '调查员', 'text', '调查员'],
    ['assistant', '律师助理', 'text', '律师助理'],
    ['document_name', '文档名称', 'text', '文档名称'],
    ['source_range', '案源时间', 'date', ''],
    ['hearing_range', '开庭时间', 'date', ''],
    ['case_type', '案件类型', 'select', '请选择'],
    ['log_content', '日志内容', 'text', '日志内容'],
  ]);

  const defaultsMatch = source.match(
    /export const getCompanyScheduleQueryInitialValues = \(today: unknown\) => \((\{[^;]+\})\);/,
  );
  assert.ok(defaultsMatch, 'CaseCenterPage 应定义公司案件开庭排期开庭日期默认值');
  const getCompanyScheduleQueryInitialValues = new Function(
    'today',
    `return (${defaultsMatch[1]});`,
  );
  assert.deepEqual(getCompanyScheduleQueryInitialValues('2026-08-02'), {
    hearing_range: ['2026-08-02', null],
  });

  assert.match(
    source,
    /schedule:shouldUseCompanyScheduleQueryFields\(initialView\)\?getCompanyScheduleQueryFields\(\):\[/,
  );
  assert.match(
    source,
    /initialValues=\{shouldUseCompanyScheduleQueryFields\(initialView\)\?getCompanyScheduleQueryInitialValues\(dayjs\(\)\):undefined\}/,
  );
});
