import { receiptBankCode } from "../bankReceiptScope";
import { message } from "antd";
import type { AxiosResponse } from "axios";
import dayjs from "dayjs";
import { api } from "../../api";
import { financeCenterApi } from "./financeCenterApi";
import type { FinanceScope, SettlementRow } from "../types";
import { settlementSourceCounts } from "../settlementIdentity";
import { rememberCaseDetailTarget } from "../../caseDetailNavigation";
import { rememberContractDetailTarget } from "../../contractDetailNavigation";
import { rememberCustomerDetailTarget } from "../../customerDetailNavigation";
import { internalFeeExportRequestParams } from "../../financeInternalFeeHelpers.mjs";
import { normalizeRefundResponse } from "../../financeRefundHelpers.mjs";
import { invoiceLegacyDefaultPageSize, normalizePaymentPackageResponse, paymentPackageRequestParams } from "../constants";
import type { ArchiveSettlementRow, ContractPaymentSourceState, Fee, FinancePersonOption, FinanceSummary, IncomingPayment, LegacyFinanceRecord, LegacyFinanceSummary, Reconciliation, Transaction, OriginalRouteConfig } from "../types";
import { financeRouteResources, loadFinanceQueryResources } from "./queryResources";
import { incomingPaymentQueryParams } from "./incomingQuery";
import type { IncomingPaymentPage } from "../hooks/useIncomingPaymentQuery";
import { financeErrorDetail, financeErrorMessageText } from "../financeErrors";

const projectionNumericId = (value: unknown) => {
    const raw = String(value ?? "");
    const modernMatch = raw.match(/^modern-fee:(\d+)$/);
    if (modernMatch) return Number(modernMatch[1]);
    const legacyMatch = raw.match(/^legacy-fee:(\d+)$/);
    if (legacyMatch) return -Number(legacyMatch[1]);
    throw new Error("财务投影费用编号无效");
};

const normalizeProjectionFees = (items: unknown[]): Fee[] => items.map((item) => {
    const row = (item || {}) as Record<string, any>;
    const projectionId = String(row.id ?? "");
    return {
        ...row,
        id: projectionNumericId(projectionId),
        projection_id: projectionId,
    } as Fee;
});

const normalizeProjectionTransactions = (items: unknown[]): Transaction[] => items.map((item) => {
    const row = (item || {}) as Record<string, any>;
    const projectionId = String(row.id ?? "");
    const modernMatch = projectionId.match(/^modern-transaction:(\d+)$/);
    return {
        ...row,
        id: modernMatch ? Number(modernMatch[1]) : projectionId,
    } as Transaction;
});

const normalizeContractPayments = (items: Fee[]): Fee[] => items.map((item) => ({
    ...item,
    data: {
        ...(item.data || {}),
        _source_module: "contract_payment",
        fee_type: item.data?.lines?.[0]?.fee_type || item.data?.payment_type,
        case_no: item.data?.lines?.[0]?.case_no,
        amount: item.data?.amount,
    },
}));

const loadTransactionsForFees = async (items: Fee[]) => {
    const ids = Array.from(new Set(items
        .filter((item) => item.module === "finance" && Number.isInteger(item.id) && item.id > 0)
        .map((item) => item.id)));
    if (!ids.length) return null;
    const requests = [];
    for (let offset = 0; offset < ids.length; offset += 500) {
        requests.push(api.get("/finance/transactions", {
            params: { finance_record_ids: ids.slice(offset, offset + 500).join(",") },
        }));
    }
    const responses = await Promise.all(requests);
    const transactions = responses.flatMap((response) => response.data.items || []);
    return { data: { items: transactions, total: transactions.length, page: 1, page_size: transactions.length } };
};

const projectionFeeParams = (route: string, tab: string) => ({
    fee_type: route.startsWith("finance-internal") ? "内部费用"
        : route.startsWith("finance-settlement") ? "结算费用"
            : route.startsWith("finance-archive-fee") ? "归档费用" : undefined,
    status: route.startsWith("finance-audit") || tab === "audit" ? "待审批" : undefined,
    source: "modern",
});

async function loadMyInternalApplications() {
    const items: Fee[] = [];
    let page = 1;
    let total = 0;
    do {
        const response = await api.get("/finance/internal-fees", {
            params: { scope: "applications", page, page_size: 200 },
        });
        const batch: Fee[] = response.data.items;
        items.push(...batch);
        total = Number(response.data.total || 0);
        if (!batch.length) break;
        page += 1;
    } while (items.length < total);
    return { data: { items, total: items.length, page: 1, page_size: items.length || 15 } };
}

