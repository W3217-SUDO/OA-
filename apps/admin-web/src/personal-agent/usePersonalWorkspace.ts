import { useEffect, useRef, useState, type SetStateAction } from "react";
import { message } from "antd";
import { api } from "../api";
import { DEFAULT_AGENT_SKILL } from "../agentSkillRouting";
import { aiWordDocumentName, isAiWordGenerationRequest, isUsableAiDocumentContent } from "../legal/constants";
import { confirmCaseAgentDocument } from "../legal/services/agentDocumentConfirmation";
import { usePersonalConversations } from "./usePersonalConversations";
import { useConversationRuntime } from "./useConversationRuntime";
import { errorText, type Material, type PendingAction, type ResponseMode, type WorkspaceCase, type WorkspaceMessage, type WorkspaceSkill, type WorkspaceState, type WorkspaceStatus } from "./types";

const SUPPORTED_FILE = /\.(pdf|docx|xlsx|txt|png|jpe?g)$/i;
export const MATERIAL_ACCEPT = ".pdf,.docx,.xlsx,.txt,.png,.jpg,.jpeg";
type Draft = { input: string; skillId: string; responseMode: ResponseMode; materials: Material[]; caseMaterials: Material[]; selectedCase: WorkspaceCase | null; savedDocuments: Record<number, string>; decisionResult?: unknown };
const EMPTY_DRAFT: Draft = { input: "", skillId: DEFAULT_AGENT_SKILL, responseMode: "fast", materials: [], caseMaterials: [], selectedCase: null, savedDocuments: {} };

