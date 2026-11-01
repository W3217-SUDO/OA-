import { useEffect, useState } from "react";
import { api } from "./api";
import { displayPeopleNames, displayPersonName } from "./personNameFormat";

export { displayPeopleNames, displayPersonName };

// 页面上显示人员一律用姓名，不直接显示登录账号（BUG20261031001）。
// 通讯录全站只取一次；接口已带姓名的优先用接口的，查不到姓名时才显示账号。
type DirectoryItem = { username?: string; display_name?: string };

let directoryRequest: Promise<Map<string, string>> | null = null;

const loadDirectory = () => {
  // 通讯录取不到（离线、测试替身）时只显示原账号，不影响页面。
  directoryRequest ??= Promise.resolve()
    .then(() => api.get("/users/directory"))
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

export function usePeopleNames() {
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
  return (value: unknown) => displayPeopleNames(names, value);
}
