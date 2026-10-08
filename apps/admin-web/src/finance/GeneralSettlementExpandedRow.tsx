import { Button, Space } from "antd";
import Table from "../components/ResizableTable";
import type { Fee, SettlementAllocationDetail } from "./types";

export interface GeneralSettlementExpandedRowProps {
  row: Fee;
  isPaymentRoute: boolean;
  isPaidRoute: boolean;
  isRejectedRoute: boolean;
  isAuditRoute: boolean;
  detailsExpanded: boolean;
  displayPersonName: (identity?: unknown, displayName?: unknown) => string;
  displayPersonNames: (identities?: unknown, displayNames?: unknown) => string;
  openTask: (source: { case_no?: unknown; customer?: unknown; data?: Record<string, unknown> }) => void;
  exportSettlement: (kind: "settlement" | "receipt" | "case", ids?: (string | number)[]) => Promise<void>;
  openCase: (caseNo: unknown) => void;
  openCustomer: (customer: string, customerNo?: string) => void;
  openContract: (contractNo: string) => void;
}

export function GeneralSettlementExpandedRow({
  row,
  isPaymentRoute: isGeneralSettlementPaymentRoute,
  isPaidRoute: isGeneralSettlementPaidRoute,
  isRejectedRoute: isGeneralSettlementRejectedRoute,
  isAuditRoute: isGeneralSettlementAuditRoute,
  detailsExpanded,
  displayPersonName: financePersonDisplayName,
  displayPersonNames: financePersonDisplayNames,
  openTask: openCaseTaskCreate,
  exportSettlement: exportGeneralSettlement,
  openCase: openCaseDetail,
  openCustomer: openCustomerDetail,
  openContract: openContractDetail,
}: GeneralSettlementExpandedRowProps) {
  return (
    <div className="finance-settlement-expanded">
      {isGeneralSettlementPaymentRoute ||
      isGeneralSettlementPaidRoute ? (
        <div className="finance-settlement-payment-context">
          <span>
            审核时间: {String(row.data?.reviewed_at || "").replace("T", " ")}
            <br />提交时间: {String(row.data?.applied_at || row.created_at || "").replace("T", " ")}
          </span>
          <span>
            审核人: {financePersonDisplayName(row.data?.reviewer, row.data?.reviewer_display_name)}
            <br />提交人: {financePersonDisplayName(row.data?.applied_by || row.owner, row.data?.applied_by_display_name || row.data?.owner_display_name)}
          </span>
          <span>
            审核备注: <em>{row.data?.review_comment || ""}</em>
            <br />提交备注: {row.description || ""}
          </span>
          {isGeneralSettlementPaidRoute && (
            <span>
              <br />付款日期: {String(row.data?.paid_at || "").replace("T", " ")}
            </span>
          )}
          <span>
            回款方式: {row.data?.payment_method || "—"}
            <br />银行备注: {row.data?.bank_remark || ""}
          </span>
        </div>
      ) : isGeneralSettlementRejectedRoute ? (
        <div className="finance-settlement-rejected-context">
          <span>
            审核时间: {String(row.data?.reviewed_at || "").replace("T", " ")}
            <br />提交时间: {String(row.data?.applied_at || row.created_at || "").replace("T", " ")}
          </span>
          <span>
            审核人: {financePersonDisplayName(row.data?.reviewer, row.data?.reviewer_display_name)}
            <br />提交人: {financePersonDisplayName(row.data?.applied_by || row.owner, row.data?.applied_by_display_name || row.data?.owner_display_name)}
          </span>
          <span>
            审核备注: <em>{row.data?.review_comment || row.data?.rejection_comment || ""}</em>
            <br />提交备注: {row.description || ""}
          </span>
          <span>
            回款方式: {row.data?.payment_method || "—"}
            <br />银行备注: {row.data?.bank_remark || ""}
          </span>
        </div>
      ) : isGeneralSettlementAuditRoute ? (
        <div className="finance-settlement-audit-context">
          <span>
            提交时间: {String(row.data?.applied_at || row.created_at || "").replace("T", " ")}
            <br />提交人: {financePersonDisplayName(row.data?.applied_by || row.owner, row.data?.applied_by_display_name || row.data?.owner_display_name)}
          </span>
          <span>
            提交备注:
            <br />{row.description || ""}
          </span>
          <span>
            回款方式: {row.data?.payment_method || "—"}
            <br />银行备注: {row.data?.bank_remark || ""}
          </span>
        </div>
      ) : (
        <>
          <div className="finance-settlement-context">
            <span>
              回款方式: {row.data?.payment_method || "—"}
            </span>
            <span>
              银行备注: {row.data?.bank_remark || ""}
            </span>
          </div>
          <div className="finance-settlement-review-note">
            回退结算审核备注: {row.data?.rejection_comment || ""}
          </div>
        </>
      )}
      {detailsExpanded && (
        <Table
          className="finance-settlement-detail-table"
          rowKey={(detail: SettlementAllocationDetail) => detail.detail_id}
          size="small"
          pagination={false}
          dataSource={row.data?.allocation_details || []}
          scroll={{ x: "max-content" }}
          columns={[
            {
              title: <span className="finance-stacked-header"><span>序</span><span>号</span></span>,
              width: 43,
              render: (_v, _detail, index) => index + 1,
            },
            {
              title: <span className="finance-stacked-header"><span>操</span><span>作</span></span>,
              width: 115,
              render: (_v, detail: SettlementAllocationDetail) => (
                <Space size={0}>
                  <Button type="link" title="新建案件任务" onClick={() => openCaseTaskCreate(detail)}>✉</Button>
                  <Button type="link" title="导出结算清单" onClick={() => void exportGeneralSettlement("settlement", [row.id])}>▣</Button>
                  <Button type="link" title="导出结算列表" onClick={() => void exportGeneralSettlement("case", [row.id])}>▦</Button>
                </Space>
              ),
            },
            { title: "案号", dataIndex: "case_no", width: 144, render: (value) => value ? <Button type="link" onClick={() => openCaseDetail(value)}>{value}</Button> : "—" },
            { title: "阶段", dataIndex: "case_stage", width: 115 },
            { title: <span className="finance-stacked-header"><span>费用</span><span>类型</span></span>, dataIndex: "fee_type", width: 115 },
            { title: <span className="finance-stacked-header"><span>费用</span><span>总金额</span></span>, dataIndex: "fee_total_amount", width: 115, align: "right", render: (value) => value == null ? "—" : Number(value).toFixed(2) },
            { title: <span className="finance-stacked-header"><span>费用</span><span>分配金额</span></span>, dataIndex: "fee_allocated_amount", width: 115, align: "right", render: (value) => value == null ? "—" : Number(value).toFixed(2) },
            { title: <span className="finance-stacked-header"><span>本笔</span><span>分配金额</span></span>, dataIndex: "current_amount", width: 115, align: "right", render: (value) => value == null ? "—" : Number(value).toFixed(2) },
            { title: <span className="finance-stacked-header"><span>本笔</span><span>分配日期</span></span>, dataIndex: "allocated_at", width: 173, render: (value) => String(value || "").replace("T", " ") || "—" },
            { title: <span className="finance-stacked-header"><span>本笔</span><span>结算金额</span></span>, dataIndex: "settlement_amount", width: 115, align: "right", render: (value) => value == null ? "—" : Number(value).toFixed(2) },
            { title: <span className="finance-stacked-header"><span>本笔</span><span>归档费</span></span>, dataIndex: "archive_fee", width: 115, align: "right", render: (value) => value == null ? "—" : Number(value).toFixed(2) },
            { title: "客户", dataIndex: "customer", width: 216, render: (value, detail: SettlementAllocationDetail) => value ? <Button type="link" onClick={() => openCustomerDetail(value, detail.customer_no)}>{value}</Button> : "—" },
            { title: <span className="finance-stacked-header"><span>经办</span><span>律师</span></span>, dataIndex: "handling_lawyer", width: 115, render: (value, detail: SettlementAllocationDetail) => financePersonDisplayNames(detail.handling_lawyers || value, detail.handling_lawyer_display_names || detail.handling_lawyer_display_name) },
            { title: <span className="finance-stacked-header"><span>律师</span><span>助理</span></span>, dataIndex: "assistant", width: 115, render: (value, detail: SettlementAllocationDetail) => financePersonDisplayName(value, detail.assistant_display_name || detail.lawyer_assistant_display_name) },
            { title: "合同号", dataIndex: "contract_no", width: 144, render: (value) => value ? <Button type="link" onClick={() => openContractDetail(value)}>{value}</Button> : "—" },
          ]}
        />
      )}
    </div>
  );
}
