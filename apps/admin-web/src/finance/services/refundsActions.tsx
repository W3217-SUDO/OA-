import { message } from "antd";
import type { FormInstance } from "antd/es/form/hooks/useForm";
import dayjs from "dayjs";
import { api } from "../../api";
import { normalizeRefundResponse, refreshRefundListWithFallback, refundAmountUpdateRequest, refundBatchStatusRequest, refundExportRequestParams, refundListRequest, refundLoadFailure, refundSelectedExportRequestParams, refundStatusForRoute } from "../../financeRefundHelpers.mjs";
import { formatRequiredDate } from "../../formSafety";
import type { Fee, FinanceFlow } from "../types";
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
/** finance refunds operations; dependencies are read when each operation runs. */
export interface FinanceRefundsDependencies {
    readonly refundDetailRequestGuard: {
        begin: () => number;
        isLatest: (token: number) => boolean;
    };
    readonly setRefundDetail: React.Dispatch<React.SetStateAction<Fee | null>>;
    readonly refundMeta: {
        total: number;
        page: number;
        pageSize: number;
    };
    readonly initialView: string;
    readonly refundStatusFilter: string;
    readonly refundGroupFilter: string;
    readonly refundRequestGuard: {
        begin: () => number;
        isLatest: (token: number) => boolean;
    };
    readonly setRefunds: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setRefundMeta: React.Dispatch<React.SetStateAction<{
        total: number;
        page: number;
        pageSize: number;
    }>>;
    readonly setSelectedRefundRows: React.Dispatch<React.SetStateAction<number[]>>;
    readonly refunds: Fee[];
    readonly activeRefundStatus: string;
    readonly refundForm: FormInstance<any>;
    readonly setRefundOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly refundAmountTarget: Fee | null;
    readonly refundAmountForm: FormInstance<any>;
    readonly setRefundMutationLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setRefundAmountTarget: React.Dispatch<React.SetStateAction<Fee | null>>;
    readonly selectedRefundRows: number[];
    readonly refundBatchStatus: string;
    readonly setRefundBatchStatusOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly refundCompleteTarget: Fee | null;
    readonly refundCompleteForm: FormInstance<any>;
    readonly setRefundCompleteTarget: React.Dispatch<React.SetStateAction<Fee | null>>;
    readonly requireRefundCaseFeeSelection: () => number[];
    readonly refundCaseFeeStatus: string;
    readonly setRefundCaseFeeMutationLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setRefundCaseFeeStatusOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setSelectedOriginalRows: React.Dispatch<React.SetStateAction<(string | number)[]>>;
    readonly loadFeeQuery: (query: Record<string, any>, page?: number, pageSize?: number) => Promise<void>;
    readonly originalQuery: Record<string, any>;
    readonly feeQueryMeta: {
        total: number;
        page: number;
        pageSize: number;
        totals: Record<string, number | null>;
    };
    readonly refundCaseFeeLogKind: "court" | "other" | "received" | null;
    readonly refundCaseFeeLogContent: string;
    readonly setRefundCaseFeeLogKind: React.Dispatch<React.SetStateAction<"court" | "other" | "received" | null>>;
    readonly setRefundCaseFeeLogContent: React.Dispatch<React.SetStateAction<string>>;
    readonly isRefundNotRequiredRoute: boolean;
    readonly refundBatchFeeForm: FormInstance<any>;
    readonly setRefundBatchFeeLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly refundBatchFeeBaseType: string;
    readonly closeRefundBatchFee: () => void;
    readonly load: () => Promise<void>;
}
export function createFinanceRefundsActions(context: FinanceRefundsDependencies) {
    const openRefundDetail = async (row: FinanceFlow) => {
        const { refundDetailRequestGuard, setRefundDetail } = context;
        const token = refundDetailRequestGuard.begin();
        try {
            const { data } = await api.get(`/records/${row.id}`);
            if (!refundDetailRequestGuard.isLatest(token))
                return;
            if (!data || data.module !== "refund") {
                throw new Error("退款详情记录无效");
            }
            if (String(data.id) !== String(row.id)) {
                throw new Error("退款详情记录不匹配");
            }
            setRefundDetail(data);
        }
        catch (error: any) {
            if (refundDetailRequestGuard.isLatest(token)) {
                message.error(error?.response?.data?.detail || error?.message || "退款详情加载失败");
            }
        }
    };
    const loadRefunds = async (page = 1, pageSize = context.refundMeta.pageSize, status = refundStatusForRoute(context.initialView, context.refundStatusFilter), preserveOnError = false, group = context.refundGroupFilter) => {
        const { refundMeta, initialView, refundStatusFilter, refundGroupFilter, refundRequestGuard, setRefunds, setRefundMeta, setSelectedRefundRows, refunds } = context;
        const requestToken = refundRequestGuard.begin();
        try {
            const request = refundListRequest(page, pageSize, status, group);
            const response = await api.get(request.url, { params: request.params });
            if (!refundRequestGuard.isLatest(requestToken)) {
                return { applied: false, response: null };
            }
            const normalized = normalizeRefundResponse(response.data, page, pageSize);
            setRefunds(normalized.items);
            setRefundMeta(normalized);
            setSelectedRefundRows([]);
            return { applied: true, response };
        }
        catch (error: any) {
            if (!refundRequestGuard.isLatest(requestToken)) {
                return { applied: false, response: null };
            }
            const failure = refundLoadFailure({
                items: refunds,
                total: refundMeta.total,
                page: refundMeta.page,
                pageSize: refundMeta.pageSize,
            }, error);
            message.error(failure.message);
            if (!preserveOnError)
                throw error;
            return { applied: false, response: null };
        }
    };
    const refreshRefundList = async (page = context.refundMeta.page) => {
        const { refundMeta, activeRefundStatus, refundGroupFilter } = context;
        return refreshRefundListWithFallback({
            load: loadRefunds,
            page,
            pageSize: refundMeta.pageSize,
            status: activeRefundStatus,
            group: refundGroupFilter,
        });
    };
    const createRefund = async () => {
        const { refundForm, setRefundOpen } = context;
        const v = await refundForm.validateFields();
        try {
            await api.post("/finance/refunds", {
                ...v,
                expected_date: v.expected_date?.format("YYYY-MM-DD") || null,
            });
            message.success("诉讼费退款草稿已创建");
            setRefundOpen(false);
            refundForm.resetFields();
            await refreshRefundList(1);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "退款申请创建失败");
        }
    };
    const updateRefundAmount = async () => {
        const { refundAmountTarget, initialView, refundStatusFilter, refundAmountForm, setRefundMutationLoading, setRefundAmountTarget, refundMeta, refundGroupFilter } = context;
        if (!refundAmountTarget)
            return;
        const mutationStatus = refundStatusForRoute(initialView, refundStatusFilter);
        const values = await refundAmountForm.validateFields();
        const request = refundAmountUpdateRequest(refundAmountTarget.id, Number(values.amount), String(values.comment || ""));
        setRefundMutationLoading(true);
        try {
            await api.patch(request.url, request.body);
            message.success("退款金额已修改");
            setRefundAmountTarget(null);
            refundAmountForm.resetFields();
            await loadRefunds(refundMeta.page, refundMeta.pageSize, mutationStatus, true, refundGroupFilter);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "退款金额修改失败");
        }
        finally {
            setRefundMutationLoading(false);
        }
    };
    const updateRefundBatchStatus = async () => {
        const { initialView, refundStatusFilter, selectedRefundRows, refundBatchStatus, setRefundMutationLoading, setRefundBatchStatusOpen, refundMeta, refundGroupFilter } = context;
        const mutationStatus = refundStatusForRoute(initialView, refundStatusFilter);
        const request = refundBatchStatusRequest(selectedRefundRows, refundBatchStatus, "批量修改退费进度");
        setRefundMutationLoading(true);
        try {
            await api.post(request.url, request.body);
            message.success("退费进度已批量修改");
            setRefundBatchStatusOpen(false);
            await loadRefunds(refundMeta.page, refundMeta.pageSize, mutationStatus, true, refundGroupFilter);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "退费进度修改失败");
        }
        finally {
            setRefundMutationLoading(false);
        }
    };
    const completeRefund = async () => {
        const { refundCompleteTarget, refundCompleteForm, setRefundCompleteTarget } = context;
        if (!refundCompleteTarget)
            return;
        const v = await refundCompleteForm.validateFields();
        try {
            await api.post(`/finance/refunds/${refundCompleteTarget.id}/complete`, {
                ...v,
                actual_date: formatRequiredDate(v.actual_date, "实际退款日期"),
            });
            message.success("退款到账已登记");
            setRefundCompleteTarget(null);
            refundCompleteForm.resetFields();
            await refreshRefundList();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "退款到账登记失败");
        }
    };
    const submitRefundCaseFeeStatus = async (forcedStatus?: string) => {
        const { requireRefundCaseFeeSelection, refundCaseFeeStatus, setRefundCaseFeeMutationLoading, setRefundCaseFeeStatusOpen, setSelectedOriginalRows, loadFeeQuery, originalQuery, feeQueryMeta } = context;
        const ids = requireRefundCaseFeeSelection();
        if (!ids.length)
            return;
        const status = forcedStatus || refundCaseFeeStatus;
        setRefundCaseFeeMutationLoading(true);
        try {
            await api.post("/finance/case-fees/refunds/status", {
                ids,
                status,
                comment: status === "R100" ? "标记不再办理退费" : "退费查询批量修改进度",
            });
            message.success(status === "R100" ? "已标记不再办理退费" : "退费进度已修改");
            setRefundCaseFeeStatusOpen(false);
            setSelectedOriginalRows([]);
            await loadFeeQuery(originalQuery, feeQueryMeta.page, feeQueryMeta.pageSize);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "退费操作失败");
        }
        finally {
            setRefundCaseFeeMutationLoading(false);
        }
    };
    const submitRefundCaseFeeLog = async () => {
        const { requireRefundCaseFeeSelection, refundCaseFeeLogKind, refundCaseFeeLogContent, setRefundCaseFeeMutationLoading, setRefundCaseFeeLogKind, setRefundCaseFeeLogContent } = context;
        const ids = requireRefundCaseFeeSelection();
        if (!ids.length || !refundCaseFeeLogKind)
            return;
        if (refundCaseFeeLogContent.trim().length < 2) {
            message.warning("请输入至少 2 个字的日志内容");
            return;
        }
        setRefundCaseFeeMutationLoading(true);
        try {
            await api.post("/finance/case-fees/refunds/logs", {
                ids,
                kind: refundCaseFeeLogKind,
                content: refundCaseFeeLogContent.trim(),
            });
            message.success("退费日志已保存");
            setRefundCaseFeeLogKind(null);
            setRefundCaseFeeLogContent("");
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "退费日志保存失败");
        }
        finally {
            setRefundCaseFeeMutationLoading(false);
        }
    };
    const exportRefunds = async (selectedOnly: boolean) => {
        const { selectedRefundRows, isRefundNotRequiredRoute, activeRefundStatus, refundGroupFilter, refundStatusFilter } = context;
        if (selectedOnly && !selectedRefundRows.length) {
            message.warning("请先选择需要导出的退款记录");
            return;
        }
        const exportParams = selectedOnly
            ? isRefundNotRequiredRoute
                ? refundSelectedExportRequestParams(selectedRefundRows, activeRefundStatus, refundGroupFilter)
                : refundSelectedExportRequestParams(selectedRefundRows, refundStatusFilter, refundGroupFilter)
            : isRefundNotRequiredRoute
                ? refundExportRequestParams(activeRefundStatus, refundGroupFilter)
                : refundExportRequestParams(refundStatusFilter, refundGroupFilter);
        try {
            const response = await api.get(selectedOnly
                ? "/finance/refunds/export-selected"
                : "/finance/refunds/export", {
                params: exportParams,
                responseType: "blob",
            });
            const url = URL.createObjectURL(response.data);
            const anchor = document.createElement("a");
            anchor.href = url;
            anchor.download = `诉讼费退款-${selectedOnly ? "选中" : "全部"}-${dayjs().format("YYYY-MM-DD")}.xls`;
            anchor.click();
            URL.revokeObjectURL(url);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail ||
                (selectedOnly ? "退款选中导出失败" : "退款全量导出失败"));
        }
    };
    const submitRefundBatchFee = async () => {
        const { refundBatchFeeForm, setRefundBatchFeeLoading, refundBatchFeeBaseType, closeRefundBatchFee, setSelectedOriginalRows, load } = context;
        const values = await refundBatchFeeForm.validateFields();
        setRefundBatchFeeLoading(true);
        try {
            const { data } = await api.post("/finance/case-fees/batch", {
                handler: values.handler,
                submit_payment: refundBatchFeeBaseType !== "代理费",
                items: values.items.map((item: Record<string, any>) => ({
                    case_id: item.case_id,
                    contract_record_id: item.contract_record_id || null,
                    fee_type_id: item.fee_type_id || null,
                    fee_type: item.fee_type,
                    amount: item.amount,
                    remark: item.remark || "",
                    deadline: item.deadline ? formatRequiredDate(item.deadline, "截止日期") : null,
                    payment_type_id: item.payment_type_id || null,
                    payment_amount: item.payment_amount || Math.abs(Number(item.amount || 0)),
                    payment_remark: item.payment_remark || "",
                    payee_username: item.payee_username || "",
                    base_amount: item.base_amount || 0,
                    reference_commission: item.reference_commission || 0,
                })),
            });
            message.success(`已创建 ${data.created} 条案件费用${refundBatchFeeBaseType === "代理费" ? "" : "并提交付款申请"}`);
            closeRefundBatchFee();
            setSelectedOriginalRows([]);
            await load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "批量新增费用失败");
        }
        finally {
            setRefundBatchFeeLoading(false);
        }
    };
    return { openRefundDetail, loadRefunds, refreshRefundList, createRefund, updateRefundAmount, updateRefundBatchStatus, completeRefund, submitRefundCaseFeeStatus, submitRefundCaseFeeLog, exportRefunds, submitRefundBatchFee };
}
