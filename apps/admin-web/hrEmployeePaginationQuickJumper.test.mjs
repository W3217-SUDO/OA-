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
  const end = source.indexOf(endNeedle, start)
  assert.notEqual(end, -1, 'missing source end anchor: ' + endNeedle)
  return source.slice(start, end)
}

test('employee list keeps the legacy GO quick-jump pagination affordance', () => {
  const employeeList = block('className="employee-list-table"', 'scroll={{x:1710}}')

  assert.ok(
    employeeList.includes("showQuickJumper:{goButton:'GO'}"),
    'employee list pagination should expose the old cPaging GO jump control',
  )
})

test('employee detail subrecord pages keep the legacy GO quick-jump pagination affordance', () => {
  const subrecordList = block('dataSource={leaveRows} pagination={{', '<Modal open={open}')

  assert.ok(
    subrecordList.includes("showQuickJumper:{goButton:'GO'}"),
    'leave, matter, and commission subrecord pagination should expose the old cPaging GO jump control',
  )
})
