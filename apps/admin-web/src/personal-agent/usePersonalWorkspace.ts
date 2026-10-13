import { useEffect, useRef, useState, type SetStateAction } from "react";
import { message } from "antd";
import { api } from "../api";
import { DEFAULT_AGENT_SKILL } from "../agentSkillRouting";
import { aiWordDocumentName, isAiWordGenerationRequest, isUsableAiDocumentContent } from "../legal/constants";
import { confirmCaseAgentDocument } from "../legal/services/agentDocumentConfirmation";
import { usePersonalConversations } from "./usePersonalConversations";
import { useConversationRuntime } from "./useConversationRuntime";
import { errorText, type ConfirmationDetail, type ConversationSnapshot, type DecisionFailure, type Material, type PendingAction, type ResponseMode, type WorkspaceCase, type WorkspaceMessage, type WorkspaceSkill, type WorkspaceState, type WorkspaceStatus } from "./types";

const SUPPORTED_FILE = /\.(pdf|docx|xlsx|txt|png|jpe?g)$/i;
export const MATERIAL_ACCEPT = ".pdf,.docx,.xlsx,.txt,.png,.jpg,.jpeg";
type Draft = { input: string; skillId: string; responseMode: ResponseMode; materials: Material[]; caseMaterials: Material[]; selectedCase: WorkspaceCase | null; savedDocuments: Record<number, string>; decisionResult?: unknown; decisionFailures: Record<string, DecisionFailure> };
const EMPTY_DRAFT: Draft = { input: "", skillId: DEFAULT_AGENT_SKILL, responseMode: "fast", materials: [], caseMaterials: [], selectedCase: null, savedDocuments: {}, decisionFailures: {} };

