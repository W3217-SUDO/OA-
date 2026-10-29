import {IncomingTotalsBody} from "./IncomingTotalsBody";
import { isHistoricalSettlement } from "./settlementIdentity";
import type { SettlementRow } from "./types";

import {financeErrorDetail} from "./financeErrors";

import {Alert, Button, Dropdown, Input, Space, message} from "antd";
import Table from "../components/ResizableTable";
import type { FitStackGroup, FitStackState } from "../components/ResizableTable";
import { columnIds, layoutTotalCells, takeTotalsStack } from "../components/stackedTotals";
import dayjs from "dayjs";

import {FinanceOriginalQueryView, type FinanceOriginalQueryViewProps} from "./FinanceOriginalQueryView";

import {GeneralSettlementExpandedRow} from "./GeneralSettlementExpandedRow";
import {FeeQueryPageSummary, FeeQueryTotalBody, InternalQueueSummary, PaymentPackagePageSummary, PaymentPackageTotalBody, PaymentQueryPageSummary, PaymentQueryTotalBody} from "./FinanceOriginalTotals";
import {FinanceFeeQueryActions} from "./FinanceFeeQueryActions";

import type {ComponentProps} from "react";

import {RefundCaseFeeOperationMenu, RefundCaseFeeMarkButton, type RefundCaseFeeOperationMenuProps, type RefundCaseFeeMarkButtonProps} from "./RefundCaseFeeActions";
import {internalApprovalRoutes, paymentPackagePageSizeOptions, paymentQueryControlledPageSize, paymentQueryDefaultPageSize, paymentQueryPageSizeOptions, paymentQueryQuickJumper, paymentQueryShowsSinglePageGo} from "./constants";
import type {ArchiveSettlementTarget, Fee, FinancePageMeta, FinanceAmountPageMeta, FinanceInternalQueueMeta, FinanceInvoicePageMeta, FinanceUnissuedPageMeta, FinanceSettlementPageMeta, FinanceFeeQueryMeta, OriginalFinanceRow, OriginalRouteConfig} from "./types";

// 财务列表一屏放不下时，把相关的金额/日期/人员列叠放在一个单元格里（数据不减少）；屏幕够宽时仍逐列显示。
// 合计行会跟着同样叠放（见 stackedTotals），未适配的合计行所在路由由 fitStackAware 阻止叠放。
function incomingFitStack(columns: any[]): FitStackGroup[] | undefined {
  const keyOf = (header: string) => {
    const column = columns.find((item) => String(item.key).startsWith(`${header}-`) || (item.key === undefined && item.dataIndex === undefined && item.title === header));
    return column ? (column.key ?? column.title) as string : undefined;
  };
  const group = (title: string, headers: string[], labels?: string[]): FitStackGroup | null => {
    const keys = headers.map(keyOf);
    return keys.every(Boolean) ? { title, keys: keys as string[], labels } : null;
  };
  // 不带行内标签的分组用两行表头说明上下两行各是什么。
  const pair = (headers: [string, string]) => {
    const item = group(headers.join("/"), headers);
    return item && { ...item, title: <span>{headers[0]}<br />{headers[1]}</span> };
  };
  const groups = [
    group("回款金额", ["回款金额", "已分金额", "未分金额"], ["回款", "已分", "未分"]),
    group("已分费用", ["已分官费", "已分代理费", "已分其他费用"], ["官费", "代理费", "其他"]),
    group("日期", ["申请日期", "截止日期"], ["申请", "截止"]),
    group("人员", ["申请人", "客户管理人", "交款人"], ["申请", "管理", "交款"]),
    group("开票金额", ["开票金额", "高开金额"], ["开票", "高开"]),
    group("人员", ["申请人", "领票人"], ["申请", "领票"]),
    group("开票", ["开票日期", "开票金额"], ["日期", "金额"]),
    group("到账", ["到账时间", "到账金额", "到账单位"], ["时间", "金额", "单位"]),
    group("到账", ["到账时间", "到账金额"], ["时间", "金额"]),
    group("付款", ["付款时间", "付款金额"], ["时间", "金额"]),
    group("日期", ["申请日期", "审核日期"], ["申请", "审核"]),
    group("提成", ["基数", "参考提成", "实际提成"], ["基数", "参考", "实际"]),
    group("结算", ["代理费结算金额", "扣归档费", "实际结算金额"], ["结算", "扣归档", "实际"]),
    pair(["开票抬头", "发票号码"]),
    pair(["助理", "开庭律师"]),
    pair(["法院案号", "法院名称"]),
    pair(["案件阶段", "付款状态"]),
    pair(["客户名称", "客户管理人"]),
  ].filter((item): item is FitStackGroup => Boolean(item));
  // 同一列只进一个分组，先出现的分组优先。
  const used = new Set<string>();
  const distinct = groups.filter((item) => {
    if (item.keys.some((key) => used.has(key))) return false;
    item.keys.forEach((key) => used.add(key));
    return true;
  });
  return distinct.length ? distinct : undefined;
}

export interface FinanceOriginalRoutesViewProps {
  originalQueryView: FinanceOriginalQueryViewProps;
  initialView: string;
  originalKind: string;
  isInvoiceMineRoute: boolean;
  isInvoicePendingRoute: boolean;
  isInvoiceCompanyRoute: boolean;
  isInvoiceUnissuedRoute: boolean;
  isGeneralSettlementRoute: boolean;
  isGeneralSettlementPaidRoute: boolean;
  isGeneralSettlementRejectedRoute: boolean;
  isGeneralSettlementAuditRoute: boolean;
  isGeneralSettlementPaymentRoute: boolean;
  isArchiveSettlementActiveRoute: boolean;
  isArchiveSettlementPaidRoute: boolean;
  isArchiveSettlementRejectedRoute: boolean;
  isArchiveSettlementPaymentRoute: boolean;
  isFeeQueryRoute: boolean;
  isInternalDetailRoute: boolean;
  isInternalApprovalRoute: boolean;
  isInternalQueueRoute?: boolean;
  internalQueueMeta?: FinanceInternalQueueMeta;
  internalQueueError?: string | null;
  loadInternalQueue?: (query: Record<string, unknown>, page?: number, pageSize?: number) => Promise<unknown>;
  isRefundCaseFeeRoute: boolean;
  activeRouteConfig: OriginalRouteConfig | undefined;
  loading: boolean;
  paymentPackageLoading: boolean;
  invoiceExportLoading: boolean;
  feeQueryExportLoading: boolean;
  settlementActionLoading: boolean;
  generalSettlementBusy: boolean;
  archiveSettlementBusy: boolean;
  internalDetailExportLoading: boolean;
  canManage: boolean;
  canApprove: boolean;
  originalColumns: any[];
  paymentOriginalColumns: any[];
  configuredRows: OriginalFinanceRow[];
  selectedOriginalRows: (string | number)[];
  setSelectedOriginalRows: (keys: (string | number)[]) => void;
  paymentQueryMeta: FinancePageMeta;
  paymentQueryPageSize: number;
  setPaymentQueryPageSize: (size: number) => void;
  paymentAuditPageSize: number;
  setPaymentAuditPageSize: (size: number) => void;
  localListPage?: { page: number; pageSize: number };
  setLocalListPage?: (value: { page: number; pageSize: number }) => void;
  paymentQueryQuickPage: string;
  setPaymentQueryQuickPage: (value: string) => void;
  feeQueryMeta: FinanceFeeQueryMeta;
  paymentPackageMeta: FinancePageMeta;
  invoiceMineMeta: FinanceInvoicePageMeta;
  invoicePendingMeta: FinanceInvoicePageMeta;
  invoiceCompanyMeta: FinanceInvoicePageMeta;
  invoiceUnissuedMeta: FinanceUnissuedPageMeta;
  generalSettlementMeta: FinanceSettlementPageMeta;
  archiveSettlementMeta: FinanceSettlementPageMeta;
  internalDetailMeta: FinanceAmountPageMeta;
  incomingMeta: FinancePageMeta & { totals: Record<string, number | null> };
  loadIncomingPayments: (query: Record<string, unknown>, page?: number, pageSize?: number) => Promise<unknown>;
  originalQuery: Record<string, unknown>;
  submitPaymentQueryQuickPage: () => void;
  refreshPaymentQueryPage: (page: number, pageSize: number) => void;
  loadPaymentPackages: (query: Record<string, unknown>, page: number, pageSize: number) => Promise<unknown>;
  loadFeeQuery: (query: Record<string, unknown>, page: number, pageSize: number) => Promise<unknown>;
  loadInvoiceMine: (query: Record<string, unknown>, page: number, pageSize: number) => Promise<unknown>;
  loadInvoicePending: (query: Record<string, unknown>, page: number, pageSize: number) => Promise<unknown>;
  loadInvoiceCompany: (query: Record<string, unknown>, page: number, pageSize: number) => Promise<unknown>;
  loadInvoiceUnissued: (query: Record<string, unknown>, page: number, pageSize: number) => Promise<unknown>;
  loadGeneralSettlements: (query: Record<string, unknown>, page: number, pageSize: number) => Promise<unknown>;
  loadArchiveSettlements: (query: Record<string, unknown>, page: number, pageSize: number) => Promise<unknown>;
  loadInternalDetails: (query: Record<string, unknown>, page: number, pageSize: number) => Promise<unknown>;
  exportConfiguredRows: (selectedOnly: boolean) => void;
  exportInvoiceUnissued: (selectedOnly: boolean) => Promise<void>;
  exportInternalDetails: (selectedOnly: boolean) => Promise<void>;
  exportInvoiceList: (selectedOnly: boolean) => Promise<void>;
  exportFeeQuery: (selectedOnly: boolean) => Promise<void>;
  exportGeneralSettlement: (kind: "settlement" | "receipt" | "case", ids?: (string | number)[]) => Promise<void>;
  exportPendingArchiveSettlements: (ids?: (string | number)[]) => Promise<void>;
  runSettlementMoreAction: (key: string) => void;
  openBatchFeeReview: () => void;
  openCaseTaskCreate: (detail: { case_no?: unknown; customer?: unknown; data?: Record<string, unknown> }) => void;
  openCaseDetail: (caseNo: unknown) => void;
  openCustomerDetail: (customer: string, customerNo?: string) => void;
  openContractDetail: (contractNo: string) => void;
  financePersonDisplayName: (identity?: unknown, displayName?: unknown) => string;
  financePersonDisplayNames: (identities?: unknown, displayNames?: unknown) => string;
  previewInternalPaymentPackage: () => Promise<void>;
  generalSettlementDetails: (number | string)[];
  setGeneralSettlementDetails: (ids: (number | string)[]) => void;
  openArchiveSettlementReview: (rows: ArchiveSettlementTarget[], approved: boolean) => void;
  openArchiveSettlementRollback: (rows: ArchiveSettlementTarget[]) => void;
  openArchiveSettlementReapply: (rows: ArchiveSettlementTarget[]) => void;
  openGeneralSettlementReapply: (rows: Fee[]) => void;
  openGeneralSettlementPayment: (targets: Fee[], action: "paid" | "rollback") => void;
  openGeneralSettlementReview: (rows: Fee[], approved: boolean) => void;
  applyGeneralSettlementRows: () => void;
  refundCaseFeeOperationMenu: RefundCaseFeeOperationMenuProps;
  refundCaseFeeMarkButton: RefundCaseFeeMarkButtonProps;
}

