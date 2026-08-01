import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('../api-server/app/main.py', import.meta.url), 'utf8')

test('CSV export endpoint accepts contract filter parameters', () => {
  const block = source.slice(source.indexOf('async def export_records('), source.indexOf('async def export_records_excel'))
  assert.match(block, /serial_no: str = ""/)
  assert.match(block, /signed_at_start: str = ""/)
  assert.match(block, /records = \[item for item in records if matches\(item\)\]/)
})
