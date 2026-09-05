import { Alert,Button,Card,DatePicker,Form,Input,Modal,Select,Space,Table,Tag } from "antd";
import { personDisplayName } from "../constants";
import type { AssistedFee,Attachment,IprDetailPageState,IprRecord } from "../types";

interface IprAssistedFeesPanelProps {
  detail: IprRecord;
  iprSectionErrors: { assistedFees: string };
  assistedFees: AssistedFee[];
  assistedFeesPageState: IprDetailPageState;
  canManageAssistedFees: boolean;
  assistedOpen: boolean;
  assistedForm: any;
  editingAssistedFee: AssistedFee | null;
  assistedEditForm: any;
  transactTarget: AssistedFee | null;
  transactForm: any;
  receiptFile: File | null;
  onRefresh: () => void;
  onOpenCreate: () => void;
  onCloseCreate: () => void;
  onCreate: () => void;
  onOpenEdit: (row: AssistedFee) => void;
  onCloseEdit: () => void;
  onUpdate: () => void;
  onConfirm: (row: AssistedFee) => void;
  onOpenTransact: (row: AssistedFee) => void;
  onCloseTransact: () => void;
  onTransact: () => void;
  onReceiptFileChange: (file: File | null) => void;
  onDelete: (row: AssistedFee) => Promise<void>;
  onPreviewAttachment: (item: Attachment) => void;
  onDownloadAttachment: (item: Attachment) => void;
  confirmIprDeletion: (kind: string, label: string, operation: () => Promise<void>) => void;
  onPageChange: (page: number, pageSize: number) => void;
}

