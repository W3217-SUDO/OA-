import type { AgentSkill } from "../agentSkillRouting";
import { agentOperationError, type AgentActionPreview } from "../AgentOperationPreview";

export type WorkspaceSkill = AgentSkill & { custom?: boolean; enabled?: boolean; instruction?: string; source?: string; sha256?: string; scope?: "system" | "global" | "personal" };
export type ResponseMode = "fast" | "deep";
export type MaterialStatus = "cached" | "readable" | "failed";
export type Material = { id: number; name: string; case_id?: number; status?: MaterialStatus; error?: string };
export type WorkspaceMessage = { role: "user" | "assistant"; content: string; created_at?: string; skill_name?: string; case_id?: number; case_no?: string; can_save_document?: boolean; can_save_personal_document?: boolean; can_save_case_document?: boolean; can_save_spreadsheet?: boolean; personal_document_save_error?: string | null; attachments?: Material[]; failed?: boolean; stopped?: boolean };

export function workspaceDocumentSaveTarget(item: WorkspaceMessage): "case" | "personal" | null {
  if (item.can_save_case_document !== undefined || item.can_save_personal_document !== undefined) {
    if (item.case_id && item.can_save_case_document === true) return "case";
    if (item.can_save_personal_document === true) return "personal";
    return null;
  }
  return item.case_id && item.can_save_document ? "case" : null;
}
export type PendingAction = { id: string; type: string; summary: string; payload?: Record<string, unknown>; preview?: AgentActionPreview; status: "pending" | "approved" | "rejected" | "executing" | "succeeded" | "failed"; error?: unknown };
export type DecisionFailure = { actionId: string; message: string; state: "syncing" | "verified" | "unknown"; hidden?: boolean };
export type ConfirmationStatus = "pending" | "executing" | "succeeded" | "failed" | "rejected";
export type ConfirmationRecord = {
  id: string;
  source: "mcp" | "personal_action";
  action_type: string;
  summary: string;
  status: ConfirmationStatus;
  requested_at: string | null;
  decided_at: string | null;
  finished_at: string | null;
  operator: string | null;
  comment: string;
  result: unknown;
  error: unknown;
  conversation_id: string | null;
  conversation_title: string | null;
  action_id: string | null;
  can_decide: boolean;
};
export type ConfirmationHistoryPage = { items: ConfirmationRecord[]; total: number; page: number; page_size: number };
export type ConfirmationDetail = { item: ConfirmationRecord; action: PendingAction | null; conversation_id: string | null; conversation_title: string | null; can_decide: boolean; request_preview: AgentActionPreview | null };
export type CompressionMetadata = {
  memory_category?: string;
  source_type?: string;
  source_label?: string;
  updated_at?: string;
  compressed_at?: string;
  covered_message_start?: number;
  covered_message_end?: number;
  covered_messages?: number;
  covered_message_range?: string;
  covered_message_count?: number;
  message_range?: string;
  input_tokens?: number;
  output_tokens?: number;
  token_count?: number;
  summary_token_count?: number;
  token_budget?: number;
  [key: string]: unknown;
};
export type WorkspaceState = { conversation_id?: string | null; conversation_title?: string; messages: WorkspaceMessage[]; pending_actions: PendingAction[]; dismissed_action_ids: string[]; structured_results?: unknown[]; memory_summary?: string; memory_summary_updated_at?: string; memory_summary_metadata?: CompressionMetadata; workspace?: ConversationWorkspace };
export type WorkspaceConversation = { id: string; title: string; message_count: number; updated_at: string; workspace?: ConversationWorkspace };
export type WorkspaceProject = { kind: "personal" | "case"; case_id?: number; serial_no?: string; title: string; available: boolean; unavailable_reason?: string };
export type ConversationSnapshot = { items: WorkspaceConversation[]; active_id: string | null; state: WorkspaceState; workspace?: ConversationWorkspace; workspaces?: WorkspaceProject[]; active_unavailable_reason?: string };
export type WorkspaceCommand = { id: string; label: string; prompt: string; skill_id: string; icon: string };
export type WorkspaceStatus = { ready: boolean; model: string; supports_response_modes?: boolean; commands: WorkspaceCommand[]; identity: { display_name?: string; department?: string; role?: string; permission_role?: string; staff_role?: string; position?: string } };
export type WorkspaceCase = { id: number; serial_no: string; title: string };
export type ConversationWorkspace = { kind: "personal"; case_id?: never } | { kind: "case"; case_id: number };
export type WorkRecord = WorkspaceCase & { module?: string; customer: string; status: string; owner: string; deadline?: string; days_remaining?: number | null; priority?: string };
export type WorkOverview = { todos: [string, number, number, string, number, number][]; my_tasks: WorkRecord[]; pending_contract_approvals: WorkRecord[]; pending_other_approvals: WorkRecord[]; visible_cases: WorkRecord[] };

export function errorText(error: unknown, label: string): string {
  return agentOperationError(error, label);
}
