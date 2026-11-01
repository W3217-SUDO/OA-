// 账号 → 姓名的纯显示规则，不依赖接口，便于测试（BUG20261031001、BUG 500787）。
const SPECIAL_NAMES: Record<string, string> = { system: "系统" };

export const displayPersonName = (names: Map<string, string>, value: unknown, displayName?: unknown) => {
  const shown = String(displayName || "").trim();
  const account = String(value || "").trim();
  if (shown && shown.toLowerCase() !== account.toLowerCase()) return shown;
  if (!account) return shown || "—";
  return names.get(account.toLowerCase()) || SPECIAL_NAMES[account.toLowerCase()] || shown || account;
};

// 多人串（“a、b,c”）逐个换成姓名，工作台、报表里的人员列用（BUG 500787）。
export const displayPeopleNames = (names: Map<string, string>, value: unknown) => {
  const people = String(value || "").split(/[、,，;；\n]+/).map((item) => item.trim()).filter(Boolean);
  return people.length ? people.map((item) => displayPersonName(names, item)).join("、") : "—";
};
