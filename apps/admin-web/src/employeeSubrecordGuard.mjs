export function employeeSubrecordCreateMessage(employeeId) {
  return employeeId ? null : "请先保存员工基本信息，再维护此页记录";
}
