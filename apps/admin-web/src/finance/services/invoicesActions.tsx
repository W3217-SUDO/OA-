import { message, Modal } from "antd";
import type { FormInstance } from "antd/es/form/hooks/useForm";
import dayjs from "dayjs";
import { api } from "../../api";
import { buildInvoiceApplicationPayload } from "../../financeInvoiceHelpers.mjs";
import { formatRequiredDate } from "../../formSafety";
import { legacyInvoiceUpdateFailureMessage } from "../constants";
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
/** finance invoices operations; dependencies are read when each operation runs. */
export interface FinanceInvoicesDependencies {
    readonly invoiceDetailRequestGuard: {
        begin: () => number;
        isLatest: (token: number) => boolean;
    };
    readonly setInvoiceDetail: React.Dispatch<React.SetStateAction<Fee | null>>;
    readonly invoiceMineMeta: {
        total: number;
        totalAmount: number;
        totalExtraAmount: number;
        page: number;
        pageSize: number;
    };
    readonly invoiceMineParams: (query: Record<string, any>, page?: number, pageSize?: number) => {
        scope: string;
        customer: any;
        application_no: any;
        invoice_type: any;
        invoice_title: any;
        invoice_no: any;
        invoice_status: any;
        invoiced_from: any;
        invoiced_to: any;
        case_no: any;
        page: number;
        page_size: number;
    };
    readonly setInvoiceMineRows: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setInvoiceMineMeta: React.Dispatch<React.SetStateAction<{
        total: number;
        totalAmount: number;
        totalExtraAmount: number;
        page: number;
        pageSize: number;
    }>>;
    readonly invoiceCompanyMeta: {
        total: number;
        totalAmount: number;
        totalExtraAmount: number;
        page: number;
        pageSize: number;
    };
    readonly invoiceCompanyParams: (query: Record<string, any>, page?: number, pageSize?: number) => {
        scope: string;
        customer: any;
        application_no: any;
        invoice_type: any;
        invoice_title: any;
        invoice_no: any;
        invoice_status: any;
        invoiced_from: any;
        invoiced_to: any;
        applicant: any;
        case_no: any;
        page: number;
        page_size: number;
    };
    readonly setInvoiceCompanyRows: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setInvoiceCompanyMeta: React.Dispatch<React.SetStateAction<{
        total: number;
        totalAmount: number;
        totalExtraAmount: number;
        page: number;
        pageSize: number;
    }>>;
    readonly invoiceUnissuedMeta: {
        total: number;
        totalAmount: number;
        totalInvoiceAmount: number;
        totalCashedAmount: number;
        totalPaidAmount: number;
        page: number;
        pageSize: number;
    };
    readonly invoiceUnissuedParams: (query: Record<string, any>, page?: number, pageSize?: number) => {
        scope: string;
        case_no: any;
        court_case_no: any;
        notary_no: any;
        invoice_amount_from: any;
        invoice_amount_to: any;
        customer: any;
        paid_organization: any;
        invoice_status: any;
        invoice_from: any;
        invoice_to: any;
        hearing_lawyer: any;
        assistant: any;
        case_stages: string;
        paid_from: any;
        paid_to: any;
        fee_types: string;
        payer_name: any;
        cashed_from: any;
        cashed_to: any;
        page: number;
        page_size: number;
    };
    readonly setInvoiceUnissuedRows: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setInvoiceUnissuedMeta: React.Dispatch<React.SetStateAction<{
        total: number;
        totalAmount: number;
        totalInvoiceAmount: number;
        totalCashedAmount: number;
        totalPaidAmount: number;
        page: number;
        pageSize: number;
    }>>;
    readonly invoicePendingMeta: {
        total: number;
        totalAmount: number;
        totalExtraAmount: number;
        page: number;
        pageSize: number;
    };
    readonly invoicePendingParams: (query: Record<string, any>, page?: number, pageSize?: number) => {
        scope: string;
        customer: any;
        application_no: any;
        invoice_type: any;
        invoice_title: any;
        invoice_no: any;
        invoice_status: any;
        invoiced_from: any;
        invoiced_to: any;
        applicant: any;
        case_no: any;
        page: number;
        page_size: number;
    };
    readonly setInvoicePendingRows: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setInvoicePendingMeta: React.Dispatch<React.SetStateAction<{
        total: number;
        totalAmount: number;
        totalExtraAmount: number;
        page: number;
        pageSize: number;
    }>>;
    readonly setContracts: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setCustomers: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setInvoiceCandidateFees: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly invoiceForm: FormInstance<any>;
    readonly cases: Fee[];
    readonly contracts: Fee[];
    readonly invoiceCandidateFees: Fee[];
    readonly fees: Fee[];
    readonly invoiceEditTarget: Fee | null;
    readonly invoices: Fee[];
    readonly setInvoiceOpen: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setInvoiceEditTarget: React.Dispatch<React.SetStateAction<Fee | null>>;
    readonly load: () => Promise<void>;
    readonly issueTarget: Fee | null;
    readonly invoiceProcess: Fee | null;
    readonly issueForm: FormInstance<any>;
    readonly setIssueTarget: React.Dispatch<React.SetStateAction<Fee | null>>;
    readonly setInvoiceProcess: React.Dispatch<React.SetStateAction<Fee | null>>;
    readonly originalQuery: Record<string, any>;
    readonly voidTarget: Fee | null;
    readonly voidForm: FormInstance<any>;
    readonly setVoidTarget: React.Dispatch<React.SetStateAction<Fee | null>>;
    readonly invoiceNumberTarget: Fee | null;
    readonly invoiceNumberForm: FormInstance<any>;
    readonly setInvoiceMutationLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setInvoiceNumberTarget: React.Dispatch<React.SetStateAction<Fee | null>>;
    readonly invoiceDateTarget: Fee | null;
    readonly invoiceDateForm: FormInstance<any>;
    readonly setInvoiceDateTarget: React.Dispatch<React.SetStateAction<Fee | null>>;
    readonly invoiceCancel: Fee | null;
    readonly invoiceCancelReason: string;
    readonly setInvoiceCancel: React.Dispatch<React.SetStateAction<Fee | null>>;
    readonly setInvoiceCancelReason: React.Dispatch<React.SetStateAction<string>>;
    readonly selectedOriginalRows: (string | number)[];
    readonly setInvoiceExportLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly isInvoicePendingRoute: boolean;
    readonly isInvoiceCompanyRoute: boolean;
    readonly initialView: string;
}
export function createFinanceInvoicesActions(context: FinanceInvoicesDependencies) {
    const openInvoiceDetail = async (row: FinanceFlow) => {
        const { invoiceDetailRequestGuard, setInvoiceDetail } = context;
        const token = invoiceDetailRequestGuard.begin();
        try {
            const { data } = await api.get(`/records/${row.id}`);
            if (!invoiceDetailRequestGuard.isLatest(token))
                return;
            if (!data || data.module !== "invoice") {
                throw new Error("发票详情记录无效");
            }
            if (String(data.id) !== String(row.id)) {
                throw new Error("发票详情记录不匹配");
            }
            setInvoiceDetail(data);
        }
        catch (error: any) {
            if (invoiceDetailRequestGuard.isLatest(token)) {
                message.error(error?.response?.data?.detail || error?.message || "发票详情加载失败");
            }
        }
    };
    const loadInvoiceMine = async (query: Record<string, any>, page = 1, pageSize = context.invoiceMineMeta.pageSize) => {
        const { invoiceMineMeta, invoiceMineParams, setInvoiceMineRows, setInvoiceMineMeta } = context;
        const response = await api.get("/finance/invoices", {
            params: invoiceMineParams(query, page, pageSize),
        });
        setInvoiceMineRows(response.data.items || []);
        setInvoiceMineMeta({
            total: response.data.total || 0,
            totalAmount: Number(response.data.total_amount || 0),
            totalExtraAmount: Number(response.data.total_extra_amount || 0),
            page: response.data.page || page,
            pageSize: response.data.page_size || pageSize,
        });
    };
    const loadInvoiceCompany = async (query: Record<string, any>, page = 1, pageSize = context.invoiceCompanyMeta.pageSize) => {
        const { invoiceCompanyMeta, invoiceCompanyParams, setInvoiceCompanyRows, setInvoiceCompanyMeta } = context;
        const response = await api.get("/finance/invoices", {
            params: invoiceCompanyParams(query, page, pageSize),
        });
        setInvoiceCompanyRows(response.data.items || []);
        setInvoiceCompanyMeta({
            total: response.data.total || 0,
            totalAmount: Number(response.data.total_amount || 0),
            totalExtraAmount: Number(response.data.total_extra_amount || 0),
            page: response.data.page || page,
            pageSize: response.data.page_size || pageSize,
        });
    };
    const loadInvoiceUnissued = async (query: Record<string, any>, page = 1, pageSize = context.invoiceUnissuedMeta.pageSize) => {
        const { invoiceUnissuedMeta, invoiceUnissuedParams, setInvoiceUnissuedRows, setInvoiceUnissuedMeta } = context;
        const response = await api.get("/finance/case-fees/invoice-status", {
            params: invoiceUnissuedParams(query, page, pageSize),
        });
        setInvoiceUnissuedRows(response.data.items || []);
        setInvoiceUnissuedMeta({
            total: response.data.total || 0,
            totalAmount: Number(response.data.totals?.amount || 0),
            totalInvoiceAmount: Number(response.data.totals?.invoice_amount || 0),
            totalCashedAmount: Number(response.data.totals?.cashed_amount || 0),
            totalPaidAmount: Number(response.data.totals?.paid_amount || 0),
            page: response.data.page || page,
            pageSize: response.data.page_size || pageSize,
        });
    };
    const loadInvoicePending = async (query: Record<string, any>, page = 1, pageSize = context.invoicePendingMeta.pageSize) => {
        const { invoicePendingMeta, invoicePendingParams, setInvoicePendingRows, setInvoicePendingMeta } = context;
        const response = await api.get("/finance/invoices", {
            params: invoicePendingParams(query, page, pageSize),
        });
        setInvoicePendingRows(response.data.items || []);
        setInvoicePendingMeta({
            total: response.data.total || 0,
            totalAmount: Number(response.data.total_amount || 0),
            totalExtraAmount: Number(response.data.total_extra_amount || 0),
            page: response.data.page || page,
            pageSize: response.data.page_size || pageSize,
        });
    };
    const loadInvoiceReferenceData = async () => {
        const { setContracts, setCustomers, setInvoiceCandidateFees } = context;
        try {
            const [contractResponse, customerResponse, feeResponse] = await Promise.all([
                api.get("/records", { params: { module: "contract", page_size: 100 } }),
                api.get("/records", { params: { module: "customer", page_size: 100 } }),
                api.get("/finance/case-fees/invoice-status", {
                    params: { scope: "company", invoice_status: "未开票", page: 1, page_size: 100, fee_types: "" },
                }),
            ]);
            const contractRows = Array.isArray(contractResponse.data?.items) ? contractResponse.data.items : [];
            const customerRows = Array.isArray(customerResponse.data?.items) ? customerResponse.data.items : [];
            const candidateRows = Array.isArray(feeResponse.data?.items) ? feeResponse.data.items : [];
            setContracts(contractRows);
            setCustomers(customerRows);
            setInvoiceCandidateFees(candidateRows);
            return { contractRows, customerRows, candidateRows };
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "合同关联数据加载失败");
            throw error;
        }
    };
    const createInvoice = async () => {
        const { invoiceForm, cases, contracts, invoiceCandidateFees, fees, invoiceEditTarget, invoices, setInvoiceOpen, setInvoiceEditTarget, load } = context;
        const v = await invoiceForm.validateFields();
        const linked = buildInvoiceApplicationPayload({
            values: v,
            cases,
            contracts,
            caseFees: invoiceCandidateFees.length ? invoiceCandidateFees : fees,
            requireSource: !invoiceEditTarget,
        });
        if (linked.ok === false) {
            message.error(linked.error);
            return;
        }
        if (!invoiceEditTarget) {
            const selectedFeeIds = new Set((linked.payload.case_fee_ids || []).map(Number));
            const duplicateInvoice = invoices.find((invoice) => !["已撤回", "已作废"].includes(invoice.status) &&
                (invoice.data?.case_fee_ids || []).some((feeId: number) => selectedFeeIds.has(Number(feeId))));
            if (duplicateInvoice) {
                message.error("所选案件费用已经申请开票，不能重复申请");
                return;
            }
        }
        try {
            if (invoiceEditTarget) {
                const response = await api.patch(`/finance/invoices/${invoiceEditTarget.id}`, linked.payload);
                const legacyFailure = legacyInvoiceUpdateFailureMessage(response);
                if (legacyFailure)
                    throw { legacyInvoiceUpdateFailure: legacyFailure };
                message.success("发票申请草稿已更新");
            }
            else {
                await api.post("/finance/invoices", linked.payload);
                message.success("发票申请草稿已创建");
            }
            setInvoiceOpen(false);
            setInvoiceEditTarget(null);
            invoiceForm.resetFields();
            await loadInvoiceReferenceData();
            await load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail ||
                error?.legacyInvoiceUpdateFailure ||
                (invoiceEditTarget
                    ? "发票申请更新失败，请确认后端已提供 PATCH /finance/invoices/{id}"
                    : "发票申请创建失败"));
        }
    };
    const issueInvoice = async () => {
        const { issueTarget, invoiceProcess, issueForm, setIssueTarget, setInvoiceProcess, load } = context;
        const target = issueTarget || invoiceProcess;
        if (!target)
            return;
        if (invoiceProcess && !String(issueForm.getFieldValue("invoice_no") || "").trim()) {
            Modal.info({ title: "提示", content: "请输入发票号码.", okText: "确定" });
            return;
        }
        const v = await issueForm.validateFields();
        try {
            await api.post(`/finance/invoices/${target.id}/issue`, {
                ...v,
                invoice_date: formatRequiredDate(v.invoice_date, "开票日期"),
            });
            message.success("开票信息已登记");
            setIssueTarget(null);
            setInvoiceProcess(null);
            issueForm.resetFields();
            load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "开票登记失败");
        }
    };
    const rejectInvoiceIssue = async () => {
        const { invoiceProcess, issueForm, setInvoiceProcess, originalQuery, invoicePendingMeta } = context;
        if (!invoiceProcess)
            return;
        const reason = String(issueForm.getFieldValue("comment") || "").trim();
        if (!reason) {
            Modal.info({ title: "提示", content: "请输入驳回原因.", okText: "确定" });
            return;
        }
        try {
            await api.post(`/finance/invoices/${invoiceProcess.id}/reject-issue`, {
                comment: reason,
            });
            message.success("发票申请已驳回");
            setInvoiceProcess(null);
            issueForm.resetFields();
            await loadInvoicePending(originalQuery, 1, invoicePendingMeta.pageSize);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "开票驳回失败");
        }
    };
    const voidInvoice = async () => {
        const { voidTarget, voidForm, setVoidTarget, load } = context;
        if (!voidTarget)
            return;
        const v = await voidForm.validateFields();
        try {
            await api.post(`/finance/invoices/${voidTarget.id}/void`, v);
            message.success("发票已作废并生成冲销流水");
            setVoidTarget(null);
            voidForm.resetFields();
            load();
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "发票作废失败");
        }
    };
    const submitInvoiceNumberChange = async () => {
        const { invoiceNumberTarget, invoiceNumberForm, setInvoiceMutationLoading, setInvoiceNumberTarget, originalQuery, invoiceCompanyMeta } = context;
        if (!invoiceNumberTarget)
            return;
        const invoiceNo = String(invoiceNumberForm.getFieldValue("new_invoice_no") || "").trim();
        if (!invoiceNo) {
            Modal.info({
                title: "提示",
                content: "请输入新发票号码.",
                okText: "确定",
            });
            return;
        }
        setInvoiceMutationLoading(true);
        try {
            await api.post(`/finance/invoices/${invoiceNumberTarget.id}/change-number`, { invoice_no: invoiceNo });
            message.success("修改成功.");
            setInvoiceNumberTarget(null);
            invoiceNumberForm.resetFields();
            await loadInvoiceCompany(originalQuery, invoiceCompanyMeta.page, invoiceCompanyMeta.pageSize);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "发票号码修改失败");
        }
        finally {
            setInvoiceMutationLoading(false);
        }
    };
    const submitInvoiceDateChange = async () => {
        const { invoiceDateTarget, invoiceDateForm, setInvoiceMutationLoading, setInvoiceDateTarget, originalQuery, invoiceCompanyMeta } = context;
        if (!invoiceDateTarget)
            return;
        const applicationDate = invoiceDateForm.getFieldValue("application_date");
        const invoiceDate = invoiceDateForm.getFieldValue("invoice_date");
        if (!applicationDate) {
            Modal.info({
                title: "提示",
                content: "请输入发票申请日期.",
                okText: "确定",
            });
            return;
        }
        if (!invoiceDate) {
            Modal.info({
                title: "提示",
                content: "请输入发票开票日期.",
                okText: "确定",
            });
            return;
        }
        setInvoiceMutationLoading(true);
        try {
            await api.post(`/finance/invoices/${invoiceDateTarget.id}/change-date`, {
                application_date: applicationDate.format("YYYY-MM-DD"),
                invoice_date: invoiceDate.format("YYYY-MM-DD"),
            });
            message.success("修改成功.");
            setInvoiceDateTarget(null);
            invoiceDateForm.resetFields();
            await loadInvoiceCompany(originalQuery, invoiceCompanyMeta.page, invoiceCompanyMeta.pageSize);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "发票日期修改失败");
        }
        finally {
            setInvoiceMutationLoading(false);
        }
    };
    const submitInvoiceCancel = async () => {
        const { invoiceCancel, invoiceCancelReason, setInvoiceMutationLoading, setInvoiceCancel, setInvoiceCancelReason, originalQuery, invoiceCompanyMeta } = context;
        if (!invoiceCancel)
            return;
        const reason = invoiceCancelReason.trim();
        if (!reason) {
            Modal.info({ title: "提示", content: "请输入作废原因.", okText: "确定" });
            return;
        }
        setInvoiceMutationLoading(true);
        try {
            await api.post(`/finance/invoices/${invoiceCancel.id}/void`, { reason });
            message.success("发票已作废并生成冲销流水");
            setInvoiceCancel(null);
            setInvoiceCancelReason("");
            await loadInvoiceCompany(originalQuery, invoiceCompanyMeta.page, invoiceCompanyMeta.pageSize);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "发票作废失败");
        }
        finally {
            setInvoiceMutationLoading(false);
        }
    };
    const exportInvoiceList = async (selectedOnly: boolean) => {
        const { selectedOriginalRows, setInvoiceExportLoading, isInvoicePendingRoute, invoicePendingParams, originalQuery, isInvoiceCompanyRoute, invoiceCompanyParams, invoiceMineParams } = context;
        if (selectedOnly && !selectedOriginalRows.length) {
            Modal.info({
                title: "提示",
                content: "请选择需要导出的发票.",
                okText: "确定",
            });
            return;
        }
        setInvoiceExportLoading(true);
        try {
            const params: Record<string, any> = {
                ...(isInvoicePendingRoute
                    ? invoicePendingParams(originalQuery, 1, 15)
                    : isInvoiceCompanyRoute
                        ? invoiceCompanyParams(originalQuery, 1, 15)
                        : invoiceMineParams(originalQuery, 1, 15)),
            };
            delete params.page;
            delete params.page_size;
            if (selectedOnly)
                params.ids = selectedOriginalRows.join(",");
            const response = await api.get("/finance/invoices/export", {
                params,
                responseType: "blob",
            });
            const url = URL.createObjectURL(response.data);
            const anchor = document.createElement("a");
            anchor.href = url;
            anchor.download = `${isInvoicePendingRoute ? "待处理开票" : isInvoiceCompanyRoute ? "公司开票" : "我的开票"}-${dayjs().format("YYYY-MM-DD")}.xls`;
            anchor.click();
            URL.revokeObjectURL(url);
            message.success("导出成功.");
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "导出失败");
        }
        finally {
            setInvoiceExportLoading(false);
        }
    };
    const exportInvoiceUnissued = async (selectedOnly: boolean) => {
        const { selectedOriginalRows, setInvoiceExportLoading, invoiceUnissuedParams, originalQuery, initialView } = context;
        if (selectedOnly && !selectedOriginalRows.length) {
            Modal.info({
                title: "提示",
                content: "请选择需要导出的费用.",
                okText: "确定",
            });
            return;
        }
        setInvoiceExportLoading(true);
        try {
            const params: Record<string, any> = {
                ...invoiceUnissuedParams(originalQuery, 1, 15),
            };
            delete params.page;
            delete params.page_size;
            if (selectedOnly)
                params.ids = selectedOriginalRows.join(",");
            const response = await api.get("/finance/case-fees/invoice-status/export", { params, responseType: "blob" });
            const url = URL.createObjectURL(response.data);
            const anchor = document.createElement("a");
            anchor.href = url;
            anchor.download = `${initialView === "finance-invoice-company-unissued" ? "公司未开票" : "未开票"}-${dayjs().format("YYYY-MM-DD")}.xls`;
            anchor.click();
            URL.revokeObjectURL(url);
            message.success("导出成功.");
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "导出失败");
        }
        finally {
            setInvoiceExportLoading(false);
        }
    };
    return { openInvoiceDetail, loadInvoiceMine, loadInvoiceCompany, loadInvoiceUnissued, loadInvoicePending, loadInvoiceReferenceData, createInvoice, issueInvoice, rejectInvoiceIssue, voidInvoice, submitInvoiceNumberChange, submitInvoiceDateChange, submitInvoiceCancel, exportInvoiceList, exportInvoiceUnissued };
}
