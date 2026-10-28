import { Alert,Button,Card,Descriptions,Form,Input,Modal } from "antd";
import Table from "../../components/ResizableTable";
import dayjs from "dayjs";
import { personDisplayName } from "../constants";
import type { IprBusinessLog,IprOperationLog,IprRecord } from "../types";

const timeText = (value?: string) => (value ? dayjs(value).format("YYYY-MM-DD HH:mm") : "—");

interface IprBusinessLogsPanelProps {
  detail: IprRecord;
  iprSectionErrors: { logs: string };
  iprBusinessLogs: IprBusinessLog[];
  profile: { role?: string; username?: string };
  iprLogOpen: boolean;
  iprLogForm: any;
  iprBusinessLogDetail: IprBusinessLog | null;
  onOpenLog: () => void;
  onCloseLog: () => void;
  onCreateLog: () => void;
  onDeleteLog: (logId: number) => Promise<void>;
  onSetBusinessLogDetail: (log: IprBusinessLog | null) => void;
  confirmIprDeletion: (kind: string, label: string, operation: () => Promise<void>) => void;
}

/** 案件日志：经办人手写的业务日志，放在案件页右侧（原系统“案件日志”）。 */
export function IprBusinessLogsPanel({
  detail,
  iprSectionErrors,
  iprBusinessLogs,
  profile,
  iprLogOpen,
  iprLogForm,
  iprBusinessLogDetail,
  onOpenLog,
  onCloseLog,
  onCreateLog,
  onDeleteLog,
  onSetBusinessLogDetail,
  confirmIprDeletion,
}: IprBusinessLogsPanelProps) {
  const canWrite = ["草稿", "已驳回", "在办"].includes(detail.status);
  const canDelete = (row: IprBusinessLog) =>
    row.created_by === profile.username || ["admin", "manager"].includes(profile.role || "");
  return (
    <>
      <Card
        size="small"
        title="案件日志"
        extra={canWrite ? <Button size="small" type="link" onClick={onOpenLog}>新增日志</Button> : null}
      >
        {iprSectionErrors.logs ? (
          <Alert type="error" showIcon message={iprSectionErrors.logs} style={{ marginBottom: 12 }} />
        ) : null}
        <Table
          rowKey="id"
          size="small"
          pagination={false}
          locale={{ emptyText: "暂未填写案件日志" }}
          dataSource={iprBusinessLogs}
          columns={[
            {
              title: "内容",
              dataIndex: "content",
              ellipsis: true,
              render: (content: string, row: IprBusinessLog) => (
                <Button type="link" size="small" onClick={() => onSetBusinessLogDetail(row)}>
                  {content}
                </Button>
              ),
            },
            {
              title: "时间",
              dataIndex: "created_at",
              width: 96,
              render: (value) => (value ? dayjs(value).format("YYYY-MM-DD") : "—"),
            },
          ]}
        />
      </Card>
      <Modal open={iprLogOpen} title="新增案件日志" onCancel={onCloseLog} onOk={onCreateLog} okText="保存日志">
        <Form form={iprLogForm} layout="vertical">
          <Form.Item name="content" label="日志内容" rules={[{ required: true, message: "请填写日志内容" }]}>
            <Input.TextArea rows={5} maxLength={4000} showCount />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={!!iprBusinessLogDetail}
        title="案件日志详情"
        onCancel={() => onSetBusinessLogDetail(null)}
        footer={
          iprBusinessLogDetail && canDelete(iprBusinessLogDetail) ? (
            <Button
              danger
              onClick={() => {
                const row = iprBusinessLogDetail;
                confirmIprDeletion("log", row.content, async () => {
                  await onDeleteLog(row.id);
                  onSetBusinessLogDetail(null);
                });
              }}
            >
              删除
            </Button>
          ) : null
        }
      >
        {iprBusinessLogDetail && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="日志内容">{iprBusinessLogDetail.content}</Descriptions.Item>
            <Descriptions.Item label="创建人">{personDisplayName(iprBusinessLogDetail.created_by_display_name)}</Descriptions.Item>
            <Descriptions.Item label="创建时间">{timeText(iprBusinessLogDetail.created_at)}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </>
  );
}

interface IprOperationLogsPanelProps {
  iprSectionErrors: { logs: string };
  iprOperationLogs: IprOperationLog[];
  iprOperationLogDetail: IprOperationLog | null;
  onSetOperationLogDetail: (log: IprOperationLog | null) => void;
}

/** 系统日志：立案、提交、结案、改字段等系统自动记下的操作（原系统“系统日志”页签）。 */
export function IprOperationLogsPanel({ iprSectionErrors, iprOperationLogs, iprOperationLogDetail, onSetOperationLogDetail }: IprOperationLogsPanelProps) {
  return (
    <>
      {iprSectionErrors.logs ? (
        <Alert type="error" showIcon message={iprSectionErrors.logs} style={{ marginBottom: 12 }} />
      ) : null}
      <Table
        rowKey="id"
        size="small"
        pagination={false}
        locale={{ emptyText: "暂未产生系统日志" }}
        dataSource={iprOperationLogs}
        columns={[
          {
            title: "操作",
            dataIndex: "action",
            width: 180,
            render: (action: string, row: IprOperationLog) => (
              <Button type="link" size="small" onClick={() => onSetOperationLogDetail(row)}>
                {action}
              </Button>
            ),
          },
          {
            title: "状态变化",
            width: 160,
            render: (_, row: IprOperationLog) =>
              row.from_status || row.to_status ? `${row.from_status || "—"} → ${row.to_status || "—"}` : "—",
          },
          { title: "说明", dataIndex: "comment", ellipsis: true, render: (value) => value || "—" },
          { title: "操作人", dataIndex: "operator_display_name", width: 110, render: personDisplayName },
          { title: "时间", dataIndex: "created_at", width: 150, render: timeText },
        ]}
      />
      <Modal open={!!iprOperationLogDetail} title="系统日志详情" footer={null} onCancel={() => onSetOperationLogDetail(null)}>
        {iprOperationLogDetail && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="操作">{iprOperationLogDetail.action}</Descriptions.Item>
            <Descriptions.Item label="说明">{iprOperationLogDetail.comment || "—"}</Descriptions.Item>
            <Descriptions.Item label="操作人">{personDisplayName(iprOperationLogDetail.operator_display_name)}</Descriptions.Item>
            <Descriptions.Item label="原状态">{iprOperationLogDetail.from_status || "—"}</Descriptions.Item>
            <Descriptions.Item label="目标状态">{iprOperationLogDetail.to_status || "—"}</Descriptions.Item>
            <Descriptions.Item label="时间">{timeText(iprOperationLogDetail.created_at)}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </>
  );
}
