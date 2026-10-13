import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = ["TaskCenterPage", "TaskList", "TaskActionModals", "TaskDetail"].map(name => fs.readFileSync(new URL(`../../src/tp/${name}.tsx`, import.meta.url), "utf8")).join("\n");

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
  assert.match(source, /canManageAcceptedTask && statusTab === "pending"/);
  assert.match(source, /canManageAcceptedTask && statusTab === "processing"/);
  const acceptedActionBlock = source.slice(source.indexOf('{canManageAcceptedTask && statusTab === "pending"'), source.indexOf("{selectedRows.length > 1"));
  assert.doesNotMatch(acceptedActionBlock, /requestTaskException|申请挂起|申请取消|撤回任务/);
});

test("received task detail exposes legal lifecycle actions and permission-gated cancellation", () => {
  const detailFooter = source.slice(source.indexOf("footer={", source.indexOf('title="案件任务"')), source.indexOf("onCancel={onClose}"));
  assert.match(detailFooter, /接受任务/);
  assert.match(detailFooter, /完成任务/);
  assert.match(detailFooter, /转交任务/);
  assert.doesNotMatch(detailFooter, /申请挂起/);
  assert.match(detailFooter, /props\.canRequestTaskException\(communication\)[\s\S]*?props\.onRequestException\(communication, "取消"\)/);
  assert.match(detailFooter, /props\.canReviewTaskException\(communication\)[\s\S]*?props\.onReviewException\(communication, true\)[\s\S]*?props\.onReviewException\(communication, false\)/);
  assert.match(source, /row\.exception_request\?\.requested_by !== profile\.username/);
  assert.match(source, /api\.post\(`\/tasks\/\$\{row\.id\}\/exception-review`, \{ approved, comment: comment\.trim\(\) \}\)/);
});

test("list and mobile detail share manual maintenance and explicit phase-task restart", () => {
  assert.match(source, /!selected\?\.auto_completed \|\| selected\.phase_completion_required/);
  assert.match(source, /!communication\.auto_completed \|\| communication\.phase_completion_required/);
  assert.match(source, /props\.canMaintainTask\(selected\)[\s\S]*?props\.onMaintainTask\(selected\)/);
  assert.match(source, /props\.canMaintainTask\(communication\)[\s\S]*?props\.onMaintainTask\(communication\)/);
  assert.match(source, /api\.post\("\/tasks\/batch-update", \{[\s\S]*?task_ids: \[maintenance\.id\]/);
  assert.match(source, /value\.isAfter\(dayjs\(\)\.add\(30, "day"\), "day"\)/);
  assert.match(source, /onReviewException\(selected, true\)/);
  assert.match(source, /onReviewException\(selected, false\)/);
});
