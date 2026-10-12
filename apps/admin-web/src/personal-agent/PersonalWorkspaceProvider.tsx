import { createContext, useContext, type ReactNode } from "react";
import { usePersonalWorkspace } from "./usePersonalWorkspace";

const PersonalWorkspaceContext = createContext<ReturnType<typeof usePersonalWorkspace> | null>(null);

// 工作台和独立 Ai 页面共用登录会话内的运行时，路由切换不清空草稿或中断回答。
export function PersonalWorkspaceProvider({ children }: { children: ReactNode }) {
  const workspace = usePersonalWorkspace();
  return <PersonalWorkspaceContext.Provider value={workspace}>{children}</PersonalWorkspaceContext.Provider>;
}

export function usePersonalWorkspaceContext() {
  const workspace = useContext(PersonalWorkspaceContext);
  if (!workspace) throw new Error("个人智能体运行时尚未挂载");
  return workspace;
}
