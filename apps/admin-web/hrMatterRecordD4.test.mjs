import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/HrCenterPage.tsx', import.meta.url), 'utf8')

test('matter editor captures only the editable matter content', () => {
  const matterForm = source.match(/kind==='matter'\?<>\s*([\s\S]*?)<\/>:<><div className="commission-form-grid">/)
  assert.ok(matterForm, 'matter form branch is present')
  assert.match(matterForm[1], /name="content"/)
  assert.doesNotMatch(matterForm[1], /name="operation_date"/)
})

test('matter maintenance uses the same HR management gate as leave records', () => {
  assert.match(source, /const recordAction=kind==='leave'&&!canManage\?readonlyAction:action/)
  assert.match(source, /const matterRecordAction=kind==='matter'&&!canManage\?readonlyAction:recordAction/)
  assert.match(source, /\(kind!=='matter'\|\|canManage\)&&\(kind!=='leave'\|\|canManage\)&&<Button type="primary"/)
  assert.match(source, /const employeeTabs=.*canManageSubrecords=actionAccess\.canProcessStatus/)
  assert.match(source, /kind="matter" canManage=\{canManageSubrecords\}/)
})

test('matter list retains client paging without a matter query field', () => {
  assert.match(source, /pagination=\{\{pageSize:15,current:subrecordPage/)
  assert.doesNotMatch(source, /matterQuery/)
})
