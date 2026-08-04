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

const querySubmit = block('const runEmployeeQuery=', 'const filtered=')
const listPanel = block('const listPanel=', 'const basicFields:')

test('employee query starts from page one and clears stale batch deletion selection', () => {
  assert.ok(querySubmit.includes('setEmployeePage(1)'), 'query should restart at the first legacy page')
  assert.ok(querySubmit.includes('setSelectedEmployeeIds([])'), 'query should clear row selections from prior filters/pages')
  assert.ok(querySubmit.includes('setBatchDeletionImpact(null)'), 'query should close stale batch deletion impact')
  assert.ok(querySubmit.includes('setDeletingEmployee(null)') && querySubmit.includes('setDeletionImpact(null)'), 'query should clear stale single-delete impact')
  assert.ok(querySubmit.includes('void load(1)'), 'query should reload the first page after cleanup')
})

test('employee query button uses the cleanup helper instead of inline load', () => {
  assert.ok(listPanel.includes('onClick={runEmployeeQuery}'), 'query button should use the cleanup helper')
  assert.ok(!listPanel.includes('onClick={()=>{setEmployeePage(1);void load(1)}}'), 'query button must not bypass cleanup')
})