async function loadPaymentApprovalApplications() {
    // 待审批筛选在服务端分页前完成，不让历史终态单据挤掉真正待办。
    const items: Fee[] = [];
    let page = 1;
    let total = 0;
    do {
        const { data } = await api.get("/finance/payment-applications/query", {
            params: { scope: "audit", page, page_size: 200 },
        });
        if (!Array.isArray(data.items) || !Number.isInteger(data.total) || data.total < 0) {
            throw new Error("请款单审批分页响应无效");
        }
        items.push(...data.items);
        total = data.total;
        if (!data.items.length && items.length < total) {
            throw new Error("请款单审批数据未完整返回，请刷新后重试");
        }
        page += 1;
    } while (items.length < total);
    return { data: { items, total, page: 1, page_size: items.length || 15 } };
}
/** finance queries operations; dependencies are read when each operation runs. */
export interface FinanceQueriesDependencies {
    readonly financeScope: FinanceScope;
    readonly isInternalQueueRoute: boolean;
    readonly loadInternalQueue: (query: Record<string, unknown>, page?: number, pageSize?: number) => Promise<any>;
    readonly onNavigate: ((route: string) => void) | undefined;
    readonly internalDetailMeta: {
        total: number;
        totalAmount: number;
        page: number;
        pageSize: number;
    };
    readonly internalDetailParams: (query: Record<string, any>, page?: number, pageSize?: number) => {
        scope: string;
        case_no: any;
        handling_lawyer: any;
        assistant: any;
        source_person: any;
        customer: any;
        customer_manager: any;
        investigator: any;
        payment_status: any;
        paid_from: any;
        paid_to: any;
        payee: any;
        case_stages: string;
        fee_types: string;
        page: number;
        page_size: number;
    };
    readonly setInternalDetailRows: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setInternalDetailMeta: React.Dispatch<React.SetStateAction<{
        total: number;
        totalAmount: number;
        page: number;
        pageSize: number;
    }>>;
    readonly setLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setFinanceDataReady: React.Dispatch<React.SetStateAction<boolean>>;
    readonly initialView: string;
    readonly tab: string;
    readonly loadPaymentQueryPage: (query: Record<string, any>, page?: number, pageSize?: number) => Promise<{
        data: {
            items: any[];
            total: number;
            page: number;
            page_size: number;
        };
    }>;
    readonly paymentQueryPageSize: number;
    readonly contractPaymentSource: ContractPaymentSourceState;
    readonly loadRefunds: (page?: number, pageSize?: number, status?: string, preserveOnError?: boolean, group?: string) => Promise<{
        applied: boolean;
        response: null;
    } | {
        applied: boolean;
        response: AxiosResponse<any, any, {}>;
    }>;
    readonly refundMeta: {
        total: number;
        page: number;
        pageSize: number;
    };
    readonly activeRefundStatus: string;
    readonly isRefundNotRequiredRoute: boolean;
    readonly paymentPackageMeta: {
        total: number;
        page: number;
        pageSize: number;
    };
    readonly isInternalDetailRoute: boolean;
    readonly currentUser: {
        username: any;
        displayName: any;
    };
    readonly isInvoiceMineRoute: boolean;
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
    readonly isInvoicePendingRoute: boolean;
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
    readonly isInvoiceCompanyRoute: boolean;
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
    readonly isInvoiceUnissuedRoute: boolean;
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
    readonly isGeneralSettlementRoute: boolean;
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
    readonly isArchiveSettlementActiveRoute: boolean;
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
    readonly isFeeQueryRoute: boolean;
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
    readonly dashboardFeeQuerySeed: Record<string, unknown>;
    readonly dashboardQueue: string;
    readonly setFees: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly financeProjectionEnabled: boolean;
    readonly financeFeeListMeta: { page: number; pageSize: number; total: number };
    readonly setFinanceFeeListMeta: React.Dispatch<React.SetStateAction<{
        page: number;
        pageSize: number;
        total: number;
    }>>;
    readonly financeTransactionMeta: { page: number; pageSize: number; total: number };
    readonly setFinanceTransactionMeta: React.Dispatch<React.SetStateAction<{
        page: number;
        pageSize: number;
        total: number;
    }>>;
    readonly setPaymentQueryMeta: React.Dispatch<React.SetStateAction<{
        total: number;
        page: number;
        pageSize: number;
    }>>;
    readonly setContractPayments: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setInvoices: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setRefunds: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setRefundMeta: React.Dispatch<React.SetStateAction<{
        total: number;
        page: number;
        pageSize: number;
    }>>;
    readonly setSelectedRefundRows: React.Dispatch<React.SetStateAction<number[]>>;
    readonly setCases: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setCustomers: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setIncoming: React.Dispatch<React.SetStateAction<IncomingPayment[]>>;
    readonly loadIncomingPayments: (query: Record<string, unknown>, page?: number, pageSize?: number) => Promise<{ data: IncomingPaymentPage } | null>;
    readonly setSelectedIncomingRows: React.Dispatch<React.SetStateAction<number[]>>;
    readonly setTransactions: React.Dispatch<React.SetStateAction<Transaction[]>>;
    readonly setReconciliations: React.Dispatch<React.SetStateAction<Reconciliation[]>>;
    readonly setSummary: React.Dispatch<React.SetStateAction<FinanceSummary>>;
    readonly setRole: React.Dispatch<any>;
    readonly setCurrentUser: React.Dispatch<React.SetStateAction<{
        username: any;
        displayName: any;
    }>>;
    readonly setFinancePeople: React.Dispatch<React.SetStateAction<FinancePersonOption[]>>;
    readonly setPendingSettlements: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setRefundReviewFees: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setPaymentPackages: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setPaymentPackageMeta: React.Dispatch<React.SetStateAction<{
        total: number;
        page: number;
        pageSize: number;
    }>>;
    readonly setInvoiceMineRows: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setInvoiceMineMeta: React.Dispatch<React.SetStateAction<{
        total: number;
        totalAmount: number;
        totalExtraAmount: number;
        page: number;
        pageSize: number;
    }>>;
    readonly setInvoicePendingRows: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setInvoicePendingMeta: React.Dispatch<React.SetStateAction<{
        total: number;
        totalAmount: number;
        totalExtraAmount: number;
        page: number;
        pageSize: number;
    }>>;
    readonly setInvoiceCompanyRows: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setInvoiceCompanyMeta: React.Dispatch<React.SetStateAction<{
        total: number;
        totalAmount: number;
        totalExtraAmount: number;
        page: number;
        pageSize: number;
    }>>;
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
    readonly setGeneralSettlementRows: React.Dispatch<React.SetStateAction<SettlementRow[]>>;
    readonly setGeneralSettlementMeta: React.Dispatch<React.SetStateAction<{
        total: number;
        page: number;
        pageSize: number;
        totals: Record<string, number>;
    }>>;
    readonly setArchiveSettlementRows: React.Dispatch<React.SetStateAction<ArchiveSettlementRow[]>>;
    readonly setArchiveSettlementMeta: React.Dispatch<React.SetStateAction<{
        total: number;
        page: number;
        pageSize: number;
        totals: Record<string, number>;
    }>>;
    readonly setFeeQueryRows: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setFeeQueryMeta: React.Dispatch<React.SetStateAction<{
        total: number;
        page: number;
        pageSize: number;
        totals: Record<string, number | null>;
    }>>;
    readonly legacyFinanceMeta: {
        total: number;
        page: number;
        pageSize: number;
    };
    readonly setLegacyFinanceLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly legacyFinanceKind: string;
    readonly legacyFinanceStatusCode: string;
    readonly legacyFinanceKeyword: string;
    readonly legacyFinanceIncludeInactive: boolean;
    readonly setLegacyFinanceRows: React.Dispatch<React.SetStateAction<LegacyFinanceRecord[]>>;
    readonly setLegacyFinanceMeta: React.Dispatch<React.SetStateAction<{
        total: number;
        page: number;
        pageSize: number;
    }>>;
    readonly setLegacyFinanceSummary: React.Dispatch<React.SetStateAction<LegacyFinanceSummary>>;
    readonly setLegacyFinanceDetailLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly setLegacyFinanceDetail: React.Dispatch<React.SetStateAction<LegacyFinanceRecord | null>>;
    readonly selectedOriginalRows: (string | number)[];
    readonly setInternalDetailExportLoading: React.Dispatch<React.SetStateAction<boolean>>;
    readonly originalQuery: Record<string, any>;
    readonly activeRouteConfig: OriginalRouteConfig;
    readonly displayedOriginalTitle: string;
    readonly configuredRows: any[];
    readonly cellValue: (row: any, header: string) => any;
}
export function createFinanceQueriesActions(context: FinanceQueriesDependencies) {
    const api = financeCenterApi(context.financeScope);
    const openCaseDetail = async (caseNo: unknown) => {
        const { onNavigate } = context;
        const serialNo = String(caseNo || "").trim();
        if (!serialNo || serialNo === "—") {
            message.warning("当前记录未关联案件");
            return;
        }
        try {
            const { data } = await api.get("/records", { params: { module: "case", keyword: serialNo, page_size: 100 } });
            const record = (data.items as Fee[]).find((item) => item.serial_no === serialNo);
            if (!record) {
                message.warning("未找到关联案件或当前账号无权查看");
                return;
            }
            rememberCaseDetailTarget({ id: record.id, serial_no: record.serial_no });
            onNavigate?.("case-company");
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "关联案件加载失败");
        }
    };
    const openContractDetail = async (contractNo: unknown) => {
        const { onNavigate } = context;
        const serialNo = String(contractNo || "").trim();
        if (!serialNo || serialNo === "—") {
            message.warning("当前记录未关联合同");
            return;
        }
        try {
            const { data } = await api.get("/records", { params: { module: "contract", keyword: serialNo, page_size: 100 } });
            const record = (data.items as Fee[]).find((item) => item.serial_no === serialNo);
            if (!record) {
                message.warning("未找到关联合同或当前账号无权查看");
                return;
            }
            rememberContractDetailTarget({ id: record.id, serial_no: record.serial_no });
            onNavigate?.("contract-company");
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "关联合同加载失败");
        }
    };
    const openCustomerDetail = async (customer: unknown, customerNo?: unknown) => {
        const { onNavigate } = context;
        const title = String(customer || "").trim();
        const serialNo = String(customerNo || "").trim();
        if (!title && !serialNo) {
            message.warning("当前记录未关联客户");
            return;
        }
        try {
            const { data } = await api.get("/records", { params: { module: "customer", keyword: serialNo || title, page_size: 100 } });
            const record = (data.items as Fee[]).find((item) => (serialNo && item.serial_no === serialNo) || (title && (item.title === title || item.customer === title)));
            if (!record) {
                message.warning("未找到关联客户或当前账号无权查看");
                return;
            }
            rememberCustomerDetailTarget({ id: record.id, title: record.title, serial_no: record.serial_no });
            onNavigate?.("customer-company");
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "关联客户加载失败");
        }
    };
    const loadInternalDetails = async (query: Record<string, any>, page = 1, pageSize = context.internalDetailMeta.pageSize) => {
        const { internalDetailParams, setInternalDetailRows, setInternalDetailMeta } = context;
        const response = await api.get("/finance/internal-fees", {
            params: internalDetailParams(query, page, pageSize),
        });
        setInternalDetailRows(response.data.items || []);
        setInternalDetailMeta({
            total: response.data.total || 0,
            totalAmount: Number(response.data.total_amount || 0),
            page: response.data.page || page,
            pageSize: response.data.page_size || pageSize,
        });
    };
    const loadFinanceProjectionPage = async (
        kind: "fees" | "transactions",
        page = 1,
        pageSize = kind === "fees" ? context.financeFeeListMeta.pageSize : context.financeTransactionMeta.pageSize,
        selectedTab = context.tab,
    ) => {
        if (!context.financeProjectionEnabled) return;
        context.setLoading(true);
        try {
            const { data } = await api.get(`/finance/projection/${kind}`, {
                params: {
                    page, page_size: pageSize,
                    ...(kind === "fees" ? projectionFeeParams(context.initialView, selectedTab) : {}),
                },
            });
            const meta = {
                page: Number(data.page || page),
                pageSize: Number(data.page_size || pageSize),
                total: Number(data.total || data.items?.length || 0),
            };
            if (kind === "fees") {
                context.setFees(normalizeProjectionFees(data.items || []));
                context.setFinanceFeeListMeta(meta);
            } else {
                context.setTransactions(normalizeProjectionTransactions(data.items || []));
                context.setFinanceTransactionMeta(meta);
            }
        } catch (error: any) {
            message.error(error?.response?.data?.detail || "财务数据加载失败");
        } finally {
            context.setLoading(false);
        }
    };
    const loadForTab = async (selectedTab: string, query?: Record<string, unknown>) => {
        const { setLoading, setFinanceDataReady, initialView, loadPaymentQueryPage, paymentQueryPageSize, contractPaymentSource, loadRefunds, refundMeta, activeRefundStatus, isRefundNotRequiredRoute, paymentPackageMeta, isInternalDetailRoute, internalDetailParams, currentUser, isInvoiceMineRoute, invoiceMineParams, isInvoicePendingRoute, invoicePendingParams, isInvoiceCompanyRoute, invoiceCompanyParams, isInvoiceUnissuedRoute, invoiceUnissuedParams, isGeneralSettlementRoute, isGeneralSettlementPendingRoute, generalSettlementParams, isArchiveSettlementActiveRoute, isArchiveSettlementPaymentRoute, isArchiveSettlementPaidRoute, isArchiveSettlementRejectedRoute, archiveSettlementParams, isFeeQueryRoute, isRefundCaseFeeRoute, feeQueryParams, dashboardFeeQuerySeed, setFees, setFinanceFeeListMeta, setPaymentQueryMeta, setContractPayments, setInvoices, setRefunds, setRefundMeta, setSelectedRefundRows, setCases, setCustomers, setIncoming, setSelectedIncomingRows, setTransactions, setReconciliations, setSummary, setRole, setCurrentUser, setFinancePeople, setPendingSettlements, setRefundReviewFees, setPaymentPackages, setPaymentPackageMeta, setInternalDetailRows, setInternalDetailMeta, setInvoiceMineRows, setInvoiceMineMeta, setInvoicePendingRows, setInvoicePendingMeta, setInvoiceCompanyRows, setInvoiceCompanyMeta, setInvoiceUnissuedRows, setInvoiceUnissuedMeta, setGeneralSettlementRows, setGeneralSettlementMeta, setArchiveSettlementRows, setArchiveSettlementMeta, setFeeQueryRows, setFeeQueryMeta } = context;
        const loadContractPaymentRecords = () => contractPaymentSource.active && contractPaymentSource.ok
            ? api.get(`/finance/payment-source/${contractPaymentSource.sourceId}`, {
                params: {
                    payment_no: contractPaymentSource.paymentNo,
                    contract_no: contractPaymentSource.contractNo,
                    customer: contractPaymentSource.customer,
                    amount: contractPaymentSource.amount,
                },
            })
            : api.get("/records", { params: { module: "contract_payment", page_size: 100 } });
        setLoading(true);
        setFinanceDataReady(false);
        try {
            if (context.dashboardQueue) {
                const [result, profile, people] = await Promise.all([
                    api.get(isRefundCaseFeeRoute ? "/finance/case-fees/refunds" : "/finance/fees/query", { params: feeQueryParams({}, 1, 15) }),
                    api.get("/auth/me"), api.get("/people/options"),
                ]);
                setFeeQueryRows(result.data.items);
                setCases(result.data.cases);
                setFeeQueryMeta({ total: result.data.total, page: result.data.page, pageSize: result.data.page_size, totals: result.data.totals || {} });
                setFinancePeople(people.data.items || []);
                setRole(profile.data.role);
                setCurrentUser({ username: profile.data.username, displayName: profile.data.display_name });
                return;
            }
            if (initialView === "finance-payment-mine" || initialView === "finance-payment-audit") {
                const paymentRequest = contractPaymentSource.active
                    ? contractPaymentSource.ok
                        ? loadContractPaymentRecords()
                        : Promise.resolve({ data: { items: [] } })
                    : initialView === "finance-payment-audit"
                        ? loadPaymentApprovalApplications()
                        : api.get("/finance/payment-applications/query", {
                        params: { scope: "mine", page: 1, page_size: 100 },
                    });
                const transactionRequest = paymentRequest.then((response) => {
                    const items: Fee[] = contractPaymentSource.active && contractPaymentSource.ok
                        ? [response.data] : response.data.items || [];
                    return loadTransactionsForFees(items);
                });
                const [paymentRes, txRes, profileRes, peopleRes, caseRes] = await Promise.all([
                    paymentRequest,
                    transactionRequest,
                    api.get("/auth/me"),
                    api.get("/people/options"),
                    api.get("/records", { params: { module: "case", page_size: 100 } }),
                ]);
                const paymentItems: Fee[] = contractPaymentSource.active && contractPaymentSource.ok
                    ? [paymentRes.data]
                    : paymentRes.data.items || [];
                const feeItems = paymentItems.filter((item) => item.module === "finance");
                const contractPaymentItems = paymentItems.filter((item) => item.module === "contract_payment");
                setFees(feeItems);
                setFinanceFeeListMeta({
                    page: 1,
                    pageSize: 100,
                    total: feeItems.length,
                });
                setContractPayments(normalizeContractPayments(contractPaymentItems));
                setTransactions(txRes?.data.items || []);
                context.setFinanceTransactionMeta({
                    page: Number(txRes?.data.page || 1),
                    pageSize: Number(txRes?.data.page_size || context.financeTransactionMeta.pageSize),
                    total: Number(txRes?.data.total || txRes?.data.items?.length || 0),
                });
                setRole(profileRes.data.role);
                setCurrentUser({
                    username: profileRes.data.username || "",
                    displayName: profileRes.data.display_name || "",
                });
                setFinancePeople(peopleRes.data.items || []);
                setCases(caseRes.data.items || []);
                return;
            }
            const resources: ReturnType<typeof financeRouteResources> = context.isInternalQueueRoute
                ? ["feeRes", "profileRes", "peopleRes"]
                : financeRouteResources(initialView, selectedTab, context.activeRouteConfig?.source);
            const feeRequest = !resources.includes("feeRes") ? null : context.isInternalQueueRoute
                    ? context.loadInternalQueue(query ?? context.originalQuery)
                    : initialView === "finance-payment-query"
                    ? loadPaymentQueryPage({}, 1, paymentQueryPageSize)
                    : initialView === "finance-internal-mine"
                        ? loadMyInternalApplications()
                    : ["finance-payment-waiting", "finance-payment-print", "finance-payment-writeoff"].includes(initialView)
                        ? api.get("/finance/payment-workflow/list", {params:{stage:initialView.replace("finance-payment-", "")}})
                    : context.financeProjectionEnabled
                        ? api.get("/finance/projection/fees", {
                            params: {
                                page: context.financeFeeListMeta.page,
                                page_size: context.financeFeeListMeta.pageSize,
                                ...projectionFeeParams(initialView, selectedTab),
                            },
                        })
                        : api.get("/records", { params: {
                            module: "finance", page_size: 100,
                            finance_view: initialView.startsWith("finance-payment-") ? "external" : undefined,
                        } });
            const feeQueryRequest = isFeeQueryRoute
                ? api.get(isRefundCaseFeeRoute ? "/finance/case-fees/refunds" : "/finance/fees/query", {
                    params: feeQueryParams(dashboardFeeQuerySeed, 1, 15),
                })
                : null;
            const { feeRes, contractPaymentRes, invoiceRes, refundRes, caseRes, customerRes, incomingRes, txRes, recRes, sumRes, profileRes, settlementRes, refundReviewRes, paymentPackageRes, internalDetailRes, invoiceMineRes, invoicePendingRes, invoiceCompanyRes, invoiceUnissuedRes, generalSettlementRes, archiveSettlementRes, feeQueryRes, peopleRes } = await loadFinanceQueryResources(
                resources, {
                feeRes: () => feeRequest!,
                contractPaymentRes: () => loadContractPaymentRecords(),
                invoiceRes: () => api.get("/records", { params: { module: "invoice", page_size: 100 } }),
                refundRes: () => loadRefunds(1, refundMeta.pageSize, activeRefundStatus, isRefundNotRequiredRoute),
                caseRes: () => api.get("/records", { params: { module: "case", page_size: 100 } }),
                customerRes: () => api.get("/records", { params: { module: "customer", page_size: 100 } }),
                incomingRes: () => context.activeRouteConfig?.source === "incoming"
                    ? context.loadIncomingPayments(context.originalQuery)
                    : api.get("/finance/incoming-payments", { params: { bank_source: receiptBankCode(initialView) } }),
                txRes: () => context.financeProjectionEnabled
                    ? api.get("/finance/projection/transactions", {
                        params: {
                            page: context.financeTransactionMeta.page,
                            page_size: context.financeTransactionMeta.pageSize,
                        },
                    })
                    : context.activeRouteConfig?.source === "feeQuery"
                        ? feeQueryRequest!.then((response) => loadTransactionsForFees(response.data.items || []))
                        : feeRequest!.then((response) => loadTransactionsForFees(response.data.items || [])),
                recRes: () => api.get("/finance/reconciliations"),
                sumRes: () => api.get<FinanceSummary>("/finance/summary"),
                profileRes: () => api.get("/auth/me"),
                settlementRes: () => api.get("/finance/settlements/pending"),
                refundReviewRes: () => api.get("/finance/fees/refund-review-candidates"),
                paymentPackageRes: () => api.get("/finance/payment-packages", {
                    params: paymentPackageRequestParams(initialView, initialView === "finance-internal-writeoff"
                        ? { status: "待核销" }
                        : {}, 1, paymentPackageMeta.pageSize),
                }),
                internalDetailRes: () => api.get("/finance/internal-fees", {
                        params: internalDetailParams(initialView === "finance-internal-detail"
                            ? {
                                routeField7: "全部",
                                routeField9: currentUser.displayName || "",
                            }
                            : { routeField7: "全部" }, 1, 15),
                    }),
                invoiceMineRes: () => api.get("/finance/invoices", {
                        params: invoiceMineParams({}, 1, invoiceLegacyDefaultPageSize(initialView)),
                    }),
                invoicePendingRes: () => api.get("/finance/invoices", {
                        params: invoicePendingParams({}, 1, invoiceLegacyDefaultPageSize(initialView)),
                    }),
                invoiceCompanyRes: () => api.get("/finance/invoices", {
                        params: invoiceCompanyParams({}, 1, invoiceLegacyDefaultPageSize(initialView)),
                    }),
                invoiceUnissuedRes: () => api.get("/finance/case-fees/invoice-status", {
                        params: invoiceUnissuedParams({
                            routeField6: "未开票",
                            routeField12: ["律师代理费"],
                        }, 1, invoiceLegacyDefaultPageSize(initialView)),
                    }),
                generalSettlementRes: () => api.get(isGeneralSettlementPendingRoute
                        ? "/finance/general-settlements/pending"
                        : "/finance/general-settlements/applications", { params: generalSettlementParams({}, 1, 10) }),
                archiveSettlementRes: () => api.get(isArchiveSettlementPaymentRoute
                        ? "/finance/archive-settlements/payment"
                        : isArchiveSettlementPaidRoute
                            ? "/finance/archive-settlements/paid"
                            : isArchiveSettlementRejectedRoute
                                ? "/finance/archive-settlements/rejected"
                                : "/finance/archive-settlements/pending", {
                        params: archiveSettlementParams({}, 1, 10),
                    }),
                feeQueryRes: () => feeQueryRequest!,
                peopleRes: () => api.get("/people/options"),
            });
            if (feeRes) {
                setFees(context.financeProjectionEnabled
                    ? normalizeProjectionFees(feeRes.data.items || [])
                    : (feeRes.data.items || []));
                setFinanceFeeListMeta({
                    page: Number(feeRes.data.page || 1),
                    pageSize: Number(feeRes.data.page_size || context.financeFeeListMeta.pageSize),
                    total: Number(feeRes.data.total || feeRes.data.items?.length || 0),
                });
                if (initialView === "finance-payment-query") {
                    setPaymentQueryMeta({
                        total: Number(feeRes.data.total || 0),
                        page: Number(feeRes.data.page || 1),
                        pageSize: Number(feeRes.data.page_size || paymentQueryPageSize),
                    });
                    setContractPayments([]);
                }
            }
            if (contractPaymentRes) {
                const contractPaymentItems = contractPaymentSource.active && contractPaymentSource.ok
                    ? [contractPaymentRes.data]
                    : contractPaymentRes.data.items || [];
                setContractPayments(normalizeContractPayments(contractPaymentItems));
            }
            if (invoiceRes) setInvoices(invoiceRes.data.items);
            if (refundRes?.applied && refundRes.response) {
                const normalizedRefunds = normalizeRefundResponse(refundRes.response.data, 1, refundMeta.pageSize);
                setRefunds(normalizedRefunds.items);
                setRefundMeta(normalizedRefunds);
                setSelectedRefundRows([]);
            }
            if (caseRes) setCases(caseRes.data.items);
            if (customerRes) setCustomers(customerRes.data.items);
            if (incomingRes && context.activeRouteConfig?.source !== "incoming") {
                setIncoming(incomingRes.data.items);
                setSelectedIncomingRows([]);
            }
            if (resources.includes("txRes")) {
                setTransactions(context.financeProjectionEnabled
                    ? normalizeProjectionTransactions(txRes?.data.items || [])
                    : (txRes?.data.items || []));
                context.setFinanceTransactionMeta({
                    page: Number(txRes?.data.page || 1),
                    pageSize: Number(txRes?.data.page_size || context.financeTransactionMeta.pageSize),
                    total: Number(txRes?.data.total || txRes?.data.items?.length || 0),
                });
            }
            if (recRes) setReconciliations(recRes.data.items);
            if (sumRes) setSummary(sumRes.data);
            if (profileRes) {
                setRole(profileRes.data.role);
                setCurrentUser({
                    username: profileRes.data.username || "",
                    displayName: profileRes.data.display_name || "",
                });
            }
            if (peopleRes) setFinancePeople(peopleRes.data.items || []);
            if (settlementRes) setPendingSettlements(settlementRes.data.items);
            if (refundReviewRes) setRefundReviewFees(refundReviewRes.data.items);
            if (paymentPackageRes) {
                const normalizedPaymentPackages = normalizePaymentPackageResponse(paymentPackageRes.data, 1, paymentPackageMeta.pageSize);
                setPaymentPackages(normalizedPaymentPackages.items);
                setPaymentPackageMeta(normalizedPaymentPackages);
            }
            if (isInternalDetailRoute && internalDetailRes) {
                setInternalDetailRows(internalDetailRes.data.items || []);
                setInternalDetailMeta({
                    total: internalDetailRes.data.total || 0,
                    totalAmount: Number(internalDetailRes.data.total_amount || 0),
                    page: internalDetailRes.data.page || 1,
                    pageSize: internalDetailRes.data.page_size || 15,
                });
            }
            if (isInvoiceMineRoute && invoiceMineRes) {
                setInvoiceMineRows(invoiceMineRes.data.items || []);
                setInvoiceMineMeta({
                    total: invoiceMineRes.data.total || 0,
                    totalAmount: Number(invoiceMineRes.data.total_amount || 0),
                    totalExtraAmount: Number(invoiceMineRes.data.total_extra_amount || 0),
                    page: invoiceMineRes.data.page || 1,
                    pageSize: invoiceMineRes.data.page_size || 15,
                });
            }
            if (isInvoicePendingRoute && invoicePendingRes) {
                setInvoicePendingRows(invoicePendingRes.data.items || []);
                setInvoicePendingMeta({
                    total: invoicePendingRes.data.total || 0,
                    totalAmount: Number(invoicePendingRes.data.total_amount || 0),
                    totalExtraAmount: Number(invoicePendingRes.data.total_extra_amount || 0),
                    page: invoicePendingRes.data.page || 1,
                    pageSize: invoicePendingRes.data.page_size || 15,
                });
            }
            if (isInvoiceCompanyRoute && invoiceCompanyRes) {
                setInvoiceCompanyRows(invoiceCompanyRes.data.items || []);
                setInvoiceCompanyMeta({
                    total: invoiceCompanyRes.data.total || 0,
                    totalAmount: Number(invoiceCompanyRes.data.total_amount || 0),
                    totalExtraAmount: Number(invoiceCompanyRes.data.total_extra_amount || 0),
                    page: invoiceCompanyRes.data.page || 1,
                    pageSize: invoiceCompanyRes.data.page_size || 15,
                });
            }
            if (isInvoiceUnissuedRoute && invoiceUnissuedRes) {
                setInvoiceUnissuedRows(invoiceUnissuedRes.data.items || []);
                setInvoiceUnissuedMeta({
                    total: invoiceUnissuedRes.data.total || 0,
                    totalAmount: Number(invoiceUnissuedRes.data.totals?.amount || 0),
                    totalInvoiceAmount: Number(invoiceUnissuedRes.data.totals?.invoice_amount || 0),
                    totalCashedAmount: Number(invoiceUnissuedRes.data.totals?.cashed_amount || 0),
                    totalPaidAmount: Number(invoiceUnissuedRes.data.totals?.paid_amount || 0),
                    page: invoiceUnissuedRes.data.page || 1,
                    pageSize: invoiceUnissuedRes.data.page_size || 15,
                });
            }
            if (isGeneralSettlementRoute && generalSettlementRes) {
                setGeneralSettlementRows(generalSettlementRes.data.items || []);
                setGeneralSettlementMeta({
                    ...settlementSourceCounts(generalSettlementRes.data),
                    total: generalSettlementRes.data.total || 0,
                    page: generalSettlementRes.data.page || 1,
                    pageSize: generalSettlementRes.data.page_size || 10,
                    totals: generalSettlementRes.data.totals || {},
                });
            }
            if (isArchiveSettlementActiveRoute && archiveSettlementRes) {
                setArchiveSettlementRows(archiveSettlementRes.data.items || []);
                setArchiveSettlementMeta({
                    ...settlementSourceCounts(archiveSettlementRes.data),
                    total: archiveSettlementRes.data.total || 0,
                    page: archiveSettlementRes.data.page || 1,
                    pageSize: archiveSettlementRes.data.page_size || 10,
                    totals: archiveSettlementRes.data.totals || {},
                });
            }
            if (isFeeQueryRoute && feeQueryRes) {
                setFeeQueryRows(feeQueryRes.data.items || []);
                setFeeQueryMeta({
                    total: feeQueryRes.data.total || 0,
                    page: feeQueryRes.data.page || 1,
                    pageSize: feeQueryRes.data.page_size || 15,
                    totals: feeQueryRes.data.totals || {},
                });
            }
        }
        catch (error: unknown) {
            message.error(context.activeRouteConfig?.source === "incoming"
                ? financeErrorDetail(error) || "回款查询失败"
                : initialView === "finance-payment-audit"
                    ? financeErrorDetail(error) || financeErrorMessageText(error) || "请款单审批加载失败"
                    : "财务中心数据加载失败");
        }
        finally {
            setLoading(false);
            setFinanceDataReady(true);
        }
    };
    const load = () => loadForTab(context.tab);
    const loadLegacyFinanceHistory = async (page = context.legacyFinanceMeta.page, pageSize = context.legacyFinanceMeta.pageSize) => {
        const { setLegacyFinanceLoading, legacyFinanceKind, legacyFinanceStatusCode, legacyFinanceKeyword, legacyFinanceIncludeInactive, setLegacyFinanceRows, setLegacyFinanceMeta, setLegacyFinanceSummary } = context;
        setLegacyFinanceLoading(true);
        try {
            const [listRes, summaryRes] = await Promise.all([
                api.get("/finance/legacy-history", {
                    params: {
                        record_kind: legacyFinanceKind,
                        status_code: legacyFinanceStatusCode.trim(),
                        keyword: legacyFinanceKeyword.trim(),
                        include_inactive: legacyFinanceIncludeInactive,
                        page,
                        page_size: pageSize,
                    },
                }),
                api.get("/finance/legacy-history/summary"),
            ]);
            setLegacyFinanceRows(listRes.data.items || []);
            setLegacyFinanceMeta({
                total: Number(listRes.data.total || 0),
                page: Number(listRes.data.page || page),
                pageSize: Number(listRes.data.page_size || pageSize),
            });
            setLegacyFinanceSummary(summaryRes.data);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "导入数据核对加载失败");
        }
        finally {
            setLegacyFinanceLoading(false);
        }
    };
    const openLegacyFinanceDetail = async (recordId: number, source?: Pick<LegacyFinanceRecord, "amount_basis" | "source_label" | "has_local_allocation_activity">) => {
        const { setLegacyFinanceDetailLoading, setLegacyFinanceDetail } = context;
        setLegacyFinanceDetailLoading(true);
        setLegacyFinanceDetail(null);
        try {
            const [{ data }, summary] = await Promise.all([
                api.get(`/finance/legacy-history/${recordId}`),
                api.get<LegacyFinanceSummary>("/finance/legacy-history/summary"),
            ]);
            context.setLegacyFinanceSummary(summary.data);
            setLegacyFinanceDetail(source ? { ...data, ...source } : data);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "导入来源明细加载失败");
        }
        finally {
            setLegacyFinanceDetailLoading(false);
        }
    };
    const exportInternalDetails = async (selectedOnly: boolean) => {
        const { selectedOriginalRows, setInternalDetailExportLoading, internalDetailParams, originalQuery } = context;
        if (selectedOnly && !selectedOriginalRows.length) {
            message.warning("请选择需要导出的费用.");
            return;
        }
        setInternalDetailExportLoading(true);
        try {
            const params: Record<string, any> = {
                ...internalDetailParams(originalQuery, 1, 15),
            };
            delete params.page;
            delete params.page_size;
            if (selectedOnly)
                params.ids = selectedOriginalRows.join(",");
            const response = await api.get("/finance/internal-fees/export", {
                params,
                responseType: "blob",
            });
            const url = URL.createObjectURL(response.data);
            const anchor = document.createElement("a");
            anchor.href = url;
            anchor.download = `内部费用明细-${dayjs().format("YYYY-MM-DD")}.xls`;
            anchor.click();
            URL.revokeObjectURL(url);
            message.success("导出成功.");
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "导出失败");
        }
        finally {
            setInternalDetailExportLoading(false);
        }
    };
    const exportConfiguredRows = async (selectedOnly: boolean) => {
        const { activeRouteConfig, initialView, isInternalDetailRoute, selectedOriginalRows, originalQuery, displayedOriginalTitle, configuredRows, cellValue } = context;
        if (!activeRouteConfig)
            return;
        if (initialView === "finance-receipts-query") {
            if (selectedOnly && !selectedOriginalRows.length) {
                message.warning("请先选择需要导出的回款");
                return;
            }
            try {
                const response = await api.get("/finance/incoming-payments/query/export", {
                    params: {
                        filters: incomingPaymentQueryParams(initialView, originalQuery).filters,
                        ids: selectedOnly ? selectedOriginalRows.join(",") : undefined,
                    }, responseType: "blob",
                });
                const url = URL.createObjectURL(response.data);
                const anchor = document.createElement("a");
                anchor.href = url;
                anchor.download = `到账查询-${dayjs().format("YYYY-MM-DD")}.xls`;
                anchor.click();
                URL.revokeObjectURL(url);
            } catch (error: unknown) {
                message.error(financeErrorDetail(error) || "到账查询导出失败");
            }
            return;
        }
        if (activeRouteConfig.source === "fees" &&
            initialView.startsWith("finance-internal") &&
            !isInternalDetailRoute) {
            if (selectedOnly && !selectedOriginalRows.length) {
                message.warning("请先选择需要导出的费用");
                return;
            }
            try {
                const response = await api.get("/finance/internal-fees/export", {
                    params: internalFeeExportRequestParams({
                        scope: initialView === "finance-internal-mine" ? "applications" : "company",
                        query: originalQuery,
                        ids: selectedOnly ? selectedOriginalRows.map(Number) : [],
                        initialView,
                    }),
                    responseType: "blob",
                });
                const url = URL.createObjectURL(response.data);
                const anchor = document.createElement("a");
                anchor.href = url;
                anchor.download = `${displayedOriginalTitle}-${dayjs().format("YYYY-MM-DD")}.xls`;
                anchor.click();
                URL.revokeObjectURL(url);
            }
            catch (error: any) {
                message.error(error?.response?.data?.detail || "内部费用导出失败");
            }
            return;
        }
        let rows = selectedOnly
            ? configuredRows.filter((row) => selectedOriginalRows.includes(row.id))
            : configuredRows;
        if (activeRouteConfig.source === "incoming" && !selectedOnly) {
            try {
                const response = await api.get<{ items: IncomingPayment[] }>("/finance/incoming-payments", {
                    params: incomingPaymentQueryParams(initialView, originalQuery),
                });
                rows = response.data.items;
            } catch (error: unknown) {
                message.error(financeErrorDetail(error) || "回款导出失败");
                return;
            }
        }
        if (!rows.length) {
            message.warning(selectedOnly ? "请先选择需要导出的记录" : "当前没有可导出的记录");
            return;
        }
        const headers = activeRouteConfig.headers.filter((header) => header !== "操作");
        const escapeCsv = (value: unknown) => `"${String(value ?? "").replaceAll('"', '""')}"`;
        const csv = [
            headers.map(escapeCsv).join(","),
            ...rows.map((row) => headers.map((header) => escapeCsv(cellValue(row, header))).join(",")),
        ].join("\r\n");
        const url = URL.createObjectURL(new Blob(["\ufeff", csv], { type: "text/csv;charset=utf-8" }));
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = `${displayedOriginalTitle}.csv`;
        anchor.click();
        URL.revokeObjectURL(url);
    };
    return { openCaseDetail, openContractDetail, openCustomerDetail, loadInternalDetails, loadFinanceProjectionPage, load, loadForTab, loadLegacyFinanceHistory, openLegacyFinanceDetail, exportInternalDetails, exportConfiguredRows };
}
