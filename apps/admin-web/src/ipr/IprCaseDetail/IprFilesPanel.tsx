import { Alert,Button,Card,DatePicker,Form,Input,Modal,Select,Space,Table,Tag } from "antd";
import { AttachmentFileInput } from "../../components/common/AttachmentContent";
import type { Attachment,IprDetailPageState,IprFileType,IprRecord } from "../types";

interface IprFilesPanelProps {
  detail: IprRecord;
  iprSectionErrors: { files: string };
  attachments: Attachment[];
  filesPageState: IprDetailPageState;
  iprFileTypes: IprFileType[];
  iprFileOpen: boolean;
  iprFileForm: any;
  iprUploadFile: File | null;
  selectedIprFileIds: number[];
  onRefresh: () => void;
  onGenerateDocument: (docType: string) => void;
  onPreviewAttachment: (item: Attachment) => void;
  onDownloadAttachment: (item: Attachment) => void;
  onOpenUpload: () => void;
  onCloseUpload: () => void;
  onUploadFile: () => void;
  onUploadFileChange: (file: File | null) => void;
  onMarkTransmitted: (row: Attachment) => void;
  onMarkSelectedTransmitted: () => void;
  onDeleteFile: (row: Attachment) => Promise<void>;
  onSelectedFileIdsChange: (ids: number[]) => void;
  confirmIprDeletion: (kind: string, label: string, operation: () => Promise<void>) => void;
  onPageChange: (page: number, pageSize: number) => void;
}

