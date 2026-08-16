import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const page = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')
const css = await readFile(new URL('./src/customer-center.css', import.meta.url), 'utf8')

test('customer mine page-size selector keeps every configured value visible', () => {
  assert.match(page, /options=\{\[10, 15, 20, 50, 100, 200\]\.map/)
  assert.match(
    css,
    /\.customer-original-pagination \.ant-select \{ width: 64px; min-width: 64px;/,
  )
})
