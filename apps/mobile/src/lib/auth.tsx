import * as SecureStore from "expo-secure-store";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, request, setApiToken, setUnauthorizedHandler } from "./api";
import type { LoginResponse, SessionUser } from "./types";

// token 只放系统加密存储（iOS 钥匙串 / 安卓 Keystore），不落普通文件。
const TOKEN_KEY = "oa_access_token";
const EXPIRES_KEY = "oa_access_token_expires_at";

type AuthState = {
  ready: boolean;
  user: SessionUser | null;
  login: (username: string, password: string) => Promise<LoginResponse>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

async function clearStoredToken() {
  setApiToken(null);
  await SecureStore.deleteItemAsync(TOKEN_KEY);
  await SecureStore.deleteItemAsync(EXPIRES_KEY);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState<SessionUser | null>(null);

  const logout = useCallback(async () => {
    await clearStoredToken();
    setUser(null);
  }, []);

  useEffect(() => {
    // 过期、被停用或在别处改密后后端返回 401，统一回到登录页。
    setUnauthorizedHandler(() => void logout());
    (async () => {
      try {
        const token = await SecureStore.getItemAsync(TOKEN_KEY);
        const expiresAt = Number(await SecureStore.getItemAsync(EXPIRES_KEY)) || 0;
        if (!token || expiresAt <= Date.now()) {
          await clearStoredToken();
          return;
        }
        setApiToken(token);
        const profile = await api.get<SessionUser>("/auth/me");
        if (profile.must_change_password) await clearStoredToken();
        else setUser(profile);
      } catch {
        await clearStoredToken();
      } finally {
        setReady(true);
      }
    })();
    return () => setUnauthorizedHandler(null);
  }, [logout]);

  const login = useCallback(async (username: string, password: string) => {
    const data = await request<LoginResponse>("/auth/login", { method: "POST", form: { username: username.trim(), password } });
    setApiToken(data.access_token);
    if (!data.must_change_password) {
      await SecureStore.setItemAsync(TOKEN_KEY, data.access_token);
      await SecureStore.setItemAsync(EXPIRES_KEY, String(Date.now() + data.expires_in * 1000));
      setUser(await api.get<SessionUser>("/auth/me"));
    }
    return data;
  }, []);

  const changePassword = useCallback(async (currentPassword: string, newPassword: string) => {
    await request("/auth/me", { method: "PATCH", json: { current_password: currentPassword, new_password: newPassword } });
    // 改密后旧 token 失效，要求用新密码重新登录。
    await clearStoredToken();
    setUser(null);
  }, []);

  const value = useMemo(() => ({ ready, user, login, changePassword, logout }), [ready, user, login, changePassword, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth 必须在 AuthProvider 内使用");
  return context;
}