export function IprAssistedFeesPanel({
  detail,
  iprSectionErrors,
  assistedFees,
  assistedFeesPageState,
  canManageAssistedFees,
  assistedOpen,
  assistedForm,
  editingAssistedFee,
  assistedEditForm,
  transactTarget,
  transactForm,
  receiptFile,
  onRefresh,
  onOpenCreate,
  onCloseCreate,
  onCreate,
  onOpenEdit,
  onCloseEdit,
  onUpdate,
  onConfirm,
  onOpenTransact,
  onCloseTransact,
  onTransact,
  onReceiptFileChange,
  onDelete,
  onPreviewAttachment,
  onDownloadAttachment,
  confirmIprDeletion,
  onPageChange,
}: IprAssistedFeesPanelProps) {
  const assistedFeesPagination = {
    current: assistedFeesPageState.page,
    pageSize: assistedFeesPageState.pageSize,
    total: assistedFeesPageState.total,
    showSizeChanger: true,
    pageSizeOptions: ["15", "20", "50"],
    onChange: onPageChange,
  };

  return (
    <>
      <Card
        size="small"
        title="协助费"
        style={{ marginTop: 16 }}
        extra={
          <Space size={0}>
            <Button size="small" onClick={onRefresh}>
              刷新
            </Button>
            {detail.status === "在办" && canManageAssistedFees ? (
              <Button type="primary" size="small" onClick={onOpenCreate}>
                新增协助费
              </Button>
            ) : null}
          </Space>
        }
      >
        {iprSectionErrors.assistedFees ? (
          <Alert
            type="error"
            showIcon
            message={iprSectionErrors.assistedFees}
            style={{ marginBottom: 12 }}
          />
        ) : null}
        <Table
          rowKey="id"
          size="small"
          pagination={assistedFeesPagination}
          dataSource={assistedFees}
          scroll={{ x: 980 }}
          columns={[
            {
              title: "协助类别",
              dataIndex: "assisted_type",
              width: 150,
            },
            {
              title: "提交",
              width: 145,
              render: (_, row: AssistedFee) =>
                `${row.request_date || "—"} / ${personDisplayName(
                  row.request_user_display_name
                )}`,
            },
            {
              title: "办理",
              width: 145,
              render: (_, row: AssistedFee) =>
                row.response_date
                  ? `${row.response_date} / ${personDisplayName(
                      row.response_user_display_name
                    )}`
                  : "—",
            },
            {
              title: "回执文件",
              width: 180,
              render: (_, row: AssistedFee) =>
                row.receipt ? (
                  <Space size={0}>
                    <Button
                      type="link"
                      onClick={() => onPreviewAttachment(row.receipt!)}
                    >
                      {row.receipt.original_name}
                    </Button>
                    <Button
                      type="link"
                      onClick={() => onDownloadAttachment(row.receipt!)}
                    >
                      下载
                    </Button>
                  </Space>
                ) : (
                  "—"
                ),
            },
            {
              title: "状态",
              dataIndex: "status",
              width: 90,
              render: (value) => (
                <Tag color={value === "已办理" ? "green" : "gold"}>
                  {value}
                </Tag>
              ),
            },
            {
              title: "操作",
              fixed: "right",
              width: 190,
              render: (_, row: AssistedFee) => (
                <Space size={0}>
                  {row.status === "待确认" &&
                    detail.status === "在办" &&
                    canManageAssistedFees && (
                      <Button type="link" onClick={() => onOpenEdit(row)}>
                        编辑
                      </Button>
                    )}
                  {row.status === "待确认" &&
                    detail.status === "在办" &&
                    canManageAssistedFees && (
                      <Button type="link" onClick={() => onConfirm(row)}>
                        确认
                      </Button>
                    )}
                  {row.status === "待办理" &&
                    detail.status === "在办" &&
                    canManageAssistedFees && (
                      <Button type="link" onClick={() => onOpenTransact(row)}>
                        办理
                      </Button>
                    )}
                  {(row.status === "待确认" || row.status === "待办理") &&
                    detail.status === "在办" &&
                    canManageAssistedFees && (
                      <Button
                        type="link"
                        danger
                        onClick={() =>
                          confirmIprDeletion(
                            "assisted-fee",
                            row.assisted_type,
                            () => onDelete(row)
                          )
                        }
                      >
                        删除
                      </Button>
                    )}
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal open={assistedOpen} title="新增知识产权协助费" onCancel={onCloseCreate} onOk={onCreate} okText="提交" />
      <Modal
        open={assistedOpen}
        title="新建知识产权资助费用"
        onCancel={onCloseCreate}
        onOk={onCreate}
        okText="提交"
      >
        <Form form={assistedForm} layout="vertical">
          <Form.Item
            name="assisted_type"
            label="协助类别"
            rules={[
              { required: true, message: "请选择或填写协助类别" },
            ]}
          >
            <Select
              showSearch
              allowClear
              options={[
                "专利资助",
                "商标资助",
                "高新技术资助",
                "其他资助",
              ].map((value) => ({ value, label: value }))}
            />
          </Form.Item>
          <Form.Item name="remark" label="说明">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={!!editingAssistedFee}
        title={
          editingAssistedFee
            ? `编辑协助费：${editingAssistedFee.assisted_type}`
            : "编辑协助费"
        }
        onCancel={onCloseEdit}
        onOk={onUpdate}
        okText="保存"
      >
        <Form form={assistedEditForm} layout="vertical">
          <Form.Item
            name="assisted_type"
            label="协助类别"
            rules={[
              { required: true, message: "请选择或填写协助类别" },
            ]}
          >
            <Select
              showSearch
              allowClear
              options={[
                "专利资助",
                "商标资助",
                "高新技术资助",
                "其他资助",
              ].map((value) => ({ value, label: value }))}
            />
          </Form.Item>
          <Form.Item name="remark" label="说明">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={!!transactTarget}
        title={
          transactTarget
            ? `办理协助费：${transactTarget.assisted_type}`
            : "办理协助费"
        }
        onCancel={onCloseTransact}
        onOk={onTransact}
        okText="保存办理"
      >
        <Form form={transactForm} layout="vertical">
          <Form.Item
            name="response_date"
            label="办理日期"
            rules={[{ required: true }]}
          >
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="回执文件" required>
            <input
              type="file"
              accept=".pdf,.doc,.docx,.xls,.xlsx,.zip,.jpg,.jpeg,.png"
              onChange={(event) =>
                onReceiptFileChange(event.target.files?.[0] || null)
              }
            />
            {receiptFile && <div>{receiptFile.name}</div>}
          </Form.Item>
          <Form.Item name="remark" label="办理说明">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
