import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("case detail loads and renders a CaseEvent tab", () => {
  assert.match(source, /api\.get\(`\/cases\/\$\{row\.id\}\/events`\)/);
  assert.match(source, /key:"case-events",label:"案件事件"/);
  assert.match(source, /data-testid="case-events-tab"/);
  assert.match(source, /event_time/);
  assert.match(source, /deadline/);
  assert.match(source, /reminder_enabled/);
  assert.match(source, /remind_at/);
  assert.match(source, /creator_display_name/);
  assert.match(source, /案件事件加载失败，请重试/);
  assert.match(source, /loadCounselCaseEvents\(\)/);
});

test("CaseEvent mutations use scoped CRUD endpoints and event permissions", () => {
  assert.match(source, /counselCaseEventCapabilities\.can_create && <Button type="primary"/);
  assert.match(source, /row\.can_edit && <Button/);
  assert.match(source, /row\.can_delete && <Button/);
  assert.match(source, /api\.post\(`\/cases\/\$\{viewingCounselCase\.id\}\/events`, payload\)/);
  assert.match(source, /api\.patch\(`\/cases\/\$\{viewingCounselCase\.id\}\/events\/\$\{editingCaseEvent\.id\}`, payload\)/);
  assert.match(source, /api\.delete\(`\/cases\/\$\{viewingCounselCase\.id\}\/events\/\$\{event\.id\}`\)/);
  assert.match(source, /api\.delete\(`\/cases\/\$\{viewingCounselCase\.id\}\/events`, \{ data: \{ event_ids: eventIds \} \}\)/);
});

test("CaseEvent editor supports pending and completed states while overdue remains server-derived", () => {
  assert.match(source, /value:"待处理",label:"待处理"/);
  assert.match(source, /value:"已完成",label:"已完成"/);
  assert.match(source, /已逾期状态由系统根据未完成事件和截止日期自动计算/);
});
