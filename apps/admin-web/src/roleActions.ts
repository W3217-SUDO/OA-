// BUG20261028012：页面功能按角色权限勾选。登录时保存的 configured_action_keys（"*" 为管理员）；
// 读不到时先按可用显示，后台仍会校验。
export const roleActionAllowed = (code: string): boolean => {
  try {
    const keys = JSON.parse(localStorage.getItem("user") || "{}").configured_action_keys;
    return !Array.isArray(keys) || keys.includes("*") || keys.includes(code);
  } catch {
    return true;
  }
};
