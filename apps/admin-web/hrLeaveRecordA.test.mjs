import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/HrCenterPage.tsx', import.meta.url), 'utf8')
const api = await readFile(new URL('../api-server/app/main.py', import.meta.url), 'utf8')

test('员工请假记录 exposes list, client pagination, create/edit/delete and empty employee guard', () => {
  assert.match(source, /kind==='leave'/)
  assert.match(source, /pagination=\{\{pageSize:15/)
  assert.match(source, /showEditor\(r\)/)
  assert.match(source, /onConfirm=\{\(\)=>void remove\(r\.id\)\}/)
  assert.match(source, /employeeSubrecordCreateMessage\(employeeId\)/)
  assert.match(source, /name="start_date"/)
  assert.match(source, /name="end_date"/)
  assert.match(source, /name="hours"/)
  assert.match(source, /name="leave_type"/)
})

test('请假记录 API provides scoped list/create/update/delete and validates dates and hours', () => {
  assert.match(api, /@app\.get\(f"\{settings\.api_prefix\}\/hr\/\{\{employee_id\}\}\/subrecords"\)/)
  assert.match(api, /@app\.post\(f"\{settings\.api_prefix\}\/hr\/\{\{employee_id\}\}\/subrecords"/)
  assert.match(api, /@app\.patch\(f"\{settings\.api_prefix\}\/hr\/\{\{employee_id\}\}\/subrecords\/\{\{subrecord_id\}\}"\)/)
  assert.match(api, /@app\.delete\(f"\{settings\.api_prefix\}\/hr\/\{\{employee_id\}\}\/subrecords\/\{\{subrecord_id\}\}"/)
  assert.match(api, /if end and end < start/)
  assert.match(api, /if hours <= 0/)
  assert.match(api, /identity\.get\("role"\) not in \{"admin", "manager"\}/)
})