export function IprFilesPanel({
  detail,
  iprSectionErrors,
  attachments,
  filesPageState,
  iprFileTypes,
  iprFileOpen,
  iprFileForm,
  iprUploadFile,
  selectedIprFileIds,
  onRefresh,
  onGenerateDocument,
  onPreviewAttachment,
  onDownloadAttachment,
  onOpenUpload,
  onCloseUpload,
  onUploadFile,
  onUploadFileChange,
  onMarkTransmitted,
  onMarkSelectedTransmitted,
  onDeleteFile,
  onSelectedFileIdsChange,
  confirmIprDeletion,
  onPageChange,
}: IprFilesPanelProps) {
  const filesPagination = {
    current: filesPageState.page,
    pageSize: filesPageState.pageSize,
    total: filesPageState.total,
    showSizeChanger: true,
    pageSizeOptions: ["15", "20", "50"],
    onChange: onPageChange,
  };

  return (
    <>
      <Card
        size="small"
        title="案件文书与附件"
        style={{ marginTop: 16 }}
        extra={<Button size="small" onClick={onRefresh}>刷新</Button>}
      >
        {iprSectionErrors.files ? (
          <Alert
            type="error"
            showIcon
            message={iprSectionErrors.files}
            style={{ marginBottom: 12 }}
          />
        ) : null}
        <Space wrap>
          {detail.status !== "草稿" &&
            detail.status !== "待立案审核" &&
            detail.status !== "已驳回" && (
              <>
                <Button onClick={() => onGenerateDocument("case-summary")}>
                  生成案件信息表（DOCX）
                </Button>
                <Button
                  onClick={() => onGenerateDocument("authorization-letter")}
                >
                  生成授权委托书（DOCX）
                </Button>
                <Button
                  onClick={() => onGenerateDocument("law-firm-letter")}
                >
                  生成律所函（DOCX）
                </Button>
                <Button
                  onClick={() => onGenerateDocument("identity-certificate")}
                >
                  生成主体核对单（DOCX）
                </Button>
              </>
            )}
        </Space>
        <div style={{ marginTop: 12 }}>
          {attachments.length
            ? attachments.map((item) => (
                <Space key={item.id} size={0}>
                  <Button
                    type="link"
                    onClick={() => onPreviewAttachment(item)}
                  >
                    {item.original_name}
                  </Button>
                  <Button
                    type="link"
                    onClick={() => onDownloadAttachment(item)}
                  >
                    下载
                  </Button>
                </Space>
              ))
            : "暂无案件附件"}
        </div>
      </Card>
      <Card
        size="small"
        title="案件文档目录"
        style={{ marginTop: 16 }}
        extra={
          detail.status === "在办" ? (
            <Space>
              <Button
                disabled={!selectedIprFileIds.length}
                onClick={onMarkSelectedTransmitted}
              >
                批量标记已转
              </Button>
              <Button size="small" type="primary" onClick={onOpenUpload}>
                上传文档
              </Button>
            </Space>
          ) : null
        }
      >
        {iprSectionErrors.files ? (
          <Alert
            type="error"
            showIcon
            message={iprSectionErrors.files}
            style={{ marginBottom: 12 }}
          />
        ) : null}
        <Table
          rowKey="id"
          size="small"
          pagination={filesPagination}
          dataSource={attachments}
          rowSelection={{
            selectedRowKeys: selectedIprFileIds,
            onChange: (keys) => onSelectedFileIdsChange(keys.map(Number)),
            getCheckboxProps: (row: Attachment) => ({
              disabled: !row.requires_transmission || !!row.is_transmitted,
            }),
          }}
          scroll={{ x: 760 }}
          columns={[
            {
              title: "文档类型",
              dataIndex: "category",
              width: 140,
              ellipsis: true,
            },
            {
              title: "文件名称",
              dataIndex: "original_name",
              width: 220,
              ellipsis: true,
              render: (_, row: Attachment) => (
                <Space size={0}>
                  <Button type="link" onClick={() => onPreviewAttachment(row)}>
                    {row.original_name}
                  </Button>
                  <Button
                    type="link"
                    onClick={() => onDownloadAttachment(row)}
                  >
                    下载
                  </Button>
                </Space>
              ),
            },
            {
              title: "上传人",
              dataIndex: "uploader_display_name",
              width: 95,
              render: (value) =>
                String(value || "").trim() || "姓名待维护",
            },
            {
              title: "文档日期",
              dataIndex: "document_date",
              width: 110,
              render: (value) => value || "—",
            },
            {
              title: "待转文",
              width: 100,
              render: (_, row: Attachment) =>
                row.requires_transmission ? (
                  row.is_transmitted ? (
                    <Tag color="green">已转</Tag>
                  ) : (
                    <Tag color="gold">是</Tag>
                  )
                ) : (
                  "否"
                ),
            },
            {
              title: "操作",
              fixed: "right",
              width: 150,
              render: (_, row: Attachment) => (
                <Space size={0}>
                  {detail.status === "在办" &&
                    row.requires_transmission &&
                    !row.is_transmitted && (
                      <Button
                        type="link"
                        onClick={() => onMarkTransmitted(row)}
                      >
                        标记已转
                      </Button>
                    )}
                  {detail.status === "在办" && (
                    <Button
                      type="link"
                      danger
                      onClick={() =>
                        confirmIprDeletion(
                          "file",
                          row.original_name,
                          () => onDeleteFile(row)
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

      <Modal
        open={iprFileOpen}
        title="上传知识产权案件文档"
        onCancel={onCloseUpload}
        onOk={onUploadFile}
        okText="上传"
      >
        <Form form={iprFileForm} layout="vertical">
          <Form.Item
            name="category"
            label="文档类型"
            rules={[{ required: true, message: "请选择文档类型" }]}
          >
            <Select
              placeholder="请选择管理员配置且适用于本案件的文档类型"
              options={iprFileTypes.map((item) => ({
                value: item.name,
                label: `${item.name}${item.requires_transmission ? "（待转文）" : ""}`,
              }))}
            />
          </Form.Item>
          <Form.Item
            name="document_date"
            label="文档日期"
            rules={[{ required: true }]}
          >
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <div style={{ marginBottom: 16, color: "#666" }}>
            待转文属性由管理员配置的文件类型决定，上传人不能自行绕过。
          </div>
          <Form.Item label="案件文档" required>
            <AttachmentFileInput
              accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.png,.jpg,.jpeg,.zip,.rar"
              onFileChange={onUploadFileChange} />
            {iprUploadFile && <div>{iprUploadFile.name}</div>}
          </Form.Item>
          <Form.Item name="remark" label="说明">
            <Input.TextArea rows={2} maxLength={1000} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
