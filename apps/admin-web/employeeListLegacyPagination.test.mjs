import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const source = await readFile(fileURLToPath(new URL('./src/HrCenterPage.tsx', import.meta.url)), 'utf8')

test('matches the legacy employee list default page size', () => {
  assert.match(source, /pagination=\{\{current:employeePage,pageSize:15,total:/)
})
