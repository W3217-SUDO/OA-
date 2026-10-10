import {PlusOutlined, ReloadOutlined} from "@ant-design/icons";
import {Alert, Button, Card, Space, Tabs} from "antd";
import Table from "../components/ResizableTable";

import RecordImportButton from "../RecordImportButton";

import {FinanceStatsCards} from "./FinanceStatsCards";
import {FinanceReceiptsActions, FinanceReceiptsTable, type FinanceReceiptsViewProps} from "./FinanceReceiptsView";
import {FinanceRefundsActions, FinanceRefundsTable, type FinanceRefundsViewProps} from "./FinanceRefundsView";
import {FinanceInvoicesActions, FinanceInvoicesTable, type FinanceInvoicesViewProps} from "./FinanceInvoicesView";

import {LegacyHistoryPanel} from "./LegacyHistoryPanel";

import type {Fee, FinanceFlow, FinanceSummary, LegacyFinanceRecord, LegacyFinanceSummary, Reconciliation, Transaction} from "./types";

export interface FinanceStandardTabsViewProps {
  receiptsView: FinanceReceiptsViewProps;
  refundsView: FinanceRefundsViewProps;
  invoicesView: FinanceInvoicesViewProps;
  tab: string;
  setTab: (tab: string) => void;
  isRefundNotRequiredRoute: boolean;
  loading: boolean;
  summary: FinanceSummary;
  canApprove: boolean;
  currentUser: { username: string; displayName: string };
  load: () => Promise<void>;
  financeProjectionEnabled: boolean;
  financeFeeListMeta: { total: number; page: number; pageSize: number };
  financeTransactionMeta: { total: number; page: number; pageSize: number };
  loadFinanceProjectionPage: (kind: "fees" | "transactions", page?: number, pageSize?: number) => Promise<void>;
  shownFees: Fee[];
  feeColumns: any[];
  invoices: FinanceFlow[];
  transactions: Transaction[];
  transactionColumns: any[];
  setFeeOpen: (open: boolean) => void;
  setFeeEditTarget: (fee: Fee | null) => void;
  feeForm: any;
  setFeeTypeOverride: (type: string) => void;
  legacyFinanceRows: LegacyFinanceRecord[];
  legacyFinanceLoading: boolean;
  legacyFinanceMeta: { total: number; page: number; pageSize: number };
  legacyFinanceSummary: LegacyFinanceSummary;
  legacyFinanceDetail: LegacyFinanceRecord | null;
  setLegacyFinanceDetail: (detail: LegacyFinanceRecord | null) => void;
  legacyFinanceDetailLoading: boolean;
  setLegacyFinanceDetailLoading: (loading: boolean) => void;
  legacyFinanceKeyword: string;
  setLegacyFinanceKeyword: (keyword: string) => void;
  legacyFinanceKind: string;
  setLegacyFinanceKind: (kind: string) => void;
  legacyFinanceStatusCode: string;
  setLegacyFinanceStatusCode: (code: string) => void;
  legacyFinanceIncludeInactive: boolean;
  setLegacyFinanceIncludeInactive: (include: boolean) => void;
  loadLegacyFinanceHistory: (...args: any[]) => Promise<void>;
  openLegacyFinanceDetail: (recordId: number) => Promise<void>;
  reconcileColumns: any[];
  reconciliations: Reconciliation[];
  onOpenReconciliation: () => void;
}

