import { Alert,Button,Card,Descriptions,Form,Input,Modal,Table } from "antd";
import dayjs from "dayjs";
import { personDisplayName } from "../constants";
import type { IprBusinessLog,IprHistoryItem,IprOperationLog,IprRecord } from "../types";

interface IprLogsPanelProps {
  detail: IprRecord;
  iprSectionErrors: { logs: string };
  iprBusinessLogs: IprBusinessLog[];
  iprOperationLogs: IprOperationLog[];
  iprHistory: IprHistoryItem[];
  profile: { role?: string; username?: string };
  iprLogOpen: boolean;
  iprLogForm: any;
  iprBusinessLogDetail: IprBusinessLog | null;
  iprOperationLogDetail: IprOperationLog | null;
  iprHistoryDetail: IprHistoryItem | null;
  onOpenLog: () => void;
  onCloseLog: () => void;
  onCreateLog: () => void;
  onDeleteLog: (logId: number) => Promise<void>;
  onSetBusinessLogDetail: (log: IprBusinessLog | null) => void;
  onSetOperationLogDetail: (log: IprOperationLog | null) => void;
  onSetHistoryDetail: (item: IprHistoryItem | null) => void;
  confirmIprDeletion: (kind: string, label: string, operation: () => Promise<void>) => void;
}

