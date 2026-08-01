import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/ContractReceivablesPage.tsx', import.meta.url), 'utf8')

test('receivables query exposes a reset action that clears form and filtered state', () => {
  assert.match(source, /form\.resetFields\(\)/)
  assert.match(source, /setQuery\(\{\}\)/)
  assert.match(source, /<Button onClick=\{\(\) => \{ form\.resetFields\(\); setQuery\(\{\}\); \}\}>重置<\/Button>/)
})
