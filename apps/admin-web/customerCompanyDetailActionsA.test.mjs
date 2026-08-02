import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')

test('company customer detail exposes note and document entry actions', () => {
  assert.match(source, /customer-detail-actions/)
  assert.match(source, /新建事项记录/)
  assert.match(source, /上传客户文件/)
})

test('company customer related-data handlers use the persisted customer and refresh the detail', () => {
  assert.match(source, /api\.post\(`\/customers\/\$\{contacts\.id\}\/notes`, v\)/)
  assert.match(source, /await refreshDetail\(\)/)
  assert.match(source, /api\.delete\(`\/customers\/\$\{contacts\.id\}\/notes\/\$\{id\}`\)/)
  assert.match(source, /data\.append\("record_id", String\(contacts\.id\)\)/)
  assert.match(source, /await api\.post\("\/attachments", data\)/)
  assert.match(source, /await api\.get\(`\/attachments\/\$\{file\.id\}\/download`/)
  assert.match(source, /await api\.delete\(`\/attachments\/\$\{id\}`\)/)
})

test('company customer detail exposes guarded delete confirmations for persisted notes and documents', () => {
  assert.match(source, /删除事项记录/)
  assert.match(source, /删除客户文档/)
  assert.match(source, /onConfirm=\{\(\) => deleteNote\(note\.id\)\}/)
  assert.match(source, /onConfirm=\{\(\) => deleteDocument\(attachment\.id\)\}/)
})

test('company customer detail provides an actionable note edit form', () => {
  assert.match(source, /编辑事项记录/)
  assert.match(source, /setEditingNote\(note\)/)
  assert.match(source, /title="编辑事项记录"/)
  assert.match(source, /保存修改/)
})

test('company customer note editor persists through the scoped update route', () => {
  assert.match(source, /api\.put\(`\/customers\/\$\{contacts\.id\}\/notes\/\$\{editingNote\.id\}`, values\)/)
  assert.match(source, /await refreshDetail\(\)/)
  assert.match(source, /onOk=\{updateNote\}/)
})
