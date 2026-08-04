import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const source = await readFile(
  fileURLToPath(new URL('./src/SystemCenterPage.tsx', import.meta.url)),
  'utf8',
)

function block(startNeedle, endNeedle) {
  const start = source.indexOf(startNeedle)
  assert.notEqual(start, -1, 'missing source anchor: ' + startNeedle)
  const end = source.indexOf(endNeedle, start)
  assert.notEqual(end, -1, 'missing source end anchor: ' + endNeedle)
  return source.slice(start, end)
}

test('system user editor loads active HR departments for the legacy department picker', () => {
  const helper = block('const loadUserDepartments = async', 'const loadRoles = async')
  const viewLoad = block('useEffect(() => {', 'const saveConfig = async')

  assert.ok(helper.includes('api.get("/hr/departments"'), 'system user editor should reuse the existing HR departments endpoint')
  assert.ok(helper.includes('active_only: true'), 'department picker should exclude inactive departments')
  assert.ok(helper.includes('setUserDepartmentOptions'), 'department options should be retained for the account editor')
  assert.ok(viewLoad.includes('void loadUserDepartments()'), 'opening system user management should load department options')
})

test('system user department uses a searchable controlled picker instead of free text', () => {
  const departmentItem = block('label="部门"', '</Form.Item>')

  assert.ok(departmentItem.includes('<Select'), 'department should use a select control')
  assert.ok(departmentItem.includes('showSearch'), 'department picker should support legacy lookup behavior')
  assert.ok(departmentItem.includes('optionFilterProp="label"'), 'department picker should search department labels')
  assert.ok(departmentItem.includes('options={userDepartmentOptions}'), 'department picker should bind active HR department options')
  assert.ok(!departmentItem.includes('<Input />'), 'department must not accept arbitrary free text')
})
