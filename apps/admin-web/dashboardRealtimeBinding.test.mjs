import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = (await readFile(new URL('./src/App.tsx', import.meta.url), 'utf8'))
  .replace(/\s+/g, '')
  .replace(/"/g, "'")

test('dashboard cards use backend-provided business routes', () => {
  assert.match(source, /metrics:\{key:string;label:string;value:string;tone:string;route:string\}\[\]/)
  assert.match(source, /key=\{m\.key\}/)
  assert.match(source, /onClick=\{\(\)=>onNavigate\(m\.route\)\}/)
  assert.doesNotMatch(source, /constmetricRoutes=/)
})

test('dashboard refreshes live metrics while open and when focus returns', () => {
  assert.match(source, /window\.setInterval\(loadDashboard,30_000\)/)
  assert.match(source, /window\.addEventListener\('focus',refreshOnFocus\)/)
  assert.match(source, /window\.removeEventListener\('focus',refreshOnFocus\)/)
})
