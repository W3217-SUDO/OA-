import type { FormInstance } from "antd";
import {
Button,
Card,
DatePicker,
Form,
Input,
Select,
Space,
Table,
Tag,message
} from "antd";
import dayjs from "dayjs";
import type { Key } from "react";
import { ListFilterBar } from "../components/common/ListFilterBar";
import { displayContractStatus } from "../contractStatusPresentation.mjs";
import { contractListActionPolicy,contractSecondaryActionPolicy } from "../contractWorkflowPolicy.mjs";
import RecordImportButton from "../RecordImportButton";
import {
CONTRACT_SEAL_READY_STATUSES,
amount,
moneyKeys,
} from "./constants";
import type { Contract,ContractWorkflowCapabilities } from "./types";

interface ContractListProps {
  initialView: string;
  queryForm: FormInstance;
  isArchiveView: boolean;
  isAuditView: boolean;
  loading: boolean;
  rows: Contract[];
  listTotal: number;
  listPagination: { current: number; pageSize: number };
  selectedRowKeys: Key[];
  selected: Contract | undefined;
  selectedActionPolicy: ReturnType<typeof contractListActionPolicy>;
  selectedSecondaryActionPolicy: ReturnType<typeof contractSecondaryActionPolicy>;
  selectedContractCapabilities: ContractWorkflowCapabilities;
  auditActionPolicy: { canReview: boolean; canReviewChange: boolean; canExport: boolean };
  profileDisplayName: string;
  profileUsername: string;
  totals: Record<string, number>;
  personName: (value: unknown) => string;
  peopleNames: (value: unknown) => string;
  contractCapabilities: (contract?: Contract | null, options?: Record<string, unknown>) => ContractWorkflowCapabilities;
  canOpenSubmitWizard: (contract: Contract) => boolean;
  onQuery: (values: Record<string, any>) => void;
  onClearQuery: () => void;
  onPageChange: (page: number, pageSize: number) => void;
  onSelectionChange: (keys: Key[]) => void;
  onView: (contract: Contract) => void;
  onEdit: (contract: Contract) => void;
  onSeal: (contract: Contract) => void;
  onOpenAttachments: (contract: Contract) => void;
  onOpenApprovalInfo: (contract: Contract) => void;
  onOpenRelatedCase: (contract: Contract) => void;
  onOpenRelatedCustomer: (contract: Contract) => void;
  onCreateCase: (contract: Contract) => void;
  onSubmitWizard: (contract: Contract) => void;
  onRevokeDraft: (contract: Contract) => void;
  onDeleteRecycled: (contract: Contract) => void;
  onDeleteCompany: (contract: Contract) => void;
  onChangeContract: (contract: Contract) => void;
  onPayment: (contract: Contract) => void;
  onInvoice: (contract: Contract) => void;
  onInvestigation: (contract: Contract) => void;
  onApprove: (contract: Contract) => void;
  onReviewChange: (contract: Contract, approved: boolean) => void;
  onExportExcel: () => void;
  onExportCsv: () => void;
  onImport: () => void;
}

