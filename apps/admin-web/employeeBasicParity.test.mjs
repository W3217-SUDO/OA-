import test from 'node:test'
import assert from 'node:assert/strict'
import {
  legacyEmployeeCoreFields,
  legacyRequiredEmployeeFields,
  firstMissingRequiredEmployeeField,
} from './src/employeeBasicParity.mjs'

test('keeps the old system core field order without removing extension fields', () => {
  assert.deepEqual(legacyEmployeeCoreFields, [
    'serial_no', 'username', 'title', 'role', 'password', 'company', 'department', 'position',
    'data_level', 'is_active', 'account_type', 'id_no', 'mobile', 'english_level', 'education',
    'extension', 'native_place', 'foreign_language', 'graduation_date', 'social_security',
    'school', 'address', 'id_address',
  ])
})

test('returns only the first missing required field in old-system order', () => {
  assert.deepEqual(firstMissingRequiredEmployeeField({}), {
    key: 'serial_no', label: '员工号', message: '请输入员工号.',
  })
  assert.deepEqual(firstMissingRequiredEmployeeField({ serial_no: 'E-1' }), {
    key: 'username', label: '用户名', message: '请输入用户名.',
  })
  assert.equal(
    firstMissingRequiredEmployeeField(Object.fromEntries(legacyRequiredEmployeeFields.map((key) => [key, 'ok']))),
    null,
  )
})
