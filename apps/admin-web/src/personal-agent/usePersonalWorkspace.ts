import { useEffect, useRef, useState, type SetStateAction } from "react";
import { message } from "antd";
import { api } from "../api";
import { aiExcelDocumentName, aiWordDocumentName, isAiSpreadsheetGenerationRequest, isAiWordGenerationRequest, isUsableAiDocumentContent } from "../legal/constants";
import { confirmCaseAgentDocument } from "../legal/services/agentDocumentConfirmation";
import { confirmPersonalAiDocument } from "./personalAiDocumentConfirmation";
import { usePersonalConversations } from "./usePersonalConversations";
import { useConversationRuntime } from "./useConversationRuntime";
import { EMPTY_PERSONAL_DRAFT as EMPTY_DRAFT, usePersonalDrafts } from "./usePersonalDrafts";
import { conversationDraftKey, conversationWorkspaceKey, PERSONAL_CONVERSATION_WORKSPACE, requireConversationWorkspace } from "./conversationWorkspace";
import { errorText, workspaceDocumentSaveTarget, type ConfirmationDetail, type ConversationWorkspace, type DecisionFailure, type Material, type PendingAction, type ResponseMode, type WorkspaceCase, type WorkspaceMessage, type WorkspaceSkill, type WorkspaceState, type WorkspaceStatus } from "./types";

const SUPPORTED_FILE = /\.(pdf|docx|xlsx|txt|png|jpe?g)$/i;
export const MATERIAL_ACCEPT = ".pdf,.docx,.xlsx,.txt,.png,.jpg,.jpeg";
type Draft = typeof EMPTY_DRAFT;

