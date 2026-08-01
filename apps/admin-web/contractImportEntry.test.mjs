import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/ContractCenterPage.tsx', import.meta.url), 'utf8')

test('contract list exposes the generic CSV template and batch import entry', () => {
  assert.match(source, /import RecordImportButton from "\.\/RecordImportButton"/)
  assert.match(source, /<RecordImportButton module="contract" onImported=\{load\} \/>/)
})
