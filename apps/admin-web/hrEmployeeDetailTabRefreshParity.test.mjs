import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/HrCenterPage.tsx', import.meta.url), 'utf8')
const legacyBindings = await readFile(new URL('../../../旧系统归档源码/SH.CRM.WEB/Scripts/HR/Staff/HR.Staff.Create.js', import.meta.url), 'utf8')

test('employee detail tabs refresh their active subrecord list like the legacy staff tabs', () => {
  assert.match(legacyBindings, /#btnStaffOffWorkDayList[\s\S]*?staff\.Staff\.OffWorkDay\.List\(false\)/)
  assert.match(legacyBindings, /#btnStaffFileList[\s\S]*?staff\.Staff\.Files\.Layout\(\)/)
  assert.match(legacyBindings, /#btnStaffEventList[\s\S]*?staff\.Staff\.Events\.Layout\(\)/)
  assert.match(source, /useEffect\(\(\)=>\{setSubrecordPage\(1\);setLeaveQueryDraft\(''\);setLeaveQuery\(''\);void load\(\)\},\[employeeId,kind\]\)/)
  assert.match(source, /<Tabs activeKey=\{detailTab\} onChange=\{setDetailTab\} items=/)
  assert.match(source, /key:'leave'[\s\S]*?destroyOnHidden:true/)
  assert.match(source, /key:'archive'[\s\S]*?destroyOnHidden:true/)
  assert.match(source, /key:'matter'[\s\S]*?destroyOnHidden:true/)
  assert.match(source, /key:'commission'[\s\S]*?destroyOnHidden:true/)
  assert.match(source, /kind="leave" canManage=\{canManageSubrecords\}\/>/)
  assert.match(source, /kind="archive" canManage=\{canManageSubrecords\}\/>/)
  assert.match(source, /kind="matter" canManage=\{canManageSubrecords\}\/>/)
  assert.match(source, /kind="commission" canManage=\{canManageSubrecords\}\/>/)
})
