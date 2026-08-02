import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/HrCenterPage.tsx', import.meta.url), 'utf8')
const api = await readFile(new URL('../api-server/app/main.py', import.meta.url), 'utf8')

test('请假记录支持显式查询与重置，并只过滤当前员工已经加载的记录', () => {
  assert.match(source, /\[leaveQueryDraft,setLeaveQueryDraft\]=useState\(''\)/)
  assert.match(source, /const leaveRows=kind==='leave'\?rows\.filter/)
  assert.match(source, /setLeaveQuery\(leaveQueryDraft\.trim\(\)\)/)
  assert.match(source, /setLeaveQueryDraft\(''\);setLeaveQuery\(''\)/)
  assert.match(source, /dataSource=\{leaveRows\}/)
  assert.match(source, />查询<\/Button>/)
  assert.match(source, />重置<\/Button>/)
})

test('请假维护按钮服从管理员或部门负责人权限，普通用户保持只读', () => {
  assert.match(source, /function EmployeeSubrecords\(\{employeeId,kind,canManage=true\}/)
  assert.match(source, /kind==='leave'&&!canManage\?readonlyAction:action/)
  assert.match(source, /\(kind!=='leave'\|\|canManage\)&&<Button type="primary"/)
  assert.match(source, /canManage=\{actionAccess\.canProcessStatus\}/)
  assert.match(api, /identity\.get\("role"\) not in \{"admin", "manager"\}/)
})
