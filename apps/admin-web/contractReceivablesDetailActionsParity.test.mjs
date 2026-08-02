import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/ContractReceivablesPage.tsx', import.meta.url), 'utf8')

test('receivables detail omits the create-plan action that is absent from the legacy item list', () => {
  const visibility = source.match(/export const shouldShowReceivableCreateAction = \(detailView: boolean\) => ([^;]+);/)

  assert.ok(visibility, 'the create-plan action must be gated by the current receivables view')
  const shouldShow = new Function('detailView', `return (${visibility[1]});`)
  assert.equal(shouldShow(true), false)
  assert.equal(shouldShow(false), true)
  assert.match(source, /shouldShowReceivableCreateAction\(detailView\) && <Button type="primary" onClick=\{openCreateReceivable\}>新增应收计划<\/Button>/)
})
