import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const lines = source.split(/\r?\n/);
const tick = String.fromCharCode(96);
const endpoint = "api.get(" + tick + "/cases/" + "$" + "{row.id}" + "/tasks" + tick + ", {";
const lineWith = (text) => lines.find((line) => line.includes(text)) || "";

test("D13 case task loaders request server page/page_size", () => {
  assert.ok(source.includes(endpoint), "task endpoint calls must include request config");
  assert.match(source, /const CASE_TASK_DEFAULT_PAGE = 1;/);
  assert.match(source, /const CASE_TASK_DEFAULT_PAGE_SIZE = 15;/);
  assert.match(source, /const loadCaseTasksPage = async \([\s\S]*params: \{ page: nextPage, page_size: nextPageSize \},[\s\S]*applyCaseTaskPageState\(data, nextPage, nextPageSize\);/);
  assert.match(source, /const loadCounselDetailTasksPage = async \([\s\S]*params: \{ page: nextPage, page_size: nextPageSize \},[\s\S]*applyCounselDetailTaskPageState\(data, nextPage, nextPageSize\);/);
  assert.match(source, /await loadCaseTasksPage\(row, CASE_TASK_DEFAULT_PAGE, CASE_TASK_DEFAULT_PAGE_SIZE\);/);
  assert.match(source, /params: \{ page: CASE_TASK_DEFAULT_PAGE, page_size: CASE_TASK_DEFAULT_PAGE_SIZE \},/);
});

test("D13 case task response consumes total/page/page_size/pages", () => {
  assert.match(source, /type CaseTaskPageState = \{ items: TaskRow\[\]; total: number; page: number; pageSize: number; pages: number \};/);
  assert.match(source, /const items = Array\.isArray\(payload\?\.items\) \? payload\.items : \[\];/);
  assert.match(source, /const total = Number\.isFinite\(Number\(payload\?\.total\)\) \? Number\(payload\.total\) : items\.length;/);
  assert.match(source, /Number\.isFinite\(Number\(payload\?\.page_size\)\)/);
  assert.match(source, /Number\.isFinite\(Number\(payload\?\.page\)\)/);
  assert.match(source, /Number\.isFinite\(Number\(payload\?\.pages\)\)/);
  assert.match(source, /setCaseTasks\(normalized\.items\);[\s\S]*setCaseTaskPage\(normalized\.page\);[\s\S]*setCaseTaskPageSize\(normalized\.pageSize\);[\s\S]*setCaseTaskTotal\(normalized\.total\);[\s\S]*setCaseTaskPages\(normalized\.pages\);/);
  assert.match(source, /setCounselDetailTasks\(normalized\.items\);[\s\S]*setCounselDetailTaskPage\(normalized\.page\);[\s\S]*setCounselDetailTaskPageSize\(normalized\.pageSize\);[\s\S]*setCounselDetailTaskTotal\(normalized\.total\);[\s\S]*setCounselDetailTaskPages\(normalized\.pages\);/);
});

test("D13 case task tables use server pagination instead of first-page local pagination", () => {
  assert.match(source, /const caseTaskBasePagination = getCaseTaskPagination\(\);/);
  assert.doesNotMatch(source, /const caseTaskPagination = \{\s*\.\.\.getCaseTaskPagination\(\),/);
  assert.doesNotMatch(source, /const counselDetailTaskPagination = \{\s*\.\.\.getCaseTaskPagination\(\),/);
  assert.match(source, /const caseTaskPagination = \{[\s\S]*current: caseTaskPage,[\s\S]*pageSize: caseTaskPageSize,[\s\S]*total: caseTaskTotal,[\s\S]*pageSizeOptions: caseTaskBasePagination\.pageSizeOptions,[\s\S]*showSizeChanger: caseTaskBasePagination\.showSizeChanger,[\s\S]*loadCaseTasksPage\(taskCase, nextPage, nextPageSize\);/);
  assert.match(source, /const counselDetailTaskPagination = \{[\s\S]*current: counselDetailTaskPage,[\s\S]*pageSize: counselDetailTaskPageSize,[\s\S]*total: counselDetailTaskTotal,[\s\S]*pageSizeOptions: caseTaskBasePagination\.pageSizeOptions,[\s\S]*showSizeChanger: caseTaskBasePagination\.showSizeChanger,[\s\S]*loadCounselDetailTasksPage\(viewingCounselCase, nextPage, nextPageSize\);/);

  const caseTaskTab = lineWith('key:"tasks"');
  const customerTaskTab = lineWith('key:"customer-tasks"');
  assert.match(caseTaskTab, /pagination=\{counselDetailTaskPagination\}/);
  assert.match(customerTaskTab, /pagination=\{counselDetailTaskPagination\}/);
  assert.doesNotMatch(caseTaskTab, /pagination=\{getCaseTaskPagination\(\)\}/);
  assert.doesNotMatch(customerTaskTab, /pagination=\{getCaseTaskPagination\(\)\}/);

  const drawerIndex = lines.findIndex((line) => line.includes("dataSource={caseTasks}"));
  const drawerBlock = lines.slice(Math.max(0, drawerIndex - 8), drawerIndex + 8).join("\n");
  assert.match(drawerBlock, /pagination=\{caseTaskPagination\}/);
  assert.doesNotMatch(drawerBlock, /pagination=\{false\}/);
});