export function IprLogsPanel({
  detail,
  iprSectionErrors,
  iprBusinessLogs,
  iprOperationLogs,
  iprHistory,
  profile,
  iprLogOpen,
  iprLogForm,
  iprBusinessLogDetail,
  iprOperationLogDetail,
  iprHistoryDetail,
  onOpenLog,
  onCloseLog,
  onCreateLog,
  onDeleteLog,
  onSetBusinessLogDetail,
  onSetOperationLogDetail,
  onSetHistoryDetail,
  confirmIprDeletion,
}: IprLogsPanelProps) {
  return (
    <>
      <Card
        size="small"
        title="案件业务日志与操作日志"
        style={{ marginTop: 16 }}
        extra={
          detail.status === "草稿" ||
          detail.status === "已驳回" ||
          detail.status === "在办" ? (
            <Button size="small" onClick={onOpenLog}>
              新增业务日志
            </Button>
          ) : null
        }
      >
        {iprSectionErrors.logs ? (
          <Alert
            type="error"
            showIcon
            message={iprSectionErrors.logs}
            style={{ marginBottom: 12 }}
          />
        ) : null}
        <Table
          rowKey="id"
          size="small"
          pagination={false}
          locale={{ emptyText: "暂未填写业务日志" }}
          dataSource={iprBusinessLogs}
          columns={[
            {
              title: "内容",
              dataIndex: "content",
              ellipsis: true,
              render: (content: string, row: IprBusinessLog) => (
                <Button
                  type="link"
                  onClick={() => onSetBusinessLogDetail(row)}
                >
                  {content}
                </Button>
              ),
            },
            {
              title: "创建人",
              dataIndex: "created_by_display_name",
              width: 110,
              render: personDisplayName,
            },
            {
              title: "时间",
              dataIndex: "created_at",
              width: 170,
              render: (value) =>
                value ? dayjs(value).format("YYYY-MM-DD HH:mm") : "—",
            },
            {
              title: "操作",
              width: 90,
              render: (_, row) =>
                row.created_by === profile.username ||
                ["admin", "manager"].includes(profile.role || "") ? (
                  <Button
                    danger
                    type="link"
                    size="small"
                    onClick={() =>
                      confirmIprDeletion("log", row.content, () =>
                        onDeleteLog(row.id)
                      )
                    }
                  >
                    删除
                  </Button>
                ) : (
                  "—"
                ),
            },
          ]}
        />
        <Table
          rowKey="id"
          size="small"
          pagination={false}
          style={{ marginTop: 12 }}
          locale={{ emptyText: "暂未产生操作日志" }}
          dataSource={iprOperationLogs}
          columns={[
            {
              title: "操作",
              dataIndex: "action",
              width: 180,
              render: (action: string, row: IprOperationLog) => (
                <Button
                  type="link"
                  onClick={() => onSetOperationLogDetail(row)}
                >
                  {action}
                </Button>
              ),
            },
            {
              title: "说明",
              dataIndex: "comment",
              ellipsis: true,
              render: (value) => value || "—",
            },
            {
              title: "操作人",
              dataIndex: "operator_display_name",
              width: 110,
              render: personDisplayName,
            },
            {
              title: "时间",
              dataIndex: "created_at",
              width: 170,
              render: (value) =>
                value ? dayjs(value).format("YYYY-MM-DD HH:mm") : "—",
            },
          ]}
        />
      </Card>
      <Card size="small" title="案件事项记录" style={{ marginTop: 16 }}>
        <Table
          rowKey="id"
          size="small"
          pagination={false}
          dataSource={iprHistory}
          locale={{ emptyText: "暂无案件事项记录" }}
          columns={[
            {
              title: "事项",
              dataIndex: "action",
              width: 160,
              render: (action: string, row: IprHistoryItem) => (
                <Button type="link" onClick={() => onSetHistoryDetail(row)}>
                  {action}
                </Button>
              ),
            },
            {
              title: "状态变化",
              width: 180,
              render: (_, row: IprHistoryItem) =>
                row.from_status || row.to_status
                  ? `${row.from_status || "—"} → ${row.to_status || "—"}`
                  : "—",
            },
            { title: "说明", dataIndex: "comment", ellipsis: true },
            {
              title: "操作人",
              dataIndex: "operator_display_name",
              width: 110,
              render: personDisplayName,
            },
            {
              title: "时间",
              dataIndex: "created_at",
              width: 170,
              render: (value) =>
                value ? dayjs(value).format("YYYY-MM-DD HH:mm") : "—",
            },
          ]}
        />
      </Card>

      <Modal
        open={iprLogOpen}
        title="新增案件业务日志"
        onCancel={onCloseLog}
        onOk={onCreateLog}
        okText="保存日志"
      >
        <Form form={iprLogForm} layout="vertical">
          <Form.Item
            name="content"
            label="业务日志内容"
            rules={[{ required: true, message: "请填写业务日志内容" }]}
          >
            <Input.TextArea rows={5} maxLength={4000} showCount />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={!!iprBusinessLogDetail}
        title="案件业务日志详情"
        footer={null}
        onCancel={() => onSetBusinessLogDetail(null)}
      >
        {iprBusinessLogDetail && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="日志内容">
              {iprBusinessLogDetail.content}
            </Descriptions.Item>
            <Descriptions.Item label="创建人">
              {personDisplayName(iprBusinessLogDetail.created_by_display_name)}
            </Descriptions.Item>
            <Descriptions.Item label="创建时间">
              {iprBusinessLogDetail.created_at}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
      <Modal
        open={!!iprOperationLogDetail}
        title="案件操作日志详情"
        footer={null}
        onCancel={() => onSetOperationLogDetail(null)}
      >
        {iprOperationLogDetail && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="操作">
              {iprOperationLogDetail.action}
            </Descriptions.Item>
            <Descriptions.Item label="说明">
              {iprOperationLogDetail.comment || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="操作人">
              {personDisplayName(iprOperationLogDetail.operator_display_name)}
            </Descriptions.Item>
            <Descriptions.Item label="原状态">
              {iprOperationLogDetail.from_status || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="目标状态">
              {iprOperationLogDetail.to_status || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="时间">
              {iprOperationLogDetail.created_at}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
      <Modal
        open={!!iprHistoryDetail}
        title="案件事项详情"
        footer={null}
        onCancel={() => onSetHistoryDetail(null)}
      >
        {iprHistoryDetail && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="事项">
              {iprHistoryDetail.action}
            </Descriptions.Item>
            <Descriptions.Item label="状态变化">
              {iprHistoryDetail.from_status || iprHistoryDetail.to_status
                ? `${iprHistoryDetail.from_status || "—"} → ${
                    iprHistoryDetail.to_status || "—"
                  }`
                : "—"}
            </Descriptions.Item>
            <Descriptions.Item label="说明">
              {iprHistoryDetail.comment || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="操作人">
              {personDisplayName(iprHistoryDetail.operator_display_name)}
            </Descriptions.Item>
            <Descriptions.Item label="时间">
              {iprHistoryDetail.created_at}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </>
  );
}
