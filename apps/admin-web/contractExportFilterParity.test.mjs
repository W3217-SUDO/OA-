import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/ContractCenterPage.tsx', import.meta.url), 'utf8')

test('CSV contract export forwards the active query filters', () => {
  const csvBlock = source.slice(source.indexOf('const exportCsv'), source.indexOf('const exportExcel'))
  assert.match(csvBlock, /serial_no: query\.serial_no \|\| undefined/)
  assert.match(csvBlock, /signed_at_end: query\.signed_at\?\./)
})
