import test from 'node:test'
import assert from 'node:assert/strict'
import { canDeleteOrganizationRole, hrActionAccess, organizationActionAccess, hrTransitionOptions, hrTransitionReasonMessage } from './src/hrAccessGuard.mjs'

test('allows an offboarded or suspended employee to be reinstated', () => {
  assert.deepEqual(hrTransitionOptions('\u79bb\u804c'), ['\u5728\u804c'])
  assert.deepEqual(hrTransitionOptions('\u505c\u7528'), ['\u5728\u804c'])
})

test('limits employee account administration to administrators while allowing managers to process HR status', () => {
  assert.deepEqual(hrActionAccess('admin'), {
    canEditEmployee: true,
    canProcessStatus: true,
    canManageAccount: true,
    canDeleteEmployee: true,
  })
  assert.deepEqual(hrActionAccess('manager'), {
    canEditEmployee: false,
    canProcessStatus: true,
    canManageAccount: false,
    canDeleteEmployee: false,
  })
  assert.deepEqual(hrActionAccess('user'), {
    canEditEmployee: false,
    canProcessStatus: false,
    canManageAccount: false,
    canDeleteEmployee: false,
  })
})

test('limits department and role administration to administrators', () => {
  assert.equal(organizationActionAccess('admin').canManageOrganization, true)
  assert.equal(organizationActionAccess('manager').canManageOrganization, false)
  assert.equal(organizationActionAccess('user').canManageOrganization, false)
})

test('protects the built-in system administrator role from deletion', () => {
  assert.equal(canDeleteOrganizationRole('SYSTEM-ADMIN'), false)
  assert.equal(canDeleteOrganizationRole('HR-MANAGER'), true)
})

test('keeps employee lifecycle transitions aligned with the dedicated HR workflow', () => {
  assert.deepEqual(hrTransitionOptions('试用'), ['在职', '离职'])
  assert.deepEqual(hrTransitionOptions('在职'), ['离职', '停用'])
  assert.deepEqual(hrTransitionOptions('离职'), ['在职'])
  assert.equal(hrTransitionReasonMessage('离职', ''), '离职或停用必须填写办理原因')
  assert.equal(hrTransitionReasonMessage('停用', 'xx'), null)
  assert.equal(hrTransitionReasonMessage('在职', ''), null)
})
