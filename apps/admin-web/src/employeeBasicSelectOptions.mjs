export const legacyEmployeeSelectOptions = {
  political_status: ["党员", "团员", "学生", "其他"],
  marriage: ["已婚", "未婚"],
  childbearing: ["已生", "未生"],
  employment_status: ["在职", "离职"],
};

export const legacyEmployeeBasicDefaults = {
  political_status: "党员",
  marriage: "未婚",
  childbearing: "未生",
  employment_status: "在职",
};

export const employeeSelectOptions = (key) =>
  (legacyEmployeeSelectOptions[key] || []).map((value) => ({ value, label: value }));
