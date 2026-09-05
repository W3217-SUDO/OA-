import type { OriginalRouteConfig } from "../types";
import { Button, message } from "antd";
import type { Fee, IncomingPayment } from "../types";
export function createConfiguredColumns(context: {
    readonly activeRouteConfig: OriginalRouteConfig;
    readonly initialView: string;
    readonly settlementColumnWidths: number[];
    readonly isGeneralSettlementRoute: boolean;
    readonly generalSettlementColumnWidths: number[];
    readonly isArchiveSettlementRejectedRoute: boolean;
    readonly archiveSettlementRejectedColumnWidths: number[];
    readonly isArchiveSettlementActiveRoute: boolean;
    readonly archiveSettlementColumnWidths: number[];
    readonly isInvoiceUnissuedRoute: boolean;
    readonly invoiceUnissuedColumnWidths: number[];
    readonly internalListColumnWidths: number[];
    readonly isInvoiceCompanyRoute: boolean;
    readonly internalListOperation: (_: unknown, row: Fee) => React.JSX.Element | null;
    readonly isInvoiceMineRoute: boolean;
    readonly invoiceMineOperation: (_: unknown, row: Fee) => React.JSX.Element;
    readonly isInvoicePendingRoute: boolean;
    readonly invoicePendingOperation: (_: unknown, row: Fee) => React.JSX.Element;
    readonly invoiceCompanyOperation: (_: unknown, row: Fee) => React.JSX.Element;
    readonly originalInvoiceOperation: (_: unknown, row: Fee) => React.JSX.Element;
    readonly originalIncomingOperation: (_: unknown, r: IncomingPayment) => React.JSX.Element;
    readonly generalSettlementOperation: (_: unknown, row: Fee) => React.JSX.Element;
    readonly archiveSettlementPendingOperation: (_: unknown, row: any) => React.JSX.Element;
    readonly paymentPackageOperation: (_: unknown, row: Fee) => React.JSX.Element;
    readonly isRefundCaseFeeRoute: boolean;
    readonly refundCaseFeeOperation: (_: unknown, row: Fee) => React.JSX.Element;
    readonly originalOperation: (_: unknown, row: Fee) => React.JSX.Element;
    readonly setFeeDetail: React.Dispatch<React.SetStateAction<Fee | null>>;
    readonly cellValue: (row: any, header: string) => any;
    readonly openCaseDetail: (caseNo: unknown) => Promise<void>;
    readonly invoices: Fee[];
    readonly openRecordFiles: (row: Fee, category: string, targets?: Fee[]) => Promise<void>;
    readonly isInternalDetailRoute: boolean;
    readonly isFeeQueryRoute: boolean;
    readonly openFinanceCustomerDetail: (row: any, header: string) => void;
    readonly openContractDetail: (contractNo: unknown) => Promise<void>;
    readonly openInvoiceProcess: (row: Fee) => void;
    readonly openInvoiceDetail: (row: Fee) => Promise<void>;
    readonly openPaymentPackageDetail: (row: Fee) => Promise<void>;
}) {
    return context.activeRouteConfig?.headers.map((header, index) => ({
        title: header.includes("/") ? (<span className="finance-stacked-header">
        {header.split("/").map((part) => (<span key={part}>{part}</span>))}
      </span>) : (header),
        key: `${header}-${index}`,
        width: context.initialView === "finance-internal-settle"
            ? context.settlementColumnWidths[index]
            : context.isGeneralSettlementRoute
                ? context.generalSettlementColumnWidths[index]
                : context.isArchiveSettlementRejectedRoute
                    ? context.archiveSettlementRejectedColumnWidths[index]
                    : context.isArchiveSettlementActiveRoute
                        ? context.archiveSettlementColumnWidths[index]
                        : context.isInvoiceUnissuedRoute
                            ? context.invoiceUnissuedColumnWidths[index]
                            : [
                                "finance-internal-refused",
                                "finance-internal-void",
                                "finance-internal-query",
                            ].includes(context.initialView)
                                ? context.internalListColumnWidths[index]
                                : header === "操作"
                                    ? context.isInvoiceCompanyRoute
                                        ? 280
                                        : 145
                                    : Math.max(90, Math.min(190, header.length * 17 + 45)),
        fixed: header === "操作" &&
            ![
                "finance-internal-refused",
                "finance-internal-void",
                "finance-internal-query",
                "finance-settlement-pending",
                "finance-settlement-audit",
                "finance-archive-fee-pending",
                "finance-archive-fee-payment",
                "finance-archive-fee-paid",
                "finance-archive-fee-refused",
            ].includes(context.initialView)
            ? ("left" as const)
            : undefined,
        render: (_: unknown, row: any) => header === "" ? null : header === "操作" ? ([
            "finance-internal-refused",
            "finance-internal-void",
            "finance-internal-query",
        ].includes(context.initialView) ? (context.internalListOperation(_, row)) : context.activeRouteConfig?.source === "invoices" ? (context.isInvoiceMineRoute
            ? context.invoiceMineOperation(_, row)
            : context.isInvoicePendingRoute
                ? context.invoicePendingOperation(_, row)
                : context.isInvoiceCompanyRoute
                    ? context.invoiceCompanyOperation(_, row)
                    : context.originalInvoiceOperation(_, row)) : context.activeRouteConfig?.source === "incoming" ? (context.originalIncomingOperation(_, row)) : context.activeRouteConfig?.source === "generalSettlements" ? (context.generalSettlementOperation(_, row)) : context.activeRouteConfig?.source === "archiveSettlements" ? (context.archiveSettlementPendingOperation(_, row)) : context.activeRouteConfig?.source === "paymentPackages" ? (context.paymentPackageOperation(_, row)) : context.isRefundCaseFeeRoute ? (context.refundCaseFeeOperation(_, row)) : (context.originalOperation(_, row))) : [
            "finance-internal-refused",
            "finance-internal-void",
            "finance-internal-query",
        ].includes(context.initialView) && header === "请款单号" ? (<Button type="link" onClick={() => context.setFeeDetail(row)}>
          {context.cellValue(row, header)}
        </Button>) : [
            "finance-internal-refused",
            "finance-internal-void",
            "finance-internal-query",
        ].includes(context.initialView) && header === "案件编号" ? (context.cellValue(row, header) ? <Button type="link" onClick={() => context.openCaseDetail(context.cellValue(row, header))}>{context.cellValue(row, header)}</Button> : "—") : context.initialView === "finance-internal-settle" && header === "案号" ? (context.cellValue(row, header) ? <Button type="link" onClick={() => context.openCaseDetail(context.cellValue(row, header))}>{context.cellValue(row, header)}</Button> : "—") : context.isInvoiceUnissuedRoute && header === "案号" ? (context.cellValue(row, header) ? <Button type="link" onClick={() => context.openCaseDetail(context.cellValue(row, header))}>{context.cellValue(row, header)}</Button> : "—") : context.isInvoiceUnissuedRoute && header === "发票查看" ? (row.data?.invoice_no ? (<Button type="link" onClick={() => {
                const invoice = context.invoices.find((item) => item.id === Number(row.data?.invoice_record_id || 0));
                if (invoice)
                    void context.openRecordFiles(invoice, "发票扫描件");
                else
                    message.warning("关联发票记录不存在或无权访问");
            }}>
            {row.data.invoice_no}
          </Button>) : null) : context.isInternalDetailRoute && header === "案号" ? (context.cellValue(row, header) ? <Button type="link" onClick={() => context.openCaseDetail(context.cellValue(row, header))}>{context.cellValue(row, header)}</Button> : "—") : context.isArchiveSettlementActiveRoute && header === "案号" ? (context.cellValue(row, header) ? <Button type="link" onClick={() => context.openCaseDetail(context.cellValue(row, header))}>{context.cellValue(row, header)}</Button> : "—") : context.isFeeQueryRoute && ["案号", "案件编号"].includes(header) ? (context.cellValue(row, header) ? <Button type="link" onClick={() => context.openCaseDetail(context.cellValue(row, header))}>{context.cellValue(row, header)}</Button> : "—") : ["客户", "客户名称", "客户编号"].includes(header) ? (context.cellValue(row, header) ? <Button type="link" onClick={() => context.openFinanceCustomerDetail(row, header)}>
          {context.cellValue(row, header)}
        </Button> : "—") : ["合同号", "合同编号"].includes(header) ? (context.cellValue(row, header) ? <Button type="link" onClick={() => context.openContractDetail(context.cellValue(row, header))}>{context.cellValue(row, header)}</Button> : "—") : (context.isInvoiceMineRoute || context.isInvoicePendingRoute || context.isInvoiceCompanyRoute) && header === "请票单号" ? (<Button type="link" onClick={() => context.isInvoicePendingRoute
                ? context.openInvoiceProcess(row)
                : void context.openInvoiceDetail(row)}>
          {context.cellValue(row, header)}
        </Button>) : context.initialView === "finance-internal-payment" &&
            header === "案件编号" ? (context.cellValue(row, header) ? <Button type="link" onClick={() => context.openCaseDetail(context.cellValue(row, header))}>{context.cellValue(row, header)}</Button> : "—") : context.activeRouteConfig?.source === "paymentPackages" &&
            header === "付款包号码" ? (<Button type="link" onClick={() => void context.openPaymentPackageDetail(row)}>
          {context.cellValue(row, header)}
        </Button>) : (context.cellValue(row, header)),
    }));
}
