import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = (await Promise.all([
  "./src/legal/CaseCenterPage.tsx",
  "./src/legal/CaseDetail/CaseTasksPanel.tsx",
  "./src/legal/services/workflowActions.tsx",
].map((path) => readFile(new URL(path, import.meta.url), "utf8")))).join("\n");
const taskTabStart = source.indexOf('{key:"tasks",label:"案件任务"');
const taskTabEnd = source.indexOf('{key:"customer-tasks",label:"客户任务"', taskTabStart);

assert.ok(taskTabStart >= 0 && taskTabEnd > taskTabStart, "案件详情必须保留案件任务页签");
assert.match(
  source.slice(taskTabStart, taskTabEnd),
  /<CaseCaseTasksPanel[\s\S]*?capabilities=\{counselDetailCapabilities\}[\s\S]*?viewingCase=\{viewingCounselCase\}[\s\S]*?onOpenTask=\{openRelatedTask\}[\s\S]*?onCreateTask=\{openCaseTaskCreator\}/,
  "案件详情必须把权限、目标案件和真实处理器一并传给案件任务面板",
);
assert.match(
  source,
  /capabilities\.can_create_case_task&&<div className="case-legacy-bottom-actions"><Button onClick=\{\(\)=>viewingCase && onCreateTask\(viewingCase\)\}>发布任务<\/Button><\/div>/,
  "案件任务面板必须以权限门禁将当前案件传给创建处理器",
);

assert.match(
  source,
  /const openCaseTaskCreator = \(row: CaseRow\) => \{\s*if \(!getCaseCapability\(row\)\.can_create_case_task\) return message\.warning/,
  "发布入口必须在打开前再次校验案件任务创建权限",
);
assert.match(
  source,
  /<Drawer open=\{Boolean\(caseTaskCreateCase\)\}[\s\S]*?title="案件任务"[\s\S]*?<Button type="primary" onClick=\{createCaseTask\}>确定<\/Button>/,
  "发布入口必须复用案件任务创建抽屉",
);
assert.match(
  source,
  /await api\.post\("\/tasks", \{[\s\S]*?customer: targetCase\.customer,[\s\S]*?case_no: targetCase\.serial_no,[\s\S]*?source: taskKind,[\s\S]*?\}\);/,
  "发布任务必须自动绑定当前案件与客户",
);
assert.match(
  source,
  /if \(taskCase\)\s*await openCaseTasks\(targetCase\);\s*else if \(viewingCounselCase\)\s*await openCounselDetail\(targetCase\);/,
  "发布成功后必须刷新当前案件详情的任务列表",
);

assert.match(
  source,
  /key === "tasks" && viewingCounselCase[\s\S]*?loadCounselDetailTasksPage\(viewingCounselCase, CASE_TASK_DEFAULT_PAGE, CASE_TASK_DEFAULT_PAGE_SIZE\)[\s\S]*?key === "customer-tasks" && viewingCounselCase[\s\S]*?loadCounselDetailCustomerTasksPage\(viewingCounselCase, CASE_TASK_DEFAULT_PAGE, CASE_TASK_DEFAULT_PAGE_SIZE\)/,
  "case and customer task tabs must refresh their own persisted task list",
);

console.log("case detail task publish row 7: PASS");