export function FinanceStandardTabsView(props: FinanceStandardTabsViewProps) {
  const {
    receiptsView,
    refundsView,
    invoicesView,
    tab,
    setTab,
    isRefundNotRequiredRoute,
    loading,
    summary,
    canApprove,
    currentUser,
    load,
    financeProjectionEnabled,
    financeFeeListMeta,
    financeTransactionMeta,
    loadFinanceProjectionPage,
    shownFees,
    feeColumns,
    invoices,
    transactions,
    transactionColumns,
    setFeeOpen,
    setFeeEditTarget,
    feeForm,
    setFeeTypeOverride,
    legacyFinanceRows,
    legacyFinanceLoading,
    legacyFinanceMeta,
    legacyFinanceSummary,
    legacyFinanceDetail,
    setLegacyFinanceDetail,
    legacyFinanceDetailLoading,
    setLegacyFinanceDetailLoading,
    legacyFinanceKeyword,
    setLegacyFinanceKeyword,
    legacyFinanceKind,
    setLegacyFinanceKind,
    legacyFinanceStatusCode,
    setLegacyFinanceStatusCode,
    legacyFinanceIncludeInactive,
    setLegacyFinanceIncludeInactive,
    loadLegacyFinanceHistory,
    openLegacyFinanceDetail,
    reconcileColumns,
    reconciliations,
    onOpenReconciliation,
  } = props;
  return (
          <>
            {isRefundNotRequiredRoute && (
              <div className="finance-original-title">
                <h5>不再办理退费案件</h5>
              </div>
            )}
            <Alert
              className="finance-rule"
              type="info"
              showIcon
              title="费用审批要素"
              description="官方费用提交前必须具备案件人员、法院和缴费通知文档三要素；内部费用允许用负数冲销，金额按两位小数进位。审批通过后才能付款。"
            />
            <FinanceStatsCards summary={summary} />
            <Card
              className="panel"
              title="财务中心"
              extra={
                <Space>
                  {["fees", "audit"].includes(tab) && (
                    <RecordImportButton module="finance" onImported={load} />
                  )}
                  <Button icon={<ReloadOutlined />} onClick={load}>
                    刷新
                  </Button>
                  {tab === "receipts" && <FinanceReceiptsActions {...receiptsView} />}
                  {["fees", "audit"].includes(tab) && (
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={() => {
                        setFeeEditTarget(null);
                        feeForm.resetFields();
                        feeForm.setFieldsValue({
                          fee_type: "官方费用",
                          handler:
                            currentUser.displayName || "姓名待维护",
                        });
                        setFeeTypeOverride("官方费用");
                        setFeeOpen(true);
                      }}
                    >
                      新增费用
                    </Button>
                  )}
                  {tab === "invoices" && <FinanceInvoicesActions {...invoicesView} />}
                  {tab === "refunds" && <FinanceRefundsActions {...refundsView} />}
                  {tab === "reconcile" && canApprove && (
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={onOpenReconciliation}
                    >
                      生成对账单
                    </Button>
                  )}
                </Space>
              }
            >
              <Tabs
                activeKey={tab}
                onChange={setTab}
                items={[
                  { key: "legacy-history", label: "历史财务账本" },
                  { key: "fees", label: "费用管理" },
                  {
                    key: "audit",
                    label: `费用审批（${summary.pending || 0}）`,
                  },
                  {
                    key: "receipts",
                    label: `回款管理（待认领 ${summary.incoming_unclaimed || 0}）`,
                  },
                  {
                    key: "invoices",
                    label: `发票申请（${invoices.filter((x) => x.status === "待审批").length}）`,
                  },
                  {
                    key: "refunds",
                    label: `诉讼费退款（${refundsView.rows.filter((x) => x.status === "待审批").length}）`,
                  },
                  { key: "transactions", label: "财务流水" },
                  { key: "reconcile", label: "周/月对账" },
                ]}
              />
              {["fees", "audit"].includes(tab) ? (
                <Table
                  rowKey="id"
                  loading={loading}
                  size="small"
                  columns={feeColumns}
                  dataSource={shownFees}
                  scroll={{ x: 1500 }}
                  pagination={financeProjectionEnabled ? {
                    current: financeFeeListMeta.page,
                    pageSize: financeFeeListMeta.pageSize,
                    total: financeFeeListMeta.total,
                    showSizeChanger: true,
                    pageSizeOptions: [20, 50, 100, 200],
                    onChange: (page, pageSize) => void loadFinanceProjectionPage("fees", page, pageSize),
                  } : undefined}
                />
              ) : tab === "receipts" ? (
                <FinanceReceiptsTable {...receiptsView} />
              ) : tab === "invoices" ? (
                <FinanceInvoicesTable {...invoicesView} />
              ) : tab === "refunds" ? (
                <FinanceRefundsTable {...refundsView} />
              ) : tab === "transactions" ? (
                <Table
                  rowKey="id"
                  loading={loading}
                  size="small"
                  columns={transactionColumns}
                  dataSource={transactions}
                  scroll={{ x: 1500 }}
                  pagination={financeProjectionEnabled ? {
                    current: financeTransactionMeta.page,
                    pageSize: financeTransactionMeta.pageSize,
                    total: financeTransactionMeta.total,
                    showSizeChanger: true,
                    pageSizeOptions: [20, 50, 100, 200],
                    onChange: (page, pageSize) => void loadFinanceProjectionPage("transactions", page, pageSize),
                  } : undefined}
                />
              ) : tab === "legacy-history" ? (
                <LegacyHistoryPanel
                  rows={legacyFinanceRows}
                  loading={legacyFinanceLoading}
                  meta={legacyFinanceMeta}
                  summary={legacyFinanceSummary}
                  detail={legacyFinanceDetail}
                  detailLoading={legacyFinanceDetailLoading}
                  keyword={legacyFinanceKeyword}
                  kind={legacyFinanceKind}
                  statusCode={legacyFinanceStatusCode}
                  includeInactive={legacyFinanceIncludeInactive}
                  onKeywordChange={setLegacyFinanceKeyword}
                  onKindChange={setLegacyFinanceKind}
                  onStatusCodeChange={setLegacyFinanceStatusCode}
                  onIncludeInactiveChange={setLegacyFinanceIncludeInactive}
                  onLoad={loadLegacyFinanceHistory}
                  onOpenDetail={openLegacyFinanceDetail}
                  onCloseDetail={() => {
                    setLegacyFinanceDetail(null);
                    setLegacyFinanceDetailLoading(false);
                  }}
                />
              ) : (
                <Table
                  rowKey="id"
                  loading={loading}
                  size="small"
                  columns={reconcileColumns}
                  dataSource={reconciliations}
                  scroll={{ x: 1150 }}
                />
              )}
            </Card>
          </>
  );
}
