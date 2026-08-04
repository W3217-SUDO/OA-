import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const officialSource = fs.readFileSync(new URL('./src/IprOfficialFilePage.tsx', import.meta.url), 'utf8');
const iprSource = fs.readFileSync(new URL('./src/IprCenterPage.tsx', import.meta.url), 'utf8');

test('official file list and detail can open linked IPR case log composer', () => {
  assert.ok(officialSource.includes('const openOfficialCaseLog = (row: Official) => {'));
  assert.ok(officialSource.includes('params.set("open_log", "1")'));
  assert.ok(officialSource.includes('params.set("log_content",'));
  assert.ok(officialSource.includes('onClick={()=>openOfficialCaseLog(r)}>新增案件日志</Button>'));
  assert.ok(officialSource.includes('onClick={()=>openOfficialCaseLog(detail)}>新增案件日志</Button>'));
});

test('IPR case detail consumes official-file log deep link and pre-fills content', () => {
  assert.ok(iprSource.includes('const shouldOpenLog = params.get("open_log") === "1";'));
  assert.ok(iprSource.includes('const logContent = params.get("log_content") || "";'));
  assert.ok(iprSource.includes('iprLogForm.setFieldsValue({ content: logContent });'));
  assert.ok(iprSource.includes('setIprLogOpen(true);'));
});