export function FinanceOriginalRoutesView(props: FinanceOriginalRoutesViewProps) {
  const {
    originalQueryView,
    initialView,
    originalKind,
    isInvoiceMineRoute,
    isInvoicePendingRoute,
    isInvoiceCompanyRoute,
    isInvoiceUnissuedRoute,
    isGeneralSettlementRoute,
    isGeneralSettlementPaidRoute,
    isGeneralSettlementRejectedRoute,
    isGeneralSettlementAuditRoute,
    isGeneralSettlementPaymentRoute,
    isArchiveSettlementActiveRoute,
    isArchiveSettlementPaidRoute,
    isArchiveSettlementRejectedRoute,
    isArchiveSettlementPaymentRoute,
    isFeeQueryRoute,
    isInternalDetailRoute,
    isInternalApprovalRoute,
    isInternalQueueRoute,
    internalQueueMeta,
    internalQueueError,
    loadInternalQueue,
    isRefundCaseFeeRoute,
    activeRouteConfig,
    loading,
    paymentPackageLoading,
    invoiceExportLoading,
    feeQueryExportLoading,
    settlementActionLoading,
    generalSettlementBusy,
    archiveSettlementBusy,
    internalDetailExportLoading,
    canManage,
    canApprove,
    originalColumns,
    paymentOriginalColumns,
    configuredRows,
    selectedOriginalRows,
    setSelectedOriginalRows,
    paymentQueryMeta,
    paymentQueryPageSize,
    setPaymentQueryPageSize,
    paymentAuditPageSize,
    setPaymentAuditPageSize,
    localListPage = { page: 1, pageSize: 15 },
    setLocalListPage,
    paymentQueryQuickPage,
    setPaymentQueryQuickPage,
    feeQueryMeta,
    paymentPackageMeta,
    invoiceMineMeta,
    invoicePendingMeta,
    invoiceCompanyMeta,
    invoiceUnissuedMeta,
    generalSettlementMeta,
    archiveSettlementMeta,
    internalDetailMeta,
    incomingMeta,
    loadIncomingPayments,
    originalQuery,
    submitPaymentQueryQuickPage,
    refreshPaymentQueryPage,
    loadPaymentPackages,
    loadFeeQuery,
    loadInvoiceMine,
    loadInvoicePending,
    loadInvoiceCompany,
    loadInvoiceUnissued,
    loadGeneralSettlements,
    loadArchiveSettlements,
    loadInternalDetails,
    exportConfiguredRows,
    exportInvoiceUnissued,
    exportInternalDetails,
    exportInvoiceList,
    exportFeeQuery,
    exportGeneralSettlement,
    exportPendingArchiveSettlements,
    runSettlementMoreAction,
    openBatchFeeReview,
    openCaseTaskCreate,
    openCaseDetail,
    openCustomerDetail,
    openContractDetail,
    financePersonDisplayName,
    financePersonDisplayNames,
    previewInternalPaymentPackage,
    generalSettlementDetails,
    setGeneralSettlementDetails,
    openArchiveSettlementReview,
    openArchiveSettlementRollback,
    openArchiveSettlementReapply,
    openGeneralSettlementReapply,
    openGeneralSettlementPayment,
    openGeneralSettlementReview,
    applyGeneralSettlementRows,
    refundCaseFeeOperationMenu,
    refundCaseFeeMarkButton,
  } = props;
  // 付款、审批等原始列表使用专用列定义，不经过 routeConfigs；表头应与实际列保持一致。
  const originalHeaders = activeRouteConfig?.headers ??
    originalColumns.map((column) =>
      typeof column.title === "string" ? column.title : "",
    );
  const settlementRouteRows = configuredRows as Fee[];
  const originalColumnIds = columnIds(originalColumns);
  const isIncomingTotalsRoute = ["finance-receipts-manage", "finance-receipts-claim", "finance-receipts-pending", "finance-receipts-allocated", "finance-receipts-query"].includes(initialView);
  // 合计行已经按叠放布局排列的路由才允许叠放列；其余路由的合计行仍按原列位置排列，叠放会让合计错位，所以不叠放。
  // 下面两个分支顺序与 components / summary 的判断顺序一致。
  const totalsBodyBranch = isIncomingTotalsRoute ? "incoming"
    : initialView === "finance-payment-query" && configuredRows.length ? "payment-query"
    : isFeeQueryRoute && configuredRows.length ? "fee-query"
    : isGeneralSettlementRoute && configuredRows.length ? "general-settlement"
    : isArchiveSettlementActiveRoute && configuredRows.length ? "archive-settlement"
    : activeRouteConfig?.source === "paymentPackages" ? "payment-packages"
    : isInternalDetailRoute && configuredRows.length ? "internal-detail"
    : isInvoiceUnissuedRoute && configuredRows.length ? "invoice-unissued"
    : (isInvoiceMineRoute || isInvoicePendingRoute || isInvoiceCompanyRoute) && configuredRows.length ? "invoice"
    : "none";
  const totalsSummaryBranch = isInternalQueueRoute ? "internal-queue"
    : initialView === "finance-payment-query" ? "payment-query"
    : isFeeQueryRoute ? "fee-query"
    : ["finance-internal-writeoff", "finance-internal-done"].includes(initialView) ? "payment-packages"
    : isInternalDetailRoute ? "internal-detail"
    : isInvoiceUnissuedRoute ? "invoice-unissued"
    : isInvoiceMineRoute || isInvoicePendingRoute || isInvoiceCompanyRoute ? "invoice"
    : ["finance-internal-refused", "finance-internal-void", "finance-internal-query"].includes(initialView) ? "internal-list"
    : "none";
  const fitStackAware = {
    body: !["archive-settlement", "payment-packages", "internal-detail"].includes(totalsBodyBranch),
    summary: !["payment-packages", "internal-detail", "internal-list"].includes(totalsSummaryBranch),
  };
  if (isInternalQueueRoute && (!internalQueueMeta || !loadInternalQueue)) throw new Error("内部费用分页配置缺失");
  return (
    <>
          <section
            className={`finance-original-panel${initialView.startsWith("finance-internal") ? " finance-internal-queues" : ""}${isGeneralSettlementRoute ? " finance-general-settlement" : ""}${
              initialView === "finance-internal-mine"
                ? " finance-original-internal-mine"
                : isInvoiceMineRoute
                  ? " finance-original-invoice-mine"
                : isInvoicePendingRoute
                  ? " finance-original-invoice-pending"
                : isInvoiceCompanyRoute
                  ? " finance-original-invoice-company"
                : isInvoiceUnissuedRoute
                  ? " finance-original-invoice-unissued"
                : isGeneralSettlementRoute
                  ? isGeneralSettlementPaidRoute
                    ? " finance-original-settlement-paid"
                    : isGeneralSettlementRejectedRoute
                      ? " finance-original-settlement-audit finance-original-settlement-rejected"
                    : isGeneralSettlementAuditRoute ||
                        isGeneralSettlementPaymentRoute
                    ? " finance-original-settlement-audit"
                    : " finance-original-settlement-pending"
                : isArchiveSettlementActiveRoute
                  ? ` finance-original-archive-pending${
                      isArchiveSettlementPaidRoute
                        ? " finance-original-archive-paid"
                        : isArchiveSettlementRejectedRoute
                          ? " finance-original-archive-rejected"
                        : ""
                    }`
                : isFeeQueryRoute
                  ? " finance-original-fee-query"
                : initialView === "finance-internal-settle"
                  ? " finance-original-internal-settle"
                  : initialView === "finance-internal-payment"
                    ? " finance-original-internal-payment"
                  : [
                          "finance-internal-writeoff",
                          "finance-internal-done",
                        ].includes(initialView)
                      ? " finance-original-payment-packages"
                  : isInternalDetailRoute
                    ? " finance-original-internal-detail"
                  : [
                        "finance-internal-refused",
                        "finance-internal-void",
                        "finance-internal-query",
                      ].includes(initialView)
                    ? " finance-original-internal-list"
                    : isInternalApprovalRoute
                      ? " finance-original-internal-approval"
                      : ""
            }`}
          >
            <FinanceOriginalQueryView {...originalQueryView} />
            {internalQueueError && <Alert type="error" showIcon message={internalQueueError} />}
            {internalQueueMeta?.amountVisible && internalQueueMeta.amountTotalsComplete === false &&
              <Alert type="warning" showIcon message={`有 ${internalQueueMeta.missingCommissionAmountCount} 条来源费用缺少可核对的提成金额，提成合计待核对；到账金额仍按实际回款显示。`} />}
            <div className="finance-original-table-wrap">
              <Table
                rowKey="id"
                size="small"
                tableLayout={initialView.startsWith("finance-internal") || isGeneralSettlementRoute || isFeeQueryRoute || isInvoiceUnissuedRoute || activeRouteConfig?.source === "incoming" ? "fixed" : undefined}
                loading={loading}
                columns={originalColumns}
                fitStack={incomingFitStack(originalColumns)}
                fitStackAware={fitStackAware}
                dataSource={configuredRows}
                expandable={
                  isGeneralSettlementRoute
                    ? {
                        showExpandColumn: false,
                        expandedRowKeys: configuredRows.map((row) => row.id),
                        expandedRowRender: (row: OriginalFinanceRow) => <GeneralSettlementExpandedRow
                          row={row as SettlementRow}
                          isPaymentRoute={isGeneralSettlementPaymentRoute}
                          isPaidRoute={isGeneralSettlementPaidRoute}
                          isRejectedRoute={isGeneralSettlementRejectedRoute}
                          isAuditRoute={isGeneralSettlementAuditRoute}
                          detailsExpanded={generalSettlementDetails.includes(row.id)}
                          displayPersonName={financePersonDisplayName}
                          displayPersonNames={financePersonDisplayNames}
                          openTask={openCaseTaskCreate}
                          exportSettlement={exportGeneralSettlement}
                          openCase={openCaseDetail}
                          openCustomer={openCustomerDetail}
                          openContract={openContractDetail}
                        />,
                      }
                    : isArchiveSettlementPaymentRoute ||
                        isArchiveSettlementPaidRoute ||
                        isArchiveSettlementRejectedRoute
                      ? {
                          showExpandColumn: false,
                          expandedRowKeys: configuredRows.map((row) => row.id),
                          expandedRowRender: (row: OriginalFinanceRow) => (
                            <div className="finance-archive-payment-context">
                              <span>
                                {(isArchiveSettlementPaidRoute || isArchiveSettlementRejectedRoute) && (
                                  <>归档费审核人: {financePersonDisplayName(row.data?.archive_payment_reviewer, row.data?.archive_payment_reviewer_display_name)}<br /></>
                                )}
                                归档审核人: {financePersonDisplayName(row.data?.archive_reviewer, row.data?.archive_reviewer_display_name)}
                                <br />归档申请人: {financePersonDisplayName(row.data?.archive_submitter, row.data?.archive_submitter_display_name)}
                              </span>
                              <span>
                                {(isArchiveSettlementPaidRoute || isArchiveSettlementRejectedRoute) && (
                                  <>归档费审核时间: {row.data?.archive_payment_reviewed_at ? dayjs(row.data.archive_payment_reviewed_at).format("YYYY-M-D H:m:s") : "—"}<br /></>
                                )}
                                归档审核时间: {row.data?.archive_reviewed_at ? dayjs(row.data.archive_reviewed_at).format("YYYY-M-D H:m:s") : "—"}
                                <br />归档提交时间: {row.data?.archive_submitted_at ? dayjs(row.data.archive_submitted_at).format("YYYY-M-D H:m:s") : "—"}
                              </span>
                              <span>
                                {(isArchiveSettlementPaidRoute || isArchiveSettlementRejectedRoute) && (
                                  <>归档费审核备注: {row.data?.archive_payment_comment || ""}<br /></>
                                )}
                                归档审核备注: {row.data?.archive_review_comment || ""}
                                <br />归档提交备注: {row.data?.archive_submit_comment || ""}
                              </span>
                              <span>
                                {(isArchiveSettlementPaidRoute || isArchiveSettlementRejectedRoute) && (
                                  <>归档费支付状态: <span className={isArchiveSettlementRejectedRoute ? "finance-archive-rejected-status" : ""}>{row.status || "已支付"}</span><br /></>
                                )}
                                归档号: {row.data?.archive_no || "—"}
                                <br />归档审核状态: {row.data?.archive_status || "审核通过"}
                              </span>
                            </div>
                          ),
                        }
                    : undefined
                }
                components={
                  ["finance-receipts-manage", "finance-receipts-claim", "finance-receipts-pending", "finance-receipts-allocated", "finance-receipts-query"].includes(initialView)
                    ? { body: { wrapper: (props: ComponentProps<"tbody">) => <IncomingTotalsBody {...props} headers={originalHeaders} totals={incomingMeta.totals} /> } }
                  : initialView === "finance-payment-query" && configuredRows.length
                    ? { body: { wrapper: (props: ComponentProps<"tbody">) => (
                      <PaymentQueryTotalBody {...props} rows={configuredRows} columnCount={paymentOriginalColumns.length} columnIds={columnIds(paymentOriginalColumns)} />
                    ) } }
                  : isFeeQueryRoute && configuredRows.length
                    ? { body: { wrapper: (props: ComponentProps<"tbody">) => (
                      <FeeQueryTotalBody {...props} headers={originalHeaders} totals={feeQueryMeta.totals} />
                    ) } }
                  : isGeneralSettlementRoute && configuredRows.length
                    ? {
                        body: {
                          wrapper: ({ children, ...wrapperProps }: ComponentProps<"tbody">) => {
                            const [stack, bodyProps] = takeTotalsStack(wrapperProps);
                            return (
                            <tbody {...bodyProps}>
                              <tr className="finance-settlement-grand-total">
                                <td />
                                {layoutTotalCells(originalColumnIds, stack, (index) => {
                                  const header = originalHeaders[index];
                                  const keyByHeader: Record<string, string> = {
                                    回款金额: "receipt_amount",
                                    已分金额: "allocated_amount",
                                    未分金额: "remaining_amount",
                                    已分官费: "assigned_official_fee",
                                    已分代理费: "assigned_agency_fee",
                                    已分其他费用: "assigned_other_fee",
                                    代理费结算金额: "agency_settlement_amount",
                                    扣归档费: "archive_fee",
                                    实际结算金额: "actual_settlement_amount",
                                  };
                                  const totalKey = keyByHeader[header];
                                  const hidePaymentTotal =
                                    (isGeneralSettlementPaymentRoute ||
                                      isGeneralSettlementPaidRoute) &&
                                    ["代理费结算金额", "实际结算金额"].includes(
                                      header,
                                    );
                                  const hideRejectedTotal =
                                    isGeneralSettlementRejectedRoute &&
                                    [
                                      "代理费结算金额",
                                      "扣归档费",
                                      "实际结算金额",
                                    ].includes(header);
                                  return totalKey && !hidePaymentTotal && !hideRejectedTotal
                                    ? generalSettlementMeta.totals[totalKey] == null ? "—" : Number(generalSettlementMeta.totals[totalKey]).toFixed(2)
                                    : null;
                                }).map((cell) => <td key={cell.key}>{cell.content}</td>)}
                              </tr>
                              {children}
                            </tbody>
                            );
                          },
                        },
                      }
                    : isArchiveSettlementActiveRoute && configuredRows.length
                      ? {
                          body: {
                            wrapper: ({ children, ...bodyProps }: ComponentProps<"tbody">) => (
                              <tbody {...bodyProps}>
                                <tr className="finance-archive-settlement-grand-total">
                                  <td />
                                  {originalHeaders.map((header, index) => (
                                    <td key={`${header}-${index}`}>
                                      {header === "回款金额"
                                        ? archiveSettlementMeta.totals.receipt_amount == null ? "—" : Number(archiveSettlementMeta.totals.receipt_amount).toFixed(2)
                                        : header === "归档费金额"
                                          ? archiveSettlementMeta.totals.archive_fee_amount == null ? "—" : Number(archiveSettlementMeta.totals.archive_fee_amount).toFixed(2)
                                          : null}
                                    </td>
                                  ))}
                                </tr>
                                {children}
                              </tbody>
                            ),
                          },
                        }
                    : activeRouteConfig?.source === "paymentPackages"
                    ? { body: { wrapper: (props: ComponentProps<"tbody">) => (
                      <PaymentPackageTotalBody {...props} headers={originalHeaders} rows={configuredRows} />
                    ) } }
                    : isInternalDetailRoute && configuredRows.length
                      ? {
                          body: {
                            wrapper: ({ children, ...bodyProps }: ComponentProps<"tbody">) => (
                              <tbody {...bodyProps}>
                                <tr className="finance-internal-detail-grand-total">
                                  <td />
                                  {originalHeaders.map(
                                    (header, index) => (
                                      <td key={`${header}-${index}`}>
                                        {header === "金额"
                                          ? internalDetailMeta.totalAmount.toFixed(
                                              2,
                                            )
                                          : null}
                                      </td>
                                    ),
                                  )}
                                </tr>
                                {children}
                              </tbody>
                            ),
                          },
                        }
                    : isInvoiceUnissuedRoute && configuredRows.length
                      ? {
                          body: {
                            wrapper: ({ children, ...wrapperProps }: ComponentProps<"tbody">) => {
                              const [stack, bodyProps] = takeTotalsStack(wrapperProps);
                              return (
                              <tbody {...bodyProps}>
                                <tr className="finance-invoice-unissued-grand-total">
                                  <td />
                                  {layoutTotalCells(originalColumnIds, stack, (index) => {
                                    const header = originalHeaders[index];
                                    return header === "金额"
                                          ? invoiceUnissuedMeta.totalAmount.toFixed(2)
                                          : header === "开票金额"
                                            ? invoiceUnissuedMeta.totalInvoiceAmount.toFixed(2)
                                            : header === "到账金额"
                                              ? invoiceUnissuedMeta.totalCashedAmount.toFixed(2)
                                              : header === "付款金额"
                                                ? invoiceUnissuedMeta.totalPaidAmount.toFixed(2)
                                                : null;
                                  }).map((cell) => <td key={cell.key}>{cell.content}</td>)}
                                </tr>
                                {children}
                              </tbody>
                              );
                            },
                          },
                        }
                    : (isInvoiceMineRoute || isInvoicePendingRoute || isInvoiceCompanyRoute) && configuredRows.length
                      ? {
                          body: {
                            wrapper: ({ children, ...wrapperProps }: ComponentProps<"tbody">) => {
                              const [stack, bodyProps] = takeTotalsStack(wrapperProps);
                              return (
                              <tbody {...bodyProps}>
                                <tr className="finance-invoice-grand-total">
                                  <td />
                                  {layoutTotalCells(originalColumnIds, stack, (index) => {
                                    const header = originalHeaders[index];
                                    return header === "开票金额"
                                          ? isInvoicePendingRoute
                                            ? invoicePendingMeta.totalAmount
                                            : isInvoiceCompanyRoute
                                              ? invoiceCompanyMeta.totalAmount
                                              : invoiceMineMeta.totalAmount
                                          : header === "高开金额"
                                            ? isInvoicePendingRoute
                                              ? invoicePendingMeta.totalExtraAmount
                                              : isInvoiceCompanyRoute
                                                ? invoiceCompanyMeta.totalExtraAmount
                                                : invoiceMineMeta.totalExtraAmount
                                            : null;
                                  }).map((cell) => <td key={cell.key}>{cell.content}</td>)}
                                </tr>
                                {children}
                              </tbody>
                              );
                            },
                          },
                        }
                    : undefined
                }
                summary={
                  isInternalQueueRoute
                    ? (_pageData: readonly OriginalFinanceRow[], fit?: FitStackState) => !loading && !internalQueueError && internalQueueMeta!.total > 0
                      ? <InternalQueueSummary meta={internalQueueMeta!} headers={originalHeaders} selectable={Boolean(activeRouteConfig?.selectable)} stack={fit?.groups} />
                      : null
                    : initialView === "finance-payment-query"
                    ? (pageData: readonly OriginalFinanceRow[], fit?: FitStackState) => <PaymentQueryPageSummary rows={pageData} columnCount={paymentOriginalColumns.length} columnIds={columnIds(paymentOriginalColumns)} stack={fit?.groups} />
                    : isFeeQueryRoute
                    ? (pageData: readonly OriginalFinanceRow[], fit?: FitStackState) => <FeeQueryPageSummary rows={pageData} headers={originalHeaders} stack={fit?.groups} />
                    : [
                          "finance-internal-writeoff",
                          "finance-internal-done",
                        ].includes(initialView)
                      ? (pageData) => <PaymentPackagePageSummary rows={pageData} headers={originalHeaders} />
                      : isInternalDetailRoute
                        ? (pageData) =>
                            pageData.length ? (
                              <Table.Summary.Row className="finance-internal-detail-summary">
                              <Table.Summary.Cell index={0} />
                              {originalHeaders.map(
                                (header, index) => (
                                  <Table.Summary.Cell
                                    key={`${header}-${index}`}
                                    index={index + 1}
                                  >
                                    {header === "金额"
                                      ? pageData
                                          .reduce(
                                            (sum, row) =>
                                              sum +
                                              Number(row.data?.amount || 0),
                                            0,
                                          )
                                          .toFixed(2)
                                      : null}
                                  </Table.Summary.Cell>
                                ),
                              )}
                              </Table.Summary.Row>
                            ) : null
                      : isInvoiceUnissuedRoute
                        ? (pageData: readonly OriginalFinanceRow[], fit?: FitStackState) =>
                            pageData.length ? (
                              <Table.Summary.Row className="finance-invoice-unissued-page-total">
                                <Table.Summary.Cell index={0} />
                                {layoutTotalCells(originalColumnIds, fit?.groups, (index) => {
                                  const header = originalHeaders[index];
                                  return header === "金额"
                                        ? pageData.reduce(
                                            (sum, row) =>
                                              sum + Number(row.data?.amount || 0),
                                            0,
                                          ).toFixed(2)
                                        : header === "开票金额"
                                          ? pageData.reduce(
                                              (sum, row) =>
                                                sum + Number(row.data?.invoice_amount || 0),
                                              0,
                                            ).toFixed(2)
                                          : header === "到账金额"
                                            ? pageData.reduce(
                                                (sum, row) =>
                                                  sum + Number(row.data?.cashed_amount || 0),
                                                0,
                                              ).toFixed(2)
                                            : header === "付款金额"
                                              ? pageData.reduce(
                                                  (sum, row) =>
                                                    sum + Number(row.data?.paid_amount || 0),
                                                  0,
                                                ).toFixed(2)
                                              : null;
                                }).map((cell, position) => <Table.Summary.Cell key={cell.key} index={position + 1}>{cell.content}</Table.Summary.Cell>)}
                              </Table.Summary.Row>
                            ) : null
                      : isInvoiceMineRoute || isInvoicePendingRoute || isInvoiceCompanyRoute
                        ? (pageData: readonly OriginalFinanceRow[], fit?: FitStackState) =>
                            pageData.length ? (
                              <Table.Summary.Row className="finance-invoice-page-total">
                                <Table.Summary.Cell index={0} />
                                {layoutTotalCells(originalColumnIds, fit?.groups, (index) => {
                                  const header = originalHeaders[index];
                                  return header === "开票金额"
                                        ? pageData
                                            .filter((row) =>
                                              isInvoicePendingRoute ||
                                              !["已撤回", "已作废"].includes(row.status || ""),
                                            )
                                            .reduce(
                                              (sum, row) =>
                                                sum +
                                                Number(row.data?.amount || 0),
                                              0,
                                            )
                                        : header === "高开金额"
                                          ? pageData
                                              .filter((row) =>
                                                isInvoicePendingRoute ||
                                                !["已撤回", "已作废"].includes(row.status || ""),
                                              )
                                              .reduce(
                                                (sum, row) =>
                                                  sum +
                                                  Number(
                                                    row.data?.extra_amount || 0,
                                                  ),
                                                0,
                                              )
                                          : null;
                                }).map((cell, position) => <Table.Summary.Cell key={cell.key} index={position + 1}>{cell.content}</Table.Summary.Cell>)}
                              </Table.Summary.Row>
                            ) : null
                      : [
                          "finance-internal-refused",
                          "finance-internal-void",
                          "finance-internal-query",
                        ].includes(initialView)
                      ? (pageData) => (
                          <Table.Summary.Row className="finance-internal-list-summary">
                            {originalHeaders.map((_header, index) => (
                              <Table.Summary.Cell key={index} index={index}>
                                {index === 5
                                  ? pageData
                                      .reduce(
                                        (sum, row) =>
                                          sum + Number(row.data?.amount || 0),
                                        0,
                                      )
                                      .toFixed(2)
                                  : null}
                              </Table.Summary.Cell>
                            ))}
                          </Table.Summary.Row>
                        )
                      : undefined
                }
                rowSelection={
                  activeRouteConfig?.selectable ||
                  initialView === "finance-payment-audit" ||
                  initialView === "finance-payment-waiting" ||
                  initialView === "finance-payment-writeoff" ||
                  initialView === "finance-payment-query"
                    ? {
                        ...(isGeneralSettlementRoute ? { columnWidth: 36 } : {}),
                        selectedRowKeys: selectedOriginalRows,
                        onChange: (keys) =>
                          setSelectedOriginalRows(
                            keys.filter(key => !isArchiveSettlementActiveRoute || !configuredRows.some(row => row.id === key && isHistoricalSettlement(row))) as (string | number)[],
                          ),
                        getTitleCheckboxProps: () =>
                          initialView === "finance-payment-waiting"
                            ? { disabled: false }
                            : {},
                        getCheckboxProps: (row) => ({
                          disabled:
                            (isArchiveSettlementActiveRoute && isHistoricalSettlement(row)) ||
                            Boolean(isInternalQueueRoute && row.data?.read_only) ||
                            (initialView === "finance-internal-refund-audit" && row.status !== "待审批"),
                        }),
                        ...(isArchiveSettlementActiveRoute
                          ? {
                              columnWidth: isArchiveSettlementRejectedRoute
                                ? 54
                                : 51,
                            }
                          : {}),
                      }
                    : undefined
                }
                rowClassName={(row) =>
                  isInvoiceMineRoute &&
                  ["已撤回", "已作废"].includes(row.status || "")
                    ? "finance-invoice-cancelled-row"
                    : ""
                }
                scroll={{
                  x: isFeeQueryRoute
                    ? originalColumns.reduce((total, column) => total + Number(column.width), 36)
                    : activeRouteConfig?.source === "incoming"
                    ? originalColumns.reduce((total, column) => total + Number(column.width || 120), 48)
                    : initialView.startsWith("finance-internal")
                      ? originalColumns.reduce((total, column) => total + Number(column.width || 120), 48)
                    : activeRouteConfig
                    ? isGeneralSettlementRoute
                      ? originalColumns.reduce((total, column) => total + Number(column.width), 36)
                    : isArchiveSettlementActiveRoute
                      ? 1904
                    : initialView === "finance-internal-settle"
                      ? 1990
                      : isInvoiceUnissuedRoute
                        ? 1904
                      : [
                            "finance-internal-refused",
                            "finance-internal-void",
                            "finance-internal-query",
                          ].includes(initialView)
                        ? 1904
                        : Math.max(1200, originalHeaders.length * 125)
                    : originalKind === "fee-query"
                      ? 2100
                      : 1650,
                }}
                pagination={{
                  size: "small",
                  current: localListPage.page,
                  onChange: (page: number, pageSize: number) => {
                    setSelectedOriginalRows([]);
                    setLocalListPage?.({ page: pageSize === localListPage.pageSize ? page : 1, pageSize });
                  },
                  pageSize: activeRouteConfig?.source === "incoming"
                    ? incomingMeta.pageSize
                    : isGeneralSettlementRoute
                    ? generalSettlementMeta.pageSize
                    : isArchiveSettlementActiveRoute
                      ? archiveSettlementMeta.pageSize
                    : isFeeQueryRoute
                      ? feeQueryMeta.pageSize
                    : initialView === "finance-payment-audit"
                      ? paymentAuditPageSize
                    : activeRouteConfig?.source === "paymentPackages"
                      ? paymentPackageMeta.pageSize
                    : paymentQueryControlledPageSize(
                        initialView,
                        paymentQueryPageSize,
                      ) ?? paymentQueryDefaultPageSize(initialView) ??
                      ([
                    "finance-payment-mine",
                    "finance-internal-mine",
                    "finance-internal-settle",
                    "finance-internal-refused",
                    "finance-internal-void",
                    "finance-internal-payment",
                    "finance-internal-writeoff",
                    "finance-internal-query",
                    "finance-internal-done",
                    ...internalApprovalRoutes,
                    ].includes(initialView)
                      ? localListPage.pageSize
                      : isInvoiceMineRoute
                      ? invoiceMineMeta.pageSize
                    : isInvoicePendingRoute
                      ? invoicePendingMeta.pageSize
                    : isInvoiceCompanyRoute
                      ? invoiceCompanyMeta.pageSize
                    : isInvoiceUnissuedRoute
                      ? invoiceUnissuedMeta.pageSize
                    : isInternalDetailRoute
                      ? internalDetailMeta.pageSize
                      : 20),
                  pageSizeOptions:
                    activeRouteConfig?.source === "incoming"
                      ? [10, 20, 50, 100, 200]
                      : activeRouteConfig?.source === "paymentPackages"
                      ? paymentPackagePageSizeOptions
                      : paymentQueryPageSizeOptions(initialView) ??
                    ([
                    "finance-payment-mine",
                    "finance-settlement-pending",
                    "finance-settlement-audit",
                    "finance-archive-fee-pending",
                    "finance-archive-fee-payment",
                    "finance-archive-fee-paid",
                    "finance-archive-fee-refused",
                    "finance-internal-mine",
                    "finance-internal-settle",
                    "finance-internal-refused",
                    "finance-internal-void",
                    "finance-internal-payment",
                    "finance-internal-writeoff",
                    "finance-internal-query",
                    "finance-internal-done",
                    "finance-internal-detail",
                    "finance-internal-company",
                    "finance-invoice-mine",
                    "finance-invoice-pending",
                    "finance-invoice-company",
                    "finance-invoice-unissued",
                    "finance-invoice-company-unissued",
                    "finance-fee-query",
                    ...internalApprovalRoutes,
                    ].includes(initialView)
                      ? [10, 15, 20, 50, 100, 200]
                      : undefined),
                  showQuickJumper: paymentQueryQuickJumper(initialView),
                  showSizeChanger: true,
                  ...(initialView === "finance-payment-query"
                    ? {
                        onShowSizeChange: (_page: number, pageSize: number) => {
                          setSelectedOriginalRows([]);
                          setPaymentQueryPageSize(pageSize);
                          refreshPaymentQueryPage(1, pageSize);
                        },
                      }
                    : {}),
                  ...(initialView === "finance-payment-audit"
                    ? {
                        onShowSizeChange: (_page: number, pageSize: number) => {
                          setSelectedOriginalRows([]);
                          setPaymentAuditPageSize(pageSize);
                        },
                      }
                    : {}),
                  ...(activeRouteConfig?.source === "paymentPackages"
                    ? {
                        onShowSizeChange: (_page: number, pageSize: number) => {
                          setSelectedOriginalRows([]);
                          void loadPaymentPackages(originalQuery, 1, pageSize).catch(
                            () => message.error("付款包查询失败"),
                          );
                        },
                      }
                    : {}),
                  ...(activeRouteConfig?.source === "incoming"
                    ? {
                        current: incomingMeta.page,
                        total: incomingMeta.total,
                        onChange: (page: number, pageSize: number) => {
                          void loadIncomingPayments(originalQuery, pageSize === incomingMeta.pageSize ? page : 1, pageSize).catch(
                            (error: unknown) => message.error(financeErrorDetail(error) || "回款翻页失败"),
                          );
                        },
                      }
                    : {}),
                  ...(isFeeQueryRoute
                    ? {
                        current: feeQueryMeta.page,
                        total: feeQueryMeta.total,
                        onChange: (page: number, pageSize: number) => {
                          setSelectedOriginalRows([]);
                          void loadFeeQuery(originalQuery, pageSize === feeQueryMeta.pageSize ? page : 1, pageSize).catch(
                            (error: unknown) =>
                              message.error(
                                financeErrorDetail(error) ||
                                  "费用查询翻页失败",
                              ),
                          );
                        },
                      }
                    : activeRouteConfig?.source === "paymentPackages"
                      ? {
                          current: paymentPackageMeta.page,
                          total: paymentPackageMeta.total,
                          onChange: (page: number, pageSize: number) => {
                            setSelectedOriginalRows([]);
                            void loadPaymentPackages(originalQuery, pageSize === paymentPackageMeta.pageSize ? page : 1, pageSize).catch(
                              () => message.error("付款包查询失败"),
                            );
                          },
                        }
                    : initialView === "finance-payment-query"
                      ? {
                          current: paymentQueryMeta.page,
                          total: paymentQueryMeta.total,
                          onChange: (page: number, pageSize: number) => {
                            refreshPaymentQueryPage(page, pageSize);
                          },
                        }
                      : {}),
                  ...(isInternalDetailRoute
                    ? {
                        current: internalDetailMeta.page,
                        total: internalDetailMeta.total,
                        onChange: (page: number, pageSize: number) => {
                          setSelectedOriginalRows([]);
                          void loadInternalDetails(
                            originalQuery,
                            pageSize === internalDetailMeta.pageSize ? page : 1,
                            pageSize,
                          ).catch((error: unknown) =>
                            message.error(
                              financeErrorDetail(error) ||
                                "内部费用明细翻页失败",
                            ),
                          );
                        },
                      }
                    : {}),
                  ...(isInvoiceMineRoute
                    ? {
                        current: invoiceMineMeta.page,
                        total: invoiceMineMeta.total,
                        onChange: (page: number, pageSize: number) => {
                          setSelectedOriginalRows([]);
                          void loadInvoiceMine(
                            originalQuery,
                            pageSize === invoiceMineMeta.pageSize ? page : 1,
                            pageSize,
                          ).catch((error: unknown) =>
                            message.error(
                              financeErrorDetail(error) ||
                                "我的开票翻页失败",
                            ),
                          );
                        },
                      }
                    : {}),
                  ...(isInvoicePendingRoute
                    ? {
                        current: invoicePendingMeta.page,
                        total: invoicePendingMeta.total,
                        onChange: (page: number, pageSize: number) => {
                          setSelectedOriginalRows([]);
                          void loadInvoicePending(
                            originalQuery,
                            pageSize === invoicePendingMeta.pageSize ? page : 1,
                            pageSize,
                          ).catch((error: unknown) =>
                            message.error(
                              financeErrorDetail(error) ||
                                "待处理开票翻页失败",
                            ),
                          );
                        },
                      }
                    : {}),
                  ...(isInvoiceCompanyRoute
                    ? {
                        current: invoiceCompanyMeta.page,
                        total: invoiceCompanyMeta.total,
                        onChange: (page: number, pageSize: number) => {
                          setSelectedOriginalRows([]);
                          void loadInvoiceCompany(
                            originalQuery,
                            pageSize === invoiceCompanyMeta.pageSize ? page : 1,
                            pageSize,
                          ).catch((error: unknown) =>
                            message.error(
                              financeErrorDetail(error) ||
                                "公司开票翻页失败",
                            ),
                          );
                        },
                      }
                    : {}),
                  ...(isInvoiceUnissuedRoute
                    ? {
                        current: invoiceUnissuedMeta.page,
                        total: invoiceUnissuedMeta.total,
                        onChange: (page: number, pageSize: number) => {
                          setSelectedOriginalRows([]);
                          void loadInvoiceUnissued(
                            originalQuery,
                            pageSize === invoiceUnissuedMeta.pageSize ? page : 1,
                            pageSize,
                          ).catch((error: unknown) =>
                            message.error(
                              financeErrorDetail(error) ||
                                "未开票列表翻页失败",
                            ),
                          );
                        },
                      }
                    : {}),
                  ...(isGeneralSettlementRoute
                    ? {
                        current: generalSettlementMeta.page,
                        total: generalSettlementMeta.total,
                        onChange: (page: number, pageSize: number) => {
                          setSelectedOriginalRows([]);
                          setGeneralSettlementDetails([]);
                          void loadGeneralSettlements(
                            originalQuery,
                            pageSize === generalSettlementMeta.pageSize ? page : 1,
                            pageSize,
                          ).catch((error: unknown) =>
                            message.error(
                              financeErrorDetail(error) ||
                                "待结算翻页失败",
                            ),
                          );
                        },
                      }
                    : {}),
                  ...(isArchiveSettlementActiveRoute
                    ? {
                        current: archiveSettlementMeta.page,
                        total: archiveSettlementMeta.total,
                        onChange: (page: number, pageSize: number) => {
                          setSelectedOriginalRows([]);
                          void loadArchiveSettlements(
                            originalQuery,
                            pageSize === archiveSettlementMeta.pageSize ? page : 1,
                            pageSize,
                          ).catch((error: unknown) =>
                            message.error(
                              financeErrorDetail(error) ||
                                (isArchiveSettlementPaymentRoute
                                  ? "待支付翻页失败"
                                  : isArchiveSettlementRejectedRoute
                                    ? "已拒绝翻页失败"
                                  : "待归档翻页失败"),
                            ),
                          );
                        },
                      }
                    : {}),
                  ...(isInternalQueueRoute ? {
                    current: internalQueueMeta!.page,
                    pageSize: internalQueueMeta!.pageSize,
                    total: internalQueueMeta!.total,
                    pageSizeOptions: [10, 15, 20, 50, 100, 200],
                    onChange: (page: number, pageSize: number) => {
                      setSelectedOriginalRows([]);
                      void loadInternalQueue!(originalQuery, pageSize === internalQueueMeta!.pageSize ? page : 1, pageSize).catch(
                        (error: unknown) => message.error(financeErrorDetail(error) || "内部费用翻页失败"),
                      );
                    },
                  } : {}),
                  showTotal: (total) =>
                    [
                      "finance-settlement-pending",
                      "finance-settlement-audit",
                      "finance-settlement-payment",
                      "finance-settlement-paid",
                      "finance-settlement-refused",
                      "finance-archive-fee-pending",
                      "finance-archive-fee-payment",
                      "finance-archive-fee-paid",
                      "finance-archive-fee-refused",
                      "finance-internal-mine",
                      "finance-internal-settle",
                      "finance-internal-refused",
                      "finance-internal-void",
                      "finance-internal-payment",
                      "finance-internal-writeoff",
                      "finance-internal-query",
                      "finance-internal-done",
                      "finance-internal-detail",
                      "finance-internal-company",
                      "finance-invoice-mine",
                      "finance-invoice-pending",
                      "finance-invoice-company",
                      "finance-invoice-unissued",
                      "finance-invoice-company-unissued",
                      "finance-fee-query",
                      ...internalApprovalRoutes,
                    ].includes(initialView)
                      ? `共有${total}条，每页显示`
                      : `共 ${total} 条`,
                }}
                locale={{
                  emptyText:
                    internalQueueError ? "查询失败，请重试" : isInternalDetailRoute ||
                    isFeeQueryRoute ||
                    initialView === "finance-payment-query"
                    ? "没有查询到符合条件的记录 。"
                    : "没有查询到符合条件的记录。",
                }}
              />
              {paymentQueryShowsSinglePageGo(
                initialView,
                configuredRows.length,
                paymentQueryControlledPageSize(
                  initialView,
                  paymentQueryPageSize,
                ) ?? paymentQueryDefaultPageSize(initialView) ?? 20,
              ) && (
                <div
                  className="finance-payment-query-single-page-go"
                  style={{
                    display: "flex",
                    justifyContent: "flex-end",
                    alignItems: "center",
                    gap: 8,
                    padding: "0 16px 16px",
                  }}
                >
                  <Input
                    aria-label="跳转页码"
                    size="small"
                    value={paymentQueryQuickPage}
                    onChange={(event) =>
                      setPaymentQueryQuickPage(event.target.value)
                    }
                    style={{ width: 50 }}
                  />
                  <Button
                    size="small"
                    onClick={submitPaymentQueryQuickPage}
                  >
                    GO
                  </Button>
                </div>
              )}
            </div>
            {isArchiveSettlementActiveRoute && archiveSettlementMeta.total > 0 && (
              <div className="finance-archive-settlement-footer">
                <Space size={7}>
                  {isArchiveSettlementPaymentRoute && configuredRows.some(row => !isHistoricalSettlement(row)) && (
                    <>
                      <Button
                        loading={archiveSettlementBusy}
                        onClick={() =>
                          openArchiveSettlementReview(
                            configuredRows.filter((row) =>
                              selectedOriginalRows.includes(row.id),
                            ),
                            true,
                          )
                        }
                      >
                        同意支付
                      </Button>
                      <Button
                        loading={archiveSettlementBusy}
                        onClick={() =>
                          openArchiveSettlementReview(
                            configuredRows.filter((row) =>
                              selectedOriginalRows.includes(row.id),
                            ),
                            false,
                          )
                        }
                      >
                        拒绝支付
                      </Button>
                    </>
                  )}
                  {isArchiveSettlementPaidRoute && configuredRows.some(row => !isHistoricalSettlement(row)) && (
                    <Button
                      loading={archiveSettlementBusy}
                      onClick={() =>
                        openArchiveSettlementRollback(
                          configuredRows.filter((row) =>
                            selectedOriginalRows.includes(row.id),
                          ),
                        )
                      }
                    >
                      回滚归档费结算
                    </Button>
                  )}
                  {isArchiveSettlementRejectedRoute && configuredRows.some(row => !isHistoricalSettlement(row)) && (
                    <Button
                      loading={archiveSettlementBusy}
                      onClick={() =>
                        openArchiveSettlementReapply(
                          configuredRows.filter((row) =>
                            selectedOriginalRows.includes(row.id),
                          ),
                        )
                      }
                    >
                      重新申请
                    </Button>
                  )}
                  <Button
                    loading={archiveSettlementBusy}
                    onClick={() => void exportPendingArchiveSettlements()}
                  >
                    导出选中
                  </Button>
                  <Button loading={archiveSettlementBusy} onClick={() => void exportPendingArchiveSettlements([])}>导出查询结果</Button>
                </Space>
              </div>
            )}
            {isGeneralSettlementRoute && generalSettlementMeta.total > 0 && (
              <div className="finance-settlement-footer">
                <Space size={7}>
                  {!isGeneralSettlementPaidRoute && settlementRouteRows.length > 0 && (
                    <Button
                      loading={generalSettlementBusy}
                      onClick={() =>
                        isGeneralSettlementRejectedRoute
                          ? openGeneralSettlementReapply(
                              settlementRouteRows.filter((row) =>
                                selectedOriginalRows.includes(row.id),
                              ),
                            )
                          : isGeneralSettlementPaymentRoute
                          ? openGeneralSettlementPayment(
                              settlementRouteRows.filter((row) =>
                                selectedOriginalRows.includes(row.id),
                              ),
                              "paid",
                            )
                          : isGeneralSettlementAuditRoute
                          ? openGeneralSettlementReview(
                              settlementRouteRows.filter((row) =>
                                selectedOriginalRows.includes(row.id),
                              ),
                              true,
                            )
                          : void applyGeneralSettlementRows()
                        }
                    >
                      {isGeneralSettlementRejectedRoute
                        ? "重新申请"
                        : isGeneralSettlementPaymentRoute
                        ? "标记已支付"
                        : isGeneralSettlementAuditRoute
                          ? "同意结算"
                          : "申请结算"}
                    </Button>
                  )}
                  {isGeneralSettlementAuditRoute && settlementRouteRows.length > 0 && (
                    <Button
                      loading={generalSettlementBusy}
                      onClick={() =>
                        openGeneralSettlementReview(
                          settlementRouteRows.filter((row) =>
                            selectedOriginalRows.includes(row.id),
                          ),
                          false,
                        )
                      }
                    >
                      拒绝结算
                    </Button>
                  )}
                  {(isGeneralSettlementAuditRoute || isGeneralSettlementPaymentRoute || isGeneralSettlementPaidRoute || isGeneralSettlementRejectedRoute) && settlementRouteRows.length > 0 && (
                    <Button
                      loading={generalSettlementBusy}
                      onClick={() =>
                        openGeneralSettlementPayment(
                          settlementRouteRows.filter((row) =>
                            selectedOriginalRows.includes(row.id),
                          ),
                          "rollback",
                        )
                      }
                    >
                      回滚
                    </Button>
                  )}
                  <Dropdown
                    trigger={["click"]}
                    menu={{
                      items: [
                        { key: "settlement", label: "导出结算清单" },
                        { key: "receipt", label: "导出到账清单" },
                        { key: "case", label: "导出案件清单" },
                      ],
                      onClick: ({ key }) =>
                        void exportGeneralSettlement(
                          key as "settlement" | "receipt" | "case",
                        ),
                    }}
                  >
                    <Button loading={generalSettlementBusy}>导出 ▾</Button>
                  </Dropdown>
                </Space>
              </div>
            )}
            {activeRouteConfig?.note && (
              <div className="finance-original-note">
                {activeRouteConfig.note}
              </div>
            )}
            {initialView === "finance-internal-payment" && (
              <div className="finance-original-payment-footer">
                <Button
                  loading={paymentPackageLoading}
                  onClick={() => void previewInternalPaymentPackage()}
                >
                  打包付款
                </Button>
                <span>提示:选择同一收款进行打包付款.</span>
              </div>
            )}
            {isInternalApprovalRoute &&
              configuredRows.some((row) => row.status === "待审批") && (
                <div className="finance-original-approval-footer">
                  <Button onClick={openBatchFeeReview}>审批</Button>
                  <span>已选择 {selectedOriginalRows.length} 条</span>
                </div>
              )}
            {activeRouteConfig?.export && (
              <div className="finance-original-footer">
                {initialView === "finance-payment-print" ? (
                  <Button
                    onClick={() => void previewInternalPaymentPackage()}
                    loading={paymentPackageLoading}
                  >
                    合并打印
                  </Button>
                ) : isInvoiceUnissuedRoute ? (
                  <Space size={7}>
                    <Dropdown
                      trigger={["click"]}
                      menu={{
                        items: [
                          { key: "selected", label: "导出选中" },
                          { key: "all", label: "导出全部" },
                        ],
                        onClick: ({ key }) =>
                          void exportInvoiceUnissued(key === "selected"),
                      }}
                    >
                      <Button
                        disabled={!configuredRows.length}
                        loading={invoiceExportLoading}
                      >
                        导出
                      </Button>
                    </Dropdown>
                    <Dropdown
                      trigger={["click"]}
                      menu={{
                        items: [
                          { key: "upload", label: "上传案件文档" },
                          {
                            key: "new-fee",
                            label: "新增案件费用",
                            children: [
                              { key: "official-fee", label: "新增官费" },
                              { key: "agency-fee", label: "新增代理费" },
                              { key: "other-fee", label: "新增其他费用" },
                            ],
                          },
                          { key: "internal-fee", label: "新增内部费用" },
                          {
                            key: "batch-modify",
                            label: "批量修改",
                            children: [
                              { key: "hearing_lawyer", label: "修改开庭律师" },
                              { key: "handling_lawyers", label: "修改经办律师" },
                              { key: "assistant", label: "修改律师助理" },
                              { key: "case_stage", label: "修改案件阶段" },
                            ],
                          },
                          { key: "authorization", label: "生成授权委托书" },
                          { key: "law-firm-letter", label: "生成律所函" },
                          { key: "identity", label: "生成身份证明" },
                          { key: "settlement", label: "生成结算提成表" },
                          { key: "tasks", label: "案件任务" },
                          { key: "logs", label: "案件日志" },
                        ],
                        onClick: ({ key }) => runSettlementMoreAction(key),
                      }}
                    >
                      <Button
                        disabled={!configuredRows.length}
                        loading={settlementActionLoading}
                      >
                        更多操作
                      </Button>
                    </Dropdown>
                  </Space>
                ) : isInternalDetailRoute ? (
                  <Dropdown
                    trigger={["click"]}
                    menu={{
                      items: [
                        { key: "selected", label: "导出选中" },
                        { key: "all", label: "导出全部" },
                      ],
                      onClick: ({ key }) =>
                        void exportInternalDetails(key === "selected"),
                    }}
                  >
                    <Button loading={internalDetailExportLoading}>导出</Button>
                  </Dropdown>
                ) : isInvoiceMineRoute || isInvoicePendingRoute || isInvoiceCompanyRoute ? (
                  <Space size={7}>
                    <Button
                      disabled={!configuredRows.length}
                      loading={invoiceExportLoading}
                      onClick={() => void exportInvoiceList(false)}
                    >
                      导出全部
                    </Button>
                    <Button
                      disabled={!configuredRows.length}
                      loading={invoiceExportLoading}
                      onClick={() => void exportInvoiceList(true)}
                    >
                      导出选中
                    </Button>
                  </Space>
                ) : initialView === "finance-internal-settle" ? (
                  <Space size={7}>
                    <Dropdown
                      trigger={["click"]}
                      menu={{
                        items: [
                          { key: "selected", label: "导出选中" },
                          { key: "all", label: "导出全部" },
                        ],
                        onClick: ({ key }) =>
                          exportConfiguredRows(key === "selected"),
                      }}
                    >
                      <Button>导出 ▾</Button>
                    </Dropdown>
                    <Dropdown
                      trigger={["click"]}
                      menu={{
                        items: [
                          { key: "upload", label: "上传案件文档" },
                          {
                            key: "new-fee",
                            label: "新增案件费用",
                            children: [
                              { key: "official-fee", label: "新增官费" },
                              { key: "agency-fee", label: "新增代理费" },
                              { key: "other-fee", label: "新增其他费用" },
                              { key: "internal-fee", label: "新增内部费用" },
                            ],
                          },
                          {
                            key: "batch-modify",
                            label: "批量修改",
                            children: [
                              { key: "hearing_lawyer", label: "修改开庭律师" },
                              {
                                key: "handling_lawyers",
                                label: "修改经办律师",
                              },
                              { key: "assistant", label: "修改律师助理" },
                              { key: "case_stage", label: "修改案件阶段" },
                            ],
                          },
                          { key: "authorization", label: "生成授权委托书" },
                          { key: "law-firm-letter", label: "生成律所函" },
                          { key: "identity", label: "生成身份证明" },
                          { key: "settlement", label: "生成结算提成表" },
                          { key: "tasks", label: "案件任务" },
                          { key: "logs", label: "案件日志" },
                        ],
                        onClick: ({ key }) => runSettlementMoreAction(key),
                      }}
                    >
                      <Button loading={settlementActionLoading}>
                        更多操作 ▾
                      </Button>
                    </Dropdown>
                    {canApprove && (
                      <Button
                        disabled={!selectedOriginalRows.length}
                        loading={settlementActionLoading}
                        onClick={() => runSettlementMoreAction("mark-paid")}
                      >
                        标记提成已发
                      </Button>
                    )}
                  </Space>
                ) : isRefundCaseFeeRoute ? (
                  <Space size={7} wrap>
                    <Dropdown
                      trigger={["click"]}
                      menu={{
                        items: [
                          { key: "selected", label: "导出选中" },
                          { key: "all", label: "导出全部" },
                        ],
                        onClick: ({ key }) => void exportFeeQuery(key === "selected"),
                      }}
                    >
                      <Button loading={feeQueryExportLoading}>导出 ▾</Button>
                    </Dropdown>
                    <Dropdown
                      trigger={["click"]}
                      menu={{
                        items: [
                          { key: "upload", label: "上传案件文档" },
                          {
                            key: "new-fee",
                            label: "新增案件费用",
                            children: [
                              { key: "official-fee", label: "新增官费" },
                              { key: "agency-fee", label: "新增代理费" },
                              { key: "other-fee", label: "新增其他费用" },
                            ],
                          },
                          { key: "internal-fee", label: "新增内部费用" },
                          {
                            key: "batch-modify",
                            label: "批量修改",
                            children: [
                              { key: "hearing_lawyer", label: "修改开庭律师" },
                              { key: "handling_lawyers", label: "修改经办律师" },
                              { key: "assistant", label: "修改律师助理" },
                              { key: "case_stage", label: "修改案件阶段" },
                            ],
                          },
                          { key: "authorization", label: "生成授权委托书" },
                          { key: "law-firm-letter", label: "生成律所函" },
                          { key: "identity", label: "生成身份证明" },
                          { key: "settlement", label: "生成结算提成表" },
                          { key: "tasks", label: "案件任务" },
                          { key: "logs", label: "案件日志" },
                        ],
                        onClick: ({ key }) => runSettlementMoreAction(key),
                      }}
                    >
                      <Button loading={settlementActionLoading}>更多操作 ▾</Button>
                    </Dropdown>
                    <RefundCaseFeeOperationMenu {...refundCaseFeeOperationMenu} />
                    {canManage && <RefundCaseFeeMarkButton {...refundCaseFeeMarkButton} />}
                  </Space>
                ) : isFeeQueryRoute ? (
                  <FinanceFeeQueryActions
                    exportLoading={feeQueryExportLoading}
                    actionLoading={settlementActionLoading}
                    onExport={exportFeeQuery}
                    onMoreAction={runSettlementMoreAction}
                  />
                ) : (
                  <Space>
                    <Button
                      disabled={!selectedOriginalRows.length}
                      onClick={() => exportConfiguredRows(true)}
                    >
                      导出选中
                    </Button>
                    <Button onClick={() => exportConfiguredRows(false)}>
                      导出全部
                    </Button>
                  </Space>
                )}
                {!isInternalDetailRoute && !isInvoiceMineRoute && !isInvoicePendingRoute && !isInvoiceCompanyRoute && !isInvoiceUnissuedRoute && (
                  <span>已选择 {selectedOriginalRows.length} 条</span>
                )}
              </div>
            )}
          </section>
    </>
  );
}
