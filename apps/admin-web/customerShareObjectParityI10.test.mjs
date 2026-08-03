import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { normalizeSharedObjectValues } from './src/customerParity.mjs'

const pageSource = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')

test('shared-object projection accepts legacy DTOs, trims and de-duplicates recipients', () => {
  assert.deepEqual(
    normalizeSharedObjectValues([
      ' alice ',
      { StaffName: 'bob' },
      { staff_name: 'carol' },
      { username: 'alice' },
      { StaffName: '' },
      null,
    ]),
    ['alice', 'bob', 'carol'],
  )
})

test('shared-object projection is safe for empty or malformed API data', () => {
  assert.deepEqual(normalizeSharedObjectValues(), [])
  assert.deepEqual(normalizeSharedObjectValues(null), [])
  assert.deepEqual(normalizeSharedObjectValues({}), [])
})

test('customer share action restores projected recipients when opening the modal', () => {
  assert.match(pageSource, /shareForm\.setFieldsValue\(\{ recipients: normalizeSharedObjectValues\(target\.data\.shared_with\) \}\)/)
})
