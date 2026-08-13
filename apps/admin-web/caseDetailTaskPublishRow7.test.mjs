import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const taskTabStart = source.indexOf('{key:"tasks",label:"案件任务"');
const taskTabEnd = source.indexOf('{key:"customer-tasks",label:"客户任务"', taskTabStart);

assert.ok(taskTabStart >= 0 && taskTabEnd > taskTabStart, "案件详情必须保留案件任务页签");
const taskTab = source.slice(taskTabStart, taskTabEnd);

assert.match(
  taskTab,
  /counselDetailCapabilities\.can_create_case_task&&<div className="case-legacy-bottom-actions"><Button onClick=\{\(\)=>openCaseTaskCreator\(viewingCounselCase\)\}>发布任务<\/Button><\/div>/,
  "案件任务页签底部必须仅向有创建权限的人员展示发布任务入口",
);

assert.match(
  source,
  /const openCaseTaskCreator = \(row: CaseRow\) => \{\s*if \(!getCaseCapability\(row\)\.can_create_case_task\) return message\.warning/,
  "发布入口必须在打开前再次校验案件任务创建权限",
);
assert.match(
  source,
  /title=\{`发布案件任务：\$\{caseTaskCreateCase\?\.serial_no \|\| ""\}`\}[\s\S]*?okText="发布任务"[\s\S]*?onOk=\{createCaseTask\}/,
  "发布入口必须复用案件任务创建弹窗",
);
assert.match(
  source,
  /await api\.post\("\/tasks", \{[\s\S]*?customer: targetCase\.customer,[\s\S]*?case_no: targetCase\.serial_no,[\s\S]*?source: "案件任务",[\s\S]*?\}\);/,
  "发布任务必须自动绑定当前案件与客户",
);
assert.match(
  source,
  /if \(taskCase\) await openCaseTasks\(targetCase\);\s*else if \(viewingCounselCase\) await openCounselDetail\(targetCase\);/,
  "发布成功后必须刷新当前案件详情的任务列表",
);

console.log("case detail task publish row 7: PASS");
