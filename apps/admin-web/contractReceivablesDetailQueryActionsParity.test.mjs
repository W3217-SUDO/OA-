import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/ContractReceivablesPage.tsx', import.meta.url), 'utf8')

test('receivables detail keeps only the legacy query action while list views retain reset', () => {
  const visibility = source.match(/export const shouldShowReceivableResetAction = \(detailView: boolean\) => ([^;]+);/)

  assert.ok(visibility, 'the reset action must be gated by the receivables view')
  const shouldShow = new Function('detailView', `return (${visibility[1]});`)
  assert.equal(shouldShow(true), false)
  assert.equal(shouldShow(false), true)
  assert.match(source, /shouldShowReceivableResetAction\(detailView\) && <Button onClick=\{\(\) => \{ form\.resetFields\(\); setQuery\(\{\}\); \}\}>重置<\/Button>/)
})
