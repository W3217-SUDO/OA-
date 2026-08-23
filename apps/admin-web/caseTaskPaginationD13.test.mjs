import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("case task loaders request server pages for each task scope", () => {
  assert.match(source, /const CASE_TASK_DEFAULT_PAGE = 1;/);
  assert.match(source, /const CASE_TASK_DEFAULT_PAGE_SIZE = 15;/);
  assert.match(source, /const loadCaseTasksPage = async \([\s\S]*?params: \{ page: nextPage, page_size: nextPageSize \},[\s\S]*?applyCaseTaskPageState\(data, nextPage, nextPageSize\);/);
  assert.match(source, /const loadCounselDetailTasksPage = async \([\s\S]*?params: \{ page: nextPage, page_size: nextPageSize, scope: "case" \},[\s\S]*?applyCounselDetailTaskPageState\(data, nextPage, nextPageSize\);/);
  assert.match(source, /const loadCounselDetailCustomerTasksPage = async \([\s\S]*?params: \{ page: nextPage, page_size: nextPageSize, scope: "customer" \},[\s\S]*?applyCounselDetailCustomerTaskPageState\(data, nextPage, nextPageSize\);/);
  assert.match(source, /key === "customer-tasks"[\s\S]*?loadCounselDetailCustomerTasksPage\(viewingCounselCase, CASE_TASK_DEFAULT_PAGE, CASE_TASK_DEFAULT_PAGE_SIZE\)/);
});

test("task page responses retain total, page, page size, and page count", () => {
  assert.match(source, /type CaseTaskPageState = \{ items: TaskRow\[\]; total: number; page: number; pageSize: number; pages: number \};/);
  assert.match(source, /setCaseTasks\(normalized\.items\);[\s\S]*?setCaseTaskPage\(normalized\.page\);[\s\S]*?setCaseTaskTotal\(normalized\.total\);/);
  assert.match(source, /setCounselDetailTasks\(normalized\.items\);[\s\S]*?setCounselDetailTaskPage\(normalized\.page\);[\s\S]*?setCounselDetailTaskTotal\(normalized\.total\);/);
  assert.match(source, /setCounselDetailCustomerTasks\(normalized\.items\);[\s\S]*?setCounselDetailCustomerTaskPage\(normalized\.page\);[\s\S]*?setCounselDetailCustomerTaskTotal\(normalized\.total\);/);
});

test("case and customer task tables use independent server pagination", () => {
  assert.match(source, /const caseTaskPagination = \{[\s\S]*?loadCaseTasksPage\(taskCase, nextPage, nextPageSize\);/);
  assert.match(source, /const counselDetailTaskPagination = \{[\s\S]*?loadCounselDetailTasksPage\(viewingCounselCase, nextPage, nextPageSize\);/);
  assert.match(source, /const counselDetailCustomerTaskPagination = \{[\s\S]*?loadCounselDetailCustomerTasksPage\(viewingCounselCase, nextPage, nextPageSize\);/);
  assert.match(source, /key:"tasks"[\s\S]*?pagination=\{counselDetailTaskPagination\}/);
  assert.match(source, /key:"customer-tasks"[\s\S]*?pagination=\{counselDetailCustomerTaskPagination\}/);
  assert.match(source, /dataSource=\{counselDetailCustomerTasks\}/);
});
