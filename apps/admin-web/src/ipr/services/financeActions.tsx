import { message } from "antd";
import type { FormInstance } from "antd/es/form/hooks/useForm";
import { api } from "../../api";
import { formatRequiredDate } from "../../formSafety";
import { getIprApiErrorMessage } from "../../iprCaseDetailParity.mjs";
import { IPR_DETAIL_DEFAULT_PAGE, IPR_LAWSUIT_FEE_OPTIONS } from "../constants";
import type { AnnualFee, AnnualFeePagePayload, AssistedFee, IprDetailPagePayload, IprDetailPageState, IprRecord } from "../types";
/** ipr finance operations; dependencies are read when each operation runs. */
export interface IprFinanceDependencies {
    readonly detail: IprRecord | null;
    readonly lawsuitFeeForm: FormInstance<any>;
    readonly setLawsuitFeeOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly loadLawsuitManagement: (caseId: number) => Promise<void>;
    readonly assistedFeesPageState: IprDetailPageState;
    readonly setAssistedFees: React.Dispatch<React.SetStateAction<AssistedFee[]>>;
    readonly setCanManageAssistedFees: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setAssistedFeesPageState: React.Dispatch<React.SetStateAction<IprDetailPageState>>;
    readonly clearIprSectionError: (section: "files" | "logs" | "reminders" | "tasks" | "assistedFees" | "annualFees") => void;
    readonly setIprSectionError: (section: "files" | "logs" | "reminders" | "tasks" | "assistedFees" | "annualFees", error: unknown) => void;
    readonly loadIprLogs: (caseId: number) => Promise<void>;
    readonly annualFeesPageState: IprDetailPageState;
    readonly annualFeeYearFilter: number | undefined;
    readonly setAnnualFees: React.Dispatch<React.SetStateAction<AnnualFee[]>>;
    readonly setAnnualFeesPageState: React.Dispatch<React.SetStateAction<IprDetailPageState>>;
    readonly setAnnualFeesCanManage: React.Dispatch<React.SetStateAction<boolean>>;
    readonly assistedForm: FormInstance<any>;
    readonly setAssistedOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly editingAssistedFee: AssistedFee | null;
    readonly assistedEditForm: FormInstance<any>;
    readonly setEditingAssistedFee: React.Dispatch<React.SetStateAction<AssistedFee | null>>;
    readonly transactTarget: AssistedFee | null;
    readonly transactForm: FormInstance<any>;
    readonly receiptFile: File | null;
    readonly setTransactTarget: React.Dispatch<React.SetStateAction<AssistedFee | null>>;
    readonly setReceiptFile: React.Dispatch<React.SetStateAction<File | null>>;
    readonly annualFeeForm: FormInstance<any>;
    readonly editingAnnualFee: AnnualFee | null;
    readonly setAnnualFeeOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setEditingAnnualFee: React.Dispatch<React.SetStateAction<AnnualFee | null>>;
}
export function createIprFinanceActions(context: IprFinanceDependencies) {
    const createLawsuitFee = async () => {
        const { detail, lawsuitFeeForm, setLawsuitFeeOpen, loadLawsuitManagement } = context;
        if (!detail)
            return;
        try {
            const values = await lawsuitFeeForm.validateFields();
            const feeOption = IPR_LAWSUIT_FEE_OPTIONS.find((item) => item.value === values.lawsuit_fee_kind);
            if (!feeOption)
                throw new Error("诉讼费用类型无效");
            await api.post(`/ipr/cases/${detail.id}/fees`, {
                title: feeOption.label,
                fee_type: feeOption.feeType,
                amount: values.amount,
                fee_date: values.fee_date?.format("YYYY-MM-DD"),
                description: values.remark || "",
            });
            message.success("诉讼费用已登记");
            setLawsuitFeeOpen(false);
            await loadLawsuitManagement(detail.id);
        }
        catch (error: any) {
            if (!error?.errorFields)
                message.error(error?.response?.data?.detail || "诉讼费用登记失败");
        }
    };
    const loadAssistedFees = async (caseId: number, nextPage = context.assistedFeesPageState.page, nextPageSize = context.assistedFeesPageState.pageSize) => {
        const { assistedFeesPageState, setAssistedFees, setCanManageAssistedFees, setAssistedFeesPageState, clearIprSectionError, setIprSectionError } = context;
        try {
            const { data } = await api.get<IprDetailPagePayload<AssistedFee>>(`/ipr/cases/${caseId}/assisted-fees`, { params: { page: nextPage, page_size: nextPageSize } });
            setAssistedFees(data.items || []);
            setCanManageAssistedFees(Boolean(data.capabilities?.can_manage));
            setAssistedFeesPageState({
                page: data.page ?? nextPage,
                pageSize: data.page_size ?? nextPageSize,
                total: data.total ?? data.items?.length ?? 0,
                pages: data.pages ?? 0,
            });
            clearIprSectionError("assistedFees");
        }
        catch (error) {
            setIprSectionError("assistedFees", error);
        }
    };
    const refreshAssistedFeesAndLogs = async (caseId: number) => {
        const { loadIprLogs } = context;
        await Promise.all([loadAssistedFees(caseId), loadIprLogs(caseId)]);
    };
    const loadAnnualFees = async (caseId: number, nextPage = context.annualFeesPageState.page, nextPageSize = context.annualFeesPageState.pageSize, nextFeeYear = context.annualFeeYearFilter) => {
        const { annualFeesPageState, annualFeeYearFilter, setAnnualFees, setAnnualFeesPageState, setAnnualFeesCanManage, clearIprSectionError, setIprSectionError } = context;
        try {
            const { data } = await api.get<AnnualFeePagePayload>(`/ipr/cases/${caseId}/annual-fees`, {
                params: {
                    page: nextPage,
                    page_size: nextPageSize,
                    fee_year: nextFeeYear,
                },
            });
            setAnnualFees(data.items || []);
            setAnnualFeesPageState({
                page: data.page ?? nextPage,
                pageSize: data.page_size ?? nextPageSize,
                total: data.total ?? data.items?.length ?? 0,
                pages: data.pages ?? 0,
            });
            setAnnualFeesCanManage(Boolean(data.capabilities?.can_manage));
            clearIprSectionError("annualFees");
        }
        catch (error) {
            setIprSectionError("annualFees", error);
        }
    };
    const createAssistedFee = async () => {
        const { detail, assistedForm, setAssistedOpen } = context;
        if (!detail)
            return;
        try {
            const values = await assistedForm.validateFields();
            await api.post(`/ipr/cases/${detail.id}/assisted-fees`, values);
            message.success("协助费已提交，等待确认");
            setAssistedOpen(false);
            assistedForm.resetFields();
            await refreshAssistedFeesAndLogs(detail.id);
        }
        catch (e: any) {
            if (!e?.errorFields)
                message.error(e?.response?.data?.detail || "新增协助费失败");
        }
    };
    const updateAssistedFee = async () => {
        const { detail, editingAssistedFee, assistedEditForm, setEditingAssistedFee } = context;
        if (!detail || !editingAssistedFee)
            return;
        try {
            const values = await assistedEditForm.validateFields();
            await api.patch(`/ipr/cases/${detail.id}/assisted-fees/${editingAssistedFee.id}`, values);
            message.success("协助费已更新");
            setEditingAssistedFee(null);
            assistedEditForm.resetFields();
            await refreshAssistedFeesAndLogs(detail.id);
        }
        catch (e: any) {
            if (!e?.errorFields)
                message.error(e?.response?.data?.detail || "编辑协助费失败");
        }
    };
    const confirmAssistedFee = async (row: AssistedFee) => {
        const { detail } = context;
        if (!detail)
            return;
        try {
            await api.post(`/ipr/cases/${detail.id}/assisted-fees/${row.id}/confirm`, {});
            message.success("协助费已确认，等待办理");
            await refreshAssistedFeesAndLogs(detail.id);
        }
        catch (e: any) {
            message.error(e?.response?.data?.detail || "确认协助费失败");
        }
    };
    const transactAssistedFee = async () => {
        const { detail, transactTarget, transactForm, receiptFile, setTransactTarget, setReceiptFile } = context;
        if (!detail || !transactTarget)
            return;
        try {
            const values = await transactForm.validateFields();
            if (!receiptFile) {
                message.warning("请上传协助费回执文件");
                return;
            }
            const payload = new FormData();
            payload.append("response_date", formatRequiredDate(values.response_date, "办理日期"));
            payload.append("file", receiptFile);
            payload.append("remark", values.remark || "");
            await api.post(`/ipr/cases/${detail.id}/assisted-fees/${transactTarget.id}/transact`, payload);
            message.success("协助费已办理并保存回执");
            setTransactTarget(null);
            setReceiptFile(null);
            transactForm.resetFields();
            await refreshAssistedFeesAndLogs(detail.id);
        }
        catch (e: any) {
            if (!e?.errorFields)
                message.error(e?.response?.data?.detail || "办理协助费失败");
        }
    };
    const deleteAssistedFee = async (row: AssistedFee) => {
        const { detail } = context;
        if (!detail)
            return;
        try {
            await api.delete(`/ipr/cases/${detail.id}/assisted-fees/${row.id}`);
            message.success("协助费已删除");
            await loadAssistedFees(detail.id);
        }
        catch (e: any) {
            message.error(e?.response?.data?.detail || "删除协助费失败");
        }
    };
    const saveAnnualFee = async () => {
        const { detail, annualFeeForm, editingAnnualFee, setAnnualFeeOpen, setEditingAnnualFee, annualFeesPageState } = context;
        if (!detail)
            return;
        try {
            const values = await annualFeeForm.validateFields();
            const payload = {
                fee_year: Number(values.fee_year),
                fee_name: String(values.fee_name || "").trim(),
                amount: Number(values.amount),
                currency: values.currency || "CNY",
                due_date: formatRequiredDate(values.due_date, "缴费期限"),
                paid_date: values.paid_date
                    ? formatRequiredDate(values.paid_date, "缴费日期")
                    : null,
                status: values.status,
                reminder_date: values.reminder_date
                    ? formatRequiredDate(values.reminder_date, "提醒日期")
                    : null,
                notes: String(values.notes || "").trim(),
            };
            if (payload.status === "已缴" && !payload.paid_date) {
                annualFeeForm.setFields([
                    {
                        name: "paid_date",
                        errors: ["已缴状态必须填写缴费日期"],
                    },
                ]);
                return;
            }
            if (payload.status !== "已缴" && payload.paid_date) {
                annualFeeForm.setFields([
                    {
                        name: "paid_date",
                        errors: ["待缴或未缴状态不能填写缴费日期"],
                    },
                ]);
                return;
            }
            if (editingAnnualFee) {
                await api.put(`/ipr/cases/${detail.id}/annual-fees/${editingAnnualFee.id}`, payload);
                message.success("年费明细已更新");
            }
            else {
                await api.post(`/ipr/cases/${detail.id}/annual-fees`, payload);
                message.success("年费明细已新增");
            }
            setAnnualFeeOpen(false);
            setEditingAnnualFee(null);
            annualFeeForm.resetFields();
            await loadAnnualFees(detail.id, IPR_DETAIL_DEFAULT_PAGE, annualFeesPageState.pageSize);
        }
        catch (error: any) {
            if (!error?.errorFields)
                message.error(getIprApiErrorMessage(error, editingAnnualFee
                    ? "更新年费明细失败"
                    : "新增年费明细失败"));
        }
    };
    const deleteAnnualFee = async (row: AnnualFee) => {
        const { detail, annualFeesPageState } = context;
        if (!detail)
            return;
        try {
            await api.delete(`/ipr/cases/${detail.id}/annual-fees/${row.id}`);
            message.success("年费明细及其专属提醒已删除");
            await loadAnnualFees(detail.id, annualFeesPageState.page, annualFeesPageState.pageSize);
        }
        catch (error) {
            message.error(getIprApiErrorMessage(error, "删除年费明细失败"));
        }
    };
    return { createLawsuitFee, loadAssistedFees, refreshAssistedFeesAndLogs, loadAnnualFees, createAssistedFee, updateAssistedFee, confirmAssistedFee, transactAssistedFee, deleteAssistedFee, saveAnnualFee, deleteAnnualFee };
}
