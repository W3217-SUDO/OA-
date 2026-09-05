import {
Alert,
Button,
Checkbox,
Descriptions,Divider,Empty,
Input,
Pagination,
Popconfirm,
Space,
Table,Tag,
Timeline
} from "antd";
import dayjs from "dayjs";
import type { Key } from "react";
import { DetailTabs } from "../components/common/DetailTabs";
import {
CONTRACT_OBJECT_PAGE_SIZES,
paginateContractObjectRows,
} from "../contractObjectListPolicy.mjs";
import {
contractObjectActionPolicy,
contractObjectHasLogs,
normalizeIncomingPaymentForContract,
normalizeInvoiceObject,
normalizePaidObject,
} from "../contractObjectPresentation.mjs";
import { displayContractStatus } from "../contractStatusPresentation.mjs";
import {
buildContractEventsRequest,
CONTRACT_EVENT_PAGE_SIZES,
contractAttachmentActionPolicy,
} from "../contractWorkflowPolicy.mjs";
import { LegacyContractHistoryPanel } from "../LegacyContractHistoryPanel";
import { legacyAttachmentQuarantineLabel,legacyAttachmentRecoveryLabel } from "../legacyHistoricalAttachmentPresentation";
import { amount,archiveCheckLabels } from "./constants";
import type {
Attachment,
Contract,
ContractArchiveSubject,
ContractArchiveSummary,
ContractEvent,
ContractObjectRow,
ContractWorkflowCapabilities,
LegacyHistoricalAttachment,
Step,
} from "./types";

interface ContractDetailViewProps {
  viewing: Contract | null;
  isContractDetailView: boolean;
  detailActiveTab: string;
  contractObjects: ContractObjectRow[];
  objectPage: number;
  objectPageSize: number;
  objectCases: Array<{ id: number; serial_no: string; title: string; customer: string }>;
  objectLogTarget: ContractObjectRow | null;
  viewingAttachments: Attachment[];
  viewingAttachmentsLoading: boolean;
  viewingAttachmentsError: string | null;
  selectedAttachmentKeys: Key[];
  attachmentBatchSaving: boolean;
  contractEvents: ContractEvent[];
  contractWorkflowEvents: ContractEvent[];
  contractEventPage: number;
  contractEventPageSize: number;
  contractEventTotal: number;
  contractEventKeyword: string;
  contractEventsLoading: boolean;
  contractEventsError: string | null;
  legacyHistoricalAttachments: LegacyHistoricalAttachment[];
  legacyHistoricalAttachmentsLoading: boolean;
  legacyHistoricalAttachmentsError: string | null;
  detailApprovals: Step[];
  detailApprovalsError: string | null;
  archiveSummary: ContractArchiveSummary | null;
  archiveSubjects: ContractArchiveSubject[];
  archiveSubjectsLoading: boolean;
  archiveClosureSaving: boolean;
  selectedArchiveObjectKeys: Key[];
  archiveClosureComment: string;
  detailReceipts: any[];
  detailInvoices: Contract[];
  detailPayments: Contract[];
  detailContractCapabilities: ContractWorkflowCapabilities;
  contractFile: File | null;
  personName: (value: unknown) => string;
  peopleNames: (value: unknown) => string;
  onTabChange: (key: string) => void;
  onObjectPageChange: (page: number, pageSize: number) => void;
  onAddObject: () => void;
  onEditObject: (row: ContractObjectRow) => void;
  onDeleteObject: (objectId: number) => void;
  onViewObjectLog: (row: ContractObjectRow) => void;
  onEventSearch: (keyword: string) => void;
  onEventKeywordChange: (keyword: string) => void;
  onEventPageChange: (page: number, pageSize: number) => void;
  onReloadEvents: () => void;
  onUploadAttachment: () => void;
  onDeleteAttachment: (item: Attachment) => void;
  onBatchDeleteAttachments: () => void;
  onAttachmentSelectionChange: (keys: Key[]) => void;
  onPreviewAttachment: (item: Attachment) => void;
  onDownloadAttachment: (item: Attachment) => void;
  onReloadAttachments: () => void;
  onReloadApprovals: () => void;
  onArchiveClosureCommentChange: (value: string) => void;
  onArchiveSelectionChange: (keys: Key[]) => void;
  onSubmitArchiveClosure: () => void;
  onContractFileChange: (file: File | null) => void;
  onOpenRelatedCustomer: () => void;
  onOpenRelatedCase: (caseNo: unknown) => void;
  onOpenRelatedPayment: (payment: Contract) => void;
  onExportDetailExcel: () => void;
  onOpenContractEvent: () => void;
  onRevokeDraft: () => void;
  onChangeContract: () => void;
  onReturn: () => void;
}