export function usePersonalWorkspace() {
  const [status, setStatus] = useState<WorkspaceStatus | null>(null);
  const [skills, setSkills] = useState<WorkspaceSkill[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [decisionId, setDecisionId] = useState("");
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const uploadLock = useRef(false);
  const decisionLock = useRef(false);
  const sendStarts = useRef(new Set<string>());
  const runtime = useConversationRuntime();
  const state = runtime.state;
  const id = state.conversation_id || "";
  const draft = drafts[id] || EMPTY_DRAFT;
  const { input, skillId, responseMode, materials, caseMaterials, selectedCase, savedDocuments, decisionResult } = draft;
  const sending = !!runtime.activities[id];
  const stopping = !!runtime.activities[id]?.stopping;
  const conversations = usePersonalConversations(runtime.activate);
  const updateDraft = <K extends keyof Draft>(target: string, key: K, value: SetStateAction<Draft[K]>) => {
    setDrafts((current) => {
      const previous = current[target] || EMPTY_DRAFT;
      const next = typeof value === "function" ? (value as (old: Draft[K]) => Draft[K])(previous[key]) : value;
      return { ...current, [target]: { ...previous, [key]: next } };
    });
  };
  const setInput = (value: SetStateAction<string>) => updateDraft(id, "input", value);
  const setSkillId = (value: string) => updateDraft(id, "skillId", value);
  const setResponseMode = (value: ResponseMode) => updateDraft(id, "responseMode", value);
  const setMaterials = (value: SetStateAction<Material[]>) => updateDraft(id, "materials", value);
  const setCaseMaterials = (value: SetStateAction<Material[]>) => updateDraft(id, "caseMaterials", value);
  const changeConversation = async (operation: () => Promise<WorkspaceState>) => {
    if (uploadLock.current || decisionLock.current || loading || sendStarts.current.has("")) throw new Error("请先完成当前文件或确认操作，再切换对话");
    await operation();
  };

  const refreshSkills = async () => {
    const { data } = await api.get<{ items: WorkspaceSkill[] }>("/agent/skills");
    setSkills(data.items);
    setDrafts((current) => Object.fromEntries(Object.entries(current).map(([key, value]) => [key, { ...value, skillId: data.items.some((item) => item.id === value.skillId && item.available) ? value.skillId : DEFAULT_AGENT_SKILL }])));
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
  const send = async () => {
    const content = input.trim();
    if (!content || stopping || sendStarts.current.has(id) || uploadLock.current || decisionLock.current || conversations.locked() || loading || loadError || !status?.ready) return;
    const skill = skills.find((item) => item.id === skillId && item.available);
    if (!skill) { message.error("所选技能已停用或不存在，请重新选择"); return; }
    // 只锁住启动阶段；模型生成期间允许其他对话独立发送。
    sendStarts.current.add(id);
    let target = id;
    try {
      if (runtime.running(id)) await runtime.stop(id);
      const conversation = id ? runtime.get(id) : await conversations.create();
      target = conversation.conversation_id!;
      if (!id) setDrafts((current) => ({ ...current, [target]: { ...draft, input: "" } }));
      else setInput("");
      const metadata = { skill_name: skill.name, case_id: selectedCase?.id, case_no: selectedCase?.serial_no };
      const generation = runtime.generate(conversation, { content, skill_id: skillId, attachment_ids: materials.map((item) => item.id), case_id: selectedCase?.id, document_ids: caseMaterials.map((item) => item.id), response_mode: status.supports_response_modes ? responseMode : "fast" }, { role: "user", content, ...metadata, attachments: [...materials, ...caseMaterials] }, metadata);
      updateDraft(target, "materials", []); updateDraft(target, "caseMaterials", []);
      sendStarts.current.delete(id);
      const completedState = await generation;
      const finalMessage = completedState?.messages.at(-1);
      if (finalMessage?.can_save_document && isAiWordGenerationRequest(content) && isUsableAiDocumentContent(finalMessage.content) && !completedState?.pending_actions.some((action) => action.preview?.path?.endsWith("/ai-space/files"))) saveWord(finalMessage, completedState!.messages.length - 1, target);
    } catch (error) {
      updateDraft(target, "input", (current) => current || content);
      message.error(errorText(error, "智能体处理失败"));
    } finally {
      sendStarts.current.delete(id);
      try { await conversations.refresh(); } catch (error) { message.error(errorText(error, "对话列表刷新失败")); }
    }
  };
  const stop = async () => { try { await runtime.stop(id); } catch (error) { message.error(errorText(error, "停止生成失败")); } };

  const decide = async (action: PendingAction, decision: "approved" | "rejected") => {
    if (decisionLock.current || runtime.running(id) || conversations.locked()) return false;
    decisionLock.current = true; setDecisionId(action.id);
    try {
      const { data } = await api.post<{ state: WorkspaceState; result?: unknown }>(`/personal-agent/actions/${action.id}/decision`, { conversation_id: state.conversation_id, decision }, { headers: { "X-OA-Agent-Confirmation": "frontend" } });
      runtime.replace(data.state); updateDraft(id, "decisionResult", data.result);
      message.success(decision === "approved" ? "操作已完成" : "已取消操作"); return true;
    } catch (error) { message.error(errorText(error, "操作未完成，请查看真实执行状态")); return false; }
    finally { decisionLock.current = false; setDecisionId(""); }
  };

  return { status, state, skills, skillId, setSkillId, input, setInput, loading, loadError, load, sending, stopping, responseMode, setResponseMode, progress: runtime.activities[id]?.progress || "", upload, uploading, materials, setMaterials, selectedCase, chooseCase, caseMaterials, setCaseMaterials, send, decide, decisionId, decisionResult, stop, refreshSkills, saveWord, savedDocuments,
    conversations: conversations.items, conversationBusy: conversations.busy, runningIds: Object.keys(runtime.activities),
    createConversation: () => changeConversation(conversations.create), selectConversation: (target: string) => target === state.conversation_id ? Promise.resolve() : changeConversation(() => conversations.select(target)),
    deleteConversation: (target: string) => changeConversation(async () => { const next = await conversations.remove(target); runtime.forget(target); setDrafts((current) => { const updated = { ...current }; delete updated[target]; return updated; }); return next; }),
  };
}
