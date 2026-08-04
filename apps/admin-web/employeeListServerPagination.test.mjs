import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const frontend = await readFile(fileURLToPath(new URL('./src/HrCenterPage.tsx', import.meta.url)), 'utf8')
const backend = await readFile(fileURLToPath(new URL('../api-server/app/main.py', import.meta.url)), 'utf8')

test('employee list requests the dedicated server-side page and all legacy filters', () => {
  assert.match(frontend, /api\.get\('\/hr\/employees',\{params:\{page:requestedPage,page_size:15,company,department,username,name,mobile,enabled\}\}\)/)
  assert.match(frontend, /dataSource=\{rows\}/)
  assert.match(frontend, /pagination=\{\{current:employeePage,pageSize:15,total:employeeTotal/)
  assert.match(frontend, /onChange:\(page\)=>changeEmployeePage\(page\)/)
})

test('employee list preserves the API total and requested page when moving to page two and back', () => {
  assert.match(frontend, /setEmployeeTotal\(Number\(payload\.total\|\|0\)\)/)
  assert.match(frontend, /setEmployeePage\(Number\(payload\.page\|\|requestedPage\)\)/)
})

test('HR list endpoint applies 15-row first and second page windows before returning rows', () => {
  assert.match(backend, /@app\.get\(f"\{settings\.api_prefix\}\/hr\/employees"\)/)
  assert.match(backend, /page: int = Query\(1, ge=1\), page_size: int = Query\(15, ge=1, le=100\)/)
  assert.match(backend, /BusinessRecord\.module == "hr", \*scope/)
  assert.match(backend, /start = \(page - 1\) \* page_size/)
  assert.match(backend, /return \{"items": rows\[start:start \+ page_size\], "total": total, "page": page, "page_size": page_size\}/)
})