export function ContractDetailView({
  viewing,
  isContractDetailView,
  detailActiveTab,
  contractObjects,
  objectPage,
  objectPageSize,
  objectCases,
  viewingAttachments,
  viewingAttachmentsLoading,
  viewingAttachmentsError,
  selectedAttachmentKeys,
  attachmentBatchSaving,
  contractEvents,
  contractWorkflowEvents,
  contractEventPage,
  contractEventPageSize,
  contractEventTotal,
  contractEventKeyword,
  contractEventsLoading,
  contractEventsError,
  legacyHistoricalAttachments,
  legacyHistoricalAttachmentsLoading,
  legacyHistoricalAttachmentsError,
  detailApprovals,
  detailApprovalsError,
  archiveSummary,
  archiveSubjects,
  archiveSubjectsLoading,
  archiveClosureSaving,
  selectedArchiveObjectKeys,
  archiveClosureComment,
  detailReceipts,
  detailInvoices,
  detailPayments,
  detailContractCapabilities,
  contractFile,
  personName,
  peopleNames,
  onTabChange,
  onObjectPageChange,
  onAddObject,
  onEditObject,
  onDeleteObject,
  onViewObjectLog,
  onEventSearch,
  onEventKeywordChange,
  onEventPageChange,
  onReloadEvents,
  onUploadAttachment,
  onDeleteAttachment,
  onBatchDeleteAttachments,
  onAttachmentSelectionChange,
  onPreviewAttachment,
  onDownloadAttachment,
  onReloadAttachments,
  onReloadApprovals,
  onArchiveClosureCommentChange,
  onArchiveSelectionChange,
  onSubmitArchiveClosure,
  onContractFileChange,
  onOpenRelatedCustomer,
  onOpenRelatedCase,
  onOpenRelatedPayment,
  onExportDetailExcel,
  onOpenContractEvent,
  onRevokeDraft,
  onChangeContract,
  onReturn,
}: ContractDetailViewProps) {
  const contractObjectPolicy = contractObjectActionPolicy(viewing?.status);
  const objectPageData = paginateContractObjectRows(contractObjects, objectPage, objectPageSize);
  const viewingHasEventEndpoint = Boolean(
    viewing && buildContractEventsRequest(viewing, { page: contractEventPage, pageSize: contractEventPageSize, keyword: contractEventKeyword }).path,
  );

  const presentedReceipts = detailReceipts
    .map((row) => {
      const item = normalizeIncomingPaymentForContract(row, viewing || {});
      if (!item) return null;
      return {
        ...row,
        receipt_no: item.sequenceNo,
        received_date: item.receivedDate,
        bank_reference: item.bankReference,
        amount: item.amount,
        official_amount: item.officialAmount,
        agency_amount: item.agencyAmount,
        other_amount: item.otherAmount,
        payment_method: item.paymentMethod,
        claimant: item.claimant,
      };
    })
    .filter(Boolean);

  const presentedInvoices = detailInvoices.map((row) => {
    const item = normalizeInvoiceObject(row);
    return {
      ...row,
      serial_no: item.applicationNo,
      status: item.status,
      description: item.remark,
      data: {
        ...row.data,
        invoice_no: item.invoiceNo,
        invoice_date: item.invoiceDate,
        amount: item.amount,
        official_amount: item.officialAmount,
        agency_amount: item.agencyAmount,
        other_amount: item.otherAmount,
        __lineThrough: item.lineThrough,
      },
    };
  });

  const presentedPayments = detailPayments.map((row) => {
    const item = normalizePaidObject(row);
    return {
      ...row,
      serial_no: item.applicationNo,
      data: {
        ...row.data,
        applicant: item.applicant,
        pending_amount: item.pendingAmount,
        payment_date: item.paymentDate,
        payment_reference: item.packageNo,
        amount: item.paidAmount,
        payment_type: item.paymentType,
        official_amount: item.officialAmount,
        other_amount: item.otherAmount,
        __lineThrough: item.lineThrough,
      },
    };
  });

  // ==================== 详情工作台模式 ====================
  if (isContractDetailView && viewing) {
    return (
      <div className="contract-detail-workbench">
        <section className="contract-detail-summary">
          <div>
            <span>客户编码：</span>
            <Button type="link" onClick={onOpenRelatedCustomer}>
              {viewing.data.customer_no || "—"}
            </Button>
          </div>
          <div>
            <span>签订日期：</span>
            <b>{viewing.data.signed_at || "—"}</b>
          </div>
          <div>
            <span>客户名称：</span>
            <Button type="link" onClick={onOpenRelatedCustomer}>
              {viewing.customer || "—"}
            </Button>
          </div>
          <div>
            <span>合同编号：</span>
            <b>{viewing.serial_no}</b>
          </div>
          <div>
            <span>客户管理人：</span>
            <b>
              {peopleNames(
                (viewing.data as any).customer_manager_display_names ||
                  viewing.data.customer_manager ||
                  (viewing.data as any).customer_managers ||
                  viewing.owner,
              )}
            </b>
          </div>
          <div>
            <span>合同名称：</span>
            <b>{viewing.title || "—"}</b>
          </div>
        </section>
        <section className="contract-detail-finance-summary">
          {[
            ["官费支付金额", viewing.data.official_paid],
            ["官费到账金额", viewing.data.official_received],
            ["官费未到金额", viewing.data.official_unreceived],
            ["官费亏损金额", viewing.data.official_loss],
            ["代理费总金额", viewing.data.agency_total],
            ["代理费到账金额", viewing.data.agency_received],
            ["代理费待收金额", viewing.data.agency_due],
            ["其他金额", viewing.data.other_total],
            ["其他金额已支付", viewing.data.other_paid],
            ["其他金额待支付", viewing.data.other_due],
            ["发票已开金额", viewing.data.invoice_opened],
            ["发票应开金额", viewing.data.invoice_should],
            ["发票高开金额", viewing.data.invoice_excess],
          ].map(([label, value]) => (
            <div key={String(label)}>
              <span>{label}：</span>
              <b>{amount(Number(value || 0))}</b>
            </div>
          ))}
        </section>
        <div className="contract-detail-scroll-region">
          <DetailTabs
            className="contract-detail-tabs"
            activeKey={detailActiveTab}
            onChange={onTabChange}
            tabBarExtraContent={<Button onClick={onExportDetailExcel}>导出Excel</Button>}
            sections={[
              {
                key: "objects",
                label: "合同标的",
                children: (
                  <>
                    <Space style={{ marginBottom: 8 }}>
                      <Button
                        size="small"
                        type="primary"
                        disabled={!viewing || !contractObjectPolicy.canEdit || !detailContractCapabilities.canEdit}
                        onClick={onAddObject}
                      >
                        新增标的
                      </Button>
                    </Space>
                    <Table
                      size="small"
                      rowKey="id"
                      scroll={{ x: 1120 }}
                      dataSource={objectPageData.items}
                      locale={{ emptyText: "暂无合同标的" }}
                      pagination={{
                        current: objectPageData.current,
                        pageSize: objectPageData.pageSize,
                        total: objectPageData.total,
                        showSizeChanger: true,
                        pageSizeOptions: [...CONTRACT_OBJECT_PAGE_SIZES],
                        showQuickJumper: { goButton: <Button size="small">GO</Button> },
                        onChange: (page, pageSize) => onObjectPageChange(page, pageSize),
                      }}
                      columns={[
                        { title: "序号", width: 64, render: (_: unknown, __: ContractObjectRow, index: number) => index + 1 },
                        { title: "案件类型", dataIndex: "case_type", width: 110 },
                        {
                          title: "案号",
                          dataIndex: "case_no",
                          width: 160,
                          render: (value: string) =>
                            value ? (
                              <Button type="link" className="contract-cell-link" onClick={() => onOpenRelatedCase(value)}>
                                {value}
                              </Button>
                            ) : (
                              "—"
                            ),
                        },
                        { title: "案件名称", dataIndex: "case_title", width: 180 },
                        { title: "案件阶段", dataIndex: "case_phase", width: 120 },
                        { title: "费用类型", dataIndex: "fee_type", width: 120 },
                        { title: "费用金额", dataIndex: "amount", width: 110, render: (value: number) => amount(value) },
                        {
                          title: "客户管理人",
                          dataIndex: "customer_manager",
                          width: 120,
                          render: (value: string) => peopleNames(value),
                        },
                        { title: "备注", dataIndex: "remark", width: 180 },
                        {
                          title: "操作",
                          width: 176,
                          fixed: "right",
                          render: (_: unknown, row: ContractObjectRow) => (
                            <Space size={0}>
                              {contractObjectHasLogs(row.logs) && (
                                <Button type="link" onClick={() => onViewObjectLog(row)}>
                                  日志
                                </Button>
                              )}
                              <Button
                                type="link"
                                disabled={!viewing || !contractObjectPolicy.canEdit || !detailContractCapabilities.canEdit}
                                onClick={() => onEditObject(row)}
                              >
                                编辑
                              </Button>
                              <Popconfirm
                                title="确认删除该合同标的？"
                                disabled={!viewing || !contractObjectPolicy.canDelete || !detailContractCapabilities.canEdit}
                                onConfirm={() => onDeleteObject(row.id)}
                              >
                                <Button
                                  type="link"
                                  danger
                                  disabled={!viewing || !contractObjectPolicy.canDelete || !detailContractCapabilities.canEdit}
                                >
                                  删除
                                </Button>
                              </Popconfirm>
                            </Space>
                          ),
                        },
                      ]}
                    />
                  </>
                ),
              },
              {
                key: "events",
                label: "事项记录",
                children: (
                  <>
                    <Space wrap style={{ marginBottom: 8 }}>
                      <Input.Search
                        allowClear
                        value={contractEventKeyword}
                        loading={contractEventsLoading}
                        placeholder="搜索事项内容"
                        onChange={(event) => onEventKeywordChange(event.target.value)}
                        onSearch={(value) => onEventSearch(value.trim())}
                      />
                      {contractEventsError && (
                        <Button type="link" onClick={onReloadEvents}>
                          重试
                        </Button>
                      )}
                    </Space>
                    {contractEventsError ? (
                      <Alert type="error" showIcon message={contractEventsError} />
                    ) : contractEvents.length ? (
                      <Timeline
                        items={contractEvents.map((event) => ({
                          children: (
                            <div className="contract-history-item">
                              <b>{event.content}</b>
                              <small>
                                {personName(event.operator)} · {dayjs(event.created_at).format("YYYY-MM-DD HH:mm")}
                              </small>
                            </div>
                          ),
                        }))}
                      />
                    ) : (
                      <Empty
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                        description={
                          viewing ? (
                            <span>
                              暂无事项记录，
                              <Button type="link" onClick={onOpenContractEvent}>
                                新建
                              </Button>
                            </span>
                          ) : (
                            "暂无事项记录"
                          )
                        }
                      />
                    )}
                    {viewingHasEventEndpoint && (
                      <Pagination
                        size="small"
                        current={contractEventPage}
                        pageSize={contractEventPageSize}
                        total={contractEventTotal}
                        showSizeChanger
                        pageSizeOptions={CONTRACT_EVENT_PAGE_SIZES.map(String)}
                        showQuickJumper={{ goButton: <Button size="small">GO</Button> }}
                        onChange={(page, pageSize) => onEventPageChange(page, pageSize)}
                      />
                    )}
                  </>
                ),
              },
              {
                key: "workflow",
                label: "流程记录",
                children: contractWorkflowEvents.length ? (
                  <Timeline
                    items={contractWorkflowEvents.map((event) => ({
                      children: (
                        <div className="contract-history-item">
                          <b>{event.content}</b>
                          <small>
                            {personName(event.operator)} · {dayjs(event.created_at).format("YYYY-MM-DD HH:mm")}
                          </small>
                        </div>
                      ),
                    }))}
                  />
                ) : (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无流程记录" />
                ),
              },
              {
                key: "attachments",
                label: "合同附件",
                children: (
                  <>
                    <Space wrap style={{ marginBottom: 8 }}>
                      <input
                        type="file"
                        accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.png,.jpg,.jpeg,.zip,.rar"
                        disabled={!viewing || ["审批中", "已归档"].includes(viewing.status)}
                        onChange={(event) => onContractFileChange(event.target.files?.[0] || null)}
                      />
                      <Button
                        onClick={onUploadAttachment}
                        disabled={!contractFile || !viewing || ["审批中", "已归档"].includes(viewing.status)}
                      >
                        上传附件
                      </Button>
                      <Button
                        danger
                        loading={attachmentBatchSaving}
                        disabled={
                          !viewing ||
                          !contractAttachmentActionPolicy(viewing.status).canDelete ||
                          !selectedAttachmentKeys.length
                        }
                        onClick={onBatchDeleteAttachments}
                      >
                        批量删除{selectedAttachmentKeys.length ? `（${selectedAttachmentKeys.length}）` : ""}
                      </Button>
                    </Space>
                    {viewingAttachmentsError ? (
                      <Alert
                        type="error"
                        showIcon
                        message={viewingAttachmentsError}
                        action={
                          <Button size="small" onClick={onReloadAttachments}>
                            重试
                          </Button>
                        }
                      />
                    ) : viewingAttachmentsLoading ? (
                      <span>正在加载合同附件…</span>
                    ) : viewingAttachments.length ? (
                      <Table
                        size="small"
                        rowKey="id"
                        pagination={false}
                        dataSource={viewingAttachments}
                        rowSelection={{
                          selectedRowKeys: selectedAttachmentKeys,
                          onChange: onAttachmentSelectionChange,
                          getCheckboxProps: () => ({
                            disabled: !viewing || !contractAttachmentActionPolicy(viewing.status).canDelete,
                          }),
                        }}
                        columns={[
                          { title: "序号", width: 64, render: (_: unknown, __: Attachment, index: number) => index + 1 },
                          { title: "文件名称", dataIndex: "original_name" },
                          { title: "分类", dataIndex: "category", width: 160 },
                          {
                            title: "上传人",
                            dataIndex: "uploader",
                            width: 120,
                            render: (_value: string, row: Attachment) =>
                              personName(row.uploader_display_name || row.uploader),
                          },
                          {
                            title: "上传日期",
                            dataIndex: "created_at",
                            width: 140,
                            render: (value: string) => (value ? dayjs(value).format("YYYY-MM-DD") : "—"),
                          },
                          {
                            title: "操作",
                            width: 180,
                            render: (_: unknown, item: Attachment) => (
                              <Space size={0}>
                                <Button type="link" onClick={() => onDownloadAttachment(item)}>
                                  下载
                                </Button>
                                <Button type="link" onClick={() => onPreviewAttachment(item)}>
                                  预览
                                </Button>
                                <Popconfirm
                                  title="确认删除该合同附件？"
                                  disabled={!viewing || ["审批中", "已归档"].includes(viewing.status)}
                                  onConfirm={() => onDeleteAttachment(item)}
                                >
                                  <Button
                                    type="link"
                                    danger
                                    disabled={!viewing || ["审批中", "已归档"].includes(viewing.status)}
                                  >
                                    删除
                                  </Button>
                                </Popconfirm>
                              </Space>
                            ),
                          },
                        ]}
                      />
                    ) : (
                      <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无合同附件" />
                    )}
                  </>
                ),
              },
              {
                key: "legacy-contract-history",
                label: "历史合同",
                children: (
                  <LegacyContractHistoryPanel
                    contractNo={viewing.serial_no}
                    customerNo={String(viewing.data.customer_no || "")}
                  />
                ),
              },
              {
                key: "legacy-attachments",
                label: "历史附件元数据",
                children: (
                  <>
                    <Alert
                      type="info"
                      showIcon
                      style={{ marginBottom: 8 }}
                      message="仅元数据：旧系统源文件不可恢复"
                      description="此处保留历史文件编号、父合同、声明大小、旧路径和隔离状态；没有下载或预览功能。"
                    />
                    {legacyHistoricalAttachmentsError ? (
                      <Alert type="error" showIcon message={legacyHistoricalAttachmentsError} />
                    ) : legacyHistoricalAttachmentsLoading ? (
                      <span>正在加载历史合同附件元数据…</span>
                    ) : (
                      <Table<LegacyHistoricalAttachment>
                        size="small"
                        rowKey="id"
                        pagination={false}
                        dataSource={legacyHistoricalAttachments}
                        locale={{ emptyText: "暂无已导入的历史合同附件元数据" }}
                        columns={[
                          { title: "历史文件ID", dataIndex: "legacy_file_id", width: 130 },
                          { title: "文件名称", dataIndex: "file_name", ellipsis: true },
                          { title: "历史合同号", dataIndex: "legacy_parent_no", width: 150 },
                          {
                            title: "声明大小",
                            dataIndex: "legacy_declared_size_bytes",
                            width: 110,
                            render: (value: number | null) => (value == null ? "—" : `${value} B`),
                          },
                          {
                            title: "恢复状态",
                            dataIndex: "recovery_status",
                            width: 210,
                            render: (value: string) => (
                              <Tag color="orange">{legacyAttachmentRecoveryLabel(value)}</Tag>
                            ),
                          },
                          {
                            title: "隔离原因",
                            dataIndex: "quarantine_reasons",
                            width: 210,
                            render: (values: string[]) => legacyAttachmentQuarantineLabel(values),
                          },
                          {
                            title: "物理文件",
                            width: 140,
                            render: () => <Tag color="default">源文件不可恢复</Tag>,
                          },
                        ]}
                      />
                    )}
                  </>
                ),
              },
              {
                key: "archive",
                label: "归档完结",
                children: (
                  <>
                    {archiveSummary && (
                      <Descriptions
                        size="small"
                        bordered
                        column={3}
                        items={[
                          { key: "contract", label: "合同编号", children: archiveSummary.serial_no },
                          { key: "title", label: "合同名称", children: archiveSummary.title },
                          { key: "customer", label: "客户", children: archiveSummary.customer || "—" },
                        ]}
                        style={{ marginBottom: 12 }}
                      />
                    )}
                    <Alert
                      type="info"
                      showIcon
                      message="按案件费用逐项归档完结"
                      description="勾选未完结的案件费用后提交。支付、开票和材料检查结果来自服务端归档核验，提交将写入费用与合同标的操作记录。"
                      style={{ marginBottom: 12 }}
                    />
                    <Table<ContractArchiveSubject>
                      rowKey="contract_object_id"
                      size="small"
                      loading={archiveSubjectsLoading}
                      pagination={false}
                      scroll={{ x: 1280 }}
                      dataSource={archiveSubjects}
                      locale={{ emptyText: "暂无可归档完结的合同标的" }}
                      columns={[
                        {
                          title: "案件编号",
                          dataIndex: "case_no",
                          width: 150,
                          render: (value: string) =>
                            value ? (
                              <Button type="link" className="contract-cell-link" onClick={() => onOpenRelatedCase(value)}>
                                {value}
                              </Button>
                            ) : (
                              "—"
                            ),
                        },
                        { title: "案件名称", dataIndex: "case_title", width: 190, ellipsis: true },
                        { title: "费用类型", dataIndex: "fee_type", width: 120 },
                        {
                          title: "合同费用",
                          dataIndex: "contract_amount",
                          width: 110,
                          render: (value: number) => amount(value),
                        },
                        {
                          title: "已支付",
                          dataIndex: "paid_amount",
                          width: 100,
                          render: (value: number) => amount(value),
                        },
                        {
                          title: "已开票",
                          dataIndex: "invoiced_amount",
                          width: 100,
                          render: (value: number) => amount(value),
                        },
                        {
                          title: "关联费用",
                          dataIndex: "case_fee_ids",
                          width: 96,
                          render: (value: number[]) => value?.length || 0,
                        },
                        {
                          title: "归档核验",
                          width: 260,
                          render: (_: unknown, row: ContractArchiveSubject) => (
                            <Space size={[4, 4]} wrap>
                              {Object.entries(row.archive_checks || {}).map(([key, passed]) => (
                                <Tag key={key} color={passed ? "green" : "orange"}>
                                  {archiveCheckLabels[key] || key}
                                  {passed ? "已完成" : "待处理"}
                                </Tag>
                              ))}
                            </Space>
                          ),
                        },
                        {
                          title: "费用完结",
                          width: 100,
                          render: (_: unknown, row: ContractArchiveSubject) => (
                            <Tag color={row.fee_archived ? "green" : "default"}>
                              {row.fee_archived ? "已完结" : "未完结"}
                            </Tag>
                          ),
                        },
                        {
                          title: "本次完结",
                          width: 110,
                          fixed: "right",
                          render: (_: unknown, row: ContractArchiveSubject) => (
                            <Checkbox
                              checked={selectedArchiveObjectKeys.includes(row.contract_object_id)}
                              disabled={
                                !detailContractCapabilities.canArchive ||
                                row.fee_archived ||
                                !row.case_fee_ids.length
                              }
                              onChange={(event) =>
                                onArchiveSelectionChange(
                                  event.target.checked
                                    ? Array.from(new Set([...selectedArchiveObjectKeys, row.contract_object_id]))
                                    : selectedArchiveObjectKeys.filter((key) => key !== row.contract_object_id),
                                )
                              }
                            >
                              完结
                            </Checkbox>
                          ),
                        },
                      ]}
                    />
                    <div style={{ marginTop: 12 }}>
                      <Input.TextArea
                        value={archiveClosureComment}
                        disabled={!detailContractCapabilities.canArchive}
                        onChange={(event) => onArchiveClosureCommentChange(event.target.value)}
                        maxLength={1000}
                        showCount
                        rows={3}
                        placeholder="填写归档完结说明"
                      />
                      <Space style={{ marginTop: 12 }}>
                        <span>已选 {selectedArchiveObjectKeys.length} 个合同标的</span>
                        <Popconfirm title="确认提交归档完结？" description="所选案件费用将被标记为已归档完结，并写入操作记录。" onConfirm={onSubmitArchiveClosure}>
                          <Button
                            type="primary"
                            loading={archiveClosureSaving}
                            disabled={!detailContractCapabilities.canArchive || !selectedArchiveObjectKeys.length}
                          >
                            提交归档完结
                          </Button>
                        </Popconfirm>
                      </Space>
                    </div>
                  </>
                ),
              },
              {
                key: "approvals",
                label: "审批信息",
                children: (
                  <>
                    {detailApprovalsError ? (
                      <Alert
                        type="error"
                        showIcon
                        message={detailApprovalsError}
                        action={
                          <Button size="small" onClick={onReloadApprovals}>
                            重试
                          </Button>
                        }
                      />
                    ) : (
                      <Table
                        size="small"
                        rowKey="id"
                        pagination={false}
                        dataSource={detailApprovals}
                        locale={{ emptyText: "暂无审批信息" }}
                        columns={[
                          { title: "审批顺序", dataIndex: "step_order", width: 100 },
                          {
                            title: "审批人",
                            dataIndex: "approver",
                            render: (_value: string, row: Step) =>
                              personName(row.approver_display_name || row.approver),
                          },
                          {
                            title: "审批日期",
                            dataIndex: "acted_at",
                            width: 140,
                            render: (value: string) => (value ? dayjs(value).format("YYYY-MM-DD") : "—"),
                          },
                          {
                            title: "状态",
                            dataIndex: "status",
                            width: 120,
                            render: (value: string) => <Tag>{value || "—"}</Tag>,
                          },
                          { title: "审批意见", dataIndex: "comment" },
                        ]}
                      />
                    )}
                  </>
                ),
              },
            ]}
          />
          <section className="contract-record-section">
            <h3>回款记录</h3>
            <Table
              size="small"
              rowKey="id"
              pagination={false}
              scroll={{ x: 1180 }}
              dataSource={presentedReceipts as any[]}
              locale={{ emptyText: "暂无回款记录" }}
              columns={[
                { title: "序号", width: 64, render: (_: unknown, __: any, index: number) => index + 1 },
                { title: "回款单号", dataIndex: "receipt_no", width: 150 },
                { title: "回款日期", dataIndex: "received_date", width: 120 },
                { title: "银行单据号", dataIndex: "bank_reference", width: 150 },
                { title: "回款金额", dataIndex: "amount", width: 110, render: (value: number) => amount(value) },
                { title: "官费", width: 100, render: (_: unknown, row: any) => amount(row.official_amount || 0) },
                { title: "代理费", width: 100, render: (_: unknown, row: any) => amount(row.agency_amount || 0) },
                { title: "其他费用", width: 100, render: (_: unknown, row: any) => amount(row.other_amount || 0) },
                { title: "回款方式", dataIndex: "payment_method", width: 120 },
                { title: "回款分配人", dataIndex: "claimant", width: 120 },
              ]}
            />
          </section>
          <section className="contract-record-section">
            <h3>开票记录</h3>
            <Table
              size="small"
              rowKey="id"
              pagination={false}
              scroll={{ x: 1120 }}
              dataSource={presentedInvoices}
              rowClassName={(row: any) => (row.data?.__lineThrough ? "contract-line-through" : "")}
              locale={{ emptyText: "暂无开票记录" }}
              columns={[
                { title: "序号", width: 64, render: (_: unknown, __: Contract, index: number) => index + 1 },
                { title: "请票单号", dataIndex: "serial_no", width: 150 },
                {
                  title: "发票号码",
                  width: 150,
                  render: (_: unknown, row: Contract) => (row.data as any).invoice_no || "—",
                },
                {
                  title: "开票日期",
                  width: 120,
                  render: (_: unknown, row: Contract) => (row.data as any).invoice_date || "—",
                },
                {
                  title: "开票金额",
                  width: 110,
                  render: (_: unknown, row: Contract) => amount((row.data as any).amount || 0),
                },
                {
                  title: "官费",
                  width: 100,
                  render: (_: unknown, row: Contract) => amount((row.data as any).official_amount || 0),
                },
                {
                  title: "代理费",
                  width: 100,
                  render: (_: unknown, row: Contract) => amount((row.data as any).agency_amount || 0),
                },
                {
                  title: "其他费用",
                  width: 100,
                  render: (_: unknown, row: Contract) => amount((row.data as any).other_amount || 0),
                },
                { title: "状态", dataIndex: "status", width: 110 },
                { title: "备注", dataIndex: "description", width: 180 },
              ]}
            />
          </section>
          <section className="contract-record-section">
            <h3>付款记录</h3>
            <Table
              size="small"
              rowKey="id"
              pagination={false}
              scroll={{ x: 1120 }}
              dataSource={presentedPayments}
              rowClassName={(row: any) => (row.data?.__lineThrough ? "contract-line-through" : "")}
              locale={{ emptyText: "暂无付款记录" }}
              columns={[
                { title: "序号", width: 64, render: (_: unknown, __: Contract, index: number) => index + 1 },
                {
                  title: "申请单号",
                  dataIndex: "serial_no",
                  width: 150,
                  render: (value: string, row: Contract) =>
                    value ? (
                      <Button type="link" className="contract-cell-link" onClick={() => onOpenRelatedPayment(row)}>
                        {value}
                      </Button>
                    ) : (
                      "—"
                    ),
                },
                {
                  title: "申请人",
                  width: 120,
                  render: (_: unknown, row: Contract) =>
                    personName(
                      (row.data as any).applicant_display_name ||
                        (row.data as any).applicant ||
                        (row as any).owner_display_name ||
                        row.owner,
                    ),
                },
                {
                  title: "待付金额",
                  width: 110,
                  render: (_: unknown, row: Contract) => amount((row.data as any).pending_amount || 0),
                },
                {
                  title: "付款日期",
                  width: 120,
                  render: (_: unknown, row: Contract) => (row.data as any).payment_date || "—",
                },
                {
                  title: "付款单据",
                  width: 140,
                  render: (_: unknown, row: Contract) => (row.data as any).payment_reference || "—",
                },
                {
                  title: "付款金额",
                  width: 110,
                  render: (_: unknown, row: Contract) => amount((row.data as any).amount || 0),
                },
                {
                  title: "付款类型",
                  width: 120,
                  render: (_: unknown, row: Contract) => (row.data as any).payment_type || "—",
                },
                {
                  title: "付款标的",
                  width: 260,
                  dataIndex: "line_summary",
                  render: (value: string) => value || "—",
                },
                {
                  title: "官费",
                  width: 100,
                  render: (_: unknown, row: Contract) => amount((row.data as any).official_amount || 0),
                },
                {
                  title: "其他费用",
                  width: 100,
                  render: (_: unknown, row: Contract) => amount((row.data as any).other_amount || 0),
                },
              ]}
            />
          </section>
        </div>
      </div>
    );
  }

  // ==================== 简单查看模式 ====================
  return (
    <>
      <Descriptions
        bordered
        size="small"
        column={2}
        items={
          viewing
            ? [
                { key: "serial", label: "合同号", children: viewing.serial_no },
                { key: "status", label: "合同状态", children: displayContractStatus(viewing.status) },
                { key: "title", label: "合同名称", children: viewing.title, span: 2 },
                {
                  key: "customer",
                  label: "客户名称",
                  children: (
                    <Button type="link" className="contract-cell-link" onClick={onOpenRelatedCustomer}>
                      {viewing.customer || "—"}
                    </Button>
                  ),
                },
                {
                  key: "case",
                  label: "关联案号",
                  children: viewing.data.case_no ? (
                    <Button type="link" className="contract-cell-link" onClick={() => onOpenRelatedCase(viewing.data.case_no)}>
                      {viewing.data.case_no}
                    </Button>
                  ) : (
                    "—"
                  ),
                },
                { key: "body", label: "合同主体", children: viewing.data.contract_body || "律所" },
                { key: "type", label: "合同类型", children: viewing.data.type || "—" },
                { key: "fee", label: "收费类型", children: viewing.data.fee_type || "—" },
                {
                  key: "source",
                  label: "案源人",
                  children: personName(
                    (viewing.data as any).source_person_display_name ||
                      viewing.data.source_person ||
                      (viewing as any).owner_display_name ||
                      viewing.owner,
                  ),
                },
                { key: "date", label: "合同日期", children: viewing.data.signed_at || "—" },
                {
                  key: "official",
                  label: "官费（支付 / 到账 / 未到）",
                  children: `${amount(viewing.data.official_paid)} / ${amount(viewing.data.official_received)} / ${amount(viewing.data.official_unreceived)}`,
                  span: 2,
                },
                {
                  key: "agency",
                  label: "代理费（总额 / 到账 / 待收）",
                  children: `${amount(viewing.data.agency_total)} / ${amount(viewing.data.agency_received)} / ${amount(viewing.data.agency_due)}`,
                  span: 2,
                },
                {
                  key: "invoice",
                  label: "发票（已开 / 应开 / 高开）",
                  children: `${amount(viewing.data.invoice_opened)} / ${amount(viewing.data.invoice_should)} / ${amount(viewing.data.invoice_excess)}`,
                  span: 2,
                },
                {
                  key: "description",
                  label: "合同说明",
                  children: viewing.description || "—",
                  span: 2,
                },
              ]
            : []
        }
      />
      <Divider>合同附件</Divider>
      {viewingAttachmentsError ? (
        <Alert
          type="error"
          showIcon
          message={viewingAttachmentsError}
          action={
            <Button size="small" onClick={onReloadAttachments}>
              重试
            </Button>
          }
        />
      ) : viewingAttachmentsLoading ? (
        <span>正在加载合同附件…</span>
      ) : viewingAttachments.length ? (
        <Space direction="vertical" size={2}>
          {viewingAttachments.map((item) => (
            <Space key={item.id} size={4}>
              <Button type="link" onClick={() => onDownloadAttachment(item)}>
                {item.original_name}
              </Button>
              <Button type="link" onClick={() => onPreviewAttachment(item)}>
                预览
              </Button>
              <small>
                {personName(item.uploader_display_name || item.uploader)} ·{" "}
                {item.created_at ? dayjs(item.created_at).format("YYYY-MM-DD") : "—"}
              </small>
            </Space>
          ))}
        </Space>
      ) : (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无合同附件" />
      )}
      <Divider>事项记录</Divider>
      <Space wrap style={{ marginBottom: 8 }}>
        <Input.Search
          allowClear
          value={contractEventKeyword}
          loading={contractEventsLoading}
          placeholder="搜索事项内容"
          onChange={(event) => onEventKeywordChange(event.target.value)}
          onSearch={(value) => onEventSearch(value.trim())}
        />
        {contractEventsError && (
          <Button type="link" onClick={onReloadEvents}>
            重试
          </Button>
        )}
      </Space>
      {contractEventsError ? <Alert type="error" showIcon message={contractEventsError} /> : null}
      {viewingHasEventEndpoint && (
        <Pagination
          size="small"
          current={contractEventPage}
          pageSize={contractEventPageSize}
          total={contractEventTotal}
          showSizeChanger
          pageSizeOptions={CONTRACT_EVENT_PAGE_SIZES.map(String)}
          showQuickJumper={{ goButton: <Button size="small">GO</Button> }}
          onChange={(page, pageSize) => onEventPageChange(page, pageSize)}
        />
      )}
      {contractEvents.length ? (
        <Timeline
          items={contractEvents.map((event) => ({
            children: (
              <div className="contract-history-item">
                <b>{event.content}</b>
                <small>
                  {personName(event.operator)} · {dayjs(event.created_at).format("YYYY-MM-DD HH:mm")}
                </small>
              </div>
            ),
          }))}
        />
      ) : (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            viewing ? (
              <span>
                暂无事项记录，
                <Button type="link" onClick={onOpenContractEvent}>
                  新建
                </Button>
              </span>
            ) : (
              "暂无事项记录"
            )
          }
        />
      )}
      <Divider>流程记录</Divider>
      {contractWorkflowEvents.length ? (
        <Timeline
          items={contractWorkflowEvents.map((event) => ({
            children: (
              <div className="contract-history-item">
                <b>{event.content}</b>
                <small>
                  {personName(event.operator)} · {dayjs(event.created_at).format("YYYY-MM-DD HH:mm")}
                </small>
              </div>
            ),
          }))}
        />
      ) : (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无流程记录" />
      )}
      <Divider>
        合同标的{" "}
        <Button size="small" type="link" disabled={!viewing || !contractObjectPolicy.canEdit} onClick={onAddObject}>
          新增标的
        </Button>
      </Divider>
      {contractObjects.length ? (
        <Table
          size="small"
          rowKey="id"
          scroll={{ x: 940 }}
          columns={[
            { title: "案件类型", dataIndex: "case_type", width: 100 },
            {
              title: "案号",
              dataIndex: "case_no",
              width: 155,
              render: (value: string) =>
                value ? (
                  <Button type="link" className="contract-cell-link" onClick={() => onOpenRelatedCase(value)}>
                    {value}
                  </Button>
                ) : (
                  "—"
                ),
            },
            { title: "案件名称", dataIndex: "case_title", width: 170, ellipsis: true },
            { title: "案件阶段", dataIndex: "case_phase", width: 110 },
            { title: "费用类型", dataIndex: "fee_type", width: 110 },
            { title: "费用金额", dataIndex: "amount", width: 110, render: (value: number) => amount(value) },
            {
              title: "客户管理人",
              dataIndex: "customer_manager",
              width: 120,
              render: (value: string) => peopleNames(value),
            },
            { title: "备注", dataIndex: "remark", width: 180, ellipsis: true },
            {
              title: "操作",
              width: 176,
              fixed: "right",
              render: (_: unknown, row: ContractObjectRow) => (
                <Space size={0}>
                  {contractObjectHasLogs(row.logs) && (
                    <Button type="link" onClick={() => onViewObjectLog(row)}>
                      日志
                    </Button>
                  )}
                  {!viewing || !contractObjectPolicy.canEdit ? null : (
                    <>
                      <Button type="link" onClick={() => onEditObject(row)}>
                        编辑
                      </Button>
                      <Popconfirm
                        title="确认删除该合同标的？"
                        disabled={!contractObjectPolicy.canDelete}
                        onConfirm={() => onDeleteObject(row.id)}
                      >
                        <Button type="link" danger disabled={!contractObjectPolicy.canDelete}>
                          删除
                        </Button>
                      </Popconfirm>
                    </>
                  )}
                </Space>
              ),
            },
          ]}
          dataSource={objectPageData.items}
          pagination={{
            current: objectPageData.current,
            pageSize: objectPageData.pageSize,
            total: objectPageData.total,
            showSizeChanger: true,
            pageSizeOptions: [...CONTRACT_OBJECT_PAGE_SIZES],
            showQuickJumper: { goButton: <Button size="small">GO</Button> },
            onChange: (page, pageSize) => onObjectPageChange(page, pageSize),
          }}
        />
      ) : (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无合同标的" />
      )}
    </>
  );
}
