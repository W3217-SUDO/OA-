import { useEffect, useState } from "react";
import { api } from "./api";

// 页面上显示人员一律用姓名，不直接显示登录账号（BUG20261031001）。
// 通讯录全站只取一次；接口已带姓名的优先用接口的，查不到姓名时才显示账号。
type DirectoryItem = { username?: string; display_name?: string };

const SPECIAL_NAMES: Record<string, string> = { system: "系统" };

let directoryRequest: Promise<Map<string, string>> | null = null;

const loadDirectory = () => {
  directoryRequest ??= api
    .get("/users/directory")
    .then(({ data }) => {
      const names = new Map<string, string>();
      for (const item of (data?.items || []) as DirectoryItem[]) {
        const username = String(item.username || "").trim().toLowerCase();
        const name = String(item.display_name || "").trim();
        if (username && name) names.set(username, name);
      }
      return names;
    })
    .catch(() => {
      directoryRequest = null;
      return new Map<string, string>();
    });
  return directoryRequest;
};

export const displayPersonName = (names: Map<string, string>, value: unknown, displayName?: unknown) => {
  const shown = String(displayName || "").trim();
  const account = String(value || "").trim();
  if (shown && shown.toLowerCase() !== account.toLowerCase()) return shown;
  if (!account) return shown || "—";
  return names.get(account.toLowerCase()) || SPECIAL_NAMES[account.toLowerCase()] || shown || account;
};

export function usePersonNames() {
  const [names, setNames] = useState<Map<string, string>>(() => new Map());
  useEffect(() => {
    let alive = true;
    void loadDirectory().then((loaded) => {
      if (alive) setNames(loaded);
    });
    return () => {
      alive = false;
    };
  }, []);
  return (value: unknown, displayName?: unknown) => displayPersonName(names, value, displayName);
}
