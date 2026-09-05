import { message } from "antd";
import type { AxiosResponse } from "axios";
import dayjs from "dayjs";
import { api } from "../../api";
import { rememberCaseDetailTarget } from "../../caseDetailNavigation";
import { rememberContractDetailTarget } from "../../contractDetailNavigation";
import { rememberCustomerDetailTarget } from "../../customerDetailNavigation";
import { internalFeeExportRequestParams } from "../../financeInternalFeeHelpers.mjs";
import { normalizeRefundResponse } from "../../financeRefundHelpers.mjs";
import { invoiceLegacyDefaultPageSize, normalizePaymentPackageResponse, paymentPackageRequestParams } from "../constants";
import type { ContractPaymentSourceState, Fee, FinancePersonOption, IncomingPayment, LegacyFinanceRecord, LegacyFinanceSummary, Receivable, Reconciliation, Transaction } from "../types";
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
/** finance queries operations; dependencies are read when each operation runs. */
export interface FinanceQueriesDependencies {
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
    readonly setFees: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setFinanceFeeListMeta: React.Dispatch<React.SetStateAction<{
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
    readonly setReceivables: React.Dispatch<React.SetStateAction<Receivable[]>>;
    readonly setIncoming: React.Dispatch<React.SetStateAction<IncomingPayment[]>>;
    readonly setSelectedIncomingRows: React.Dispatch<React.SetStateAction<number[]>>;
    readonly setTransactions: React.Dispatch<React.SetStateAction<Transaction[]>>;
    readonly setReconciliations: React.Dispatch<React.SetStateAction<Reconciliation[]>>;
    readonly setSummary: React.Dispatch<any>;
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
    readonly setGeneralSettlementRows: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly setGeneralSettlementMeta: React.Dispatch<React.SetStateAction<{
        total: number;
        page: number;
        pageSize: number;
        totals: Record<string, number>;
    }>>;
    readonly setArchiveSettlementRows: React.Dispatch<React.SetStateAction<any[]>>;
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
        const { internalDetailMeta, internalDetailParams, setInternalDetailRows, setInternalDetailMeta } = context;
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
    const load = async () => {
        const { setLoading, setFinanceDataReady, initialView, loadPaymentQueryPage, paymentQueryPageSize, contractPaymentSource, loadRefunds, refundMeta, activeRefundStatus, isRefundNotRequiredRoute, paymentPackageMeta, isInternalDetailRoute, internalDetailParams, currentUser, isInvoiceMineRoute, invoiceMineParams, isInvoicePendingRoute, invoicePendingParams, isInvoiceCompanyRoute, invoiceCompanyParams, isInvoiceUnissuedRoute, invoiceUnissuedParams, isGeneralSettlementRoute, isGeneralSettlementPendingRoute, generalSettlementParams, isArchiveSettlementActiveRoute, isArchiveSettlementPaymentRoute, isArchiveSettlementPaidRoute, isArchiveSettlementRejectedRoute, archiveSettlementParams, isFeeQueryRoute, isRefundCaseFeeRoute, feeQueryParams, dashboardFeeQuerySeed, setFees, setFinanceFeeListMeta, setPaymentQueryMeta, setContractPayments, setInvoices, setRefunds, setRefundMeta, setSelectedRefundRows, setCases, setCustomers, setReceivables, setIncoming, setSelectedIncomingRows, setTransactions, setReconciliations, setSummary, setRole, setCurrentUser, setFinancePeople, setPendingSettlements, setRefundReviewFees, setPaymentPackages, setPaymentPackageMeta, setInternalDetailRows, setInternalDetailMeta, setInvoiceMineRows, setInvoiceMineMeta, setInvoicePendingRows, setInvoicePendingMeta, setInvoiceCompanyRows, setInvoiceCompanyMeta, setInvoiceUnissuedRows, setInvoiceUnissuedMeta, setGeneralSettlementRows, setGeneralSettlementMeta, setArchiveSettlementRows, setArchiveSettlementMeta, setFeeQueryRows, setFeeQueryMeta } = context;
        setLoading(true);
        setFinanceDataReady(false);
        try {
            const [feeRes, contractPaymentRes, invoiceRes, refundRes, caseRes, customerRes, receivableRes, incomingRes, txRes, recRes, sumRes, profileRes, settlementRes, refundReviewRes, paymentPackageRes, internalDetailRes, invoiceMineRes, invoicePendingRes, invoiceCompanyRes, invoiceUnissuedRes, generalSettlementRes, archiveSettlementRes, feeQueryRes, peopleRes,] = await Promise.all([
                initialView === "finance-payment-query"
                    ? loadPaymentQueryPage({}, 1, paymentQueryPageSize)
                    : api.get("/records", { params: { module: "finance", page_size: 100 } }),
                initialView === "finance-payment-query"
                    ? Promise.resolve({
                        data: {
                            items: [],
                            total: 0,
                            page: 1,
                            page_size: paymentQueryPageSize,
                        },
                    })
                    : contractPaymentSource.active && contractPaymentSource.ok
                        ? api.get(`/finance/payment-source/${contractPaymentSource.sourceId}`, {
                            params: {
                                payment_no: contractPaymentSource.paymentNo,
                                contract_no: contractPaymentSource.contractNo,
                                customer: contractPaymentSource.customer,
                                amount: contractPaymentSource.amount,
                            },
                        })
                        : api.get("/records", { params: { module: "contract_payment", page_size: 100 } }),
                api.get("/records", { params: { module: "invoice", page_size: 100 } }),
                loadRefunds(1, refundMeta.pageSize, activeRefundStatus, isRefundNotRequiredRoute),
                api.get("/records", { params: { module: "case", page_size: 100 } }),
                api.get("/records", { params: { module: "customer", page_size: 100 } }),
                api.get("/receivables"),
                api.get("/finance/incoming-payments"),
                api.get("/finance/transactions"),
                api.get("/finance/reconciliations"),
                api.get("/finance/summary"),
                api.get("/auth/me"),
                api.get("/finance/settlements/pending"),
                api.get("/finance/fees/refund-review-candidates"),
                api.get("/finance/payment-packages", {
                    params: paymentPackageRequestParams(initialView, initialView === "finance-internal-writeoff"
                        ? { status: "待核销" }
                        : {}, 1, paymentPackageMeta.pageSize),
                }),
                isInternalDetailRoute
                    ? api.get("/finance/internal-fees", {
                        params: internalDetailParams(initialView === "finance-internal-detail"
                            ? {
                                routeField7: "全部",
                                routeField9: currentUser.displayName || "姓名待维护",
                            }
                            : { routeField7: "全部" }, 1, 15),
                    })
                    : Promise.resolve({
                        data: {
                            items: [],
                            total: 0,
                            total_amount: 0,
                            page: 1,
                            page_size: 15,
                        },
                    }),
                isInvoiceMineRoute
                    ? api.get("/finance/invoices", {
                        params: invoiceMineParams({}, 1, invoiceLegacyDefaultPageSize(initialView)),
                    })
                    : Promise.resolve({
                        data: {
                            items: [],
                            total: 0,
                            total_amount: 0,
                            total_extra_amount: 0,
                            page: 1,
                            page_size: invoiceLegacyDefaultPageSize(initialView),
                        },
                    }),
                isInvoicePendingRoute
                    ? api.get("/finance/invoices", {
                        params: invoicePendingParams({}, 1, invoiceLegacyDefaultPageSize(initialView)),
                    })
                    : Promise.resolve({
                        data: {
                            items: [],
                            total: 0,
                            total_amount: 0,
                            total_extra_amount: 0,
                            page: 1,
                            page_size: invoiceLegacyDefaultPageSize(initialView),
                        },
                    }),
                isInvoiceCompanyRoute
                    ? api.get("/finance/invoices", {
                        params: invoiceCompanyParams({}, 1, invoiceLegacyDefaultPageSize(initialView)),
                    })
                    : Promise.resolve({
                        data: {
                            items: [],
                            total: 0,
                            total_amount: 0,
                            total_extra_amount: 0,
                            page: 1,
                            page_size: invoiceLegacyDefaultPageSize(initialView),
                        },
                    }),
                isInvoiceUnissuedRoute
                    ? api.get("/finance/case-fees/invoice-status", {
                        params: invoiceUnissuedParams({
                            routeField6: "未开票",
                            routeField12: ["律师代理费"],
                        }, 1, invoiceLegacyDefaultPageSize(initialView)),
                    })
                    : Promise.resolve({
                        data: {
                            items: [],
                            total: 0,
                            totals: {},
                            page: 1,
                            page_size: invoiceLegacyDefaultPageSize(initialView),
                        },
                    }),
                isGeneralSettlementRoute
                    ? api.get(isGeneralSettlementPendingRoute
                        ? "/finance/general-settlements/pending"
                        : "/finance/general-settlements/applications", { params: generalSettlementParams({}, 1, 10) })
                    : Promise.resolve({
                        data: { items: [], total: 0, totals: {}, page: 1, page_size: 10 },
                    }),
                isArchiveSettlementActiveRoute
                    ? api.get(isArchiveSettlementPaymentRoute
                        ? "/finance/archive-settlements/payment"
                        : isArchiveSettlementPaidRoute
                            ? "/finance/archive-settlements/paid"
                            : isArchiveSettlementRejectedRoute
                                ? "/finance/archive-settlements/rejected"
                                : "/finance/archive-settlements/pending", {
                        params: archiveSettlementParams({}, 1, 10),
                    })
                    : Promise.resolve({
                        data: { items: [], total: 0, totals: {}, page: 1, page_size: 10 },
                    }),
                isFeeQueryRoute
                    ? api.get(isRefundCaseFeeRoute ? "/finance/case-fees/refunds" : "/finance/fees/query", {
                        params: feeQueryParams(dashboardFeeQuerySeed, 1, 15),
                    })
                    : Promise.resolve({
                        data: { items: [], total: 0, totals: {}, page: 1, page_size: 15 },
                    }),
                api.get("/people/options").catch(() => ({ data: { items: [] } })),
            ]);
            setFees(feeRes.data.items);
            setFinanceFeeListMeta({
                page: Number(feeRes.data.page || 1),
                pageSize: Number(feeRes.data.page_size || 100),
                total: Number(feeRes.data.total || feeRes.data.items?.length || 0),
            });
            if (initialView === "finance-payment-query") {
                setPaymentQueryMeta({
                    total: Number(feeRes.data.total || 0),
                    page: Number(feeRes.data.page || 1),
                    pageSize: Number(feeRes.data.page_size || paymentQueryPageSize),
                });
            }
            const contractPaymentItems = contractPaymentSource.active && contractPaymentSource.ok
                ? [contractPaymentRes.data]
                : contractPaymentRes.data.items || [];
            setContractPayments(contractPaymentItems.map((item: Fee) => ({
                ...item,
                data: {
                    ...(item.data || {}),
                    _source_module: "contract_payment",
                    fee_type: item.data?.lines?.[0]?.fee_type || item.data?.payment_type,
                    case_no: item.data?.lines?.[0]?.case_no,
                    amount: item.data?.amount,
                },
            })));
            setInvoices(invoiceRes.data.items);
            if (refundRes?.applied && refundRes.response) {
                const normalizedRefunds = normalizeRefundResponse(refundRes.response.data, 1, refundMeta.pageSize);
                setRefunds(normalizedRefunds.items);
                setRefundMeta(normalizedRefunds);
                setSelectedRefundRows([]);
            }
            setCases(caseRes.data.items);
            setCustomers(customerRes.data.items);
            setReceivables(receivableRes.data.items);
            setIncoming(incomingRes.data.items);
            setSelectedIncomingRows([]);
            setTransactions(txRes.data.items);
            setReconciliations(recRes.data.items);
            setSummary(sumRes.data);
            setRole(profileRes.data.role);
            setCurrentUser({
                username: profileRes.data.username || "",
                displayName: profileRes.data.display_name || "",
            });
            setFinancePeople(peopleRes.data.items || []);
            setPendingSettlements(settlementRes.data.items);
            setRefundReviewFees(refundReviewRes.data.items);
            const normalizedPaymentPackages = normalizePaymentPackageResponse(paymentPackageRes.data, 1, paymentPackageMeta.pageSize);
            setPaymentPackages(normalizedPaymentPackages.items);
            setPaymentPackageMeta(normalizedPaymentPackages);
            if (isInternalDetailRoute) {
                setInternalDetailRows(internalDetailRes.data.items || []);
                setInternalDetailMeta({
                    total: internalDetailRes.data.total || 0,
                    totalAmount: Number(internalDetailRes.data.total_amount || 0),
                    page: internalDetailRes.data.page || 1,
                    pageSize: internalDetailRes.data.page_size || 15,
                });
            }
            if (isInvoiceMineRoute) {
                setInvoiceMineRows(invoiceMineRes.data.items || []);
                setInvoiceMineMeta({
                    total: invoiceMineRes.data.total || 0,
                    totalAmount: Number(invoiceMineRes.data.total_amount || 0),
                    totalExtraAmount: Number(invoiceMineRes.data.total_extra_amount || 0),
                    page: invoiceMineRes.data.page || 1,
                    pageSize: invoiceMineRes.data.page_size || 15,
                });
            }
            if (isInvoicePendingRoute) {
                setInvoicePendingRows(invoicePendingRes.data.items || []);
                setInvoicePendingMeta({
                    total: invoicePendingRes.data.total || 0,
                    totalAmount: Number(invoicePendingRes.data.total_amount || 0),
                    totalExtraAmount: Number(invoicePendingRes.data.total_extra_amount || 0),
                    page: invoicePendingRes.data.page || 1,
                    pageSize: invoicePendingRes.data.page_size || 15,
                });
            }
            if (isInvoiceCompanyRoute) {
                setInvoiceCompanyRows(invoiceCompanyRes.data.items || []);
                setInvoiceCompanyMeta({
                    total: invoiceCompanyRes.data.total || 0,
                    totalAmount: Number(invoiceCompanyRes.data.total_amount || 0),
                    totalExtraAmount: Number(invoiceCompanyRes.data.total_extra_amount || 0),
                    page: invoiceCompanyRes.data.page || 1,
                    pageSize: invoiceCompanyRes.data.page_size || 15,
                });
            }
            if (isInvoiceUnissuedRoute) {
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
            if (isGeneralSettlementRoute) {
                setGeneralSettlementRows(generalSettlementRes.data.items || []);
                setGeneralSettlementMeta({
                    total: generalSettlementRes.data.total || 0,
                    page: generalSettlementRes.data.page || 1,
                    pageSize: generalSettlementRes.data.page_size || 10,
                    totals: generalSettlementRes.data.totals || {},
                });
            }
            if (isArchiveSettlementActiveRoute) {
                setArchiveSettlementRows(archiveSettlementRes.data.items || []);
                setArchiveSettlementMeta({
                    total: archiveSettlementRes.data.total || 0,
                    page: archiveSettlementRes.data.page || 1,
                    pageSize: archiveSettlementRes.data.page_size || 10,
                    totals: archiveSettlementRes.data.totals || {},
                });
            }
            if (isFeeQueryRoute) {
                setFeeQueryRows(feeQueryRes.data.items || []);
                setFeeQueryMeta({
                    total: feeQueryRes.data.total || 0,
                    page: feeQueryRes.data.page || 1,
                    pageSize: feeQueryRes.data.page_size || 15,
                    totals: feeQueryRes.data.totals || {},
                });
            }
        }
        catch {
            message.error("财务中心数据加载失败");
        }
        finally {
            setLoading(false);
            setFinanceDataReady(true);
        }
    };
    const loadLegacyFinanceHistory = async (page = context.legacyFinanceMeta.page, pageSize = context.legacyFinanceMeta.pageSize) => {
        const { legacyFinanceMeta, setLegacyFinanceLoading, legacyFinanceKind, legacyFinanceStatusCode, legacyFinanceKeyword, legacyFinanceIncludeInactive, setLegacyFinanceRows, setLegacyFinanceMeta, setLegacyFinanceSummary } = context;
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
            message.error(error?.response?.data?.detail || "历史财务账本加载失败");
        }
        finally {
            setLegacyFinanceLoading(false);
        }
    };
    const openLegacyFinanceDetail = async (recordId: number) => {
        const { setLegacyFinanceDetailLoading, setLegacyFinanceDetail } = context;
        setLegacyFinanceDetailLoading(true);
        setLegacyFinanceDetail(null);
        try {
            const { data } = await api.get(`/finance/legacy-history/${recordId}`);
            setLegacyFinanceDetail(data);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "历史财务明细加载失败");
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
                        scope: initialView === "finance-internal-mine" ? "mine" : "company",
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
        const rows = selectedOnly
            ? configuredRows.filter((row) => selectedOriginalRows.includes(row.id))
            : configuredRows;
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
    return { openCaseDetail, openContractDetail, openCustomerDetail, loadInternalDetails, load, loadLegacyFinanceHistory, openLegacyFinanceDetail, exportInternalDetails, exportConfiguredRows };
}
