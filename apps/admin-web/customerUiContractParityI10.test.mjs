import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { isCustomerRegistrationAddressSafe, isCustomerPostalCodeSafe } from './src/customerParity.mjs'

const pageSource = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')
const customerCss = await readFile(new URL('./src/customer-center.css', import.meta.url), 'utf8')

test('customer address and postal-code validators reject unsafe values', () => {
  assert.equal(isCustomerRegistrationAddressSafe('A-1'), true)
  assert.equal(isCustomerPostalCodeSafe('200000'), true)
  for (const value of ['A\\B', 'A"B', 'A<B']) assert.equal(isCustomerRegistrationAddressSafe(value), false)
  for (const value of ['200-000', '200\\000', '20"0000']) assert.equal(isCustomerPostalCodeSafe(value), false)
})

test('customer people autocomplete filters manager and contact accounts independently', () => {
  assert.match(pageSource, /api\.get\("\/users\/directory", \{ params: \{ purpose: "customer_manager" \} \}\)/)
  assert.match(pageSource, /user\.eligible_customer_person === true \|\| retained\.has\(user\.username\)/)
  assert.match(pageSource, /const customerContactOptions = useMemo\(/)
  assert.match(pageSource, /user\.account_type === "[^"]+" \|\| retained\.has\(user\.username\)/)
  assert.match(pageSource, /options=\{customerContactOptions\}/)
  assert.match(pageSource, /contact_accounts/)
  assert.match(pageSource, /customer_managers: directoryOptions\.some\(\(option\) => option\.value === profile\.username\) \? \[profile\.username\] : \[\]/)
})

test('customer detail renders contact accounts and audit events through labels', () => {
  assert.match(pageSource, /const contactAccountLabels =/)
  assert.match(pageSource, /contact_account_display_names\?\.length/)
  assert.match(pageSource, /contactAccountLabels\(contacts\)/)
  assert.match(pageSource, /api\.get\(`\/records\/\$\{target\.id\}\/history`\)/)
})

test('customer people selectors wrap selected names without expanding the form grid', () => {
  assert.match(pageSource, /className="customer-person-multi-field"/)
  assert.match(customerCss, /\.customer-create-form \.customer-person-multi-field \{/)
  assert.match(customerCss, /\.customer-create-form \.customer-person-multi-field \.ant-select-selection-overflow[\s\S]*?flex-wrap: wrap;/)
  assert.match(customerCss, /\.customer-create-form \.customer-control-grid \.customer-person-multi-field[\s\S]*?grid-column: span 2;/)
})

test('public customers retain administrator edit and claim actions', () => {
  assert.match(pageSource, /initialView === "customer-public"\s*\? profile\.role === "admin"/)
  assert.match(pageSource, /if \(key === "edit"\) startEdit\(target\)/)
  assert.match(pageSource, /key: "claim"/)
})
