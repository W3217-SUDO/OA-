import { message } from "antd";
import { DEFAULT_AGENT_SKILL, encodeAgentSkillMessage, type AgentSkill } from "../../agentSkillRouting";
import { api } from "../../api";
import { AGENT_DOCUMENT_LIMIT, aiWordDocumentName, isAiWordGenerationRequest, isExistingAnswerWordConversionRequest, isUsableAiDocumentContent } from "../constants";
import type { CaseAgentAction, CaseAgentAttachment, CaseAgentDocument, CaseAgentState, CaseAgentStatus, CaseRow } from "../types";
/** legal assistant operations; dependencies are read when each operation runs. */
export interface CaseAssistantDependencies {
    readonly setAgentLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setAgentStatus: React.Dispatch<React.SetStateAction<CaseAgentStatus | null>>;
    readonly setAgentState: React.Dispatch<React.SetStateAction<CaseAgentState | null>>;
    readonly setAgentDocuments: React.Dispatch<React.SetStateAction<CaseAgentDocument[]>>;
    readonly setAgentDocumentIds: React.Dispatch<React.SetStateAction<number[]>>;
    readonly setAgentSkillId: React.Dispatch<React.SetStateAction<string>>;
    readonly agentCase: CaseRow | null;
    readonly agentInput: string;
    readonly agentSkillId: string;
    readonly agentScreenshots: CaseAgentAttachment[];
    readonly agentState: CaseAgentState | null;
    readonly agentSending: boolean;
    readonly activeCaseAgentRequestRef: React.RefObject<AbortController | null>;
    readonly agentDocumentIds: number[];
    readonly agentDocuments: CaseAgentDocument[];
    readonly setAgentInput: React.Dispatch<React.SetStateAction<string>>;
    readonly setAgentScreenshots: React.Dispatch<React.SetStateAction<CaseAgentAttachment[]>>;
    readonly setAgentMaterialPickerOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setAgentSending: React.Dispatch<React.SetStateAction<boolean>>;
    readonly stateWithAgentScreenshotPreviews: (nextState: CaseAgentState) => {
        messages: {
            attachments: {
                preview_url: string | undefined;
                id: number;
                name: string;
                mime_type?: string | undefined;
            }[] | undefined;
            id?: string | undefined;
            role: "assistant" | "user";
            content: string;
            operator?: string | undefined;
            created_at?: string | undefined;
        }[];
        thread_id: string;
        pending_actions: CaseAgentAction[];
        last_response: string;
        updated_at?: string | undefined;
        active_skill?: string | undefined;
    };
    readonly viewingCounselCase: CaseRow | null;
    readonly refreshCounselDetailAttachments: (caseId: number) => Promise<any>;
    readonly selectCounselDocCategory: (category: string) => void;
    readonly agentDecisionLoading: string;
    readonly setAgentDecisionLoading: React.Dispatch<React.SetStateAction<string>>;
}
export function createCaseAssistantActions(context: CaseAssistantDependencies) {
    const loadCaseAgent = async (row: CaseRow, resetMaterials = false) => {
        const { setAgentLoading, setAgentStatus, setAgentState, setAgentDocuments, setAgentDocumentIds, setAgentSkillId } = context;
        setAgentLoading(true);
        try {
            const [statusRes, stateRes, contextRes] = await Promise.all([
                api.get(`/case-spaces/${row.id}/agent/status`),
                api.get(`/case-spaces/${row.id}/agent/state`),
                api.get(`/case-spaces/${row.id}/context`),
            ]);
            setAgentStatus(statusRes.data);
            setAgentState(stateRes.data);
            const documents = (contextRes.data?.documents || []) as CaseAgentDocument[];
            const availableIds = documents.map((item) => Number(item.id)).filter((id) => id > 0);
            setAgentDocuments(documents);
            setAgentDocumentIds((current) => resetMaterials ? availableIds.slice(0, AGENT_DOCUMENT_LIMIT) : current.filter((id) => availableIds.includes(id)).slice(0, AGENT_DOCUMENT_LIMIT));
            const activeSkill = String(stateRes.data?.active_skill || DEFAULT_AGENT_SKILL);
            const activeAvailable = (statusRes.data?.skills || []).some((item: AgentSkill) => item.id === activeSkill && item.available);
            setAgentSkillId(activeAvailable ? activeSkill : DEFAULT_AGENT_SKILL);
        }
        catch (error: any) {
            const status = error?.response?.status;
            setAgentState(null);
            if (status === 503) {
                try {
                    const { data } = await api.get(`/case-spaces/${row.id}/agent/status`);
                    setAgentStatus(data);
                }
                catch {
                    setAgentStatus(null);
                }
            }
            else {
                setAgentStatus(null);
            }
            message.error(error?.response?.data?.detail || "案件智能体加载失败");
        }
        finally {
            setAgentLoading(false);
        }
    };
    const sendCaseAgentMessage = async (preset?: string) => {
        const { agentCase, agentInput, agentSkillId, agentScreenshots, agentState, setAgentSkillId, agentSending, activeCaseAgentRequestRef, agentDocumentIds, agentDocuments, setAgentState, setAgentInput, setAgentScreenshots, setAgentDocumentIds, setAgentMaterialPickerOpen, setAgentSending, stateWithAgentScreenshotPreviews, viewingCounselCase, refreshCounselDetailAttachments, selectCounselDocCategory } = context;
        if (!agentCase)
            return;
        const content = String(preset ?? agentInput).trim() || (agentSkillId === "screenshot-evidence" && agentScreenshots.length ? "请分析上传的截图证据" : "");
        if (!content)
            return message.warning("请输入要询问的案件问题");
        const effectiveSkillId = isAiWordGenerationRequest(content) ? "legal-document-drafting" : agentSkillId;
        const previousAssistantDocument = isExistingAnswerWordConversionRequest(content)
            ? [...(agentState?.messages || [])].reverse().find((item) => item.role === "assistant" && isUsableAiDocumentContent(item.content))?.content || ""
            : "";
        if (effectiveSkillId !== agentSkillId)
            setAgentSkillId(effectiveSkillId);
        if (agentSending)
            activeCaseAgentRequestRef.current?.abort();
        const outgoingScreenshots = [...agentScreenshots];
        const outgoingDocumentIds = [...agentDocumentIds];
        const outgoingDocuments = agentDocuments.filter((item) => outgoingDocumentIds.includes(item.id));
        const optimisticAttachments = Array.from(new Map([
            ...outgoingScreenshots,
            ...outgoingDocuments.map((item) => ({ id: item.id, name: item.original_name })),
        ].map((item) => [item.id, item])).values());
        const optimisticId = `pending-${Date.now()}`;
        setAgentState((current) => current ? {
            ...current,
            messages: [...(current.messages || []), { id: optimisticId, role: "user", content, attachments: optimisticAttachments }],
        } : current);
        setAgentInput("");
        setAgentScreenshots([]);
        setAgentDocumentIds([]);
        setAgentMaterialPickerOpen(false);
        const controller = new AbortController();
        activeCaseAgentRequestRef.current = controller;
        setAgentSending(true);
        try {
            const response = await fetch(`/api/v1/case-spaces/${agentCase.id}/agent/messages`, {
                method: "POST",
                signal: controller.signal,
                headers: {
                    "Content-Type": "application/json",
                    ...(localStorage.getItem("access_token") ? { Authorization: `Bearer ${localStorage.getItem("access_token")}` } : {}),
                },
                body: JSON.stringify({
                    message: encodeAgentSkillMessage(effectiveSkillId, content),
                    skill_id: effectiveSkillId,
                    attachment_ids: outgoingScreenshots.map((item) => item.id),
                    document_ids: outgoingDocumentIds,
                    stream: true,
                }),
            });
            if (!response.ok || !response.body) {
                const payload = await response.json().catch(() => ({}));
                throw new Error(payload.detail || "案件智能体响应失败");
            }
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            const streamId = `stream-${Date.now()}`;
            let buffer = "";
            let streamedContent = "";
            while (true) {
                const { done, value } = await reader.read();
                buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
                const lines = buffer.split("\n");
                buffer = lines.pop() || "";
                for (const line of lines) {
                    if (!line.trim())
                        continue;
                    const event = JSON.parse(line);
                    if (event.type === "delta") {
                        streamedContent += String(event.content || "");
                        setAgentState((current) => current ? {
                            ...current,
                            messages: [
                                ...current.messages.filter((item) => item.id !== streamId),
                                { id: streamId, role: "assistant", content: streamedContent },
                            ],
                        } : current);
                    }
                    else if (event.type === "state") {
                        setAgentState(stateWithAgentScreenshotPreviews(event.state));
                    }
                    else if (event.type === "error") {
                        throw new Error(event.detail || "案件智能体响应失败");
                    }
                }
                if (done)
                    break;
            }
            if (streamedContent.trim() && isAiWordGenerationRequest(content)) {
                const name = aiWordDocumentName(content, streamedContent);
                await api.post(`/cases/${agentCase.id}/ai-space/files`, { name, content: streamedContent });
                message.success(`Word 文档已生成到 AI 空间：${name}`);
                if (viewingCounselCase?.id === agentCase.id) {
                    await refreshCounselDetailAttachments(agentCase.id);
                    selectCounselDocCategory("AI空间");
                }
            }
        }
        catch (error: any) {
            if (!controller.signal.aborted) {
                if (previousAssistantDocument) {
                    const name = aiWordDocumentName(content, previousAssistantDocument);
                    await api.post(`/cases/${agentCase.id}/ai-space/files`, { name, content: previousAssistantDocument });
                    setAgentState((current) => current ? {
                        ...current,
                        messages: [
                            ...current.messages.filter((item) => !String(item.id || "").startsWith("stream-")),
                            { id: `document-${Date.now()}`, role: "assistant", content: `Word 文档已生成到 AI 空间：${name}` },
                        ],
                    } : current);
                    if (viewingCounselCase?.id === agentCase.id) {
                        await refreshCounselDetailAttachments(agentCase.id);
                        selectCounselDocCategory("AI空间");
                    }
                    message.success(`Word 文档已生成到 AI 空间：${name}`);
                    return;
                }
                const rawDetail = error?.response?.data?.detail || error?.message || "案件智能体响应失败";
                const visibleDetail = /model_(?:http|request|empty)|upstream/i.test(String(rawDetail))
                    ? "模型本轮生成失败，请点击重新发送；案件材料和已发送问题不会丢失。"
                    : String(rawDetail);
                setAgentState((current) => current ? {
                    ...current,
                    messages: [
                        ...current.messages.filter((item) => !String(item.id || "").startsWith("stream-")),
                        { id: `error-${Date.now()}`, role: "assistant", content: visibleDetail },
                    ],
                } : current);
                message.error(visibleDetail);
            }
        }
        finally {
            if (activeCaseAgentRequestRef.current === controller) {
                activeCaseAgentRequestRef.current = null;
                setAgentSending(false);
            }
        }
    };
    const decideCaseAgentAction = async (action: CaseAgentAction, decision: "approved" | "rejected") => {
        const { agentCase, agentDecisionLoading, setAgentDecisionLoading, setAgentState } = context;
        if (!agentCase || agentDecisionLoading)
            return;
        setAgentDecisionLoading(action.id);
        try {
            const { data } = await api.post(`/case-spaces/${agentCase.id}/agent/actions/${action.id}/decision`, {
                decision,
                comment: decision === "approved" ? "在案件智能体面板批准" : "在案件智能体面板驳回",
            });
            setAgentState(data);
            message.success(decision === "approved" ? "已记录批准决定" : "已记录驳回决定");
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "审批操作失败");
        }
        finally {
            setAgentDecisionLoading("");
        }
    };
    return { loadCaseAgent, sendCaseAgentMessage, decideCaseAgentAction };
}
