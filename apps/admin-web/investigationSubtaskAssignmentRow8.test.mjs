import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
  new URL("./src/InvestigationCenterPage.tsx", import.meta.url),
  "utf8",
);

test("新增调查子任务沿用父调查任务的授权信息", () => {
  assert.match(source, /import \{ INVESTIGATION_REGION_GROUPS \} from "\.\/investigationRegionOptions\.mjs"/);
  assert.match(source, /const investigationTaskScopeGroups = \(data: Record<string, any>\)/);
  assert.match(source, /start_date: target\.data\.authorized_from/);
  assert.match(source, /end_date: target\.data\.authorized_to/);
  assert.match(source, /authorization_scope: String\(target\.data\.authorization_scope \|\| ""\)\.trim\(\)/);
  assert.match(source, /message=\{`授权区域：\$\{taskAuthorizationScope \|\| "未配置"\}`\}/);
  assert.match(source, /description=\{`授权时间：\$\{taskTarget\?\.data\.authorized_from \|\| "未配置"\} 至 \$\{taskTarget\?\.data\.authorized_to \|\| "未配置"\}`\}/);
});

test("调查员和调查区域都从系统受控选项中选择", () => {
  assert.match(source, /label="负责人"[\s\S]*?placeholder="请选择系统人员"[\s\S]*?options=\{casePeopleOptions\.map/);
  assert.match(source, /label="调查省份"[\s\S]*?options=\{taskScopeGroups\.map/);
  assert.match(source, /onChange=\{\(\) => taskForm\.setFieldValue\("city", undefined\)\}/);
  assert.match(source, /label="调查城市"[\s\S]*?options=\{taskCityOptions\.map/);
  assert.doesNotMatch(source, /<Form\.Item label="区县" name="district"><Input \/><\/Form\.Item>/);
  assert.match(source, /province: regionPath\[0\] \|\| v\.province \|\| ""/);
  assert.match(source, /city: regionPath\[1\] \|\| v\.city \|\| ""/);
  assert.match(source, /authorization_scope: regionPath\.length \? "" : v\.authorization_scope \|\| ""/);
  assert.match(source, /return groups;/);
});

test("完成和继续分配分别关闭或保留新增子任务界面，并即时刷新任务表", () => {
  assert.match(source, /const createTask = async \(nextAction: "complete" \| "continue"\)/);
  assert.match(source, /await api\.get\(`\/investigations\/\$\{taskTarget\.id\}\/tasks`\)/);
  assert.match(source, /if \(nextAction === "complete"\) \{[\s\S]*?setTaskTarget\(null\)[\s\S]*?setCreatingSubtask\(false\)/);
  assert.match(source, /onClick=\{\(\) => void createTask\("complete"\)\}[\s\S]*?完成/);
  assert.match(source, /onClick=\{\(\) => void createTask\("continue"\)\}[\s\S]*?继续分配/);
});

console.log("investigation subtask assignment row 8: PASS");
