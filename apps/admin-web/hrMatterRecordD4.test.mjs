import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/HrCenterPage.tsx', import.meta.url), 'utf8')
const api = await readFile(new URL('../api-server/app/main.py', import.meta.url), 'utf8')

test('事项弹窗只采集旧站可编辑的事项内容，操作日期由服务端生成', () => {
  const matterForm = source.match(/kind==='matter'\?<>\s*([\s\S]*?)<\/>:<><div className="commission-form-grid">/)
  assert.ok(matterForm, '应能定位事项表单分支')
  assert.match(matterForm[1], /name="content"/)
  assert.doesNotMatch(matterForm[1], /name="operation_date"/)
  assert.match(api, /operation_date = str\(data\.get\("operation_date"\) or date\.today\(\)\)/)
})

test('事项维护按钮与请假记录使用相同的人事管理权限', () => {
  assert.match(source, /const recordAction=kind==='leave'&&!canManage\?readonlyAction:action/)
  assert.match(source, /const matterRecordAction=kind==='matter'&&!canManage\?readonlyAction:recordAction/)
  assert.match(source, /\(kind!=='matter'\|\|canManage\)&&\(kind!=='leave'\|\|canManage\)&&<Button type="primary"/)
  assert.match(source, /\{key:'matter',label:'事项记录',children:<EmployeeSubrecords employeeId=\{employeeId\} kind="matter" canManage=\{actionAccess\.canProcessStatus\}\/>\}/)
})

test('事项列表保持旧站实证的15条分页且不新增事项查询栏', () => {
  assert.match(source, /pagination=\{\{pageSize:15,current:subrecordPage/)
  assert.doesNotMatch(source, /matterQuery/)
})
