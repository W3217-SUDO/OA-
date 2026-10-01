import { message } from "antd";
import type { ClipboardEvent, ComponentProps, Key } from "react";
import { useEffect, useRef, useState } from "react";
import { DEFAULT_AGENT_SKILL } from "../../agentSkillRouting";
import { api } from "../../api";
import type { CaseAgentDrawer } from "../CaseAgentDrawer";
import { AGENT_DOCUMENT_LIMIT } from "../constants";
import { createCaseAssistantActions } from "../services/assistantActions";
import type { CaseAgentAttachment, CaseAgentDocument, CaseAgentState, CaseAgentStatus, CaseRow } from "../types";
import { useCaseAgentDrawer } from "./useCaseAgentDrawer";

type DrawerProps = Omit<ComponentProps<typeof CaseAgentDrawer>, "counselDetailCapabilities">;

interface CaseAgentWorkspaceDependencies {
  viewingCounselCase: CaseRow | null;
  refreshCounselDetailAttachments: (caseId: number) => Promise<unknown>;
  selectCounselDocCategory: (category: string) => void;
}

export function useCaseAgentWorkspace({
  viewingCounselCase,
  refreshCounselDetailAttachments,
  selectCounselDocCategory,
}: CaseAgentWorkspaceDependencies) {
  const [agentCase, setAgentCase] = useState<CaseRow | null>(null);
  const [agentOpen, setAgentOpen] = useState(false);
  const [agentStatus, setAgentStatus] = useState<CaseAgentStatus | null>(null);
  const [agentState, setAgentState] = useState<CaseAgentState | null>(null);
  const [agentLoading, setAgentLoading] = useState(false);
  const [agentSending, setAgentSending] = useState(false);
  const [agentDecisionLoading, setAgentDecisionLoading] = useState("");
  const [agentInput, setAgentInput] = useState("");
  const [agentSkillId, setAgentSkillId] = useState(DEFAULT_AGENT_SKILL);
  const [agentScreenshots, setAgentScreenshots] = useState<CaseAgentAttachment[]>([]);
  const [agentScreenshotUploading, setAgentScreenshotUploading] = useState(false);
  const [agentDocuments, setAgentDocuments] = useState<CaseAgentDocument[]>([]);
  const [agentDocumentIds, setAgentDocumentIds] = useState<number[]>([]);
  const [agentMaterialPickerOpen, setAgentMaterialPickerOpen] = useState(false);
  const [agentHistoryExpanded, setAgentHistoryExpanded] = useState(false);
  const { agentDrawerWidth, startAgentDrawerResize } = useCaseAgentDrawer();
  const agentMessagesEndRef = useRef<HTMLDivElement>(null);
  const agentScreenshotInputRef = useRef<HTMLInputElement>(null);
  const agentScreenshotPreviewUrlsRef = useRef(new Map<number, string>());
  const agentScreenshotUploadRequestsRef = useRef(new Set<AbortController>());
  const activeCaseAgentRequestRef = useRef<AbortController | null>(null);

  const stateWithAgentScreenshotPreviews = (nextState: CaseAgentState): CaseAgentState => ({
    ...nextState,
    messages: (nextState.messages || []).map((item) => ({
      ...item,
      attachments: item.attachments?.map((attachment) => ({
        ...attachment,
        preview_url: agentScreenshotPreviewUrlsRef.current.get(attachment.id),
      })),
    })),
  });
  const clearAgentScreenshotPreviews = () => {
    agentScreenshotPreviewUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
    agentScreenshotPreviewUrlsRef.current.clear();
  };
  const removeAgentScreenshot = (attachment: CaseAgentAttachment) => {
    const previewUrl = agentScreenshotPreviewUrlsRef.current.get(attachment.id);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    agentScreenshotPreviewUrlsRef.current.delete(attachment.id);
    setAgentScreenshots((current) => current.filter((entry) => entry.id !== attachment.id));
  };
  const uploadCaseAgentScreenshot = async (file?: File) => {
    if (!file || !agentCase) return;
    if (!["image/png", "image/jpeg", "image/webp"].includes(file.type))
      return message.error("截图仅支持 PNG、JPG、JPEG 或 WebP");
    if (file.size > 6 * 1024 * 1024)
      return message.error("单张截图不能超过 6MB");
    if (agentScreenshots.length >= 4)
      return message.warning("单次最多分析 4 张截图");
    const form = new FormData();
    form.append("file", file);
    form.append("record_id", String(agentCase.id));
    form.append("category", "智能体截图证据");
    form.append("remark", "由案件智能体上传，用于截图证据分析");
    const controller = new AbortController();
    agentScreenshotUploadRequestsRef.current.add(controller);
    setAgentScreenshotUploading(true);
    try {
      const { data } = await api.post("/attachments", form, { signal: controller.signal });
      if (controller.signal.aborted) return;
      const attachment = data.attachment || data;
      const id = Number(attachment.id);
      const previewUrl = URL.createObjectURL(file);
      agentScreenshotPreviewUrlsRef.current.set(id, previewUrl);
      setAgentScreenshots((current) => [...current, { id, name: String(attachment.original_name || file.name), mime_type: file.type, preview_url: previewUrl }]);
      message.success("截图已加入当前案件空间");
    } catch (error: unknown) {
      if (controller.signal.aborted) return;
      const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      message.error(detail || "截图上传失败");
    } finally {
      agentScreenshotUploadRequestsRef.current.delete(controller);
      if (!controller.signal.aborted) {
        setAgentScreenshotUploading(false);
        if (agentScreenshotInputRef.current) agentScreenshotInputRef.current.value = "";
      }
    }
  };

  const { loadCaseAgent, sendCaseAgentMessage, decideCaseAgentAction, restoreCaseAgentAction } = createCaseAssistantActions({
    get setAgentLoading() { return setAgentLoading; },
    get setAgentStatus() { return setAgentStatus; },
    get setAgentState() { return setAgentState; },
    get setAgentDocuments() { return setAgentDocuments; },
    get setAgentDocumentIds() { return setAgentDocumentIds; },
    get setAgentSkillId() { return setAgentSkillId; },
    get agentCase() { return agentCase; },
    get agentInput() { return agentInput; },
    get agentSkillId() { return agentSkillId; },
    get agentScreenshots() { return agentScreenshots; },
    get agentState() { return agentState; },
    get agentSending() { return agentSending; },
    get activeCaseAgentRequestRef() { return activeCaseAgentRequestRef; },
    get agentDocumentIds() { return agentDocumentIds; },
    get agentDocuments() { return agentDocuments; },
    get setAgentInput() { return setAgentInput; },
    get setAgentScreenshots() { return setAgentScreenshots; },
    get setAgentMaterialPickerOpen() { return setAgentMaterialPickerOpen; },
    get setAgentSending() { return setAgentSending; },
    get stateWithAgentScreenshotPreviews() { return stateWithAgentScreenshotPreviews; },
    get viewingCounselCase() { return viewingCounselCase; },
    get refreshCounselDetailAttachments() { return refreshCounselDetailAttachments; },
    get selectCounselDocCategory() { return selectCounselDocCategory; },
    get agentDecisionLoading() { return agentDecisionLoading; },
    get setAgentDecisionLoading() { return setAgentDecisionLoading; },
  });
  const openCaseAgent = (row: CaseRow) => {
    clearAgentScreenshotPreviews();
    setAgentCase(row);
    setAgentOpen(true);
    setAgentInput("");
    setAgentScreenshots([]);
    setAgentDocuments([]);
    setAgentDocumentIds([]);
    setAgentMaterialPickerOpen(false);
    setAgentHistoryExpanded(false);
    void loadCaseAgent(row, true);
  };
  const updateAgentDocumentSelection = (checkedKeys: Key[] | { checked: Key[]; halfChecked: Key[] }) => {
    const keys = Array.isArray(checkedKeys) ? checkedKeys : checkedKeys.checked;
    const selectedIds = keys.map(String).filter((key) => key.startsWith("document:")).map((key) => Number(key.slice("document:".length))).filter((id) => id > 0);
    if (selectedIds.length > AGENT_DOCUMENT_LIMIT) message.warning(`单轮最多选择 ${AGENT_DOCUMENT_LIMIT} 份材料`);
    setAgentDocumentIds(selectedIds.slice(0, AGENT_DOCUMENT_LIMIT));
  };
  const stopCaseAgentResponse = () => {
    activeCaseAgentRequestRef.current?.abort();
    activeCaseAgentRequestRef.current = null;
    setAgentSending(false);
    message.info("已停止本轮生成，可以继续补充要求");
  };
  const pasteCaseAgentScreenshot = (event: ClipboardEvent<HTMLTextAreaElement>) => {
    const itemFile = Array.from(event.clipboardData.items)
      .find((item) => item.kind === "file" && item.type.startsWith("image/"))
      ?.getAsFile();
    const file = itemFile || Array.from(event.clipboardData.files).find((item) => item.type.startsWith("image/"));
    if (!file) return;
    event.preventDefault();
    if (agentSkillId !== "screenshot-evidence") setAgentSkillId("screenshot-evidence");
    void uploadCaseAgentScreenshot(file);
  };

  useEffect(() => {
    if (!agentOpen) return;
    requestAnimationFrame(() => agentMessagesEndRef.current?.scrollIntoView({ behavior: "auto", block: "end" }));
  }, [agentOpen, agentState?.messages.length]);
  useEffect(() => () => {
    activeCaseAgentRequestRef.current?.abort();
    activeCaseAgentRequestRef.current = null;
    agentScreenshotUploadRequestsRef.current.forEach((controller) => controller.abort());
    agentScreenshotUploadRequestsRef.current.clear();
    clearAgentScreenshotPreviews();
  }, []);

  const drawerProps: DrawerProps = {
    agentOpen, setAgentOpen, agentCase, agentDrawerWidth, startAgentDrawerResize,
    agentStatus, agentLoading, agentSending, agentSkillId, setAgentSkillId,
    loadCaseAgent, agentState, agentDecisionLoading, decideCaseAgentAction,
    restoreCaseAgentAction, agentHistoryExpanded, setAgentHistoryExpanded,
    sendCaseAgentMessage, agentMaterialPickerOpen, setAgentMaterialPickerOpen,
    agentDocuments, agentDocumentIds, setAgentDocumentIds, updateAgentDocumentSelection,
    agentScreenshots, removeAgentScreenshot, agentScreenshotInputRef,
    uploadCaseAgentScreenshot, agentScreenshotUploading, agentInput, setAgentInput,
    pasteCaseAgentScreenshot, stopCaseAgentResponse, agentMessagesEndRef,
  };
  return { openCaseAgent, drawerProps };
}
