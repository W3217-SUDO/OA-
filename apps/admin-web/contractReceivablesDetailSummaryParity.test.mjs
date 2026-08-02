import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/ContractReceivablesPage.tsx', import.meta.url), 'utf8')

test('receivables detail totals seven amount columns once per contract and renders both summaries', () => {
  const totals = source.match(/export const calculateReceivablesDetailTotals = \(([^)]*)\) => ([\s\S]*?\n\};)/)
  assert.ok(totals, 'detail totals must aggregate unique contracts')
  assert.match(source, /const detailSummary = useMemo\(\(\) => calculateReceivablesDetailTotals\(detailRows, contractById\)/)
  assert.match(source, /renderDetailSummaryRow\(detailSummary[^)]*\)[\s\S]*?renderDetailSummaryRow\(detailSummary[^)]*\)/)
})
