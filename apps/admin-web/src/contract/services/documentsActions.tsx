import { message } from "antd";
import { api } from "../../api";
import { openAttachmentOnlinePreview } from "../../attachmentOnlinePreview.mjs";
import { confirmOperation } from "../../components/common/confirmOperation";
import { buildContractAttachmentDeletePlan } from "../../contractAttachmentBatch.mjs";
import type { ContractMutationGate } from "../../contractMutationGate.mjs";
import { canMutateContractAttachments, contractAttachmentActionPolicy, extractContractErrorMessage, normalizeContractActionResponse, normalizeContractAttachment, validateContractAttachment } from "../../contractWorkflowPolicy.mjs";
import type { Attachment, Contract, LegacyHistoricalAttachment } from "../types";
/** contract documents operations; dependencies are read when each operation runs. */
export interface ContractDocumentsDependencies {
    readonly setViewingAttachmentsLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setViewingAttachmentsError: React.Dispatch<React.SetStateAction<string | null>>;
    readonly setViewingAttachments: React.Dispatch<React.SetStateAction<Attachment[]>>;
    readonly setSelectedAttachmentKeys: React.Dispatch<React.SetStateAction<React.Key[]>>;
    readonly setLegacyHistoricalAttachmentsLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setLegacyHistoricalAttachmentsError: React.Dispatch<React.SetStateAction<string | null>>;
    readonly setLegacyHistoricalAttachments: React.Dispatch<React.SetStateAction<LegacyHistoricalAttachment[]>>;
    readonly wizardDraft: Contract | null;
    readonly contractFile: File | null;
    readonly setContractFile: React.Dispatch<React.SetStateAction<File | null>>;
    readonly loadWizardContext: (contractId: number) => Promise<Contract>;
    readonly viewing: Contract | null;
    readonly openViewing: (contract: Contract, options?: {
        detailTab?: string | undefined;
    }) => Promise<void>;
    readonly selectedAttachmentKeys: React.Key[];
    readonly contractMutationGates: React.RefObject<{
        submit: ContractMutationGate;
        payment: ContractMutationGate;
        invoice: ContractMutationGate;
        attachment: ContractMutationGate;
    }>;
    readonly setAttachmentBatchSaving: React.Dispatch<React.SetStateAction<boolean>>;
}
export function createContractDocumentsActions(context: ContractDocumentsDependencies) {
    const reloadViewingAttachments = async (contract: Contract) => {
        const { setViewingAttachmentsLoading, setViewingAttachmentsError, setViewingAttachments, setSelectedAttachmentKeys } = context;
        setViewingAttachmentsLoading(true);
        setViewingAttachmentsError(null);
        try {
            const response = await api.get("/attachments", { params: { record_id: contract.id } });
            setViewingAttachments((response.data.items || []).map((item: Attachment) => ({ ...item, ...normalizeContractAttachment(item) })));
            setSelectedAttachmentKeys([]);
        }
        catch (error: any) {
            setViewingAttachmentsError(extractContractErrorMessage(error, "合同附件加载失败"));
        }
        finally {
            setViewingAttachmentsLoading(false);
        }
    };
    const loadLegacyHistoricalAttachments = async (contract: Contract) => {
        const { setLegacyHistoricalAttachmentsLoading, setLegacyHistoricalAttachmentsError, setLegacyHistoricalAttachments } = context;
        setLegacyHistoricalAttachmentsLoading(true);
        setLegacyHistoricalAttachmentsError(null);
        try {
            const response = await api.get("/legacy-history/attachments", {
                params: { legacy_entity_type: "FCM_Contract_File", legacy_parent_no: contract.serial_no, include_inactive: true, page_size: 200 },
            });
            setLegacyHistoricalAttachments(response.data.items || []);
        }
        catch (error: any) {
            setLegacyHistoricalAttachments([]);
            setLegacyHistoricalAttachmentsError(extractContractErrorMessage(error, "历史合同附件元数据加载失败"));
        }
        finally {
            setLegacyHistoricalAttachmentsLoading(false);
        }
    };
    const downloadAttachment = async (item: Attachment) => {
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
            message.error(extractContractErrorMessage(error, "附件下载失败"));
        }
    };
    const previewAttachment = async (item: Attachment) => {
        try {
            await openAttachmentOnlinePreview(api, item);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || error?.message || "合同附件预览失败");
        }
    };
    const uploadDraftContractAttachment = async () => {
        const { wizardDraft, contractFile, setContractFile, loadWizardContext } = context;
        if (!wizardDraft)
            return;
        if (!contractFile) {
            message.warning("请先选择合同附件");
            return;
        }
        const attachmentError = validateContractAttachment(contractFile);
        if (attachmentError) {
            message.warning(attachmentError);
            return;
        }
        const attachment = new FormData();
        attachment.append("file", contractFile);
        attachment.append("record_id", String(wizardDraft.id));
        attachment.append("category", "合同附件");
        attachment.append("remark", "合同草稿补传附件");
        try {
            const response = await api.post("/attachments", attachment);
            const feedback = normalizeContractActionResponse(response, "合同附件上传失败");
            if (!feedback.ok)
                throw new Error(feedback.message);
            setContractFile(null);
            await loadWizardContext(wizardDraft.id);
            message.success("合同附件已上传");
        }
        catch (error: any) {
            message.error(extractContractErrorMessage(error, "合同附件上传失败"));
        }
    };
    const uploadViewingAttachment = async () => {
        const { viewing, contractFile, setContractFile, openViewing } = context;
        if (!viewing)
            return;
        if (!contractFile) {
            message.warning("请先选择合同附件");
            return;
        }
        const attachmentPolicy = contractAttachmentActionPolicy(viewing.status);
        if (!attachmentPolicy.canUpload || !canMutateContractAttachments(viewing.status)) {
            message.warning("当前合同状态不允许修改附件");
            return;
        }
        const attachmentError = validateContractAttachment(contractFile);
        if (attachmentError && attachmentError !== "请选择合同附件") {
            message.error(attachmentError);
            return;
        }
        if (contractFile.size > 20 * 1024 * 1024) {
            message.error("单个文件不能超过 20MB");
            return;
        }
        const attachment = new FormData();
        attachment.append("file", contractFile);
        attachment.append("record_id", String(viewing.id));
        attachment.append("category", "合同附件");
        attachment.append("remark", "合同详情补传附件");
        try {
            const response = await api.post("/attachments", attachment);
            const feedback = normalizeContractActionResponse(response, "合同附件上传失败");
            if (!feedback.ok)
                throw new Error(feedback.message);
            setContractFile(null);
            await openViewing(viewing);
            message.success("合同附件已上传");
        }
        catch (error: any) {
            message.error(extractContractErrorMessage(error, "合同附件上传失败"));
        }
    };
    const deleteViewingAttachment = async (item: Attachment) => {
        const { openViewing, viewing } = context;
        try {
            const response = await api.delete(`/attachments/${item.id}`);
            const feedback = normalizeContractActionResponse(response, "合同附件删除失败");
            if (!feedback.ok)
                throw new Error(feedback.message);
            await openViewing(viewing!);
            message.success("合同附件已删除");
        }
        catch (error: any) {
            message.error(extractContractErrorMessage(error, "合同附件删除失败"));
        }
    };
    const batchDeleteViewingAttachments = async () => {
        const { viewing, selectedAttachmentKeys, contractMutationGates, setAttachmentBatchSaving, setSelectedAttachmentKeys } = context;
        const target = viewing;
        const deletePlan = buildContractAttachmentDeletePlan(selectedAttachmentKeys);
        if (!target)
            return;
        if (!deletePlan.length) {
            message.warning("请先选择要删除的合同附件");
            return;
        }
        if (!contractAttachmentActionPolicy(target.status).canDelete) {
            message.warning("当前合同状态不允许删除附件");
            return;
        }
        confirmOperation({
            title: "确认批量删除合同附件？",
            content: `将删除已选择的 ${deletePlan.length} 个合同附件。若后端返回失败，失败项会保留选中并显示原始失败消息。`,
            okText: "确认删除",
            okButtonProps: { danger: true },
            cancelText: "取消",
            onConfirm: async () => {
                if (!contractMutationGates.current.attachment.tryEnter())
                    return;
                setAttachmentBatchSaving(true);
                try {
                    const response = await api.post(`/contracts/${target.id}/attachments/delete`, { fileIds: deletePlan });
                    const feedback = normalizeContractActionResponse(response, "合同附件删除失败");
                    const rawFailed = Array.isArray(response.data?.failed) ? response.data.failed : [];
                    const summary: {
                        deleted: number;
                        failed: {
                            id: number;
                            message: string;
                        }[];
                    } = {
                        deleted: Number(response.data?.deleted || 0),
                        failed: rawFailed.map((item: any, index: number) => ({
                            id: Number(item.id ?? item.file_id ?? item.fileId ?? deletePlan[index]) || 0,
                            message: String(item.message || item.detail || feedback.message),
                        })),
                    };
                    if (!feedback.ok && !summary.failed.length) {
                        summary.failed = deletePlan.map((id) => ({ id: Number(id), message: feedback.message }));
                    }
                    if (summary.failed.length) {
                        setSelectedAttachmentKeys(summary.failed.map((item) => item.id).filter(Boolean));
                        if (summary.deleted)
                            await reloadViewingAttachments(target);
                        message.error(`合同附件批量删除未完成：${summary.failed.map((item) => item.message).join("；")}`);
                        return;
                    }
                    if (summary.deleted)
                        await reloadViewingAttachments(target);
                    setSelectedAttachmentKeys([]);
                    message.success(`已删除 ${summary.deleted || deletePlan.length} 个合同附件`);
                }
                finally {
                    contractMutationGates.current.attachment.leave();
                    setAttachmentBatchSaving(false);
                }
            },
        });
    };
    return { reloadViewingAttachments, loadLegacyHistoricalAttachments, downloadAttachment, previewAttachment, uploadDraftContractAttachment, uploadViewingAttachment, deleteViewingAttachment, batchDeleteViewingAttachments };
}
