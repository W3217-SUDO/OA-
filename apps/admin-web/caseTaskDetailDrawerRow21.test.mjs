import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const openStart = source.indexOf("const loadCaseTaskDetail");
const openEnd = source.indexOf("const openRelatedFee", openStart);
const detailLogic = source.slice(openStart, openEnd);
const drawerStart = source.indexOf('title="任务详情"');
const drawerEnd = source.indexOf('title="案件任务"', drawerStart);
const detailDrawer = source.slice(drawerStart, drawerEnd);

test("row 21 opens the task detail in the case page instead of navigating away", () => {
  assert.ok(openStart > 0 && drawerStart > 0);
  assert.match(detailLogic, /api\.get\(`\/records\/\$\{task\.id\}`\)/);
  assert.match(detailLogic, /api\.get\(`\/tasks\/\$\{task\.id\}\/history`\)/);
  assert.doesNotMatch(detailLogic, /onNavigate|rememberTaskDetailTarget/);
});

test("row 21 restores the legacy detail, history, withdrawal and feedback controls", () => {
  for (const label of ["任务已分派", "任务处理中", "任务完成", "任务验收", "过程记录", "任务资料附件", "留言附件", "撤回任务", "上传附件", "提交留言"]) {
    assert.match(detailDrawer, new RegExp(label));
  }
  assert.match(detailLogic, /\/withdraw/);
  assert.match(detailLogic, /\/feedback/);
  assert.match(detailLogic, /任务反馈附件/);
  assert.match(detailLogic, /任务资料附件/);
});

