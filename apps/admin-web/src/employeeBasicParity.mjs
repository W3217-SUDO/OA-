export const legacyEmployeeCoreFields = [
  'serial_no', 'username', 'title', 'role', 'password', 'company', 'department', 'position',
  'data_level', 'is_active', 'account_type', 'id_no', 'mobile', 'english_level', 'education',
  'extension', 'native_place', 'foreign_language', 'graduation_date', 'social_security',
  'school', 'address', 'id_address',
]

export const legacyRequiredEmployeeFields = [
  'serial_no', 'username', 'title', 'role', 'password', 'department', 'position',
]

const labels = {
  serial_no: '员工号',
  username: '用户名',
  title: '中文姓名',
  role: '角色',
  password: '密码',
  department: '部门',
  position: '职务',
}

export function firstMissingRequiredEmployeeField(values) {
  const key = legacyRequiredEmployeeFields.find((item) => (
    values?.[item] == null || String(values[item]).trim() === ''
  ))
  return key ? { key, label: labels[key], message: `请输入${labels[key]}.` } : null
}