export function usePersonalWorkspace() {
  const [status, setStatus] = useState<WorkspaceStatus | null>(null);
  const [skills, setSkills] = useState<WorkspaceSkill[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [decisionId, setDecisionId] = useState("");
  const [dismissalId, setDismissalId] = useState("");
  const [dismissedByConversation, setDismissedByConversation] = useState<Record<string, string[]>>({});
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const draftsRef = useRef<Record<string, Draft>>({});
  const uploadLock = useRef(false);
  const decisionLock = useRef(false);
  const dismissalLock = useRef(false);
  const sendStarts = useRef(new Set<string>());
  const runtime = useConversationRuntime();
  const state = runtime.state;
  const id = state.conversation_id || "";
  const draft = drafts[id] || EMPTY_DRAFT;
  const { input, skillId, responseMode, materials, caseMaterials, selectedCase, savedDocuments, decisionResult, decisionFailures } = draft;
  const sending = !!runtime.activities[id];
  const stopping = !!runtime.activities[id]?.stopping;
  const conversations = usePersonalConversations(runtime.activate);
  const updateDraft = <K extends keyof Draft>(target: string, key: K, value: SetStateAction<Draft[K]>) => {
    const current = draftsRef.current;
    const previous = current[target] || EMPTY_DRAFT;
    const next = typeof value === "function" ? (value as (old: Draft[K]) => Draft[K])(previous[key]) : value;
    draftsRef.current = { ...current, [target]: { ...previous, [key]: next } };
    setDrafts(draftsRef.current);
  };
  const setInput = (value: SetStateAction<string>) => updateDraft(id, "input", value);
  const updateDecisionFailure = (target: string, actionId: string, failure: DecisionFailure | undefined) => updateDraft(target, "decisionFailures", (current) => {
    const next = { ...current };
    if (failure) next[actionId] = failure;
    else delete next[actionId];
    return next;
  });
  const setSkillId = (value: string) => updateDraft(id, "skillId", value);
  const setResponseMode = (value: ResponseMode) => updateDraft(id, "responseMode", value);
  const setMaterials = (value: SetStateAction<Material[]>) => updateDraft(id, "materials", value);
  const setCaseMaterials = (value: SetStateAction<Material[]>) => updateDraft(id, "caseMaterials", value);
  const changeConversation = async (operation: () => Promise<WorkspaceState>) => {
    if (uploadLock.current || decisionLock.current || dismissalLock.current || loading || sendStarts.current.has("")) throw new Error("请先完成当前文件、确认或收起操作，再切换对话");
    // 返回切换后的会话，便于调用方紧接着把问题发给这条对话。
    return await operation();
  };

  const refreshSkills = async () => {
    const { data } = await api.get<{ items: WorkspaceSkill[] }>("/agent/skills");
    setSkills(data.items);
    draftsRef.current = Object.fromEntries(Object.entries(draftsRef.current).map(([key, value]) => [key, { ...value, skillId: data.items.some((item) => item.id === value.skillId && item.available) ? value.skillId : DEFAULT_AGENT_SKILL }]));
    setDrafts(draftsRef.current);
  };
  const load = async () => {
    if (runtime.anyRunning()) { message.warning("请先停止正在运行的对话再刷新"); return; }
    setLoading(true); setLoadError("");
    try {
      runtime.reset();
      const [statusResponse] = await Promise.all([api.get<WorkspaceStatus>("/personal-agent/status"), conversations.load(), refreshSkills()]);
      setStatus(statusResponse.data);
    } catch (error) { setLoadError(errorText(error, "工作台加载失败")); }
    finally { setLoading(false); }
  };
  useEffect(() => { void load(); }, []);

  const upload = async (files: File[]) => {
    if (!files.length || uploadLock.current || conversations.locked()) return;
    if (materials.length + caseMaterials.length + files.length > 12) { message.warning("每次提问最多选择12份材料"); return; }
    if (files.some((file) => !SUPPORTED_FILE.test(file.name) || !file.size || file.size > 20 * 1024 * 1024)) {
      message.error("请选择20MB以内的 PDF、Word（.docx）、Excel（.xlsx）、TXT 或 PNG/JPG 图片"); return;
    }
    uploadLock.current = true; setUploading(true);
    try {
      for (const file of files) {
        const form = new FormData(); form.append("file", file); form.append("category", "个人智能体材料");
        const { data } = await api.post<{ id: number; original_name: string }>("/attachments", form);
        setMaterials((current) => [...current, { id: data.id, name: data.original_name }]);
      }
    } catch (error) { message.error(errorText(error, "文件上传失败")); }
    finally { uploadLock.current = false; setUploading(false); }
  };

  const chooseCase = (item: WorkspaceCase | null) => { updateDraft(id, "selectedCase", item); setCaseMaterials([]); };
  const saveWord = (item: WorkspaceMessage, index: number, target = id) => {
    if (!item.case_id || !item.content.trim()) return;
    const name = aiWordDocumentName("", item.content);
    confirmCaseAgentDocument({ caseId: item.case_id, serialNo: item.case_no || "", name, content: item.content, onSaved: async () => { updateDraft(target, "savedDocuments", (current) => ({ ...current, [index]: name })); } });
  };
  // override 用于工作台提醒和快捷问题：它们把完整问题直接交给智能体，不经过输入框。
  // target 用于把问题发给一条刚建的对话，避免沿用闭包里的旧会话。
  const send = async (override?: string, target?: WorkspaceState) => {
    const targetId = target?.conversation_id || id;
    const targetDraft = draftsRef.current[targetId] || EMPTY_DRAFT;
    const { skillId, responseMode, materials, caseMaterials, selectedCase } = targetDraft;
    const content = (override ?? targetDraft.input).trim();
    if (!content || runtime.stopping(targetId) || sendStarts.current.has(targetId) || uploadLock.current || decisionLock.current || conversations.locked() || loading || loadError || !status?.ready) return;
    const skill = skills.find((item) => item.id === skillId && item.available);
    if (!skill) { message.error("所选技能已停用或不存在，请重新选择"); return; }
    // 只锁住启动阶段；模型生成期间允许其他对话独立发送。
    sendStarts.current.add(targetId);
    let written = targetId;
    let starting = true;
    let beforeSend: Draft | undefined;
    let consumedDraft: Draft | undefined;
    try {
      if (runtime.running(targetId)) await runtime.stop(targetId);
      const conversation = targetId ? runtime.get(targetId) : await conversations.create();
      written = conversation.conversation_id!;
      if (!targetId) {
        const current = { ...draftsRef.current, [written]: draftsRef.current[""] || targetDraft };
        delete current[""];
        draftsRef.current = current;
        setDrafts(current);
      }
      const metadata = { skill_name: skill.name, case_id: selectedCase?.id, case_no: selectedCase?.serial_no };
      const generation = runtime.generate(conversation, { content, skill_id: skillId, attachment_ids: materials.map((item) => item.id), case_id: selectedCase?.id, document_ids: caseMaterials.map((item) => item.id), response_mode: status.supports_response_modes ? responseMode : "fast" }, { role: "user", content, ...metadata, attachments: [...materials, ...caseMaterials] }, metadata);
      beforeSend = draftsRef.current[written] || EMPTY_DRAFT;
      // 只消费本轮快照，停止等待期间的新输入和新材料留给下一轮。
      if (override === undefined) updateDraft(written, "input", (current) => current === targetDraft.input ? "" : current);
      updateDraft(written, "materials", (current) => current.filter((item) => !materials.some((sent) => sent.id === item.id)));
      updateDraft(written, "caseMaterials", (current) => current.filter((item) => !caseMaterials.some((sent) => sent.id === item.id)));
      consumedDraft = draftsRef.current[written];
      sendStarts.current.delete(targetId);
      starting = false;
      const completedState = await generation;
      const finalMessage = completedState?.messages.at(-1);
      if (finalMessage?.can_save_document && isAiWordGenerationRequest(content) && isUsableAiDocumentContent(finalMessage.content) && !completedState?.pending_actions.some((action) => action.preview?.path?.endsWith("/ai-space/files"))) saveWord(finalMessage, completedState!.messages.length - 1, written);
    } catch (error) {
      if (beforeSend && consumedDraft) {
        const previous = beforeSend;
        const consumed = consumedDraft;
        updateDraft(written, "input", (current) => current === consumed.input ? previous.input : current);
        updateDraft(written, "materials", (current) => current === consumed.materials ? previous.materials : current);
        updateDraft(written, "caseMaterials", (current) => current === consumed.caseMaterials ? previous.caseMaterials : current);
      }
      message.error(errorText(error, "智能体处理失败"));
    } finally {
      if (starting) sendStarts.current.delete(targetId);
      try { await conversations.refresh(); } catch (error) { message.error(errorText(error, "对话列表刷新失败")); }
    }
  };
  const stop = async () => { try { await runtime.stop(id); } catch (error) { message.error(errorText(error, "停止生成失败")); } };

  const decide = async (action: PendingAction, decision: "approved" | "rejected") => {
    if (decisionLock.current) return false;
    if (loading || conversations.locked() || sendStarts.current.has(id)) throw new Error("正在加载或切换对话，请完成后再确认");
    if (!id) throw new Error("请先选择待确认操作所属的对话");
    if (draftsRef.current[id]?.decisionFailures[action.id] && runtime.get(id).pending_actions.some((item) => item.id === action.id && item.status === "pending")) throw new Error("请先从历史记录读取最新详情，再决定该操作，禁止直接重复提交");
    decisionLock.current = true; setDecisionId(action.id);
    try {
      // 先等待服务端停止生成并释放锁；已确认写入仍由服务端拒绝中断。
      if (runtime.running(id)) await runtime.stop(id);
      const current = runtime.get(id);
      if (!current.pending_actions.some((item) => item.id === action.id && item.status === "pending")) throw new Error("待确认操作不存在或已处理，请核对最新状态");
      let response;
      try {
        response = await api.post<{ state: WorkspaceState; result?: unknown }>(`/personal-agent/actions/${action.id}/decision`, { conversation_id: id, decision }, { headers: { "X-OA-Agent-Confirmation": "frontend" } });
      } catch (error) {
        const failureMessage = errorText(error, "确认操作失败");
        updateDecisionFailure(id, action.id, { actionId: action.id, message: failureMessage, state: "syncing" });
        // 决定可能已在服务端落库；只读回查会话，不重试写入或把失败当成功。
        try {
          const { data } = await api.get<ConversationSnapshot>("/personal-agent/conversations", { timeout: 15000 });
          if (data.state.conversation_id !== id) throw new Error("服务端当前对话已变化，请刷新核对原操作状态");
          runtime.replace(data.state);
          updateDecisionFailure(id, action.id, { actionId: action.id, message: failureMessage, state: "verified" });
        } catch (syncError) {
          const text = `${failureMessage}；${errorText(syncError, "最新对话状态读取失败")}，禁止重复提交`;
          updateDecisionFailure(id, action.id, { actionId: action.id, message: text, state: "unknown" });
          throw new Error(text, { cause: error });
        }
        throw error;
      }
      const { data } = response;
      if (data.state.conversation_id !== id) throw new Error("确认响应对话编号不匹配，请核对实际执行状态，禁止重复提交");
      runtime.replace(data.state); updateDraft(id, "decisionResult", data.result);
      message.success(decision === "approved" ? "操作已完成" : "已取消操作"); return true;
    } finally { decisionLock.current = false; setDecisionId(""); }
  };

  const dismissActions = async (actions: PendingAction[]) => {
    if (dismissalLock.current || decisionLock.current || loading || conversations.locked() || !id) throw new Error("请完成当前操作后再收起");
    const actionIds = actions.map((action) => action.id);
    if (!actionIds.length || actionIds.some((actionId) => !state.pending_actions.some((item) => item.id === actionId))) throw new Error("操作卡不存在，请核对当前对话");
    dismissalLock.current = true; setDismissalId(actionIds[0]);
    try {
      const { data } = await api.post<{ state: WorkspaceState }>(`/personal-agent/conversations/${encodeURIComponent(id)}/actions/dismiss`, { action_ids: actionIds });
      if (data.state.conversation_id !== id || actionIds.some((actionId) => !data.state.dismissed_action_ids.includes(actionId))) throw new Error("收起响应不匹配，请刷新核对展示状态");
      // 仅保留已持久化的展示结果，避免同会话较早的流式快照重新展开旧卡。
      setDismissedByConversation((current) => ({ ...current, [id]: data.state.dismissed_action_ids }));
    } finally { dismissalLock.current = false; setDismissalId(""); }
  };
  const dismissAction = (action: PendingAction) => dismissActions([action]);

  const reopenConfirmation = async (detail: ConfirmationDetail) => {
    const target = detail.conversation_id;
    const action = detail.action;
    if (!detail.can_decide || detail.item.status !== "pending" || !target || !action || action.status !== "pending" || detail.item.action_id !== action.id) throw new Error("该记录不是可恢复的待确认操作");
    if (runtime.running(target)) throw new Error("请先停止所属对话的回答，再恢复待确认操作");
    const next = await changeConversation(() => conversations.select(target));
    if (next.conversation_id !== target) throw new Error("恢复响应对话不匹配，不能打开确认");
    runtime.replace(next);
    const current = next.pending_actions.find((item) => item.id === action.id);
    if (!current || current.status !== "pending") throw new Error("操作已处理或不再可确认，请查看最新状态");
    updateDecisionFailure(target, action.id, undefined);
    return { conversationId: target, actionId: current.id };
  };
  const dismissedIds = new Set([...state.dismissed_action_ids, ...(dismissedByConversation[id] ?? [])]);
  const visibleActions = state.pending_actions.filter((action) => !dismissedIds.has(action.id));

  const hideDecisionFailure = (actionId: string) => {
    const failure = draftsRef.current[id]?.decisionFailures[actionId];
    if (failure) updateDecisionFailure(id, actionId, { ...failure, hidden: true });
  };
  return { status, state, skills, skillId, setSkillId, input, setInput, loading, loadError, load, sending, stopping, responseMode, setResponseMode, progress: runtime.activities[id]?.progress || "", upload, uploading, materials, setMaterials, selectedCase, chooseCase, caseMaterials, setCaseMaterials, send, decide, decisionId, decisionResult, decisionFailures, hideDecisionFailure, stop, refreshSkills, saveWord, savedDocuments, dismissAction, dismissActions, dismissalId, visibleActions, reopenConfirmation,
    conversations: conversations.items, conversationBusy: conversations.busy, runningIds: Object.keys(runtime.activities),
    createConversation: () => changeConversation(conversations.create), selectConversation: (target: string) => target === state.conversation_id ? Promise.resolve() : changeConversation(() => conversations.select(target)),
    deleteConversation: (target: string) => changeConversation(async () => { const next = await conversations.remove(target); runtime.forget(target); const updated = { ...draftsRef.current }; delete updated[target]; draftsRef.current = updated; setDrafts(updated); return next; }),
  };
}
