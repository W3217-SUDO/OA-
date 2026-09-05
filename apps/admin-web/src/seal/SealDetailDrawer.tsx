import {
  Button,
  Descriptions,
  Drawer,
  Form,
  Input,
  Space,
  Table,
  Tag,
  Timeline,
  Upload,
} from "antd";
import { DownloadOutlined, FileDoneOutlined, ReloadOutlined, UploadOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import type { FormInstance } from "antd";
import type { AttachmentRow, EventRow, SealRow } from "./types";
import { personDisplayName, sealAttachmentLabel, sealAttachmentListLabel, statusColors } from "./constants";
import {
  canBatchDeleteSealFiles,
  canSealAction,
  formatSealAttachmentSize,
  getSealAttachmentExtension,
  sealFilePagination,
} from "../sealWorkflowPolicy";

interface SealDetailDrawerProps {
  open: boolean;
  detail: SealRow | null;
  tab: string;
  history: EventRow[];
  attachments: AttachmentRow[];
  attachmentPage: number;
  attachmentPageSize: number;
  attachmentTotal: number;
  attachmentSelectedKeys: number[];
  detailAuditForm: FormInstance;
  actionSubmitting: boolean;
  onClose: () => void;
  onRefresh: () => void;
  onDetailApproval: (approved: boolean) => void;
  onAttachmentPageChange: (page: number, pageSize: number) => void;
  onAttachmentSelectionChange: (keys: number[]) => void;
  onUploadFiles: (files: File[]) => void;
  onRemoveFiles: () => void;
  onRemoveFile: (item: AttachmentRow) => void;
  onPreviewAttachment: (item: AttachmentRow) => void;
  onDownloadAttachment: (item: AttachmentRow) => void;
  onOpenAuditList: () => void;
  onOpenCustomerDetail: (customer: unknown, customerNo?: unknown) => void;
  onOpenCaseDetail: (caseNo: unknown) => void;
  onOpenContractDetail: (contractNo: unknown) => void;
}

export function SealDetailDrawer({
  open,
  detail,
  tab,
  history,
  attachments,
  attachmentPage,
  attachmentPageSize,
  attachmentTotal,
  attachmentSelectedKeys,
  detailAuditForm,
  actionSubmitting,
  onClose,
  onRefresh,
  onDetailApproval,
  onAttachmentPageChange,
  onAttachmentSelectionChange,
  onUploadFiles,
  onRemoveFiles,
  onRemoveFile,
  onPreviewAttachment,
  onDownloadAttachment,
  onOpenAuditList,
  onOpenCustomerDetail,
  onOpenCaseDetail,
  onOpenContractDetail,
}: SealDetailDrawerProps) {
  const isAuditTab = tab === "audit";
  const canApprove = detail ? canSealAction("approve", detail) : false;
  const canReject = detail ? canSealAction("reject", detail) : false;
  const showAuditFooter = isAuditTab && (canApprove || canReject);
  const showAuditForm = isAuditTab && (canApprove || canReject);

  return (
    <Drawer
      open={open}
      size={640}
      title={`${
        showAuditFooter ? "用印审核" : "用印详情"
      }：${detail?.serial_no || ""}`}
      extra={detail ? <Button icon={<ReloadOutlined />} onClick={onRefresh}>刷新</Button> : null}
      footer={
        detail && showAuditFooter ? (
          <Space>
            {canApprove && (
              <Button type="primary" loading={actionSubmitting} onClick={() => onDetailApproval(true)}>
                通过
              </Button>
            )}
            {canReject && (
              <Button danger loading={actionSubmitting} onClick={() => onDetailApproval(false)}>
                拒绝
              </Button>
            )}
            <Button disabled={actionSubmitting} onClick={onClose}>取消</Button>
          </Space>
        ) : null
      }
      onClose={onClose}
    >
      {detail && (
        <>
          <Descriptions
            bordered
            size="small"
            column={2}
            items={[
              {
                key: "title",
                label: "申请标题",
                children: detail.title,
                span: 2,
              },
              {
                key: "customer",
                label: "客户",
                children: detail.customer ? <Button type="link" onClick={() => onOpenCustomerDetail(detail.customer, detail.data.customer_no)}>{detail.customer}</Button> : "—",
              },
              {
                key: "customer_no",
                label: "客户编号",
                children: detail.data.customer_no || "—",
              },
              {
                key: "use_type",
                label: "用印类型",
                children: detail.data.use_type || "—",
              },
              {
                key: "case",
                label: "关联案号",
                children: detail.data.case_no ? (
                  <Button
                    type="link"
                    onClick={() => onOpenCaseDetail(detail.data.case_no)}
                  >
                    {detail.data.case_no}
                  </Button>
                ) : (
                  "—"
                ),
              },
              {
                key: "contract",
                label: "关联合同号",
                children: detail.data.contract_no ? (
                  <Button
                    type="link"
                    onClick={() =>
                      onOpenContractDetail(detail.data.contract_no)
                    }
                  >
                    {detail.data.contract_no}
                  </Button>
                ) : (
                  "—"
                ),
              },
              {
                key: "seal",
                label: "印章",
                children: detail.seal_asset?.name || detail.data.seal_name,
              },
              {
                key: "copies",
                label: "申请份数",
                children: detail.data.copies,
              },
              {
                key: "print_quantity",
                label: "盖章份数",
                children: detail.data.print_quantity ?? detail.data.copies ?? "—",
              },
              {
                key: "electronic",
                label: "电子印章",
                children: detail.data.is_electronic_seal ? "是" : "否",
              },
              {
                key: "print",
                label: "打印盖章",
                children: detail.data.is_offline_print ? "需要" : "不需要",
              },
              {
                key: "purpose",
                label: "用途",
                children: detail.data.purpose,
                span: 2,
              },
              {
                key: "remark",
                label: "用印备注",
                children: detail.data.remark || detail.description || "—",
                span: 2,
              },
              {
                key: "method",
                label: "办理方式",
                children: detail.data.delivery_method,
              },
              {
                key: "date",
                label: "计划日期",
                children: detail.data.use_date,
              },
              {
                key: "actual",
                label: "实际份数",
                children: detail.data.actual_copies || "—",
              },
              {
                key: "archive",
                label: "归档号",
                children: detail.data.archive_no || "—",
              },
              {
                key: "status",
                label: "当前状态",
                children: (
                  <Tag color={statusColors[detail.status]}>
                    {detail.status}
                  </Tag>
                ),
              },
              { key: "owner", label: "申请人", children: personDisplayName(detail.owner_display_name) },
            ]}
          />
          {showAuditForm && (
            <Form form={detailAuditForm} layout="vertical" style={{ marginTop: 16 }}>
              <Form.Item label="审批意见" name="comment">
                <Input.TextArea rows={4} />
              </Form.Item>
            </Form>
          )}
          <h3 className="seal-history-title">
            <FileDoneOutlined /> {sealAttachmentListLabel}
          </h3>
          {detail.status === "草稿" && (
            <Space>
              <Upload
                multiple
                showUploadList={false}
                beforeUpload={(file, fileList) => {
                  const firstFile = fileList[0] as File & { uid?: string };
                  const currentFile = file as File & { uid?: string };
                  if (!firstFile || firstFile.uid === currentFile.uid || firstFile === currentFile) {
                    onUploadFiles(fileList as File[]);
                  }
                  return Upload.LIST_IGNORE;
                }}
              >
                <Button icon={<UploadOutlined />}>上传用印文件</Button>
              </Upload>
              <Button
                danger
                disabled={
                  !canBatchDeleteSealFiles(
                    detail.status,
                    attachmentSelectedKeys,
                  )
                }
                onClick={onRemoveFiles}
              >
                批量删除
              </Button>
            </Space>
          )}
          <Table
            size="small"
            rowKey="id"
            style={{ marginTop: 10 }}
            rowSelection={
              detail.status === "草稿"
                ? {
                    selectedRowKeys: attachmentSelectedKeys,
                    onChange: (keys) =>
                      onAttachmentSelectionChange(keys as number[]),
                  }
                : undefined
            }
            pagination={{
              current: attachmentPage,
              pageSize: attachmentPageSize,
              total: attachmentTotal,
              showSizeChanger: sealFilePagination.showSizeChanger,
              pageSizeOptions: sealFilePagination.pageSizeOptions.map(String),
              showQuickJumper: sealFilePagination.showQuickJumper,
              showTotal: sealFilePagination.showTotal,
              onChange: onAttachmentPageChange,
            }}
            locale={{
              emptyText: `暂无${sealAttachmentListLabel}`,
            }}
            dataSource={attachments}
            columns={[
              {
                title: "文件名称",
                dataIndex: "original_name",
                ellipsis: true,
                render: (value: string, item: AttachmentRow) => (
                  <Button type="link" onClick={() => onPreviewAttachment(item)}>
                    {value}
                  </Button>
                ),
              },
              {
                title: "附件类别",
                width: 100,
                dataIndex: "category",
                render: (value: string) => <Tag>{sealAttachmentLabel(value)}</Tag>,
              },
              {
                title: "类型",
                width: 70,
                render: (_: unknown, item: AttachmentRow) =>
                  getSealAttachmentExtension(item.original_name) || "—",
              },
              {
                title: "大小",
                width: 90,
                dataIndex: "size",
                render: (value: number) => formatSealAttachmentSize(value),
              },
              { title: "上传人", dataIndex: "uploader_display_name", width: 90, render: personDisplayName },
              {
                title: "上传时间",
                dataIndex: "created_at",
                width: 145,
                render: (value: string) =>
                  dayjs(value).format("YYYY-MM-DD HH:mm"),
              },
              {
                title: "操作",
                width: 130,
                render: (_: unknown, item: AttachmentRow) => (
                  <Space size={0}>
                    <Button
                      type="link"
                      onClick={() => onPreviewAttachment(item)}
                    >
                      预览
                    </Button>
                    <Button
                      type="link"
                      icon={<DownloadOutlined />}
                      onClick={() => onDownloadAttachment(item)}
                    >
                      下载
                    </Button>
                    {detail.status === "草稿" && (
                      <Button
                        type="link"
                        danger
                        onClick={() => onRemoveFile(item)}
                      >
                        删除
                      </Button>
                    )}
                  </Space>
                ),
              },
            ]}
          />
          <h3 className="seal-history-title">
            <FileDoneOutlined /> 流程记录
          </h3>
          <Button type="link" onClick={onOpenAuditList}>
            审核记录
          </Button>
          <Timeline
            items={history.map((x) => ({
              color: x.to_status === "已拒绝" ? "red" : "green",
              children: (
                <div>
                  <b>{x.action}</b>{" "}
                  <Tag>
                    {x.from_status || "创建"} → {x.to_status}
                  </Tag>
                  <div>
                    {personDisplayName(x.operator_display_name)} ·{" "}
                    {dayjs(x.created_at).format("YYYY-MM-DD HH:mm")}
                  </div>
                  {x.comment && <small>{x.comment}</small>}
                </div>
              ),
            }))}
          />
        </>
      )}
    </Drawer>
  );
}
