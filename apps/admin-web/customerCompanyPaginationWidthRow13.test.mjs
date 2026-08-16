import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const page = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')
const css = await readFile(new URL('./src/customer-center.css', import.meta.url), 'utf8')

test('company customer page-size selector keeps every configured value visible', () => {
  assert.match(page, /"customer-company": "company"/)
  assert.match(page, /isOriginalCustomerList && <div className="customer-original-pagination">/)
  assert.match(page, /options=\{\[10, 15, 20, 50, 100, 200\]\.map/)
  const selectorWidth = css.match(
    /\.customer-original-pagination \.ant-select \{ width: (\d+)px; min-width: (\d+)px;/,
  )
  assert.ok(selectorWidth, 'page-size selector must define a stable width')
  assert.ok(Number(selectorWidth[1]) >= 64, 'page-size selector must fit three-digit values')
  assert.equal(selectorWidth[1], selectorWidth[2], 'width and min-width must stay aligned')
})
