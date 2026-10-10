import { useEffect, useRef, useState } from "react";
import { message } from "antd";
import { api } from "../api";
import { DEFAULT_AGENT_SKILL } from "../agentSkillRouting";
import { aiWordDocumentName, isAiWordGenerationRequest, isUsableAiDocumentContent } from "../legal/constants";
import { confirmCaseAgentDocument } from "../legal/services/agentDocumentConfirmation";
import { errorText, type Material, type PendingAction, type WorkspaceCase, type WorkspaceMessage, type WorkspaceSkill, type WorkspaceState, type WorkspaceStatus } from "./types";

const SUPPORTED_FILE = /\.(pdf|docx|xlsx|txt|png|jpe?g)$/i;
export const MATERIAL_ACCEPT = ".pdf,.docx,.xlsx,.txt,.png,.jpg,.jpeg";

export function usePersonalWorkspace() {
  const [status, setStatus] = useState<WorkspaceStatus | null>(null);
  const [state, setState] = useState<WorkspaceState>({ messages: [], pending_actions: [] });
  const [skills, setSkills] = useState<WorkspaceSkill[]>([]);
  const [skillId, setSkillId] = useState(DEFAULT_AGENT_SKILL);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [selectedCase, setSelectedCase] = useState<WorkspaceCase | null>(null);
  const [caseMaterials, setCaseMaterials] = useState<Material[]>([]);
  const [decisionId, setDecisionId] = useState("");
  const [decisionResult, setDecisionResult] = useState<unknown>();
  const [savedDocuments, setSavedDocuments] = useState<Record<number, string>>({});
  const requestRef = useRef<AbortController | null>(null);
  const uploadLock = useRef(false);
  const decisionLock = useRef(false);

  const refreshSkills = async () => {
    const { data } = await api.get<{ items: WorkspaceSkill[] }>("/agent/skills");
    setSkills(data.items);
    setSkillId((current) => data.items.some((item) => item.id === current && item.available) ? current : DEFAULT_AGENT_SKILL);
  };
  const load = async () => {
    setLoading(true);
    setLoadError("");
    try {
      const [statusResponse, stateResponse] = await Promise.all([
        api.get<WorkspaceStatus>("/personal-agent/status"), api.get<WorkspaceState>("/personal-agent/state"), refreshSkills(),
      ]);
      setStatus(statusResponse.data);
      setState(stateResponse.data);
      setSavedDocuments({});
    } catch (error) { setLoadError(errorText(error, "工作台加载失败")); }
    finally { setLoading(false); }
  };
  useEffect(() => { void load(); return () => requestRef.current?.abort(); }, []);

  const upload = async (files: File[]) => {
    if (!files.length || uploadLock.current || requestRef.current) return;
    if (materials.length + caseMaterials.length + files.length > 12) { message.warning("每次提问最多选择12份材料"); return; }
    if (files.some((file) => !SUPPORTED_FILE.test(file.name) || !file.size || file.size > 20 * 1024 * 1024)) {
      message.error("请选择20MB以内的 PDF、Word（.docx）、Excel（.xlsx）、TXT 或 PNG/JPG 图片"); return;
    }
    uploadLock.current = true;
    setUploading(true);
    try {
      for (const file of files) {
        const form = new FormData();
        form.append("file", file);
        form.append("category", "个人智能体材料");
        const { data } = await api.post<{ id: number; original_name: string }>("/attachments", form);
        setMaterials((current) => [...current, { id: data.id, name: data.original_name }]);
      }
    } catch (error) { message.error(errorText(error, "文件上传失败")); }
    finally { uploadLock.current = false; setUploading(false); }
  };

  const chooseCase = (item: WorkspaceCase | null) => { setSelectedCase(item); setCaseMaterials([]); };
  const send = async () => {
    const content = input.trim();
    if (!content || requestRef.current || uploadLock.current || loading || loadError || !status?.ready) return;
    const skill = skills.find((item) => item.id === skillId && item.available);
    if (!skill) { message.error("所选技能已停用或不存在，请重新选择"); return; }
    const controller = new AbortController();
    requestRef.current = controller;
    setSending(true);
    setInput("");
    const assistantIndex = state.messages.length + 1;
    const metadata = { skill_name: skill.name, case_id: selectedCase?.id, case_no: selectedCase?.serial_no };
    setState((current) => ({ ...current, messages: [...current.messages, { role: "user", content, ...metadata, attachments: [...materials, ...caseMaterials] }, { role: "assistant", content: "", ...metadata }] }));
    try {
      const response = await fetch("/api/v1/personal-agent/messages", {
        method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("access_token") || ""}` },
        body: JSON.stringify({ content, skill_id: skillId, attachment_ids: materials.map((item) => item.id), case_id: selectedCase?.id, document_ids: caseMaterials.map((item) => item.id) }), signal: controller.signal,
      });
      if (!response.ok || !response.body) {
        const detail = await response.text();
        throw new Error(detail || "智能体响应失败");
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let completed = false;
      let finalState: WorkspaceState | null = null;
      const consume = (chunk: string) => {
        buffer += chunk.replace(/\r\n/g, "\n");
        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() || "";
        for (const block of blocks) {
          const line = block.split("\n").find((item) => item.startsWith("data:"));
          if (!line) continue;
          const event = JSON.parse(line.slice(5).trim()) as { type: string; content?: string; detail?: string; state?: WorkspaceState };
          if (event.type === "delta") {
            setState((current) => ({ ...current, messages: current.messages.map((item, index) => index === assistantIndex ? { ...item, content: item.content + (event.content || "") } : item) }));
          } else if (event.type === "state" && event.state) { completed = true; finalState = event.state; setState(event.state); }
          else if (event.type === "error") throw new Error(event.detail || "智能体处理失败");
        }
      };
      while (true) {
        const { done, value } = await reader.read();
        if (done) { consume(decoder.decode()); break; }
        consume(decoder.decode(value, { stream: true }));
      }
      if (!completed) throw new Error("响应中断，未收到完整结果，请重新发送");
      const completedState = finalState as WorkspaceState | null;
      const finalMessage = completedState?.messages.at(-1);
      if (finalMessage?.can_save_document && isAiWordGenerationRequest(content) && isUsableAiDocumentContent(finalMessage.content) && !completedState?.pending_actions.some((action) => action.preview?.path?.endsWith("/ai-space/files"))) {
        saveWord(finalMessage, completedState!.messages.length - 1);
      }
      setMaterials([]);
      setCaseMaterials([]);
    } catch (error) {
      const stopped = (error as Error).name === "AbortError";
      setState((current) => ({ ...current, messages: current.messages.map((item, index) => index === assistantIndex ? { ...item, failed: !stopped, content: stopped ? item.content || "已停止生成" : errorText(error, "智能体处理失败") } : item) }));
      if (!stopped) setInput(content);
    } finally { requestRef.current = null; setSending(false); }
  };

  const decide = async (action: PendingAction, decision: "approved" | "rejected") => {
    if (decisionLock.current || sending) return false;
    decisionLock.current = true;
    setDecisionId(action.id);
    try {
      const { data } = await api.post<{ state: WorkspaceState; result?: unknown }>(`/personal-agent/actions/${action.id}/decision`, { decision }, { headers: { "X-OA-Agent-Confirmation": "frontend" } });
      setState(data.state);
      setDecisionResult(data.result);
      message.success(decision === "approved" ? "操作已完成" : "已取消操作");
      return true;
    } catch (error) { message.error(errorText(error, "操作未完成，请查看真实执行状态")); return false; }
    finally { decisionLock.current = false; setDecisionId(""); }
  };

  const saveWord = (item: WorkspaceMessage, index: number) => {
    if (!item.case_id || !item.content.trim()) return;
    const name = aiWordDocumentName("", item.content);
    confirmCaseAgentDocument({ caseId: item.case_id, serialNo: item.case_no || "", name, content: item.content, onSaved: async () => { setSavedDocuments((current) => ({ ...current, [index]: name })); } });
  };

  return { status, state, skills, skillId, setSkillId, input, setInput, loading, loadError, load, sending, upload, uploading, materials, setMaterials, selectedCase, chooseCase, caseMaterials, setCaseMaterials, send, decide, decisionId, decisionResult, stop: () => requestRef.current?.abort(), refreshSkills, saveWord, savedDocuments };
}
