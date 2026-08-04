import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./src/TaskCenterPage.tsx", import.meta.url), "utf8");
const tick = String.fromCharCode(96);
const endpoint = "api.get(" + tick + "/cases/" + "$" + "{record.id}" + "/tasks" + tick + ", {";

test("TaskCenter case task drawer requests server page/page_size", () => {
  assert.ok(source.includes(endpoint), "case task drawer must request tasks with config");
  assert.match(source, /const CASE_CONTEXT_TASK_DEFAULT_PAGE = 1;/);
  assert.match(source, /const CASE_CONTEXT_TASK_DEFAULT_PAGE_SIZE = 15;/);
  assert.match(source, /const loadCaseContextTasksPage = async \([\s\S]*params: \{ page: nextPage, page_size: nextPageSize \},[\s\S]*applyCaseContextTaskPageState\(data, nextPage, nextPageSize\);/);
  assert.match(source, /await loadCaseContextTasksPage\(record, CASE_CONTEXT_TASK_DEFAULT_PAGE, CASE_CONTEXT_TASK_DEFAULT_PAGE_SIZE\);/);
});

test("TaskCenter case task drawer consumes pagination metadata", () => {
  assert.match(source, /type CaseContextTaskPageState = \{ items: TaskRow\[\]; total: number; page: number; pageSize: number; pages: number \};/);
  assert.match(source, /const items = Array\.isArray\(payload\?\.items\) \? payload\.items : \[\];/);
  assert.match(source, /const total = Number\.isFinite\(Number\(payload\?\.total\)\) \? Number\(payload\.total\) : items\.length;/);
  assert.match(source, /Number\.isFinite\(Number\(payload\?\.page_size\)\)/);
  assert.match(source, /Number\.isFinite\(Number\(payload\?\.page\)\)/);
  assert.match(source, /Number\.isFinite\(Number\(payload\?\.pages\)\)/);
  assert.match(source, /setCaseTasks\(normalized\.items\);[\s\S]*setCaseTaskContextMeta\(\{[\s\S]*total: normalized\.total,[\s\S]*page: normalized\.page,[\s\S]*pageSize: normalized\.pageSize,[\s\S]*pages: normalized\.pages,/);
});

test("TaskCenter case task drawer uses server pagination instead of first page only", () => {
  assert.match(source, /const caseTaskContextPagination = \{[\s\S]*current: caseTaskContextMeta\.page,[\s\S]*pageSize: caseTaskContextMeta\.pageSize,[\s\S]*total: caseTaskContextMeta\.total,[\s\S]*loadCaseContextTasksPage\(caseContext\.record, nextPage, nextPageSize\);/);
  const drawerIndex = source.indexOf("dataSource={caseTasks}");
  assert.notEqual(drawerIndex, -1, "case task drawer table must render caseTasks");
  const drawerBlock = source.slice(Math.max(0, drawerIndex - 500), drawerIndex + 500);
  assert.match(drawerBlock, /pagination=\{caseTaskContextPagination\}/);
  assert.doesNotMatch(drawerBlock, /pagination=\{false\}/);
});
