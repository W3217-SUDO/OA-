import {
  isCustomerRegistrationAddressSafe,
  isCustomerPostalCodeSafe,
} from "../customerParity.mjs";
import type { Profile } from "./types";

export const customerRegistrationAddressRules = [{
  validator: (_rule: unknown, value: unknown) =>
    isCustomerRegistrationAddressSafe(value)
      ? Promise.resolve()
      : Promise.reject(new Error("注册地址禁止输入非法字符")),
}];

export const customerPostalCodeRules = [{
  validator: (_rule: unknown, value: unknown) =>
    isCustomerPostalCodeSafe(value)
      ? Promise.resolve()
      : Promise.reject(new Error("邮编禁止输入非法字符")),
}];

export const colors: Record<string, string> = {
  正常: "green",
  跟进中: "blue",
  潜在: "blue",
  目标: "cyan",
  立项: "geekblue",
  关怀: "purple",
  签约: "green",
  谈判: "orange",
  价值: "gold",
  公海: "orange",
  已回收: "red",
};

export const prioritizeNewCustomerManagers = (existing: string[], selected: string[]) => {
  const previous = Array.from(new Set((existing || []).filter(Boolean)));
  const requested = Array.from(new Set((selected || []).filter(Boolean)));
  const added = requested.filter((manager) => !previous.includes(manager));
  const retained = previous.filter((manager) => requested.includes(manager));
  return [...added.reverse(), ...retained];
};

export const initialProfile = (): Profile => {
  try {
    const stored = JSON.parse(localStorage.getItem("user") || "{}");
    return {
      username: stored.username || "",
      display_name: stored.display_name || "",
      department: stored.department || "",
      role: stored.role,
    };
  } catch {
    return { username: "", display_name: "", department: "" };
  }
};
