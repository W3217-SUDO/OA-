import { message, Modal } from "antd";
import type { FormInstance } from "antd/es/form/hooks/useForm";
import dayjs from "dayjs";
import { api } from "../../api";
import type { FinanceActionGate } from "../../financeActionGate.mjs";
import { normalizeSettlementContextRows, settlementContextPageSize, settlementContextTasksRequest } from "../constants";
import type { Fee } from "../types";
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
/** finance settlements operations; dependencies are read when each operation runs. */
export interface FinanceSettlementsDependencies {
    readonly generalSettlementMeta: {
        total: number;
        page: number;
        pageSize: number;
        totals: Record<string, number>;
    };
    readonly isGeneralSettlementPendingRoute: boolean;
    readonly generalSettlementParams: (query: Record<string, any>, page?: number, pageSize?: number) => {
        customer: any;
        case_no: any;
        customer_manager: any;
        received_from: any;
        received_to: any;
        payer: any;
        payment_method: any;
        applied_by: any;
        applied_from: any;
        applied_to: any;
        hearing_lawyer: any;
        assistant: any;
        reviewer: any;
        reviewed_from: any;
        reviewed_to: any;
        source_person: any;
        paid_from: any;
        paid_to: any;
        status: string;
        page: number;
        page_size: number;
        case_customer?: undefined;
    } | {
        customer: any;
        case_no: any;
        received_from: any;
        received_to: any;
        payer: any;
        payment_method: any;
        case_customer: any;
        hearing_lawyer: any;
        assistant: any;
        customer_manager: any;
        source_person: any;
        page: number;
        page_size: number;
        applied_by?: undefined;
        applied_from?: undefined;
        applied_to?: undefined;
        reviewer?: undefined;
        reviewed_from?: undefined;
        reviewed_to?: undefined;
        paid_from?: undefined;
        paid_to?: undefined;
        status?: undefined;
    };
    readonly setGeneralSettlementRows: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setGeneralSettlementMeta: React.Dispatch<React.SetStateAction<{
        total: number;
        page: number;
        pageSize: number;
        totals: Record<string, number>;
    }>>;
    readonly archiveSettlementMeta: {
        total: number;
        page: number;
        pageSize: number;
        totals: Record<string, number>;
    };
    readonly isArchiveSettlementPaymentRoute: boolean;
    readonly isArchiveSettlementPaidRoute: boolean;
    readonly isArchiveSettlementRejectedRoute: boolean;
    readonly archiveSettlementParams: (query: Record<string, any>, page?: number, pageSize?: number) => {
        case_no: any;
        customer: any;
        reviewer: any;
        reviewed_from: any;
        reviewed_to: any;
        archive_from: any;
        archive_to: any;
        payment_from: any;
        payment_to: any;
        page: number;
        page_size: number;
        submitted_from: any;
        submitted_to: any;
        case_type: any;
        case_stage: any;
        payer: any;
        received_from: any;
        received_to: any;
        hearing_lawyer: any;
        assistant: any;
        submitted_by: any;
    } | {
        case_no: any;
        customer: any;
        reviewer: any;
        reviewed_from: any;
        reviewed_to: any;
        archive_from: any;
        archive_to: any;
        payment_from: any;
        payment_to: any;
        page: number;
        page_size: number;
        settled_from: any;
        settled_to: any;
        case_type: any;
        case_stage: any;
        payer: any;
        received_from: any;
        received_to: any;
        hearing_lawyer: any;
        assistant: any;
        submitted_by: any;
    };
    readonly setArchiveSettlementRows: React.Dispatch<React.SetStateAction<any[]>>;
    readonly setArchiveSettlementMeta: React.Dispatch<React.SetStateAction<{
        total: number;
        page: number;
        pageSize: number;
        totals: Record<string, number>;
    }>>;
    readonly generalSettlementReviewTargets: Fee[];
    readonly financeActionGates: {
        archiveSettlement: FinanceActionGate;
        generalSettlement: FinanceActionGate;
        paymentPackage: FinanceActionGate;
    };
    readonly setGeneralSettlementBusy: React.Dispatch<React.SetStateAction<boolean>>;
    readonly generalSettlementReviewApproved: boolean;
    readonly generalSettlementReviewComment: string;
    readonly setGeneralSettlementReviewTargets: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setGeneralSettlementReviewComment: React.Dispatch<React.SetStateAction<string>>;
    readonly setSelectedOriginalRows: React.Dispatch<React.SetStateAction<(string | number)[]>>;
    readonly setGeneralSettlementDetails: React.Dispatch<React.SetStateAction<(string | number)[]>>;
    readonly originalQuery: Record<string, any>;
    readonly generalSettlementPaymentTargets: Fee[];
    readonly generalSettlementPaymentAction: "paid" | "rollback";
    readonly generalSettlementPaymentComment: string;
    readonly setGeneralSettlementPaymentTargets: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setGeneralSettlementPaymentComment: React.Dispatch<React.SetStateAction<string>>;
    readonly generalSettlementReapplyTargets: Fee[];
    readonly generalSettlementReapplyComment: string;
    readonly setGeneralSettlementReapplyTargets: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setGeneralSettlementReapplyComment: React.Dispatch<React.SetStateAction<string>>;
    readonly selectedOriginalRows: (string | number)[];
    readonly setArchiveSettlementBusy: React.Dispatch<React.SetStateAction<boolean>>;
    readonly archiveSettlementReviewTargets: any[];
    readonly archiveSettlementReviewApproved: boolean;
    readonly archiveSettlementReviewComment: string;
    readonly setArchiveSettlementReviewTargets: React.Dispatch<React.SetStateAction<any[]>>;
    readonly setArchiveSettlementReviewComment: React.Dispatch<React.SetStateAction<string>>;
    readonly archiveSettlementRollbackTargets: any[];
    readonly archiveSettlementRollbackComment: string;
    readonly setArchiveSettlementRollbackTargets: React.Dispatch<React.SetStateAction<any[]>>;
    readonly setArchiveSettlementRollbackComment: React.Dispatch<React.SetStateAction<string>>;
    readonly archiveSettlementReapplyTargets: any[];
    readonly archiveSettlementReapplyComment: string;
    readonly setArchiveSettlementReapplyTargets: React.Dispatch<React.SetStateAction<any[]>>;
    readonly setArchiveSettlementReapplyComment: React.Dispatch<React.SetStateAction<string>>;
    readonly generalSettlementApplyTargets: (string | number)[];
    readonly generalSettlementApplyComment: string;
    readonly setGeneralSettlementApplyTargets: React.Dispatch<React.SetStateAction<(string | number)[]>>;
    readonly setGeneralSettlementApplyComment: React.Dispatch<React.SetStateAction<string>>;
    readonly selectedSettlementCases: () => Fee[];
    readonly setSettlementLogContent: React.Dispatch<React.SetStateAction<string>>;
    readonly setSettlementContext: React.Dispatch<React.SetStateAction<{
        mode: "logs" | "tasks" | "log-create" | "task-create";
        caseRecords: Fee[];
    } | null>>;
    readonly currentUser: {
        username: any;
        displayName: any;
    };
    readonly setSettlementTaskForm: React.Dispatch<React.SetStateAction<{
        title: string;
        owner: string;
        deadline: any;
        priority: string;
    }>>;
    readonly setSettlementActionLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setSettlementContextRows: React.Dispatch<React.SetStateAction<any[]>>;
    readonly settlementLogContent: string;
    readonly settlementContext: {
        mode: "logs" | "tasks" | "log-create" | "task-create";
        caseRecords: Fee[];
    } | null;
    readonly settlementTaskForm: {
        title: string;
        owner: string;
        deadline: any;
        priority: string;
    };
    readonly settlementBatchForm: FormInstance<any>;
    readonly setSettlementBatchOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly load: () => Promise<void>;
}
export function createFinanceSettlementsActions(context: FinanceSettlementsDependencies) {
    const loadGeneralSettlements = async (query: Record<string, any>, page = 1, pageSize = context.generalSettlementMeta.pageSize) => {
        const { generalSettlementMeta, isGeneralSettlementPendingRoute, generalSettlementParams, setGeneralSettlementRows, setGeneralSettlementMeta } = context;
        const response = await api.get(isGeneralSettlementPendingRoute
            ? "/finance/general-settlements/pending"
            : "/finance/general-settlements/applications", {
            params: generalSettlementParams(query, page, pageSize),
        });
        setGeneralSettlementRows(response.data.items || []);
        setGeneralSettlementMeta({
            total: response.data.total || 0,
            page: response.data.page || page,
            pageSize: response.data.page_size || pageSize,
            totals: response.data.totals || {},
        });
    };
    const loadArchiveSettlements = async (query: Record<string, any>, page = 1, pageSize = context.archiveSettlementMeta.pageSize) => {
        const { archiveSettlementMeta, isArchiveSettlementPaymentRoute, isArchiveSettlementPaidRoute, isArchiveSettlementRejectedRoute, archiveSettlementParams, setArchiveSettlementRows, setArchiveSettlementMeta } = context;
        const response = await api.get(isArchiveSettlementPaymentRoute
            ? "/finance/archive-settlements/payment"
            : isArchiveSettlementPaidRoute
                ? "/finance/archive-settlements/paid"
                : isArchiveSettlementRejectedRoute
                    ? "/finance/archive-settlements/rejected"
                    : "/finance/archive-settlements/pending", {
            params: archiveSettlementParams(query, page, pageSize),
        });
        setArchiveSettlementRows(response.data.items || []);
        setArchiveSettlementMeta({
            total: response.data.total || 0,
            page: response.data.page || page,
            pageSize: response.data.page_size || pageSize,
            totals: response.data.totals || {},
        });
    };
    const submitGeneralSettlementReview = async () => {
        const { generalSettlementReviewTargets, financeActionGates, setGeneralSettlementBusy, generalSettlementReviewApproved, generalSettlementReviewComment, setGeneralSettlementReviewTargets, setGeneralSettlementReviewComment, setSelectedOriginalRows, setGeneralSettlementDetails, originalQuery, generalSettlementMeta } = context;
        if (!generalSettlementReviewTargets.length)
            return;
        if (!financeActionGates.generalSettlement.tryEnter()) {
            message.info("操作正在提交，请勿重复点击");
            return;
        }
        setGeneralSettlementBusy(true);
        try {
            const response = await api.post("/finance/general-settlements/applications/review", {
                application_ids: generalSettlementReviewTargets.map((row) => row.id),
                approved: generalSettlementReviewApproved,
                comment: generalSettlementReviewComment,
            });
            message.success(generalSettlementReviewApproved
                ? `已同意 ${response.data.reviewed} 条结算申请`
                : `已拒绝 ${response.data.reviewed} 条结算申请`);
            setGeneralSettlementReviewTargets([]);
            setGeneralSettlementReviewComment("");
            setSelectedOriginalRows([]);
            setGeneralSettlementDetails([]);
            await loadGeneralSettlements(originalQuery, generalSettlementMeta.page, generalSettlementMeta.pageSize);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "结算审核失败");
            throw error;
        }
        finally {
            financeActionGates.generalSettlement.leave();
            setGeneralSettlementBusy(false);
        }
    };
    const submitGeneralSettlementPayment = async () => {
        const { generalSettlementPaymentTargets, generalSettlementPaymentAction, generalSettlementPaymentComment, financeActionGates, setGeneralSettlementBusy, setGeneralSettlementPaymentTargets, setGeneralSettlementPaymentComment, setSelectedOriginalRows, setGeneralSettlementDetails, originalQuery, generalSettlementMeta } = context;
        if (!generalSettlementPaymentTargets.length)
            return;
        if (generalSettlementPaymentAction === "rollback" &&
            !generalSettlementPaymentComment.trim()) {
            message.warning("请输入审核备注.");
            return;
        }
        if (!financeActionGates.generalSettlement.tryEnter()) {
            message.info("操作正在提交，请勿重复点击");
            return;
        }
        setGeneralSettlementBusy(true);
        try {
            const response = await api.post("/finance/general-settlements/applications/payment", {
                application_ids: generalSettlementPaymentTargets.map((row) => row.id),
                action: generalSettlementPaymentAction,
                comment: generalSettlementPaymentComment,
            });
            message.success(generalSettlementPaymentAction === "paid"
                ? `已标记 ${response.data.processed} 条结算为已支付`
                : `已回退 ${response.data.processed} 条结算`);
            setGeneralSettlementPaymentTargets([]);
            setGeneralSettlementPaymentComment("");
            setSelectedOriginalRows([]);
            setGeneralSettlementDetails([]);
            await loadGeneralSettlements(originalQuery, generalSettlementMeta.page, generalSettlementMeta.pageSize);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "结算付款处理失败");
            throw error;
        }
        finally {
            financeActionGates.generalSettlement.leave();
            setGeneralSettlementBusy(false);
        }
    };
    const submitGeneralSettlementReapply = async () => {
        const { generalSettlementReapplyTargets, generalSettlementReapplyComment, financeActionGates, setGeneralSettlementBusy, setGeneralSettlementReapplyTargets, setGeneralSettlementReapplyComment, setSelectedOriginalRows, setGeneralSettlementDetails, originalQuery, generalSettlementMeta } = context;
        if (!generalSettlementReapplyTargets.length)
            return;
        if (!generalSettlementReapplyComment.trim()) {
            message.warning("请输入备注.");
            return;
        }
        if (!financeActionGates.generalSettlement.tryEnter()) {
            message.info("操作正在提交，请勿重复点击");
            return;
        }
        setGeneralSettlementBusy(true);
        try {
            const response = await api.post("/finance/general-settlements/applications/reapply", {
                application_ids: generalSettlementReapplyTargets.map((row) => row.id),
                comment: generalSettlementReapplyComment,
            });
            message.success(`已重新申请 ${response.data.reapplied} 条结算`);
            setGeneralSettlementReapplyTargets([]);
            setGeneralSettlementReapplyComment("");
            setSelectedOriginalRows([]);
            setGeneralSettlementDetails([]);
            await loadGeneralSettlements(originalQuery, generalSettlementMeta.page, generalSettlementMeta.pageSize);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "重新申请结算失败");
            throw error;
        }
        finally {
            financeActionGates.generalSettlement.leave();
            setGeneralSettlementBusy(false);
        }
    };
    const exportGeneralSettlement = async (kind: "settlement" | "receipt" | "case", ids?: (string | number)[]) => {
        const { selectedOriginalRows, isGeneralSettlementPendingRoute, setGeneralSettlementBusy } = context;
        const selectedOnly = ids !== undefined;
        const selectedIds = ids ?? selectedOriginalRows;
        if (!isGeneralSettlementPendingRoute && !selectedOnly) {
            Modal.info({
                title: "提示",
                content: "请选择需要导出的结算申请.",
                okText: "确定",
            });
            return;
        }
        if (selectedOnly && !selectedIds.length) {
            Modal.info({
                title: "提示",
                content: "请选择需要导出的回款.",
                okText: "确定",
            });
            return;
        }
        setGeneralSettlementBusy(true);
        try {
            const response = await api.get("/finance/general-settlements/export", {
                params: selectedOnly
                    ? isGeneralSettlementPendingRoute
                        ? { kind, ids: selectedIds.join(",") }
                        : { kind, application_ids: selectedIds.join(",") }
                    : { kind },
                responseType: "blob",
            });
            const names = {
                settlement: "结算清单",
                receipt: "到账清单",
                case: "案件清单",
            };
            const url = URL.createObjectURL(response.data);
            const anchor = document.createElement("a");
            anchor.href = url;
            anchor.download = `${names[kind]}-${dayjs().format("YYYY-MM-DD")}.xls`;
            anchor.click();
            URL.revokeObjectURL(url);
            message.success("导出成功.");
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "导出失败");
        }
        finally {
            setGeneralSettlementBusy(false);
        }
    };
    const exportPendingArchiveSettlements = async () => {
        const { selectedOriginalRows, isArchiveSettlementRejectedRoute, financeActionGates, setArchiveSettlementBusy, isArchiveSettlementPaidRoute, isArchiveSettlementPaymentRoute } = context;
        if (!selectedOriginalRows.length) {
            Modal.info({
                title: "提示",
                content: isArchiveSettlementRejectedRoute
                    ? "请选择案件."
                    : "请选择需要导出的归档费.",
                okText: "确定",
            });
            return;
        }
        if (!financeActionGates.archiveSettlement.tryEnter()) {
            message.info("操作正在提交，请勿重复点击");
            return;
        }
        setArchiveSettlementBusy(true);
        try {
            const response = await api.get(isArchiveSettlementPaidRoute
                ? "/finance/archive-settlements/paid/export"
                : isArchiveSettlementRejectedRoute
                    ? "/finance/archive-settlements/rejected/export"
                    : isArchiveSettlementPaymentRoute
                        ? "/finance/archive-settlements/payment/export"
                        : "/finance/archive-settlements/export", {
                params: { ids: selectedOriginalRows.join(",") },
                responseType: "blob",
            });
            const url = URL.createObjectURL(response.data);
            const anchor = document.createElement("a");
            anchor.href = url;
            anchor.download = `${isArchiveSettlementPaidRoute
                ? "已支付归档费"
                : isArchiveSettlementRejectedRoute
                    ? "已拒绝归档费"
                    : isArchiveSettlementPaymentRoute
                        ? "待支付归档费"
                        : "待归档"}-${dayjs().format("YYYY-MM-DD")}.xls`;
            anchor.click();
            URL.revokeObjectURL(url);
            message.success("导出成功.");
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "导出失败");
        }
        finally {
            financeActionGates.archiveSettlement.leave();
            setArchiveSettlementBusy(false);
        }
    };
    const submitArchiveSettlementReview = async () => {
        const { archiveSettlementReviewTargets, archiveSettlementReviewApproved, archiveSettlementReviewComment, financeActionGates, setArchiveSettlementBusy, setArchiveSettlementReviewTargets, setArchiveSettlementReviewComment, setSelectedOriginalRows, originalQuery, archiveSettlementMeta } = context;
        if (!archiveSettlementReviewTargets.length)
            return;
        if (!archiveSettlementReviewApproved && !archiveSettlementReviewComment.trim()) {
            message.warning("请输入备注.");
            return;
        }
        if (!financeActionGates.archiveSettlement.tryEnter()) {
            message.info("操作正在提交，请勿重复点击");
            return;
        }
        setArchiveSettlementBusy(true);
        try {
            const response = await api.post("/finance/archive-settlements/payment/review", {
                settlement_ids: archiveSettlementReviewTargets.map((row) => String(row.id)),
                approved: archiveSettlementReviewApproved,
                comment: archiveSettlementReviewComment,
            });
            message.success(archiveSettlementReviewApproved
                ? `同意结算 ${response.data.reviewed} 条归档费`
                : `拒绝结算 ${response.data.reviewed} 条归档费`);
            setArchiveSettlementReviewTargets([]);
            setArchiveSettlementReviewComment("");
            setSelectedOriginalRows([]);
            await loadArchiveSettlements(originalQuery, archiveSettlementMeta.page, archiveSettlementMeta.pageSize);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail ||
                (archiveSettlementReviewApproved
                    ? "标识已结算出错."
                    : "拒绝结算出错."));
        }
        finally {
            financeActionGates.archiveSettlement.leave();
            setArchiveSettlementBusy(false);
        }
    };
    const submitArchiveSettlementRollback = async () => {
        const { archiveSettlementRollbackTargets, archiveSettlementRollbackComment, isArchiveSettlementRejectedRoute, financeActionGates, setArchiveSettlementBusy, setArchiveSettlementRollbackTargets, setArchiveSettlementRollbackComment, setSelectedOriginalRows, originalQuery, archiveSettlementMeta } = context;
        if (!archiveSettlementRollbackTargets.length)
            return;
        if (!archiveSettlementRollbackComment.trim()) {
            message.warning(isArchiveSettlementRejectedRoute ? "请输入审核备注." : "请输入备注.");
            return;
        }
        if (!financeActionGates.archiveSettlement.tryEnter()) {
            message.info("操作正在提交，请勿重复点击");
            return;
        }
        setArchiveSettlementBusy(true);
        try {
            const response = await api.post(isArchiveSettlementRejectedRoute
                ? "/finance/archive-settlements/rejected/rollback"
                : "/finance/archive-settlements/paid/rollback", {
                record_ids: archiveSettlementRollbackTargets.map((row) => Number(row.id)),
                comment: archiveSettlementRollbackComment.trim(),
            });
            message.success(isArchiveSettlementRejectedRoute
                ? `已恢复 ${response.data.rolled_back} 条已拒绝归档费`
                : `已回滚 ${response.data.rolled_back} 条归档费结算`);
            setArchiveSettlementRollbackTargets([]);
            setArchiveSettlementRollbackComment("");
            setSelectedOriginalRows([]);
            await loadArchiveSettlements(originalQuery, archiveSettlementMeta.page, archiveSettlementMeta.pageSize);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "归档费回滚出错.");
        }
        finally {
            financeActionGates.archiveSettlement.leave();
            setArchiveSettlementBusy(false);
        }
    };
    const submitArchiveSettlementReapply = async () => {
        const { archiveSettlementReapplyTargets, financeActionGates, setArchiveSettlementBusy, archiveSettlementReapplyComment, setArchiveSettlementReapplyTargets, setArchiveSettlementReapplyComment, setSelectedOriginalRows, originalQuery, archiveSettlementMeta } = context;
        if (!archiveSettlementReapplyTargets.length)
            return;
        if (!financeActionGates.archiveSettlement.tryEnter()) {
            message.info("操作正在提交，请勿重复点击");
            return;
        }
        setArchiveSettlementBusy(true);
        try {
            const response = await api.post("/finance/archive-settlements/rejected/reapply", {
                record_ids: archiveSettlementReapplyTargets.map((row) => Number(row.id)),
                comment: archiveSettlementReapplyComment.trim(),
            });
            message.success(`已重新申请 ${response.data.reapplied} 条归档费`);
            setArchiveSettlementReapplyTargets([]);
            setArchiveSettlementReapplyComment("");
            setSelectedOriginalRows([]);
            await loadArchiveSettlements(originalQuery, archiveSettlementMeta.page, archiveSettlementMeta.pageSize);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "归档费重新申请失败");
        }
        finally {
            financeActionGates.archiveSettlement.leave();
            setArchiveSettlementBusy(false);
        }
    };
    const submitGeneralSettlementApply = async () => {
        const { generalSettlementApplyTargets, setGeneralSettlementBusy, generalSettlementApplyComment, setGeneralSettlementApplyTargets, setGeneralSettlementApplyComment, setSelectedOriginalRows, setGeneralSettlementDetails, originalQuery, generalSettlementMeta } = context;
        if (!generalSettlementApplyTargets.length)
            return;
        setGeneralSettlementBusy(true);
        try {
            const response = await api.post("/finance/general-settlements/apply", {
                receipt_ids: generalSettlementApplyTargets.map(Number),
                comment: generalSettlementApplyComment,
            });
            message.success(`已生成 ${response.data.created} 条结算申请`);
            setGeneralSettlementApplyTargets([]);
            setGeneralSettlementApplyComment("");
            setSelectedOriginalRows([]);
            setGeneralSettlementDetails([]);
            await loadGeneralSettlements(originalQuery, 1, generalSettlementMeta.pageSize);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "申请结算失败");
            throw error;
        }
        finally {
            setGeneralSettlementBusy(false);
        }
    };
    const loadSettlementContextTasks = async (caseId: number) => {
        const firstRequest = settlementContextTasksRequest(caseId, 1);
        const firstResponse = await api.get(firstRequest.url, {
            params: firstRequest.params,
        });
        const firstRows = normalizeSettlementContextRows(firstResponse.data);
        const total = Number(firstResponse.data?.total || firstRows.length);
        const totalPages = Math.max(1, Math.ceil(total / settlementContextPageSize));
        if (totalPages === 1)
            return firstRows;
        const restResponses = await Promise.all(Array.from({ length: totalPages - 1 }, (_value, index) => {
            const request = settlementContextTasksRequest(caseId, index + 2);
            return api.get(request.url, { params: request.params });
        }));
        return [
            ...firstRows,
            ...restResponses.flatMap((response) => normalizeSettlementContextRows(response.data)),
        ];
    };
    const openSettlementContext = async (mode: "tasks" | "logs" | "log-create" | "task-create") => {
        const { selectedSettlementCases, setSettlementLogContent, setSettlementContext, currentUser, setSettlementTaskForm, setSettlementActionLoading, setSettlementContextRows } = context;
        const linked = selectedSettlementCases();
        if (!linked.length)
            return;
        if (mode === "log-create") {
            setSettlementLogContent("");
            setSettlementContext({ mode, caseRecords: linked });
            return;
        }
        if (mode === "task-create") {
            const firstAssistant = linked[0]?.data?.assistant || currentUser.username;
            setSettlementTaskForm({
                title: "",
                owner: firstAssistant,
                deadline: dayjs().add(15, "day"),
                priority: "普通",
            });
            setSettlementContext({ mode, caseRecords: linked });
            return;
        }
        setSettlementActionLoading(true);
        try {
            if (mode === "tasks") {
                const groups = await Promise.all(linked.map(async (item) => (await loadSettlementContextTasks(item.id)).map((row: any) => ({ ...row, source_case_no: item.serial_no }))));
                setSettlementContextRows(groups.flat());
            }
            else {
                const groups = await Promise.all(linked.map(async (item) => {
                    const { data } = await api.get(`/cases/${item.id}/logs`);
                    return (data.items || []).map((row: any) => ({ ...row, source_case_no: item.serial_no }));
                }));
                setSettlementContextRows(groups.flat());
            }
            setSettlementContext({ mode, caseRecords: linked });
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "案件信息加载失败");
        }
        finally {
            setSettlementActionLoading(false);
        }
    };
    const submitSettlementLog = async () => {
        const { settlementLogContent, settlementContext, setSettlementActionLoading, setSettlementContext } = context;
        const content = settlementLogContent.trim();
        if (!content) {
            message.warning("请输入日志内容");
            return;
        }
        const linked = settlementContext?.caseRecords || [];
        setSettlementActionLoading(true);
        try {
            await Promise.all(linked.map((item) => api.post(`/cases/${item.id}/logs`, { content })));
            message.success(`已为 ${linked.length} 个案件添加日志`);
            setSettlementContext(null);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "日志添加失败");
        }
        finally {
            setSettlementActionLoading(false);
        }
    };
    const submitSettlementTask = async () => {
        const { settlementTaskForm, settlementContext, setSettlementActionLoading, setSettlementContext } = context;
        const form = settlementTaskForm;
        if (!form.title.trim()) {
            message.warning("请输入任务名称");
            return;
        }
        if (!form.owner.trim()) {
            message.warning("请选择负责人");
            return;
        }
        if (!form.deadline) {
            message.warning("请选择截止日期");
            return;
        }
        const linked = settlementContext?.caseRecords || [];
        setSettlementActionLoading(true);
        try {
            await Promise.all(linked.map((item) => api.post("/tasks", {
                title: form.title.trim(),
                owner: form.owner.trim(),
                deadline: form.deadline.format("YYYY-MM-DD"),
                priority: form.priority,
                source: "案件任务",
                case_record_id: item.id,
                case_module: "case",
            })));
            message.success(`已为 ${linked.length} 个案件创建任务`);
            setSettlementContext(null);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "任务创建失败");
        }
        finally {
            setSettlementActionLoading(false);
        }
    };
    const generateSettlementDocument = async (key: "authorization" | "law-firm-letter" | "identity" | "settlement") => {
        const { selectedSettlementCases, setSettlementActionLoading } = context;
        const linked = selectedSettlementCases();
        if (!linked.length)
            return;
        const nameMap: Record<string, string> = {
            authorization: "授权委托书",
            "law-firm-letter": "律所函",
            identity: "身份证明",
            settlement: "结算提成表",
        };
        setSettlementActionLoading(true);
        try {
            for (const caseRecord of linked) {
                const response = await api.get(`/cases/${caseRecord.id}/documents/generate`, { params: { doc_type: key }, responseType: "blob" });
                const url = URL.createObjectURL(response.data);
                const anchor = document.createElement("a");
                anchor.href = url;
                const cd = response.headers["content-disposition"];
                const match = cd && cd.match(/filename\*=UTF-8''([^;]+)/);
                anchor.download = match ? decodeURIComponent(match[1]) : `${nameMap[key]}-${caseRecord.serial_no}.docx`;
                anchor.click();
                URL.revokeObjectURL(url);
            }
            message.success(`${nameMap[key]}已为 ${linked.length} 个案件生成并下载`);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "文书生成失败");
        }
        finally {
            setSettlementActionLoading(false);
        }
    };
    const submitSettlementBatch = async () => {
        const { selectedSettlementCases, settlementBatchForm, setSettlementActionLoading, setSettlementBatchOpen, setSelectedOriginalRows, load } = context;
        const linked = selectedSettlementCases();
        if (!linked.length)
            return;
        const values = await settlementBatchForm.validateFields();
        const body: Record<string, any> = {
            case_ids: linked.map((row) => row.id),
            comment: values.comment || "待结算列表批量修改",
        };
        if (values.hearing_lawyer?.trim())
            body.hearing_lawyer = values.hearing_lawyer.trim();
        if (values.handling_lawyers?.trim()) {
            body.handling_lawyers = values.handling_lawyers
                .split(/[，,]/)
                .map((item: string) => item.trim())
                .filter(Boolean);
        }
        if (values.assistant?.trim())
            body.assistant = values.assistant.trim();
        if (values.source_lawyer?.trim())
            body.source_lawyer = values.source_lawyer.trim();
        if (values.case_stage)
            body.case_stage = values.case_stage;
        if (values.litigation_amount != null)
            body.litigation_amount = values.litigation_amount;
        if (Object.keys(body).length <= 2) {
            message.warning("请至少修改一个字段");
            return;
        }
        setSettlementActionLoading(true);
        try {
            const { data } = await api.post("/cases/batch-update", body);
            message.success(`已修改 ${data.updated} 个案件`);
            setSettlementBatchOpen(false);
            setSelectedOriginalRows([]);
            await load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "批量修改失败");
        }
        finally {
            setSettlementActionLoading(false);
        }
    };
    return { loadGeneralSettlements, loadArchiveSettlements, submitGeneralSettlementReview, submitGeneralSettlementPayment, submitGeneralSettlementReapply, exportGeneralSettlement, exportPendingArchiveSettlements, submitArchiveSettlementReview, submitArchiveSettlementRollback, submitArchiveSettlementReapply, submitGeneralSettlementApply, loadSettlementContextTasks, openSettlementContext, submitSettlementLog, submitSettlementTask, generateSettlementDocument, submitSettlementBatch };
}