export function usePersonalWorkspace() {
  const [status, setStatus] = useState<WorkspaceStatus | null>(null);
  const [skills, setSkills] = useState<WorkspaceSkill[]>([]);
  const [initialLoading, setLoading] = useState(true);
  const [initialLoadError, setLoadError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [decisionId, setDecisionId] = useState("");
  const [dismissalId, setDismissalId] = useState("");
  const [documentRevision, setDocumentRevision] = useState(0);
  const [dismissedByConversation, setDismissedByConversation] = useState<Record<string, string[]>>({});
  const drafts = usePersonalDrafts();
  const draftsRef = drafts.ref;
  const uploadLock = useRef(false);
  const decisionLock = useRef(false);
  const dismissalLock = useRef(false);
  const sendStarts = useRef(new Set<string>());
  const documentConfirmations = useRef(new Set<string>());
  const runtime = useConversationRuntime();
  const conversations = usePersonalConversations(runtime.activate, runtime.remember);
  const loading = initialLoading || conversations.loading;
  const loadError = initialLoadError || conversations.error;
  const state = runtime.state;
  const id = state.conversation_id || "";
  const draftKey = conversationDraftKey(id, conversations.workspace);
  const draft = drafts.items[draftKey] || EMPTY_DRAFT;
  const { input, skillId, responseMode, materials, caseMaterials, selectedCase, savedDocuments, savedSpreadsheets, decisionResult, decisionFailures } = draft;
  const sending = !!runtime.activities[id];
  const stopping = !!runtime.activities[id]?.stopping;
  const updateDraft = drafts.update;
  const setInput = (value: SetStateAction<string>) => updateDraft(draftKey, "input", value);
  const updateDecisionFailure = (target: string, actionId: string, failure: DecisionFailure | undefined) => updateDraft(target, "decisionFailures", (current) => {
    const next = { ...current };
    if (failure) next[actionId] = failure;
    else delete next[actionId];
    return next;
  });
  const setSkillId = (value: string) => updateDraft(draftKey, "skillId", value);
  const setResponseMode = (value: ResponseMode) => updateDraft(draftKey, "responseMode", value);
  const setMaterials = (value: SetStateAction<Material[]>) => updateDraft(draftKey, "materials", value);
  const setCaseMaterials = (value: SetStateAction<Material[]>) => updateDraft(draftKey, "caseMaterials", value);
  const changeConversation = async (operation: () => Promise<WorkspaceState>) => {
    if (uploadLock.current || decisionLock.current || dismissalLock.current || loading || sendStarts.current.has(draftKey)) throw new Error("请先完成当前文件、确认或收起操作，再切换对话");
    // 返回切换后的会话，便于调用方紧接着把问题发给这条对话。
    return await operation();
  };

  const refreshSkills = async () => {
    const { data } = await api.get<{ items: WorkspaceSkill[] }>("/agent/skills");
    setSkills(data.items);
    drafts.refreshSkills(data.items);
  };
  const load = async () => {
    if (runtime.anyRunning()) { message.warning("请先停止正在运行的对话再刷新"); return; }
    setLoading(true); setLoadError("");
    try {
      runtime.reset();
      const [globalResult] = await Promise.allSettled([
        Promise.all([api.get<WorkspaceStatus>("/personal-agent/status"), refreshSkills()]).then(([response]) => setStatus(response.data)),
        conversations.load(),
      ]);
      if (globalResult.status === "rejected") throw globalResult.reason;
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
        try {
          const { data } = await api.post<{
            attachment_id: number;
            attachment: { original_name: string };
            cache_status?: "cached" | "failed";
            reading_status?: "readable" | "failed" | "pending";
            reading_error?: string | null;
            reading?: { status?: "parsed" | "visual" | "failed" | "unavailable"; detail?: string; cache_status?: string };
          }>("/agent-tools/upload", form);
          const readingStatus = data.reading_status || data.reading?.status;
          const readingError = data.reading_error || data.reading?.detail || undefined;
          const status = readingStatus === "readable" || readingStatus === "parsed" || readingStatus === "visual" ? "readable" : readingStatus === "failed" || readingStatus === "unavailable" || data.cache_status === "failed" ? "failed" : "cached";
          const material: Material = { id: data.attachment_id, name: data.attachment.original_name, status, error: readingError };
          setMaterials((current) => [...current, material]);
          if (status === "failed") message.error(`${material.name}：${material.error || "文件已缓存，但正文无法读取"}`);
          else if (status === "cached") message.info(`${material.name}：已缓存，发送问题时读取正文`);
        } catch (error) {
          message.error(`${file.name}：${errorText(error, "文件上传失败")}`);
        }
      }
    } catch (error) { message.error(errorText(error, "文件上传失败")); }
    finally { uploadLock.current = false; setUploading(false); }
  };

  const chooseCase = (item: WorkspaceCase | null) => { updateDraft(draftKey, "selectedCase", item); setCaseMaterials([]); };
  const chooseCaseMaterials = (item: WorkspaceCase, materials: Material[]) => drafts.chooseMaterials(draftKey, item, materials);
  const saveWord = async (item: WorkspaceMessage, index: number, target = id) => {
    const current = runtime.get(target);
    const source = current.messages[index];
    if (!target || !source || source.role !== "assistant" || source.content !== item.content || !source.content.trim() || source.failed || source.stopped || (runtime.running(target) && index === current.messages.length - 1)) { message.error("原回答尚未完整生成或已变化，请核对当前会话后保存"); return; }
    const destination = workspaceDocumentSaveTarget(source);
    if (!destination) { message.error(source.personal_document_save_error || "当前回答不具备文档保存能力"); return; }
    const name = aiWordDocumentName("", source.content);
    const onSaved = (savedName: string) => {
      updateDraft(target, "savedDocuments", (current) => ({ ...current, [index]: savedName }));
      setDocumentRevision((value) => value + 1);
    };
    if (destination === "case") {
      confirmCaseAgentDocument({ caseId: source.case_id!, serialNo: source.case_no || "", name, content: source.content, onSaved: async () => onSaved(name) });
      return;
    }
    const key = `${target}:${index}`;
    if (documentConfirmations.current.has(key) || draftsRef.current[target]?.savedDocuments[index]) return;
    documentConfirmations.current.add(key);
    try {
      await confirmPersonalAiDocument({ conversationId: target, messageIndex: index, name, content: source.content, onSaved: (file) => onSaved(file.name) });
    } catch (error) { message.error(errorText(error, "个人文档保存未完成")); }
    finally { documentConfirmations.current.delete(key); }
  };
  const saveSpreadsheet = async (item: WorkspaceMessage, index: number, target = id) => {
    const current = runtime.get(target);
    const source = current.messages[index];
    if (!target || !source || source.role !== "assistant" || source.content !== item.content || !source.content.trim() || source.failed || source.stopped || (runtime.running(target) && index === current.messages.length - 1)) { message.error("原回答尚未完整生成或已变化，请核对当前会话后保存"); return; }
    if (!source.can_save_spreadsheet || workspaceDocumentSaveTarget(source) !== "personal") { message.error(source.personal_document_save_error || "当前回答没有可保存的 Excel 表格"); return; }
    const key = `xlsx:${target}:${index}`;
    if (documentConfirmations.current.has(key) || draftsRef.current[target]?.savedSpreadsheets[index]) return;
    documentConfirmations.current.add(key);
    try {
      const name = aiExcelDocumentName("", source.content);
      await confirmPersonalAiDocument({ conversationId: target, messageIndex: index, name, content: source.content, format: "xlsx", onSaved: (file) => {
        updateDraft(target, "savedSpreadsheets", (current) => ({ ...current, [index]: file.name }));
        setDocumentRevision((value) => value + 1);
      } });
    } catch (error) { message.error(errorText(error, "个人 Excel 保存未完成")); }
    finally { documentConfirmations.current.delete(key); }
  };
  // override 用于工作台提醒和快捷问题：它们把完整问题直接交给智能体，不经过输入框。
  // target 用于把问题发给一条刚建的对话，避免沿用闭包里的旧会话。
  const send = async (override?: string, target?: WorkspaceState) => {
    const view = conversations.capture();
    const targetId = target?.conversation_id || id;
    const targetKey = conversationDraftKey(targetId, view.workspace);
    const targetDraft = draftsRef.current[targetKey] || EMPTY_DRAFT;
    const { skillId, responseMode, materials, caseMaterials, selectedCase } = targetDraft;
    const content = (override ?? targetDraft.input).trim();
    if (!content || runtime.stopping(targetId) || sendStarts.current.has(targetKey) || uploadLock.current || decisionLock.current || conversations.locked() || loading || loadError || !status?.ready) return;
    const unreadableMaterials = materials.filter((item) => item.status === "failed");
    if (unreadableMaterials.length) {
      message.error(`请先移除无法读取的材料：${unreadableMaterials.map((item) => item.name).join("、")}`);
      return;
    }
    const skill = skills.find((item) => item.id === skillId && item.available);
    if (!skill) { message.error("所选技能已停用或不存在，请重新选择"); return; }
    // 只锁住启动阶段；模型生成期间允许其他对话独立发送。
    sendStarts.current.add(targetKey);
    let written = targetKey;
    let starting = true;
    let beforeSend: Draft | undefined;
    let consumedDraft: Draft | undefined;
    try {
      if (view.workspace && targetId && conversationWorkspaceKey(requireConversationWorkspace((target || runtime.get(targetId)).workspace)) !== conversationWorkspaceKey(view.workspace)) throw new Error("目标对话不属于当前空间，请重新选择后发送");
      if (runtime.running(targetId)) await runtime.stop(targetId);
      const conversation = targetId ? runtime.get(targetId) : await conversations.create(view);
      written = conversation.conversation_id!;
      if (!targetId) {
        drafts.move(targetKey, written);
      }
      const referencedCase = view.workspace && !caseMaterials.length ? null : selectedCase;
      const metadata = { skill_name: skill.name, case_id: referencedCase?.id, case_no: referencedCase?.serial_no };
      const generation = runtime.generate(conversation, { content, skill_id: skillId, attachment_ids: materials.map((item) => item.id), case_id: referencedCase?.id, document_ids: caseMaterials.map((item) => item.id), response_mode: status.supports_response_modes ? responseMode : "fast", ...(view.workspace ? { workspace: view.workspace } : {}) }, { role: "user", content, ...metadata, attachments: [...materials, ...caseMaterials] }, metadata);
      beforeSend = draftsRef.current[written] || EMPTY_DRAFT;
      // 只消费本轮快照，停止等待期间的新输入和新材料留给下一轮。
      if (override === undefined) updateDraft(written, "input", (current) => current === targetDraft.input ? "" : current);
      updateDraft(written, "materials", (current) => current.filter((item) => !materials.some((sent) => sent.id === item.id)));
      updateDraft(written, "caseMaterials", (current) => current.filter((item) => !caseMaterials.some((sent) => sent.id === item.id)));
      consumedDraft = draftsRef.current[written];
      sendStarts.current.delete(targetKey);
      starting = false;
      const completedState = await generation;
      const finalMessage = completedState?.messages.at(-1);
      if (finalMessage?.can_save_document && isAiWordGenerationRequest(content) && isUsableAiDocumentContent(finalMessage.content) && !completedState?.pending_actions.some((action) => action.preview?.path?.endsWith("/ai-space/files"))) saveWord(finalMessage, completedState!.messages.length - 1, written);
      if (finalMessage?.can_save_spreadsheet && isAiSpreadsheetGenerationRequest(content) && isUsableAiDocumentContent(finalMessage.content) && !completedState?.pending_actions.some((action) => action.preview?.path?.endsWith("/ai-space/files"))) saveSpreadsheet(finalMessage, completedState!.messages.length - 1, written);
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
      if (starting) sendStarts.current.delete(targetKey);
      try { await conversations.refresh(view); } catch (error) { message.error(errorText(error, "对话列表刷新失败")); }
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
          const data = await conversations.read(conversations.capture(), 15000);
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
  const selectWorkspace = async (workspace: ConversationWorkspace) => {
    if (uploadLock.current || decisionLock.current || dismissalLock.current || conversations.locked() || loading) throw new Error("请先完成当前文件、确认或切换操作，再打开空间");
    if (workspace.kind === "case" && loadError) throw new Error("工作区加载失败，请先重试或返回个人空间");
    return conversations.openWorkspace(workspace, true);
  };
  const setProjectMode = async (enabled: boolean) => {
    try { await conversations.openWorkspace(enabled ? PERSONAL_CONVERSATION_WORKSPACE : undefined); }
    catch (error) { message.error(errorText(error, "空间切换失败")); }
  };
  return { status, state, skills, skillId, setSkillId, input, setInput, loading, loadError, load, sending, stopping, responseMode, setResponseMode, progress: runtime.activities[id]?.progress || "", upload, uploading, materials, setMaterials, selectedCase, chooseCase, chooseCaseMaterials, caseMaterials, setCaseMaterials, send, decide, decisionId, decisionResult, decisionFailures, hideDecisionFailure, stop, refreshSkills, saveWord, saveSpreadsheet, savedDocuments, savedSpreadsheets, documentRevision, dismissAction, dismissActions, dismissalId, visibleActions, reopenConfirmation, draftKey,
    currentWorkspace: conversations.workspace, workspaceProjects: conversations.projects, selectWorkspace, setProjectMode,
    conversations: conversations.items, conversationBusy: conversations.busy, runningIds: Object.keys(runtime.activities),
    createConversation: () => changeConversation(() => conversations.create()), selectConversation: (target: string) => target === state.conversation_id ? Promise.resolve() : changeConversation(() => conversations.select(target)),
    deleteConversation: (target: string) => changeConversation(async () => { const next = await conversations.remove(target); runtime.forget(target); drafts.remove(target); return next; }),
  };
}
