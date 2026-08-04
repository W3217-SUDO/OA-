import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const source = await readFile(
  fileURLToPath(new URL('./src/HrCenterPage.tsx', import.meta.url)),
  'utf8',
)

test('employee leave rows expose the legacy view entry before edit/delete', () => {
  assert.match(
    source,
    /const leaveCreateAction=kind==='leave'&&canManage\?\{title:'操作',width:250,[\s\S]*?icon=\{<EyeOutlined\/>\} onClick=\{\(\)=>setViewing\(_r\)\}>查看<\/Button>[\s\S]*?onClick=\{\(\)=>showEditor\(_r\)\}>编辑<\/Button>[\s\S]*?void remove\(_r\.id\)/,
    'leave action should offer 新增/查看/编辑/删除 like the legacy OffWorkDay view entry',
  )
})

test('employee commission rows expose the legacy view entry', () => {
  assert.match(
    source,
    /const commissionRecordAction=kind==='commission'&&!canManage\?readonlyAction:viewAction/,
    'commission action should reuse the view action',
  )
  assert.match(
    source,
    /const viewAction=\{title:'操作',width:190,render:\(_v:any,r:Subrecord\)=><Space size=\{0\}><Button type="link" icon=\{<EyeOutlined\/>\} onClick=\{\(\)=>setViewing\(r\)\}>查看<\/Button>/,
    'view action should expose the read-only 查看 button',
  )
})

test('subrecord view dialog is read-only and covers leave and commission fields', () => {
  assert.match(source, /title=\{`查看\$\{title\}`\}/)
  assert.match(source, /footer=\{<Button onClick=\{\(\)=>setViewing\(null\)\}>关闭<\/Button>\}/)
  assert.match(source, /<Descriptions bordered size="small" column=\{2\} items=\{kind==='leave'\?/)
  assert.match(source, /label:'请假开始',children:viewing\.data\?\.start_date\|\|'—'/)
  assert.match(source, /label:'请假结束',children:viewing\.data\?\.end_date\|\|'—'/)
  assert.match(source, /label:'小时',children:viewing\.data\?\.hours\?\?'—'/)
  assert.match(source, /label:'类型',children:viewing\.data\?\.leave_type\|\|'—'/)
  assert.match(source, /label:'备注',children:viewing\.data\?\.remark\|\|'—'/)
  for (const key of ['base_salary', 'hearing_rate', 'hearing_fixed', 'document_rate', 'document_fixed', 'source_rate', 'source_fixed', 'investigation_rate', 'investigation_fixed', 'quality_rate', 'quality_fixed']) {
    assert.ok(source.includes(`viewing.data?.${key}`), `view dialog should cover ${key}`)
  }
})

test('matter rows do not gain a legacy view entry', () => {
  const action = source.slice(source.indexOf('const action={title'), source.indexOf('const action={title') + source.slice(source.indexOf('const action={title')).indexOf(String.fromCharCode(10)));
  assert.doesNotMatch(action, /setViewing\(r\)/, 'plain matter action should stay 编辑/删除')
  assert.doesNotMatch(source, /const matterCreateAction[\s\S]*?setViewing\(_r\)/, 'matter create action should not add 查看')
})

test('view entry preserves edit and delete contracts', () => {
  assert.match(source, /const viewAction=\{title:'操作',width:190,[\s\S]*?onClick=\{\(\)=>showEditor\(r\)\}>编辑<\/Button>[\s\S]*?onConfirm=\{\(\)=>void remove\(r\.id\)\}/)
})