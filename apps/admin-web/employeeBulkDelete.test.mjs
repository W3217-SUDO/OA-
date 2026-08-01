import test from 'node:test'
import assert from 'node:assert/strict'
import { normalizeEmployeeIds } from './src/employeeBulkDelete.mjs'

test('normalizes selected formal employee identifiers for a batch deletion request', () => {
  assert.deepEqual(normalizeEmployeeIds([7, 2, 7]), [2, 7])
})

test('rejects an empty or account-only employee selection', () => {
  assert.throws(() => normalizeEmployeeIds([]), /请至少选择一名员工/)
  assert.throws(() => normalizeEmployeeIds([-4, 0]), /请至少选择一名员工/)
})
