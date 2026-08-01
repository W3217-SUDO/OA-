import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/TaskCenterPage.tsx', import.meta.url), 'utf8')
const api = await readFile(new URL('../api-server/app/main.py', import.meta.url), 'utf8')

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

test('事务中心任务 API validates owner/status, withdrawal reason, attachments and precise batch deletion', () => {
  assert.match(api, /batch-delete/)
  assert.match(api, /任务发起人或系统管理员可以撤回任务/)
  assert.match(api, /批量撤回任务必须填写撤回原因/)
  assert.match(api, /任务存在子任务，不能删除/)
  assert.match(api, /file_attachments/) 
  assert.match(api, /record\.module == "task"/) 
})
