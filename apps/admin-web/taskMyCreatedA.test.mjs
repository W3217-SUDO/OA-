import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

let source = ''
for (const name of ['TaskCenterPage.tsx', 'TaskList.tsx', 'TaskCreateModal.tsx', 'TaskDetail.tsx', 'TaskActionModals.tsx', 'types.ts', 'constants.ts']) {
  source += await readFile(new URL(`./src/tp/${name}`, import.meta.url), 'utf8')
}
let api = ''
for (const name of ['areas/tp/router.py', 'core/tasks.py', 'models_shared.py']) {
  api += await readFile(new URL(`../api-server/app/${name}`, import.meta.url), 'utf8')
}

test('事务中心我的任务 exposes list filters, pagination, create/detail and attachment controls', () => {
  assert.match(source, /任务编号/)
  assert.match(source, /任务标题/)
  assert.match(source, /任务内容/)
  assert.match(source, /pageSize/)
  assert.match(source, /重置/)
  assert.match(source, /新增任务/)
  assert.match(source, /发起任务/)
  assert.match(source, /选择任务资料附件/)
  assert.match(source, /选择反馈附件/)
  assert.match(source, /撤回任务/)
})

test('事务中心任务 API validates initiator-only withdrawal, reasons, batch lifecycle and material uploads', () => {
  // Legacy TaskDetail.cshtml comments out deletion links; TaskList has no active delete command.
  assert.match(api, /tasks\/batch-lifecycle/)
  assert.match(api, /只有任务发起人可以撤回任务/)
  assert.match(api, /只有待接收或处理中的任务可以撤回/)
  assert.match(api, /撤回任务必须填写撤回原因/)
  assert.match(api, /批量撤回任务必须填写撤回原因/)
  assert.match(api, /只有任务参与人可以上传任务资料附件/)
  assert.match(api, /请至少选择一个任务资料附件/)
  assert.match(api, /attachments\.append\(attachment\)/)
})

test('事务中心我发起的任务 restores the legacy batch acceptance action with dedicated server validation', () => {
  assert.match(source, /批量验收任务/)
  assert.match(source, /TaskBatchLifecycleAction = "accept" \| "complete" \| "confirm" \| "handoff" \| "withdraw"/)
  assert.match(api, /\^\(accept\|complete\|confirm\|handoff\|withdraw\)\$/)
  assert.match(api, /仅任务发起人可以批量确认完成/)
  assert.match(api, /当前状态不能批量确认/)
})

test('事务中心 batch selection trusts the server-authorized task page instead of re-filtering it locally', () => {
  assert.match(source, /\(\) => tasks\.filter\(\(row\) => selectedKeys\.includes\(row\.id\)\)/)
})

test('事务中心未读空列表仍显示标记已读，未选择时只提示且不调用写接口', () => {
  assert.match(source, /\{isUnread && \(\s*<Button[\s\S]*?标记已读/)
  assert.doesNotMatch(source, /hideTaskFooter[\s\S]*?isUnread \|\|/)
  const handler = source.slice(source.indexOf('const markSelectedUnreadTasksRead'), source.indexOf('const taskBatchLabels'))
  assert.match(handler, /if \(!selectedRows\.length\) \{[\s\S]*?message\.warning\([\s\S]*?return;[\s\S]*?\}/)
  assert.ok(handler.indexOf('return;') < handler.indexOf('api.post("/tasks/messages/batch-read"'))
})

test('我发起的任务空状态页隐藏底部新增和更多操作', () => {
  assert.match(source, /hideTaskFooter[\s\S]*?\(isCreated \|\|/)
  assert.match(source, /hideTaskFooter[\s\S]*?isAccepted \|\|/)
})
