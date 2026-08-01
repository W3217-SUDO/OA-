import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')

test('customer reset sends explicit empty filters and first page', () => {
  assert.match(source, /const load = async \(overrides: Partial<\{ keyword: string; customerType: string; managerKeyword: string; page: number \}> = \{\}\)/)
  assert.match(source, /const requestKeyword = overrides\.keyword \?\? keyword/)
  assert.match(source, /customer_name: requestKeyword/)
  assert.match(source, /customer_type: requestCustomerType/)
  assert.match(source, /manager: requestManagerKeyword/)
  assert.match(source, /const resetCustomerType = customerTypeOptions\[0\]\?\.value \|\| "客户";/)
  assert.match(source, /setSelectedRowKeys\(\[\]\);\s*setPage\(1\);\s*setJumpPage\("1"\);/)
  assert.match(source, /void load\(\{ keyword: "", customerType: resetCustomerType, managerKeyword: "", page: 1 \}\)/)
})

