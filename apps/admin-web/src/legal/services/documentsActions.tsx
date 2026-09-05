import { message } from "antd";
import type { FormInstance } from "antd/es/form/hooks/useForm";
import dayjs from "dayjs";
import { api } from "../../api";
import { openAttachmentOnlinePreview } from "../../attachmentOnlinePreview.mjs";
import { getCaseAttachmentUploadValidationError, getCaseFileRenameValidationError, hasCaseFileTypeOption } from "../../caseFileFrontendParity.mjs";
import { DEFAULT_CASE_ATTACHMENT_CATEGORY } from "../constants";
import type { AttachmentPreview, AttachmentRow, CaseAgentAttachment, CaseAiDraftEditor, CaseDocumentFolderEditor, CaseFileTypeOption, CaseRow, CaseTaskAttachment, CaseWordEditor, CaseWordEditorBlock, ContractRow } from "../types";
/** legal documents operations; dependencies are read when each operation runs. */
export interface CaseDocumentsDependencies {
    readonly applyCounselDocumentFolderPayload: (payload: any) => CaseFileTypeOption[];
    readonly setCounselDetailAttachments: React.Dispatch<React.SetStateAction<AttachmentRow[]>>;
    readonly agentCase: CaseRow | null;
    readonly agentScreenshots: CaseAgentAttachment[];
    readonly setAgentScreenshotUploading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly agentScreenshotPreviewUrlsRef: React.RefObject<Map<number, string>>;
    readonly setAgentScreenshots: React.Dispatch<React.SetStateAction<CaseAgentAttachment[]>>;
    readonly agentScreenshotInputRef: React.RefObject<HTMLInputElement | null>;
    readonly viewingCounselCase: CaseRow | null;
    readonly generatingCaseDocumentType: string;
    readonly setCaseDocumentGenerationError: React.Dispatch<React.SetStateAction<string>>;
    readonly setGeneratingCaseDocumentType: React.Dispatch<React.SetStateAction<string>>;
    readonly setExpandedCounselDocGroups: React.Dispatch<React.SetStateAction<Record<string, boolean>>>;
    readonly setActiveCounselDocCategory: React.Dispatch<React.SetStateAction<string>>;
    readonly setCaseSealAssets: React.Dispatch<React.SetStateAction<{
        id: number;
        status: string;
        seal_type: string;
        name: string;
    }[]>>;
    readonly caseFileSealForm: FormInstance<any>;
    readonly setSealingCounselAttachment: React.Dispatch<React.SetStateAction<AttachmentRow | null>>;
    readonly sealingCounselAttachment: AttachmentRow | null;
    readonly openCounselDetail: (row: CaseRow, preferredTab?: string | undefined) => Promise<void>;
    readonly caseCustomers: CaseRow[];
    readonly contracts: ContractRow[];
    readonly activeCounselDocCategory: string;
    readonly counselUploadCategory: string;
    readonly counselDetailUploadRef: React.RefObject<HTMLInputElement | null>;
    readonly attachmentPreview: AttachmentPreview | null;
    readonly setAttachmentPreviewLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setAttachmentPreview: React.Dispatch<React.SetStateAction<AttachmentPreview | null>>;
    readonly movingCounselAttachmentIds: number[] | null;
    readonly caseAttachmentMoveForm: FormInstance<any>;
    readonly setMovingCounselAttachmentIds: React.Dispatch<React.SetStateAction<number[] | null>>;
    readonly setSelectedCounselAttachmentKeys: React.Dispatch<React.SetStateAction<React.Key[]>>;
    readonly renamingCounselAttachment: AttachmentRow | null;
    readonly attachmentRenameForm: FormInstance<any>;
    readonly setRenamingCounselAttachment: React.Dispatch<React.SetStateAction<AttachmentRow | null>>;
    readonly aiDraftForm: FormInstance<any>;
    readonly setAiDraftEditor: React.Dispatch<React.SetStateAction<CaseAiDraftEditor | null>>;
    readonly wordEditorLockTokenRef: React.RefObject<string>;
    readonly setWordEditor: React.Dispatch<React.SetStateAction<CaseWordEditor | null>>;
    readonly setWordEditorLockLost: React.Dispatch<React.SetStateAction<boolean>>;
    readonly wordEditorOpening: boolean;
    readonly wordEditor: CaseWordEditor | null;
    readonly setWordEditorOpening: React.Dispatch<React.SetStateAction<boolean>>;
    readonly wordEditorChanged: (editor: CaseWordEditor) => boolean;
    readonly wordEditorSavingRef: React.RefObject<boolean>;
    readonly setWordEditorSaving: React.Dispatch<React.SetStateAction<boolean>>;
    readonly aiDraftEditor: CaseAiDraftEditor | null;
    readonly selectCounselDocCategory: (category: string) => void;
    readonly setPromotingAiDraft: React.Dispatch<React.SetStateAction<AttachmentRow | null>>;
    readonly setAiDraftPromoteOptionsLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setAiDraftPromoteOptions: React.Dispatch<React.SetStateAction<CaseFileTypeOption[]>>;
    readonly aiDraftPromoteForm: FormInstance<any>;
    readonly counselUploadCategoryOptions: {
        value: string;
        label: string;
    }[];
    readonly promotingAiDraft: AttachmentRow | null;
    readonly caseDocumentFolderEditor: CaseDocumentFolderEditor | null;
    readonly caseDocumentFolderForm: FormInstance<any>;
    readonly setViewingCounselCase: React.Dispatch<React.SetStateAction<CaseRow | null>>;
    readonly setCounselUploadCategory: React.Dispatch<React.SetStateAction<string>>;
    readonly setCaseDocumentFolderEditor: React.Dispatch<React.SetStateAction<CaseDocumentFolderEditor | null>>;
    readonly selectedCases: CaseRow[];
    readonly selectedCase: CaseRow | undefined;
    readonly initialView: string;
    readonly caseUploadCategory: string;
    readonly fileTypeOptionsForCase: (caseType: unknown) => CaseFileTypeOption[];
    readonly caseUploadRef: React.RefObject<HTMLInputElement | null>;
    readonly load: () => Promise<void>;
}
export function createCaseDocumentsActions(context: CaseDocumentsDependencies) {
    const refreshCounselDocumentFolderTree = async (caseId: number): Promise<CaseFileTypeOption[]> => {
        const { applyCounselDocumentFolderPayload } = context;
        const { data } = await api.get(`/cases/${caseId}/document-folders`);
        return applyCounselDocumentFolderPayload(data);
    };
    const refreshCounselDetailAttachments = async (caseId: number) => {
        const { setCounselDetailAttachments } = context;
        const { data } = await api.get("/attachments", { params: { record_id: caseId, page_size: 200 } });
        const items = Array.isArray(data?.items) ? data.items : [];
        setCounselDetailAttachments(items);
        try {
            await refreshCounselDocumentFolderTree(caseId);
        }
        catch {
            message.warning("文件列表已更新，目录刷新失败，请刷新页面重试");
        }
        return items;
    };
    const uploadCaseAgentScreenshot = async (file?: File) => {
        const { agentCase, agentScreenshots, setAgentScreenshotUploading, agentScreenshotPreviewUrlsRef, setAgentScreenshots, agentScreenshotInputRef } = context;
        if (!file || !agentCase)
            return;
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
        setAgentScreenshotUploading(true);
        try {
            const { data } = await api.post("/attachments", form);
            const attachment = data.attachment || data;
            const id = Number(attachment.id);
            const previewUrl = URL.createObjectURL(file);
            agentScreenshotPreviewUrlsRef.current.set(id, previewUrl);
            setAgentScreenshots((current) => [...current, { id, name: String(attachment.original_name || file.name), mime_type: file.type, preview_url: previewUrl }]);
            message.success("截图已加入当前案件空间");
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "截图上传失败");
        }
        finally {
            setAgentScreenshotUploading(false);
            if (agentScreenshotInputRef.current)
                agentScreenshotInputRef.current.value = "";
        }
    };
    const downloadCaseTaskAttachment = async (item: CaseTaskAttachment) => {
        try {
            const response = await api.get(`/attachments/${item.id}/download`, { responseType: "blob" });
            const url = URL.createObjectURL(response.data);
            const anchor = document.createElement("a");
            anchor.href = url;
            anchor.download = item.original_name;
            anchor.click();
            URL.revokeObjectURL(url);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "附件下载失败");
        }
    };
    const generateCaseDocument = async (documentType: string) => {
        const { viewingCounselCase, generatingCaseDocumentType, setCaseDocumentGenerationError, setGeneratingCaseDocumentType, setCounselDetailAttachments, setExpandedCounselDocGroups, setActiveCounselDocCategory } = context;
        if (!viewingCounselCase || generatingCaseDocumentType)
            return;
        setCaseDocumentGenerationError("");
        setGeneratingCaseDocumentType(documentType);
        try {
            const { data } = await api.post(`/cases/${viewingCounselCase.id}/documents/${documentType}`);
            const targetCategory = String(data.category || "案件文档全部");
            setCounselDetailAttachments((current) => [data, ...current.filter((item) => item.id !== data.id)]);
            setExpandedCounselDocGroups((current) => ({ ...current, "案件文档全部": true }));
            setActiveCounselDocCategory(targetCategory);
            message.success(`${data.original_name || "案件文书"}已生成并归入案件附件`);
            try {
                await refreshCounselDetailAttachments(viewingCounselCase.id);
            }
            catch {
                message.warning("文书已生成，但附件列表刷新失败，请稍后刷新页面");
            }
        }
        catch (error: any) {
            const detail = error?.response?.data?.detail || "案件文书生成失败";
            setCaseDocumentGenerationError(detail);
            message.error(detail);
        }
        finally {
            setGeneratingCaseDocumentType("");
        }
    };
    const openCounselAttachmentSeal = async (item: AttachmentRow) => {
        const { viewingCounselCase, setCaseSealAssets, caseFileSealForm, setSealingCounselAttachment } = context;
        if (!viewingCounselCase)
            return;
        try {
            const { data } = await api.get("/seals/assets");
            const available = (data.items || []).filter((asset: {
                status: string;
            }) => asset.status === "可用");
            setCaseSealAssets(available);
            caseFileSealForm.setFieldsValue({
                title: `${viewingCounselCase.serial_no}-${item.original_name}-用印申请`,
                use_type: "案件用印",
                case_no: viewingCounselCase.serial_no,
                contract_no: viewingCounselCase.data.contract_no || "",
                customer: viewingCounselCase.customer,
                seal_asset_id: undefined,
                use_date: dayjs(),
                copies: 2,
                delivery_method: "现场用印",
                is_electronic_seal: false,
                is_offline_print: true,
                purpose: "案件文件用印",
                remark: "",
            });
            setSealingCounselAttachment(item);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "可用印章加载失败");
        }
    };
    const submitCounselAttachmentSeal = async () => {
        const { viewingCounselCase, sealingCounselAttachment, caseFileSealForm, setSealingCounselAttachment, openCounselDetail } = context;
        if (!viewingCounselCase || !sealingCounselAttachment)
            return;
        try {
            const values = await caseFileSealForm.validateFields();
            const response = await api.post("/seals/applications", {
                title: String(values.title || "").trim(),
                customer: viewingCounselCase.customer,
                case_no: viewingCounselCase.serial_no,
                contract_no: viewingCounselCase.data.contract_no || "",
                use_type: "案件用印",
                source_attachment_ids: [sealingCounselAttachment.id],
                seal_asset_id: values.seal_asset_id,
                copies: values.copies,
                print_quantity: values.copies,
                purpose: String(values.purpose || "").trim(),
                use_date: values.use_date.format("YYYY-MM-DD"),
                delivery_method: values.delivery_method,
                is_electronic_seal: Boolean(values.is_electronic_seal),
                is_offline_print: Boolean(values.is_offline_print),
                remark: String(values.remark || "").trim(),
                description: String(values.remark || "").trim(),
                document_names: sealingCounselAttachment.original_name,
            });
            await api.post(`/seals/applications/${response.data.id}/submit`, {
                comment: "从案件文档发起用印并提交审批",
            });
            message.success("用印申请已创建并提交审批");
            setSealingCounselAttachment(null);
            caseFileSealForm.resetFields();
            await openCounselDetail(viewingCounselCase);
        }
        catch (error: any) {
            if (!error?.errorFields)
                message.error(error?.response?.data?.detail || "提交用印失败");
        }
    };
    const uploadCounselDetailAttachment = async (file?: File) => {
        const { viewingCounselCase, caseCustomers, contracts, activeCounselDocCategory, counselUploadCategory, openCounselDetail, counselDetailUploadRef } = context;
        const uploadValidationError = getCaseAttachmentUploadValidationError(file);
        if (uploadValidationError)
            return message.warning(uploadValidationError);
        if (!file || !viewingCounselCase)
            return message.warning("请先打开案件详情再上传文件");
        const data = new FormData();
        data.append("file", file);
        const customerRecordId = Number(viewingCounselCase.data.customer_record_id || viewingCounselCase.data.customer_id)
            || caseCustomers.find((item) => item.title === viewingCounselCase.customer)?.id;
        const contractRecordId = Number(viewingCounselCase.data.contract_record_id || viewingCounselCase.data.contract_id)
            || contracts.find((item) => item.serial_no === viewingCounselCase.data.contract_no)?.id;
        const targetRecordId = activeCounselDocCategory === "客户文档"
            ? customerRecordId
            : activeCounselDocCategory === "合同文档"
                ? contractRecordId
                : viewingCounselCase.id;
        if (!targetRecordId)
            return message.warning(`当前案件没有可用的${activeCounselDocCategory}关联记录`);
        const uploadCategory = activeCounselDocCategory === "客户文档" || activeCounselDocCategory === "合同文档"
            ? activeCounselDocCategory
            : counselUploadCategory || DEFAULT_CASE_ATTACHMENT_CATEGORY;
        data.append("record_id", String(targetRecordId));
        data.append("category", uploadCategory);
        data.append("remark", `案件详情关联文档：${uploadCategory}`);
        if (activeCounselDocCategory === "客户文档" || activeCounselDocCategory === "合同文档") {
            data.append("source_case_id", String(viewingCounselCase.id));
        }
        try {
            await api.post("/attachments", data);
            message.success("案件文件已上传");
            await openCounselDetail(viewingCounselCase);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "案件文件上传失败");
        }
        finally {
            if (counselDetailUploadRef.current)
                counselDetailUploadRef.current.value = "";
        }
    };
    const downloadCounselDetailAttachment = async (item: AttachmentRow) => {
        try {
            const response = await api.get(`/attachments/${item.id}/download`, { responseType: "blob" });
            const url = URL.createObjectURL(response.data);
            const link = document.createElement("a");
            link.href = url;
            link.download = item.original_name;
            link.click();
            URL.revokeObjectURL(url);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "案件文件下载失败");
        }
    };
    const unlockCounselDetailAttachment = async (item: AttachmentRow) => {
        const { viewingCounselCase } = context;
        if (!viewingCounselCase)
            return message.warning("请先打开案件详情再解锁文件");
        try {
            await api.post(`/cases/${viewingCounselCase.id}/attachments/${item.id}/unlock`);
            message.success("案件文件已解锁");
            await refreshCounselDetailAttachments(viewingCounselCase.id);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "案件文件解锁失败");
        }
    };
    const previewCounselDetailAttachment = async (item: AttachmentRow) => {
        try {
            await openAttachmentOnlinePreview(api, item);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || error?.message || "案件文件预览失败");
        }
    };
    const loadAttachmentPdfPage = async (page: number) => {
        const { attachmentPreview, setAttachmentPreviewLoading, setAttachmentPreview } = context;
        if (!attachmentPreview?.attachmentId || attachmentPreview.kind !== "pdf")
            return;
        const targetPage = Math.min(Math.max(page, 1), attachmentPreview.pageCount || 1);
        if (targetPage === attachmentPreview.page)
            return;
        setAttachmentPreviewLoading(true);
        try {
            const response = await api.get(`/attachments/${attachmentPreview.attachmentId}/pdf-preview/pages/${targetPage}.png`, {
                params: { width: 1440 },
                responseType: "blob",
            });
            const nextUrl = URL.createObjectURL(response.data);
            if (attachmentPreview.url)
                URL.revokeObjectURL(attachmentPreview.url);
            setAttachmentPreview({ ...attachmentPreview, page: targetPage, url: nextUrl });
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "PDF 页面加载失败");
        }
        finally {
            setAttachmentPreviewLoading(false);
        }
    };
    const moveCounselAttachments = async () => {
        const { viewingCounselCase, movingCounselAttachmentIds, caseAttachmentMoveForm, setMovingCounselAttachmentIds, setSelectedCounselAttachmentKeys, openCounselDetail } = context;
        if (!viewingCounselCase || !movingCounselAttachmentIds?.length)
            return;
        const values = await caseAttachmentMoveForm.validateFields();
        try {
            const { data } = await api.post(`/cases/${viewingCounselCase.id}/attachments/move`, { attachment_ids: movingCounselAttachmentIds, category: values.category });
            message.success(`已将 ${data.moved} 个文件移至${data.category}`);
            setMovingCounselAttachmentIds(null);
            caseAttachmentMoveForm.resetFields();
            setSelectedCounselAttachmentKeys([]);
            await openCounselDetail(viewingCounselCase);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "更改文档目录失败");
        }
    };
    const renameCounselAttachment = async () => {
        const { renamingCounselAttachment, viewingCounselCase, attachmentRenameForm, setRenamingCounselAttachment, openCounselDetail } = context;
        if (!renamingCounselAttachment || !viewingCounselCase)
            return;
        const values = await attachmentRenameForm.validateFields();
        const renameValidationError = getCaseFileRenameValidationError(values.original_name, renamingCounselAttachment.original_name);
        if (renameValidationError)
            return message.warning(renameValidationError);
        try {
            await api.put(`/cases/attachments/${renamingCounselAttachment.id}/rename`, { original_name: values.original_name.trim() });
            message.success("案件文件已重命名");
            setRenamingCounselAttachment(null);
            attachmentRenameForm.resetFields();
            await openCounselDetail(viewingCounselCase);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "案件文件重命名失败");
        }
    };
    const openEditAiDraft = async (item: AttachmentRow) => {
        const { viewingCounselCase, aiDraftForm, setAiDraftEditor } = context;
        if (!viewingCounselCase)
            return;
        try {
            const { data } = await api.get(`/cases/${viewingCounselCase.id}/ai-space/files/${item.id}/content`);
            aiDraftForm.setFieldsValue({ name: data.name || item.original_name, content: data.content || "" });
            setAiDraftEditor({ mode: "edit", item });
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "AI 草稿读取失败");
        }
    };
    const releaseCaseWordEditorLock = async (editor: CaseWordEditor) => {
        try {
            await api.delete(`/cases/${editor.caseId}/attachments/${editor.item.id}/word-editor/lock`, {
                data: { lock_token: editor.lockToken },
            });
        }
        catch {
            // The lock has a server-side expiry. A failed best-effort release must not hide the editor close action.
        }
    };
    const finishClosingCaseWordEditor = async (editor: CaseWordEditor) => {
        const { wordEditorLockTokenRef, setWordEditor, setWordEditorLockLost } = context;
        await releaseCaseWordEditorLock(editor);
        if (wordEditorLockTokenRef.current === editor.lockToken)
            wordEditorLockTokenRef.current = "";
        setWordEditor((current) => current?.lockToken === editor.lockToken ? null : current);
        setWordEditorLockLost(false);
    };
    const openCaseWordEditor = async (item: AttachmentRow) => {
        const { viewingCounselCase, wordEditorOpening, wordEditor, setWordEditorOpening, wordEditorLockTokenRef, setWordEditor, setWordEditorLockLost } = context;
        if (!viewingCounselCase)
            return;
        if (wordEditorOpening || wordEditor)
            return;
        if (/\.doc$/i.test(item.original_name)) {
            message.warning("旧版 .doc 文件暂不支持在线编辑，请先转换为 .docx 后再编辑");
            return;
        }
        if (!/\.docx$/i.test(item.original_name)) {
            message.warning("仅 .docx Word 文件支持在线编辑");
            return;
        }
        const caseId = viewingCounselCase.id;
        setWordEditorOpening(true);
        try {
            const { data } = await api.get(`/cases/${caseId}/attachments/${item.id}/word-editor/content`);
            const blocks = Array.isArray(data.blocks)
                ? data.blocks.map((block: any, index: number) => ({ id: String(block.id || index), text: String(block.text || ""), editable: block.editable !== false, readOnlyReason: block.read_only_reason }))
                : [{ id: "content", text: String(data.content || ""), editable: true }];
            if (!data.lock_token)
                throw new Error("未取得文件编辑锁");
            wordEditorLockTokenRef.current = data.lock_token;
            setWordEditor({
                caseId,
                item,
                lockToken: data.lock_token,
                blocks,
                savedBlocks: blocks.map((block: CaseWordEditorBlock) => ({ ...block })),
                version: String(data.version || ""),
                expiresAt: data.lock_expires_at,
            });
            setWordEditorLockLost(false);
        }
        catch (error: any) {
            const detail = error?.response?.data?.detail;
            const lockDetail = detail && typeof detail === "object" ? detail : {};
            const holder = lockDetail.lock_holder || error?.response?.data?.lock_holder;
            const expiresAt = lockDetail.lock_expires_at || error?.response?.data?.lock_expires_at;
            const detailMessage = typeof detail === "string" ? detail : lockDetail.message;
            message.error(holder ? `文件正由 ${holder} 编辑，锁定至 ${expiresAt || "稍后"}` : detailMessage || error?.message || "打开 Word 在线编辑失败");
        }
        finally {
            setWordEditorOpening(false);
        }
    };
    const saveCaseWordEditor = async () => {
        const { wordEditor, wordEditorChanged, wordEditorSavingRef, setWordEditorSaving, wordEditorLockTokenRef, setWordEditor, setWordEditorLockLost } = context;
        if (!wordEditor)
            return;
        if (!wordEditorChanged(wordEditor)) {
            message.info("文档内容没有变化，无需保存");
            return;
        }
        const blocksSnapshot = wordEditor.blocks.map((block) => ({ ...block }));
        wordEditorSavingRef.current = true;
        setWordEditorSaving(true);
        try {
            const { data } = await api.put(`/cases/${wordEditor.caseId}/attachments/${wordEditor.item.id}/word-editor/content`, { lock_token: wordEditor.lockToken, version: wordEditor.version, blocks: blocksSnapshot });
            const nextLockToken = String(data.lock_token || wordEditor.lockToken);
            wordEditorLockTokenRef.current = nextLockToken;
            setWordEditor((current) => current && current.lockToken === wordEditor.lockToken ? {
                ...current,
                savedBlocks: blocksSnapshot,
                lockToken: nextLockToken,
                version: String(data.version ?? current.version),
                expiresAt: data.lock_expires_at || current.expiresAt,
            } : current);
            setWordEditorLockLost(false);
            message.success("Word 文档已保存回案件文件");
            try {
                await refreshCounselDetailAttachments(wordEditor.caseId);
            }
            catch {
                message.warning("Word 文档已保存，但附件列表刷新失败，请稍后刷新页面");
            }
        }
        catch (error: any) {
            const detail = error?.response?.data?.detail;
            const detailMessage = typeof detail === "string" ? detail : detail?.message;
            setWordEditorLockLost(error?.response?.status === 409);
            message.error(error?.response?.status === 409
                ? `${detailMessage || "Word 编辑锁已失效"}；当前内容仍保留，请复制后关闭并重新打开文件`
                : detailMessage || "Word 文档保存失败；当前编辑内容仍保留，可稍后重试");
        }
        finally {
            wordEditorSavingRef.current = false;
            setWordEditorSaving(false);
        }
    };
    const saveAiDraft = async () => {
        const { viewingCounselCase, aiDraftEditor, aiDraftForm, setAiDraftEditor, openCounselDetail, selectCounselDocCategory } = context;
        if (!viewingCounselCase || !aiDraftEditor)
            return;
        const values = await aiDraftForm.validateFields();
        try {
            if (aiDraftEditor.mode === "create") {
                await api.post(`/cases/${viewingCounselCase.id}/ai-space/files`, {
                    name: String(values.name || "").trim(),
                    content: values.content || "",
                });
                message.success("AI Word 文档已保存");
            }
            else if (aiDraftEditor.item) {
                if (String(values.name || "").trim() !== aiDraftEditor.item.original_name) {
                    await api.put(`/cases/attachments/${aiDraftEditor.item.id}/rename`, { original_name: String(values.name || "").trim() });
                }
                await api.put(`/cases/${viewingCounselCase.id}/ai-space/files/${aiDraftEditor.item.id}/content`, { content: values.content || "" });
                message.success("AI Word 文档已更新");
            }
            setAiDraftEditor(null);
            aiDraftForm.resetFields();
            await openCounselDetail(viewingCounselCase);
            selectCounselDocCategory("AI空间");
        }
        catch (error: any) {
            if (!error?.errorFields)
                message.error(error?.response?.data?.detail || "AI 草稿保存失败");
        }
    };
    const openPromoteAiDraft = async (item: AttachmentRow) => {
        const { viewingCounselCase, setPromotingAiDraft, setAiDraftPromoteOptionsLoading, applyCounselDocumentFolderPayload, setAiDraftPromoteOptions, aiDraftPromoteForm, counselUploadCategoryOptions } = context;
        if (!viewingCounselCase)
            return;
        setPromotingAiDraft(item);
        setAiDraftPromoteOptionsLoading(true);
        try {
            const { data } = await api.get(`/cases/${viewingCounselCase.id}/document-folders`);
            const options = applyCounselDocumentFolderPayload(data);
            const selectableOptions = (items: CaseFileTypeOption[]): CaseFileTypeOption[] => items.flatMap(option => option.options?.length ? selectableOptions(option.options) : option.disabled ? [] : [option]);
            setAiDraftPromoteOptions(options);
            aiDraftPromoteForm.setFieldsValue({ category: selectableOptions(options)[0]?.value });
        }
        catch (error: any) {
            setAiDraftPromoteOptions(counselUploadCategoryOptions);
            aiDraftPromoteForm.setFieldsValue({ category: counselUploadCategoryOptions[0]?.value });
            message.error(error?.response?.data?.detail || "读取正式案件文档目录失败");
        }
        finally {
            setAiDraftPromoteOptionsLoading(false);
        }
    };
    const promoteAiDraft = async () => {
        const { viewingCounselCase, promotingAiDraft, aiDraftPromoteForm, setPromotingAiDraft, openCounselDetail, selectCounselDocCategory } = context;
        if (!viewingCounselCase || !promotingAiDraft)
            return;
        const { category } = await aiDraftPromoteForm.validateFields();
        try {
            await api.post(`/cases/${viewingCounselCase.id}/ai-space/files/${promotingAiDraft.id}/promote`, { category });
            message.success(`已转入正式目录：${category}`);
            setPromotingAiDraft(null);
            aiDraftPromoteForm.resetFields();
            await openCounselDetail(viewingCounselCase);
            selectCounselDocCategory(String(category));
        }
        catch (error: any) {
            if (!error?.errorFields)
                message.error(error?.response?.data?.detail || "AI 草稿转入正式系统失败");
        }
    };
    const saveCaseDocumentFolder = async () => {
        const { viewingCounselCase, caseDocumentFolderEditor, caseDocumentFolderForm, setViewingCounselCase, setCounselDetailAttachments, setExpandedCounselDocGroups, setActiveCounselDocCategory, setCounselUploadCategory, setSelectedCounselAttachmentKeys, setCaseDocumentFolderEditor } = context;
        if (!viewingCounselCase || !caseDocumentFolderEditor)
            return;
        const { name } = await caseDocumentFolderForm.validateFields();
        const normalizedName = String(name || "").trim();
        try {
            const response = caseDocumentFolderEditor.mode === "create"
                ? await api.post(`/cases/${viewingCounselCase.id}/document-folders`, { name: normalizedName })
                : await api.put(`/cases/${viewingCounselCase.id}/document-folders`, { original_name: caseDocumentFolderEditor.originalName, name: normalizedName });
            const folders = Array.isArray(response.data?.folders) ? response.data.folders : [];
            const originalName = caseDocumentFolderEditor.originalName || "";
            setViewingCounselCase((current) => current ? ({ ...current, data: { ...current.data, custom_case_document_folders: folders } }) : current);
            await refreshCounselDocumentFolderTree(viewingCounselCase.id);
            if (caseDocumentFolderEditor.mode === "rename")
                setCounselDetailAttachments((current) => current.map((item) => item.category === originalName ? { ...item, category: normalizedName } : item));
            setExpandedCounselDocGroups((current) => ({ ...current, "案件文档全部": true }));
            setActiveCounselDocCategory(normalizedName);
            setCounselUploadCategory(normalizedName);
            setSelectedCounselAttachmentKeys([]);
            message.success(caseDocumentFolderEditor.mode === "create" ? "案件文档目录已新增" : "案件文档目录已重命名");
            setCaseDocumentFolderEditor(null);
            caseDocumentFolderForm.resetFields();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "案件文档目录保存失败");
        }
    };
    const generateSelectedCaseDocuments = async (documentType: string) => {
        const { selectedCases } = context;
        if (!selectedCases.length)
            return message.warning("请先选择需要生成文书的案件");
        try {
            await Promise.all(selectedCases.map((row) => api.post(`/cases/${row.id}/documents/${documentType}`)));
            message.success(`已为 ${selectedCases.length} 个案件生成文书并归入案件附件`);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "案件文书生成失败");
        }
    };
    const uploadCaseFile = async (file?: File) => {
        const { selectedCase, initialView, caseUploadCategory, fileTypeOptionsForCase, caseUploadRef } = context;
        const uploadValidationError = getCaseAttachmentUploadValidationError(file);
        if (uploadValidationError)
            return message.warning(uploadValidationError);
        if (!file || !selectedCase)
            return message.warning("请先选择案件再上传文件");
        const category = initialView === "case-files-receipt" ? "案件票据文件" : caseUploadCategory;
        if (initialView !== "case-files-receipt" && !hasCaseFileTypeOption(category, fileTypeOptionsForCase(selectedCase.data.case_type))) {
            return message.warning("当前案件类型未配置该材料类型，请先在系统参数中维护关联");
        }
        const data = new FormData();
        data.append("file", file);
        data.append("record_id", String(selectedCase.id));
        data.append("category", category);
        data.append("remark", initialView === "case-files-receipt" ? "案件票据批量上传" : `案件列表上传：${category}`);
        try {
            await api.post("/attachments", data);
            message.success("案件文件已上传");
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "上传失败");
        }
        finally {
            if (caseUploadRef.current)
                caseUploadRef.current.value = "";
        }
    };
    const uploadCaseInvoiceFile = async (file?: File) => {
        const { load, caseUploadRef } = context;
        if (!file)
            return;
        const data = new FormData();
        data.append("file", file);
        data.append("category", "案件发票文件");
        data.append("remark", "案件发票文件导入");
        try {
            await api.post("/attachments", data);
            message.success("发票文件已上传，请点击开始导入完成案件匹配");
            await load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "发票文件上传失败");
        }
        finally {
            if (caseUploadRef.current)
                caseUploadRef.current.value = "";
        }
    };
    return { refreshCounselDocumentFolderTree, refreshCounselDetailAttachments, uploadCaseAgentScreenshot, downloadCaseTaskAttachment, generateCaseDocument, openCounselAttachmentSeal, submitCounselAttachmentSeal, uploadCounselDetailAttachment, downloadCounselDetailAttachment, unlockCounselDetailAttachment, previewCounselDetailAttachment, loadAttachmentPdfPage, moveCounselAttachments, renameCounselAttachment, openEditAiDraft, releaseCaseWordEditorLock, finishClosingCaseWordEditor, openCaseWordEditor, saveCaseWordEditor, saveAiDraft, openPromoteAiDraft, promoteAiDraft, saveCaseDocumentFolder, generateSelectedCaseDocuments, uploadCaseFile, uploadCaseInvoiceFile };
}
