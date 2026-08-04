import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const source = fs.readFileSync(new URL('./src/CaseCenterPage.tsx', import.meta.url), 'utf8');

test('案件提醒支持日期截止校验、创建与删除确认', () => {
  assert.match(source, /api\.post\(`\/cases\/\$\{viewingCounselCase\.id\}\/reminders`/);
  assert.match(source, /api\.delete\(`\/cases\/\$\{viewingCounselCase\.id\}\/reminders\/\$\{reminder\.id\}`/);
  assert.match(source, /提醒日期不能晚于截止日期/);
  assert.match(source, /删除案件提醒/);
  assert.match(source, /can_create_reminder/);
  assert.match(source, /can_delete_reminder/);
  assert.match(source, /待归档审核|已归档/);
});

test('case detail logs expose both legacy case log and refund log entry buttons', () => {
  assert.ok(source.includes('type CaseLogKind = "case" | "refund"'));
  assert.ok(source.includes('const openCounselLogCreator = (kind: CaseLogKind) => {'));
  assert.ok(source.includes('setCaseLogKind(kind);'));
  assert.ok(source.includes('openCounselLogCreator("case")'));
  assert.ok(source.includes('>新增日志</Button>'));
  assert.ok(source.includes('openCounselLogCreator("refund")'));
  assert.ok(source.includes('>新增退费日志</Button>'));
  assert.ok(source.includes('<Space size={0}><Button type="link" size="small" onClick={()=>openCounselLogCreator("case")}>新增日志</Button><Button type="link" size="small" onClick={()=>openCounselLogCreator("refund")}>新增退费日志</Button></Space>'));
  assert.ok(source.includes('const logContent = caseLogKind === "refund" ? `退费日志：${values.content.trim()}` : values.content.trim();'));
  assert.ok(source.includes('api.post(`/cases/${viewingCounselCase.id}/logs`,{content:logContent})'));
});

test('案件日志写入专用接口并回显到系统日志', () => {
  assert.match(source, /api\.post\(`\/cases\/\$\{viewingCounselCase\.id\}\/logs`/);
  assert.match(source, /新增案件日志/);
  assert.match(source, /请输入日志内容/);
  assert.match(source, /key:\"logs\",label:\"系统日志\"/);
});
