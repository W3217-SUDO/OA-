import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

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

const querySubmit = block('const runEmployeeQuery=', 'const changeEmployeePage=')
const pageChange = block('const changeEmployeePage=', 'const filtered=')
const listPanel = block('const listPanel=', 'const basicFields:')

test('employee query starts from page one and clears stale deletion selection state', () => {
  assert.ok(querySubmit.includes('setEmployeePage(1)'), 'query should restart at the first legacy page')
  assert.ok(querySubmit.includes('setSelectedEmployeeIds([])'), 'query should clear row selections from prior filters/pages')
  assert.ok(querySubmit.includes('setBatchDeletionImpact(null)'), 'query should close stale batch deletion impact')
  assert.ok(querySubmit.includes('setDeletingEmployee(null)') && querySubmit.includes('setDeletionImpact(null)'), 'query should clear stale single-delete impact')
  assert.ok(querySubmit.includes('setViewing(null)') && querySubmit.includes("setDetailTab('basic')"), 'query should close stale detail view and return it to the basic tab')
  assert.ok(querySubmit.includes('setEditingEmployee(null)') && querySubmit.includes('employeeEditForm.resetFields()'), 'query should close stale edit and approval form state')
  assert.ok(querySubmit.includes('setTransitioningEmployee(null)') && querySubmit.includes('transitionForm.resetFields()'), 'query should close stale HR transition state')
  assert.ok(querySubmit.includes('setResettingEmployee(null)') && querySubmit.includes('passwordResetForm.resetFields()'), 'query should close stale password reset state')
  assert.ok(querySubmit.includes('void load(1)'), 'query should reload the first page after cleanup')
  assert.ok(listPanel.includes('onClick={runEmployeeQuery}'), 'query button should use the cleanup helper')
})

test('employee pagination clears stale deletion selection before loading the requested page', () => {
  assert.ok(pageChange.includes('setSelectedEmployeeIds([])'), 'page change should clear row selections from the previous page')
  assert.ok(pageChange.includes('setBatchDeletionImpact(null)'), 'page change should close stale batch deletion impact')
  assert.ok(pageChange.includes('setDeletingEmployee(null)') && pageChange.includes('setDeletionImpact(null)'), 'page change should clear stale single-delete impact')
  assert.ok(pageChange.includes('setViewing(null)') && pageChange.includes("setDetailTab('basic')"), 'page change should close stale detail view and return it to the basic tab')
  assert.ok(pageChange.includes('setEditingEmployee(null)') && pageChange.includes('employeeEditForm.resetFields()'), 'page change should close stale edit and approval form state')
  assert.ok(pageChange.includes('setTransitioningEmployee(null)') && pageChange.includes('transitionForm.resetFields()'), 'page change should close stale HR transition state')
  assert.ok(pageChange.includes('setResettingEmployee(null)') && pageChange.includes('passwordResetForm.resetFields()'), 'page change should close stale password reset state')
  assert.ok(pageChange.includes('void load(page)'), 'page change should still load the requested page')
  assert.ok(listPanel.includes('onChange:(page)=>changeEmployeePage(page)'), 'pagination should use the cleanup helper')
  assert.ok(!listPanel.includes('onChange:(page)=>void load(page)'), 'pagination must not bypass cleanup with direct load')
})
