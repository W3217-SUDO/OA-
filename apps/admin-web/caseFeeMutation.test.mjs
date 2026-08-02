import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const source = fs.readFileSync(new URL('./src/CaseCenterPage.tsx', import.meta.url), 'utf8');

test('案件费用草稿提供独立修改与删除确认入口', () => {
  assert.match(source, /api\.put\(`\/finance\/fees\/\$\{editingFeeRow\.id\}`/);
  assert.match(source, /api\.delete\(`\/finance\/fees\/\$\{row\.id\}`/);
  assert.match(source, /row\.status===\"草稿\"&&counselDetailCapabilities\.can_create_finance/);
  assert.match(source, /key:\"edit\",label:\"修改\"/);
  assert.match(source, /key:\"delete\",label:\"删除\"/);
  assert.match(source, /<Dropdown trigger=\{\[\"click\"\]\} menu=\{\{items:\[\{key:\"edit\"/);
  assert.match(source, /Modal\.confirm\(\{ title: `删除费用/);
  assert.match(source, /仅草稿费用可以修改/);
  assert.match(source, /仅草稿费用可以删除/);
});

test('费用弹窗编辑态使用保存文案并可取消清空目标', () => {
  assert.match(source, /open=\{Boolean\(feeCase \|\| editingFeeRow\)\}/);
  assert.match(source, /okText=\{editingFeeRow \? \"保存费用草稿\" : \"创建费用草稿\"\}/);
  assert.match(source, /setFeeCase\(null\); setEditingFeeRow\(null\); feeForm\.resetFields\(\)/);
});