export function ContractList({
  initialView,
  queryForm,
  isArchiveView,
  isAuditView,
  loading,
  rows,
  listTotal,
  listPagination,
  selectedRowKeys,
  selected,
  selectedActionPolicy,
  selectedSecondaryActionPolicy,
  selectedContractCapabilities,
  auditActionPolicy,
  profileDisplayName,
  profileUsername,
  totals,
  personName,
  peopleNames,
  contractCapabilities,
  canOpenSubmitWizard,
  onQuery,
  onClearQuery,
  onPageChange,
  onSelectionChange,
  onView,
  onEdit,
  onSeal,
  onOpenAttachments,
  onOpenApprovalInfo,
  onOpenRelatedCase,
  onOpenRelatedCustomer,
  onCreateCase,
  onSubmitWizard,
  onRevokeDraft,
  onDeleteRecycled,
  onDeleteCompany,
  onChangeContract,
  onPayment,
  onInvoice,
  onInvestigation,
  onApprove,
  onReviewChange,
  onExportExcel,
  onExportCsv,
}: ContractListProps) {
  const textCell = (value: string) => displayContractStatus(value);

  const moneyColumn = (title: string, key: (typeof moneyKeys)[number]) => ({
    title: (
      <span>
        {title.split("|")[0]}
        <br />
        {title.split("|")[1] || ""}
      </span>
    ),
    key,
    width: 76,
    align: "right" as const,
    render: (_: unknown, r: Contract) => String(r.data[key] ?? 0),
  });

  const columns = [
    {
      title: "合同号",
      dataIndex: "serial_no",
      width: 160,
      ellipsis: true,
      render: (v: string, r: Contract) => (
        <Button type="link" className="contract-cell-link" title={v} onClick={() => onView(r)}>
          {v}
        </Button>
      ),
    },
    {
      title: "合同名称",
      dataIndex: "title",
      width: 220,
      ellipsis: true,
      render: (value: string) => (
        <span className="contract-cell-text" title={value}>
          {value}
        </span>
      ),
    },
    {
      title: "合同主体",
      key: "body",
      width: 74,
      render: (_: unknown, r: Contract) => r.data.contract_body || "律所",
    },
    { title: "合同状态", dataIndex: "status", width: 74, render: textCell },
    {
      title: "客户管理人",
      key: "customerManager",
      width: 120,
      ellipsis: true,
      render: (_: unknown, r: Contract) =>
        peopleNames(
          (r.data as any).customer_manager_display_names ||
            (r.data as any).customer_manager ||
            (r.data as any).customer_managers ||
            r.owner,
        ),
    },
    {
      title: "签订日期",
      key: "signedAt",
      width: 108,
      render: (_: unknown, r: Contract) => (r.data as any).signed_at || "—",
    },
    {
      title: "客户编号",
      key: "customerNo",
      width: 118,
      render: (_: unknown, r: Contract) =>
        r.data.customer_no ? (
          <Button type="link" className="contract-cell-link" onClick={() => onOpenRelatedCustomer(r)}>
            {r.data.customer_no}
          </Button>
        ) : (
          "—"
        ),
    },
    {
      title: "客户名称",
      dataIndex: "customer",
      width: 190,
      ellipsis: true,
      render: (value: string, r: Contract) =>
        value ? (
          <Button type="link" className="contract-cell-link" onClick={() => onOpenRelatedCustomer(r)}>
            {value}
          </Button>
        ) : (
          "—"
        ),
    },
    {
      title: "案源人",
      key: "source",
      width: 74,
      render: (_: unknown, r: Contract) =>
        personName(
          (r.data as any).source_person_display_name || r.data.source_person || (r as any).owner_display_name || r.owner,
        ),
    },
    moneyColumn("官费|支付金额", "official_paid"),
    moneyColumn("官费|到账金额", "official_received"),
    moneyColumn("官费|未到金额", "official_unreceived"),
    moneyColumn("官费|亏损金额", "official_loss"),
    moneyColumn("代理费|总金额", "agency_total"),
    moneyColumn("代理费|到账金额", "agency_received"),
    moneyColumn("代理费|待收金额", "agency_due"),
    moneyColumn("其他金额", "other_total"),
    moneyColumn("其他金额|已支付", "other_paid"),
    moneyColumn("其他金额|待支付", "other_due"),
    moneyColumn("发票|已开金额", "invoice_opened"),
    moneyColumn("发票|应开金额", "invoice_should"),
    moneyColumn("发票|高开金额", "invoice_excess"),
    {
      title: "操作",
      key: "operations",
      width: 150,
      fixed: "right" as const,
      render: (_: unknown, r: Contract) => (
        <Space size={0}>
          {contractCapabilities(r).canEdit && (
            <Button type="link" onClick={() => onEdit(r)}>
              编辑合同
            </Button>
          )}
          {CONTRACT_SEAL_READY_STATUSES.includes(r.status) && (
            <Button type="link" onClick={() => onSeal(r)}>
              合同用印
            </Button>
          )}
          <Button type="link" onClick={() => onOpenAttachments(r)}>
            合同附件
          </Button>
          <Button type="link" onClick={() => onOpenApprovalInfo(r)}>
            审批信息
          </Button>
          <Button type="link" onClick={() => onOpenRelatedCase(r)}>
            关联案件
          </Button>
          <Button
            type="link"
            disabled={!contractListActionPolicy(r.status).canCreateCase}
            title={
              contractListActionPolicy(r.status).canCreateCase
                ? "以该合同和客户新建案件"
                : "只能从审批中、审批通过或已完成的合同新建案件"
            }
            onClick={() => onCreateCase(r)}
          >
            新建案件
          </Button>
          {canOpenSubmitWizard(r) && contractCapabilities(r).canSubmit && (
            <Button type="link" onClick={() => onSubmitWizard(r)}>
              重新上传
            </Button>
          )}
          {canOpenSubmitWizard(r) && contractCapabilities(r).canSubmit && (
            <Button type="link" onClick={() => onSubmitWizard(r)}>
              提交审批
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const auditColumns = [
    columns[0],
    columns[1],
    { title: "合同状态", dataIndex: "status", width: 88, render: textCell },
    {
      title: "合同总金额",
      key: "amount",
      width: 105,
      align: "right" as const,
      render: (_: unknown, r: Contract) => amount(r.data.amount),
    },
    moneyColumn("回款累计", "agency_received"),
    moneyColumn("应收代理费", "agency_due"),
    moneyColumn("未到账垫付款", "official_unreceived"),
    {
      title: "案源人",
      key: "source",
      width: 90,
      render: (_: unknown, r: Contract) =>
        personName(
          (r.data as any).source_person_display_name || r.data.source_person || (r as any).owner_display_name || r.owner,
        ),
    },
    {
      title: "客户管理人",
      key: "customerManager",
      width: 100,
      render: (_: unknown, r: Contract) =>
        peopleNames(
          (r.data as any).customer_manager_display_names || r.data.customer_manager || (r.data as any).customer_managers,
        ),
    },
    {
      title: "签订日期",
      key: "signedAt",
      width: 105,
      render: (_: unknown, r: Contract) => r.data.signed_at || "—",
    },
    {
      title: "客户编号",
      key: "customerNo",
      width: 105,
      render: (_: unknown, r: Contract) =>
        r.data.customer_no ? (
          <Button type="link" className="contract-cell-link" onClick={() => onOpenRelatedCustomer(r)}>
            {r.data.customer_no}
          </Button>
        ) : (
          "—"
        ),
    },
    {
      title: "客户名称",
      dataIndex: "customer",
      width: 180,
      ellipsis: true,
      render: (value: string, r: Contract) =>
        value ? (
          <Button type="link" className="contract-cell-link" onClick={() => onOpenRelatedCustomer(r)}>
            {value}
          </Button>
        ) : (
          "—"
        ),
    },
  ];

  const archiveColumns = [
    columns[0],
    columns[1],
    {
      title: "客户名称",
      dataIndex: "customer",
      width: 190,
      ellipsis: true,
      render: (value: string, row: Contract) =>
        value ? (
          <Button type="link" className="contract-cell-link" onClick={() => onOpenRelatedCustomer(row)}>
            {value}
          </Button>
        ) : (
          "—"
        ),
    },
    {
      title: "归档状态",
      dataIndex: "archive_status",
      width: 100,
      render: (value: Contract["archive_status"]) => (
        <Tag color={value === "已归档" ? "green" : "orange"}>{value || "—"}</Tag>
      ),
    },
    {
      title: "归档日期",
      dataIndex: "archive_date",
      width: 130,
      render: (value: string) => (value ? dayjs(value).format("YYYY-MM-DD") : "—"),
    },
    {
      title: "负责人",
      dataIndex: "owner",
      width: 110,
      render: (value: string) => personName(value),
    },
    { title: "部门", dataIndex: "department", width: 130 },
    {
      title: "操作",
      width: 90,
      fixed: "right" as const,
      render: (_: unknown, row: Contract) => (
        <Button type="link" onClick={() => onView(row)}>
          查看
        </Button>
      ),
    },
  ];

  const needSelected = (callback: () => void) => {
    if (!selected) return;
    callback();
  };

  return (
    <Card className="panel contract-original-panel" title="合同查询">
      <ListFilterBar form={queryForm} className="contract-query" onFinish={onQuery}>
        <Form.Item label="合同编号" name="serial_no">
          <Input placeholder="合同编号" />
        </Form.Item>
        <Form.Item label="客户名称" name="customer">
          <Input placeholder="客户名称" />
        </Form.Item>
        {isArchiveView ? (
          <>
            <Form.Item label="归档状态" name="archive_status">
              <Select
                allowClear
                placeholder="全部状态"
                options={["归档中", "已归档"].map((value) => ({ value, label: value }))}
              />
            </Form.Item>
            <Form.Item label="归档日期" name="archive_date">
              <DatePicker.RangePicker />
            </Form.Item>
          </>
        ) : (
          <>
            <Form.Item label="合同名称" name="title">
              <Input placeholder="合同名称" />
            </Form.Item>
            <Form.Item label="合同类型" name="type">
              <Select
                allowClear
                placeholder="请选择"
                options={["法律顾问合同", "争议解决合同", "框架合作合同", "非诉项目合同", "其他"].map(
                  (value) => ({ value, label: value }),
                )}
              />
            </Form.Item>
            <Form.Item label={isAuditView ? "案号" : "案件编号"} name="case_no">
              <Input placeholder="案号" />
            </Form.Item>
            <Form.Item label="收费类型" name="fee_type">
              <Select
                allowClear
                placeholder="请选择"
                options={["固定收费", "固定+后期", "免费代理", "法律援助", "计时收费", "全风险代理"].map(
                  (value) => ({ value, label: value }),
                )}
              />
            </Form.Item>
            <Form.Item label="合同日期" name="signed_at">
              <DatePicker.RangePicker />
            </Form.Item>
            {initialView === "contract-mine" ? (
              <Form.Item label="案源人">
                <Input disabled value={personName(profileDisplayName || profileUsername)} />
              </Form.Item>
            ) : (
              <Form.Item label="案源人" name="source_person">
                <Input placeholder="案源人" />
              </Form.Item>
            )}
            <Form.Item label="合同主体" name="contract_body">
              <Select
                allowClear
                placeholder="请选择"
                options={["律所", "平台"].map((value) => ({ value, label: value }))}
              />
            </Form.Item>
          </>
        )}
        <Form.Item className="contract-query-submit">
          <Space>
            <Button type="primary" htmlType="submit">
              查询
            </Button>
            <Button htmlType="button" onClick={onClearQuery}>
              清空
            </Button>
          </Space>
        </Form.Item>
      </ListFilterBar>
      <Table
        className="contract-original-table"
        rowKey="id"
        size="small"
        loading={loading}
        columns={isArchiveView ? archiveColumns : isAuditView ? auditColumns : columns}
        dataSource={rows}
        rowSelection={{
          selectedRowKeys,
          onChange: (keys) => {
            onSelectionChange(keys.length ? [keys[keys.length - 1]] : []);
          },
        }}
        tableLayout="fixed"
        scroll={{ x: isArchiveView || isAuditView ? 1450 : 2360, y: "calc(100dvh - 390px)" }}
        pagination={{
          current: listPagination.current,
          pageSize: listPagination.pageSize,
          total: listTotal,
          showSizeChanger: true,
          pageSizeOptions: [10, 15, 20, 50, 100, 200],
          showQuickJumper: { goButton: <Button size="small">GO</Button> },
          showTotal: (total) => `共有${total}条`,
          onChange: onPageChange,
        }}
        summary={
          isArchiveView || isAuditView
            ? undefined
            : () => (
                <Table.Summary>
                  <Table.Summary.Row className="contract-total-row">
                    <Table.Summary.Cell index={0} colSpan={6}>
                      本页合计
                    </Table.Summary.Cell>
                    {moneyKeys.map((key, index) => (
                      <Table.Summary.Cell key={key} index={index + 6} align="right">
                        {amount(totals[key])}
                      </Table.Summary.Cell>
                    ))}
                  </Table.Summary.Row>
                </Table.Summary>
              )
        }
      />
      {isArchiveView && (
        <div className="contract-bottom-actions">
          <Space size={4} wrap>
            <Button onClick={onExportExcel}>导出Excel</Button>
            <Button onClick={() => needSelected(() => onView(selected!))}>合同查看</Button>
          </Space>
        </div>
      )}
      {!isArchiveView && !isAuditView && (
        <div className="contract-bottom-actions">
          <Space size={4} wrap>
            <RecordImportButton module="contract" onImported={() => onQuery(queryForm.getFieldsValue())} />
            <Button onClick={onExportExcel}>导出Excel</Button>
            <Button onClick={onExportCsv}>导出CSV</Button>
            <Button onClick={() => needSelected(() => onView(selected!))}>合同查看</Button>
            <Button
              danger
              disabled={!selected || selected.status !== "草稿"}
              onClick={() => needSelected(() => onRevokeDraft(selected!))}
            >
              撤销草稿
            </Button>
            {initialView === "contract-company" ? (
              <Button
                danger
                disabled={!selected}
                onClick={() => needSelected(() => onDeleteCompany(selected!))}
              >
                删除合同
              </Button>
            ) : (
              <Button
                danger
                disabled={!selected || selected.status !== "已回收"}
                onClick={() => needSelected(() => onDeleteRecycled(selected!))}
              >
                删除合同
              </Button>
            )}
            <Button
              disabled={!selectedContractCapabilities.canChange}
              onClick={() => needSelected(() => onChangeContract(selected!))}
            >
              合同变更
            </Button>
            <Button onClick={() => needSelected(() => onSeal(selected!))}>合同用印</Button>
            <Button
              disabled={!selectedContractCapabilities.canPayment}
              onClick={() => needSelected(() => onPayment(selected!))}
            >
              合同付款
            </Button>
            <Button
              disabled={!selectedContractCapabilities.canInvoice}
              onClick={() => needSelected(() => onInvoice(selected!))}
            >
              合同开票
            </Button>
            <Button
              disabled={!selectedActionPolicy.canCreateCase}
              onClick={() => needSelected(() => onCreateCase(selected!))}
            >
              新建案件
            </Button>
            <Button
              disabled={!selectedSecondaryActionPolicy.canInvestigation}
              onClick={() => needSelected(() => onInvestigation(selected!))}
            >
              新建调查任务
            </Button>
          </Space>
        </div>
      )}
      {isAuditView &&
        (!["contract-audit-pending", "contract-audit-refused", "contract-audit-approved"].includes(initialView) ||
          rows.length > 0) && (
          <div className="contract-bottom-actions">
            <Space>
              <Button onClick={onExportExcel}>导出Excel</Button>
              <Button onClick={onExportCsv}>导出CSV</Button>
              {auditActionPolicy.canReview && (
                <Button
                  type="primary"
                  disabled={!selectedContractCapabilities.canOpenApproval}
                  onClick={() =>
                    needSelected(() => {
                      if (selected?.status !== "审批中") return message.warning("所选合同不在待审批状态");
                      onApprove(selected!);
                    })
                  }
                >
                  合同审批
                </Button>
              )}
              {auditActionPolicy.canReviewChange && (
                <>
                  <Button
                    disabled={!selectedContractCapabilities.canReviewChange}
                    onClick={() =>
                      needSelected(() => {
                        if (selected?.data.pending_change?.status !== "待审批") return message.warning("所选合同没有待审批变更");
                        onReviewChange(selected!, true);
                      })
                    }
                  >
                    通过合同变更
                  </Button>
                  <Button
                    danger
                    disabled={!selectedContractCapabilities.canReviewChange}
                    onClick={() =>
                      needSelected(() => {
                        if (selected?.data.pending_change?.status !== "待审批") return message.warning("所选合同没有待审批变更");
                        onReviewChange(selected!, false);
                      })
                    }
                  >
                    驳回合同变更
                  </Button>
                </>
              )}
            </Space>
          </div>
        )}
    </Card>
  );
}
