import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')

test('company customer query clears text filters after sending their current values', () => {
  assert.match(source, /const queryCustomerList = \(\) => \{/)
  assert.match(source, /const requestKeyword = keyword;\s*const requestManagerKeyword = managerKeyword;/)
  assert.match(source, /void load\(\{\s*keyword: requestKeyword,\s*customerType,\s*managerKeyword: requestManagerKeyword,\s*page: 1,\s*\}\)\.finally\(\(\) => \{\s*if \(initialView === "customer-company"\) \{\s*setKeyword\(""\);\s*setManagerKeyword\(""\);\s*\}\s*\}\);/)
  assert.match(source, /onPressEnter=\{queryCustomerList\}/)
  assert.match(source, /<Button type="primary" icon=\{<SearchOutlined \/>\} onClick=\{queryCustomerList\}>/)
})
