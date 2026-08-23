import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/HrCenterPage.tsx', import.meta.url), 'utf8')

test('employee archive writes remain guarded while preview and download stay available', () => {
  const archiveBranch = source.match(/if\(kind==='archive'\)\{([\s\S]*?)\n  \}/)
  assert.ok(archiveBranch)
  assert.match(archiveBranch[1], /canManage\?<Popconfirm/)
  assert.match(archiveBranch[1], /\{canManage&&<Button type="primary" icon=\{<UploadOutlined\/>\}/)
  assert.match(archiveBranch[1], /void preview\(r\)/)
  assert.match(archiveBranch[1], /void download\(r\)/)
})

test('employee archive tab receives the shared management guard in read and edit contexts', () => {
  assert.match(source, /canManageSubrecords=actionAccess\.canProcessStatus/)
  assert.match(source, /kind="archive" canManage=\{canManageSubrecords\}/)
  assert.match(source, /employeeTabs\(viewing\.id,details,false\)/)
  assert.match(source, /employeeTabs\(editingEmployee\.id,[\s\S]*,true\)/)
})

test('employee archive retains bounded paging and upload reset behavior', () => {
  assert.match(source, /pagination=\{\{pageSize:15,showSizeChanger:true,pageSizeOptions:\[10,15,20,50,100,200\]/)
  assert.match(source, /setUploadOpen\(false\);setUploadFile\(null\)/)
})
