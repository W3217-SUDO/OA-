import { message } from "antd";
import type { FormInstance } from "antd/es/form/hooks/useForm";
import { api } from "../../api";
import { formatRequiredDate } from "../../formSafety";
import { assertIprMutationSuccess, getIprApiErrorMessage } from "../../iprCaseDetailParity.mjs";
import type { Attachment, CpcApplication, IprDetailPagePayload, IprDetailPageState, IprFileType, IprRecord } from "../types";
/** ipr documents operations; dependencies are read when each operation runs. */
export interface IprDocumentsDependencies {
    readonly filesPageState: IprDetailPageState;
    readonly setAttachments: React.Dispatch<React.SetStateAction<Attachment[]>>;
    readonly setFilesPageState: React.Dispatch<React.SetStateAction<IprDetailPageState>>;
    readonly clearIprSectionError: (section: "files" | "logs" | "reminders" | "tasks" | "assistedFees" | "annualFees") => void;
    readonly setIprSectionError: (section: "files" | "logs" | "reminders" | "tasks" | "assistedFees" | "annualFees", error: unknown) => void;
    readonly cpcHistoryRequest: React.RefObject<number>;
    readonly setCpcApplicationsLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setCpcApplicationsError: React.Dispatch<React.SetStateAction<string>>;
    readonly activeIprDetailId: React.RefObject<number | null>;
    readonly setCpcApplications: React.Dispatch<React.SetStateAction<CpcApplication[]>>;
    readonly setCpcGenerating: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setIprFileTypes: React.Dispatch<React.SetStateAction<IprFileType[]>>;
    readonly openDetail: (record: IprRecord) => Promise<void>;
    readonly detail: IprRecord | null;
    readonly iprFileForm: FormInstance<any>;
    readonly iprUploadFile: File | null;
    readonly setIprFileOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setIprUploadFile: React.Dispatch<React.SetStateAction<File | null>>;
    readonly iprBatchForm: FormInstance<any>;
    readonly iprBatchFile: File | null;
    readonly setIprBatchOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setIprBatchFile: React.Dispatch<React.SetStateAction<File | null>>;
    readonly selectedIprFileIds: number[];
    readonly setSelectedIprFileIds: React.Dispatch<React.SetStateAction<number[]>>;
}
export function createIprDocumentsActions(context: IprDocumentsDependencies) {
    const loadIprFiles = async (caseId: number, nextPage = context.filesPageState.page, nextPageSize = context.filesPageState.pageSize) => {
        const { filesPageState, setAttachments, setFilesPageState, clearIprSectionError, setIprSectionError } = context;
        try {
            const { data } = await api.get<IprDetailPagePayload<Attachment>>(`/ipr/cases/${caseId}/files`, {
                params: { page: nextPage, page_size: nextPageSize },
            });
            setAttachments(data.items || []);
            setFilesPageState({
                page: data.page ?? nextPage,
                pageSize: data.page_size ?? nextPageSize,
                total: data.total ?? data.items?.length ?? 0,
                pages: data.pages ?? 0,
            });
            clearIprSectionError("files");
        }
        catch (error) {
            setIprSectionError("files", error);
        }
    };
    const loadCpcApplications = async (caseId: number) => {
        const { cpcHistoryRequest, setCpcApplicationsLoading, setCpcApplicationsError, activeIprDetailId, setCpcApplications } = context;
        const requestId = cpcHistoryRequest.current + 1;
        cpcHistoryRequest.current = requestId;
        setCpcApplicationsLoading(true);
        setCpcApplicationsError("");
        try {
            const { data } = await api.get<{
                items: CpcApplication[];
            }>(`/ipr/cases/${caseId}/cpc-applications`);
            if (requestId !== cpcHistoryRequest.current ||
                activeIprDetailId.current !== caseId)
                return;
            setCpcApplications(data.items || []);
        }
        catch (error: any) {
            if (requestId !== cpcHistoryRequest.current ||
                activeIprDetailId.current !== caseId)
                return;
            setCpcApplications([]);
            setCpcApplicationsError(getIprApiErrorMessage(error, "CPC申报历史加载失败"));
        }
        finally {
            if (requestId === cpcHistoryRequest.current &&
                activeIprDetailId.current === caseId)
                setCpcApplicationsLoading(false);
        }
    };
    const generateCpcApplication = async (record: IprRecord) => {
        const { setCpcGenerating, activeIprDetailId } = context;
        if (record.data?.case_kind !== "专利") {
            message.warning("CPC申报仅适用于专利案件");
            return;
        }
        setCpcGenerating(true);
        try {
            await api.post(`/ipr/cases/${record.id}/cpc-applications`);
            message.success("CPC基础申报信息文件已生成");
            if (activeIprDetailId.current === record.id)
                await loadCpcApplications(record.id);
        }
        catch (error: any) {
            message.error(getIprApiErrorMessage(error, "CPC申报文件生成失败"));
        }
        finally {
            setCpcGenerating(false);
        }
    };
    const downloadCpcApplication = async (record: IprRecord, application: CpcApplication) => {
        try {
            const response = await api.get(`/ipr/cases/${record.id}/cpc-applications/${application.id}/download`, { responseType: "blob" });
            const url = URL.createObjectURL(response.data);
            const anchor = document.createElement("a");
            anchor.href = url;
            anchor.download =
                application.original_name ||
                    `CPC申报信息-${record.serial_no}.zip`;
            anchor.click();
            URL.revokeObjectURL(url);
        }
        catch (error: any) {
            let errorMessage = getIprApiErrorMessage(error, "CPC申报文件下载失败");
            if (error?.response?.data instanceof Blob) {
                try {
                    const payload = JSON.parse(await error.response.data.text());
                    errorMessage = getIprApiErrorMessage({ ...error, response: { ...error.response, data: payload } }, errorMessage);
                }
                catch {
                    // Keep the standard request error when a file response has no JSON error body.
                }
            }
            message.error(errorMessage);
        }
    };
    const loadIprFileTypes = async (caseKind: string) => {
        const { setIprFileTypes } = context;
        try {
            const { data } = await api.get<{
                items: IprFileType[];
            }>("/ipr/case-file-types", { params: { case_kind: caseKind } });
            setIprFileTypes(data.items || []);
        }
        catch (e: any) {
            setIprFileTypes([]);
            message.error(e?.response?.data?.detail || "案件文档类型加载失败");
        }
    };
    const openCpcApplicationWorkbench = async (record: IprRecord) => {
        const { openDetail } = context;
        if (record.data?.case_kind !== "专利")
            return;
        await openDetail(record);
    };
    const generateDocument = async (documentType: string) => {
        const { detail, setAttachments } = context;
        if (!detail)
            return;
        try {
            const { data } = await api.post(`/ipr/cases/${detail.id}/documents/${documentType}`);
            setAttachments((items) => [data, ...items]);
            message.success("案件文书已生成并归入案件附件");
        }
        catch (e: any) {
            message.error(e?.response?.data?.detail || "案件文书生成失败");
        }
    };
    const downloadAttachment = async (item: Attachment) => {
        try {
            const response = await api.get(`/attachments/${item.id}/download`, { responseType: "blob" });
            const url = URL.createObjectURL(response.data);
            const anchor = document.createElement("a");
            anchor.href = url;
            anchor.download = item.original_name;
            anchor.click();
            URL.revokeObjectURL(url);
        }
        catch {
            message.error("案件附件下载失败");
        }
    };
    const previewAttachment = async (item: Attachment) => {
        const previewWindow = window.open("", "_blank");
        if (!previewWindow) {
            message.warning("预览窗口被浏览器拦截");
            return;
        }
        previewWindow.opener = null;
        try {
            const response = await api.get(`/attachments/${item.id}/download`, { responseType: "blob" });
            const url = URL.createObjectURL(response.data);
            previewWindow.location.href = url;
        }
        catch {
            previewWindow.close();
            message.error("案件附件预览失败");
        }
    };
    const uploadIprFile = async () => {
        const { detail, iprFileForm, iprUploadFile, setIprFileOpen, setIprUploadFile } = context;
        if (!detail)
            return;
        try {
            const values = await iprFileForm.validateFields();
            if (!iprUploadFile) {
                message.warning("请选择案件文档");
                return;
            }
            const payload = new FormData();
            payload.append("file", iprUploadFile);
            payload.append("category", values.category);
            payload.append("document_date", formatRequiredDate(values.document_date, "文档日期"));
            payload.append("remark", values.remark || "");
            const uploadResponse = await api.post(`/ipr/cases/${detail.id}/files`, payload);
            const uploadResult = assertIprMutationSuccess(uploadResponse, "案件文档已上传");
            message.success(uploadResult);
            setIprFileOpen(false);
            setIprUploadFile(null);
            iprFileForm.resetFields();
            await loadIprFiles(detail.id);
        }
        catch (e: any) {
            if (!e?.errorFields)
                message.error(getIprApiErrorMessage(e, "上传案件文档失败"));
        }
    };
    const uploadIprBatchFile = async () => {
        const { iprBatchForm, iprBatchFile, setIprBatchOpen, setIprBatchFile } = context;
        try {
            const values = await iprBatchForm.validateFields();
            if (!iprBatchFile) {
                message.warning("请选择案件文档");
                return;
            }
            const payload = new FormData();
            payload.append("file", iprBatchFile);
            payload.append("case_ids", JSON.stringify(values.case_ids));
            payload.append("category", values.category);
            payload.append("document_date", formatRequiredDate(values.document_date, "文档日期"));
            payload.append("remark", values.remark || "");
            const batchUploadResponse = await api.post("/ipr/cases/files/batch-upload", payload);
            const batchUploadResult = assertIprMutationSuccess(batchUploadResponse, `已向 ${batchUploadResponse.data.created} 个案件上传文档`);
            message.success(batchUploadResult);
            setIprBatchOpen(false);
            setIprBatchFile(null);
            iprBatchForm.resetFields();
        }
        catch (e: any) {
            if (!e?.errorFields)
                message.error(getIprApiErrorMessage(e, "批量上传案件文档失败"));
        }
    };
    const markIprFileTransmitted = async (row: Attachment) => {
        const { detail } = context;
        if (!detail)
            return;
        try {
            const markResponse = await api.post(`/ipr/cases/${detail.id}/files/${row.id}/mark-transmitted`, { comment: "" });
            const markResult = assertIprMutationSuccess(markResponse, "已标记为已转");
            message.success(markResult);
            await loadIprFiles(detail.id);
        }
        catch (e: any) {
            message.error(getIprApiErrorMessage(e, "标记已转失败"));
        }
    };
    const markSelectedIprFilesTransmitted = async () => {
        const { detail, selectedIprFileIds, setSelectedIprFileIds } = context;
        if (!detail || !selectedIprFileIds.length)
            return;
        try {
            const batchMarkResponse = await api.post(`/ipr/cases/${detail.id}/files/mark-transmitted`, {
                attachment_ids: selectedIprFileIds,
                comment: "",
            });
            const batchMarkResult = assertIprMutationSuccess(batchMarkResponse, `已标记 ${batchMarkResponse.data.updated} 份文档为已转`);
            message.success(batchMarkResult);
            setSelectedIprFileIds([]);
            await loadIprFiles(detail.id);
        }
        catch (e: any) {
            message.error(getIprApiErrorMessage(e, "批量标记已转失败"));
        }
    };
    const deleteIprFile = async (row: Attachment) => {
        const { detail } = context;
        if (!detail)
            return;
        try {
            const deleteResponse = await api.delete(`/ipr/cases/${detail.id}/files/${row.id}`);
            const deleteResult = assertIprMutationSuccess(deleteResponse, "案件文档已删除");
            message.success(deleteResult);
            await loadIprFiles(detail.id);
        }
        catch (e: any) {
            message.error(getIprApiErrorMessage(e, "删除案件文档失败"));
        }
    };
    return { loadIprFiles, loadCpcApplications, generateCpcApplication, downloadCpcApplication, loadIprFileTypes, openCpcApplicationWorkbench, generateDocument, downloadAttachment, previewAttachment, uploadIprFile, uploadIprBatchFile, markIprFileTransmitted, markSelectedIprFilesTransmitted, deleteIprFile };
}
