import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/HrCenterPage.tsx', import.meta.url), 'utf8')
const legacy = await readFile(new URL('../../../旧系统归档源码/SH.CRM.WEB/Areas/HR/Views/Staff/PartialView/OffWorkDayList.cshtml', import.meta.url), 'utf8')
const legacyBindings = await readFile(new URL('../../../旧系统归档源码/SH.CRM.WEB/Scripts/HR/Staff/HR.Staff.Create.js', import.meta.url), 'utf8')

test('旧端请假行级新增入口在新端继续可用', () => {
  assert.match(legacy, /btn_staffoffworkday_add/)
  assert.match(legacyBindings, /btn_staffoffworkday_add[\s\S]*?staff\.Staff\.OffWorkDay\.Open/)
  assert.match(source, /const leaveCreateAction=kind==='leave'[\s\S]*?PlusOutlined[\s\S]*?showEditor\(\)/)
  assert.match(source, /const leaveDisplayAction=kind==='leave'[\s\S]*?leaveCreateAction/)
})
