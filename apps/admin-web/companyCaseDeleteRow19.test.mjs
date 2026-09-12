import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = ["./src/legal/CaseCenterPage.tsx", "./src/legal/services/workflowActions.tsx"]
  .map(path => fs.readFileSync(new URL(path, import.meta.url), "utf8")).join("\n");
const backend = fs.readFileSync(new URL("../api-server/app/areas/legal/router.py", import.meta.url), "utf8");

test("公司案件提供受权限控制的删除入口", () => {
  assert.match(source, /const canDeleteSelectedCompanyCase = isCompanyCaseListRoute\(initialView\)/);
  assert.match(source, /\["admin", "manager"\]\.includes\(profile\.role \|\| ""\)/);
  assert.match(source, /selectedCases\.every\(\(row\) => getCaseCapability\(row\)\.can_delete_case\)/);
  assert.match(source, /api\.post\("\/cases\/batch-delete", \{ case_ids: caseIds \}\)/);
  assert.match(source, /案件任务、附件、费用、排期和操作记录也会一并删除/);
});

test("后端专用删除接口只允许管理员或管理人员并拒绝归档案件", () => {
  assert.match(backend, /@router\.delete\(f"\{settings\.api_prefix\}\/cases\/\{\{case_id\}\}"/);
  assert.match(backend, /identity\.get\("role"\) not in \{"admin", "manager"\}/);
  assert.match(backend, /record\.status in \{"已归档", "已合并"\}/);
  assert.match(backend, /BusinessRecord\.data\["case_id"\]\.as_integer\(\) == case_id/);
});
