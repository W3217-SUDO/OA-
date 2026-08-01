import test from 'node:test'
import assert from 'node:assert/strict'
import { hrActionAccess, organizationActionAccess } from './src/hrAccessGuard.mjs'

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
