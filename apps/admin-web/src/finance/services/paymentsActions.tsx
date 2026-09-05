import { message, Modal } from "antd";
import type { FormInstance } from "antd/es/form/hooks/useForm";
import dayjs from "dayjs";
import { api } from "../../api";
import type { FinanceActionGate } from "../../financeActionGate.mjs";
import { formatRequiredDate } from "../../formSafety";
import { contractPaymentQueryRequestParams, createPaymentPrintPreview, normalizePaymentPackageResponse, paymentPackageEmptySelectionMessage, paymentPackageRequestParams, paymentPackageWordExportPath, paymentPackageWriteoffPayload, paymentQueryRequestParams, paymentQueryServerPagePlan } from "../constants";
import type { Fee, PaymentPackagePreview, PaymentPrintDocumentData, Transaction } from "../types";
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
/** finance payments operations; dependencies are read when each operation runs. */
export interface FinancePaymentsDependencies {
    readonly setFeeDetail: React.Dispatch<React.SetStateAction<Fee | null>>;
    readonly feeQueryMeta: {
        total: number;
        page: number;
        pageSize: number;
        totals: Record<string, number | null>;
    };
    readonly isRefundCaseFeeRoute: boolean;
    readonly feeQueryParams: (query: Record<string, any>, page?: number, pageSize?: number) => {
        case_no: any;
        court_case_no: any;
        court_name: any;
        paid_from: any;
        paid_to: any;
        customer: any;
        paid_organization: any;
        refund_status: any;
        refund_amount_from: any;
        refund_amount_to: any;
        hearing_lawyer: any;
        assistant: any;
        case_stages: string;
        fee_types: string;
        page: number;
        page_size: number;
        scope?: undefined;
        unpaid_official?: undefined;
        notary_no?: undefined;
        payment_status?: undefined;
    } | {
        scope: any;
        unpaid_official: any;
        case_no: any;
        court_case_no: any;
        notary_no: any;
        refund_amount_from: any;
        refund_amount_to: any;
        customer: any;
        paid_organization: any;
        payment_status: any;
        paid_from: any;
        paid_to: any;
        hearing_lawyer: any;
        assistant: any;
        case_stages: string;
        fee_types: string;
        page: number;
        page_size: number;
        court_name?: undefined;
        refund_status?: undefined;
    };
    readonly setFeeQueryRows: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setFeeQueryMeta: React.Dispatch<React.SetStateAction<{
        total: number;
        page: number;
        pageSize: number;
        totals: Record<string, number | null>;
    }>>;
    readonly paymentQueryPageSize: number;
    readonly paymentPackageMeta: {
        total: number;
        page: number;
        pageSize: number;
    };
    readonly initialView: string;
    readonly setPaymentPackages: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setPaymentPackageMeta: React.Dispatch<React.SetStateAction<{
        total: number;
        page: number;
        pageSize: number;
    }>>;
    readonly feeForm: FormInstance<any>;
    readonly feeEditTarget: Fee | null;
    readonly closeFeeModal: () => void;
    readonly load: () => Promise<void>;
    readonly financeFeeRefreshGuard: {
        begin: () => number;
        isLatest: (token: number) => boolean;
    };
    readonly setFees: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setFinanceFeeListMeta: React.Dispatch<React.SetStateAction<{
        page: number;
        pageSize: number;
        total: number;
    }>>;
    readonly paymentCancelTarget: Fee | null;
    readonly paymentCancelReason: string;
    readonly setPaymentCancelTarget: React.Dispatch<React.SetStateAction<Fee | null>>;
    readonly setPaymentCancelReason: React.Dispatch<React.SetStateAction<string>>;
    readonly financeFeeListMeta: {
        page: number;
        pageSize: number;
        total: number;
    };
    readonly originalQuery: Record<string, any>;
    readonly paymentRollbackTarget: Fee | null;
    readonly paymentRollbackComment: string;
    readonly setPaymentRollbackTarget: React.Dispatch<React.SetStateAction<Fee | null>>;
    readonly setPaymentRollbackComment: React.Dispatch<React.SetStateAction<string>>;
    readonly writeoffTarget: Fee | null;
    readonly writeoffForm: FormInstance<any>;
    readonly contractPayments: Fee[];
    readonly setWriteoffTarget: React.Dispatch<React.SetStateAction<Fee | null>>;
    readonly paymentStatus: (fee: Fee) => any;
    readonly feeDetail: Fee | null;
    readonly paymentPackageWriteoffTarget: Fee | null;
    readonly paymentPackageWriteoffForm: FormInstance<any>;
    readonly financeActionGates: {
        archiveSettlement: FinanceActionGate;
        generalSettlement: FinanceActionGate;
        paymentPackage: FinanceActionGate;
    };
    readonly setPaymentPackageLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setPaymentPackageWriteoffTarget: React.Dispatch<React.SetStateAction<Fee | null>>;
    readonly paymentPrintPreview: PaymentPrintDocumentData | null;
    readonly setPaymentWordExportLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly transactions: Transaction[];
    readonly currentUser: {
        username: any;
        displayName: any;
    };
    readonly setPaymentPrintPreview: React.Dispatch<React.SetStateAction<PaymentPrintDocumentData | null>>;
    readonly feeReviewTargets: Fee[];
    readonly setFeeReviewLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly feeReviewComment: string;
    readonly setFeeReviewTargets: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setFeeReviewComment: React.Dispatch<React.SetStateAction<string>>;
    readonly setSelectedOriginalRows: React.Dispatch<React.SetStateAction<(string | number)[]>>;
    readonly configuredRows: any[];
    readonly selectedOriginalRows: (string | number)[];
    readonly setPaymentPackagePreview: React.Dispatch<React.SetStateAction<PaymentPackagePreview | null>>;
    readonly paymentPackagePreview: PaymentPackagePreview | null;
    readonly setPaymentPackageDetail: React.Dispatch<React.SetStateAction<Fee | null>>;
    readonly paymentPackageSelectedFeeIds: number[];
    readonly paymentPackageEditForm: FormInstance<any>;
    readonly paymentPackageEditTarget: Fee | null;
    readonly setPaymentPackageEditTarget: React.Dispatch<React.SetStateAction<Fee | null>>;
    readonly setPaymentPackageEditorOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setPaymentPackageSelectedFeeIds: React.Dispatch<React.SetStateAction<number[]>>;
    readonly setFeeQueryExportLoading: React.Dispatch<React.SetStateAction<boolean>>;
}
export function createFinancePaymentsActions(context: FinancePaymentsDependencies) {
    const openPaymentDetail = async (row: Fee) => {
        const { setFeeDetail } = context;
        try {
            const { data } = await api.get(`/records/${row.id}`);
            if (!data || !["finance", "contract_payment"].includes(data.module)) {
                throw new Error("请款单详情记录无效");
            }
            const packageNo = String(data.data?.payment_package_no || data.data?.package_no || "").trim();
            let detail = data;
            if (packageNo) {
                try {
                    const packageResponse = await api.get("/records", {
                        params: { module: "finance_package", keyword: packageNo },
                    });
                    const paymentPackage = (packageResponse.data?.items || []).find((item: Fee) => item.module === "finance_package" &&
                        (String(item.serial_no || "").trim() === packageNo ||
                            String(item.data?.package_no || "").trim() === packageNo ||
                            String(item.data?.payment_package_no || "").trim() === packageNo));
                    if (paymentPackage) {
                        detail = {
                            ...data,
                            data: {
                                ...data.data,
                                package_no: data.data?.package_no || packageNo,
                                payment_package_no: data.data?.payment_package_no || packageNo,
                                payment_package_context: paymentPackage,
                            },
                        };
                    }
                }
                catch {
                    detail = {
                        ...data,
                        data: {
                            ...data.data,
                            package_no: data.data?.package_no || packageNo,
                            payment_package_no: data.data?.payment_package_no || packageNo,
                        },
                    };
                }
            }
            setFeeDetail(detail);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail ||
                error?.message ||
                "请款单详情加载失败");
        }
    };
    const loadFeeQuery = async (query: Record<string, any>, page = 1, pageSize = context.feeQueryMeta.pageSize) => {
        const { feeQueryMeta, isRefundCaseFeeRoute, feeQueryParams, setFeeQueryRows, setFeeQueryMeta } = context;
        const response = await api.get(isRefundCaseFeeRoute
            ? "/finance/case-fees/refunds"
            : "/finance/fees/query", {
            params: feeQueryParams(query, page, pageSize),
        });
        setFeeQueryRows(response.data.items || []);
        setFeeQueryMeta({
            total: response.data.total || 0,
            page: response.data.page || page,
            pageSize: response.data.page_size || pageSize,
            totals: response.data.totals || {},
        });
    };
    const loadPaymentQueryPage = async (query: Record<string, any>, page = 1, pageSize = context.paymentQueryPageSize) => {
        const { paymentQueryPageSize } = context;
        const requests = paymentQueryServerPagePlan(page, pageSize);
        const responses = await Promise.all(requests.flatMap((request) => [
            api.get("/records", {
                params: paymentQueryRequestParams(query, request.page, request.pageSize),
            }),
            api.get("/records", {
                params: contractPaymentQueryRequestParams(query, request.page, request.pageSize),
            }),
        ]));
        const seen = new Set<string>();
        const mergedItems = responses
            .flatMap((response) => response.data?.items || [])
            .filter((item: Fee) => {
            const key = String(item.module || item.data?._source_module || "finance") + ":" + String(item.id);
            if (seen.has(key))
                return false;
            seen.add(key);
            return true;
        });
        return {
            data: {
                items: mergedItems.slice(0, pageSize),
                total: responses.reduce((sum, response) => sum + Number(response.data?.total || 0), 0),
                page,
                page_size: pageSize,
            },
        };
    };
    const loadPaymentPackages = async (query: Record<string, any>, page = 1, pageSize = context.paymentPackageMeta.pageSize) => {
        const { paymentPackageMeta, initialView, setPaymentPackages, setPaymentPackageMeta } = context;
        const response = await api.get("/finance/payment-packages", {
            params: paymentPackageRequestParams(initialView, query, page, pageSize),
        });
        const normalized = normalizePaymentPackageResponse(response.data, page, pageSize);
        setPaymentPackages(normalized.items);
        setPaymentPackageMeta(normalized);
        return response;
    };
    const createFee = async () => {
        const { feeForm, feeEditTarget, closeFeeModal, load } = context;
        const v = await feeForm.validateFields();
        try {
            feeEditTarget
                ? await api.put(`/finance/fees/${feeEditTarget.id}`, v)
                : await api.post("/finance/fees", v);
            message.success(feeEditTarget ? "费用已更新" : "费用已创建");
            closeFeeModal();
            load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "创建失败");
        }
    };
    const feeAction = async (row: Fee, type: "submit" | "approve") => {
        const { load } = context;
        try {
            if (type === "submit" && row.data.fee_type === "官方费用") {
                const { data } = await api.get(`/finance/fees/${row.id}/readiness`);
                if (!data.ready) {
                    Modal.warning({
                        title: "案件付款三要素不完整",
                        content: (<div>
                {data.missing.map((item: string) => (<div key={item}>• {item}</div>))}
              </div>),
                    });
                    return;
                }
            }
            await api.post(`/finance/fees/${row.id}/${type}`, {
                comment: type === "submit" ? "提交财务审批" : "审批通过",
            });
            message.success(type === "submit" ? "已提交审批" : "费用已审批");
            load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "操作失败");
        }
    };
    const refreshCurrentFinanceFeeList = async ({ page, pageSize, status, query, }: {
        page: number;
        pageSize: number;
        status: string;
        query: Record<string, any>;
    }) => {
        const { financeFeeRefreshGuard, setFees, setFinanceFeeListMeta } = context;
        const token = financeFeeRefreshGuard.begin();
        try {
            const response = await api.get("/records", {
                params: {
                    module: "finance",
                    page: Math.max(1, page),
                    page_size: Math.min(100, Math.max(1, pageSize)),
                    keyword: String(query?.keyword || query?.paymentNo || "").trim(),
                    record_status: status && status !== "全部" ? status : undefined,
                },
            });
            if (!financeFeeRefreshGuard.isLatest(token))
                return false;
            setFees(Array.isArray(response.data?.items) ? response.data.items : []);
            setFinanceFeeListMeta({
                page: Number(response.data?.page || page),
                pageSize: Number(response.data?.page_size || pageSize),
                total: Number(response.data?.total || 0),
            });
            return true;
        }
        catch (error: any) {
            if (financeFeeRefreshGuard.isLatest(token)) {
                message.error(error?.response?.data?.detail || "财务费用刷新失败");
            }
            return false;
        }
    };
    const submitPaymentCancel = async () => {
        const { paymentCancelTarget, paymentCancelReason, setPaymentCancelTarget, setPaymentCancelReason, financeFeeListMeta, originalQuery } = context;
        if (!paymentCancelTarget)
            return;
        const reason = paymentCancelReason.trim();
        if (!reason) {
            message.warning("请输入撤回原因.");
            return;
        }
        try {
            await api.post(`/finance/fees/${paymentCancelTarget.id}/cancel`, {
                reason,
            });
            message.success("撤销成功！");
            setPaymentCancelTarget(null);
            setPaymentCancelReason("");
            await refreshCurrentFinanceFeeList({
                page: financeFeeListMeta.page,
                pageSize: financeFeeListMeta.pageSize,
                status: paymentCancelTarget.status,
                query: originalQuery,
            });
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "撤销失败！");
        }
    };
    const submitPaymentRollback = async () => {
        const { paymentRollbackTarget, paymentRollbackComment, setPaymentRollbackTarget, setPaymentRollbackComment, financeFeeListMeta, originalQuery } = context;
        if (!paymentRollbackTarget)
            return;
        try {
            await api.post(`/finance/fees/${paymentRollbackTarget.id}/rollback`, {
                comment: paymentRollbackComment.trim(),
            });
            message.success("回滚成功！");
            setPaymentRollbackTarget(null);
            setPaymentRollbackComment("");
            await refreshCurrentFinanceFeeList({
                page: financeFeeListMeta.page,
                pageSize: financeFeeListMeta.pageSize,
                status: paymentRollbackTarget.status,
                query: originalQuery,
            });
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "回滚失败！");
        }
    };
    const writeoffFee = async () => {
        const { writeoffTarget, writeoffForm, contractPayments, setWriteoffTarget, financeFeeListMeta, paymentStatus, originalQuery, feeDetail } = context;
        if (!writeoffTarget)
            return;
        const values = await writeoffForm.validateFields();
        const target = writeoffTarget;
        try {
            const contractPayment = contractPayments.find((item) => item.id === target.id);
            if (contractPayment) {
                await api.post(`/contract-payment-applications/${contractPayment.id}/writeoff`, {
                    writeoff_date: formatRequiredDate(values.writeoff_date || dayjs(), "核销日期"),
                    voucher_no: values.voucher_no,
                    comment: values.comment || "",
                });
                message.success("合同付款已核销");
                setWriteoffTarget(null);
                writeoffForm.resetFields();
                await refreshCurrentFinanceFeeList({
                    page: financeFeeListMeta.page,
                    pageSize: financeFeeListMeta.pageSize,
                    status: paymentStatus(target),
                    query: originalQuery,
                });
                if (feeDetail?.id === target.id) {
                    await openPaymentDetail(target);
                }
                return;
            }
            await api.post(`/finance/fees/${writeoffTarget.id}/writeoff`, values);
            message.success("付款已核销并留痕");
            setWriteoffTarget(null);
            writeoffForm.resetFields();
            await refreshCurrentFinanceFeeList({
                page: financeFeeListMeta.page,
                pageSize: financeFeeListMeta.pageSize,
                status: paymentStatus(target),
                query: originalQuery,
            });
            if (feeDetail?.id === target.id) {
                await openPaymentDetail(target);
            }
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "付款核销失败");
        }
    };
    const writeoffPaymentPackage = async () => {
        const { paymentPackageWriteoffTarget, paymentPackageWriteoffForm, financeActionGates, setPaymentPackageLoading, setPaymentPackageWriteoffTarget, load } = context;
        if (!paymentPackageWriteoffTarget)
            return;
        const values = await paymentPackageWriteoffForm.validateFields();
        if (!financeActionGates.paymentPackage.tryEnter()) {
            message.info("操作正在提交，请勿重复点击");
            return;
        }
        setPaymentPackageLoading(true);
        try {
            await api.post(`/finance/payment-packages/${paymentPackageWriteoffTarget.id}/writeoff`, paymentPackageWriteoffPayload(values, (value) => formatRequiredDate(value, "付款日期")));
            message.success("核销成功.");
            setPaymentPackageWriteoffTarget(null);
            paymentPackageWriteoffForm.resetFields();
            await load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "付款包核销失败");
        }
        finally {
            financeActionGates.paymentPackage.leave();
            setPaymentPackageLoading(false);
        }
    };
    const downloadPaymentPrintWord = async (packageNoOverride?: string) => {
        const { paymentPrintPreview, setPaymentWordExportLoading } = context;
        if (!paymentPrintPreview && !packageNoOverride)
            return;
        const packageNo = String(packageNoOverride || paymentPrintPreview?.packageNo || "").trim();
        if (!packageNo) {
            message.warning("付款包号不能为空，不能导出 Word");
            return;
        }
        setPaymentWordExportLoading(true);
        try {
            const response = await api.get(paymentPackageWordExportPath(packageNo), { params: { scope: "internal_fee" }, responseType: "blob" });
            const disposition = response.headers?.["content-disposition"] ||
                response.headers?.["Content-Disposition"] ||
                "";
            const filenameMatch = /filename\*=UTF-8''([^;]+)/i.exec(disposition) ||
                /filename="?([^";]+)"?/i.exec(disposition);
            let filename = packageNo + "-付款申请单.docx";
            if (filenameMatch?.[1]) {
                try {
                    filename = decodeURIComponent(filenameMatch[1]);
                }
                catch {
                    filename = filenameMatch[1];
                }
            }
            const url = URL.createObjectURL(response.data);
            const anchor = document.createElement("a");
            anchor.href = url;
            anchor.download = filename;
            anchor.click();
            URL.revokeObjectURL(url);
            message.success("付款单 Word 已下载");
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "付款单 Word 下载失败");
        }
        finally {
            setPaymentWordExportLoading(false);
        }
    };
    const printPayment = async (row: Fee) => {
        const { transactions, currentUser, setPaymentPrintPreview } = context;
        let printRow = row;
        const packageNo = String(row.data.payment_package_no || row.data.package_no || "").trim();
        if (packageNo) {
            try {
                const { data } = await api.get("/records", {
                    params: { module: "finance_package", keyword: packageNo },
                });
                const paymentPackage = (data?.items || []).find((item: Fee) => item.module === "finance_package" &&
                    (String(item.serial_no || "").trim() === packageNo ||
                        String(item.data?.package_no || "").trim() === packageNo ||
                        String(item.data?.payment_package_no || "").trim() === packageNo));
                if (!paymentPackage) {
                    message.warning("未找到付款包或当前账号无权查看");
                    return;
                }
                printRow = {
                    ...row,
                    data: {
                        ...row.data,
                        package_no: row.data.package_no || packageNo,
                        payment_package_no: row.data.payment_package_no || packageNo,
                        payment_package_context: paymentPackage,
                    },
                };
            }
            catch (error: any) {
                message.error(error?.response?.data?.detail || "付款包详情加载失败");
                return;
            }
        }
        const preview = createPaymentPrintPreview(printRow, transactions, currentUser.displayName || "姓名待维护", dayjs().format("YYYY-MM-DD HH:mm"));
        if (!preview) {
            message.warning("该请款单尚无付款流水，不能打印付款单");
            return;
        }
        setPaymentPrintPreview(preview);
    };
    const submitFeeReview = async (approved: boolean) => {
        const { feeReviewTargets, setFeeReviewLoading, feeReviewComment, setFeeReviewTargets, setFeeReviewComment, setSelectedOriginalRows, load } = context;
        if (!feeReviewTargets.length)
            return;
        setFeeReviewLoading(true);
        try {
            if (feeReviewTargets.every((item) => item.data?._source_module === "contract_payment")) {
                for (const target of feeReviewTargets) {
                    await api.post(`/contract-payment-applications/${target.id}/review`, {
                        approved,
                        comment: feeReviewComment,
                    });
                }
            }
            else if (feeReviewTargets.length === 1) {
                await api.post(`/finance/fees/${feeReviewTargets[0].id}/review`, {
                    approved,
                    comment: feeReviewComment,
                });
            }
            else {
                await api.post("/finance/fees/batch-review", {
                    fee_ids: feeReviewTargets.map((item) => item.id),
                    approved,
                    comment: feeReviewComment,
                });
            }
            message.success(approved ? "审批已通过" : "申请已拒绝");
            setFeeReviewTargets([]);
            setFeeReviewComment("");
            setSelectedOriginalRows([]);
            await load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "审批失败");
        }
        finally {
            setFeeReviewLoading(false);
        }
    };
    const previewInternalPaymentPackage = async () => {
        const { configuredRows, selectedOriginalRows, initialView, financeActionGates, setPaymentPackageLoading, setPaymentPackagePreview } = context;
        const targets = configuredRows.filter((row) => selectedOriginalRows.includes(row.id));
        if (!targets.length) {
            Modal.info({
                title: "提示",
                content: paymentPackageEmptySelectionMessage(initialView),
                okText: "确定",
            });
            return;
        }
        const payees = new Set(targets.map((row) => String(row.data?.payee || row.data?.applicant || row.owner || "").trim()));
        if (payees.size !== 1 || payees.has("")) {
            Modal.warning({
                title: "提示",
                content: "请选择同一收款人的提成进行打包付款.",
                okText: "确定",
            });
            return;
        }
        if (!financeActionGates.paymentPackage.tryEnter()) {
            message.info("操作正在提交，请勿重复点击");
            return;
        }
        setPaymentPackageLoading(true);
        try {
            const { data } = await api.post("/finance/payment-packages/preview", {
                fee_ids: targets.map((row) => row.id),
            });
            setPaymentPackagePreview(data);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "付款包预览生成失败");
        }
        finally {
            financeActionGates.paymentPackage.leave();
            setPaymentPackageLoading(false);
        }
    };
    const submitInternalPaymentPackage = async () => {
        const { paymentPackagePreview, financeActionGates, setPaymentPackageLoading, setPaymentPackagePreview, setSelectedOriginalRows, load } = context;
        if (!paymentPackagePreview || paymentPackagePreview.submitted)
            return;
        if (!financeActionGates.paymentPackage.tryEnter()) {
            message.info("操作正在提交，请勿重复点击");
            return;
        }
        setPaymentPackageLoading(true);
        try {
            await api.post("/finance/payment-packages", {
                fee_ids: paymentPackagePreview.items.map((item) => item.fee_id),
                package_no: paymentPackagePreview.package_no,
                comment: "待付款列表打包付款",
            });
            setPaymentPackagePreview({ ...paymentPackagePreview, submitted: true });
            setSelectedOriginalRows([]);
            message.success("付款包已提交，正在打开打印");
            await load();
            window.setTimeout(() => window.print(), 50);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "付款包提交失败");
        }
        finally {
            financeActionGates.paymentPackage.leave();
            setPaymentPackageLoading(false);
        }
    };
    const openPaymentPackageDetail = async (row: Fee) => {
        const { setPaymentPackageDetail } = context;
        try {
            const { data } = await api.get(`/finance/payment-packages/${row.id}`);
            setPaymentPackageDetail(data);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "付款包详情加载失败");
        }
    };
    const submitPaymentPackageEditor = async () => {
        const { paymentPackageSelectedFeeIds, paymentPackageEditForm, financeActionGates, setPaymentPackageLoading, paymentPackageEditTarget, setPaymentPackageEditTarget, setPaymentPackageEditorOpen, setPaymentPackageSelectedFeeIds, originalQuery, paymentPackageMeta } = context;
        if (!paymentPackageSelectedFeeIds.length) {
            message.warning("请至少选择一笔内部费用");
            return;
        }
        const values = await paymentPackageEditForm.validateFields();
        if (!financeActionGates.paymentPackage.tryEnter()) {
            message.info("操作正在提交，请勿重复点击");
            return;
        }
        setPaymentPackageLoading(true);
        try {
            const isEditingPaymentPackage = Boolean(paymentPackageEditTarget);
            if (isEditingPaymentPackage) {
                await api.put(`/finance/payment-packages/${paymentPackageEditTarget!.id}`, {
                    fee_ids: paymentPackageSelectedFeeIds,
                    comment: values.comment || "",
                });
                message.success("付款包已更新");
            }
            else {
                const { data: preview } = await api.post("/finance/payment-packages/preview", {
                    fee_ids: paymentPackageSelectedFeeIds,
                });
                await api.post("/finance/payment-packages", {
                    fee_ids: paymentPackageSelectedFeeIds,
                    package_no: preview.package_no,
                    comment: values.comment || "",
                });
                message.success("付款包已新增");
            }
            setPaymentPackageEditTarget(null);
            setPaymentPackageEditorOpen(false);
            setPaymentPackageSelectedFeeIds([]);
            paymentPackageEditForm.resetFields();
            await loadPaymentPackages(originalQuery, isEditingPaymentPackage ? paymentPackageMeta.page : 1, paymentPackageMeta.pageSize);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "付款包保存失败");
        }
        finally {
            financeActionGates.paymentPackage.leave();
            setPaymentPackageLoading(false);
        }
    };
    const exportFeeQuery = async (selectedOnly: boolean) => {
        const { selectedOriginalRows, setFeeQueryExportLoading, isRefundCaseFeeRoute, feeQueryParams, originalQuery, feeQueryMeta } = context;
        if (selectedOnly && !selectedOriginalRows.length) {
            Modal.info({
                title: "提示",
                content: "请选择需要导出的费用.",
                okText: "确定",
            });
            return;
        }
        setFeeQueryExportLoading(true);
        try {
            const response = await api.get(isRefundCaseFeeRoute
                ? "/finance/case-fees/refunds/export"
                : "/finance/fees/query/export", {
                params: {
                    ...feeQueryParams(originalQuery, 1, feeQueryMeta.pageSize),
                    page: undefined,
                    page_size: undefined,
                    selected_only: selectedOnly,
                    ids: selectedOnly ? selectedOriginalRows.join(",") : undefined,
                },
                responseType: "blob",
            });
            const url = URL.createObjectURL(response.data);
            const anchor = document.createElement("a");
            anchor.href = url;
            anchor.download = `${isRefundCaseFeeRoute ? "退费查询" : "费用查询"}-${dayjs().format("YYYY-MM-DD")}.xls`;
            anchor.click();
            URL.revokeObjectURL(url);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail ||
                (isRefundCaseFeeRoute ? "退费查询导出失败" : "费用查询导出失败"));
        }
        finally {
            setFeeQueryExportLoading(false);
        }
    };
    return { openPaymentDetail, loadFeeQuery, loadPaymentQueryPage, loadPaymentPackages, createFee, feeAction, refreshCurrentFinanceFeeList, submitPaymentCancel, submitPaymentRollback, writeoffFee, writeoffPaymentPackage, downloadPaymentPrintWord, printPayment, submitFeeReview, previewInternalPaymentPackage, submitInternalPaymentPackage, openPaymentPackageDetail, submitPaymentPackageEditor, exportFeeQuery };
}
