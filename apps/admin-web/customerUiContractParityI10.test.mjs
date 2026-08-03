import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import {
  isCustomerRegistrationAddressSafe,
  isCustomerPostalCodeSafe,
} from './src/customerParity.mjs'

const pageSource = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')

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

test('customer detail reads auditable customer events and renders event columns', () => {
  assert.match(pageSource, /api\.get\(`\/records\/\$\{target\.id\}\/history`\)/)
  assert.match(pageSource, /key: "events"/)
  assert.match(pageSource, /dataIndex: "action"/)
  assert.match(pageSource, /dataIndex: "operator"/)
  assert.match(pageSource, /dataIndex: "created_at"/)
})
