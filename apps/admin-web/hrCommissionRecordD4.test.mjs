import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/HrCenterPage.tsx', import.meta.url), 'utf8')

test('commission records keep write controls behind the subrecord management guard', () => {
  assert.match(source, /const commissionRecordAction=kind==='commission'&&!canManage\?readonlyAction:viewAction/)
  assert.match(source, /const canMaintainCommission=kind!=='commission'\|\|canManage/)
  assert.match(source, /canManageSubrecords=actionAccess\.canProcessStatus/)
})

test('commission tab receives the shared management guard for view and edit contexts', () => {
  assert.match(source, /kind="commission" canManage=\{canManageSubrecords\}/)
  assert.match(source, /employeeTabs\(viewing\.id,details,false\)/)
  assert.match(source, /employeeTabs\(editingEmployee\.id,[\s\S]*,true\)/)
})

test('commission records keep defaults, case lookup, and readable paging', () => {
  assert.match(source, /const commissionDefaults=\{base_salary:0,hearing_rate:0\.10,hearing_fixed:0,document_rate:0\.05,document_fixed:0,source_rate:0\.05,source_fixed:0,investigation_rate:0\.05,investigation_fixed:0,quality_rate:0\.02,quality_fixed:0\}/)
  assert.match(source, /api\.get\(`\/hr\/\$\{employeeId\}\/performance-for-case\/\$\{performanceCaseId\}`\)/)
  assert.match(source, /pagination=\{\{pageSize:15,current:subrecordPage/)
})
