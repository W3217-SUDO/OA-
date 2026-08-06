import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import {
  isCustomerRegistrationAddressSafe,
  isCustomerPostalCodeSafe,
} from './src/customerParity.mjs'

const pageSource = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')
const customerCss = await readFile(new URL('./src/customer-center.css', import.meta.url), 'utf8')

test('legacy customer address and postal-code validators reject forbidden characters', () => {
  assert.equal(isCustomerRegistrationAddressSafe('上海路 1 号'), true)
  assert.equal(isCustomerRegistrationAddressSafe('上海路<1号'), false)
  assert.equal(isCustomerRegistrationAddressSafe('上海路\\1号'), false)
  assert.equal(isCustomerPostalCodeSafe('200000'), true)
  assert.equal(isCustomerPostalCodeSafe('200-000'), false)
  assert.equal(isCustomerPostalCodeSafe('200—000'), false)
  assert.equal(isCustomerPostalCodeSafe('20"0000'), false)
  for (const forbidden of ['\\', "'", '"', '<', '>', '|']) {
    assert.equal(isCustomerRegistrationAddressSafe(`A${forbidden}B`), false)
  }
  for (const forbidden of ['-', '—', '\\', "'", '"', '<', '>', '|']) {
    assert.equal(isCustomerPostalCodeSafe(`200${forbidden}000`), false)
  }
  assert.equal(isCustomerRegistrationAddressSafe('A-1'), true)
  assert.equal(isCustomerRegistrationAddressSafe('A—1'), true)
})

test('customer forms consume the legacy address and postal-code validators', () => {
  assert.match(pageSource, /isCustomerRegistrationAddressSafe/)
  assert.match(pageSource, /isCustomerPostalCodeSafe/)
  assert.match(pageSource, /注册地址禁止输入/)
  assert.match(pageSource, /邮编禁止输入/)
})

test('customer people autocompletes recorded names and retains only existing legacy selections', () => {
  assert.match(pageSource, /api\.get\("\/users\/directory", \{ params: \{ purpose: "customer_manager" \} \}\)/)
  assert.match(pageSource, /user\.eligible_customer_person === true \|\| retained\.has\(user\.username\)/)
  assert.match(pageSource, /const retained = new Set\(/)
  assert.match(pageSource, /客户来源" name="customer_source"><Select showSearch optionFilterProp="label" options=\{directoryOptions\}/)
  assert.match(pageSource, /客户联系人账号" name="contact"><Select mode="multiple" showSearch optionFilterProp="label" options=\{directoryOptions\}/)
  assert.match(pageSource, /contact_accounts/)
  assert.match(pageSource, /customer_managers: directoryOptions\.some\(\(option\) => option\.value === profile\.username\) \? \[profile\.username\] : \[\]/)
})

test('customer detail renders multi contact accounts and shared recipients through person labels', () => {
  assert.match(pageSource, /const contactAccountLabels =/)
  assert.match(pageSource, /contact_account_display_names\?\.length/)
  assert.match(pageSource, /contact_accounts\?\.length/)
  assert.match(pageSource, /contactAccountLabels\(contacts\)/)
  assert.match(pageSource, /dataSource=\{sharedObjects\.map\(\(value\) => \(\{ value \}\)\)\}/)
  assert.match(pageSource, /dataIndex: "value", render: \(value: string\) => userLabel\(value\)/)
})

test('customer create people selectors can visibly wrap multiple selected names', () => {
  assert.match(pageSource, /className="customer-person-multi-field" label="客户管理人" name="customer_managers"/)
  assert.match(pageSource, /className="customer-person-multi-field" label="客户联系人账号" name="contact"/)
  assert.match(customerCss, /\.customer-create-form \.customer-person-multi-field \{/)
  assert.match(customerCss, /height: auto;/)
  assert.match(customerCss, /\.customer-create-form \.customer-control-grid \.customer-person-multi-field[\s\S]*grid-column: span 2;/)
  assert.match(customerCss, /\.customer-create-form \.customer-person-multi-field \.ant-select-selector[\s\S]*height: auto !important;/)
  assert.match(customerCss, /\.customer-create-form \.customer-person-multi-field \.ant-select[\s\S]*height: auto !important;/)
  assert.match(customerCss, /\.customer-create-form \.customer-person-multi-field \.ant-select-selection-overflow[\s\S]*flex-wrap: wrap;/)
  assert.match(customerCss, /\.customer-create-form \.customer-person-multi-field \.ant-select-selection-overflow[\s\S]*min-height: 19px;/)
})
test('customer detail reads auditable customer events and renders event columns', () => {
  assert.match(pageSource, /api\.get\(`\/records\/\$\{target\.id\}\/history`\)/)
  assert.match(pageSource, /key: "events"/)
  assert.match(pageSource, /dataIndex: "action"/)
  assert.match(pageSource, /dataIndex: "operator"/)
  assert.match(pageSource, /dataIndex: "created_at"/)
})

test('public customer list exposes edit only to administrators and always keeps claim', () => {
  assert.match(
    pageSource,
    /initialView === "customer-public"\s*\? profile\.role === "admin"[\s\S]*\{ key: "edit", label: "客户编辑" \}[\s\S]*\{ key: "claim", label: "拾回" \}/,
  )
  assert.match(pageSource, /if \(key === "edit"\) startEdit\(target\)/)
})
