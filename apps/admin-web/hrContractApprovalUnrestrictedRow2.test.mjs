import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const hrSource = await readFile(fileURLToPath(new URL('./src/HrCenterPage.tsx', import.meta.url)), 'utf8')
const contractSource = await readFile(fileURLToPath(new URL('./src/ContractCenterPage.tsx', import.meta.url)), 'utf8')

test('persisted employees can be added to or removed from contract approver candidates directly', () => {
  assert.match(hrSource, /canConfigureContractApproval=\(employeeId\?:number\)=>Boolean\(employeeId&&employeeId>0\)/)
  assert.doesNotMatch(hrSource, /系统管理员或非员工账号不能配置为合同审批人/)
  assert.match(hrSource, /data\.user\?\.contract_approval_enabled\?\?data\.employee\?\.data\?\.contract_approval_enabled/)
})

test('contract workflows request the dedicated approver directory after load and settings save', () => {
  const calls = contractSource.match(/api\.get\("\/users\/directory", \{ params: \{ purpose: "contract_approver" \} \}\)/g) || []
  assert.equal(calls.length, 2)
})
