import test from 'node:test'
import assert from 'node:assert/strict'
import {readFile} from 'node:fs/promises'

const source = await readFile(new URL('./src/HrCenterPage.tsx', import.meta.url), 'utf8')
const api = await readFile(new URL('../api-server/app/main.py', import.meta.url), 'utf8')

test('提成维护入口与记录操作服从人事管理权限，普通员工保持只读', () => {
  assert.match(source, /const commissionRecordAction=kind==='commission'&&!canManage\?readonlyAction:viewAction/)
  assert.match(source, /const canMaintainCommission=kind!=='commission'\|\|canManage/)
  assert.match(source, /\{canMaintainCommission&&\(kind!=='matter'\|\|canManage\)&&\(kind!=='leave'\|\|canManage\)&&<Button type="primary"/)
  assert.match(source, /\{key:'commission',label:'提成设定',children:<EmployeeSubrecords employeeId=\{employeeId\} kind="commission" canManage=\{actionAccess\.canProcessStatus\}\/>\}/)
})

test('提成页保留旧站字段、默认值、案件适用方案和15条分页', () => {
  for (const title of [
    '开始日期', '结束日期', '基本工资', '开庭比例提成', '开庭固定提成',
    '文书比例提成', '文书固定提成', '案源比例提成', '案源固定提成',
    '调查比例提成', '调查固定提成', '品管比例提成', '品管固定提成', '操作',
  ]) {
    assert.match(source, new RegExp(`title:'${title}'`))
  }
  assert.match(source, /const commissionDefaults=\{base_salary:0,hearing_rate:0\.10,hearing_fixed:0,document_rate:0\.05,document_fixed:0,source_rate:0\.05,source_fixed:0,investigation_rate:0\.05,investigation_fixed:0,quality_rate:0\.02,quality_fixed:0\}/)
  assert.match(source, /api\.get\(`\/hr\/\$\{employeeId\}\/performance-for-case\/\$\{performanceCaseId\}`\)/)
  assert.match(source, /pagination=\{\{pageSize:15,current:subrecordPage/)
})

test('提成新建弹窗要求开始日期并可取消，服务端拒绝反向日期与负数', () => {
  assert.match(source, /name="start_date" label="开始" rules=\{\[\{required:true\}\]\}/)
  assert.match(source, /onCancel=\{\(\)=>\{setOpen\(false\);form\.resetFields\(\)\}\}/)
  assert.match(api, /if end and end < start: raise HTTPException\(status_code=422, detail="提成结束不能早于开始"\)/)
  assert.match(api, /if value < 0: raise HTTPException\(status_code=422, detail="提成或工资数值不能为负数"\)/)
})
