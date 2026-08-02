import test from 'node:test'
import assert from 'node:assert/strict'
import { access, readdir, readFile } from 'node:fs/promises'
import path from 'node:path'

const workspaceRoot = path.resolve(process.cwd(), '..', '..', '..')
let oldRepo = ''
for (const entry of await readdir(workspaceRoot, { withFileTypes: true })) {
  if (!entry.isDirectory()) continue
  const candidate = path.join(workspaceRoot, entry.name)
  try { await access(path.join(candidate, 'SH.CRM.WEB', '.codegraph')); oldRepo = path.join(candidate, 'SH.CRM.WEB'); break } catch {}
}
if (!oldRepo) throw new Error('old source repository with .codegraph not found')
const oldContactsController = await readFile(path.join(oldRepo, 'Areas', 'CRM', 'Controllers', 'CustomerContactsController .cs'), 'utf8')
const localPage = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')

test('customer contact detail preserves the legacy default page size and server paging', () => {
  assert.match(oldContactsController, /PageNo = pageNo\.HasValue \? pageNo\.Value : 1/)
  assert.match(oldContactsController, /PageSize = pageSize\.HasValue \? pageSize\.Value : 15/)
  assert.match(oldContactsController, /Skip\(model\.SearchCondition\.PageSize \* \(model\.SearchCondition\.PageNo - 1\)\)/)
  assert.match(localPage, /customer-contact-table[\s\S]*pagination=\{\{/) 
})

test('customer contact pagination exposes the same six size choices', () => {
  for (const size of [10, 15, 20, 50, 100, 200]) {
    assert.match(localPage, new RegExp(`\\b${size}\\b`))
  }
  assert.match(localPage, /pageSizeOptions:\s*\[10, 15, 20, 50, 100, 200\]/)
})
