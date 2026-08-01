import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/BusinessPage.tsx', import.meta.url), 'utf8')

test('事项记录列表 exposes query, reset, pagination and detail/actions', () => {
  assert.match(source, /load=async\(nextPage=page,nextKeyword=keyword,nextRecordStatus=recordStatus\)/)
  assert.match(source, /record_status:nextRecordStatus/)
  assert.match(source, /void load\(1,'',''\)/)
  assert.match(source, /pagination=\{\{current:page,total,pageSize:20/)
  assert.match(source, /openDetails\(row\)/)
  assert.match(source, /startEdit\(row\)/)
  assert.match(source, /onConfirm=\{\(\)=>remove\(row\.id\)\}/)
})
