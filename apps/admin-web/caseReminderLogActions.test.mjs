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

test('案件日志写入专用接口并回显到系统日志', () => {
  assert.match(source, /api\.post\(`\/cases\/\$\{viewingCounselCase\.id\}\/logs`/);
  assert.match(source, /新增案件日志/);
  assert.match(source, /请输入日志内容/);
  assert.match(source, /key:\"logs\",label:\"系统日志\"/);
});
