import { message } from "antd";
import type { FormInstance } from "antd/es/form/hooks/useForm";
import dayjs from "dayjs";
import { api } from "../../api";
import { formatRequiredDate } from "../../formSafety";
import { attachmentRecordModule } from "../constants";
import type { Attachment, Fee, FinanceFlow, Transaction } from "../types";
type OriginalFieldSpec = {
    label: string;
    key?: string;
    control?: "date" | "money" | "multi";
    options?: string[];
    defaultValue?: any;
    disabled?: boolean;
    readOnly?: boolean;
    pickerLabel?: string;
};
type OriginalRouteConfig = {
    fields: OriginalFieldSpec[];
    headers: string[];
    source: "fees" | "incoming" | "invoices" | "settlements" | "generalSettlements" | "archiveSettlements" | "feeQuery" | "refundReviewFees" | "paymentPackages" | "unissuedFees";
    selectable?: boolean;
    clear?: boolean;
    upload?: boolean;
    export?: boolean;
    note?: string;
};
/** finance documents operations; dependencies are read when each operation runs. */
export interface FinanceDocumentsDependencies {
    readonly setRecordFiles: React.Dispatch<React.SetStateAction<Attachment[]>>;
    readonly setRecordFileTarget: React.Dispatch<React.SetStateAction<Fee | null>>;
    readonly setRecordFileTargets: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setRecordFile: React.Dispatch<React.SetStateAction<File | null>>;
    readonly setRecordUploadFiles: React.Dispatch<React.SetStateAction<File[]>>;
    readonly recordFileForm: FormInstance<any>;
    readonly recordFileTypeTree: any[];
    readonly setRecordFileTypeTree: React.Dispatch<React.SetStateAction<any[]>>;
    readonly recordFileTarget: Fee | null;
    readonly recordFile: File | null;
    readonly recordUploadFiles: File[];
    readonly recordFileTargets: Fee[];
    readonly voucherTarget: Transaction | null;
    readonly voucherForm: FormInstance<any>;
    readonly voucherFile: File | null;
    readonly setVoucherTarget: React.Dispatch<React.SetStateAction<Transaction | null>>;
    readonly setVoucherFile: React.Dispatch<React.SetStateAction<File | null>>;
    readonly load: () => Promise<void>;
}
export function createFinanceDocumentsActions(context: FinanceDocumentsDependencies) {
    const openRecordFiles = async (row: FinanceFlow, category: string, targets: FinanceFlow[] = [row]) => {
        const { setRecordFiles, setRecordFileTarget, setRecordFileTargets, setRecordFile, setRecordUploadFiles, recordFileForm, recordFileTypeTree, setRecordFileTypeTree } = context;
        try {
            const recordModule = attachmentRecordModule(row, category);
            const { data } = await api.get("/attachments", {
                params: { record_id: row.id, category, module: row.module || recordModule },
            });
            setRecordFiles(data.items);
            setRecordFileTarget(row);
            setRecordFileTargets(targets);
            setRecordFile(null);
            setRecordUploadFiles([]);
            recordFileForm.setFieldsValue({ category, remark: "", document_date: dayjs() });
            if (targets.length > 1 && !recordFileTypeTree.length) {
                api.get("/system/parameters/options", { params: { category: "case_file_type" } })
                    .then(({ data }) => setRecordFileTypeTree(data.items || []))
                    .catch(() => setRecordFileTypeTree([]));
            }
        }
        catch (error: any) {
            setRecordFiles([]);
            setRecordFileTarget(null);
            setRecordFileTargets([]);
            setRecordFile(null);
            setRecordUploadFiles([]);
            message.error(error?.response?.data?.detail || "业务凭证加载失败");
        }
    };
    const uploadRecordFile = async () => {
        const { recordFileTarget, recordFile, recordUploadFiles, recordFileForm, recordFileTargets } = context;
        if (!recordFileTarget || (!recordFile && !recordUploadFiles.length))
            return message.warning("请选择文件");
        const v = await recordFileForm.validateFields();
        try {
            const filesToUpload = recordUploadFiles.length ? recordUploadFiles : [recordFile!];
            for (const target of recordFileTargets.length ? recordFileTargets : [recordFileTarget]) {
                for (const sourceFile of filesToUpload) {
                    const form = new FormData();
                    form.append("file", sourceFile);
                    form.append("record_id", String(target.id));
                    form.append("category", v.category);
                    form.append("module", attachmentRecordModule(target, v.category));
                    form.append("remark", v.remark || "");
                    if (v.document_date)
                        form.append("document_date", formatRequiredDate(v.document_date, "参考日期"));
                    await api.post("/attachments", form);
                }
            }
            message.success(`${filesToUpload.length} 个文件已上传到 ${recordFileTargets.length || 1} 个案件`);
            await openRecordFiles(recordFileTarget, v.category, recordFileTargets);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "上传失败");
        }
    };
    const deleteRecordFile = async (row: Attachment) => {
        const { setRecordFiles } = context;
        try {
            await api.delete(`/attachments/${row.id}`);
            setRecordFiles((files) => files.filter((x) => x.id !== row.id));
            message.success("凭证已删除");
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "删除失败");
        }
    };
    const uploadVoucher = async () => {
        const { voucherTarget, voucherForm, voucherFile, setVoucherTarget, setVoucherFile, load } = context;
        if (!voucherTarget)
            return;
        const v = await voucherForm.validateFields();
        if (!voucherFile) {
            message.warning("请选择凭证文件");
            return;
        }
        const form = new FormData();
        form.append("file", voucherFile);
        form.append("finance_transaction_id", String(voucherTarget.id));
        form.append("category", v.category);
        form.append("remark", v.remark || "");
        try {
            const { data } = await api.post("/attachments", form);
            const vouchers = [...(voucherTarget.vouchers || []), data];
            setVoucherTarget({
                ...voucherTarget,
                vouchers,
                voucher_count: vouchers.length,
                voucher_categories: [...new Set(vouchers.map((x) => x.category))],
            });
            setVoucherFile(null);
            voucherForm.setFieldValue("remark", "");
            message.success("凭证上传成功");
            load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "凭证上传失败");
        }
    };
    const downloadVoucher = async (row: Attachment) => {
        try {
            const res = await api.get(`/attachments/${row.id}/download`, {
                responseType: "blob",
            });
            const url = URL.createObjectURL(res.data);
            const a = document.createElement("a");
            a.href = url;
            a.download = row.original_name;
            a.click();
            URL.revokeObjectURL(url);
        }
        catch {
            message.error("凭证下载失败");
        }
    };
    const deleteVoucher = async (row: Attachment) => {
        const { voucherTarget, setVoucherTarget, load } = context;
        try {
            await api.delete(`/attachments/${row.id}`);
            if (voucherTarget) {
                const vouchers = voucherTarget.vouchers.filter((x) => x.id !== row.id);
                setVoucherTarget({
                    ...voucherTarget,
                    vouchers,
                    voucher_count: vouchers.length,
                    voucher_categories: [...new Set(vouchers.map((x) => x.category))],
                });
            }
            message.success("凭证已删除");
            load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "删除失败");
        }
    };
    return { openRecordFiles, uploadRecordFile, deleteRecordFile, uploadVoucher, downloadVoucher, deleteVoucher };
}
