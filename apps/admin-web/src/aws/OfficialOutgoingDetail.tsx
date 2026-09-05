import { Button, Card, Descriptions, Drawer, Popconfirm, Space, Table, Timeline, Upload } from "antd";
import { UploadOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import type { Attachment, HistoryEvent, RecordRow } from "./types";
import { fileSize, personDisplayName } from "./constants";

interface OfficialOutgoingDetailProps {
  open: boolean;
  detail: any;
  history: HistoryEvent[];
  onClose: () => void;
  onOpenSource: (row: any) => void;
  onPreviewAttachment: (row: Attachment) => void;
  onUploadFile: (row: any, file: File, stamped?: boolean) => void;
  onDeleteFile: (row: any, attachment: Attachment) => void;
  onSubmit: (row: RecordRow) => void;
}

export function OfficialOutgoingDetail({
  open,
  detail,
  history,
  onClose,
  onOpenSource,
  onPreviewAttachment,
  onUploadFile,
  onDeleteFile,
  onSubmit,
}: OfficialOutgoingDetailProps) {
  const isEditable = detail && ["草稿", "已拒绝", "已撤回"].includes(detail.status);

  return (
    <Drawer
      open={open}
      title={detail ? `正式发文详情：${detail.official_no || detail.serial_no}` : "正式发文详情"}
      width={760}
      onClose={onClose}
    >
      {detail && (
        <>
          <Descriptions
            bordered
            size="small"
            column={2}
            items={[
              { key: "title", label: "文书名称", children: detail.title },
              { key: "status", label: "状态", children: detail.status },
              {
                key: "source",
                label: "来源业务",
                children: detail.source_serial_no ? (
                  <Button type="link" className="case-cell-link" onClick={() => onOpenSource(detail)}>
                    {`${detail.source_type === "contract" ? "合同" : "案件"}｜${detail.source_serial_no}`}
                  </Button>
                ) : (
                  "—"
                ),
              },
              { key: "seal", label: "印章类型", children: detail.seal_type || "—" },
              { key: "copies", label: "盖章份数", children: detail.print_quantity || 1 },
              { key: "electronic", label: "电子印章", children: detail.is_electronic_seal ? "是" : "否" },
              { key: "offline", label: "打印盖章", children: detail.is_offline_print ? "需要" : "不需要" },
              { key: "customer", label: "客户名称", children: detail.customer || "—" },
              {
                key: "applied",
                label: "申请时间",
                children: detail.created_at ? dayjs(detail.created_at).format("YYYY-MM-DD HH:mm") : "—",
              },
              { key: "content", label: "文书内容", children: detail.content || "—", span: 2 },
              { key: "remark", label: "备注", children: detail.description || "—", span: 2 },
            ]}
          />
          <Card
            size="small"
            title="正式发文附件"
            style={{ marginTop: 16 }}
            extra={
              isEditable ? (
                <Upload
                  key="upload"
                  showUploadList={false}
                  beforeUpload={(item) => {
                    void onUploadFile(detail, item as unknown as File);
                    return false;
                  }}
                >
                  <Button icon={<UploadOutlined />}>上传附件</Button>
                </Upload>
              ) : null
            }
          >
            <Table
              size="small"
              rowKey="id"
              pagination={false}
              dataSource={detail.attachments || []}
              columns={[
                { title: "文件名称", dataIndex: "original_name", ellipsis: true },
                { title: "类别", dataIndex: "category", width: 150 },
                { title: "大小", dataIndex: "size", width: 100, render: (value: number) => fileSize(value) },
                { title: "上传人", dataIndex: "uploader_display_name", width: 90, render: personDisplayName },
                {
                  title: "上传时间",
                  dataIndex: "created_at",
                  width: 150,
                  render: (value: string) => (value ? new Date(value).toLocaleString() : "—"),
                },
                {
                  title: "操作",
                  width: 180,
                  render: (_, item: Attachment) => (
                    <Space size={2}>
                      <Button type="link" size="small" onClick={() => onPreviewAttachment(item)}>
                        查看
                      </Button>
                      <Button
                        type="link"
                        size="small"
                        onClick={() => window.open(`/api/v1/attachments/${item.id}/download`, "_blank")}
                      >
                        下载
                      </Button>
                      {isEditable && item.category === "正式发文附件" && (
                        <Popconfirm
                          title="确认删除该正式发文附件？"
                          onConfirm={() => onDeleteFile(detail, item)}
                        >
                          <Button danger type="link" size="small">
                            删除
                          </Button>
                        </Popconfirm>
                      )}
                    </Space>
                  ),
                },
              ]}
            />
          </Card>
          {detail.status === "已通过" && (
            <Card size="small" title="盖章文件" style={{ marginTop: 16 }}>
              <Upload
                showUploadList={false}
                beforeUpload={(item) => {
                  void onUploadFile(detail, item as unknown as File, true);
                  return false;
                }}
              >
                <Button type="primary" icon={<UploadOutlined />}>
                  上传盖章文件并标记已盖章
                </Button>
              </Upload>
            </Card>
          )}
          {isEditable && (
            <Button
              style={{ marginTop: 16 }}
              type="primary"
              onClick={() => onSubmit(detail)}
            >
              提交审批
            </Button>
          )}
          <Card size="small" title="审批与办理记录" style={{ marginTop: 16 }}>
            <Timeline
              items={history.map((item) => ({
                color:
                  item.to_status === "已通过" || item.to_status === "已盖章"
                    ? "green"
                    : item.to_status === "已拒绝"
                      ? "red"
                      : "blue",
                children: (
                  <div>
                    <b>{item.action}</b>
                    {item.from_status && <span>　{item.from_status} → {item.to_status}</span>}
                    <div style={{ color: "#999", fontSize: 12 }}>
                      {personDisplayName(item.operator_display_name)} ·{" "}
                      {new Date(item.created_at).toLocaleString("zh-CN")}
                    </div>
                    {item.comment && <div>{item.comment}</div>}
                  </div>
                ),
              }))}
            />
          </Card>
        </>
      )}
    </Drawer>
  );
}
