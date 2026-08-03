import test from 'node:test'
import assert from 'node:assert/strict'
import { buildContactStatusPatch, buildContactStatusRequest, runContactStatusUpdate } from './src/customerParity.mjs'
import { readFile } from 'node:fs/promises'

const pageSource = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')
const mainSource = await readFile(new URL('../api-server/app/main.py', import.meta.url), 'utf8')

test('contact status patches preserve legacy default and active actions', () => {
  assert.deepEqual(buildContactStatusPatch({ id: 'c1', is_valid: false }, 'primary'), { is_primary: true })
  assert.deepEqual(buildContactStatusPatch({ id: 'c1', is_valid: false }, 'active'), { is_valid: true })
  assert.deepEqual(buildContactStatusPatch(null, 'active'), {})
  assert.deepEqual(buildContactStatusPatch({ id: 'c1' }, 'unknown'), {})
  assert.deepEqual(
    buildContactStatusRequest(12, 'c1', { id: 'c1', is_valid: false }, 'active'),
    { method: 'patch', url: '/customers/12/contacts/c1/status', data: { is_valid: true } },
  )
  assert.equal(buildContactStatusRequest(12, 'c1', { id: 'c1' }, 'unknown'), null)
})

test('contact status UI sends the dedicated status patch contract', () => {
  assert.match(pageSource, /buildContactStatusRequest\(contacts\.id, contact\.id, contact, action\)/)
  assert.match(pageSource, /runContactStatusUpdate\(/)
  assert.match(pageSource, /\(url, data\) => api\.patch\(url, data\)/)
})

test('contact status success refreshes detail before the customer list', async () => {
  const request = buildContactStatusRequest(12, 'c1', { id: 'c1' }, 'primary')
  const calls = []
  const result = await runContactStatusUpdate(
    request,
    async (url, data) => calls.push(['patch', url, data]),
    async () => calls.push(['detail']),
    async () => calls.push(['list']),
  )
  assert.equal(result, true)
  assert.deepEqual(calls, [
    ['patch', '/customers/12/contacts/c1/status', { is_primary: true }],
    ['detail'],
    ['list'],
  ])
})

test('customer UI exposes guarded contact status actions in both detail renderers', () => {
  assert.match(pageSource, /buildContactStatusRequest/)
  assert.match(pageSource, /updateContactStatus/)
  assert.match(pageSource, /updateContactStatus\(row,\s*"primary"\)/)
  assert.match(pageSource, /updateContactStatus\(row,\s*"active"\)/)
  assert.match(pageSource, /updateContactStatus\(r, "primary"\)/)
  assert.match(pageSource, /updateContactStatus\(r, "active"\)/)
})

test('customer detail keeps event history in page and drawer without clearing list selection from child writes', () => {
  assert.equal((pageSource.match(/key: "events"/g) || []).length, 2)
  for (const functionName of ['addContact', 'updateContact', 'updateContactStatus', 'addNote', 'updateNote', 'uploadDocument']) {
    const start = pageSource.indexOf(`const ${functionName}`)
    assert.notEqual(start, -1, `${functionName} handler is present`)
    const nextHandler = pageSource.indexOf('\n  const ', start + 1)
    const block = pageSource.slice(start, nextHandler === -1 ? undefined : nextHandler)
    assert.doesNotMatch(block, /setSelectedRowKeys\(\[\]\)/, `${functionName} must not clear customer-list selection`)
  }
  assert.match(pageSource, /historyError/)
  assert.match(pageSource, /操作记录加载失败/)
  for (const field of ['action', 'operator', 'comment', 'created_at']) {
    assert.match(mainSource, new RegExp(`"${field}"`), `history response exposes ${field}`)
  }
})
