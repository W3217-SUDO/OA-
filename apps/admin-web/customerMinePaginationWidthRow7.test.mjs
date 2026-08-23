import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const page = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')
const css = await readFile(new URL('./src/customer-center.css', import.meta.url), 'utf8')

test('customer mine page-size selector keeps every configured value visible', () => {
  assert.match(page, /options=\{\[10, 15, 20, 50, 100, 200\]\.map/)
  const width = css.match(/\.customer-original-pagination \.ant-select \{ width: (\d+)px; min-width: (\d+)px;/)
  assert.ok(width, 'page-size selector must have a stable readable width')
  assert.ok(Number(width[1]) >= 64, 'page-size selector must fit three-digit values')
  assert.equal(width[1], width[2])
})
