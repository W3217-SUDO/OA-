import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/HrCenterPage.tsx', import.meta.url), 'utf8')

function block(startNeedle, endNeedle) {
  const start = source.indexOf(startNeedle)
  assert.notEqual(start, -1, 'missing source anchor: ' + startNeedle)
  const end = source.indexOf(endNeedle, start)
  assert.notEqual(end, -1, 'missing source end anchor: ' + endNeedle)
  return source.slice(start, end)
}

test('unsaved employee archive tab stays read-only and cannot open attachment upload', () => {
  const unsavedArchive = block("if(!employeeId&&kind==='archive')", 'const remove=')
  assert.ok(unsavedArchive.includes('employeeSubrecordCreateMessage(employeeId)'), 'unsaved archive should reuse HR subrecord save-first message')
  assert.ok(unsavedArchive.includes('pagination={false}'), 'unsaved archive should render an empty, non-paged table')
  assert.ok(unsavedArchive.includes('<Empty image={Empty.PRESENTED_IMAGE_SIMPLE}'), 'unsaved archive should show an empty-state explanation')
  assert.ok(!unsavedArchive.includes('UploadOutlined'), 'unsaved archive must not show the upload entry')
  assert.ok(!unsavedArchive.includes('setUploadOpen(true)'), 'unsaved archive must not open an upload modal without record_id')
})

test('saved employee archive still supports view, download, upload and delete with HR manage permission', () => {
  const archiveBranch = block("if(kind==='archive')", 'const action=')
  assert.ok(source.includes("kind==='archive'?await api.get('/attachments',{params:{record_id:employeeId,category:"), 'archive list should load employee-file attachments')
  assert.ok(archiveBranch.includes("api.post('/attachments',data"), 'archive upload should use the real attachment endpoint')
  assert.ok(source.includes("api.delete(kind==='archive'?`/attachments/${id}`"), 'archive delete should keep the real attachment delete endpoint')
  assert.ok(source.includes("api.get(`/attachments/${item.id}/download`"), 'archive download should use the real attachment download endpoint')
  assert.ok(archiveBranch.includes('canManage?<Popconfirm'), 'delete remains HR-manage gated')
  assert.ok(archiveBranch.includes('{canManage&&<Button type="primary" icon={<UploadOutlined/>}'), 'upload remains HR-manage gated for saved employees')
})
