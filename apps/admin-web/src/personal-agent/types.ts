import type { AgentSkill } from "../agentSkillRouting";
import type { AgentActionPreview } from "../AgentOperationPreview";

export type WorkspaceSkill = AgentSkill & { custom?: boolean; enabled?: boolean; instruction?: string };
export type ResponseMode = "fast" | "deep";
export type Material = { id: number; name: string; case_id?: number };
export type WorkspaceMessage = { role: "user" | "assistant"; content: string; created_at?: string; skill_name?: string; case_id?: number; case_no?: string; can_save_document?: boolean; attachments?: Material[]; failed?: boolean };
export type PendingAction = { id: string; type: string; summary: string; payload?: Record<string, unknown>; preview?: AgentActionPreview; status: "pending" | "approved" | "rejected" };
export type WorkspaceState = { messages: WorkspaceMessage[]; pending_actions: PendingAction[]; structured_results?: unknown[] };
export type WorkspaceCommand = { id: string; label: string; prompt: string; skill_id: string; icon: string };
export type WorkspaceStatus = { ready: boolean; model: string; supports_response_modes?: boolean; commands: WorkspaceCommand[]; identity: { display_name?: string; department?: string; role?: string; permission_role?: string; staff_role?: string; position?: string } };
export type WorkspaceCase = { id: number; serial_no: string; title: string };
export type WorkRecord = WorkspaceCase & { module?: string; customer: string; status: string; owner: string; deadline?: string; days_remaining?: number | null; priority?: string };
export type WorkOverview = { todos: [string, number, number, string, number, number][]; my_tasks: WorkRecord[]; pending_contract_approvals: WorkRecord[]; pending_other_approvals: WorkRecord[]; visible_cases: WorkRecord[] };

export function errorText(error: unknown, label: string): string {
  const value = error as { response?: { data?: { detail?: string } }; message?: string };
  return value.response?.data?.detail || value.message || label;
}
