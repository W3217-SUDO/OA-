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

test('keeps the old system required field order', () => {
  assert.deepEqual(legacyRequiredEmployeeFields, [
    'serial_no', 'username', 'title', 'role', 'password', 'department', 'position',
  ])
})

test('returns each required field as the first missing field in old-system order', () => {
  const labels = {
    serial_no: '员工号',
    username: '用户名',
    title: '中文姓名',
    role: '角色',
    password: '密码',
    department: '部门',
    position: '职务',
  }

  legacyRequiredEmployeeFields.forEach((key, index) => {
    const precedingValues = Object.fromEntries(
      legacyRequiredEmployeeFields.slice(0, index).map((field) => [field, 'ok']),
    )
    assert.deepEqual(firstMissingRequiredEmployeeField(precedingValues), {
      key,
      label: labels[key],
      message: `请输入${labels[key]}.`,
    })
  })

  assert.equal(
    firstMissingRequiredEmployeeField(Object.fromEntries(legacyRequiredEmployeeFields.map((key) => [key, 'ok']))),
    null,
  )
})

test('does not treat extension fields as required core fields', () => {
  assert.equal(firstMissingRequiredEmployeeField({
    serial_no: 'E-1',
    username: 'u',
    title: 'n',
    role: 'user',
    password: 'p',
    department: 'd',
    position: 'employee',
  }), null)
})
