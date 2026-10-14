import type { ConversationWorkspace } from "./types";

export const PERSONAL_CONVERSATION_WORKSPACE: ConversationWorkspace = { kind: "personal" };

export function conversationWorkspaceKey(workspace: ConversationWorkspace): string {
  return workspace.kind === "personal" ? "personal" : `case:${workspace.case_id}`;
}

export function conversationDraftKey(conversationId: string | null | undefined, workspace?: ConversationWorkspace): string {
  return conversationId || (workspace ? `workspace:${conversationWorkspaceKey(workspace)}` : "");
}

export function requireConversationWorkspace(value: ConversationWorkspace | undefined): ConversationWorkspace {
  if (value?.kind === "personal" && value.case_id === undefined) return PERSONAL_CONVERSATION_WORKSPACE;
  if (value?.kind === "case" && Number.isSafeInteger(value.case_id) && value.case_id > 0) return { kind: "case", case_id: value.case_id };
  throw new Error("会话响应缺少有效的空间归属，请刷新核对");
}

export function conversationWorkspaceParams(workspace?: ConversationWorkspace) {
  if (!workspace) return undefined;
  return { workspace_kind: workspace.kind, ...(workspace.kind === "case" ? { workspace_case_id: workspace.case_id } : {}) };
}
