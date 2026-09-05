import { Button, Card, Descriptions, Drawer, Space, Table, Tag, Timeline } from "antd";
import { UploadOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import type { Attachment, HistoryEvent, RecordRow } from "./types";
import { personDisplayName } from "./constants";

interface DocumentDetailProps {
  open: boolean;
  viewing: RecordRow | null;
  attachments: Attachment[];
  history: HistoryEvent[];
  actionButton?: React.ReactNode;
  onClose: () => void;
  onOpenCustomerDetail: (customer: string) => void;
  onOpenCaseDetail: (caseNo: string) => void;
  onPreviewAttachment: (row: Attachment) => void;
  onDownload: (row: Attachment) => void;
  onOpenUpload: (target: RecordRow, category: string) => void;
}

export function DocumentDetail({
  open,
  viewing,
  attachments,
  history,
  actionButton,
  onClose,
  onOpenCustomerDetail,
  onOpenCaseDetail,
  onPreviewAttachment,
  onDownload,
  onOpenUpload,
}: DocumentDetailProps) {
  const recordAttachments = attachments.filter((a) => a.record_id === viewing?.id);

  return (
    <Drawer
      size={720}
      open={open}
      title={`收发文详情：${viewing?.serial_no || ""}`}
      onClose={onClose}
      extra={viewing && actionButton}
    >
      {viewing && (
        <>
          <Descriptions bordered size="small" column={2}>
            <Descriptions.Item label="文件名称" span={2}>
              {viewing.title}
            </Descriptions.Item>
            <Descriptions.Item label="收发类型">
              <Tag
                color={viewing.data.direction === "发文" ? "blue" : "green"}
              >
                {viewing.data.direction}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={viewing.status === "已归档" ? "green" : "blue"}>
                {viewing.status}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="客户/主体" span={2}>
              {viewing.customer ? (
                <Button type="link" onClick={() => onOpenCustomerDetail(viewing.customer)}>
                  {viewing.customer}
                </Button>
              ) : (
                "—"
              )}
            </Descriptions.Item>
            <Descriptions.Item label="关联案号">
              {viewing.data.case_no ? (
                <Button type="link" onClick={() => onOpenCaseDetail(viewing.data.case_no)}>
                  {viewing.data.case_no}
                </Button>
              ) : (
                "—"
              )}
            </Descriptions.Item>
            <Descriptions.Item label="来文/送达单位">
              {viewing.data.sender || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="负责人">
              {personDisplayName(viewing.owner_display_name)}
            </Descriptions.Item>
            <Descriptions.Item label="登记日期">
              {viewing.data.registered_at || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="签收/送达日期">
              {viewing.data.signed_at || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="签收/确认人">
              {personDisplayName(viewing.data.signer_display_name)}
            </Descriptions.Item>
            <Descriptions.Item label="归档编号">
              {viewing.data.archive_no || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="存放位置">
              {viewing.data.archive_location || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="备注" span={2}>
              {viewing.description || "—"}
            </Descriptions.Item>
          </Descriptions>
          <Card
            size="small"
            title={`关联附件（${recordAttachments.length}）`}
            style={{ marginTop: 16 }}
            extra={
              <Button
                type="link"
                icon={<UploadOutlined />}
                onClick={() =>
                  onOpenUpload(
                    viewing,
                    viewing.data.direction === "发文" ? "发文附件" : "收文附件",
                  )
                }
              >
                上传附件
              </Button>
            }
          >
            <Table
              rowKey="id"
              size="small"
              pagination={false}
              dataSource={recordAttachments}
              columns={[
                {
                  title: "文件名",
                  dataIndex: "original_name",
                  ellipsis: true,
                },
                { title: "分类", dataIndex: "category", width: 100 },
                { title: "上传人", dataIndex: "uploader_display_name", width: 80, render: personDisplayName },
                {
                  title: "操作",
                  width: 100,
                  render: (_: unknown, r: Attachment) => (
                    <Space size={0}>
                      <Button type="link" onClick={() => onPreviewAttachment(r)}>
                        查看
                      </Button>
                      <Button type="link" onClick={() => onDownload(r)}>
                        下载
                      </Button>
                    </Space>
                  ),
                },
              ]}
            />
          </Card>
          <Card size="small" title="办理记录" style={{ marginTop: 16 }}>
            <Timeline
              items={history.map((x) => ({
                color: x.to_status === "已归档" ? "green" : "blue",
                children: (
                  <div>
                    <b>{x.action}</b>
                    {x.from_status && (
                      <span>
                        　{x.from_status} → {x.to_status}
                      </span>
                    )}
                    <div style={{ color: "#999", fontSize: 12 }}>
                      {personDisplayName(x.operator_display_name)} ·{" "}
                      {new Date(x.created_at).toLocaleString("zh-CN")}
                    </div>
                    {x.comment && <div>{x.comment}</div>}
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
