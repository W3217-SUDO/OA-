import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const oldRoot = new URL('../../../旧系统归档源码/SH.CRM.WEB/', import.meta.url)
const oldCustomerScript = await readFile(new URL('Scripts/CRM/Customer/Customer.js', oldRoot), 'utf8')
const oldCustomerListScript = await readFile(new URL('Scripts/CRM/Customer/CRM.Customer.js', oldRoot), 'utf8')
const pageSource = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')
const actionsSource = pageSource.slice(
  pageSource.indexOf('const originalActionItems'),
  pageSource.indexOf('const managerLocked'),
)

test('customer more actions expose legacy communication and contact-management entries', () => {
  assert.match(oldCustomerScript, /customer\.OpenCommunication\(" \+ c\.CustomerId \+ "\)/)
  assert.match(oldCustomerScript, /customer\.ContactsList\(" \+ c\.CustomerId \+ "\)/)
  assert.match(actionsSource, /key: "communication", label: "新增沟通记录"/)
  assert.match(actionsSource, /key: "contact-management", label: "联系人管理"/)
  assert.match(actionsSource, /if \(key === "communication"\) openCustomerCommunication\(target\)/)
  assert.match(pageSource, /const openCustomerCommunication = \(customer: Customer\) => \{[\s\S]*onNavigate\?\.\("user-communications"\)/)
  assert.match(actionsSource, /if \(key === "contact-management"\)[\s\S]*void openDetail\(target, "contacts"\)/)
})

test('customer page separates civil case and ipr case navigation from legacy case jumps', () => {
  assert.match(oldCustomerListScript, /CaseList: function \(customerNo\)/)
  assert.match(oldCustomerScript, /IPR\/Case\/CaseList\?customerId=/)
  assert.match(pageSource, /title: "民事案件数量"/)
  assert.match(pageSource, /title: "知识产权案件数量"/)
  assert.match(pageSource, /const openCustomerIprCases = \(customer: Customer\) => \{[\s\S]*target: "ipr-cases"/)
  assert.match(pageSource, /onNavigate\?\.\("ipr-patent"\)/)
})
