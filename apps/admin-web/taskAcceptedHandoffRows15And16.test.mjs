import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/TaskCenterPage.tsx", import.meta.url), "utf8");

test("rows 15 and 16 use an active employee selector with stable usernames", () => {
  assert.match(source, /api\.get\("\/users\/directory"\)/);
  assert.match(source, /filter\(\(item: DirectoryUser\) => item\.is_active !== false\)/);
  assert.match(source, /value: user\.username/);
  assert.match(source, /label: `\$\{user\.display_name \|\| user\.username\}（\$\{user\.department/);
  assert.match(source, /placeholder="输入姓名或部门搜索"/);
});

test("handoff form displays task times and posts the selected recipient", () => {
  assert.match(source, /label="任务开始时间"[\s\S]*handoff\?\.start_at \|\| handoff\?\.created_at/);
  assert.match(source, /label="任务结束时间"[\s\S]*handoff\?\.end_at \|\| handoff\?\.deadline/);
  assert.match(source, /await api\.post\(`\/tasks\/\$\{handoff\.id\}\/handoff`, values\)/);
});

test("received task actions are state-scoped and do not expose exception requests", () => {
  assert.match(source, /\["待接收", "待处理"\]\.includes\(selected\?\.workflow_status/);
  assert.match(source, /\["待接收", "待处理", "处理中"\]\.includes\(selected\?\.workflow_status/);
  const acceptedActionBlock = source.slice(source.indexOf("{canManageAcceptedTask && [\"待接收\""), source.indexOf("{selectedRows.length > 1"));
  assert.doesNotMatch(acceptedActionBlock, /requestTaskException|申请挂起|申请取消|撤回任务/);
});

test("received task detail exposes only legal lifecycle actions", () => {
  const detailFooter = source.slice(source.indexOf("footer={", source.indexOf('title="案件任务"')), source.indexOf("onCancel={closeCommunication}"));
  assert.match(detailFooter, /接受任务/);
  assert.match(detailFooter, /完成任务/);
  assert.match(detailFooter, /转交任务/);
  assert.doesNotMatch(detailFooter, /申请挂起|申请取消/);
});
