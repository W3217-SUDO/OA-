import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = (await readFile(new URL('./src/App.tsx', import.meta.url), 'utf8'))
  .replace(/\s+/g, '')
  .replace(/"/g, "'")

test('dashboard cards use backend-provided business routes', () => {
  assert.match(source, /query\?:\{scope\?:'mine'\|'company';unpaid_official\?:boolean\}/)
  assert.match(source, /key=\{m\.key\}/)
  assert.match(source, /rememberDashboardFeeQuery\(metric\.query\)/)
  assert.match(source, /onClick=\{\(\)=>navigateMetric\(m\)\}/)
  assert.match(source, /detail_context\?:\{contract_no:string;return_view:string;amount_filter\?:string;owner\?:string\}/)
  assert.match(source, /sessionStorage\.setItem\('sunhold:receivable-detail-context',JSON\.stringify\(metric\.detail_context\)\)/)
  assert.doesNotMatch(source, /constmetricRoutes=/)
})

test('dashboard refreshes live metrics while open and when focus returns', () => {
  assert.match(source, /window\.setInterval\(loadDashboard,30_000\)/)
  assert.match(source, /window\.addEventListener\('focus',refreshOnFocus\)/)
  assert.match(source, /window\.removeEventListener\('focus',refreshOnFocus\)/)
})
