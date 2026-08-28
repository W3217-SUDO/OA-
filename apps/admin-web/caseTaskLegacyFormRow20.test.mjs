import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const drawerStart = source.indexOf('<Drawer open={Boolean(caseTaskCreateCase)}');
const drawerEnd = source.indexOf('</Drawer>', drawerStart) + '</Drawer>'.length;
const taskDrawer = source.slice(drawerStart, drawerEnd);

test("row 20 restores the complete legacy task drawer", () => {
  for (const label of ["案件编号", "任务主标题", "优先级", "负责人", "协作人", "任务开始时间", "结束时间", "任务描述", "任务附件"]) {
    assert.match(taskDrawer, new RegExp(label));
  }
  for (const step of ["任务填写", "任务分派", "任务处理", "任务完成"]) assert.match(taskDrawer, new RegExp(step));
  assert.match(taskDrawer, /<Upload multiple fileList=\{caseTaskMaterialFiles\}/);
});

test("row 20 persists task times and uploads selected materials", () => {
  assert.match(source, /start_at: startAt\.format\("YYYY-MM-DDTHH:mm:ss"\)/);
  assert.match(source, /end_at: endAt\.format\("YYYY-MM-DDTHH:mm:ss"\)/);
  assert.match(source, /deadline: formatRequiredDate\(endAt, "结束时间"\)/);
  assert.match(source, /api\.post\(`\/tasks\/\$\{createdTask\.id\}\/materials`, materialBody\)/);
  assert.match(source, /message\.success\(caseTaskMaterialFiles\.length \? `\$\{taskKind\}及附件已创建`/);
});
