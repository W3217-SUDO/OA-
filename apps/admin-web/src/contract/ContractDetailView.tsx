import {
Alert,
Button,
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
import { ContractFinancialRecords } from "./ContractFinancialRecords";
import { DetailTabs } from "../components/common/DetailTabs";
import {
CONTRACT_OBJECT_PAGE_SIZES,
paginateContractObjectRows,
} from "../contractObjectListPolicy.mjs";
import {
contractObjectActionPolicy,
contractObjectHasLogs,
} from "../contractObjectPresentation.mjs";
import { displayContractStatus } from "../contractStatusPresentation.mjs";
import {
buildContractEventsRequest,
CONTRACT_EVENT_PAGE_SIZES,
contractAttachmentActionPolicy,
} from "../contractWorkflowPolicy.mjs";
import { amount } from "./constants";
import type {
Attachment,
Contract,
ContractEvent,
ContractObjectRow,
ContractWorkflowCapabilities,
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
  detailApprovals: Step[];
  detailApprovalsError: string | null;
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
  detailApprovals,
  detailApprovalsError,
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

  // ==================== 详情工作台模式 ====================
  if (isContractDetailView && viewing) {
    return (
      <div className="contract-detail-workbench">
        <h3 className="contract-detail-section-title">基本信息</h3>
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
        <h3 className="contract-detail-section-title">财务信息</h3>
        <section className="contract-detail-finance-summary">
          {[
            [["官费支付金额", viewing.data.official_paid], ["官费到账金额", viewing.data.official_received], ["官费未到金额", viewing.data.official_unreceived], ["官费亏损金额", viewing.data.official_loss]],
            [["代理费总金额", viewing.data.agency_total], ["代理费到账金额", viewing.data.agency_received], ["代理费待收金额", viewing.data.agency_due]],
            [["其他金额", viewing.data.other_total], ["其他金额已支付", viewing.data.other_paid], ["其他金额待支付", viewing.data.other_due]],
            [["发票已开金额", viewing.data.invoice_opened], ["发票应开金额", viewing.data.invoice_should], ["发票高开金额", viewing.data.invoice_excess]],
          ].map((group, index) => (
            <div className="contract-detail-finance-group" key={index}>
              {group.map(([label, value]) => <div key={String(label)}><span>{label}：</span><b>{amount(Number(value || 0))}</b></div>)}
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
                    <ContractFinancialRecords viewing={viewing} detailReceipts={detailReceipts} detailInvoices={detailInvoices} detailPayments={detailPayments} personName={personName} onOpenRelatedPayment={onOpenRelatedPayment} />
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
