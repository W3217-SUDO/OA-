import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { normalizeEmployeeIds } from './src/employeeBulkDelete.mjs'

const source = await readFile(
  fileURLToPath(new URL('./src/HrCenterPage.tsx', import.meta.url)),
  'utf8',
)

function block(startNeedle, endNeedle) {
  const start = source.indexOf(startNeedle)
  assert.notEqual(start, -1, 'missing source anchor: ' + startNeedle)
  const end = endNeedle ? source.indexOf(endNeedle, start) : source.length
  assert.notEqual(end, -1, 'missing source end anchor: ' + endNeedle)
  return source.slice(start, end)
}

const cleanupBlock = block('const openDeletionBlockerCleanup', 'const openPasswordReset=')
const deletionModal = block('const deletionModal=', 'const batchDeletionModal=')
const batchDeletionModal = block('const batchDeletionModal=', 'if(!isNew)return')

const EMPLOYEE_SUBRECORD = '员工附属记录'
const EMPLOYEE_ARCHIVE_FILE = '员工档案文件'
const BUSINESS_LINK = '业务关联'
const SYSTEM_USER_MANAGEMENT = '系统用户管理'
const PROTECTED_LOGIN = '受保护登录账号'
const CASE_REFERENCE = '案件'
const LEAVE = '请假'
const MATTER = '事项'
const COMMISSION = '提成'
const CLEANUP = '去清理'

function missingTerms(text, checks) {
  return checks
    .filter(([needle]) => !text.includes(needle))
    .map(([, label]) => label)
}

test('single employee deletion impact keeps old business-occupied guard and explains every blocker class', () => {
  assert.ok(source.includes('/hr/employees/${row.id}/deletion-impact'), 'single delete should ask backend for deletion impact before deleting')
  assert.ok(deletionModal.includes('disabled:!deletionImpact?.deletable'), 'occupied employees must not be directly deletable')
  assert.ok(deletionModal.includes('blocker.records.join'), 'single modal should show blocker record identifiers')
  assert.deepEqual(missingTerms(deletionModal, [
    [EMPLOYEE_SUBRECORD, 'employee subrecords'],
    [EMPLOYEE_ARCHIVE_FILE, 'employee archive files'],
    [BUSINESS_LINK, 'old business-occupied guard'],
    [SYSTEM_USER_MANAGEMENT, 'System User Management guidance'],
    [PROTECTED_LOGIN, 'protected login account blocker'],
    [CASE_REFERENCE, 'case reference blocker'],
  ]), [])
})

test('single employee deletion impact can jump to cleanable HR tabs', () => {
  assert.ok(deletionModal.includes('openDeletionBlockerCleanup(blocker)'), 'cleanable HR blockers should expose a cleanup action')
  assert.ok(deletionModal.includes(CLEANUP), 'cleanup action should be visible to admins')
  assert.ok(cleanupBlock.includes(EMPLOYEE_ARCHIVE_FILE) && cleanupBlock.includes("'archive'"), 'archive blockers should jump to the archive tab')
  assert.ok(cleanupBlock.includes('/^leave#/i') && cleanupBlock.includes("'leave'"), 'leave blockers should jump to the leave tab')
  assert.ok(cleanupBlock.includes('/^matter#/i') && cleanupBlock.includes("'matter'"), 'matter blockers should jump to the matter tab')
  assert.ok(cleanupBlock.includes('/^commission#/i') && cleanupBlock.includes("'commission'"), 'commission blockers should jump to the commission tab')
  assert.ok(cleanupBlock.includes(LEAVE) || cleanupBlock.includes('/^leave#/i'), 'cleanup routing should cover leave records')
  assert.ok(cleanupBlock.includes(MATTER) || cleanupBlock.includes('/^matter#/i'), 'cleanup routing should cover matter records')
  assert.ok(cleanupBlock.includes(COMMISSION) || cleanupBlock.includes('/^commission#/i'), 'cleanup routing should cover commission records')
})

test('batch employee deletion impact explains blockers with record identifiers and action paths', () => {
  assert.ok(source.includes('/hr/employees/batch-deletion-impact'), 'batch delete should ask backend for deletion impact before deleting')
  assert.ok(batchDeletionModal.includes('disabled:!batchDeletionImpact?.deletable'), 'batch delete must stay disabled while any employee is occupied')
  assert.ok(batchDeletionModal.includes('blocker.records.join'), 'batch modal should show blocker record identifiers, not only blocker kind')
  assert.deepEqual(missingTerms(batchDeletionModal, [
    [EMPLOYEE_SUBRECORD, 'employee subrecords'],
    [EMPLOYEE_ARCHIVE_FILE, 'employee archive files'],
    [PROTECTED_LOGIN, 'protected login account blocker'],
    [BUSINESS_LINK, 'old business-occupied guard'],
    [CASE_REFERENCE, 'case reference blocker'],
  ]), [])
  assert.ok(
    batchDeletionModal.includes('openDeletionBlockerCleanup') || batchDeletionModal.includes(CLEANUP),
    'batch modal should provide an action path for cleanable HR blockers',
  )
})

test('empty batch employee selection keeps an explicit no-op prompt', () => {
  assert.throws(
    () => normalizeEmployeeIds([]),
    (error) => error instanceof Error
      && error.message.includes('员工')
      && error.message.includes('选择'),
  )
})
